"""Phase 2 LightGBM Lambdarank scorer (optional; falls back to fusion when unavailable)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from app.fusion import CHANNELS

_booster: Any | None = None
_feature_names: list[str] | None = None
_meta: dict[str, Any] | None = None


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
    global _booster, _feature_names, _meta

    if _booster is not None and _feature_names is not None and _meta is not None:
        return _booster, _feature_names, _meta

    try:
        import lightgbm as lgb
    except (ImportError, OSError):  # pragma: no cover - missing lib or OpenMP
        return None, list(CHANNELS), {}

    model_file = Path(model_path or default_model_path())
    meta_file = Path(meta_path or default_meta_path())
    if not model_file.exists():
        return None, list(CHANNELS), {}

    booster = lgb.Booster(model_file=str(model_file))
    meta: dict[str, Any] = {}
    if meta_file.exists():
        with open(meta_file, encoding="utf-8") as meta_handle:
            meta = json.load(meta_handle)

    feature_names = list(meta.get("feature_names", CHANNELS))
    _booster = booster
    _feature_names = feature_names
    _meta = meta
    return booster, feature_names, meta


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
    booster, feature_names, meta = load_ltr_model()
    return {
        "ltr_ok": booster is not None,
        "ltr_model_path": default_model_path(),
        "ltr_feature_names": feature_names,
        "ltr_trained_at": meta.get("trained_at"),
    }
