from pathlib import Path

from app import posters

SAMPLE_POSTERS = Path(__file__).resolve().parent / "fixtures" / "poster_urls.sample.json"


def test_load_poster_lookup_parses_sample():
    lookup = posters.load_poster_lookup(str(SAMPLE_POSTERS))
    assert lookup[1]["poster_url"].endswith(".jpg")
    assert "w185" in lookup[1]["poster_thumb_url"]


def test_enrich_movie_omits_fields_when_missing():
    payload = posters.enrich_movie(999, {"movie_id": 999, "title": "Unknown"}, {})
    assert payload == {"movie_id": 999, "title": "Unknown"}


def test_enrich_movie_adds_urls_when_present():
    lookup = posters.load_poster_lookup(str(SAMPLE_POSTERS))
    payload = posters.enrich_movie(1, {"movie_id": 1, "title": "Toy Story (1995)"}, lookup)
    assert "poster_url" in payload
    assert "poster_thumb_url" in payload
