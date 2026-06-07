"""Tests for runtime catalog loading and views."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app import runtime_catalog  # noqa: E402
from app.runtime_catalog import SearchHit  # noqa: E402


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


def test_parse_year_from_title():
    assert runtime_catalog.parse_year("Toy Story (1995)") == 1995
    assert runtime_catalog.parse_year("No year here") is None


def test_load_from_movies_csv(tmp_path: Path):
    movies = tmp_path / "movies.csv"
    _write_movies_csv(
        movies,
        [
            (1, "Toy Story (1995)", "Animation|Children|Comedy"),
            (2, "Jumanji (1995)", "Adventure|Children|Fantasy"),
        ],
    )
    catalog = runtime_catalog.load_runtime_catalog(
        movies_csv_path=movies,
        ratings_csv_path=tmp_path / "missing_ratings.csv",
        serving_stats_path=tmp_path / "missing_stats.json",
    )
    assert catalog.movie_titles[1] == "Toy Story (1995)"
    assert "Comedy" in catalog.movie_genres[1]
    assert catalog.movie_years[1] == 1995
    assert catalog.known_genres == {"Animation", "Children", "Comedy", "Adventure", "Fantasy"}


def test_popularity_from_serving_stats(tmp_path: Path):
    movies = tmp_path / "movies.csv"
    _write_movies_csv(movies, [(1, "A (2000)", "Comedy"), (2, "B (2001)", "Drama")])
    stats = tmp_path / "stats.json"
    stats.write_text(
        json.dumps(
            {
                "movie_popularity": {"1": 10, "2": 50},
                "popular_movie_ids": [2, 1],
                "num_users": 100,
                "num_items": 2,
            }
        ),
        encoding="utf-8",
    )
    catalog = runtime_catalog.load_runtime_catalog(
        movies_csv_path=movies,
        ratings_csv_path=tmp_path / "ratings.csv",
        serving_stats_path=stats,
    )
    assert catalog.popular_movie_ids == [2, 1]
    assert catalog.movie_popularity[2] == 50
    assert catalog.num_users == 100
    assert catalog.num_items == 2


def test_popularity_fallback_from_ratings(tmp_path: Path):
    movies = tmp_path / "movies.csv"
    _write_movies_csv(movies, [(1, "A (2000)", "Comedy"), (2, "B (2001)", "Drama")])
    ratings = tmp_path / "ratings.csv"
    _write_ratings_csv(ratings, [(1, 1), (2, 1), (2, 2), (3, 2)])
    catalog = runtime_catalog.load_runtime_catalog(
        movies_csv_path=movies,
        ratings_csv_path=ratings,
        serving_stats_path=tmp_path / "missing_stats.json",
    )
    assert catalog.movie_popularity[2] == 2
    assert catalog.movie_popularity[1] == 2
    assert set(catalog.popular_movie_ids[:2]) == {1, 2}
    assert catalog.num_users == 3
    assert catalog.num_items == 2


def test_search_movies_substring_case_insensitive(tmp_path: Path):
    movies = tmp_path / "movies.csv"
    _write_movies_csv(
        movies,
        [(1, "Toy Story (1995)", "Animation"), (2, "Toy Soldiers (1991)", "Action")],
    )
    catalog = runtime_catalog.load_runtime_catalog(movies_csv_path=movies)
    hits = catalog.search_movies("TOY")
    assert len(hits) == 2
    assert all(isinstance(hit, SearchHit) for hit in hits)


def test_genre_seed_ids_with_year_min(tmp_path: Path):
    movies = tmp_path / "movies.csv"
    _write_movies_csv(
        movies,
        [
            (1, "Old Comedy (1980)", "Comedy"),
            (2, "New Comedy (2010)", "Comedy"),
        ],
    )
    ratings = tmp_path / "ratings.csv"
    _write_ratings_csv(ratings, [(1, 1), (1, 2), (2, 2)])
    catalog = runtime_catalog.load_runtime_catalog(movies_csv_path=movies, ratings_csv_path=ratings)
    ids = catalog.genre_seed_ids("Comedy", 10, year_min=2000)
    assert ids == [2]


def test_singleton_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    movies = tmp_path / "movies.csv"
    _write_movies_csv(movies, [(1, "A (2000)", "Comedy")])
    monkeypatch.setenv("MOVIES_CSV_PATH", str(movies))
    monkeypatch.setenv("RATINGS_CSV_PATH", str(tmp_path / "ratings.csv"))
    monkeypatch.setenv("SERVING_STATS_PATH", str(tmp_path / "stats.json"))

    runtime_catalog.reset_default_catalog()
    first = runtime_catalog.get_default_catalog()
    second = runtime_catalog.get_default_catalog()
    assert first is second

    replacement = runtime_catalog.load_runtime_catalog(movies_csv_path=movies)
    runtime_catalog.set_default_catalog(replacement)
    assert runtime_catalog.get_default_catalog() is replacement
    runtime_catalog.reset_default_catalog()
