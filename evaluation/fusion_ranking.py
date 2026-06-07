"""Offline helpers that run the same Phase 1 fusion pipeline as reco-api serving."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

REPO_ROOT = Path(__file__).resolve().parents[1]
RECO_API_ROOT = REPO_ROOT / "services" / "reco-api"
MODELS_DIR = RECO_API_ROOT / "models"

if TYPE_CHECKING:
    from app.artifact_bundle import ArtifactBundle
    from app.runtime_catalog import RuntimeCatalog

_APP_MODULES = (
    "app.artifact_bundle",
    "app.runtime_catalog",
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
    sys.modules.pop("app.retrievers", None)


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


def __getattr__(name: str):
    if name in ("EvalCatalog", "RuntimeCatalog"):
        _ensure_api_on_path()
        return importlib.import_module("app.runtime_catalog").RuntimeCatalog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def load_eval_catalog(
    movies_csv: str | Path,
    serving_stats_json: str | Path | None = None,
    ratings_csv: str | Path | None = None,
) -> RuntimeCatalog:
    """Build catalog metadata aligned with the served movie id set."""
    _ensure_api_on_path()
    runtime_catalog_mod = importlib.import_module("app.runtime_catalog")
    missing = Path("__missing_eval_artifact__")
    return runtime_catalog_mod.load_runtime_catalog(
        movies_csv_path=movies_csv,
        serving_stats_path=serving_stats_json if serving_stats_json is not None else missing,
        ratings_csv_path=ratings_csv if ratings_csv is not None else missing,
        candidate_pool=500,
    )


def rank_seed_set(
    seed_ids: list[int],
    catalog: RuntimeCatalog,
    *,
    fusion_weights: dict[str, float] | None = None,
    top_k: int = 24,
) -> list[int]:
    """Return ranked movie ids for a seed set using the serving fusion pipeline."""
    _ensure_api_on_path()
    seed_ranker = importlib.import_module("app.seed_ranker")
    try:
        result = seed_ranker.rank_seed_set(
            seed_ranker.RankRequest(
                seed_movie_ids=seed_ids,
                catalog=catalog,
                top_k=top_k,
                fusion_weights=fusion_weights,
                shuffle=False,
            )
        )
    except (seed_ranker.InvalidSeedsError, seed_ranker.ContentUnavailableError):
        return []
    return [item.movie_id for item in result.items]
