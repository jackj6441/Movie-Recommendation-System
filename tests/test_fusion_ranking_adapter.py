"""Tests for the evaluation fusion_ranking bundle adapter."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "evaluation"
RECO_API_ROOT = REPO_ROOT / "services" / "reco-api"
MODELS_DIR = RECO_API_ROOT / "models"

sys.path.insert(0, str(EVAL_DIR))
sys.path.insert(0, str(RECO_API_ROOT))


@pytest.fixture(autouse=True)
def isolate_serving_modules():
    from fusion_ranking import _reload_ranking_modules

    _reload_ranking_modules()
    yield
    _reload_ranking_modules()


def test_configure_artifact_paths_installs_bundle_without_artifact_env(monkeypatch):
    monkeypatch.delenv("CONTENT_EMBEDDINGS_PATH", raising=False)
    monkeypatch.delenv("CONTENT_INDEX_PATH", raising=False)
    monkeypatch.delenv("ITEM_FACTORS_SVD_PATH", raising=False)
    monkeypatch.delenv("ITEM_NEIGHBORS_PATH", raising=False)
    monkeypatch.delenv("FUSION_WEIGHTS_PATH", raising=False)

    from fusion_ranking import configure_artifact_paths

    bundle = configure_artifact_paths(
        content_embeddings=MODELS_DIR / "content_embeddings.npz",
        content_index=MODELS_DIR / "content_index.json",
    )

    assert bundle.content.ok is True
    assert "CONTENT_EMBEDDINGS_PATH" not in __import__("os").environ

    artifact_bundle = importlib.import_module("app.artifact_bundle")
    assert artifact_bundle.get_default_bundle() is bundle


def test_rank_seed_set_uses_installed_bundle():
    from fusion_ranking import configure_artifact_paths, load_eval_catalog, rank_seed_set

    configure_artifact_paths(
        content_embeddings=MODELS_DIR / "content_embeddings.npz",
        content_index=MODELS_DIR / "content_index.json",
    )
    catalog = load_eval_catalog(REPO_ROOT / "ml-latest-small" / "movies.csv")
    ranked = rank_seed_set([1, 2, 3], catalog, top_k=5)
    assert ranked
    assert all(movie_id not in {1, 2, 3} for movie_id in ranked)
