"""Seed-based ranking pipeline.

Encapsulates the shared logic used by both the recommendations and explanations
endpoints: validate seeds, build an anchor vector, score candidates, and return
a ranked list alongside similar-movie context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app import content

# Number of ranked items returned to the product UI. Sized so the results page
# can show 3 featured picks plus a poster grid and still survive client filters.
TOP_K = 24


class InvalidSeedsError(Exception):
    """Raised when the seed list is empty or no seeds survive content filtering."""


class ContentUnavailableError(Exception):
    """Raised when content embeddings cannot be retrieved for the validated seeds."""


@dataclass(frozen=True)
class Catalog:
    """Immutable snapshot of the movie catalog needed for ranking."""

    movie_titles: dict[int, str]
    popular_movie_ids: list[int]
    candidate_pool: int
    movie_genres: dict[int, list[str]] = field(default_factory=dict)
    movie_years: dict[int, int] = field(default_factory=dict)


@dataclass
class RankedItem:
    movie_id: int
    title: str
    content_score: float


@dataclass
class RankedList:
    items: list[RankedItem]
    seed_movie_ids: list[int]
    anchor_movie_id: int
    similar_movies: list[tuple[int, float]]  # (movie_id, similarity)


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec if norm == 0 else vec / norm


def _passes_filters(
    movie_id: int,
    catalog: Catalog,
    genre_set: set[str],
    year_min: Optional[int],
    year_max: Optional[int],
) -> bool:
    """Return True if a movie satisfies the genre (ANY) and year-range filters."""
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


def _build_candidate_ids(
    catalog: Catalog,
    exclude: set[int],
    shuffle: bool,
    genres: Optional[list[str]] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> list[int]:
    """Return content-indexed candidate movie IDs, excluding seeds.

    Without filters we score only the most popular slice of the catalog for
    speed. When any genre/year filter is active we widen the candidate base to
    the full catalog first so niche filters still surface real matches instead
    of going empty, then rank by seed similarity downstream.
    """
    ranked = catalog.popular_movie_ids if catalog.popular_movie_ids else sorted(catalog.movie_titles.keys())
    filters_active = bool(genres) or year_min is not None or year_max is not None

    if filters_active:
        seen = set(ranked)
        base = list(ranked) + [mid for mid in catalog.movie_titles.keys() if mid not in seen]
        genre_set = {g.lower() for g in genres} if genres else set()
        candidates = [
            mid
            for mid in base
            if mid not in exclude and _passes_filters(mid, catalog, genre_set, year_min, year_max)
        ]
    else:
        pool_size = min(catalog.candidate_pool * 3, len(ranked))
        candidates = [mid for mid in ranked[:pool_size] if mid not in exclude]

    candidates = content.filter_movie_ids(candidates)
    if shuffle:
        rng = np.random.default_rng()
        rng.shuffle(candidates)
        candidates = candidates[: catalog.candidate_pool]
    return candidates


def rank(
    seeds: list[int],
    shuffle: bool,
    catalog: Catalog,
    genres: Optional[list[str]] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> RankedList:
    """Score and rank candidate movies against a seed set using content embeddings.

    The anchor vector is the normalised mean of all valid seed embeddings.
    Candidates are scored by cosine similarity to that anchor vector.

    Raises:
        InvalidSeedsError: if no seeds are in the catalog or survive content filtering.
        ContentUnavailableError: if embeddings cannot be retrieved for valid seeds.
    """
    valid_seeds = [mid for mid in seeds if mid in catalog.movie_titles]
    valid_seeds = content.filter_movie_ids(valid_seeds)
    if not valid_seeds:
        raise InvalidSeedsError("no valid seeds after content filtering")

    seed_vectors = content.get_embeddings_for_movies(valid_seeds)
    if not seed_vectors:
        raise ContentUnavailableError("content embeddings unavailable for seeds")

    anchor_vec = _normalize(np.mean(seed_vectors, axis=0))
    anchor_movie_id = valid_seeds[0]

    candidate_ids = _build_candidate_ids(
        catalog,
        exclude=set(valid_seeds),
        shuffle=shuffle,
        genres=genres,
        year_min=year_min,
        year_max=year_max,
    )
    if not candidate_ids:
        return RankedList(
            items=[],
            seed_movie_ids=valid_seeds,
            anchor_movie_id=anchor_movie_id,
            similar_movies=[],
        )

    scores = np.array(
        content.get_similarity_scores_from_vector(anchor_vec, candidate_ids),
        dtype=np.float32,
    )
    top_indices = np.argsort(scores)[::-1][:TOP_K]
    items = [
        RankedItem(
            movie_id=int(candidate_ids[idx]),
            title=catalog.movie_titles.get(int(candidate_ids[idx]), f"Movie {candidate_ids[idx]}"),
            content_score=float(scores[idx]),
        )
        for idx in top_indices
    ]

    similar_movies: list[tuple[int, float]] = []
    try:
        similar_movies = list(content.get_similar(anchor_movie_id, topn=3))
    except Exception:
        similar_movies = []

    return RankedList(
        items=items,
        seed_movie_ids=valid_seeds,
        anchor_movie_id=anchor_movie_id,
        similar_movies=similar_movies,
    )
