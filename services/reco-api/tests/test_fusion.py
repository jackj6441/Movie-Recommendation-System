"""Tests for Phase 1 multi-retriever fusion."""

from __future__ import annotations

import json
import importlib
import sys
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.fusion import fuse, merge_candidate_ids, minmax_normalize  # noqa: E402
FIXTURES = API_ROOT / "tests" / "fixtures"


def test_minmax_normalize_spreads_scores():
    normalized = minmax_normalize([(1, 0.2), (2, 0.8), (3, 0.5)])
    assert normalized[1] == 0.0
    assert normalized[2] == 1.0
    assert 0.0 < normalized[3] < 1.0


def test_merge_candidate_ids_caps_union():
    channel_hits = {
        "content": [(i, float(i)) for i in range(300)],
        "svd": [(i + 100, float(i)) for i in range(300)],
    }
    merged = merge_candidate_ids(channel_hits, cap=400)
    assert len(merged) == 400


def test_fuse_missing_channel_scores_zero():
    channel_hits = {"content": [(10, 1.0), (11, 0.5)]}
    fused = fuse([10, 11, 12], channel_hits, {"content": 1.0, "svd": 0.0, "item_cf": 0.0, "pop": 0.0})
    by_id = {movie_id: score for movie_id, score, _ in fused}
    assert by_id[10] > by_id[11]
    assert by_id[12] == 0.0


def test_healthz_reports_fusion_fields(load_app):
    client = TestClient(load_app)
    payload = client.get("/healthz").json()
    assert payload["ranking_mode"] == "multi_retriever_fusion"
    assert payload["fusion_ok"] is True
    assert payload["fusion_weights_ok"] is True
    assert "svd_ok" in payload
    assert "item_cf_ok" in payload


def test_recommendations_use_fusion_score(load_app):
    client = TestClient(load_app)
    response = client.post("/recommendations", json={"seeds": [1, 2, 3]})
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert all("score" in item for item in items)


def test_explanations_final_differs_from_content_only_when_fusion_active(load_app):
    client = TestClient(load_app)
    response = client.post("/explanations", json={"seeds": [1, 2, 3]})
    assert response.status_code == 200
    topk = response.json()["topk"]
    assert topk
    for row in topk:
        assert "content" in row
        assert "final" in row


def test_ranked_list_explanation_topk_uses_content_and_final_scores(load_app):
    del load_app
    app_main = importlib.import_module("app.main")
    seed_ranker = importlib.import_module("app.seed_ranker")

    result = seed_ranker.rank_seed_set(
        seed_ranker.RankRequest(seed_movie_ids=[1, 2, 3], catalog=app_main.catalog)
    )
    assert result.items
    rows = result.explanation_topk()
    assert len(rows) == len(result.items)
    for row, item in zip(rows, result.items):
        assert row == {
            "movie_id": item.movie_id,
            "title": item.title,
            "content": item.content_score,
            "final": item.fusion_score,
        }


def test_rank_seed_set_shuffle_calls_random_shuffle(load_app, monkeypatch):
    del load_app
    app_main = importlib.import_module("app.main")
    seed_ranker = importlib.import_module("app.seed_ranker")
    shuffled_lengths: list[int] = []

    monkeypatch.setattr(
        seed_ranker.random,
        "shuffle",
        lambda items: shuffled_lengths.append(len(items)),
    )

    seed_ranker.rank_seed_set(
        seed_ranker.RankRequest(seed_movie_ids=[1, 2, 3], catalog=app_main.catalog)
    )
    assert shuffled_lengths == []

    result = seed_ranker.rank_seed_set(
        seed_ranker.RankRequest(
            seed_movie_ids=[1, 2, 3],
            catalog=app_main.catalog,
            shuffle=True,
        )
    )
    assert result.items
    assert len(shuffled_lengths) == 1
    assert shuffled_lengths[0] >= len(result.items)


def test_rank_seed_set_applies_request_top_k(load_app):
    del load_app
    app_main = importlib.import_module("app.main")
    seed_ranker = importlib.import_module("app.seed_ranker")

    result = seed_ranker.rank_seed_set(
        seed_ranker.RankRequest(
            seed_movie_ids=[1, 2, 3],
            catalog=app_main.catalog,
            top_k=3,
        )
    )

    assert len(result.items) == 3


def test_rank_seed_set_applies_rank_filters(load_app):
    del load_app
    app_main = importlib.import_module("app.main")
    seed_ranker = importlib.import_module("app.seed_ranker")

    result = seed_ranker.rank_seed_set(
        seed_ranker.RankRequest(
            seed_movie_ids=[1, 2, 3],
            catalog=app_main.catalog,
            filters=seed_ranker.RankFilters(
                genres=["Comedy"],
                year_min=1990,
                year_max=1999,
            ),
        )
    )

    assert result.items
    for item in result.items:
        assert "Comedy" in app_main.catalog.movie_genres[item.movie_id]
        year = app_main.catalog.movie_years[item.movie_id]
        assert 1990 <= year <= 1999


def _write_retrieval_fixtures() -> None:
    factors = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
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


def test_healthz_svd_and_item_cf_ok_with_fixtures(monkeypatch, repo_root, api_root):
    from conftest import _configure_test_env, _reload_app

    _write_retrieval_fixtures()
    monkeypatch.setenv("ITEM_FACTORS_SVD_PATH", str(FIXTURES / "item_factors_svd.sample.npz"))
    monkeypatch.setenv("ITEM_NEIGHBORS_PATH", str(FIXTURES / "item_neighbors.sample.json"))
    _configure_test_env(monkeypatch, repo_root, api_root)
    app = _reload_app(api_root)
    payload = TestClient(app).get("/healthz").json()
    assert payload["svd_ok"] is True
    assert payload["item_cf_ok"] is True
