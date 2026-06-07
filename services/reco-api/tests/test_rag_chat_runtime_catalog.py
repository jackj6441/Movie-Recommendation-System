"""R2: rag_chat accepts a single RuntimeCatalog seam."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app import rag_chat as rag_chat_service  # noqa: E402
from app.rag_resolve import ChatContext  # noqa: E402
from app.runtime_catalog import load_runtime_catalog  # noqa: E402


def _write_movies_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["movieId", "title", "genres"])
        writer.writerow([1, "Toy Story (1995)", "Animation|Comedy"])
        writer.writerow([2, "Jumanji (1995)", "Adventure|Comedy"])


def test_try_rank_passes_runtime_catalog_to_ranker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    movies = tmp_path / "movies.csv"
    _write_movies_csv(movies)
    catalog = load_runtime_catalog(
        movies_csv_path=movies,
        ratings_csv_path=tmp_path / "missing_ratings.csv",
        serving_stats_path=tmp_path / "missing_stats.json",
    )

    seen: dict[str, object] = {}

    def fake_rank_seed_set(request):
        seen["catalog"] = request.catalog
        raise rag_chat_service.seed_ranker.InvalidSeedsError("test")

    monkeypatch.setattr(rag_chat_service.seed_ranker, "rank_seed_set", fake_rank_seed_set)

    rag_chat_service.try_rank(
        [1],
        ChatContext(genres=["Comedy"]),
        shuffle=False,
        catalog=catalog,
    )

    assert seen["catalog"] is catalog
