"""Tests for the serving ArtifactBundle (R1: load, capabilities, flat health keys)."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

API_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = API_ROOT / "tests" / "fixtures"
MODELS = API_ROOT / "models"

sys.path.insert(0, str(API_ROOT))

from app import artifact_bundle  # noqa: E402


@pytest.fixture(autouse=True)
def reset_bundle_singleton():
    artifact_bundle.reset_default_bundle()
    yield
    artifact_bundle.reset_default_bundle()


def _write_retrieval_fixtures() -> None:
    factors = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    np.savez(FIXTURES / "item_factors_svd.sample.npz", factors=factors, movie_ids=np.array([1, 2, 3]))
    neighbors = {"1": [[2, 0.9], [3, 0.8]], "2": [[1, 0.9]], "3": [[1, 0.7]]}
    with open(FIXTURES / "item_neighbors.sample.json", "w", encoding="utf-8") as neighbors_file:
        json.dump(neighbors, neighbors_file)


def test_load_artifact_bundle_reads_content_and_fusion_defaults():
    bundle = artifact_bundle.load_artifact_bundle(
        content_embeddings_path=str(MODELS / "content_embeddings.npz"),
        content_index_path=str(MODELS / "content_index.json"),
    )
    assert bundle.content.ok is True
    assert bundle.content.filter_movie_ids([1, 999999]) == [1]
    assert bundle.fusion.weights["content"] == pytest.approx(0.45)
    assert bundle.fusion.svd_ok is False
    assert bundle.fusion.item_cf_ok is False


def test_load_artifact_bundle_reads_svd_and_item_cf_fixtures():
    _write_retrieval_fixtures()
    bundle = artifact_bundle.load_artifact_bundle(
        content_embeddings_path=str(MODELS / "content_embeddings.npz"),
        content_index_path=str(MODELS / "content_index.json"),
        item_factors_svd_path=str(FIXTURES / "item_factors_svd.sample.npz"),
        item_neighbors_path=str(FIXTURES / "item_neighbors.sample.json"),
    )
    assert bundle.fusion.svd_ok is True
    assert bundle.fusion.item_cf_ok is True
    factors, movie_ids, id_to_row = bundle.fusion.item_factors()
    assert factors is not None
    assert int(movie_ids[0]) == 1
    assert id_to_row[2] == 1


def test_content_get_similar_returns_ranked_neighbors():
    bundle = artifact_bundle.load_artifact_bundle(
        content_embeddings_path=str(MODELS / "content_embeddings.npz"),
        content_index_path=str(MODELS / "content_index.json"),
    )
    similar = bundle.content.get_similar(1, topn=3)
    assert similar
    assert all(movie_id != 1 for movie_id, _ in similar)
    assert similar == sorted(similar, key=lambda item: item[1], reverse=True)


def test_bundle_health_exposes_flat_compatible_keys():
    _write_retrieval_fixtures()
    bundle = artifact_bundle.load_artifact_bundle(
        content_embeddings_path=str(MODELS / "content_embeddings.npz"),
        content_index_path=str(MODELS / "content_index.json"),
        item_factors_svd_path=str(FIXTURES / "item_factors_svd.sample.npz"),
        item_neighbors_path=str(FIXTURES / "item_neighbors.sample.json"),
    )
    health = bundle.health()
    assert health["content_ok"] is True
    assert health["fusion_ok"] is True
    assert health["fusion_weights_ok"] is True
    assert health["svd_ok"] is True
    assert health["item_cf_ok"] is True
    assert set(health["fusion_weights"]) == {"content", "svd", "item_cf", "pop"}
    assert health["ltr_ok"] is False
    assert "ltr_model_path" in health
    assert "ltr_feature_names" in health
    assert "ltr_trained_at" in health


def test_load_artifact_bundle_from_env_uses_monkeypatched_paths(monkeypatch):
    _write_retrieval_fixtures()
    monkeypatch.setenv("CONTENT_EMBEDDINGS_PATH", str(MODELS / "content_embeddings.npz"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(MODELS / "content_index.json"))
    monkeypatch.setenv("ITEM_FACTORS_SVD_PATH", str(FIXTURES / "item_factors_svd.sample.npz"))
    monkeypatch.setenv("ITEM_NEIGHBORS_PATH", str(FIXTURES / "item_neighbors.sample.json"))
    bundle = artifact_bundle.load_artifact_bundle_from_env()
    assert bundle.fusion.svd_ok is True
    assert bundle.fusion.item_cf_ok is True


def test_get_default_bundle_caches_until_reset(monkeypatch):
    monkeypatch.setenv("CONTENT_EMBEDDINGS_PATH", str(MODELS / "content_embeddings.npz"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(MODELS / "content_index.json"))
    first = artifact_bundle.get_default_bundle()
    second = artifact_bundle.get_default_bundle()
    assert first is second
    artifact_bundle.reset_default_bundle()
    third = artifact_bundle.get_default_bundle()
    assert third is not first


def test_missing_content_embeddings_raises():
    with pytest.raises(OSError):
        artifact_bundle.load_artifact_bundle(
            content_embeddings_path=str(MODELS / "__missing_content__.npz"),
            content_index_path=str(MODELS / "content_index.json"),
        )
