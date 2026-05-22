import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import SEED_LISTINGS_PATH, settings
from backend.app.indexing.manager import IndexManager
from backend.app.models import ScrapeStatus, SearchResponse
from backend.app.scraper.service import ScrapeService
from backend.app.search_service import SearchService
from backend.app.storage import count_listings, load_seed_from_file, upsert_many

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

index_manager = IndexManager()
search_service = SearchService(index_manager)
scrape_service = ScrapeService()


def _bootstrap_data() -> None:
    if count_listings() == 0 and SEED_LISTINGS_PATH.exists():
        logger.info("Loading initial seed listings")
        upsert_many(load_seed_from_file(SEED_LISTINGS_PATH))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _bootstrap_data()
    yield


app = FastAPI(
    title="TheRealReal Search",
    description="Lexical + multimodal semantic search over TheRealReal listings",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "listings": count_listings(),
        "index_ready": index_manager.ready,
        "scrape_defaults": {
            "headless": settings.scrape_headless,
            "persistent_profile": settings.scrape_persistent_profile,
            "profile_dir": str(settings.browser_profile_path()),
            "warmup_enabled": settings.scrape_warmup_enabled,
            "require_login": settings.scrape_require_login,
            "login_wait_seconds": settings.scrape_login_wait_seconds,
            "slow_mo_ms": settings.scrape_slow_mo_ms,
            "keep_browser_open_seconds": settings.scrape_keep_browser_open_seconds,
        },
    }


@app.get("/api/search", response_model=SearchResponse)
async def search(q: str = Query(..., min_length=1), limit: int = Query(default=24, ge=1, le=100)):
    if count_listings() == 0:
        raise HTTPException(status_code=400, detail="No listings indexed. Run scrape first.")
    return search_service.search(q.strip(), limit=limit)


@app.post("/api/scrape", response_model=ScrapeStatus)
async def scrape():
    result = await scrape_service.scrape()

    if count_listings() > 0:
        index_manager.build()

    if result.status in ("blocked", "captcha_required", "login_required") and not result.used_seed_fallback:
        raise HTTPException(
            status_code=503,
            detail=result.model_dump(),
        )

    if result.status == "empty" and count_listings() == 0:
        raise HTTPException(
            status_code=503,
            detail=result.model_dump(),
        )

    return result


@app.post("/api/reindex")
async def reindex():
    if count_listings() == 0:
        raise HTTPException(status_code=400, detail="No listings to index.")
    index_manager.build()
    return {"status": "ok", "listings": count_listings(), "index_ready": index_manager.ready}
