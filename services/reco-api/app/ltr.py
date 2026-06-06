"""Phase 2 LightGBM Lambdarank scorer (optional; falls back to fusion when unavailable)."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from app.artifact_bundle import get_default_bundle, load_artifact_bundle
from app.fusion import CHANNELS


def default_model_path() -> str:
    return os.getenv("LTR_MODEL_PATH", "models/ltr_model.txt")


def default_meta_path() -> str:
    return os.getenv("LTR_META_PATH", "models/ltr_meta.json")


def rating_to_relevance(rating: float) -> int:
    """Graded relevance for offline labels: >=4 high, 3 medium, else low."""
    if rating >= 4.0:
        return 2
    if rating >= 3.0:
        return 1
    return 0


def load_ltr_model(
    model_path: str | None = None,
    meta_path: str | None = None,
) -> tuple[Any | None, list[str], dict[str, Any]]:
    if model_path is None and meta_path is None:
        ltr = get_default_bundle().ltr
        return ltr.booster, list(ltr.feature_names), dict(ltr.meta)

    bundle = load_artifact_bundle(
        ltr_model_path=model_path or default_model_path(),
        ltr_meta_path=meta_path or default_meta_path(),
    )
    ltr = bundle.ltr
    return ltr.booster, list(ltr.feature_names), dict(ltr.meta)


def ltr_available() -> bool:
    booster, _, _ = load_ltr_model()
    return booster is not None


def features_to_matrix(
    rows: list[tuple[int, dict[str, float]]],
    feature_names: list[str] | None = None,
) -> np.ndarray:
    names = feature_names or list(CHANNELS)
    matrix = np.zeros((len(rows), len(names)), dtype=np.float32)
    for row_index, (_, breakdown) in enumerate(rows):
        for col_index, name in enumerate(names):
            matrix[row_index, col_index] = float(breakdown.get(name, 0.0))
    return matrix


def score_candidates(
    rows: list[tuple[int, dict[str, float]]],
) -> list[tuple[int, float, dict[str, float]]]:
    """Return (movie_id, ltr_score, channel_features) sorted by score descending."""
    booster, feature_names, _ = load_ltr_model()
    if booster is None or not rows:
        return []

    matrix = features_to_matrix(rows, feature_names)
    scores = booster.predict(matrix)
    ranked = [
        (int(movie_id), float(scores[idx]), dict(breakdown))
        for idx, (movie_id, breakdown) in enumerate(rows)
    ]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked


def ltr_health() -> dict[str, Any]:
    health = get_default_bundle().health()
    return {
        "ltr_ok": health["ltr_ok"],
        "ltr_model_path": health["ltr_model_path"],
        "ltr_feature_names": health["ltr_feature_names"],
        "ltr_trained_at": health["ltr_trained_at"],
    }
