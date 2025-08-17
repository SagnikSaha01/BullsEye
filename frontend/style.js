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
function pc100(x) {
  if (x == null) return 0;
  const v = Number(x);
  return Math.round((v <= 1 ? v * 100 : v));
}
function dominantFromAvg(avg) {
  if (!avg) return { label: "N/A", valuePct: null };
  const neg = Number(avg.negative ?? 0);
  const neu = Number(avg.neutral  ?? 0);
  const pos = Number(avg.positive ?? 0);
  const max = Math.max(neg, neu, pos);
  if (max === pos) return { label: "Positive", valuePct: pc100(pos) };
  if (max === neu) return { label: "Neutral",  valuePct: pc100(neu) };
  return { label: "Negative", valuePct: pc100(neg) };
}
function formatFromResponse(data) {
  // For finbertprobs, show dominant class with its percentage from average_sentiment
  const avg = data?.average_sentiment;
  const dom = dominantFromAvg(avg);
  return dom.valuePct != null ? `${dom.valuePct}% ${dom.label}` : "N/A";
}

/* -------------------- API -------------------- */
async function fetchYahooSentimentGET(ticker, classifier = "finbertprobs") {
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

      // prediction is a dict of floats for finbertprobs
      const p = it.prediction || {};
      const negPct = pc100(p.negative);
      const neuPct = pc100(p.neutral);
      const posPct = pc100(p.positive);

      return `
        <div class="item">
          <a class="title" href="${url}" target="_blank" rel="noopener">${title}</a>
          <span class="meta">${src}</span>
          ${prev ? `<div class="meta" style="margin-top:6px;">${prev}</div>` : ""}
          <div class="preds">
            <span class="badge pos">Pos ${posPct}%</span>
            <span class="badge neu">Neu ${neuPct}%</span>
            <span class="badge neg">Neg ${negPct}%</span>
          </div>
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
    // Use finbertprobs for this flow
    const data = await fetchYahooSentimentGET(ticker, "finbertprobs");
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
