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


def _get_required_env(name: str) -> str:
    value = os.getenv(name, '').strip()
    if value:
        return value
    raise RuntimeError(f'Missing required environment variable: {name}')


def _parse_cors_origins() -> tuple[str, ...]:
    raw_value = _get_required_env('BACKEND_CORS_ORIGINS')
    origins = tuple(origin.strip().rstrip('/') for origin in raw_value.split(',') if origin.strip())
    if origins:
        return origins
    raise RuntimeError('BACKEND_CORS_ORIGINS must contain at least one origin or "*"')


@dataclass(slots=True)
class Settings:
    database_url: str = _get_required_env('DATABASE_URL')
    cors_origins: tuple[str, ...] = _parse_cors_origins()
    seed_on_startup: bool = os.getenv('SEED_ON_STARTUP', 'true').lower() == 'true'
    reset_db_on_startup: bool = os.getenv('RESET_DB_ON_STARTUP', 'false').lower() == 'true'

    @property
    def allow_all_cors_origins(self) -> bool:
        return '*' in self.cors_origins

    @property
    def cors_origin_regex(self) -> str | None:
        return None


settings = Settings()
