"""
Where the data comes from.

Order of preference:
  1. data/MIS_Data.xlsx   - the filled-in MIS template
  2. dummy data           - generated in memory, used for the demo

So the dashboard always has something to show, and switching to real data is
only a matter of placing the file. Nothing in the rest of the code changes.
"""

import os
import datetime as dt
from pathlib import Path

import pandas as pd

from . import dummy

BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = Path(os.getenv("MIS_EXCEL_PATH", BASE_DIR / "data" / "MIS_Data.xlsx"))

# sheet name in the template -> internal table name
SHEET_MAP = {
    "1 Item Master": "items",
    "2 Client Master": "clients",
    "3 Transporter Master": "transporters",
    "5 Inward GRN": "inward",
    "6 Dispatch": "dispatch",
    "7 Orders": "orders",
    "8 Daily Stock": "stock",
    "9 Warehouse Ops": "wh_ops",
    "11 Complaints": "complaints",
}

# template heading -> internal column name
COLUMN_MAP = {
    "Item Code": "item_code",
    "Item Name": "item_name",
    "Company / Principal": "company",
    "UOM": "uom",
    "Category": "category",
    "Client Code": "client_code",
    "Client Name": "client_name",
    "City": "city",
    "State": "state",
    "Warehouse Served": "warehouse",
    "Warehouse": "warehouse",
    "Transporter Code": "transporter_code",
    "Transporter Name": "transporter_name",
    "Committed TAT (Days)": "committed_tat",
    "GRN No": "grn_no",
    "GRN Date": "date",
    "Received Qty": "qty",
    "Damaged Qty": "damaged_qty",
    "GRN Status": "status",
    "Dispatch Date": "date",
    "Dispatch Qty": "qty",
    "Expected Delivery Date": "expected_delivery",
    "Actual Delivery Date": "actual_delivery",
    "POD Received (Y/N)": "pod_received",
    "Order No": "order_no",
    "Order Date": "order_date",
    "Order Qty": "order_qty",
    "Dispatched Qty": "dispatched_qty",
    "Order Status": "status",
    "Reason for Pending": "reason",
    "Date": "date",
    "Stock Date": "date",
    "Batch No": "batch_no",
    "Expiry Date": "expiry_date",
    "Closing Qty": "closing_qty",
    "Blocked / Quarantine Qty": "blocked_qty",
    "Last Movement Date": "last_movement_date",
    "Inward Qty": "inward_qty",
    "Inward Lines": "inward_lines",
    "Outward Qty": "outward_qty",
    "Outward Lines": "outward_lines",
    "GRNs Received": "grns_received",
    "GRNs Posted": "grns_posted",
    "Manpower Deployed": "manpower",
    "Man-hours Worked": "manhours",
    "Storage Capacity (Pallets)": "capacity_pallets",
    "Occupied (Pallets)": "occupied_pallets",
    "Complaint No": "complaint_no",
    "Complaint Date": "date",
    "Severity": "severity",
    "Status": "status",
    "Closure Date": "closure_date",
    "Root Cause": "root_cause",
}

DATE_COLS = [
    "date",
    "order_date",
    "expiry_date",
    "last_movement_date",
    "expected_delivery",
    "actual_delivery",
    "closure_date",
]

_cache = {"data": None, "source": None, "loaded_at": None}


def _from_excel(path: Path) -> dict:
    tables = {}
    book = pd.read_excel(path, sheet_name=None)
    for sheet, df in book.items():
        key = SHEET_MAP.get(sheet.strip())
        if not key:
            continue
        df = df.rename(columns={c: COLUMN_MAP.get(str(c).strip(), str(c).strip()) for c in df.columns})
        # the template ships with one italic example row; drop rows with no key value
        df = df.dropna(how="all")
        for col in DATE_COLS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True).dt.date
        tables[key] = df.reset_index(drop=True)
    return tables


def load(force: bool = False) -> dict:
    """Return the tables, from cache unless force=True."""
    if _cache["data"] is not None and not force:
        return _cache["data"]

    if EXCEL_PATH.exists():
        try:
            data = _from_excel(EXCEL_PATH)
            # the blank template carries one example row; treat that as "not filled yet"
            thin = [k for k in ("dispatch", "orders", "stock") if k not in data or len(data[k]) < 5]
            if thin:
                raise ValueError(f"not enough rows yet in: {thin}")
            _cache.update(data=data, source=f"Excel ({EXCEL_PATH.name})", loaded_at=dt.datetime.now())
            return data
        except Exception as exc:  # fall back rather than crash the dashboard
            print(f"[store] could not read {EXCEL_PATH}: {exc}. Using dummy data.")

    data = dummy.build()
    _cache.update(data=data, source="Dummy data (demo)", loaded_at=dt.datetime.now())
    return data


def source() -> str:
    if _cache["source"] is None:
        load()
    return _cache["source"]


def loaded_at() -> str:
    if _cache["loaded_at"] is None:
        load()
    return _cache["loaded_at"].strftime("%d-%m-%Y %H:%M")
