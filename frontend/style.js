"use strict";

const API_BASE   = "http://127.0.0.1:8000";

// Elements
const yfText     = document.getElementById("yfText");
const redditText = document.getElementById("redditText");
const newsText   = document.getElementById("newsText");
const statusEl   = document.getElementById("status");
const input      = document.getElementById("tickerInput");
const btn        = document.getElementById("searchBtn");
const brandLogo  = document.getElementById("brandLogo");

const yfRow      = document.getElementById("yfRow");
const redditRow  = document.getElementById("redditRow");
const newsRow    = document.getElementById("newsRow");

const panel      = document.getElementById("articlesPanel"); // Yahoo
const redditPanel= document.getElementById("redditPanel");    // Reddit
const newsPanel  = document.getElementById("newsPanel");      // General news

// State
let currentTicker     = null;
let lastYahooResult   = null;
let lastNewsResult    = null;
let lastRedditResult  = null;   // contains predictions & average_sentiment
let lastRedditTexts   = null;   // texts from /reddit/fetch

let yahooPanelOpen    = false;
let newsPanelOpen     = false;
let redditPanelOpen   = false;

/* -------------------- UI helpers -------------------- */
function setStatus(msg, type = "") {
  statusEl.className = `status ${type}`;
  statusEl.textContent = msg || "";
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
function formatAvgDisplay(avg) {
  const dom = dominantFromAvg(avg);
  return dom.valuePct != null ? `${dom.valuePct}% ${dom.label}` : "N/A";
}

/* -------------------- API -------------------- */
// Yahoo
async function fetchYahooSentimentGET(ticker, classifier = "finbertprobs") {
  const url = `${API_BASE}/api/yf/sentiment/${encodeURIComponent(ticker)}?classifier=${encodeURIComponent(classifier)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// General News
async function fetchGeneralNewsPOST(ticker, classifier = "finbertprobs", limit = 50, include_description = true, sort_by = "publishedAt") {
  const url = `${API_BASE}/api/sentiment/news/${encodeURIComponent(ticker)}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      classifier,
      limit_articles: limit,
      include_description,
      sort_by
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Reddit
async function fetchRedditSentimentPOST(ticker, classifier = "finbertprobs", timeframe = "day", limit_posts = 80, include_comments = true, comments_per_post = 8, include_finance_subs = true) {
  const url = `${API_BASE}/api/sentiment/reddit/${encodeURIComponent(ticker)}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      classifier,
      timeframe,
      limit_posts,
      include_comments,
      comments_per_post,
      include_finance_subs
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
async function fetchRedditTextsGET(ticker, timeframe = "day", limit_posts = 80, include_comments = true, comments_per_post = 8, include_finance_subs = true) {
  const params = new URLSearchParams({
    ticker,
    timeframe,
    limit_posts,
    include_comments,
    comments_per_post,
    include_finance_subs
  });
  const url = `${API_BASE}/reddit/fetch?${params.toString()}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* -------------------- Renderers -------------------- */
// Yahoo panel: uses detailed_predictions provided by backend
function renderArticlesYahoo(items) {
  if (!Array.isArray(items) || !items.length) {
    panel.innerHTML = `<h4>Yahoo Articles</h4><div class="item"><span class="meta">No articles found.</span></div>`;
    return;
  }
  const html = [
    `<h4>Yahoo Articles</h4>`,
    ...items.map((it) => {
      const title = it.title || "(No title)";
      const url   = it.url || "#";
      const src   = it.source || "Unknown";
      const prev  = it.content_preview || "";
      const p     = it.prediction || {};
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

// General News panel: uses detailed_predictions provided by backend with deduplication
function renderArticlesNews(items) {
  if (!Array.isArray(items) || !items.length) {
    newsPanel.innerHTML = `<h4>General News</h4><div class="item"><span class="meta">No articles found.</span></div>`;
    return;
  }

  // Deduplicate articles based on URL or title
  const seen = new Set();
  const uniqueItems = items.filter((it) => {
    const url = it.article_url || "";
    const title = it.article_title || it.text || "";
    const key = url || title; // Use URL as primary key, fallback to title
    
    if (!key || seen.has(key)) {
      return false; // Skip if no key or already seen
    }
    seen.add(key);
    return true;
  });

  const html = [
    `<h4>General News</h4>`,
    ...uniqueItems.map((it) => {
      const title = it.article_title || it.text || "(No title)";
      const url   = it.article_url || "#";
      const src   = it.source || "Unknown";
      const prev  = it.text || "";
      const p     = it.prediction || {};
      const negPct = pc100(p.negative);
      const neuPct = pc100(p.neutral);
      const posPct = pc100(p.positive);
      return `
        <div class="item">
          <a class="title" href="${url}" target="_blank" rel="noopener">${title}</a>
          <span class="meta">${src}${it.publishedAt ? ` • ${new Date(it.publishedAt).toLocaleString()}` : ""}</span>
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
  newsPanel.innerHTML = html;
}

// Reddit panel: pair /reddit/fetch texts with /api/sentiment/reddit predictions by index
function renderReddit(texts, predictions) {
  if (!Array.isArray(texts) || !texts.length) {
    redditPanel.innerHTML = `<h4>Reddit</h4><div class="item"><span class="meta">No posts found.</span></div>`;
    return;
  }
  const n = Math.min(texts.length, Array.isArray(predictions) ? predictions.length : 0);
  if (n === 0) {
    redditPanel.innerHTML = `<h4>Reddit</h4><div class="item"><span class="meta">No sentiment available.</span></div>`;
    return;
  }

  const html = [
    `<h4>Reddit</h4>`,
    ...Array.from({ length: n }).map((_, i) => {
      const text = texts[i] || "";
      const pred = predictions[i];

      // pred may be a dict (finbertprobs) or a string label
      let posPct = null, neuPct = null, negPct = null;
      if (pred && typeof pred === "object") {
        posPct = pc100(pred.positive);
        neuPct = pc100(pred.neutral);
        negPct = pc100(pred.negative);
      }

      return `
        <div class="item">
          <div class="meta">${text}</div>
          ${
            posPct !== null
              ? `<div class="preds">
                  <span class="badge pos">Pos ${posPct}%</span>
                  <span class="badge neu">Neu ${neuPct}%</span>
                  <span class="badge neg">Neg ${negPct}%</span>
                 </div>`
              : `<div class="preds"><span class="badge neu">${String(pred)}</span></div>`
          }
        </div>
      `;
    })
  ].join("");

  redditPanel.innerHTML = html;
}

/* -------------------- Handlers -------------------- */
async function handleSearch() {
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) {
    setStatus("Enter a stock ticker (e.g., TSLA).", "error");
    return;
  }
  currentTicker = ticker;

  setStatus("Fetching sentiment...", "ok");
  yfText.textContent     = "—";
  redditText.textContent = "—";
  newsText.textContent   = "—";

  // close panels
  panel.classList.add("hidden");
  redditPanel.classList.add("hidden");
  newsPanel.classList.add("hidden");
  yahooPanelOpen  = false;
  redditPanelOpen = false;
  newsPanelOpen   = false;

  // Optional logo swap
  brandLogo.onerror = () => (brandLogo.src = "components/tesla.png");
  brandLogo.src = `components/${ticker.toLowerCase()}.png`;

  // Kick off all three in parallel, but don't fail the whole flow if one rejects
  const results = await Promise.allSettled([
    fetchYahooSentimentGET(ticker, "finbertprobs"),
    fetchGeneralNewsPOST(ticker, "finbertprobs", 50, true, "publishedAt"),
    fetchRedditSentimentPOST(ticker, "finbertprobs", "day", 80, true, 8, true),
  ]);

  const [yfRes, newsRes, redditRes] = results;

  if (yfRes.status === "fulfilled") {
    lastYahooResult  = yfRes.value;
    yfText.textContent = formatAvgDisplay(yfRes.value.average_sentiment);
  } else {
    lastYahooResult = null;
    yfText.textContent = "N/A";
    console.error("Yahoo failed:", yfRes.reason);
  }

  if (newsRes.status === "fulfilled") {
    lastNewsResult   = newsRes.value;
    newsText.textContent = formatAvgDisplay(newsRes.value.average_sentiment);
  } else {
    lastNewsResult = null;
    newsText.textContent = "N/A";
    console.error("News failed:", newsRes.reason);
  }

  if (redditRes.status === "fulfilled") {
    lastRedditResult = redditRes.value;
    redditText.textContent = formatAvgDisplay(redditRes.value.average_sentiment);
    lastRedditTexts = null; // reset so we fetch texts lazily on click
  } else {
    lastRedditResult = null;
    redditText.textContent = "N/A";
    lastRedditTexts = null;
    console.error("Reddit failed:", redditRes.reason);
  }

  const hadError = results.some(r => r.status === "rejected");
  setStatus(hadError ? "Some sources failed." : "Done.", hadError ? "error" : "ok");
}


function toggleYahoo() {
  if (!lastYahooResult || !Array.isArray(lastYahooResult.detailed_predictions)) {
    setStatus("No Yahoo articles loaded. Search a ticker first.", "error");
    return;
  }
  // Close others
  redditPanel.classList.add("hidden"); redditPanelOpen = false;
  newsPanel.classList.add("hidden");   newsPanelOpen = false;

  if (yahooPanelOpen) {
    panel.classList.add("hidden");
    yahooPanelOpen = false;
  } else {
    renderArticlesYahoo(lastYahooResult.detailed_predictions);
    panel.classList.remove("hidden");
    yahooPanelOpen = true;
  }
}

async function toggleReddit() {
  if (!lastRedditResult) {
    setStatus("No Reddit sentiment loaded. Search a ticker first.", "error");
    return;
  }
  // Close others
  panel.classList.add("hidden");     yahooPanelOpen = false;
  newsPanel.classList.add("hidden"); newsPanelOpen  = false;

  try {
    if (redditPanelOpen) {
      redditPanel.classList.add("hidden");
      redditPanelOpen = false;
      return;
    }
    // Lazily fetch texts (so initial search remains fast)
    if (!lastRedditTexts) {
      const r = await fetchRedditTextsGET(currentTicker, "day", 80, true, 8, true);
      lastRedditTexts = Array.isArray(r.texts) ? r.texts : [];
    }
    renderReddit(lastRedditTexts, lastRedditResult.predictions || []);
    redditPanel.classList.remove("hidden");
    redditPanelOpen = true;
  } catch (e) {
    console.error(e);
    setStatus("Failed to load Reddit posts.", "error");
  }
}

function toggleNews() {
  if (!lastNewsResult || !Array.isArray(lastNewsResult.detailed_predictions)) {
    setStatus("No General News loaded. Search a ticker first.", "error");
    return;
  }
  // Close others
  panel.classList.add("hidden");       yahooPanelOpen = false;
  redditPanel.classList.add("hidden"); redditPanelOpen = false;

  if (newsPanelOpen) {
    newsPanel.classList.add("hidden");
    newsPanelOpen = false;
  } else {
    renderArticlesNews(lastNewsResult.detailed_predictions);
    newsPanel.classList.remove("hidden");
    newsPanelOpen = true;
  }
}

/* -------------------- Wire up -------------------- */
btn.addEventListener("click", handleSearch);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSearch();
});
yfRow.addEventListener("click", toggleYahoo);
redditRow.addEventListener("click", toggleReddit);
newsRow.addEventListener("click", toggleNews);