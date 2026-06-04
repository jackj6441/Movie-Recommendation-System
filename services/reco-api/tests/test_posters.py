import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from conftest import _configure_test_env, _reload_app


def _poster_app(monkeypatch, repo_root: Path, api_root: Path, *, poster_urls: str, poster_meta: str | None = None):
    fixtures = api_root / "tests" / "fixtures"
    extra = {"POSTER_URLS_PATH": str(fixtures / poster_urls)}
    if poster_meta is not None:
        extra["POSTER_META_PATH"] = str(fixtures / poster_meta)
    _configure_test_env(monkeypatch, repo_root, api_root, **extra)
    return _reload_app(api_root)


def test_movie_search_includes_poster_fields_for_known_movie(monkeypatch, repo_root, api_root):
    client = TestClient(_poster_app(monkeypatch, repo_root, api_root, poster_urls="poster_urls.sample.json"))
    response = client.get("/movies/search", params={"q": "toy story"})
    assert response.status_code == 200
    items = response.json()
    toy_story = next(item for item in items if item["movie_id"] == 1)
    assert toy_story["poster_url"].startswith("https://image.tmdb.org/t/p/w500/")
    assert toy_story["poster_thumb_url"].startswith("https://image.tmdb.org/t/p/w185/")


def test_recommendations_include_poster_fields(monkeypatch, repo_root, api_root):
    client = TestClient(_poster_app(monkeypatch, repo_root, api_root, poster_urls="poster_urls.sample.json"))
    response = client.post("/recommendations", json={"seeds": [1], "shuffle": False})
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["seed_movies"]
    assert payload["seed_movies"][0]["movie_id"] == 1
    assert "poster_url" in payload["seed_movies"][0]


def test_healthz_reports_poster_coverage(monkeypatch, repo_root, api_root):
    client = TestClient(
        _poster_app(
            monkeypatch,
            repo_root,
            api_root,
            poster_urls="poster_urls.sample.json",
            poster_meta="poster_meta.sample.json",
        )
    )
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["poster_ok"] is True
    assert payload["poster_count"] > 0


def test_movie_search_omits_poster_when_lookup_missing(monkeypatch, repo_root, api_root):
    client = TestClient(_poster_app(monkeypatch, repo_root, api_root, poster_urls="poster_urls.empty.json"))
    response = client.get("/movies/search", params={"q": "toy"})
    assert response.status_code == 200
    for item in response.json():
        assert "poster_url" not in item
