"use strict";

const API_BASE   = "http://127.0.0.1:8000";

const yfText     = document.getElementById("yfText");
const statusEl   = document.getElementById("status");
const input      = document.getElementById("tickerInput");
const btn        = document.getElementById("searchBtn");
const brandLogo  = document.getElementById("brandLogo");
const yfRow      = document.getElementById("yfRow");
const panel      = document.getElementById("articlesPanel");

// Keep last API result so we can render articles without refetching
let lastResult = null;
let panelOpen  = false;

/* -------------------- UI helpers -------------------- */
function setStatus(msg, type = "") {
  statusEl.className = `status ${type}`;
  statusEl.textContent = msg || "";
}
function pct(n, d) {
  if (!d) return null;
  return Math.round((n / d) * 100);
}
function formatFromResponse(data) {
  const avg = data?.average_sentiment;
  const br  = avg?.breakdown || {};
  const pos = Number(br.positive || 0);
  const neu = Number(br.neutral  || 0);
  const neg = Number(br.negative || 0);
  const total = pos + neu + neg || (Array.isArray(data?.predictions) ? data.predictions.length : 0);

  if (total > 0) {
    const posPct = pct(pos, total);
    if (posPct !== null) return `${posPct}% Positive`;
  }

  if (Array.isArray(data?.predictions) && data.predictions.length) {
    const norm = data.predictions.map((p) => String(p).toLowerCase());
    const posCount = norm.filter((p) => p.includes("pos")).length;
    const posPct = pct(posCount, norm.length);
    if (posPct !== null) return `${posPct}% Positive`;
  }

  return "N/A";
}
function dominantClass(pred) {
  // pred can be string or dict (for finbertprobs)
  if (typeof pred === "string") {
    const p = pred.toLowerCase();
    if (p.includes("pos")) return "pos";
    if (p.includes("neg")) return "neg";
    if (p.includes("neu")) return "neu";
    return "";
  }
  if (pred && typeof pred === "object") {
    const { positive = 0, neutral = 0, negative = 0 } = pred;
    const max = Math.max(positive, neutral, negative);
    if (max === positive) return "pos";
    if (max === negative) return "neg";
    if (max === neutral)  return "neu";
  }
  return "";
}
function predLabel(pred) {
  if (typeof pred === "string") {
    return pred.charAt(0).toUpperCase() + pred.slice(1);
  }
  if (pred && typeof pred === "object") {
    const cls = dominantClass(pred);
    if (cls === "pos") return "Positive";
    if (cls === "neg") return "Negative";
    if (cls === "neu") return "Neutral";
  }
  return "—";
}

/* -------------------- API -------------------- */
async function fetchYahooSentimentGET(ticker, classifier = "vader") {
  const url = `${API_BASE}/api/yf/sentiment/${encodeURIComponent(ticker)}?classifier=${encodeURIComponent(classifier)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* -------------------- Render -------------------- */
function renderArticles(items) {
  if (!Array.isArray(items) || !items.length) {
    panel.innerHTML = `<h4>Articles</h4><div class="item"><span class="meta">No articles found.</span></div>`;
    return;
  }
  const html = [
    `<h4>Articles</h4>`,
    ...items.map((it) => {
      const title = it.title || "(No title)";
      const url   = it.url || "#";
      const src   = it.source || "Unknown";
      const prev  = it.content_preview || "";
      const cls   = dominantClass(it.prediction);
      const lab   = predLabel(it.prediction);
      return `
        <div class="item">
          <a class="title" href="${url}" target="_blank" rel="noopener">${title}</a>
          <span class="pred ${cls}">${lab}</span>
          <span class="meta">${src}</span>
          ${prev ? `<div class="meta" style="margin-top:6px;">${prev}</div>` : ""}
        </div>
      `;
    })
  ].join("");
  panel.innerHTML = html;
}

/* -------------------- Handlers -------------------- */
async function handleSearch() {
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) {
    setStatus("Enter a stock ticker (e.g., TSLA).", "error");
    return;
  }

  setStatus("Fetching sentiment...", "ok");
  yfText.textContent = "—";
  panel.classList.add("hidden");
  panelOpen = false;

  // Optional logo swap if you have components/{ticker}.png
  brandLogo.onerror = () => (brandLogo.src = "components/tesla.png");
  brandLogo.src = `components/${ticker.toLowerCase()}.png`;

  try {
    const data = await fetchYahooSentimentGET(ticker, "vader");
    lastResult = data; // keep it so clicking can render articles
    yfText.textContent = formatFromResponse(data);
    setStatus("Done.", "ok");
  } catch (err) {
    console.error(err);
    yfText.textContent = "N/A";
    setStatus("Failed to fetch sentiment.", "error");
  }
}

function toggleArticles() {
  if (!lastResult || !Array.isArray(lastResult.detailed_predictions)) {
    setStatus("No articles loaded. Search a ticker first.", "error");
    return;
  }
  if (panelOpen) {
    panel.classList.add("hidden");
    panelOpen = false;
  } else {
    renderArticles(lastResult.detailed_predictions);
    panel.classList.remove("hidden");
    panelOpen = true;
  }
}

/* -------------------- Wire up -------------------- */
btn.addEventListener("click", handleSearch);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSearch();
});
yfRow.addEventListener("click", toggleArticles);
