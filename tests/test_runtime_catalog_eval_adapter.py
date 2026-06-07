"""R3: evaluation and training use the same RuntimeCatalog loader as serving."""

from __future__ import annotations

import csv
import importlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "evaluation"
RECO_API_ROOT = REPO_ROOT / "services" / "reco-api"
MODELS_DIR = RECO_API_ROOT / "models"

sys.path.insert(0, str(EVAL_DIR))
sys.path.insert(0, str(RECO_API_ROOT))


def _write_movies_csv(path: Path, rows: list[tuple[int, str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["movieId", "title", "genres"])
        for movie_id, title, genres in rows:
            writer.writerow([movie_id, title, genres])


def _write_ratings_csv(path: Path, rows: list[tuple[int, int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["userId", "movieId", "rating", "timestamp"])
        for user_id, movie_id in rows:
            writer.writerow([user_id, movie_id, 4.0, 1])


@pytest.fixture(autouse=True)
def isolate_serving_modules():
    from fusion_ranking import _reload_ranking_modules

    _reload_ranking_modules()
    yield
    _reload_ranking_modules()


def test_eval_catalog_is_runtime_catalog_alias():
    from fusion_ranking import EvalCatalog
    from app.runtime_catalog import RuntimeCatalog

    assert EvalCatalog.__name__ == RuntimeCatalog.__name__
    assert EvalCatalog.__module__ == RuntimeCatalog.__module__


def test_load_eval_catalog_includes_genres_and_years(tmp_path: Path):
    from fusion_ranking import load_eval_catalog

    movies = tmp_path / "movies.csv"
    _write_movies_csv(
        movies,
        [(1, "Toy Story (1995)", "Animation|Comedy"), (2, "Heat (1995)", "Action|Crime")],
    )
    catalog = load_eval_catalog(movies)
    assert catalog.movie_genres[1] == ["Animation", "Comedy"]
    assert catalog.movie_years[1] == 1995
    assert "Comedy" in catalog.known_genres


def test_load_eval_catalog_popularity_from_ratings(tmp_path: Path):
    from fusion_ranking import load_eval_catalog

    movies = tmp_path / "movies.csv"
    _write_movies_csv(movies, [(1, "A (2000)", "Comedy"), (2, "B (2001)", "Drama")])
    ratings = tmp_path / "ratings.csv"
    _write_ratings_csv(ratings, [(1, 1), (2, 1), (2, 2)])
    catalog = load_eval_catalog(movies, ratings_csv=ratings)
    assert catalog.movie_popularity[1] == 2
    assert catalog.movie_popularity[2] == 1
    assert catalog.popular_movie_ids == [1, 2]


def test_load_eval_catalog_popularity_from_serving_stats(tmp_path: Path):
    from fusion_ranking import load_eval_catalog

    movies = tmp_path / "movies.csv"
    _write_movies_csv(movies, [(1, "A (2000)", "Comedy"), (2, "B (2001)", "Drama")])
    stats = tmp_path / "stats.json"
    stats.write_text(
        json.dumps({"movie_popularity": {"1": 5, "2": 20}, "popular_movie_ids": [2, 1]}),
        encoding="utf-8",
    )
    catalog = load_eval_catalog(movies, serving_stats_json=stats)
    assert catalog.popular_movie_ids == [2, 1]


def test_rank_seed_set_uses_ranking_view(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from fusion_ranking import configure_artifact_paths, load_eval_catalog, rank_seed_set

    configure_artifact_paths(
        content_embeddings=MODELS_DIR / "content_embeddings.npz",
        content_index=MODELS_DIR / "content_index.json",
    )
    movies = tmp_path / "movies.csv"
    _write_movies_csv(movies, [(1, "A (2000)", "Comedy"), (2, "B (2001)", "Drama"), (3, "C (2002)", "Drama")])
    catalog = load_eval_catalog(movies)

    seen: dict[str, object] = {}

    def fake_rank_seed_set(request):
        seen["request"] = request
        raise seed_ranker.InvalidSeedsError("test")

    seed_ranker = importlib.import_module("app.seed_ranker")
    monkeypatch.setattr(seed_ranker, "rank_seed_set", fake_rank_seed_set)

    rank_seed_set([1, 2], catalog, top_k=5)
    assert seen["request"].seed_movie_ids == [1, 2]
    assert seen["request"].catalog is catalog
    assert seen["request"].top_k == 5
