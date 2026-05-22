# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is a FastAPI-based hybrid search application over luxury resale listings from TheRealReal. It combines BM25 lexical search, semantic text embeddings, and CLIP image embeddings fused via Reciprocal Rank Fusion (RRF). See `README.md` for full details.

### Running the application

```bash
source /workspace/.venv/bin/activate
python run.py
```

The server starts on `http://0.0.0.0:8000`. On first launch, 15 seed listings are automatically loaded from `data/seed_listings.json` into an SQLite database at `data/listings.db`.

### Important caveats

- **First search is slow**: The first call to `GET /api/search?q=...` triggers lazy loading of two sentence-transformers models (~400MB total download from HuggingFace, then index building). Expect 10-30 seconds on first search. Subsequent searches are fast (~60ms).
- **No test suite**: The project has no automated tests, no `pyproject.toml`, and no lint configuration. There is no `pytest`, `flake8`, `ruff`, or similar tooling configured.
- **No CI/CD**: No GitHub Actions or other CI pipelines exist.
- **SQLite auto-managed**: The database at `data/listings.db` is auto-created on first launch. No migrations or manual setup needed.
- **Playwright Chromium**: Required for the scraper (`POST /api/scrape`). Install once via `python3 -m playwright install chromium` after installing pip dependencies.
- **Live scraping usually blocked**: TheRealReal uses PerimeterX bot protection. The app falls back to seed data gracefully.

### Key API endpoints

- `GET /api/health` — status check
- `GET /api/search?q=<query>&limit=<n>` — hybrid search
- `POST /api/scrape` — scrape + reindex (usually falls back to seed data)
- `POST /api/reindex` — rebuild indexes from DB
