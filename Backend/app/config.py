from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Prefer the repository-level .env so backend and frontend share one source of truth.
load_dotenv(REPO_ROOT / '.env', override=False)
load_dotenv(BACKEND_ROOT / '.env', override=False)


DEFAULT_CORS_ORIGINS = (
    'http://127.0.0.1:3000',
    'http://localhost:3000',
    'http://127.0.0.1:4173',
    'http://localhost:4173',
    'http://127.0.0.1:5173',
    'http://localhost:5173',
)

LOCAL_ORIGIN_REGEX = (
    r'^https?://('
    r'localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|'
    r'10(?:\.\d{1,3}){3}|'
    r'192\.168(?:\.\d{1,3}){2}|'
    r'172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}'
    r')(?::\d+)?$'
)


def _parse_cors_origins() -> tuple[str, ...]:
    raw_value = os.getenv('BACKEND_CORS_ORIGINS')
    if not raw_value:
        return DEFAULT_CORS_ORIGINS
    origins = tuple(origin.strip().rstrip('/') for origin in raw_value.split(',') if origin.strip())
    return origins or DEFAULT_CORS_ORIGINS


@dataclass(slots=True)
class Settings:
    database_url: str = os.getenv('DATABASE_URL', 'postgresql+psycopg://postgres:postgres@localhost:5432/lab_scalable')
    cors_origins: tuple[str, ...] = _parse_cors_origins()
    seed_on_startup: bool = os.getenv('SEED_ON_STARTUP', 'true').lower() == 'true'
    reset_db_on_startup: bool = os.getenv('RESET_DB_ON_STARTUP', 'false').lower() == 'true'

    @property
    def allow_all_cors_origins(self) -> bool:
        return '*' in self.cors_origins

    @property
    def cors_origin_regex(self) -> str | None:
        return None if self.allow_all_cors_origins else LOCAL_ORIGIN_REGEX


settings = Settings()
