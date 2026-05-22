"""Persist whether the user has completed an interactive TRR login via Re-scrape."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.config import DATA_DIR

AUTH_STATE_PATH = DATA_DIR / "auth_session.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def is_session_authenticated() -> bool:
    if not AUTH_STATE_PATH.exists():
        return False
    try:
        data = json.loads(AUTH_STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return bool(data.get("authenticated"))


def mark_session_authenticated() -> None:
    _ensure_data_dir()
    AUTH_STATE_PATH.write_text(
        json.dumps(
            {
                "authenticated": True,
                "authenticated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )


def clear_session() -> None:
    if AUTH_STATE_PATH.exists():
        AUTH_STATE_PATH.unlink()


def auth_status() -> dict:
    authenticated = is_session_authenticated()
    return {
        "authenticated": authenticated,
        "needs_login": not authenticated,
        "message": (
            "Sign in via Re-scrape to enable live scraping."
            if not authenticated
            else "Session on file — Re-scrape will reuse your browser profile."
        ),
    }
