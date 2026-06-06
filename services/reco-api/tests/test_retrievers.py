"""Tests that retrievers read fusion/content artifacts from the bundle."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

API_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = API_ROOT / "tests" / "fixtures"
MODELS = API_ROOT / "models"

sys.path.insert(0, str(API_ROOT))

from app import artifact_bundle  # noqa: E402
from app.retrievers import content_retriever, item_cf, svd  # noqa: E402


@pytest.fixture(autouse=True)
def reset_bundle_singleton():
    artifact_bundle.reset_default_bundle()
    yield
    artifact_bundle.reset_default_bundle()


def _write_retrieval_fixtures() -> None:
    factors = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ],
        dtype=np.float32,
    )
    np.savez(
        FIXTURES / "item_factors_svd.sample.npz",
        movie_ids=np.array([1, 2, 3], dtype=np.int64),
        factors=factors,
    )
    neighbors = {
        "1": [[2, 0.9], [3, 0.4]],
        "2": [[3, 0.8]],
        "3": [[1, 0.7]],
    }
    with open(FIXTURES / "item_neighbors.sample.json", "w", encoding="utf-8") as neighbors_file:
        json.dump(neighbors, neighbors_file)


def _load_test_bundle(monkeypatch):
    _write_retrieval_fixtures()
    monkeypatch.setenv("CONTENT_EMBEDDINGS_PATH", str(MODELS / "content_embeddings.npz"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(MODELS / "content_index.json"))
    monkeypatch.setenv("ITEM_FACTORS_SVD_PATH", str(FIXTURES / "item_factors_svd.sample.npz"))
    monkeypatch.setenv("ITEM_NEIGHBORS_PATH", str(FIXTURES / "item_neighbors.sample.json"))
    return artifact_bundle.get_default_bundle()


def test_svd_retriever_reads_fusion_artifacts_from_bundle(monkeypatch):
    _load_test_bundle(monkeypatch)
    hits = svd.retrieve([1], exclude={1}, top_k=5)
    assert hits
    assert all(movie_id != 1 for movie_id, _ in hits)


def test_item_cf_retriever_reads_neighbors_from_bundle(monkeypatch):
    _load_test_bundle(monkeypatch)
    hits = item_cf.retrieve([1], exclude={1}, top_k=5)
    movie_ids = [movie_id for movie_id, _ in hits]
    assert 2 in movie_ids
    assert 3 in movie_ids


def test_content_retriever_reads_embeddings_from_bundle(monkeypatch):
    _load_test_bundle(monkeypatch)
    hits = content_retriever.retrieve([1], exclude={1}, top_k=5)
    assert hits
    assert all(movie_id != 1 for movie_id, _ in hits)


def test_svd_retriever_does_not_call_artifacts_shim(monkeypatch):
    bundle = _load_test_bundle(monkeypatch)
    monkeypatch.setattr(
        "app.artifacts.load_item_factors",
        MagicMock(side_effect=AssertionError("retriever should use bundle directly")),
    )
    monkeypatch.setattr("app.retrievers.svd.get_default_bundle", lambda: bundle)
    hits = svd.retrieve([1], exclude={1}, top_k=3)
    assert hits
