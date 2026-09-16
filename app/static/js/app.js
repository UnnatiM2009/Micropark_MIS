/* Micropark MIS dashboard - front end.
   Every figure comes from the /api endpoints. Nothing is calculated here
   except the threshold colouring, which decides when a number is shown in
   amber or red. */

const charts = {};
const state = { warehouse: "All", days: 30, tab: "overview", loaded: {} };

/* Where a figure stops being acceptable. Change these as targets are agreed. */
const THRESHOLDS = {
  fill_rate:       { good: 97, watch: 93, direction: "higher" },
  on_time:         { good: 95, watch: 90, direction: "higher" },
  space_util:      { good: 85, watch: 92, direction: "lower" },
  open_complaints: { good: 3,  watch: 8,  direction: "lower" },
  pending_grn:     { good: 3,  watch: 8,  direction: "lower" },
  pending_orders:  { good: 10, watch: 25, direction: "lower" },
  fefo:            { good: 99, watch: 97, direction: "higher" },
  temp_compliance: { good: 99.5, watch: 98, direction: "higher" },
  excursions:      { good: 0, watch: 3, direction: "lower" },
  non_saleable:    { good: 500, watch: 2000, direction: "lower" },
};

function css(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function fmt(v, unit) {
  if (unit === "%") return v.toFixed(1) + "%";
  if (typeof v === "number" && Math.abs(v) >= 1000) return v.toLocaleString("en-IN");
  return String(v);
}

function grade(key, value) {
  const t = THRESHOLDS[key];
  if (!t) return "";
  if (t.direction === "higher") {
    if (value >= t.good) return "good";
    if (value >= t.watch) return "watch";
    return "breach";
  }
  if (value <= t.good) return "good";
  if (value <= t.watch) return "watch";
  return "breach";
}

async function get(path) {
  const url = path + (path.includes("?") ? "&" : "?") +
    "warehouse=" + encodeURIComponent(state.warehouse) + "&days=" + state.days;
  const res = await fetch(url);
  if (!res.ok) throw new Error(path + " returned " + res.status);
  return res.json();
}

/* ---------------------------------------------------------------- charts */
function baseOptions(extra) {
  const grid = css("--rule-soft");
  const text = css("--ink-soft");
  return Object.assign({
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: false, labels: { color: text, boxWidth: 10, font: { size: 11 } } },
      tooltip: {
        backgroundColor: "rgba(16, 32, 60, 0.94)",
        titleColor: "#ffffff",
        bodyColor: "#e8edf5",
        titleFont: { size: 12 },
        bodyFont: { size: 12 },
        padding: 8,
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: text, font: { size: 10 }, maxRotation: 0, autoSkipPadding: 12 } },
      y: { grid: { color: grid }, border: { display: false }, ticks: { color: text, font: { size: 10 } } },
    },
  }, extra || {});
}

function draw(id, config) {
  const el = document.getElementById(id);
  if (!el) return;
  const box = el.parentElement;
  let msg = box.querySelector(".chart-empty");
  const noData = !config.data.labels || config.data.labels.length === 0;

  if (noData) {
    if (charts[id]) { charts[id].destroy(); delete charts[id]; }
    el.style.display = "none";
    if (!msg) {
      msg = document.createElement("div");
      msg.className = "chart-empty empty";
      msg.textContent = "Nothing to show for this selection.";
      box.appendChild(msg);
    }
    msg.style.display = "";
    return;
  }

  if (msg) msg.style.display = "none";
  el.style.display = "";
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(el, config);
}

/* ---------------------------------------------------------------- tables */
function table(el, columns, rows, emptyText) {
  if (!rows || rows.length === 0) {
    el.innerHTML = '<tbody><tr><td class="empty">' + (emptyText || "Nothing to show for this selection.") + "</td></tr></tbody>";
    return;
  }
  const head = "<thead><tr>" + columns.map(c =>
    '<th class="' + (c.num ? "num" : "") + '">' + c.label + "</th>").join("") + "</tr></thead>";
  const body = "<tbody>" + rows.map(r => "<tr>" + columns.map(c => {
    const raw = r[c.key];
    const cls = [c.num ? "num" : "", c.flag ? c.flag(r) : ""].filter(Boolean).join(" ");
    const val = c.render ? c.render(raw, r) : (typeof raw === "number" ? raw.toLocaleString("en-IN") : (raw ?? "-"));
    return '<td class="' + cls + '">' + val + "</td>";
  }).join("") + "</tr>").join("") + "</tbody>";
  el.innerHTML = head + body;
}

/* ---------------------------------------------------------------- tabs */
function showTab(name) {
  state.tab = name;
  document.querySelectorAll(".tab").forEach(b =>
    b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  ["overview", "inventory", "dispatch", "warehouse", "compliance", "complaints"].forEach(t =>
    document.getElementById("panel-" + t).classList.toggle("hidden", t !== name));
  loadTab(name);
}

/* ---------------------------------------------------------------- loaders */
async function loadHeader() {
  const meta = await fetch("/api/meta").then(r => r.json());
  const sel = document.getElementById("warehouse");
  if (!sel.options.length) {
    meta.warehouses.forEach(w => {
      const o = document.createElement("option");
      o.value = w;
      o.textContent = w === "All" ? "All warehouses" : w;
      sel.appendChild(o);
    });
  }
  const chip = document.getElementById("source-chip");
  chip.textContent = "Source: " + meta.source;
  chip.classList.toggle("demo", meta.source.indexOf("Dummy") === 0);
  document.getElementById("updated").textContent = "Data read at " + meta.loaded_at;
  document.getElementById("today").textContent = "As on " + meta.today;
}

async function loadKpis() {
  const d = await get("/api/summary");
  document.getElementById("kpis").innerHTML = d.tiles.map(t => {
    const g = grade(t.key, t.value);
    return '<div class="kpi ' + g + '">' +
      '<div class="label">' + t.label + "</div>" +
      '<div class="value">' + fmt(t.value, t.unit) +
      (t.unit && t.unit !== "%" ? '<span class="unit">' + t.unit + "</span>" : "") + "</div>" +
      '<div class="hint">' + t.hint + "</div></div>";
  }).join("");
}

async function loadOverview() {
  const [trend, wh, clients, prod] = await Promise.all([
    get("/api/trend"), get("/api/warehouses"), get("/api/clients"), get("/api/productivity"),
  ]);

  draw("ch-trend", {
    type: "line",
    data: {
      labels: trend.labels,
      datasets: [
        { label: "Inward", data: trend.inward, borderColor: css("--blue-soft"), backgroundColor: "transparent", borderWidth: 1.6, pointRadius: 0, tension: 0.25 },
        { label: "Dispatch", data: trend.outward, borderColor: css("--blue"), backgroundColor: "transparent", borderWidth: 2, pointRadius: 0, tension: 0.25 },
      ],
    },
    options: baseOptions({ plugins: { legend: { display: true, position: "bottom", labels: { color: css("--ink-soft"), boxWidth: 10, font: { size: 11 } } } } }),
  });

  draw("ch-wh", {
    type: "bar",
    data: {
      labels: wh.labels,
      datasets: [
        { label: "Inward", data: wh.inward, backgroundColor: css("--blue-soft"), borderRadius: 2 },
        { label: "Dispatch", data: wh.outward, backgroundColor: css("--blue"), borderRadius: 2 },
      ],
    },
    options: baseOptions({ plugins: { legend: { display: true, position: "bottom", labels: { color: css("--ink-soft"), boxWidth: 10, font: { size: 11 } } } } }),
  });

  draw("ch-clients", {
    type: "bar",
    data: { labels: clients.labels, datasets: [{ data: clients.qty, backgroundColor: css("--blue"), borderRadius: 2 }] },
    options: baseOptions({ indexAxis: "y", scales: {
      x: { grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
      y: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10.5 } } },
    } }),
  });

  draw("ch-prod", {
    type: "line",
    data: {
      labels: prod.labels,
      datasets: [
        { label: "Lines per man-hour", data: prod.lines_per_manhour, borderColor: css("--good"), borderWidth: 2, pointRadius: 0, tension: 0.25, yAxisID: "y" },
        { label: "Space used %", data: prod.space_util, borderColor: css("--watch"), borderWidth: 1.6, pointRadius: 0, tension: 0.25, borderDash: [4, 3], yAxisID: "y1" },
      ],
    },
    options: baseOptions({
      plugins: { legend: { display: true, position: "bottom", labels: { color: css("--ink-soft"), boxWidth: 10, font: { size: 11 } } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, maxRotation: 0, autoSkipPadding: 14 } },
        y: { position: "left", grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
        y1: { position: "right", min: 0, max: 100, grid: { display: false }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, callback: v => v + "%" } },
      },
    }),
  });
}

async function loadInventory() {
  const [expiry, ageing, stock] = await Promise.all([
    get("/api/expiry"), get("/api/ageing"), get("/api/stock-top"),
  ]);

  const expColours = [css("--breach"), css("--watch"), css("--watch"), css("--blue-soft"), css("--blue")];
  draw("ch-expiry", {
    type: "bar",
    data: {
      labels: expiry.buckets.map(b => b.label),
      datasets: [{ data: expiry.buckets.map(b => b.qty), backgroundColor: expColours, borderRadius: 2 }],
    },
    options: baseOptions(),
  });

  draw("ch-ageing", {
    type: "bar",
    data: {
      labels: ageing.buckets.map(b => b.label),
      datasets: [{ data: ageing.buckets.map(b => b.qty), backgroundColor: [css("--good"), css("--blue"), css("--blue-soft"), css("--watch"), css("--breach")], borderRadius: 2 }],
    },
    options: baseOptions(),
  });

  draw("ch-stock", {
    type: "bar",
    data: { labels: stock.labels, datasets: [{ data: stock.qty, backgroundColor: css("--blue"), borderRadius: 2 }] },
    options: baseOptions({ indexAxis: "y", scales: {
      x: { grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
      y: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10.5 } } },
    } }),
  });

  const [recon, batches] = await Promise.all([get("/api/reconciliation"), get("/api/batch-stock")]);

  const reconRows = (recon.rows || []).concat(
    recon.totals && (recon.rows || []).length
      ? [Object.assign({ warehouse: "Total" }, recon.totals, { counts: "" })]
      : []
  );
  table(document.getElementById("tbl-recon"), [
    { key: "warehouse", label: "Warehouse" },
    { key: "opening", label: "Opening", num: true },
    { key: "inward", label: "Inward", num: true },
    { key: "dispatch", label: "Dispatch", num: true },
    { key: "adjustment", label: "Adjustment", num: true },
    { key: "closing", label: "Closing", num: true },
    { key: "difference", label: "Difference", num: true, flag: r => r.difference === 0 ? "flag-good" : "flag-breach" },
    { key: "variance", label: "Count variance", num: true, flag: r => r.variance > 0 ? "flag-watch" : "" },
  ], reconRows);

  table(document.getElementById("tbl-batch"), [
    { key: "item", label: "Item" },
    { key: "company", label: "Company" },
    { key: "batch", label: "Batch" },
    { key: "expiry", label: "Expiry" },
    { key: "days", label: "Days left", num: true, flag: r => r.days <= 30 ? "flag-breach" : (r.days <= 90 ? "flag-watch" : "") },
    { key: "qty", label: "Qty", num: true },
    { key: "blocked", label: "Blocked", num: true, flag: r => r.blocked > 0 ? "flag-watch" : "" },
    { key: "warehouse", label: "Warehouse" },
  ], batches.rows);

  table(document.getElementById("tbl-expiry"), [
    { key: "item", label: "Item" },
    { key: "batch", label: "Batch" },
    { key: "expiry", label: "Expiry" },
    { key: "days", label: "Days left", num: true, flag: r => r.days <= 30 ? "flag-breach" : "flag-watch" },
    { key: "qty", label: "Qty", num: true },
    { key: "warehouse", label: "Warehouse" },
  ], expiry.rows, "No batch is expiring within 90 days.");
}

async function loadDispatch() {
  const [pending, transport, company, ovd, delivery] = await Promise.all([
    get("/api/pending-orders"), get("/api/transporters"), get("/api/company-dispatch"),
    get("/api/order-vs-dispatch"), get("/api/delivery-status"),
  ]);

  barH("ch-company", company.labels || [], company.qty || []);

  draw("ch-ovd", {
    type: "line",
    data: {
      labels: ovd.labels || [],
      datasets: [
        { label: "Ordered", data: ovd.ordered || [], borderColor: css("--blue-soft"), borderWidth: 1.6, pointRadius: 0, tension: 0.25 },
        { label: "Dispatched", data: ovd.dispatched || [], borderColor: css("--blue"), borderWidth: 2, pointRadius: 0, tension: 0.25 },
      ],
    },
    options: baseOptions({ plugins: { legend: { display: true, position: "bottom", labels: { color: css("--ink-soft"), boxWidth: 10, font: { size: 11 } } } } }),
  });

  barV("ch-delstatus", (delivery.status || []).map(x => x.label), (delivery.status || []).map(x => x.count),
       [css("--good"), css("--watch"), css("--blue"), css("--breach")]);
  barV("ch-tat", (delivery.tat || []).map(x => x.label), (delivery.tat || []).map(x => x.count));

  draw("ch-reasons", {
    type: "bar",
    data: {
      labels: pending.reasons.map(r => r.label),
      datasets: [{ data: pending.reasons.map(r => r.qty), backgroundColor: css("--blue"), borderRadius: 2 }],
    },
    options: baseOptions({ indexAxis: "y", scales: {
      x: { grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
      y: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10.5 } } },
    } }),
  });

  table(document.getElementById("tbl-transport"), [
    { key: "name", label: "Transporter" },
    { key: "consignments", label: "Consignments", num: true },
    { key: "committed_tat", label: "Committed", num: true, render: v => v + " d" },
    { key: "avg_tat", label: "Actual", num: true, render: v => v + " d" },
    { key: "on_time", label: "On time", num: true, render: v => v.toFixed(1) + "%", flag: r => r.on_time >= 95 ? "flag-good" : (r.on_time >= 90 ? "flag-watch" : "flag-breach") },
    { key: "pod", label: "POD received", num: true, render: v => v.toFixed(1) + "%" },
  ], transport.rows);

  table(document.getElementById("tbl-pending"), [
    { key: "order_no", label: "Order" },
    { key: "date", label: "Order date" },
    { key: "age", label: "Days old", num: true, flag: r => r.age > 7 ? "flag-breach" : (r.age > 3 ? "flag-watch" : "") },
    { key: "client", label: "Client" },
    { key: "item", label: "Item" },
    { key: "pending", label: "Pending qty", num: true },
    { key: "reason", label: "Reason" },
    { key: "warehouse", label: "Warehouse" },
  ], pending.rows, "No order is pending for this selection.");
}

async function loadComplaints() {
  const d = await get("/api/complaints");

  document.getElementById("cmp-tiles").innerHTML = d.tiles.map(t =>
    '<div class="kpi"><div class="label">' + t.label + "</div>" +
    '<div class="value">' + t.value + (t.unit ? '<span class="unit">' + t.unit + "</span>" : "") + "</div></div>"
  ).join("");

  draw("ch-cmp-cat", {
    type: "bar",
    data: { labels: d.by_category.map(x => x.label), datasets: [{ data: d.by_category.map(x => x.count), backgroundColor: css("--blue"), borderRadius: 2 }] },
    options: baseOptions({ indexAxis: "y", scales: {
      x: { grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, precision: 0 } },
      y: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
    } }),
  });

  draw("ch-cmp-cause", {
    type: "bar",
    data: { labels: d.by_cause.map(x => x.label), datasets: [{ data: d.by_cause.map(x => x.count), backgroundColor: css("--blue-soft"), borderRadius: 2 }] },
    options: baseOptions({ indexAxis: "y", scales: {
      x: { grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, precision: 0 } },
      y: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
    } }),
  });

  draw("ch-cmp-age", {
    type: "bar",
    data: { labels: d.ageing.map(x => x.label), datasets: [{ data: d.ageing.map(x => x.count), backgroundColor: [css("--good"), css("--watch"), css("--breach")], borderRadius: 2 }] },
    options: baseOptions({ scales: {
      x: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
      y: { grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, precision: 0 } },
    } }),
  });

  barH("ch-cmp-client", (d.by_client || []).map(x => x.label), (d.by_client || []).map(x => x.count));
  barH("ch-cmp-wh", (d.by_warehouse || []).map(x => x.label), (d.by_warehouse || []).map(x => x.count), css("--blue-soft"));

  table(document.getElementById("tbl-cmp"), [
    { key: "no", label: "Complaint" },
    { key: "date", label: "Date" },
    { key: "age", label: "Days open", num: true, flag: r => r.age > 7 ? "flag-breach" : (r.age > 2 ? "flag-watch" : "") },
    { key: "client", label: "Client" },
    { key: "category", label: "Category" },
    { key: "severity", label: "Severity", flag: r => r.severity === "Critical" ? "flag-breach" : "" },
    { key: "warehouse", label: "Warehouse" },
  ], d.rows, "No complaint is open for this selection.");
}


/* a horizontal bar chart, used wherever the labels are long */
function barH(id, labels, data, colour) {
  draw(id, {
    type: "bar",
    data: { labels: labels, datasets: [{ data: data, backgroundColor: colour || css("--blue"), borderRadius: 2 }] },
    options: baseOptions({ indexAxis: "y", scales: {
      x: { grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
      y: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
    } }),
  });
}

/* a plain vertical bar chart */
function barV(id, labels, data, colours) {
  draw(id, {
    type: "bar",
    data: { labels: labels, datasets: [{ data: data, backgroundColor: colours || css("--blue"), borderRadius: 2 }] },
    options: baseOptions(),
  });
}

function tiles(elId, list) {
  document.getElementById(elId).innerHTML = list.map(t => {
    const g = t.key ? grade(t.key, t.value) : "";
    return '<div class="kpi ' + g + '"><div class="label">' + t.label + "</div>" +
      '<div class="value">' + (t.unit === "%" ? t.value.toFixed(1) + "%" : t.value.toLocaleString("en-IN")) +
      (t.unit && t.unit !== "%" ? '<span class="unit">' + t.unit + "</span>" : "") + "</div>" +
      (t.hint ? '<div class="hint">' + t.hint + "</div>" : "") + "</div>";
  }).join("");
}

async function loadWarehouse() {
  const [pick, prod, grn] = await Promise.all([
    get("/api/picking-status"), get("/api/productivity"), get("/api/pending-grn"),
  ]);

  tiles("pick-tiles", (pick.stages || []).map(s => ({
    label: s.label, value: s.count, hint: s.pct + "% of orders received",
  })));

  barH("ch-picking", (pick.stages || []).map(s => s.label), (pick.stages || []).map(s => s.count));

  draw("ch-pickdaily", {
    type: "line",
    data: {
      labels: pick.labels || [],
      datasets: [
        { label: "Received", data: pick.received || [], borderColor: css("--blue-soft"), borderWidth: 1.6, pointRadius: 0, tension: 0.25 },
        { label: "Dispatched", data: pick.dispatched || [], borderColor: css("--blue"), borderWidth: 2, pointRadius: 0, tension: 0.25 },
      ],
    },
    options: baseOptions({ plugins: { legend: { display: true, position: "bottom", labels: { color: css("--ink-soft"), boxWidth: 10, font: { size: 11 } } } } }),
  });

  draw("ch-prod2", {
    type: "line",
    data: {
      labels: prod.labels || [],
      datasets: [
        { label: "Lines per man-hour", data: prod.lines_per_manhour || [], borderColor: css("--good"), borderWidth: 2, pointRadius: 0, tension: 0.25, yAxisID: "y" },
        { label: "Space used %", data: prod.space_util || [], borderColor: css("--watch"), borderWidth: 1.6, pointRadius: 0, tension: 0.25, borderDash: [4, 3], yAxisID: "y1" },
      ],
    },
    options: baseOptions({
      plugins: { legend: { display: true, position: "bottom", labels: { color: css("--ink-soft"), boxWidth: 10, font: { size: 11 } } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, maxRotation: 0, autoSkipPadding: 14 } },
        y: { position: "left", grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 } } },
        y1: { position: "right", min: 0, max: 100, grid: { display: false }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, callback: v => v + "%" } },
      },
    }),
  });

  table(document.getElementById("tbl-grn"), [
    { key: "grn", label: "GRN" },
    { key: "date", label: "Date" },
    { key: "age", label: "Days old", num: true, flag: r => r.age > 3 ? "flag-breach" : (r.age > 1 ? "flag-watch" : "") },
    { key: "item", label: "Item" },
    { key: "qty", label: "Qty", num: true },
    { key: "status", label: "Status" },
    { key: "warehouse", label: "Warehouse" },
  ], grn.rows, "Every GRN in this period is posted.");
}

async function loadCompliance() {
  const [fefo, ret, temp] = await Promise.all([
    get("/api/fefo"), get("/api/returns"), get("/api/temperature"),
  ]);

  const tempTile = (temp.tiles || []).find(t => t.label === "Compliance");
  const excTile = (temp.tiles || []).find(t => t.label === "Excursions");
  const nonSale = (ret.tiles || []).find(t => t.label === "Non-saleable");
  const damaged = (ret.tiles || []).find(t => t.label === "Damaged Units");
  const recalls = (ret.tiles || []).find(t => t.label === "Recall Entries");

  tiles("comp-tiles", [
    { label: "FEFO Compliance", value: fefo.compliance || 0, unit: "%", key: "fefo", hint: (fefo.breaches || 0) + " lines picked out of order" },
    { label: "Temperature Compliance", value: tempTile ? tempTile.value : 0, unit: "%", key: "temp_compliance", hint: "Readings within the permitted band" },
    { label: "Excursions", value: excTile ? excTile.value : 0, key: "excursions", hint: "Readings outside the band" },
    { label: "Damaged Units", value: damaged ? damaged.value : 0, hint: "At receipt and in returns" },
    { label: "Non-saleable", value: nonSale ? nonSale.value : 0, key: "non_saleable", hint: "Cannot be sold again" },
    { label: "Recall Entries", value: recalls ? recalls.value : 0, hint: "Batches recalled by the principal" },
  ]);

  draw("ch-fefo", {
    type: "line",
    data: {
      labels: (fefo.trend || {}).labels || [],
      datasets: [{ label: "FEFO %", data: (fefo.trend || {}).pct || [], borderColor: css("--good"), borderWidth: 2, pointRadius: 0, tension: 0.25 }],
    },
    options: baseOptions({ scales: {
      x: { grid: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, maxRotation: 0, autoSkipPadding: 14 } },
      y: { min: 80, max: 100, grid: { color: css("--rule-soft") }, border: { display: false }, ticks: { color: css("--ink-soft"), font: { size: 10 }, callback: v => v + "%" } },
    } }),
  });

  const tt = temp.trend || {};
  draw("ch-temp", {
    type: "line",
    data: {
      labels: tt.labels || [],
      datasets: [
        { label: "High", data: tt.max_temp || [], borderColor: css("--breach"), borderWidth: 1.8, pointRadius: 0, tension: 0.25 },
        { label: "Low", data: tt.min_temp || [], borderColor: css("--blue"), borderWidth: 1.8, pointRadius: 0, tension: 0.25 },
        { label: "Upper limit", data: (tt.labels || []).map(() => tt.limit_high), borderColor: css("--watch"), borderWidth: 1.2, borderDash: [5, 4], pointRadius: 0 },
        { label: "Lower limit", data: (tt.labels || []).map(() => tt.limit_low), borderColor: css("--watch"), borderWidth: 1.2, borderDash: [5, 4], pointRadius: 0 },
      ],
    },
    options: baseOptions({ plugins: { legend: { display: true, position: "bottom", labels: { color: css("--ink-soft"), boxWidth: 10, font: { size: 11 } } } } }),
  });

  barH("ch-rettype", (ret.by_type || []).map(x => x.label), (ret.by_type || []).map(x => x.qty));
  barH("ch-retreason", (ret.by_reason || []).map(x => x.label), (ret.by_reason || []).map(x => x.qty), css("--blue-soft"));
  barH("ch-retaction", (ret.by_action || []).map(x => x.label), (ret.by_action || []).map(x => x.qty), css("--watch"));

  table(document.getElementById("tbl-zones"), [
    { key: "zone", label: "Zone" },
    { key: "limit", label: "Permitted" },
    { key: "min_temp", label: "Lowest", num: true, render: v => v + " C" },
    { key: "max_temp", label: "Highest", num: true, render: v => v + " C" },
    { key: "readings", label: "Readings", num: true },
    { key: "excursions", label: "Excursions", num: true, flag: r => r.excursions > 0 ? "flag-breach" : "flag-good" },
    { key: "compliance", label: "Compliance", num: true, render: v => v.toFixed(1) + "%" },
  ], temp.zones);

  table(document.getElementById("tbl-excursion"), [
    { key: "date", label: "Date" },
    { key: "zone", label: "Zone" },
    { key: "slot", label: "Slot" },
    { key: "min_temp", label: "Low", num: true, render: v => v + " C" },
    { key: "max_temp", label: "High", num: true, render: v => v + " C", flag: () => "flag-breach" },
    { key: "warehouse", label: "Warehouse" },
  ], temp.rows, "No excursion recorded in this period.");

  table(document.getElementById("tbl-returns"), [
    { key: "ref", label: "Reference" },
    { key: "date", label: "Date" },
    { key: "type", label: "Type", flag: r => r.type === "Recall" ? "flag-breach" : "" },
    { key: "client", label: "Client" },
    { key: "item", label: "Item" },
    { key: "batch", label: "Batch" },
    { key: "qty", label: "Qty", num: true },
    { key: "reason", label: "Reason" },
    { key: "condition", label: "Condition", flag: r => r.condition === "Non-saleable" ? "flag-watch" : "" },
    { key: "action", label: "Action" },
  ], ret.rows, "Nothing returned in this period.");
}

const LOADERS = {
  overview: loadOverview,
  inventory: loadInventory,
  dispatch: loadDispatch,
  warehouse: loadWarehouse,
  compliance: loadCompliance,
  complaints: loadComplaints,
};

async function loadTab(name) {
  try {
    await LOADERS[name]();
  } catch (err) {
    console.error(err);
  }
}

async function reloadAll() {
  await loadKpis();
  await loadTab(state.tab);
}

/* ---------------------------------------------------------------- start */
document.querySelectorAll(".tab").forEach(b =>
  b.addEventListener("click", () => showTab(b.dataset.tab)));

document.getElementById("warehouse").addEventListener("change", e => {
  state.warehouse = e.target.value;
  reloadAll();
});

document.getElementById("period").addEventListener("change", e => {
  state.days = parseInt(e.target.value, 10);
  reloadAll();
});

document.getElementById("refresh").addEventListener("click", async () => {
  await fetch("/api/refresh", { method: "POST" });
  await loadHeader();
  await reloadAll();
});

(async function start() {
  await loadHeader();
  await reloadAll();
})();
