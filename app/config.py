from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:  # A missing optional dotenv loader must not block the local-rules demo.
    pass

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "incidents.db"
DEFAULT_RUNBOOKS_PATH = PROJECT_ROOT / "data" / "runbooks.json"


def get_db_path() -> Path:
    """Resolve the SQLite file path at runtime, allowing tests to isolate databases."""
    return Path(os.getenv("INCIDENT_DB_PATH", str(DEFAULT_DB_PATH))).expanduser().resolve()


def get_runbooks_path() -> Path:
    return Path(os.getenv("RUNBOOKS_PATH", str(DEFAULT_RUNBOOKS_PATH))).expanduser().resolve()


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or None


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
