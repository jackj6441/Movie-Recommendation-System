from pathlib import Path

from fastapi.testclient import TestClient

from app import movie_details
from conftest import _configure_test_env, _reload_app

SAMPLE_DETAILS = Path(__file__).resolve().parent / "fixtures" / "movie_details.sample.json"


def _details_app(
    monkeypatch,
    repo_root: Path,
    api_root: Path,
    *,
    poster_urls: str = "poster_urls.sample.json",
    movie_details_file: str = "movie_details.sample.json",
    movie_details_meta: str | None = "movie_details_meta.sample.json",
):
    fixtures = api_root / "tests" / "fixtures"
    extra = {
        "POSTER_URLS_PATH": str(fixtures / poster_urls),
        "MOVIE_DETAILS_PATH": str(fixtures / movie_details_file),
    }
    if movie_details_meta is not None:
        extra["MOVIE_DETAILS_META_PATH"] = str(fixtures / movie_details_meta)
    _configure_test_env(monkeypatch, repo_root, api_root, **extra)
    return _reload_app(api_root)


def test_load_details_lookup_parses_sample():
    lookup = movie_details.load_details_lookup(str(SAMPLE_DETAILS))
    assert lookup[1]["tmdb_id"] == 862
    assert "Woody" in lookup[1]["overview"]


def test_enrich_movie_adds_overview_and_watch_url():
    lookup = movie_details.load_details_lookup(str(SAMPLE_DETAILS))
    payload = movie_details.enrich_movie(
        1,
        {"movie_id": 1, "title": "Toy Story (1995)", "genres": ["Animation"]},
        lookup,
    )
    assert payload["overview"].startswith("Led by Woody")
    assert payload["watch_url"] == "https://www.themoviedb.org/movie/862"


def test_enrich_movie_omits_fields_when_missing():
    payload = movie_details.enrich_movie(999, {"movie_id": 999, "title": "Unknown"}, {})
    assert payload == {"movie_id": 999, "title": "Unknown"}


def test_recommendations_include_genres_overview_and_watch_url(monkeypatch, repo_root, api_root):
    client = TestClient(_details_app(monkeypatch, repo_root, api_root))
    response = client.post("/recommendations", json={"seeds": [1], "shuffle": False})
    assert response.status_code == 200
    payload = response.json()
    seed = payload["seed_movies"][0]
    assert seed["movie_id"] == 1
    assert "Animation" in seed["genres"]
    assert "overview" in seed
    assert seed["watch_url"] == "https://www.themoviedb.org/movie/862"


def test_healthz_reports_details_coverage(monkeypatch, repo_root, api_root):
    client = TestClient(_details_app(monkeypatch, repo_root, api_root))
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["details_ok"] is True
    assert payload["details_count"] > 0
