/* TradingView charts grid — live charts of all pairs */

// Default watchlist — major pairs, gold, crypto, indices
const DEFAULT_SYMBOLS = [
  { tv: "FX:EURUSD",        label: "EUR/USD" },
  { tv: "FX:GBPUSD",        label: "GBP/USD" },
  { tv: "FX:USDJPY",        label: "USD/JPY" },
  { tv: "OANDA:XAUUSD",     label: "GOLD" },
  { tv: "BINANCE:BTCUSDT",  label: "BTC/USDT" },
  { tv: "FX:AUDUSD",        label: "AUD/USD" },
];

const STORAGE_KEY = "tv_symbols";
let currentTf = "15";   // M15 default
let symbols = loadSymbols();
let widgets = {};       // containerId -> TradingView.widget instance

function loadSymbols() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch (_) {}
  return [...DEFAULT_SYMBOLS];
}

function saveSymbols() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(symbols)); } catch (_) {}
}

// ── Render the full grid ──────────────────────────────────────────────────────
function renderCharts() {
  const grid = document.getElementById("chart-grid");
  if (!grid) return;
  grid.innerHTML = "";
  widgets = {};

  symbols.forEach((sym, i) => {
    const cell = document.createElement("div");
    cell.className = "chart-cell";

    const head = document.createElement("div");
    head.className = "chart-head";
    head.innerHTML = `<span class="chart-name">${sym.label}</span>`;

    const rm = document.createElement("button");
    rm.className = "chart-remove";
    rm.textContent = "✕";
    rm.title = "Убрать";
    rm.addEventListener("click", () => removeSymbol(i));
    head.appendChild(rm);

    const containerId = `tv_chart_${i}`;
    const body = document.createElement("div");
    body.className = "chart-body";
    body.id = containerId;

    cell.appendChild(head);
    cell.appendChild(body);
    grid.appendChild(cell);

    createWidget(containerId, sym.tv);
  });
}

function createWidget(containerId, symbol) {
  if (typeof TradingView === "undefined") return;
  widgets[containerId] = new TradingView.widget({
    autosize: true,
    symbol: symbol,
    interval: currentTf,
    timezone: "Etc/UTC",
    theme: "dark",
    style: "1",            // candles
    locale: "ru",
    toolbar_bg: "#131722",
    enable_publishing: false,
    hide_top_toolbar: false,
    hide_legend: false,
    save_image: false,
    container_id: containerId,
    studies: [],
    backgroundColor: "#0d0f14",
    gridColor: "#1a1e2e",
  });
}

// ── Add / remove ──────────────────────────────────────────────────────────────
function addSymbol(raw) {
  let tv = raw.trim().toUpperCase();
  if (!tv) return;
  // If user typed just "EURUSD" without exchange prefix, assume FX:
  if (!tv.includes(":")) tv = "FX:" + tv;
  const label = tv.split(":")[1] || tv;
  if (symbols.some(s => s.tv === tv)) return;  // no duplicates
  symbols.push({ tv, label });
  saveSymbols();
  renderCharts();
}

function removeSymbol(index) {
  symbols.splice(index, 1);
  saveSymbols();
  renderCharts();
}

// ── Timeframe switch ──────────────────────────────────────────────────────────
function setTimeframe(tf) {
  currentTf = tf;
  renderCharts();  // recreate widgets at new interval
}

// ── Wire up controls (called from app.js after DOM ready) ─────────────────────
function initCharts() {
  renderCharts();

  const addBtn = document.getElementById("btn-add-symbol");
  const addInput = document.getElementById("add-symbol");
  if (addBtn && addInput) {
    addBtn.addEventListener("click", () => { addSymbol(addInput.value); addInput.value = ""; });
    addInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { addSymbol(addInput.value); addInput.value = ""; }
    });
  }

  document.querySelectorAll(".tf").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tf").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      setTimeframe(btn.dataset.tf);
    });
  });
}
