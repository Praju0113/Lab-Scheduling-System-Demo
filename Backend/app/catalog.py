from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent / 'data' / 'test_catalog.json'


@lru_cache(maxsize=1)
def build_test_catalog() -> list[dict]:
    with CATALOG_PATH.open('r', encoding='utf-8') as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def test_catalog_map() -> dict[str, dict]:
    return {item['test_name']: dict(item) for item in build_test_catalog()}


@lru_cache(maxsize=1)
def category_catalog_map() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in build_test_catalog():
        grouped.setdefault(item['category'], []).append(dict(item))
    return grouped


def category_names() -> list[str]:
    return list(category_catalog_map().keys())


def catalog_item(name: str) -> dict:
    item = test_catalog_map().get(name)
    if item is None:
        raise KeyError(f'Unknown test name: {name}')
    return dict(item)
