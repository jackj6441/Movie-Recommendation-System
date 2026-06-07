"""Seed-based ranking pipeline.

Orchestrates four retrievers (content, SVD, item-CF, popularity), merges candidates,
and ranks with Phase 1 fusion or Phase 2 LightGBM Lambdarank.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from app.artifact_bundle import get_default_bundle
from app.fusion import CANDIDATE_CAP, CHANNELS, feature_rows, fuse, merge_candidate_ids
from app import ltr as ltr_ranker
from app.retrievers import content_retriever, item_cf, popularity, svd

if TYPE_CHECKING:
    from app.runtime_catalog import RuntimeCatalog

TOP_K = 24


class InvalidSeedsError(Exception):
    """Raised when the seed list is empty or no seeds survive content filtering."""


class ContentUnavailableError(Exception):
    """Raised when content embeddings cannot be retrieved for the validated seeds."""


@dataclass(frozen=True)
class RankFilters:
    """Optional ranking constraints applied after candidate generation."""

    genres: Optional[list[str]] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None


@dataclass(frozen=True)
class RankRequest:
    """Ranker-owned request shape for turning a Seed Set into a Ranked List."""

    seed_movie_ids: list[int]
    catalog: RuntimeCatalog
    filters: RankFilters = field(default_factory=RankFilters)
    top_k: int = TOP_K
    fusion_weights: Optional[dict[str, float]] = None
    ranking_mode: Optional[str] = None
    shuffle: bool = False


@dataclass
class RankedItem:
    movie_id: int
    title: str
    content_score: float
    fusion_score: float
    channel_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class RankedList:
    items: list[RankedItem]
    seed_movie_ids: list[int]
    anchor_movie_id: int
    similar_movies: list[tuple[int, float]]
    ranking_mode: str = "multi_retriever_fusion"

    def explanation_topk(self) -> list[dict[str, Any]]:
        """Explanation endpoint rows: content-only vs fusion final scores per item."""
        return [
            {
                "movie_id": item.movie_id,
                "title": item.title,
                "content": item.content_score,
                "final": item.fusion_score,
            }
            for item in self.items
        ]


def resolve_ranking_mode() -> str:
    """Return active ranker: ``ltr`` only when model is loaded and env requests it."""
    mode = os.getenv("RANKING_MODE", "fusion").strip().lower()
    if mode == "ltr" and ltr_ranker.ltr_available():
        return "ltr"
    return "fusion"


def active_ranking_mode_label() -> str:
    if resolve_ranking_mode() == "ltr":
        return "multi_retriever_ltr"
    return "multi_retriever_fusion"


def collect_channel_hits(
    valid_seeds: list[int],
    exclude: set[int],
    catalog: RuntimeCatalog,
) -> dict[str, list[tuple[int, float]]]:
    return {
        "content": content_retriever.retrieve(valid_seeds, exclude),
        "svd": svd.retrieve(valid_seeds, exclude),
        "item_cf": item_cf.retrieve(valid_seeds, exclude),
        "pop": popularity.retrieve(
            catalog.popular_movie_ids,
            catalog.movie_popularity,
            exclude,
        ),
    }


def _passes_filters(
    movie_id: int,
    catalog: RuntimeCatalog,
    genre_set: set[str],
    year_min: Optional[int],
    year_max: Optional[int],
) -> bool:
    if genre_set:
        movie_genre_list = catalog.movie_genres.get(movie_id, [])
        if not any(g.lower() in genre_set for g in movie_genre_list):
            return False
    if year_min is not None or year_max is not None:
        year = catalog.movie_years.get(movie_id)
        if year is None:
            return False
        if year_min is not None and year < year_min:
            return False
        if year_max is not None and year > year_max:
            return False
    return True


def _filter_candidate_ids(
    candidate_ids: list[int],
    catalog: RuntimeCatalog,
    genre_set: set[str],
    year_min: Optional[int],
    year_max: Optional[int],
) -> list[int]:
    if not genre_set and year_min is None and year_max is None:
        return candidate_ids
    return [
        movie_id
        for movie_id in candidate_ids
        if _passes_filters(movie_id, catalog, genre_set, year_min, year_max)
    ]


def _candidate_cap(catalog: RuntimeCatalog, filters: RankFilters) -> int:
    has_filters = bool(filters.genres) or filters.year_min is not None or filters.year_max is not None
    if has_filters:
        return catalog.candidate_pool
    return CANDIDATE_CAP


def rank_seed_set(request: RankRequest) -> RankedList:
    """Run multi-retriever retrieval then fusion or LTR scoring."""
    catalog = request.catalog
    bundle = get_default_bundle()
    content_artifacts = bundle.content
    valid_seeds = [mid for mid in request.seed_movie_ids if mid in catalog.movie_titles]
    valid_seeds = content_artifacts.filter_movie_ids(valid_seeds)
    if not valid_seeds:
        raise InvalidSeedsError("no valid seeds after content filtering")

    if not content_artifacts.get_embeddings_for_movies(valid_seeds):
        raise ContentUnavailableError("content embeddings unavailable for seeds")

    exclude = set(valid_seeds)
    anchor_movie_id = valid_seeds[0]
    channel_hits = collect_channel_hits(valid_seeds, exclude, catalog)
    filters = request.filters

    merged_ids = merge_candidate_ids(
        channel_hits,
        cap=_candidate_cap(catalog, filters),
    )
    genre_set = {g.lower() for g in filters.genres} if filters.genres else set()
    filtered_ids = _filter_candidate_ids(
        merged_ids,
        catalog,
        genre_set,
        filters.year_min,
        filters.year_max,
    )

    if not filtered_ids:
        return RankedList(
            items=[],
            seed_movie_ids=valid_seeds,
            anchor_movie_id=anchor_movie_id,
            similar_movies=[],
            ranking_mode=active_ranking_mode_label(),
        )

    content_raw = {mid: score for mid, score in channel_hits["content"]}
    mode = request.ranking_mode or resolve_ranking_mode()
    scored: list[tuple[int, float, dict[str, float]]]

    if mode == "ltr":
        rows = feature_rows(filtered_ids, channel_hits)
        scored = ltr_ranker.score_candidates(rows)
        if not scored:
            mode = "fusion"
            weights = request.fusion_weights if request.fusion_weights is not None else dict(bundle.fusion.weights)
            scored = fuse(filtered_ids, channel_hits, weights)
    else:
        weights = request.fusion_weights if request.fusion_weights is not None else dict(bundle.fusion.weights)
        scored = fuse(filtered_ids, channel_hits, weights)

    if request.shuffle and scored:
        random.shuffle(scored)

    items: list[RankedItem] = []
    for movie_id, final_score, breakdown in scored[: request.top_k]:
        items.append(
            RankedItem(
                movie_id=movie_id,
                title=catalog.movie_titles.get(movie_id, f"Movie {movie_id}"),
                content_score=float(content_raw.get(movie_id, 0.0)),
                fusion_score=float(final_score),
                channel_scores={channel: float(breakdown[channel]) for channel in CHANNELS},
            )
        )

    similar_movies: list[tuple[int, float]] = []
    try:
        similar_movies = list(content_artifacts.get_similar(anchor_movie_id, topn=3))
    except Exception:
        similar_movies = []

    label = "multi_retriever_ltr" if mode == "ltr" else "multi_retriever_fusion"
    return RankedList(
        items=items,
        seed_movie_ids=valid_seeds,
        anchor_movie_id=anchor_movie_id,
        similar_movies=similar_movies,
        ranking_mode=label,
    )
