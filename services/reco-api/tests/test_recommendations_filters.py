import csv
import importlib
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

_YEAR_RE = re.compile(r"\((\d{4})\)")


def load_app(monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    api_root = repo_root / "services" / "reco-api"

    monkeypatch.setenv("MOVIES_CSV_PATH", str(repo_root / "ml-latest-small" / "movies.csv"))
    monkeypatch.setenv("RATINGS_CSV_PATH", str(repo_root / "ml-latest-small" / "ratings.csv"))
    monkeypatch.setenv("SERVING_STATS_PATH", str(repo_root / "ml-latest-small" / "__no_serving_stats__.json"))
    monkeypatch.setenv("CONTENT_EMBEDDINGS_PATH", str(api_root / "models" / "content_embeddings.npz"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(api_root / "models" / "content_index.json"))
    monkeypatch.setenv("ONNX_MODEL_PATH", str(api_root / "models" / "ncf.onnx"))
    monkeypatch.setenv("METADATA_PATH", str(api_root / "models" / "metadata.json"))

    sys.path.insert(0, str(api_root))
    sys.modules.pop("app.main", None)
    sys.modules.pop("app.content", None)
    sys.modules.pop("app.rag", None)
    sys.modules.pop("app.seed_ranker", None)
    return importlib.import_module("app.main").app


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


def test_recommendations_filters_by_genre(monkeypatch):
    client = TestClient(load_app(monkeypatch))
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


def test_recommendations_filters_by_year_range(monkeypatch):
    client = TestClient(load_app(monkeypatch))

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


def test_recommendations_combined_filters_use_any_genre(monkeypatch):
    client = TestClient(load_app(monkeypatch))
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


def test_recommendations_returns_up_to_top_k(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    response = client.post("/recommendations", json={"seeds": [1, 2, 3]})

    assert response.status_code == 200
    items = response.json()["items"]
    assert 0 < len(items) <= 24


def test_recommendations_unmatchable_filter_returns_empty(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    response = client.post(
        "/recommendations",
        json={"seeds": [1, 2, 3], "year_min": 1700, "year_max": 1701},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
