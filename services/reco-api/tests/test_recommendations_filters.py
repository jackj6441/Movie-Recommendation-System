import csv
import re
from pathlib import Path

from fastapi.testclient import TestClient

_YEAR_RE = re.compile(r"\((\d{4})\)")


def _genre_map() -> dict[int, list[str]]:
    repo_root = Path(__file__).resolve().parents[3]
    movies_csv = repo_root / "ml-latest-small" / "movies.csv"
    mapping: dict[int, list[str]] = {}
    with open(movies_csv, newline="", encoding="utf-8") as csvfile:
        for row in csv.DictReader(csvfile):
            mid = int(row["movieId"])
            mapping[mid] = [g for g in row["genres"].split("|") if g and g != "(no genres listed)"]
    return mapping


def _year_from_title(title: str) -> int | None:
    matches = _YEAR_RE.findall(title)
    return int(matches[-1]) if matches else None


def test_recommendations_filters_by_genre(load_app):
    client = TestClient(load_app)
    genres = _genre_map()

    response = client.post(
        "/recommendations",
        json={"seeds": [1, 2, 3], "genres": ["Comedy"]},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert items, "genre filter should still return matches"
    for item in items:
        movie_genres = [g.lower() for g in genres.get(item["movie_id"], [])]
        assert "comedy" in movie_genres


def test_recommendations_filters_by_year_range(load_app):
    client = TestClient(load_app)

    response = client.post(
        "/recommendations",
        json={"seeds": [1, 2, 3], "year_min": 1990, "year_max": 1999},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert items, "year filter should still return matches"
    for item in items:
        year = _year_from_title(item["title"])
        assert year is not None
        assert 1990 <= year <= 1999


def test_recommendations_combined_filters_use_any_genre(load_app):
    client = TestClient(load_app)
    genres = _genre_map()

    response = client.post(
        "/recommendations",
        json={"seeds": [1, 2, 3], "genres": ["Comedy", "Romance"], "year_min": 2000, "year_max": 2009},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    for item in items:
        movie_genres = {g.lower() for g in genres.get(item["movie_id"], [])}
        assert movie_genres & {"comedy", "romance"}
        year = _year_from_title(item["title"])
        assert year is not None and 2000 <= year <= 2009


def test_recommendations_returns_up_to_top_k(load_app):
    client = TestClient(load_app)

    response = client.post("/recommendations", json={"seeds": [1, 2, 3]})

    assert response.status_code == 200
    items = response.json()["items"]
    assert 0 < len(items) <= 24


def test_recommendations_unmatchable_filter_returns_empty(load_app):
    client = TestClient(load_app)

    response = client.post(
        "/recommendations",
        json={"seeds": [1, 2, 3], "year_min": 1700, "year_max": 1701},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
