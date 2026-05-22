from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
LISTINGS_DB = DATA_DIR / "listings.db"
INDEX_DIR = DATA_DIR / "indexes"
SEED_LISTINGS_PATH = DATA_DIR / "seed_listings.json"
DEFAULT_BROWSER_PROFILE = DATA_DIR / "browser_profile"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Scraping ---
    scrape_max_pages: int = 3
    scrape_page_size: int = 48
    scrape_list_url: str = "https://www.therealreal.com/sales/shop-new-arrivals-5753"
    scrape_list_urls: str = ""
    scrape_timeout_ms: int = 90000
    scrape_headless: bool = False
    scrape_fallback_to_seed: bool = False
    scrape_stop_on_block: bool = True

    scrape_warmup_enabled: bool = False
    scrape_home_url: str = "https://www.therealreal.com/"
    scrape_warmup_delay_min_ms: int = 2500
    scrape_warmup_delay_max_ms: int = 5000
    scrape_delay_min_ms: int = 2000
    scrape_delay_max_ms: int = 6000
    scrape_scroll_steps: int = 4

    scrape_use_stealth: bool = True
    scrape_persistent_profile: bool = True
    scrape_user_data_dir: str = ""
    scrape_slow_mo_ms: int = 0
    scrape_keep_browser_open_seconds: int = 120
    scrape_browser_channel: str = ""

    scrape_require_login: bool = True
    scrape_login_url: str = "https://www.therealreal.com/?auth_modal[view]=login"
    scrape_login_wait_seconds: int = 180
    scrape_open_landing_on_no_new: bool = True
    scrape_retry_after_sign_in: bool = True
    scrape_prefer_google_sign_in: bool = True
    scrape_login_first: bool = True
    scrape_cookies_path: str = ""

    lexical_weight: float = 1.0
    semantic_text_weight: float = 1.0
    semantic_image_weight: float = 0.8
    rrf_k: int = 60

    text_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    clip_model: str = "sentence-transformers/clip-ViT-B-32"
    search_top_k: int = 24

    def browser_profile_path(self) -> Path:
        if self.scrape_user_data_dir.strip():
            return Path(self.scrape_user_data_dir).expanduser()
        return DEFAULT_BROWSER_PROFILE

    def listing_urls(self) -> list[str]:
        urls = [self.scrape_list_url.strip()]
        if self.scrape_list_urls.strip():
            urls.extend(u.strip() for u in self.scrape_list_urls.split(",") if u.strip())
        seen: set[str] = set()
        unique: list[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique


settings = Settings()
