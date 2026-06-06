"""Typed serving artifact bundle: content embeddings, fusion artifacts, and optional LTR."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_FUSION_WEIGHTS: dict[str, float] = {
    "content": 0.45,
    "svd": 0.20,
    "item_cf": 0.30,
    "pop": 0.05,
}

_default_bundle: ArtifactBundle | None = None


@dataclass(frozen=True)
class ContentArtifacts:
    embeddings: np.ndarray
    movie_ids: np.ndarray
    movie_id_to_row: dict[int, int]

    @property
    def ok(self) -> bool:
        return len(self.movie_ids) > 0

    def filter_movie_ids(self, movie_ids: list[int]) -> list[int]:
        return [mid for mid in movie_ids if mid in self.movie_id_to_row]

    def get_similar(self, movie_id: int, topn: int = 10) -> list[tuple[int, float]]:
        if movie_id not in self.movie_id_to_row:
            return []

        anchor_idx = self.movie_id_to_row[movie_id]
        anchor_vec = self.embeddings[anchor_idx]
        sims = self.embeddings @ anchor_vec
        sims[anchor_idx] = float("-inf")
        top_indices = np.argsort(sims)[::-1][:topn]
        return [(int(self.movie_ids[idx]), float(sims[idx])) for idx in top_indices]

    def get_similarity_scores(self, anchor_movie_id: int, candidate_movie_ids: list[int]) -> list[float]:
        if anchor_movie_id not in self.movie_id_to_row:
            return [0.0 for _ in candidate_movie_ids]

        anchor_vec = self.embeddings[self.movie_id_to_row[anchor_movie_id]]
        scores: list[float] = []
        for movie_id in candidate_movie_ids:
            idx = self.movie_id_to_row.get(movie_id)
            if idx is None:
                scores.append(0.0)
                continue
            scores.append(float(self.embeddings[idx] @ anchor_vec))
        return scores

    def get_embeddings_for_movies(self, movie_ids: list[int]) -> list[np.ndarray]:
        vectors: list[np.ndarray] = []
        for movie_id in movie_ids:
            idx = self.movie_id_to_row.get(movie_id)
            if idx is None:
                continue
            vectors.append(self.embeddings[idx])
        return vectors

    def get_similarity_scores_from_vector(
        self,
        anchor_vec: np.ndarray,
        candidate_movie_ids: list[int],
    ) -> list[float]:
        scores: list[float] = []
        for movie_id in candidate_movie_ids:
            idx = self.movie_id_to_row.get(movie_id)
            if idx is None:
                scores.append(0.0)
                continue
            scores.append(float(self.embeddings[idx] @ anchor_vec))
        return scores


@dataclass(frozen=True)
class FusionArtifacts:
    weights: dict[str, float]
    factors: np.ndarray | None = None
    factor_movie_ids: np.ndarray | None = None
    factor_id_to_row: dict[int, int] | None = None
    item_neighbors: dict[str, list[list[float | int]]] | None = None

    @property
    def svd_ok(self) -> bool:
        return self.factors is not None

    @property
    def item_cf_ok(self) -> bool:
        return self.item_neighbors is not None

    def item_factors(self) -> tuple[np.ndarray | None, np.ndarray | None, dict[int, int] | None]:
        return self.factors, self.factor_movie_ids, self.factor_id_to_row


@dataclass(frozen=True)
class LtrArtifacts:
    booster: Any | None
    feature_names: list[str]
    meta: dict[str, Any]
    model_path: str

    @property
    def ok(self) -> bool:
        return self.booster is not None


@dataclass(frozen=True)
class ArtifactBundle:
    content: ContentArtifacts
    fusion: FusionArtifacts
    ltr: LtrArtifacts

    def health(self) -> dict[str, Any]:
        weights = self.fusion.weights
        return {
            "content_ok": self.content.ok,
            "fusion_ok": bool(weights),
            "fusion_weights_ok": bool(weights),
            "svd_ok": self.fusion.svd_ok,
            "item_cf_ok": self.fusion.item_cf_ok,
            "fusion_weights": dict(weights),
            "ltr_ok": self.ltr.ok,
            "ltr_model_path": self.ltr.model_path,
            "ltr_feature_names": list(self.ltr.feature_names),
            "ltr_trained_at": self.ltr.meta.get("trained_at"),
        }


def _load_content_artifacts(
    embeddings_path: str,
    index_path: str,
) -> ContentArtifacts:
    data = np.load(embeddings_path)
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

    return ContentArtifacts(
        embeddings=embeddings,
        movie_ids=movie_ids,
        movie_id_to_row=movie_id_to_row,
    )


def _load_fusion_weights(weights_path: str) -> dict[str, float]:
    weights = dict(DEFAULT_FUSION_WEIGHTS)
    if os.path.exists(weights_path):
        with open(weights_path, encoding="utf-8") as weights_file:
            raw = json.load(weights_file)
        if isinstance(raw, dict) and "weights" in raw:
            raw = raw["weights"]
        for key, value in raw.items():
            if key in weights:
                weights[key] = float(value)
    return weights


def _load_fusion_artifacts(
    *,
    weights_path: str,
    item_factors_path: str,
    item_neighbors_path: str,
) -> FusionArtifacts:
    weights = _load_fusion_weights(weights_path)

    factors: np.ndarray | None = None
    factor_movie_ids: np.ndarray | None = None
    factor_id_to_row: dict[int, int] | None = None
    if os.path.exists(item_factors_path):
        data = np.load(item_factors_path)
        factors = data["factors"].astype(np.float32)
        factor_movie_ids = data["movie_ids"].astype(np.int64)
        factor_id_to_row = {int(mid): int(row) for row, mid in enumerate(factor_movie_ids)}

    item_neighbors: dict[str, list[list[float | int]]] | None = None
    if os.path.exists(item_neighbors_path):
        with open(item_neighbors_path, encoding="utf-8") as neighbors_file:
            item_neighbors = json.load(neighbors_file)

    return FusionArtifacts(
        weights=weights,
        factors=factors,
        factor_movie_ids=factor_movie_ids,
        factor_id_to_row=factor_id_to_row,
        item_neighbors=item_neighbors,
    )


def _load_ltr_artifacts(model_path: str, meta_path: str) -> LtrArtifacts:
    try:
        import lightgbm as lgb
    except (ImportError, OSError):  # pragma: no cover - missing lib or OpenMP
        from app.fusion import CHANNELS

        return LtrArtifacts(
            booster=None,
            feature_names=list(CHANNELS),
            meta={},
            model_path=model_path,
        )

    from app.fusion import CHANNELS

    model_file = Path(model_path)
    meta_file = Path(meta_path)
    if not model_file.exists():
        return LtrArtifacts(
            booster=None,
            feature_names=list(CHANNELS),
            meta={},
            model_path=model_path,
        )

    booster = lgb.Booster(model_file=str(model_file))
    meta: dict[str, Any] = {}
    if meta_file.exists():
        with open(meta_file, encoding="utf-8") as meta_handle:
            meta = json.load(meta_handle)

    feature_names = list(meta.get("feature_names", CHANNELS))
    return LtrArtifacts(
        booster=booster,
        feature_names=feature_names,
        meta=meta,
        model_path=model_path,
    )


def load_artifact_bundle(
    *,
    content_embeddings_path: str | None = None,
    content_index_path: str | None = None,
    fusion_weights_path: str | None = None,
    item_factors_svd_path: str | None = None,
    item_neighbors_path: str | None = None,
    ltr_model_path: str | None = None,
    ltr_meta_path: str | None = None,
) -> ArtifactBundle:
    content = _load_content_artifacts(
        content_embeddings_path or os.getenv("CONTENT_EMBEDDINGS_PATH", "models/content_embeddings.npz"),
        content_index_path or os.getenv("CONTENT_INDEX_PATH", "models/content_index.json"),
    )
    fusion = _load_fusion_artifacts(
        weights_path=fusion_weights_path or os.getenv("FUSION_WEIGHTS_PATH", "models/fusion_weights.json"),
        item_factors_path=item_factors_svd_path or os.getenv("ITEM_FACTORS_SVD_PATH", "models/item_factors_svd.npz"),
        item_neighbors_path=item_neighbors_path or os.getenv("ITEM_NEIGHBORS_PATH", "models/item_neighbors.json"),
    )
    ltr = _load_ltr_artifacts(
        ltr_model_path or os.getenv("LTR_MODEL_PATH", "models/ltr_model.txt"),
        ltr_meta_path or os.getenv("LTR_META_PATH", "models/ltr_meta.json"),
    )
    return ArtifactBundle(content=content, fusion=fusion, ltr=ltr)


def load_artifact_bundle_from_env() -> ArtifactBundle:
    return load_artifact_bundle()


def get_default_bundle() -> ArtifactBundle:
    global _default_bundle
    if _default_bundle is None:
        _default_bundle = load_artifact_bundle_from_env()
    return _default_bundle


def reset_default_bundle() -> None:
    global _default_bundle
    _default_bundle = None
