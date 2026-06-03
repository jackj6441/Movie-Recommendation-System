import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(monkeypatch, *, poster_urls: str, poster_meta: str | None = None):
    repo_root = Path(__file__).resolve().parents[3]
    api_root = repo_root / "services" / "reco-api"
    fixtures = api_root / "tests" / "fixtures"

    monkeypatch.setenv("MOVIES_CSV_PATH", str(repo_root / "ml-latest-small" / "movies.csv"))
    monkeypatch.setenv("RATINGS_CSV_PATH", str(repo_root / "ml-latest-small" / "ratings.csv"))
    monkeypatch.setenv("SERVING_STATS_PATH", str(repo_root / "ml-latest-small" / "__no_serving_stats__.json"))
    monkeypatch.setenv("CONTENT_EMBEDDINGS_PATH", str(api_root / "models" / "content_embeddings.npz"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(api_root / "models" / "content_index.json"))
    monkeypatch.setenv("ONNX_MODEL_PATH", str(api_root / "models" / "ncf.onnx"))
    monkeypatch.setenv("METADATA_PATH", str(api_root / "models" / "metadata.json"))
    monkeypatch.setenv("POSTER_URLS_PATH", str(fixtures / poster_urls))
    if poster_meta is not None:
        monkeypatch.setenv("POSTER_META_PATH", str(fixtures / poster_meta))

    sys.path.insert(0, str(api_root))
    for module_name in ["app.main", "app.content", "app.posters", "app.rag", "app.seed_ranker", "app.metrics"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("app.main").app


def test_movie_search_includes_poster_fields_for_known_movie(monkeypatch):
    client = TestClient(load_app(monkeypatch, poster_urls="poster_urls.sample.json"))
    response = client.get("/movies/search", params={"q": "toy story"})
    assert response.status_code == 200
    items = response.json()
    toy_story = next(item for item in items if item["movie_id"] == 1)
    assert toy_story["poster_url"].startswith("https://image.tmdb.org/t/p/w500/")
    assert toy_story["poster_thumb_url"].startswith("https://image.tmdb.org/t/p/w185/")


def test_movie_search_omits_poster_fields_when_missing(monkeypatch):
    client = TestClient(load_app(monkeypatch, poster_urls="poster_urls.sample.json"))
    response = client.get("/movies/search", params={"q": "jumanji"})
    assert response.status_code == 200
    items = response.json()
    jumanji = next(item for item in items if item["movie_id"] == 2)
    assert set(jumanji.keys()) == {"movie_id", "title"}


def test_genre_seeds_include_poster_fields(monkeypatch):
    client = TestClient(load_app(monkeypatch, poster_urls="poster_urls.sample.json"))
    response = client.get("/genres/all/seeds", params={"limit": 50})
    assert response.status_code == 200
    seeds = response.json()["seeds"]
    toy_story = next(seed for seed in seeds if seed["movie_id"] == 1)
    assert "poster_url" in toy_story


def test_healthz_reports_poster_stats(monkeypatch):
    client = TestClient(
        load_app(
            monkeypatch,
            poster_urls="poster_urls.sample.json",
            poster_meta="poster_meta.sample.json",
        )
    )
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["poster_ok"] is True
    assert payload["poster_count"] == 1
    assert payload["poster_coverage"] == 0.0001
