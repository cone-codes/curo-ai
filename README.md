# TheRealReal Search

Hybrid search over luxury resale listings from [The RealReal](https://www.therealreal.com): **BM25 lexical** retrieval plus **multimodal semantic** search (text embeddings + CLIP image embeddings), fused with **Reciprocal Rank Fusion (RRF)**.

## Features

- Playwright scraper for new arrivals (with seed-data fallback when bot protection blocks automated access)
- Indexes title, description, designer, category, condition, size, images, and metadata
- Search API combining lexical + semantic text + semantic image channels
- Web UI with search bar and **Re-scrape listings** button

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install chromium

# From repo root
python run.py
```

Open http://localhost:8000

On first launch, seed listings load automatically so search works immediately. Click **Re-scrape listings** to attempt a live scrape; if PerimeterX blocks the request, the app refreshes the seed catalog and rebuilds indexes.

## Configuration

Environment variables (optional `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SCRAPE_LIST_URL` | New arrivals sale URL | Listing page to scrape |
| `SCRAPE_MAX_PAGES` | 3 | Pages per scrape run |
| `SCRAPE_FALLBACK_TO_SEED` | true | Load `data/seed_listings.json` when live scrape returns nothing |
| `TEXT_EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Sentence-transformers model for text |
| `CLIP_MODEL` | clip-ViT-B-32 | CLIP model for image/text alignment |
| `RRF_K` | 60 | RRF constant (standard default) |

## API

- `GET /api/search?q=chanel+bag` — hybrid search
- `POST /api/scrape` — scrape + reindex
- `POST /api/reindex` — rebuild indexes from DB
- `GET /api/health` — status

## Ranking

1. **Lexical**: BM25 over tokenized title, description, and metadata fields
2. **Semantic text**: cosine similarity of query vs listing text embeddings
3. **Semantic image**: CLIP — query text vs listing image embeddings (falls back to text in CLIP space when images are unavailable)
4. **Fusion**: weighted Reciprocal Rank Fusion across the three ranked lists

## Live scraping notes

The RealReal uses PerimeterX bot protection. Live scraping works best from residential networks or with approved access. The scraper is implemented for when access succeeds; otherwise seed data keeps the app fully functional for development and demos.

## Project layout

```
backend/app/          # FastAPI app, scraper, indexes
backend/static/       # Search UI
data/seed_listings.json
run.py
```
