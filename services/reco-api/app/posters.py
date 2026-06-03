"""Offline TMDB poster lookup loaded from a JSON artifact at startup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_poster_lookup(path: str) -> dict[int, dict[str, str]]:
    lookup_path = Path(path)
    if not lookup_path.is_file():
        return {}

    try:
        with lookup_path.open(encoding="utf-8") as lookup_file:
            raw = json.load(lookup_file)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw, dict):
        return {}

    lookup: dict[int, dict[str, str]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        poster_url = value.get("poster_url")
        poster_thumb_url = value.get("poster_thumb_url")
        if not poster_url or not poster_thumb_url:
            continue
        try:
            movie_id = int(key)
        except (TypeError, ValueError):
            continue
        lookup[movie_id] = {
            "poster_url": str(poster_url),
            "poster_thumb_url": str(poster_thumb_url),
        }
    return lookup


def load_poster_meta(path: str) -> dict[str, Any]:
    meta_path = Path(path)
    if not meta_path.is_file():
        return {}

    try:
        with meta_path.open(encoding="utf-8") as meta_file:
            raw = json.load(meta_file)
    except (OSError, json.JSONDecodeError):
        return {}

    return raw if isinstance(raw, dict) else {}


def enrich_movie(movie_id: int, payload: dict, lookup: dict[int, dict[str, str]]) -> dict:
    enriched = dict(payload)
    posters = lookup.get(movie_id)
    if not posters:
        return enriched
    enriched["poster_url"] = posters["poster_url"]
    enriched["poster_thumb_url"] = posters["poster_thumb_url"]
    return enriched


def poster_health_fields(
    lookup: dict[int, dict[str, str]],
    meta: dict[str, Any],
    catalog_size: int,
) -> dict[str, Any]:
    poster_count = int(meta.get("poster_count", len(lookup)))
    catalog_movies = int(meta.get("catalog_movies", catalog_size))
    coverage = meta.get("poster_coverage")
    if coverage is None and catalog_movies > 0:
        coverage = poster_count / catalog_movies
    elif coverage is not None:
        coverage = float(coverage)

    return {
        "poster_ok": bool(lookup),
        "poster_count": poster_count,
        "poster_coverage": coverage,
    }
