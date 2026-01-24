import json
import os
from typing import Tuple

import numpy as np

_embeddings: np.ndarray | None = None
_movie_ids: np.ndarray | None = None
_movie_id_to_row: dict[int, int] | None = None


def _load_embeddings() -> Tuple[np.ndarray, np.ndarray, dict[int, int]]:
    global _embeddings, _movie_ids, _movie_id_to_row

    if _embeddings is not None and _movie_ids is not None and _movie_id_to_row is not None:
        return _embeddings, _movie_ids, _movie_id_to_row

    npz_path = os.getenv("CONTENT_EMBEDDINGS_PATH", "models/content_embeddings.npz")
    index_path = os.getenv("CONTENT_INDEX_PATH", "models/content_index.json")

    data = np.load(npz_path)
    embeddings = data["embeddings"].astype(np.float32)
    movie_ids = data["movie_ids"].astype(np.int64)

    movie_id_to_row: dict[int, int] = {}
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as index_file:
            index_data = json.load(index_file)
            raw_map = index_data.get("movie_id_to_row", {})
            movie_id_to_row = {int(k): int(v) for k, v in raw_map.items()}
    if not movie_id_to_row:
        movie_id_to_row = {int(mid): int(idx) for idx, mid in enumerate(movie_ids)}

    _embeddings = embeddings
    _movie_ids = movie_ids
    _movie_id_to_row = movie_id_to_row
    return embeddings, movie_ids, movie_id_to_row


def get_similar(movie_id: int, topn: int = 10) -> list[tuple[int, float]]:
    embeddings, movie_ids, movie_id_to_row = _load_embeddings()
    if movie_id not in movie_id_to_row:
        return []

    anchor_idx = movie_id_to_row[movie_id]
    anchor_vec = embeddings[anchor_idx]
    sims = embeddings @ anchor_vec
    sims[anchor_idx] = float("-inf")
    top_indices = np.argsort(sims)[::-1][:topn]
    return [(int(movie_ids[idx]), float(sims[idx])) for idx in top_indices]


def get_similarity_scores(anchor_movie_id: int, candidate_movie_ids: list[int]) -> list[float]:
    embeddings, _, movie_id_to_row = _load_embeddings()
    if anchor_movie_id not in movie_id_to_row:
        return [0.0 for _ in candidate_movie_ids]

    anchor_vec = embeddings[movie_id_to_row[anchor_movie_id]]
    scores: list[float] = []
    for movie_id in candidate_movie_ids:
        idx = movie_id_to_row.get(movie_id)
        if idx is None:
            scores.append(0.0)
            continue
        scores.append(float(embeddings[idx] @ anchor_vec))
    return scores


def filter_movie_ids(movie_ids: list[int]) -> list[int]:
    _, _, movie_id_to_row = _load_embeddings()
    return [mid for mid in movie_ids if mid in movie_id_to_row]


def get_embeddings_for_movies(movie_ids: list[int]) -> list[np.ndarray]:
    embeddings, _, movie_id_to_row = _load_embeddings()
    vectors: list[np.ndarray] = []
    for movie_id in movie_ids:
        idx = movie_id_to_row.get(movie_id)
        if idx is None:
            continue
        vectors.append(embeddings[idx])
    return vectors


def get_similarity_scores_from_vector(anchor_vec: np.ndarray, candidate_movie_ids: list[int]) -> list[float]:
    embeddings, _, movie_id_to_row = _load_embeddings()
    scores: list[float] = []
    for movie_id in candidate_movie_ids:
        idx = movie_id_to_row.get(movie_id)
        if idx is None:
            scores.append(0.0)
            continue
        scores.append(float(embeddings[idx] @ anchor_vec))
    return scores
