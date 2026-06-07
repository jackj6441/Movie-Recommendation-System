"""Offline TMDB movie details (overview, watch URL) loaded from a JSON artifact at startup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TMDB_MOVIE_URL_TEMPLATE = "https://www.themoviedb.org/movie/{tmdb_id}"


def load_details_lookup(path: str) -> dict[int, dict[str, Any]]:
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

    lookup: dict[int, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        try:
            movie_id = int(key)
        except (TypeError, ValueError):
            continue
        tmdb_id = value.get("tmdb_id")
        overview = value.get("overview")
        entry: dict[str, Any] = {}
        if tmdb_id is not None:
            try:
                entry["tmdb_id"] = int(tmdb_id)
            except (TypeError, ValueError):
                pass
        if isinstance(overview, str) and overview.strip():
            entry["overview"] = overview.strip()
        if entry:
            lookup[movie_id] = entry
    return lookup


def load_details_meta(path: str) -> dict[str, Any]:
    meta_path = Path(path)
    if not meta_path.is_file():
        return {}

    try:
        with meta_path.open(encoding="utf-8") as meta_file:
            raw = json.load(meta_file)
    except (OSError, json.JSONDecodeError):
        return {}

    return raw if isinstance(raw, dict) else {}


def enrich_movie(movie_id: int, payload: dict, lookup: dict[int, dict[str, Any]]) -> dict:
    enriched = dict(payload)
    details = lookup.get(movie_id)
    if not details:
        return enriched
    overview = details.get("overview")
    if isinstance(overview, str) and overview:
        enriched["overview"] = overview
    tmdb_id = details.get("tmdb_id")
    if isinstance(tmdb_id, int) and tmdb_id > 0:
        enriched["watch_url"] = TMDB_MOVIE_URL_TEMPLATE.format(tmdb_id=tmdb_id)
    return enriched


def details_health_fields(
    lookup: dict[int, dict[str, Any]],
    meta: dict[str, Any],
    catalog_size: int,
) -> dict[str, Any]:
    details_count = int(meta.get("details_count", len(lookup)))
    catalog_movies = int(meta.get("catalog_movies", catalog_size))
    coverage = meta.get("details_coverage")
    if coverage is None and catalog_movies > 0:
        coverage = details_count / catalog_movies
    elif coverage is not None:
        coverage = float(coverage)

    return {
        "details_ok": bool(lookup),
        "details_count": details_count,
        "details_coverage": coverage,
    }
