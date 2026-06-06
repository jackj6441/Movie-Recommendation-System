"""Load optional Phase 1 fusion artifacts (SVD factors, item neighbors, weights)."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.artifact_bundle import DEFAULT_FUSION_WEIGHTS, get_default_bundle, load_artifact_bundle

__all__ = [
    "DEFAULT_FUSION_WEIGHTS",
    "fusion_health",
    "load_fusion_weights",
    "load_item_factors",
    "load_item_neighbors",
]


def load_fusion_weights(path: str | None = None) -> dict[str, float]:
    if path is None:
        return dict(get_default_bundle().fusion.weights)
    return dict(load_artifact_bundle(fusion_weights_path=path).fusion.weights)


def load_item_factors(
    path: str | None = None,
) -> tuple[np.ndarray | None, np.ndarray | None, dict[int, int] | None]:
    if path is None:
        return get_default_bundle().fusion.item_factors()
    return load_artifact_bundle(item_factors_svd_path=path).fusion.item_factors()


def load_item_neighbors(path: str | None = None) -> dict[str, list[list[float | int]]] | None:
    if path is None:
        return get_default_bundle().fusion.item_neighbors
    return load_artifact_bundle(item_neighbors_path=path).fusion.item_neighbors


def fusion_health() -> dict[str, Any]:
    health = get_default_bundle().health()
    return {
        "fusion_ok": health["fusion_ok"],
        "fusion_weights_ok": health["fusion_weights_ok"],
        "svd_ok": health["svd_ok"],
        "item_cf_ok": health["item_cf_ok"],
        "fusion_weights": health["fusion_weights"],
    }
