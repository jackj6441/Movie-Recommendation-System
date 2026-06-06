"""Offline helpers that run the same Phase 1 fusion pipeline as reco-api serving."""

from __future__ import annotations

import csv
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

REPO_ROOT = Path(__file__).resolve().parents[1]
RECO_API_ROOT = REPO_ROOT / "services" / "reco-api"
MODELS_DIR = RECO_API_ROOT / "models"

if TYPE_CHECKING:
    from app.artifact_bundle import ArtifactBundle

_APP_MODULES = (
    "app.artifact_bundle",
    "app.content",
    "app.artifacts",
    "app.ltr",
    "app.fusion",
    "app.retrievers.content_retriever",
    "app.retrievers.svd",
    "app.retrievers.item_cf",
    "app.retrievers.popularity",
    "app.seed_ranker",
)


def _ensure_api_on_path() -> None:
    api_path = str(RECO_API_ROOT)
    if api_path not in sys.path:
        sys.path.insert(0, api_path)


def _reload_ranking_modules() -> None:
    _ensure_api_on_path()
    for module_name in _APP_MODULES:
        sys.modules.pop(module_name, None)


def configure_artifact_paths(
    *,
    content_embeddings: str | Path | None = None,
    content_index: str | Path | None = None,
    item_factors_svd: str | Path | None = None,
    item_neighbors: str | Path | None = None,
    fusion_weights: str | Path | None = None,
    ltr_model: str | Path | None = None,
    ltr_meta: str | Path | None = None,
) -> ArtifactBundle:
    """Load serving artifacts into an in-memory bundle and install it as the default."""
    _reload_ranking_modules()
    artifact_bundle = importlib.import_module("app.artifact_bundle")
    artifact_bundle.reset_default_bundle()
    bundle = artifact_bundle.load_artifact_bundle(
        content_embeddings_path=str(content_embeddings or MODELS_DIR / "content_embeddings.npz"),
        content_index_path=str(content_index or MODELS_DIR / "content_index.json"),
        item_factors_svd_path=str(item_factors_svd or MODELS_DIR / "item_factors_svd.npz"),
        item_neighbors_path=str(item_neighbors or MODELS_DIR / "item_neighbors.json"),
        fusion_weights_path=str(fusion_weights or MODELS_DIR / "fusion_weights.json"),
        ltr_model_path=str(ltr_model or MODELS_DIR / "ltr_model.txt"),
        ltr_meta_path=str(ltr_meta or MODELS_DIR / "ltr_meta.json"),
    )
    artifact_bundle.set_default_bundle(bundle)
    return bundle


@dataclass(frozen=True)
class EvalCatalog:
    movie_titles: dict[int, str]
    popular_movie_ids: list[int]
    movie_popularity: dict[int, int]


def load_eval_catalog(
    movies_csv: str | Path,
    serving_stats_json: str | Path | None = None,
    ratings_csv: str | Path | None = None,
) -> EvalCatalog:
    """Build catalog metadata aligned with the served movie id set."""
    movie_titles: dict[int, str] = {}
    with open(movies_csv, newline="", encoding="utf-8") as csvfile:
        for row in csv.DictReader(csvfile):
            movie_id = int(row.get("movieId", "0"))
            title = (row.get("title") or "").strip()
            if movie_id and title:
                movie_titles[movie_id] = title

    popular_movie_ids: list[int] = []
    movie_popularity: dict[int, int] = {}
    stats_path = Path(serving_stats_json) if serving_stats_json else None
    if stats_path and stats_path.exists():
        with open(stats_path, encoding="utf-8") as stats_file:
            stats = json.load(stats_file)
        movie_popularity = {
            int(key): int(value) for key, value in stats.get("movie_popularity", {}).items()
        }
        popular_movie_ids = [int(mid) for mid in stats.get("popular_movie_ids", [])]

    if not popular_movie_ids and ratings_csv:
        import pandas as pd

        counts = pd.read_csv(ratings_csv, usecols=["movieId"])["movieId"].astype(int).value_counts()
        catalog_ids = set(movie_titles)
        movie_popularity = {
            int(mid): int(cnt) for mid, cnt in counts.items() if int(mid) in catalog_ids
        }
        popular_movie_ids = [
            int(mid) for mid in counts.sort_values(ascending=False).index if int(mid) in catalog_ids
        ]

    if not popular_movie_ids:
        popular_movie_ids = sorted(
            movie_popularity,
            key=lambda movie_id: movie_popularity[movie_id],
            reverse=True,
        )

    return EvalCatalog(
        movie_titles=movie_titles,
        popular_movie_ids=popular_movie_ids,
        movie_popularity=movie_popularity,
    )


def rank_seed_set(
    seed_ids: list[int],
    catalog: EvalCatalog,
    *,
    fusion_weights: dict[str, float] | None = None,
    top_k: int = 24,
) -> list[int]:
    """Return ranked movie ids for a seed set using the serving fusion pipeline."""
    _ensure_api_on_path()
    seed_ranker = importlib.import_module("app.seed_ranker")
    serving_catalog = seed_ranker.Catalog(
        movie_titles=catalog.movie_titles,
        popular_movie_ids=catalog.popular_movie_ids,
        candidate_pool=500,
        movie_popularity=catalog.movie_popularity,
    )
    try:
        result = seed_ranker.rank(
            seed_ids,
            shuffle=False,
            catalog=serving_catalog,
            fusion_weights=fusion_weights,
            top_k=top_k,
        )
    except (seed_ranker.InvalidSeedsError, seed_ranker.ContentUnavailableError):
        return []
    return [item.movie_id for item in result.items]
