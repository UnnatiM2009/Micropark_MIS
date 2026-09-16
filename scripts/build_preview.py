"""
Build a single HTML file that contains the dashboard and its data.

Useful when you want to send the dashboard to someone before it is deployed,
or show it on a phone with no server running. Everything is baked in: the
figures for every warehouse and period combination are calculated once and
written into the page.

    python scripts/build_preview.py

Output: preview/dashboard_preview.html
"""

import base64
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app import branding, kpis, store  # noqa: E402

PERIODS = [7, 30, 90]

ENDPOINTS = {
    "/api/summary": lambda w, d: kpis.summary(w, d),
    "/api/trend": lambda w, d: kpis.trend(w, d),
    "/api/productivity": lambda w, d: kpis.productivity(w, d),
    "/api/expiry": lambda w, d: kpis.expiry(w),
    "/api/ageing": lambda w, d: kpis.ageing(w),
    "/api/stock-top": lambda w, d: kpis.stock_top(w),
    "/api/clients": lambda w, d: kpis.clients(w, d),
    "/api/warehouses": lambda w, d: kpis.warehouses(d),
    "/api/pending-orders": lambda w, d: kpis.pending_orders(w, d),
    "/api/transporters": lambda w, d: kpis.transporters(w, d),
    "/api/complaints": lambda w, d: kpis.complaints(w, d),
    "/api/company-dispatch": lambda w, d: kpis.company_dispatch(w, d),
    "/api/order-vs-dispatch": lambda w, d: kpis.order_vs_dispatch(w, d),
    "/api/delivery-status": lambda w, d: kpis.delivery_status(w, d),
    "/api/picking-status": lambda w, d: kpis.picking_status(w, d),
    "/api/pending-grn": lambda w, d: kpis.pending_grn(w, d),
    "/api/reconciliation": lambda w, d: kpis.reconciliation(w, d),
    "/api/batch-stock": lambda w, d: kpis.batch_stock(w),
    "/api/fefo": lambda w, d: kpis.fefo(w, d),
    "/api/returns": lambda w, d: kpis.returns(w, d),
    "/api/temperature": lambda w, d: kpis.temperature(w, d),
}


def build():
    meta = kpis.meta()
    payloads = {}
    for wh in meta["warehouses"]:
        for days in PERIODS:
            bag = {}
            for path, fn in ENDPOINTS.items():
                bag[path] = fn(wh, days)
            payloads[f"{wh}|{days}"] = bag

    data = {"meta": meta, "payloads": payloads}

    html = (BASE / "app" / "templates" / "index.html").read_text()
    css = (BASE / "app" / "static" / "css" / "styles.css").read_text()
    js = (BASE / "app" / "static" / "js" / "app.js").read_text()

    # --- swap the network calls for lookups in the baked-in data
    old_get = '''async function get(path) {
  const url = path + (path.includes("?") ? "&" : "?") +
    "warehouse=" + encodeURIComponent(state.warehouse) + "&days=" + state.days;
  const res = await fetch(url);
  if (!res.ok) throw new Error(path + " returned " + res.status);
  return res.json();
}'''
    new_get = '''async function get(path) {
  const bag = window.__DATA__.payloads[state.warehouse + "|" + state.days] || {};
  return bag[path] || {};
}'''
    assert old_get in js, "get() not found - app.js changed"
    js = js.replace(old_get, new_get)

    old_meta = '  const meta = await fetch("/api/meta").then(r => r.json());'
    new_meta = '  const meta = window.__DATA__.meta;'
    assert old_meta in js
    js = js.replace(old_meta, new_meta)

    old_refresh = '  await fetch("/api/refresh", { method: "POST" });\n'
    assert old_refresh in js
    js = js.replace(old_refresh, '')

    # --- inline whichever logo is installed, since a standalone file cannot fetch /logo
    logo_file = branding.logo_path()
    logo_uri = ("data:" + branding.logo_mime(logo_file) + ";base64,"
                + base64.b64encode(logo_file.read_bytes()).decode())
    html = html.replace('src="/logo"', 'src="' + logo_uri + '"')
    print(f"logo: {logo_file.name}" + ("  (drawn fallback)" if branding.using_fallback() else ""))

    # --- inline the assets
    html = html.replace('<link rel="stylesheet" href="/static/css/styles.css">',
                        "<style>\n" + css + "\n</style>")
    chart_js = (BASE / "app" / "static" / "vendor" / "chart.umd.js").read_text()
    html = html.replace('<script src="/static/vendor/chart.umd.js"></script>',
                        "<script>\n" + chart_js + "\n</script>")

    html = html.replace('<script src="/static/js/app.js"></script>',
                        "<script>\nwindow.__DATA__ = " + json.dumps(data, default=str) +
                        ";\n</script>\n<script>\n" + js + "\n</script>")

    out_dir = BASE / "preview"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "dashboard_preview.html"
    out.write_text(html)
    size = out.stat().st_size / 1024
    print(f"written: {out}  ({size:.0f} KB, source: {store.source()})")


if __name__ == "__main__":
    build()
