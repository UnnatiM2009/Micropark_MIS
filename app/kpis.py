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

    stock = d["stock"]
    if warehouse != "All":
        stock = stock[stock["warehouse"] == warehouse]

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
    stock = d["stock"]
    if warehouse != "All":
        stock = stock[stock["warehouse"] == warehouse]
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
    stock = d["stock"]
    if warehouse != "All":
        stock = stock[stock["warehouse"] == warehouse]
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
        return dict(tiles=[], by_category=[], by_cause=[], ageing=[], rows=[])

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

    return dict(
        tiles=[
            dict(label="Total Complaints", value=total),
            dict(label="Closed", value=closed),
            dict(label="Open", value=open_),
            dict(label="Avg Closure TAT", value=avg_tat, unit="days"),
        ],
        by_category=[dict(label=r.category, count=int(r.size)) for r in cat.itertuples()],
        by_cause=[dict(label=r.root_cause, count=int(r.size)) for r in cause.itertuples()],
        ageing=ageing_rows,
        rows=rows,
    )


def stock_top(warehouse: str = "All", limit: int = 12) -> dict:
    d = store.load()
    stock = d["stock"]
    if warehouse != "All":
        stock = stock[stock["warehouse"] == warehouse]
    if stock.empty:
        return dict(labels=[], qty=[])
    names = d["items"].set_index("item_code")["item_name"].to_dict()
    g = stock.groupby("item_code", as_index=False)["closing_qty"].sum().sort_values("closing_qty", ascending=False).head(limit)
    return dict(
        labels=[names.get(c, c) for c in g["item_code"]],
        qty=[int(v) for v in g["closing_qty"]],
    )
