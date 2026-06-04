"""Popularity retriever: top-rated catalog movies by offline rating counts."""

from __future__ import annotations

from app.fusion import RETRIEVER_TOP_K


def retrieve(
    popular_movie_ids: list[int],
    movie_popularity: dict[int, int],
    exclude: set[int],
    top_k: int = RETRIEVER_TOP_K,
) -> list[tuple[int, float]]:
    hits: list[tuple[int, float]] = []
    for movie_id in popular_movie_ids:
        if movie_id in exclude:
            continue
        hits.append((movie_id, float(movie_popularity.get(movie_id, 0))))
        if len(hits) >= top_k:
            break
    return hits
