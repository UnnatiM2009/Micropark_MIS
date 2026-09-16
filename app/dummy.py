"""
Dummy data generator.

The dashboard runs on this until real data is available. The seed is fixed, so
the same numbers come up every time and screenshots stay consistent.

When the real Excel arrives, drop it in data/MIS_Data.xlsx and this file is
ignored automatically (see store.py).
"""

import random
import datetime as dt

import pandas as pd

SEED = 20260916
DAYS = 90  # how much history to generate

# The eight pharma warehousing and C&F locations Micropark operates.
# Automobile dealership operations are deliberately out of scope here.
# capacity is pallet positions, scaled against the stated seven lakh sq ft.
WAREHOUSES = [
    ("Bhiwandi", "Maharashtra", 4200),
    ("Nagpur", "Maharashtra", 3000),
    ("Pune", "Maharashtra", 2200),
    ("Indore", "Madhya Pradesh", 1800),
    ("Lucknow", "Uttar Pradesh", 1600),
    ("Bangalore", "Karnataka", 1500),
    ("Zirakpur", "Punjab", 1400),
    ("Varanasi", "Uttar Pradesh", 1100),
]
WAREHOUSE_NAMES = [w[0] for w in WAREHOUSES]
CAPACITY = {w[0]: w[2] for w in WAREHOUSES}
# relative daily throughput, so Bhiwandi behaves like the biggest site
SCALE = {"Bhiwandi": 1.0, "Nagpur": 0.8, "Pune": 0.62, "Indore": 0.55,
         "Lucknow": 0.5, "Bangalore": 0.48, "Zirakpur": 0.42, "Varanasi": 0.34}

# principals whose stock is handled. Micropark handles over forty pharma companies.
COMPANIES = [
    "Sun Pharma", "Cipla", "Dr Reddys", "Mankind", "Alkem", "Zydus",
    "Torrent Pharma", "Lupin", "Glenmark", "Intas", "Abbott", "Emcure",
]

PRODUCTS = [
    ("Amoxicillin 500mg Cap", "Strip"),
    ("Azithromycin 500mg Tab", "Strip"),
    ("Paracetamol 650mg Tab", "Strip"),
    ("Pantoprazole 40mg Tab", "Strip"),
    ("Metformin 500mg Tab", "Strip"),
    ("Amlodipine 5mg Tab", "Strip"),
    ("Atorvastatin 10mg Tab", "Strip"),
    ("Cetirizine 10mg Tab", "Strip"),
    ("Ceftriaxone 1g Inj", "Vial"),
    ("Insulin Glargine 100IU", "Vial"),
    ("Human Mixtard 30/70", "Vial"),
    ("Ondansetron 4mg Inj", "Ampoule"),
    ("Diclofenac Gel 30g", "Tube"),
    ("Cough Syrup 100ml", "Bottle"),
    ("ORS Sachet", "Sachet"),
    ("Vitamin D3 60K", "Sachet"),
    ("Iron Folic Acid Tab", "Strip"),
    ("Calcium Carbonate Tab", "Strip"),
    ("Levocetirizine 5mg Tab", "Strip"),
    ("Montelukast 10mg Tab", "Strip"),
    ("Rabeprazole 20mg Tab", "Strip"),
    ("Clopidogrel 75mg Tab", "Strip"),
    ("Telmisartan 40mg Tab", "Strip"),
    ("Thyroxine 50mcg Tab", "Strip"),
    ("Hepatitis B Vaccine", "Vial"),
]

CLIENT_NAMES = [
    ("Shree Medical Agencies", "Nagpur", "Maharashtra"),
    ("Vidarbha Drug Agency", "Nagpur", "Maharashtra"),
    ("Sai Pharma Distributors", "Amravati", "Maharashtra"),
    ("Deshmukh Medical Stores", "Yavatmal", "Maharashtra"),
    ("Konark Pharma Traders", "Bhiwandi", "Maharashtra"),
    ("Thane Medico Distributors", "Thane", "Maharashtra"),
    ("Western Drug House", "Mumbai", "Maharashtra"),
    ("Ganesh Pharma Traders", "Pune", "Maharashtra"),
    ("City Care Hospital", "Pune", "Maharashtra"),
    ("New India Medicals", "Nashik", "Maharashtra"),
    ("Central Drug House", "Indore", "Madhya Pradesh"),
    ("Malwa Medical Agency", "Indore", "Madhya Pradesh"),
    ("Apex Medical Agency", "Bhopal", "Madhya Pradesh"),
    ("Narmada Pharma", "Jabalpur", "Madhya Pradesh"),
    ("Awadh Medical Stores", "Lucknow", "Uttar Pradesh"),
    ("Gomti Drug Distributors", "Lucknow", "Uttar Pradesh"),
    ("Kashi Pharma Agency", "Varanasi", "Uttar Pradesh"),
    ("Ganga Medicose", "Varanasi", "Uttar Pradesh"),
    ("Sangam Healthcare", "Prayagraj", "Uttar Pradesh"),
    ("Tricity Medical Agency", "Zirakpur", "Punjab"),
    ("Doaba Drug House", "Ludhiana", "Punjab"),
    ("Shivalik Pharma", "Chandigarh", "Chandigarh"),
    ("Deccan Medical Distributors", "Bangalore", "Karnataka"),
    ("Cauvery Pharma Agency", "Bangalore", "Karnataka"),
    ("Mysore Drug Traders", "Mysore", "Karnataka"),
    ("Life Care Hospital", "Nagpur", "Maharashtra"),
    ("Sunrise Distributors", "Raipur", "Chhattisgarh"),
    ("Krishna Medicals", "Wardha", "Maharashtra"),
    ("Balaji Drug House", "Chandrapur", "Maharashtra"),
    ("Omkar Pharma", "Akola", "Maharashtra"),
]

TRANSPORTERS = [
    ("TR-01", "Nagpur Roadlines", 3),
    ("TR-02", "Vidarbha Carriers", 2),
    ("TR-03", "Maharashtra Transport Co", 4),
    ("TR-04", "Speed Cargo Movers", 2),
    ("TR-05", "Central India Logistics", 5),
    ("TR-06", "North Star Carriers", 4),
    ("TR-07", "Deccan Express Cargo", 3),
]

COMPLAINT_CATEGORIES = [
    "Short Quantity",
    "Damage",
    "Delivery Delay",
    "Wrong Dispatch",
    "Batch Mismatch",
    "Expiry Related",
    "Returns Related",
    "Temperature Excursion",
]

RETURN_REASONS = [
    "Short expiry", "Damaged in transit", "Wrong supply", "Client cancelled",
    "Breakage at unloading", "Principal recall", "Excess supply",
]

ZONES = ["Ambient Zone A", "Ambient Zone B", "Cold Room 1"]

ROOT_CAUSES = ["Warehouse", "Transport", "Process", "System", "Client Side"]

RETURN_TYPES = ["Sales Return", "Damage", "Expiry", "Recall", "Breakage", "Wrong Supply"]

RETURN_REASONS = [
    "Short expiry at client end", "Damaged in transit", "Excess supply",
    "Ordered in error", "Batch recalled by principal", "Packing damaged",
    "Cold chain not maintained", "Wrong item supplied",
]

RETURN_ACTIONS = ["Restocked", "Quarantined", "Returned to Principal", "Destroyed", "Pending Decision"]

# warehouses holding cold chain product
COLD_CHAIN_SITES = ["Bhiwandi", "Nagpur", "Pune", "Bangalore"]

PENDING_REASONS = [
    "Stock not available",
    "Short expiry stock",
    "Payment hold",
    "Transport not available",
    "Documentation pending",
]


def build():
    """Return a dict of DataFrames that looks like a filled-in MIS template."""
    rnd = random.Random(SEED)
    today = dt.date.today()
    start = today - dt.timedelta(days=DAYS - 1)

    # ---------------------------------------------------------------- masters
    items = []
    for i, (name, uom) in enumerate(PRODUCTS):
        cold = "Insulin" in name or "Vaccine" in name or "Mixtard" in name
        items.append(
            dict(
                item_code=f"MP-{10200 + i}",
                item_name=name,
                company=COMPANIES[i % len(COMPANIES)],
                uom=uom,
                category="Cold Chain" if cold else "General",
            )
        )
    items = pd.DataFrame(items)

    # each client is served by the nearest location, falling back to Nagpur
    city_to_wh = {
        "Nagpur": "Nagpur", "Amravati": "Nagpur", "Yavatmal": "Nagpur",
        "Wardha": "Nagpur", "Chandrapur": "Nagpur", "Akola": "Nagpur",
        "Raipur": "Nagpur", "Bhiwandi": "Bhiwandi", "Thane": "Bhiwandi",
        "Mumbai": "Bhiwandi", "Pune": "Pune", "Nashik": "Pune",
        "Indore": "Indore", "Bhopal": "Indore", "Jabalpur": "Indore",
        "Lucknow": "Lucknow", "Prayagraj": "Lucknow", "Varanasi": "Varanasi",
        "Zirakpur": "Zirakpur", "Ludhiana": "Zirakpur", "Chandigarh": "Zirakpur",
        "Bangalore": "Bangalore", "Mysore": "Bangalore",
    }
    clients = pd.DataFrame(
        [
            dict(
                client_code=f"CL-{i + 1:03d}",
                client_name=n,
                city=c,
                state=st,
                warehouse=city_to_wh.get(c, "Nagpur"),
            )
            for i, (n, c, st) in enumerate(CLIENT_NAMES)
        ]
    )

    transporters = pd.DataFrame(
        [dict(transporter_code=c, transporter_name=n, committed_tat=t) for c, n, t in TRANSPORTERS]
    )

    item_codes = items["item_code"].tolist()
    client_codes = clients["client_code"].tolist()

    # ---------------------------------------------------------------- stock snapshot
    stock = []
    for wh in WAREHOUSE_NAMES:
        for code in item_codes:
            for b in range(rnd.randint(2, 4)):
                # a spread of expiry dates so the expiry report has something to show
                bucket = rnd.random()
                if bucket < 0.06:
                    days_to_expiry = rnd.randint(5, 30)
                elif bucket < 0.16:
                    days_to_expiry = rnd.randint(31, 90)
                elif bucket < 0.35:
                    days_to_expiry = rnd.randint(91, 180)
                else:
                    days_to_expiry = rnd.randint(181, 730)
                last_move = today - dt.timedelta(days=rnd.choice([0, 1, 2, 3, 5, 8, 14, 30, 60, 95, 140]))
                stock.append(
                    dict(
                        warehouse=wh,
                        item_code=code,
                        batch_no=f"B{rnd.randint(2300, 2609)}{rnd.randint(1, 9)}",
                        expiry_date=today + dt.timedelta(days=days_to_expiry),
                        closing_qty=rnd.randint(40, 2600),
                        blocked_qty=rnd.choice([0, 0, 0, 0, rnd.randint(5, 90)]),
                        last_movement_date=last_move,
                    )
                )
    stock = pd.DataFrame(stock)

    # ---------------------------------------------------------------- daily movement
    inward, dispatch, orders, wh_ops, complaints = [], [], [], [], []
    returns, temperature = [], []
    ret_seq = 0
    returns, temperature = [], []
    ret_seq = 0
    order_seq = 0
    cmp_seq = 0

    for d in range(DAYS):
        day = start + dt.timedelta(days=d)
        weekend = day.weekday() == 6  # Sunday, lighter operations
        factor = 0.35 if weekend else 1.0

        for wh in WAREHOUSE_NAMES:
            wh_scale = SCALE[wh]

            # ----- inward
            n_grn = max(1, int(rnd.randint(4, 11) * factor * wh_scale))
            grns_posted = 0
            for g in range(n_grn):
                posted = rnd.random() > 0.12
                grns_posted += 1 if posted else 0
                qty = rnd.randint(300, 1600)
                inward.append(
                    dict(
                        date=day,
                        warehouse=wh,
                        grn_no=f"GRN-{day.strftime('%d%m')}-{g + 1:03d}",
                        item_code=rnd.choice(item_codes),
                        qty=qty,
                        damaged_qty=rnd.choice([0] * 12 + [rnd.randint(1, 25)]),
                        status="Posted" if posted else "Pending",
                    )
                )

            # ----- orders and dispatch
            n_orders = max(1, int(rnd.randint(8, 22) * factor * wh_scale))
            day_out_qty = 0
            day_out_lines = 0
            for o in range(n_orders):
                order_seq += 1
                served = clients.loc[clients["warehouse"] == wh, "client_code"].tolist() or client_codes
                client = rnd.choice(served)
                item = rnd.choice(item_codes)
                order_qty = rnd.randint(50, 900)

                # an order older than about ten days would normally be closed
                recent = (today - day).days <= 10
                roll = rnd.random()
                if not recent:
                    status, disp_qty = ("Dispatched", order_qty) if roll < 0.985 else ("Cancelled", 0)
                elif roll < 0.86:
                    status, disp_qty = "Dispatched", order_qty
                elif roll < 0.93:
                    status, disp_qty = "Partial", int(order_qty * rnd.uniform(0.3, 0.8))
                elif roll < 0.99:
                    status, disp_qty = "Open", 0
                else:
                    status, disp_qty = "Cancelled", 0

                orders.append(
                    dict(
                        order_no=f"ORD-{order_seq:05d}",
                        order_date=day,
                        client_code=client,
                        warehouse=wh,
                        item_code=item,
                        order_qty=order_qty,
                        dispatched_qty=disp_qty,
                        status=status,
                        reason=rnd.choice(PENDING_REASONS) if status in ("Open", "Partial") else "",
                    )
                )

                if disp_qty > 0:
                    tr = rnd.choice(TRANSPORTERS)
                    committed = tr[2]
                    # most deliveries on time, some late
                    actual = committed + rnd.choice([0] * 40 + [1, 1, 2])
                    disp_date = day
                    delivered = disp_date + dt.timedelta(days=actual)
                    dispatch.append(
                        dict(
                            date=disp_date,
                            warehouse=wh,
                            client_code=client,
                            item_code=item,
                            qty=disp_qty,
                            transporter_code=tr[0],
                            expected_delivery=disp_date + dt.timedelta(days=committed),
                            actual_delivery=delivered if delivered <= today else None,
                            pod_received="Y" if delivered <= today - dt.timedelta(days=2) and rnd.random() > 0.08 else "N",
                            fefo_ok="Y" if rnd.random() > 0.035 else "N",
                        )
                    )
                    day_out_qty += disp_qty
                    day_out_lines += 1

            # ----- the picking funnel: each step can only lose orders, never gain
            picked_n = max(0, n_orders - rnd.choice([0, 0, 0, 0, 1, 1, 2]))
            packed_n = max(0, picked_n - rnd.choice([0, 0, 0, 0, 0, 1]))
            dispatched_n = max(0, packed_n - rnd.choice([0, 0, 0, 0, 0, 1]))

            # ----- warehouse operations for the day
            in_qty = sum(r["qty"] for r in inward if r["date"] == day and r["warehouse"] == wh)
            in_lines = sum(1 for r in inward if r["date"] == day and r["warehouse"] == wh)
            manpower = max(4, int(rnd.randint(9, 16) * wh_scale))
            manhours = manpower * (4 if weekend else 8)
            capacity = CAPACITY[wh]
            wh_ops.append(
                dict(
                    date=day,
                    warehouse=wh,
                    inward_qty=in_qty,
                    inward_lines=in_lines,
                    outward_qty=day_out_qty,
                    outward_lines=day_out_lines,
                    grns_received=n_grn,
                    grns_posted=grns_posted,
                    manpower=manpower,
                    manhours=manhours,
                    capacity_pallets=capacity,
                    occupied_pallets=int(capacity * rnd.uniform(0.62, 0.93)),
                    opening_stock=0,       # filled in below, once the day is known
                    adjustment_qty=rnd.choice([0] * 9 + [-rnd.randint(2, 40), rnd.randint(2, 40)]),
                    closing_stock=0,
                    orders_received=n_orders,
                    orders_picked=picked_n,
                    orders_packed=packed_n,
                    orders_dispatched=dispatched_n,
                    cycle_counts=rnd.randint(15, 60),
                    count_variance=rnd.choice([0] * 4 + [rnd.randint(1, 18)]),
                )
            )

            # ----- returns, damage and the occasional recall
            if rnd.random() < 0.22 * factor:
                ret_seq += 1
                rtype = rnd.choice(["Sales Return"] * 5 + ["Damage"] * 3 + ["Expiry"] * 2 + ["Breakage", "Recall"])
                saleable = rtype in ("Sales Return",) and rnd.random() > 0.4
                returns.append(
                    dict(
                        return_ref=f"RET-{ret_seq:04d}",
                        date=day,
                        type=rtype,
                        client_code=rnd.choice(client_codes),
                        warehouse=wh,
                        item_code=rnd.choice(item_codes),
                        batch_no=f"B{rnd.randint(2300, 2609)}{rnd.randint(1, 9)}",
                        qty=rnd.randint(5, 260),
                        reason=rnd.choice(RETURN_REASONS),
                        condition="Saleable" if saleable else "Non-saleable",
                        action="Restocked" if saleable else rnd.choice(
                            ["Quarantined", "Returned to Principal", "Destroyed", "Pending Decision"]),
                    )
                )

            # ----- temperature readings, two slots a day per zone
            zones_here = [z for z in ZONES if not z.startswith("Cold") or wh in COLD_CHAIN_SITES]
            for zone in zones_here:
                cold = zone.startswith("Cold")
                for slot in ("Morning", "Evening"):
                    if cold:
                        lo = round(rnd.uniform(2.3, 3.8), 1)
                        hi = round(lo + rnd.uniform(1.8, 3.6), 1)
                        limit_lo, limit_hi = 2.0, 8.0
                    else:
                        lo = round(rnd.uniform(18.5, 21.0), 1)
                        hi = round(lo + rnd.uniform(1.5, 3.0), 1)
                        limit_lo, limit_hi = 15.0, 25.0
                    if rnd.random() < 0.012:          # the occasional excursion
                        hi = round(limit_hi + rnd.uniform(0.4, 2.6), 1)
                    breach = hi > limit_hi or lo < limit_lo
                    temperature.append(
                        dict(
                            date=day,
                            warehouse=wh,
                            zone=zone,
                            slot=slot,
                            min_temp=lo,
                            max_temp=hi,
                            limit_low=limit_lo,
                            limit_high=limit_hi,
                            excursion="Y" if breach else "N",
                            action="Reported and stock quarantined" if breach else "Not applicable",
                        )
                    )

            # ----- complaints, a few a week
            if rnd.random() < 0.28 * factor:
                cmp_seq += 1
                closed = rnd.random() < 0.68
                closure_days = rnd.choice([1, 1, 2, 2, 3, 4, 6, 9])
                closure_date = day + dt.timedelta(days=closure_days)
                if closure_date > today:
                    closed = False
                complaints.append(
                    dict(
                        complaint_no=f"CMP-{cmp_seq:04d}",
                        date=day,
                        client_code=rnd.choice(client_codes),
                        warehouse=wh,
                        category=rnd.choice(COMPLAINT_CATEGORIES),
                        severity=rnd.choice(["Minor"] * 5 + ["Major"] * 3 + ["Critical"]),
                        status="Closed" if closed else "Open",
                        closure_date=closure_date if closed else None,
                        root_cause=rnd.choice(ROOT_CAUSES) if closed else "Not Established",
                    )
                )

    # ---------------------------------------------------------------- daily stock balance
    # Work the balance backwards from the stock actually on hand today, so the
    # reconciliation on the screen adds up instead of drifting.
    ops_df = pd.DataFrame(wh_ops).sort_values(["warehouse", "date"]).reset_index(drop=True)
    openings, closings = [], []
    for wh in WAREHOUSE_NAMES:
        rows = ops_df[ops_df["warehouse"] == wh]
        net = int((rows["inward_qty"] - rows["outward_qty"] + rows["adjustment_qty"]).sum())
        on_hand = int(stock.loc[stock["warehouse"] == wh, "closing_qty"].sum())
        running = on_hand - net
        for r in rows.itertuples():
            opening = running
            closing = opening + int(r.inward_qty) - int(r.outward_qty) + int(r.adjustment_qty)
            openings.append((r.Index, opening))
            closings.append((r.Index, closing))
            running = closing
    ops_df.loc[[i for i, _ in openings], "opening_stock"] = [v for _, v in openings]
    ops_df.loc[[i for i, _ in closings], "closing_stock"] = [v for _, v in closings]
    ops_df["opening_stock"] = ops_df["opening_stock"].astype(int)
    ops_df["closing_stock"] = ops_df["closing_stock"].astype(int)

    stock["date"] = today

    return dict(
        items=items,
        clients=clients,
        transporters=transporters,
        stock=stock,
        inward=pd.DataFrame(inward),
        dispatch=pd.DataFrame(dispatch),
        orders=pd.DataFrame(orders),
        wh_ops=ops_df,
        complaints=pd.DataFrame(complaints),
        returns=pd.DataFrame(returns),
        temperature=pd.DataFrame(temperature),
    )
