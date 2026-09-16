# Micropark Logistics — Pharma Operations MIS Dashboard

A daily operations dashboard for the pharma warehousing, distribution and C&F
business of **Micropark Logistics Private Limited**, Nagpur.

Built with **Python, FastAPI, HTML, CSS and JavaScript**. It opens in a normal
browser on a laptop or a mobile phone. There is nothing to install on the device.

It runs on generated dummy data out of the box, so it can be deployed and shown
before any real data is available.

## Scope

Pharma handling only: distribution, warehousing and carrying and forwarding
agency work for the pharma companies whose stock Micropark holds. The automobile
dealership business is **not** covered here and is reported separately.

Eight locations are set up in the dashboard, matching the warehouse network:

| Location | State | Pallet positions |
|---|---|---|
| Bhiwandi | Maharashtra | 4,200 |
| Nagpur | Maharashtra | 3,000 |
| Pune | Maharashtra | 2,200 |
| Indore | Madhya Pradesh | 1,800 |
| Lucknow | Uttar Pradesh | 1,600 |
| Bangalore | Karnataka | 1,500 |
| Zirakpur | Punjab | 1,400 |
| Varanasi | Uttar Pradesh | 1,100 |

The pallet figures are an assumption drawn from the stated seven lakh square feet
of warehousing space, and should be replaced with the actual racking capacity of
each site. They sit in `WAREHOUSES` in `app/dummy.py`, and come from the
**Storage Capacity (Pallets)** column once real data is loaded.

## Logo

Drag your logo file onto **`add_logo.bat`**. That is the whole process. Then
reload the dashboard in the browser, no restart needed.

By hand instead: save the file into `app/static/img/` as `logo.png`. Other
formats work too (`.svg`, `.jpg`, `.webp`, `.gif`), and the server picks up
whichever is there.

Until a logo is added, the header shows `logo-fallback.svg`, a drawn stand-in,
so nothing ever appears broken. A PNG with a transparent background, roughly
400 to 600 px wide, gives the best result. See `app/static/img/README.md`.

## What it shows

| Tab | Contents |
|---|---|
| **Overview** | Ten headline figures, daily inward against dispatch, warehouse-wise volume, top clients, productivity and space utilisation |
| **Inventory** | Stock by time left to expiry, stock ageing, highest stock items, and a table of batches expiring within 90 days |
| **Dispatch** | Reasons orders are held up, transporter performance, and the full pending order list |
| **Complaints** | Open and closed position, category and root cause split, ageing of open complaints |

Filters for warehouse and period (7, 30 or 90 days) apply across every screen.

Figures turn **amber or red** when they cross the limits set in
`app/static/js/app.js` (see `THRESHOLDS`), so exceptions stand out without
anyone having to read every number.

---

## Showing the demo on a laptop

**Windows:** double-click **`start_dashboard.bat`**.

**Mac or Linux:** run **`./start_dashboard.sh`**.

The first run takes a couple of minutes while it sets itself up. After that it
starts in a few seconds. It then opens the dashboard in your browser on its own.

A black window stays open behind the browser. Leave it there while you present.
Closing it, or pressing Ctrl+C in it, stops the dashboard.

That window also prints a second address, something like `http://192.168.1.14:8000`.
Anyone on the same wi-fi can open that on their phone, so you can hand the phone
to the MD and let him scroll through it himself.

If the port is busy the launcher moves to the next free one, so a second copy
running in the background will not stop the demo.

### If there is no internet in the room

Everything the dashboard needs is inside the project, so it runs on a laptop
with no connection at all. Charts are drawn by a copy of Chart.js kept in
`app/static/vendor/`, not fetched from the internet. Only the web font comes
from outside, and the page falls back to a normal system font without it.

There is also `preview/dashboard_preview.html`, a single self-contained file.
Double-click it and the whole dashboard opens in the browser with no Python and
no server running. Useful as a backup during a presentation, or to email to
someone. It is a snapshot, so the Refresh button does nothing there.

## If the launcher reports a problem

The launcher prints the reason and stops, rather than closing on you. The common
ones:

**"No module named uvicorn"** — the packages did not install. Open a command
window in this folder and run:

```
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python run_demo.py
```

If there is no `venv` folder, delete it if it exists and run the launcher again;
it rebuilds the environment from scratch.

**"Python is not installed"** — install Python 3.11 or later from
python.org, and tick **Add python.exe to PATH** on the first installer screen.

**Packages fail to install** — the first run needs internet. Behind an office
firewall or proxy, pip is usually what gets blocked. Try:

```
venv\Scripts\python -m pip install -r requirements.txt --proxy http://user:pass@proxyserver:port
```

**In every one of these cases**, the demo itself is not lost. Double-click
`preview/dashboard_preview.html` and the whole dashboard opens in the browser
with no Python, no server and no internet.

## Running it on your own machine

```bash
git clone https://github.com/<your-username>/micropark-mis-dashboard.git
cd micropark-mis-dashboard

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac or Linux

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>.

To let others in the office see it from their own machines, start it with
`uvicorn app.main:app --host 0.0.0.0 --port 8000` and give them
`http://<your-ip>:8000`.

---

## Putting it on GitHub

```bash
git init
git add .
git commit -m "MIS dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/micropark-mis-dashboard.git
git push -u origin main
```

Real data is never committed. `.gitignore` already excludes `data/*.xlsx`.

---

## Deploying on Render

1. Push the repository to GitHub as above.
2. On [render.com](https://render.com), choose **New → Web Service** and connect
   the repository.
3. Render reads `render.yaml` and fills everything in. If you are setting it up
   by hand instead, use:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health check path:** `/healthz`
4. Deploy. You get a link like `https://micropark-mis-dashboard.onrender.com`
   that works on any phone or laptop.

**Note on the free plan:** the service sleeps after about 15 minutes of no use,
and the next visitor waits roughly 30 seconds for it to wake. For daily use by
management, the paid starter plan avoids this.

---

## Switching from dummy data to real data

Place the filled-in MIS template at `data/MIS_Data.xlsx`. On the next start, or
when someone presses **Refresh**, every figure comes from that file instead.

The sheet names and column headings must match the MIS Data Input Template. The
mapping lives in `app/store.py` — if a heading in your file differs, add it to
`COLUMN_MAP` rather than renaming the column in the file.

If the file is missing, unreadable, or barely filled in, the dashboard falls
back to dummy data and says so in the grey bar at the top. It does not crash.

You can point it somewhere else with an environment variable:

```bash
MIS_EXCEL_PATH=/path/to/MIS_Data.xlsx uvicorn app.main:app
```

---

## Adding a username and password

Set two environment variables and a login box appears:

```
DASHBOARD_USER=micropark
DASHBOARD_PASS=<something long>
```

On Render, add these under **Environment**. Leave them unset and the dashboard
is open to anyone with the link. This is basic protection, suitable for an
internal tool. For proper user accounts with roles, that is a later step.

---

## Project structure

```
app/
  main.py        FastAPI routes. Serves the page and the /api endpoints.
  store.py       Decides where data comes from: Excel if present, else dummy.
  kpis.py        Every calculation. Pandas in, plain numbers out.
  dummy.py       Generates the demo data. Fixed seed, so figures stay the same.
  templates/
    index.html   The single page.
  static/
    css/styles.css
    js/app.js    Fetches the API and draws the charts and tables.
    vendor/      Chart.js, kept locally so the dashboard works offline.
    img/         Your logo goes here. See the README in that folder.
data/
  MIS_Data.xlsx  Your filled template goes here. Not committed.
scripts/
  build_preview.py  Builds a single-file offline copy of the dashboard.
  add_logo.py       Installs a logo file into the project.
run_demo.py      Starts the server and opens the browser. Used by the launchers.
start_dashboard.bat   Double-click launcher for Windows.
start_dashboard.sh    Launcher for Mac and Linux.
add_logo.bat          Drag a logo file onto this to install it.
render.yaml      Render deployment settings.
```

The calculations sit in `kpis.py`, away from the web layer, so a report can be
corrected without touching the page, and the same functions can later feed a
scheduled email or an Excel export.

---

## API

Every endpoint accepts `warehouse` and `days`.

| Endpoint | Returns |
|---|---|
| `GET /api/meta` | Warehouse list, data source, last read time |
| `GET /api/summary` | The ten headline figures |
| `GET /api/trend` | Daily inward and outward quantity |
| `GET /api/productivity` | Lines per man-hour and space utilisation by day |
| `GET /api/expiry` | Expiry buckets and the batches needing action |
| `GET /api/ageing` | Stock by days since last movement |
| `GET /api/stock-top` | Items holding the most stock |
| `GET /api/clients` | Dispatch quantity by client |
| `GET /api/warehouses` | Inward and outward by warehouse |
| `GET /api/pending-orders` | Pending orders and the reasons |
| `GET /api/transporters` | Delivery reliability by transporter |
| `GET /api/complaints` | Complaint position, categories, causes, ageing |
| `POST /api/refresh` | Re-read the Excel file without restarting |

Interactive API documentation is at `/docs`.

---

## Next steps

- Move the data into PostgreSQL so month-on-month trends survive a file being
  replaced. Render offers a managed PostgreSQL instance.
- A scheduled job that reads the Excel from a shared folder every 30 minutes,
  instead of pressing Refresh.
- Proper user accounts, so a warehouse in-charge sees only his own location.
- Excel and PDF export of any screen.
- A daily summary email at 9 am to management.
