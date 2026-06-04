"""Content embedding retriever: cosine similarity to the seed anchor vector."""

from __future__ import annotations

import numpy as np

from app import content
from app.fusion import RETRIEVER_TOP_K


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec if norm == 0 else vec / norm


def retrieve(
    seed_movie_ids: list[int],
    exclude: set[int],
    top_k: int = RETRIEVER_TOP_K,
) -> list[tuple[int, float]]:
    seed_vectors = content.get_embeddings_for_movies(seed_movie_ids)
    if not seed_vectors:
        return []

    embeddings, movie_ids, movie_id_to_row = content._load_embeddings()
    anchor = _normalize(np.mean(seed_vectors, axis=0))
    sims = embeddings @ anchor

    for movie_id in exclude:
        row = movie_id_to_row.get(movie_id)
        if row is not None:
            sims[row] = float("-inf")

    top_indices = np.argsort(sims)[::-1][:top_k]
    return [(int(movie_ids[idx]), float(sims[idx])) for idx in top_indices if sims[idx] > float("-inf")]
