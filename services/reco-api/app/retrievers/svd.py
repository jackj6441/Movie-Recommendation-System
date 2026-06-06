"""SVD item-factor retriever: dot product with mean seed factor vector."""

from __future__ import annotations

import numpy as np

from app.artifact_bundle import get_default_bundle
from app.fusion import RETRIEVER_TOP_K


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec if norm == 0 else vec / norm


def retrieve(
    seed_movie_ids: list[int],
    exclude: set[int],
    top_k: int = RETRIEVER_TOP_K,
) -> list[tuple[int, float]]:
    factors, movie_ids, id_to_row = get_default_bundle().fusion.item_factors()
    if factors is None or id_to_row is None or movie_ids is None:
        return []

    seed_rows = [id_to_row[mid] for mid in seed_movie_ids if mid in id_to_row]
    if not seed_rows:
        return []

    anchor = _normalize(np.mean(factors[seed_rows], axis=0))
    scores = factors @ anchor

    for movie_id in exclude:
        row = id_to_row.get(movie_id)
        if row is not None:
            scores[row] = float("-inf")

    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        (int(movie_ids[idx]), float(scores[idx]))
        for idx in top_indices
        if scores[idx] > float("-inf")
    ]
