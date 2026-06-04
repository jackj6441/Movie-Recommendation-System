"""Load optional Phase 1 fusion artifacts (SVD factors, item neighbors, weights)."""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np

DEFAULT_FUSION_WEIGHTS: dict[str, float] = {
    "content": 0.45,
    "svd": 0.20,
    "item_cf": 0.30,
    "pop": 0.05,
}

_item_factors: np.ndarray | None = None
_item_factor_movie_ids: np.ndarray | None = None
_item_factor_id_to_row: dict[int, int] | None = None
_item_neighbors: dict[str, list[list[float | int]]] | None = None
_fusion_weights: dict[str, float] | None = None


def load_fusion_weights(path: str | None = None) -> dict[str, float]:
    global _fusion_weights
    if _fusion_weights is not None:
        return _fusion_weights

    weights_path = path or os.getenv(
        "FUSION_WEIGHTS_PATH", "models/fusion_weights.json"
    )
    weights = dict(DEFAULT_FUSION_WEIGHTS)
    if os.path.exists(weights_path):
        with open(weights_path, encoding="utf-8") as weights_file:
            raw = json.load(weights_file)
        if isinstance(raw, dict) and "weights" in raw:
            raw = raw["weights"]
        for key, value in raw.items():
            if key in weights:
                weights[key] = float(value)
    _fusion_weights = weights
    return weights


def load_item_factors(
    path: str | None = None,
) -> tuple[np.ndarray | None, np.ndarray | None, dict[int, int] | None]:
    global _item_factors, _item_factor_movie_ids, _item_factor_id_to_row

    if _item_factors is not None:
        return _item_factors, _item_factor_movie_ids, _item_factor_id_to_row

    npz_path = path or os.getenv("ITEM_FACTORS_SVD_PATH", "models/item_factors_svd.npz")
    if not os.path.exists(npz_path):
        return None, None, None

    data = np.load(npz_path)
    factors = data["factors"].astype(np.float32)
    movie_ids = data["movie_ids"].astype(np.int64)
    id_to_row = {int(mid): int(row) for row, mid in enumerate(movie_ids)}

    _item_factors = factors
    _item_factor_movie_ids = movie_ids
    _item_factor_id_to_row = id_to_row
    return factors, movie_ids, id_to_row


def load_item_neighbors(path: str | None = None) -> dict[str, list[list[float | int]]] | None:
    global _item_neighbors
    if _item_neighbors is not None:
        return _item_neighbors

    json_path = path or os.getenv("ITEM_NEIGHBORS_PATH", "models/item_neighbors.json")
    if not os.path.exists(json_path):
        return None

    with open(json_path, encoding="utf-8") as neighbors_file:
        _item_neighbors = json.load(neighbors_file)
    return _item_neighbors


def fusion_health() -> dict[str, Any]:
    factors, _, _ = load_item_factors()
    neighbors = load_item_neighbors()
    weights = load_fusion_weights()
    return {
        "fusion_ok": bool(weights),
        "fusion_weights_ok": bool(weights),
        "svd_ok": factors is not None,
        "item_cf_ok": neighbors is not None,
        "fusion_weights": weights,
    }
