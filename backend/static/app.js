const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const resultsEl = document.getElementById("results");
const statusLine = document.getElementById("status-line");
const statsEl = document.getElementById("stats");
const rescrapeBtn = document.getElementById("rescrape-btn");

async function fetchAuthStatus() {
  const res = await fetch("/api/auth/status");
  if (!res.ok) return null;
  return res.json();
}

async function fetchHealth() {
  const res = await fetch("/api/health");
  if (!res.ok) return;
  const data = await res.json();
  const auth = await fetchAuthStatus();
  const authHint = auth?.needs_login
    ? " · sign in on first Re-scrape"
    : auth?.authenticated
      ? " · TRR session saved"
      : "";
  const mode = data.scrape_defaults?.headless ? "headless" : "headed";
  statsEl.textContent = `${data.listings} listings · index ${data.index_ready ? "ready" : "building"} · scrape ${mode}${authHint}`;
}

function formatPrice(listing) {
  if (listing.price == null) return "";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: listing.currency || "USD",
    maximumFractionDigits: 0,
  }).format(listing.price);
}

const TRR_LANDING = "https://www.therealreal.com/";

function openSignInTab(url) {
  const target = url || TRR_LANDING;
  window.open(target, "_blank", "noopener,noreferrer");
}

function formatScrapeStatus(data) {
  const parts = [
    `Status: ${data.status}`,
    `Outcome: ${data.outcome || "n/a"}`,
    `${data.new_listings} new, ${data.total_listings} total`,
    `${data.products_found ?? 0} products this run`,
  ];
  if (data.block_type) parts.push(`Block: ${data.block_type}`);
  if (data.blocked_at_url) parts.push(`Blocked at: ${data.blocked_at_url}`);
  if (data.pages_scraped) parts.push(`Pages scraped: ${data.pages_scraped}`);
  if (data.used_seed_fallback) parts.push("Seed fallback used");
  if (data.session_authenticated) parts.push("TRR session active");
  if (data.message) parts.push(data.message);
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
  const auth = await fetchAuthStatus();
  if (auth?.needs_login) {
    const proceed = window.confirm(
      "First Re-scrape: a browser window will open so you can sign in to The RealReal.\n\n" +
        "After you sign in, scraping will continue automatically.\n\nContinue?"
    );
    if (!proceed) return;
  }

  rescrapeBtn.disabled = true;
  statusLine.textContent = auth?.needs_login
    ? "Opening browser — sign in to The RealReal when prompted…"
    : "Re-scraping listings (reusing your saved session)…";

  try {
    const res = await fetch("/api/scrape", { method: "POST" });
    const data = await res.json();
    const payload = data.detail && typeof data.detail === "object" ? data.detail : data;

    if (!res.ok) {
      statusLine.textContent = formatScrapeStatus(payload);
      if (payload.status === "login_required" || payload.outcome === "login_required") {
        statusLine.textContent +=
          " Set SCRAPE_HEADLESS=false, then click Re-scrape again to sign in.";
      } else if (payload.block_type === "captcha") {
        statusLine.textContent += " Complete any captcha in the browser window.";
      }
      if (payload.new_listings === 0 || payload.opened_sign_in_tab) {
        openSignInTab(payload.sign_in_landing_url);
      }
      await fetchHealth();
      return;
    }

    statusLine.textContent = formatScrapeStatus(payload);
    if (payload.new_listings === 0 || payload.opened_sign_in_tab) {
      openSignInTab(payload.sign_in_landing_url);
      statusLine.textContent += " — opened The RealReal in a new tab to sign in.";
    }
    await fetchHealth();
  } catch (err) {
    statusLine.textContent = err.message;
  } finally {
    rescrapeBtn.disabled = false;
  }
});

fetchHealth();
