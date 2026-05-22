const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const resultsEl = document.getElementById("results");
const statusLine = document.getElementById("status-line");
const statsEl = document.getElementById("stats");
const rescrapeBtn = document.getElementById("rescrape-btn");

async function fetchHealth() {
  const res = await fetch("/api/health");
  if (!res.ok) return;
  const data = await res.json();
  const mode = data.scrape_defaults?.headless ? "headless" : "headed";
  statsEl.textContent = `${data.listings} listings · index ${data.index_ready ? "ready" : "building"} · scrape ${mode}`;
}

function formatPrice(listing) {
  if (listing.price == null) return "";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: listing.currency || "USD",
    maximumFractionDigits: 0,
  }).format(listing.price);
}

function formatScrapeStatus(data) {
  const parts = [
    `Status: ${data.status}`,
    `Outcome: ${data.outcome || "n/a"}`,
    `${data.new_listings} new, ${data.total_listings} total`,
    `${data.products_found ?? 0} products this run`,
  ];
  if (data.block_type) {
    parts.push(`Block: ${data.block_type}`);
  }
  if (data.blocked_at_url) {
    parts.push(`Blocked at: ${data.blocked_at_url}`);
  }
  if (data.pages_scraped) {
    parts.push(`Pages scraped: ${data.pages_scraped}`);
  }
  if (data.used_seed_fallback) {
    parts.push("Seed fallback used");
  }
  if (data.message) {
    parts.push(data.message);
  }
  return parts.join(" · ");
}

function renderResults(payload) {
  if (!payload.results.length) {
    resultsEl.innerHTML = '<p class="empty">No matches found. Try another query or re-scrape for new listings.</p>';
    return;
  }

  resultsEl.innerHTML = payload.results
    .map(({ listing, score, rank, match_reasons }) => {
      const img = listing.image_urls?.[0] || "";
      const meta = [
        listing.designer,
        listing.category,
        listing.condition,
        listing.size,
        formatPrice(listing),
      ]
        .filter(Boolean)
        .join(" · ");

      const badges = (match_reasons || [])
        .map((r) => `<span class="badge">${r.replace(/_/g, " ")}</span>`)
        .join("");

      return `
        <article class="card">
          ${img ? `<img src="${img}" alt="${listing.title}" loading="lazy" />` : "<div></div>"}
          <div class="card-body">
            <h2><a href="${listing.url}" target="_blank" rel="noopener noreferrer">#${rank} ${listing.title}</a></h2>
            <p class="meta">${meta}</p>
            <p class="description">${listing.description}</p>
            <div class="badges">${badges}<span class="badge score">RRF ${score.toFixed(4)}</span></div>
          </div>
        </article>
      `;
    })
    .join("");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = queryInput.value.trim();
  if (!q) return;

  statusLine.textContent = "Searching…";
  resultsEl.innerHTML = "";

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      throw new Error(detail || "Search failed");
    }
    statusLine.textContent = `${data.total} results in ${data.took_ms} ms for “${data.query}”`;
    renderResults(data);
  } catch (err) {
    statusLine.textContent = err.message;
  }
});

rescrapeBtn.addEventListener("click", async () => {
  rescrapeBtn.disabled = true;
  statusLine.textContent =
    "Scraping TheRealReal with session warmup (headed browser recommended). This may take 1–2 minutes…";

  try {
    const res = await fetch("/api/scrape", { method: "POST" });
    const data = await res.json();
    const payload = data.detail && typeof data.detail === "object" ? data.detail : data;

    if (!res.ok) {
      statusLine.textContent = formatScrapeStatus(payload);
      if (payload.block_type === "captcha") {
        statusLine.textContent +=
          " — Try SCRAPE_HEADLESS=false locally and complete the captcha in the browser window.";
      }
      await fetchHealth();
      return;
    }

    statusLine.textContent = formatScrapeStatus(payload);
    await fetchHealth();
  } catch (err) {
    statusLine.textContent = err.message;
  } finally {
    rescrapeBtn.disabled = false;
  }
});

fetchHealth();
