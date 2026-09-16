"""
All the calculations sit here, separate from the web layer.

Each function takes the loaded tables plus a filter (warehouse, number of days)
and returns plain Python types, so the FastAPI layer only has to hand them over
as JSON.
"""

import datetime as dt

import pandas as pd

from . import store


def _filter(df: pd.DataFrame, warehouse: str, days: int, date_col: str = "date") -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df
    if warehouse and warehouse != "All" and "warehouse" in out.columns:
        out = out[out["warehouse"] == warehouse]
    if days and date_col in out.columns:
        cutoff = dt.date.today() - dt.timedelta(days=days - 1)
        col = pd.to_datetime(out[date_col], errors="coerce").dt.date
        out = out[col >= cutoff]
    return out


def _stock_now(warehouse: str = "All") -> pd.DataFrame:
    """The current stock position. With a dated stock sheet, only the latest day counts."""
    d = store.load()
    stock = d["stock"]
    if stock is None or stock.empty:
        return stock
    if "date" in stock.columns:
        latest = pd.to_datetime(stock["date"], errors="coerce").max()
        stock = stock[pd.to_datetime(stock["date"], errors="coerce") == latest]
    if warehouse and warehouse != "All":
        stock = stock[stock["warehouse"] == warehouse]
    return stock


def _pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, 1)


def meta() -> dict:
    d = store.load()
    wh = sorted(d["wh_ops"]["warehouse"].dropna().unique().tolist())
    return dict(
        warehouses=["All"] + wh,
        source=store.source(),
        loaded_at=store.loaded_at(),
        today=dt.date.today().strftime("%d-%m-%Y"),
    )


def summary(warehouse: str = "All", days: int = 30) -> dict:
    d = store.load()
    today = dt.date.today()

    dispatch = _filter(d["dispatch"], warehouse, days)
    inward = _filter(d["inward"], warehouse, days)
    orders = _filter(d["orders"], warehouse, days, "order_date")
    ops = _filter(d["wh_ops"], warehouse, days)
    complaints = _filter(d["complaints"], warehouse, days)

    stock = _stock_now(warehouse)

    # stock and expiry
    stock_units = int(stock["closing_qty"].sum()) if not stock.empty else 0
    exp = pd.to_datetime(stock["expiry_date"], errors="coerce").dt.date
    near_expiry = int(stock.loc[(exp - today).apply(lambda x: x.days) <= 90, "closing_qty"].sum()) if not stock.empty else 0

    # orders and fill rate
    ordered = int(orders["order_qty"].sum()) if not orders.empty else 0
    dispatched_against = int(orders["dispatched_qty"].sum()) if not orders.empty else 0
    pending_orders = orders[orders["status"].isin(["Open", "Partial"])] if not orders.empty else orders
    pending_count = int(len(pending_orders))
    pending_qty = int((pending_orders["order_qty"] - pending_orders["dispatched_qty"]).sum()) if not pending_orders.empty else 0

    # delivery performance
    on_time = 0.0
    if not dispatch.empty and "actual_delivery" in dispatch.columns:
        delivered = dispatch.dropna(subset=["actual_delivery"])
        if not delivered.empty:
            act = pd.to_datetime(delivered["actual_delivery"], errors="coerce").dt.date
            exp_d = pd.to_datetime(delivered["expected_delivery"], errors="coerce").dt.date
            on_time = _pct(int((act <= exp_d).sum()), len(delivered))

    # warehouse operations
    space_util = 0.0
    lines_per_mh = 0.0
    pending_grn = 0
    if not ops.empty:
        latest_day = ops["date"].max()
        latest = ops[ops["date"] == latest_day]
        space_util = _pct(int(latest["occupied_pallets"].sum()), int(latest["capacity_pallets"].sum()))
        total_lines = int(ops["inward_lines"].sum() + ops["outward_lines"].sum())
        total_mh = int(ops["manhours"].sum())
        lines_per_mh = round(total_lines / total_mh, 2) if total_mh else 0.0
        pending_grn = int((latest["grns_received"] - latest["grns_posted"]).sum())

    open_complaints = int((complaints["status"] != "Closed").sum()) if not complaints.empty else 0

    return dict(
        period_days=days,
        warehouse=warehouse,
        tiles=[
            dict(key="stock_units", label="Stock in Hand", value=stock_units, unit="units", hint="Closing stock across all batches"),
            dict(key="inward_qty", label="Inward", value=int(inward["qty"].sum()) if not inward.empty else 0, unit="units", hint=f"Received in last {days} days"),
            dict(key="dispatch_qty", label="Dispatched", value=int(dispatch["qty"].sum()) if not dispatch.empty else 0, unit="units", hint=f"Sent out in last {days} days"),
            dict(key="fill_rate", label="Order Fill Rate", value=_pct(dispatched_against, ordered), unit="%", hint="Dispatched quantity against ordered"),
            dict(key="pending_orders", label="Pending Orders", value=pending_count, unit="orders", hint=f"{pending_qty:,} units not yet sent"),
            dict(key="on_time", label="On-Time Delivery", value=on_time, unit="%", hint="Delivered on or before promised date"),
            dict(key="near_expiry", label="Near Expiry", value=near_expiry, unit="units", hint="Expiring within 90 days"),
            dict(key="open_complaints", label="Open Complaints", value=open_complaints, unit="nos", hint="Not yet closed"),
            dict(key="space_util", label="Space Utilisation", value=space_util, unit="%", hint="Pallet positions occupied today"),
            dict(key="pending_grn", label="Pending GRN", value=pending_grn, unit="nos", hint="Received today but not yet posted"),
        ],
    )


def trend(warehouse: str = "All", days: int = 30) -> dict:
    """Daily inward against outward, from the warehouse operations sheet."""
    d = store.load()
    ops = _filter(d["wh_ops"], warehouse, days)
    if ops.empty:
        return dict(labels=[], inward=[], outward=[])
    g = ops.groupby("date", as_index=False)[["inward_qty", "outward_qty"]].sum().sort_values("date")
    return dict(
        labels=[pd.Timestamp(x).strftime("%d-%b") for x in g["date"]],
        inward=[int(v) for v in g["inward_qty"]],
        outward=[int(v) for v in g["outward_qty"]],
    )


def productivity(warehouse: str = "All", days: int = 30) -> dict:
    d = store.load()
    ops = _filter(d["wh_ops"], warehouse, days)
    if ops.empty:
        return dict(labels=[], lines_per_manhour=[], space_util=[])
    g = ops.groupby("date", as_index=False)[
        ["inward_lines", "outward_lines", "manhours", "occupied_pallets", "capacity_pallets"]
    ].sum().sort_values("date")
    lpm = ((g["inward_lines"] + g["outward_lines"]) / g["manhours"].replace(0, pd.NA)).fillna(0)
    util = (g["occupied_pallets"] / g["capacity_pallets"].replace(0, pd.NA) * 100).fillna(0)
    return dict(
        labels=[pd.Timestamp(x).strftime("%d-%b") for x in g["date"]],
        lines_per_manhour=[round(float(v), 2) for v in lpm],
        space_util=[round(float(v), 1) for v in util],
    )


def expiry(warehouse: str = "All") -> dict:
    """Near-expiry stock, bucketed, plus the worst cases as a table."""
    d = store.load()
    today = dt.date.today()
    stock = _stock_now(warehouse)
    if stock.empty:
        return dict(buckets=[], rows=[])

    s = stock.copy()
    s["days_to_expiry"] = (pd.to_datetime(s["expiry_date"], errors="coerce").dt.date - today).apply(
        lambda x: x.days if pd.notna(x) else 9999
    )

    edges = [(0, 30, "0-30 days"), (31, 60, "31-60 days"), (61, 90, "61-90 days"),
             (91, 180, "91-180 days"), (181, 99999, "Above 180 days")]
    buckets = []
    for lo, hi, label in edges:
        sel = s[(s["days_to_expiry"] >= lo) & (s["days_to_expiry"] <= hi)]
        buckets.append(dict(label=label, qty=int(sel["closing_qty"].sum()), batches=int(len(sel))))

    items = d["items"].set_index("item_code")["item_name"].to_dict()
    top = s[s["days_to_expiry"] <= 90].sort_values("days_to_expiry").head(25)
    rows = [
        dict(
            warehouse=r.warehouse,
            item=items.get(r.item_code, r.item_code),
            batch=r.batch_no,
            expiry=pd.Timestamp(r.expiry_date).strftime("%d-%m-%Y"),
            days=int(r.days_to_expiry),
            qty=int(r.closing_qty),
        )
        for r in top.itertuples()
    ]
    return dict(buckets=buckets, rows=rows)


def ageing(warehouse: str = "All") -> dict:
    """Slow and non-moving stock, by days since last movement."""
    d = store.load()
    today = dt.date.today()
    stock = _stock_now(warehouse)
    if stock.empty or "last_movement_date" not in stock.columns:
        return dict(buckets=[])
    s = stock.copy()
    s["age"] = (today - pd.to_datetime(s["last_movement_date"], errors="coerce").dt.date).apply(
        lambda x: x.days if pd.notna(x) else 0
    )
    edges = [(0, 7, "0-7 days"), (8, 30, "8-30 days"), (31, 60, "31-60 days"),
             (61, 90, "61-90 days"), (91, 99999, "Above 90 days")]
    return dict(
        buckets=[
            dict(label=label, qty=int(s.loc[(s["age"] >= lo) & (s["age"] <= hi), "closing_qty"].sum()))
            for lo, hi, label in edges
        ]
    )


def clients(warehouse: str = "All", days: int = 30, limit: int = 10) -> dict:
    d = store.load()
    dispatch = _filter(d["dispatch"], warehouse, days)
    if dispatch.empty:
        return dict(labels=[], qty=[])
    names = d["clients"].set_index("client_code")["client_name"].to_dict()
    g = dispatch.groupby("client_code", as_index=False)["qty"].sum().sort_values("qty", ascending=False).head(limit)
    return dict(
        labels=[names.get(c, c) for c in g["client_code"]],
        qty=[int(v) for v in g["qty"]],
    )


def warehouses(days: int = 30) -> dict:
    d = store.load()
    ops = _filter(d["wh_ops"], "All", days)
    if ops.empty:
        return dict(labels=[], inward=[], outward=[])
    g = ops.groupby("warehouse", as_index=False)[["inward_qty", "outward_qty"]].sum()
    return dict(
        labels=g["warehouse"].tolist(),
        inward=[int(v) for v in g["inward_qty"]],
        outward=[int(v) for v in g["outward_qty"]],
    )


def pending_orders(warehouse: str = "All", days: int = 30, limit: int = 30) -> dict:
    d = store.load()
    orders = _filter(d["orders"], warehouse, days, "order_date")
    if orders.empty:
        return dict(rows=[], reasons=[])
    p = orders[orders["status"].isin(["Open", "Partial"])].copy()
    if p.empty:
        return dict(rows=[], reasons=[])
    p["pending_qty"] = p["order_qty"] - p["dispatched_qty"]
    p["age"] = (dt.date.today() - pd.to_datetime(p["order_date"], errors="coerce").dt.date).apply(
        lambda x: x.days if pd.notna(x) else 0
    )
    names = d["clients"].set_index("client_code")["client_name"].to_dict()
    items = d["items"].set_index("item_code")["item_name"].to_dict()
    top = p.sort_values(["age", "pending_qty"], ascending=[False, False]).head(limit)
    rows = [
        dict(
            order_no=r.order_no,
            date=pd.Timestamp(r.order_date).strftime("%d-%m-%Y"),
            age=int(r.age),
            client=names.get(r.client_code, r.client_code),
            warehouse=r.warehouse,
            item=items.get(r.item_code, r.item_code),
            pending=int(r.pending_qty),
            status=r.status,
            reason=r.reason or "-",
        )
        for r in top.itertuples()
    ]
    rg = p.groupby("reason", as_index=False)["pending_qty"].sum().sort_values("pending_qty", ascending=False)
    reasons = [dict(label=r.reason or "Not stated", qty=int(r.pending_qty)) for r in rg.itertuples()]
    return dict(rows=rows, reasons=reasons)


def transporters(warehouse: str = "All", days: int = 30) -> dict:
    d = store.load()
    dispatch = _filter(d["dispatch"], warehouse, days)
    if dispatch.empty:
        return dict(rows=[])
    names = d["transporters"].set_index("transporter_code")
    rows = []
    for code, g in dispatch.groupby("transporter_code"):
        delivered = g.dropna(subset=["actual_delivery"])
        if delivered.empty:
            on_time, avg_tat = 0.0, 0.0
        else:
            act = pd.to_datetime(delivered["actual_delivery"], errors="coerce").dt.date
            exp_d = pd.to_datetime(delivered["expected_delivery"], errors="coerce").dt.date
            disp = pd.to_datetime(delivered["date"], errors="coerce").dt.date
            on_time = _pct(int((act <= exp_d).sum()), len(delivered))
            avg_tat = round(float((act - disp).apply(lambda x: x.days).mean()), 1)
        pod = _pct(int((g["pod_received"] == "Y").sum()), len(g))
        rows.append(
            dict(
                code=code,
                name=str(names.loc[code, "transporter_name"]) if code in names.index else code,
                consignments=int(len(g)),
                qty=int(g["qty"].sum()),
                committed_tat=int(names.loc[code, "committed_tat"]) if code in names.index else 0,
                avg_tat=avg_tat,
                on_time=on_time,
                pod=pod,
            )
        )
    rows.sort(key=lambda r: r["on_time"], reverse=True)
    return dict(rows=rows)


def complaints(warehouse: str = "All", days: int = 30) -> dict:
    d = store.load()
    c = _filter(d["complaints"], warehouse, days)
    if c.empty:
        return dict(tiles=[], by_category=[], by_cause=[], by_client=[], by_warehouse=[], ageing=[], rows=[])

    today = dt.date.today()
    total = int(len(c))
    closed = int((c["status"] == "Closed").sum())
    open_ = total - closed

    closed_rows = c.dropna(subset=["closure_date"])
    if not closed_rows.empty:
        tat = (
            pd.to_datetime(closed_rows["closure_date"], errors="coerce").dt.date
            - pd.to_datetime(closed_rows["date"], errors="coerce").dt.date
        ).apply(lambda x: x.days)
        avg_tat = round(float(tat.mean()), 1)
    else:
        avg_tat = 0.0

    open_rows = c[c["status"] != "Closed"].copy()
    open_rows["age"] = (today - pd.to_datetime(open_rows["date"], errors="coerce").dt.date).apply(
        lambda x: x.days if pd.notna(x) else 0
    )
    buckets = [(0, 2, "0-2 days"), (3, 7, "3-7 days"), (8, 99999, "Above 7 days")]
    ageing_rows = [
        dict(label=label, count=int(((open_rows["age"] >= lo) & (open_rows["age"] <= hi)).sum()))
        for lo, hi, label in buckets
    ]

    cat = c.groupby("category", as_index=False).size().sort_values("size", ascending=False)
    cause = c[c["root_cause"] != "Not Established"].groupby("root_cause", as_index=False).size().sort_values("size", ascending=False)

    names = d["clients"].set_index("client_code")["client_name"].to_dict()
    rows = [
        dict(
            no=r.complaint_no,
            date=pd.Timestamp(r.date).strftime("%d-%m-%Y"),
            age=int(r.age),
            client=names.get(r.client_code, r.client_code),
            warehouse=r.warehouse,
            category=r.category,
            severity=r.severity,
        )
        for r in open_rows.sort_values("age", ascending=False).head(25).itertuples()
    ]

    repeat = 0
    if not c.empty:
        pairs = c.groupby(["client_code", "category"]).size()
        repeat = int((pairs - 1).clip(lower=0).sum())

    client_names = d["clients"].set_index("client_code")["client_name"].to_dict()
    by_client_g = c.groupby("client_code", as_index=False).size().sort_values("size", ascending=False).head(10)
    by_wh_g = c.groupby("warehouse", as_index=False).size().sort_values("size", ascending=False)

    return dict(
        by_client=[dict(label=client_names.get(r.client_code, r.client_code), count=int(r.size))
                   for r in by_client_g.itertuples()],
        by_warehouse=[dict(label=r.warehouse, count=int(r.size)) for r in by_wh_g.itertuples()],
        tiles=[
            dict(label="Total Complaints", value=total),
            dict(label="Closed", value=closed),
            dict(label="Open", value=open_),
            dict(label="Avg Closure TAT", value=avg_tat, unit="days"),
            dict(label="Repeat Complaints", value=repeat),
        ],
        by_category=[dict(label=r.category, count=int(r.size)) for r in cat.itertuples()],
        by_cause=[dict(label=r.root_cause, count=int(r.size)) for r in cause.itertuples()],
        ageing=ageing_rows,
        rows=rows,
    )


def stock_top(warehouse: str = "All", limit: int = 12) -> dict:
    d = store.load()
    stock = _stock_now(warehouse)
    if stock.empty:
        return dict(labels=[], qty=[])
    names = d["items"].set_index("item_code")["item_name"].to_dict()
    g = stock.groupby("item_code", as_index=False)["closing_qty"].sum().sort_values("closing_qty", ascending=False).head(limit)
    return dict(
        labels=[names.get(c, c) for c in g["item_code"]],
        qty=[int(v) for v in g["closing_qty"]],
    )


# ====================================================================
# Views added to close the gaps against the reporting note
# ====================================================================

def companies(warehouse: str = "All", days: int = 30, limit: int = 10) -> dict:
    """Company-wise (principal-wise) dispatch, from section 2.2 of the note."""
    d = store.load()
    dispatch = _filter(d["dispatch"], warehouse, days)
    if dispatch.empty:
        return dict(labels=[], qty=[])
    company = d["items"].set_index("item_code")["company"].to_dict()
    g = dispatch.copy()
    g["company"] = g["item_code"].map(company).fillna("Not mapped")
    g = g.groupby("company", as_index=False)["qty"].sum().sort_values("qty", ascending=False).head(limit)
    return dict(labels=g["company"].tolist(), qty=[int(v) for v in g["qty"]])


def order_flow(warehouse: str = "All", days: int = 30) -> dict:
    """Picking and packing status: how far orders got through the chain."""
    d = store.load()
    ops = _filter(d["wh_ops"], warehouse, days)
    if ops.empty:
        return dict(labels=[], counts=[], pending=[])
    stages = [
        ("Received", "orders_received"),
        ("Picked", "orders_picked"),
        ("Packed", "orders_packed"),
        ("Dispatched", "orders_dispatched"),
    ]
    labels, counts = [], []
    for label, col in stages:
        if col in ops.columns:
            labels.append(label)
            counts.append(int(ops[col].sum()))
    pending = []
    if len(counts) == 4:
        pending = [
            dict(label="Awaiting picking", value=counts[0] - counts[1]),
            dict(label="Picked, not packed", value=counts[1] - counts[2]),
            dict(label="Packed, not dispatched", value=counts[2] - counts[3]),
        ]
    return dict(labels=labels, counts=counts, pending=pending)


def delivery_status(warehouse: str = "All", days: int = 30) -> dict:
    """Delivered, in transit or running late, from section 2.2 of the note."""
    d = store.load()
    dispatch = _filter(d["dispatch"], warehouse, days)
    if dispatch.empty:
        return dict(labels=[], counts=[])
    today = dt.date.today()
    act = pd.to_datetime(dispatch["actual_delivery"], errors="coerce").dt.date
    exp = pd.to_datetime(dispatch["expected_delivery"], errors="coerce").dt.date

    delivered_on_time = int(((act.notna()) & (act <= exp)).sum())
    delivered_late = int(((act.notna()) & (act > exp)).sum())
    overdue = int(((act.isna()) & (exp < today)).sum())
    in_transit = int(len(dispatch)) - delivered_on_time - delivered_late - overdue
    return dict(
        labels=["Delivered on time", "Delivered late", "Overdue", "In transit"],
        counts=[delivered_on_time, delivered_late, overdue, max(0, in_transit)],
    )


def reconciliation(warehouse: str = "All", days: int = 30) -> dict:
    """Opening plus inward minus dispatch equals closing, checked day by day."""
    d = store.load()
    ledger = d.get("stock_ledger")
    if ledger is None or ledger.empty:
        return dict(rows=[], totals={}, unmatched=0)
    led = _filter(ledger, warehouse, days)
    if led.empty:
        return dict(rows=[], totals={}, unmatched=0)

    g = led.groupby("date", as_index=False)[
        ["opening_qty", "inward_qty", "dispatch_qty", "adjustment_qty", "closing_qty"]
    ].sum().sort_values("date", ascending=False)

    rows, unmatched = [], 0
    for r in g.itertuples():
        expected = r.opening_qty + r.inward_qty - r.dispatch_qty + r.adjustment_qty
        variance = int(r.closing_qty - expected)
        if variance:
            unmatched += 1
        rows.append(
            dict(
                date=pd.Timestamp(r.date).strftime("%d-%m-%Y"),
                opening=int(r.opening_qty),
                inward=int(r.inward_qty),
                dispatch=int(r.dispatch_qty),
                adjustment=int(r.adjustment_qty),
                closing=int(r.closing_qty),
                variance=variance,
            )
        )
    totals = dict(
        opening=int(g["opening_qty"].iloc[-1]),
        inward=int(g["inward_qty"].sum()),
        dispatch=int(g["dispatch_qty"].sum()),
        adjustment=int(g["adjustment_qty"].sum()),
        closing=int(g["closing_qty"].iloc[0]),
    )
    return dict(rows=rows[:30], totals=totals, unmatched=unmatched)


def batch_stock(warehouse: str = "All", limit: int = 40) -> dict:
    """Batch-wise stock, the base record behind every inventory report."""
    stock = _stock_now(warehouse)
    if stock.empty:
        return dict(rows=[])
    d = store.load()
    names = d["items"].set_index("item_code")["item_name"].to_dict()
    today = dt.date.today()
    s = stock.copy()
    s["days_to_expiry"] = (pd.to_datetime(s["expiry_date"], errors="coerce").dt.date - today).apply(
        lambda x: x.days if pd.notna(x) else 0
    )
    s = s.sort_values("closing_qty", ascending=False).head(limit)
    return dict(
        rows=[
            dict(
                item=names.get(r.item_code, r.item_code),
                batch=r.batch_no,
                warehouse=r.warehouse,
                expiry=pd.Timestamp(r.expiry_date).strftime("%d-%m-%Y"),
                days=int(r.days_to_expiry),
                qty=int(r.closing_qty),
                blocked=int(getattr(r, "blocked_qty", 0) or 0),
            )
            for r in s.itertuples()
        ]
    )


def returns(warehouse: str = "All", days: int = 30) -> dict:
    """Returns, damages, expiry write-offs and recalls: section 2.4 of the note."""
    d = store.load()
    ret = _filter(d.get("returns"), warehouse, days)
    inward = _filter(d["inward"], warehouse, days)

    damaged_at_receipt = int(inward["damaged_qty"].sum()) if not inward.empty and "damaged_qty" in inward.columns else 0

    if ret is None or ret.empty:
        return dict(tiles=[dict(label="Damaged at receipt", value=damaged_at_receipt, unit="units")],
                    by_type=[], by_action=[], recalls=[], rows=[])

    total_qty = int(ret["qty"].sum())
    non_saleable = int(ret.loc[ret["condition"] == "Non-saleable", "qty"].sum()) if "condition" in ret.columns else 0
    recall_rows = ret[ret["rtype"] == "Recall"] if "rtype" in ret.columns else ret.iloc[0:0]

    names = d["clients"].set_index("client_code")["client_name"].to_dict()
    items = d["items"].set_index("item_code")["item_name"].to_dict()

    by_type = ret.groupby("rtype", as_index=False)["qty"].sum().sort_values("qty", ascending=False)
    by_action = ret.groupby("action", as_index=False)["qty"].sum().sort_values("qty", ascending=False)

    return dict(
        tiles=[
            dict(label="Returned / rejected", value=total_qty, unit="units"),
            dict(label="Damaged at receipt", value=damaged_at_receipt, unit="units"),
            dict(label="Not saleable", value=non_saleable, unit="units"),
            dict(label="Recall entries", value=int(len(recall_rows)), unit="nos"),
        ],
        by_type=[dict(label=r.rtype, qty=int(r.qty)) for r in by_type.itertuples()],
        by_action=[dict(label=r.action or "Not stated", qty=int(r.qty)) for r in by_action.itertuples()],
        recalls=[
            dict(
                ref=r.return_ref,
                date=pd.Timestamp(r.date).strftime("%d-%m-%Y"),
                item=items.get(r.item_code, r.item_code),
                batch=r.batch_no,
                qty=int(r.qty),
                warehouse=r.warehouse,
                action=r.action,
            )
            for r in recall_rows.sort_values("date", ascending=False).head(15).itertuples()
        ],
        rows=[
            dict(
                ref=r.return_ref,
                date=pd.Timestamp(r.date).strftime("%d-%m-%Y"),
                rtype=r.rtype,
                client=names.get(r.client_code, r.client_code),
                item=items.get(r.item_code, r.item_code),
                batch=r.batch_no,
                qty=int(r.qty),
                reason=r.reason,
                action=r.action,
                warehouse=r.warehouse,
            )
            for r in ret.sort_values("date", ascending=False).head(25).itertuples()
        ],
    )


def temperature(warehouse: str = "All", days: int = 30) -> dict:
    """Cold chain and controlled area readings, and any excursion."""
    d = store.load()
    temp = _filter(d.get("temperature"), warehouse, days)
    if temp is None or temp.empty:
        return dict(tiles=[], trend=dict(labels=[], min_temp=[], max_temp=[]), by_warehouse=[], rows=[])

    excursions = temp[temp["excursion"] == "Y"]
    cold = temp[temp["zone"].astype(str).str.contains("Cold", case=False, na=False)]

    trend_src = cold if not cold.empty else temp
    g = trend_src.groupby("date", as_index=False)[["min_temp", "max_temp"]].agg({"min_temp": "min", "max_temp": "max"}).sort_values("date")

    byw = temp.groupby("warehouse").apply(
        lambda x: pd.Series({"readings": len(x), "excursions": int((x["excursion"] == "Y").sum())}),
        include_groups=False,
    ).reset_index()

    return dict(
        tiles=[
            dict(label="Readings logged", value=int(len(temp)), unit="nos"),
            dict(label="Excursions", value=int(len(excursions)), unit="nos"),
            dict(label="Compliance", value=_pct(len(temp) - len(excursions), len(temp)), unit="%"),
            dict(label="Cold chain sites", value=int(cold["warehouse"].nunique()), unit="nos"),
        ],
        trend=dict(
            labels=[pd.Timestamp(x).strftime("%d-%b") for x in g["date"]],
            min_temp=[round(float(v), 1) for v in g["min_temp"]],
            max_temp=[round(float(v), 1) for v in g["max_temp"]],
        ),
        by_warehouse=[dict(label=r.warehouse, excursions=int(r.excursions)) for r in byw.itertuples()],
        rows=[
            dict(
                date=pd.Timestamp(r.date).strftime("%d-%m-%Y"),
                warehouse=r.warehouse,
                zone=r.zone,
                slot=r.slot,
                min_temp=float(r.min_temp),
                max_temp=float(r.max_temp),
                action=r.action or "-",
            )
            for r in excursions.sort_values("date", ascending=False).head(20).itertuples()
        ],
    )


def fefo(warehouse: str = "All", days: int = 30) -> dict:
    """
    FEFO compliance: was the earliest expiring batch the one that went out.

    If the dispatch sheet carries a FEFO column it is used directly. Otherwise
    each dispatched batch is compared against the earliest expiry still held for
    that item at that warehouse, which is an indication rather than a proof.
    """
    d = store.load()
    dispatch = _filter(d["dispatch"], warehouse, days)
    if dispatch.empty:
        return dict(compliance=0.0, checked=0, breaches=0, method="", rows=[])

    items = d["items"].set_index("item_code")["item_name"].to_dict()

    if "fefo_ok" in dispatch.columns:
        method = "From the FEFO column in the dispatch sheet"
        bad = dispatch[dispatch["fefo_ok"] == "N"]
        checked = int(len(dispatch))
    else:
        method = "Compared against the earliest expiry still in stock"
        stock = _stock_now(warehouse)
        if stock.empty:
            return dict(compliance=0.0, checked=0, breaches=0, method=method, rows=[])
        earliest = (
            stock.groupby(["warehouse", "item_code"])["expiry_date"]
            .min().reset_index().rename(columns={"expiry_date": "earliest_expiry"})
        )
        merged = dispatch.merge(earliest, on=["warehouse", "item_code"], how="left")
        de = pd.to_datetime(merged["expiry_date"], errors="coerce")
        ee = pd.to_datetime(merged["earliest_expiry"], errors="coerce")
        bad = merged[(ee.notna()) & (de > ee)]
        checked = int(len(merged))

    return dict(
        compliance=_pct(checked - len(bad), checked),
        checked=checked,
        breaches=int(len(bad)),
        method=method,
        rows=[
            dict(
                date=pd.Timestamp(r.date).strftime("%d-%m-%Y"),
                item=items.get(r.item_code, r.item_code),
                batch=r.batch_no,
                expiry=pd.Timestamp(r.expiry_date).strftime("%d-%m-%Y") if pd.notna(r.expiry_date) else "-",
                qty=int(r.qty),
                warehouse=r.warehouse,
            )
            for r in bad.sort_values("date", ascending=False).head(20).itertuples()
        ],
    )


# ==================================================================== dispatch detail


def company_dispatch(warehouse: str = "All", days: int = 30, limit: int = 12) -> dict:
    """Volume handled for each pharma company whose stock we hold."""
    d = store.load()
    dispatch = _filter(d["dispatch"], warehouse, days)
    if dispatch.empty:
        return dict(labels=[], qty=[])
    company = d["items"].set_index("item_code")["company"].to_dict()
    g = dispatch.copy()
    g["company"] = g["item_code"].map(company)
    g = g.groupby("company", as_index=False)["qty"].sum().sort_values("qty", ascending=False).head(limit)
    return dict(labels=g["company"].tolist(), qty=[int(v) for v in g["qty"]])


def order_vs_dispatch(warehouse: str = "All", days: int = 30) -> dict:
    """Ordered against dispatched, day by day."""
    d = store.load()
    orders = _filter(d["orders"], warehouse, days, "order_date")
    if orders.empty:
        return dict(labels=[], ordered=[], dispatched=[])
    g = orders.groupby("order_date", as_index=False)[["order_qty", "dispatched_qty"]].sum().sort_values("order_date")
    return dict(
        labels=[pd.Timestamp(x).strftime("%d-%b") for x in g["order_date"]],
        ordered=[int(v) for v in g["order_qty"]],
        dispatched=[int(v) for v in g["dispatched_qty"]],
    )


def delivery_status(warehouse: str = "All", days: int = 30) -> dict:
    """Where every consignment of the period currently stands, plus the TAT spread."""
    d = store.load()
    dispatch = _filter(d["dispatch"], warehouse, days)
    if dispatch.empty:
        return dict(status=[], tat=[])

    today = dt.date.today()
    act = pd.to_datetime(dispatch["actual_delivery"], errors="coerce").dt.date
    exp = pd.to_datetime(dispatch["expected_delivery"], errors="coerce").dt.date
    disp = pd.to_datetime(dispatch["date"], errors="coerce").dt.date

    delivered = act.notna()
    late = delivered & (act > exp)
    overdue = (~delivered) & (exp < today)

    status = [
        dict(label="Delivered on time", count=int((delivered & ~late).sum())),
        dict(label="Delivered late", count=int(late.sum())),
        dict(label="In transit", count=int(((~delivered) & (~overdue)).sum())),
        dict(label="Overdue", count=int(overdue.sum())),
    ]

    tat_days = (act - disp).dropna().apply(lambda x: x.days)
    buckets = [(0, 1, "1 day"), (2, 2, "2 days"), (3, 3, "3 days"),
               (4, 5, "4-5 days"), (6, 99, "6 days and above")]
    tat = [dict(label=label, count=int(((tat_days >= lo) & (tat_days <= hi)).sum()))
           for lo, hi, label in buckets]
    return dict(status=status, tat=tat)


# ==================================================================== warehouse detail


def picking_status(warehouse: str = "All", days: int = 30) -> dict:
    """Orders received, picked, packed and dispatched, with what fell out at each step."""
    d = store.load()
    ops = _filter(d["wh_ops"], warehouse, days)
    if ops.empty:
        return dict(stages=[], labels=[], received=[], dispatched=[])
    received = int(ops["orders_received"].sum())
    picked = int(ops["orders_picked"].sum())
    packed = int(ops["orders_packed"].sum())
    dispatched = int(ops["orders_dispatched"].sum())
    stages = [
        dict(label="Received", count=received, pct=100.0),
        dict(label="Picked", count=picked, pct=_pct(picked, received)),
        dict(label="Packed", count=packed, pct=_pct(packed, received)),
        dict(label="Dispatched", count=dispatched, pct=_pct(dispatched, received)),
    ]
    g = ops.groupby("date", as_index=False)[["orders_received", "orders_dispatched"]].sum().sort_values("date")
    return dict(
        stages=stages,
        labels=[pd.Timestamp(x).strftime("%d-%b") for x in g["date"]],
        received=[int(v) for v in g["orders_received"]],
        dispatched=[int(v) for v in g["orders_dispatched"]],
    )


def pending_grn(warehouse: str = "All", days: int = 30, limit: int = 25) -> dict:
    """GRNs received but not yet posted in the system."""
    d = store.load()
    inward = _filter(d["inward"], warehouse, days)
    if inward.empty or "status" not in inward.columns:
        return dict(rows=[])
    pend = inward[inward["status"] != "Posted"].copy()
    if pend.empty:
        return dict(rows=[])
    pend["age"] = (dt.date.today() - pd.to_datetime(pend["date"], errors="coerce").dt.date).apply(
        lambda x: x.days if pd.notna(x) else 0
    )
    items = d["items"].set_index("item_code")["item_name"].to_dict()
    top = pend.sort_values("age", ascending=False).head(limit)
    return dict(rows=[
        dict(grn=r.grn_no, date=pd.Timestamp(r.date).strftime("%d-%m-%Y"), age=int(r.age),
             warehouse=r.warehouse, item=items.get(r.item_code, r.item_code),
             qty=int(r.qty), status=r.status)
        for r in top.itertuples()
    ])


def reconciliation(warehouse: str = "All", days: int = 30) -> dict:
    """Opening plus inward minus dispatch plus adjustment, against closing."""
    d = store.load()
    ops = _filter(d["wh_ops"], warehouse, days)
    if ops.empty:
        return dict(rows=[], totals={})
    rows = []
    for wh, g in ops.sort_values("date").groupby("warehouse"):
        opening = int(g["opening_stock"].iloc[0])
        inward = int(g["inward_qty"].sum())
        out = int(g["outward_qty"].sum())
        adj = int(g["adjustment_qty"].sum())
        closing = int(g["closing_stock"].iloc[-1])
        expected = opening + inward - out + adj
        rows.append(dict(
            warehouse=wh, opening=opening, inward=inward, dispatch=out,
            adjustment=adj, closing=closing, difference=closing - expected,
            counts=int(g["cycle_counts"].sum()), variance=int(g["count_variance"].sum()),
        ))
    rows.sort(key=lambda r: r["closing"], reverse=True)
    totals = dict(
        opening=sum(r["opening"] for r in rows),
        inward=sum(r["inward"] for r in rows),
        dispatch=sum(r["dispatch"] for r in rows),
        adjustment=sum(r["adjustment"] for r in rows),
        closing=sum(r["closing"] for r in rows),
        difference=sum(r["difference"] for r in rows),
        variance=sum(r["variance"] for r in rows),
    )
    return dict(rows=rows, totals=totals)


def batch_stock(warehouse: str = "All", limit: int = 40) -> dict:
    """Batch-wise closing stock, largest first."""
    d = store.load()
    stock = d["stock"]
    if warehouse != "All":
        stock = stock[stock["warehouse"] == warehouse]
    if stock.empty:
        return dict(rows=[])
    today = dt.date.today()
    names = d["items"].set_index("item_code")["item_name"].to_dict()
    company = d["items"].set_index("item_code")["company"].to_dict()
    s = stock.sort_values("closing_qty", ascending=False).head(limit)
    return dict(rows=[
        dict(
            item=names.get(r.item_code, r.item_code),
            company=company.get(r.item_code, "-"),
            batch=r.batch_no,
            expiry=pd.Timestamp(r.expiry_date).strftime("%d-%m-%Y"),
            days=(pd.Timestamp(r.expiry_date).date() - today).days,
            qty=int(r.closing_qty),
            blocked=int(r.blocked_qty),
            warehouse=r.warehouse,
        )
        for r in s.itertuples()
    ])


# ==================================================================== pharma compliance


def fefo(warehouse: str = "All", days: int = 30) -> dict:
    """How often the earliest expiring batch was the one picked."""
    d = store.load()
    dispatch = _filter(d["dispatch"], warehouse, days)
    if dispatch.empty:
        return dict(compliance=0.0, breaches=0, lines=0, trend=dict(labels=[], pct=[]))

    if "fefo_ok" in dispatch.columns:
        ok = dispatch["fefo_ok"] == "Y"
    else:
        # derive it: was an older batch of the same item still lying in stock?
        stock = d["stock"]
        earliest = stock.groupby("item_code")["expiry_date"].min().to_dict()
        picked = pd.to_datetime(dispatch["expiry_date"], errors="coerce").dt.date
        floor = dispatch["item_code"].map(earliest)
        ok = picked <= pd.to_datetime(floor, errors="coerce").dt.date

    g = dispatch.assign(_ok=ok.astype(int)).groupby("date", as_index=False)["_ok"].mean().sort_values("date")
    return dict(
        compliance=_pct(int(ok.sum()), len(dispatch)),
        breaches=int((~ok).sum()),
        lines=int(len(dispatch)),
        trend=dict(
            labels=[pd.Timestamp(x).strftime("%d-%b") for x in g["date"]],
            pct=[round(float(v) * 100, 1) for v in g["_ok"]],
        ),
    )


def returns(warehouse: str = "All", days: int = 30) -> dict:
    """Returns, damage, expiry write-offs and recalls."""
    d = store.load()
    if "returns" not in d or d["returns"].empty:
        return dict(tiles=[], by_type=[], by_reason=[], by_action=[], rows=[], recalls=[])
    r = _filter(d["returns"], warehouse, days)
    if r.empty:
        return dict(tiles=[], by_type=[], by_reason=[], by_action=[], rows=[], recalls=[])

    names = d["items"].set_index("item_code")["item_name"].to_dict()
    clients = d["clients"].set_index("client_code")["client_name"].to_dict()

    damaged = int(r.loc[r["type"].isin(["Damage", "Breakage"]), "qty"].sum())
    inward = _filter(d["inward"], warehouse, days)
    damaged += int(inward["damaged_qty"].sum()) if not inward.empty and "damaged_qty" in inward else 0
    non_saleable = int(r.loc[r["condition"] == "Non-saleable", "qty"].sum())

    tiles = [
        dict(label="Returned Units", value=int(r["qty"].sum())),
        dict(label="Damaged Units", value=damaged),
        dict(label="Non-saleable", value=non_saleable),
        dict(label="Recall Entries", value=int((r["type"] == "Recall").sum())),
    ]

    def counted(col):
        g = r.groupby(col, as_index=False)["qty"].sum().sort_values("qty", ascending=False)
        return [dict(label=str(row[0]), qty=int(row[1])) for row in g.itertuples(index=False)]

    rows = [
        dict(ref=x.return_ref, date=pd.Timestamp(x.date).strftime("%d-%m-%Y"), type=x.type,
             client=clients.get(x.client_code, x.client_code), warehouse=x.warehouse,
             item=names.get(x.item_code, x.item_code), batch=x.batch_no, qty=int(x.qty),
             reason=x.reason, condition=x.condition, action=x.action)
        for x in r.sort_values("date", ascending=False).head(25).itertuples()
    ]
    recalls = [row for row in rows if row["type"] == "Recall"]
    return dict(tiles=tiles, by_type=counted("type"), by_reason=counted("reason"),
                by_action=counted("action"), rows=rows, recalls=recalls)


def temperature(warehouse: str = "All", days: int = 30) -> dict:
    """Cold chain and controlled area readings, with any excursions."""
    d = store.load()
    if "temperature" not in d or d["temperature"].empty:
        return dict(tiles=[], zones=[], trend=dict(labels=[], series=[]), rows=[])
    t = _filter(d["temperature"], warehouse, days)
    if t.empty:
        return dict(tiles=[], zones=[], trend=dict(labels=[], series=[]), rows=[])

    breaches = t[t["excursion"] == "Y"]
    tiles = [
        dict(label="Readings Logged", value=int(len(t))),
        dict(label="Excursions", value=int(len(breaches))),
        dict(label="Compliance", value=_pct(int(len(t) - len(breaches)), len(t)), unit="%"),
        dict(label="Zones Monitored", value=int(t["zone"].nunique())),
    ]

    zones = []
    for zone, g in t.groupby("zone"):
        zb = g[g["excursion"] == "Y"]
        zones.append(dict(
            zone=zone,
            readings=int(len(g)),
            min_temp=round(float(g["min_temp"].min()), 1),
            max_temp=round(float(g["max_temp"].max()), 1),
            limit=f"{g['limit_low'].iloc[0]:.0f} to {g['limit_high'].iloc[0]:.0f} C",
            excursions=int(len(zb)),
            compliance=_pct(int(len(g) - len(zb)), len(g)),
        ))
    zones.sort(key=lambda z: z["excursions"], reverse=True)

    cold = t[t["zone"].str.contains("Cold", case=False, na=False)]
    source = cold if not cold.empty else t
    g = source.groupby("date", as_index=False)[["min_temp", "max_temp"]].agg({"min_temp": "min", "max_temp": "max"}).sort_values("date")
    trend = dict(
        labels=[pd.Timestamp(x).strftime("%d-%b") for x in g["date"]],
        min_temp=[round(float(v), 1) for v in g["min_temp"]],
        max_temp=[round(float(v), 1) for v in g["max_temp"]],
        limit_high=float(source["limit_high"].iloc[0]),
        limit_low=float(source["limit_low"].iloc[0]),
        zone=str(source["zone"].iloc[0]) if not cold.empty else "All zones",
    )

    rows = [
        dict(date=pd.Timestamp(x.date).strftime("%d-%m-%Y"), warehouse=x.warehouse, zone=x.zone,
             slot=x.slot, min_temp=float(x.min_temp), max_temp=float(x.max_temp), action=x.action)
        for x in breaches.sort_values("date", ascending=False).head(25).itertuples()
    ]
    return dict(tiles=tiles, zones=zones, trend=trend, rows=rows)
