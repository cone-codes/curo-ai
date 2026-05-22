from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
LISTINGS_DB = DATA_DIR / "listings.db"
INDEX_DIR = DATA_DIR / "indexes"
SEED_LISTINGS_PATH = DATA_DIR / "seed_listings.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    scrape_max_pages: int = 3
    scrape_page_size: int = 48
    scrape_list_url: str = "https://www.therealreal.com/sales/shop-new-arrivals-5753"
    scrape_timeout_ms: int = 60000
    scrape_headless: bool = True
    # When live scrape fails (e.g. bot protection), load/merge seed listings.
    scrape_fallback_to_seed: bool = True

    # Hybrid search weights (RRF constant k is separate)
    lexical_weight: float = 1.0
    semantic_text_weight: float = 1.0
    semantic_image_weight: float = 0.8
    rrf_k: int = 60

    text_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    clip_model: str = "sentence-transformers/clip-ViT-B-32"
    search_top_k: int = 24


settings = Settings()
