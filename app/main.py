"""
Micropark Logistics - MIS Dashboard
FastAPI application.

Run locally:
    uvicorn app.main:app --reload

The HTML page is served at /, and every figure on it comes from the /api
endpoints below.
"""

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Query, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import branding, kpis, store

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Micropark Logistics MIS Dashboard",
    description="Daily operations MIS for warehouse, inventory, dispatch and complaints",
    version="1.0.0",
)

# ---------------------------------------------------------------- optional login
# Set DASHBOARD_USER and DASHBOARD_PASS as environment variables to switch on a
# simple username and password. Leave them unset and the dashboard is open.
USER = os.getenv("DASHBOARD_USER")
PASS = os.getenv("DASHBOARD_PASS")
security = HTTPBasic(auto_error=False)


def guard(credentials: HTTPBasicCredentials = Depends(security)):
    if not USER or not PASS:
        return "open"
    if (
        credentials
        and secrets.compare_digest(credentials.username, USER)
        and secrets.compare_digest(credentials.password, PASS)
    ):
        return credentials.username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authorised",
        headers={"WWW-Authenticate": "Basic"},
    )


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def home(_=Depends(guard)):
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/logo", include_in_schema=False)
def logo():
    """Serves whichever logo file is in app/static/img/, without a restart."""
    path = branding.logo_path()
    return FileResponse(
        path,
        media_type=branding.logo_mime(path),
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Render pings this to check the service is alive."""
    return {"status": "ok"}


@app.get("/api/meta")
def api_meta(_=Depends(guard)):
    return kpis.meta()


@app.get("/api/summary")
def api_summary(warehouse: str = "All", days: int = Query(30, ge=1, le=365), _=Depends(guard)):
    return kpis.summary(warehouse, days)


@app.get("/api/trend")
def api_trend(warehouse: str = "All", days: int = Query(30, ge=1, le=365), _=Depends(guard)):
    return kpis.trend(warehouse, days)


@app.get("/api/productivity")
def api_productivity(warehouse: str = "All", days: int = Query(30, ge=1, le=365), _=Depends(guard)):
    return kpis.productivity(warehouse, days)


@app.get("/api/expiry")
def api_expiry(warehouse: str = "All", _=Depends(guard)):
    return kpis.expiry(warehouse)


@app.get("/api/ageing")
def api_ageing(warehouse: str = "All", _=Depends(guard)):
    return kpis.ageing(warehouse)


@app.get("/api/stock-top")
def api_stock_top(warehouse: str = "All", _=Depends(guard)):
    return kpis.stock_top(warehouse)


@app.get("/api/clients")
def api_clients(warehouse: str = "All", days: int = Query(30, ge=1, le=365), _=Depends(guard)):
    return kpis.clients(warehouse, days)


@app.get("/api/warehouses")
def api_warehouses(days: int = Query(30, ge=1, le=365), _=Depends(guard)):
    return kpis.warehouses(days)


@app.get("/api/pending-orders")
def api_pending_orders(warehouse: str = "All", days: int = Query(30, ge=1, le=365), _=Depends(guard)):
    return kpis.pending_orders(warehouse, days)


@app.get("/api/transporters")
def api_transporters(warehouse: str = "All", days: int = Query(30, ge=1, le=365), _=Depends(guard)):
    return kpis.transporters(warehouse, days)


@app.get("/api/complaints")
def api_complaints(warehouse: str = "All", days: int = Query(30, ge=1, le=365), _=Depends(guard)):
    return kpis.complaints(warehouse, days)


@app.post("/api/refresh")
def api_refresh(_=Depends(guard)):
    """Re-read the Excel file without restarting the server."""
    store.load(force=True)
    return {"status": "reloaded", "source": store.source(), "loaded_at": store.loaded_at()}
