"""Deterministic Seed Set / filter resolution for conversational RAG (v1, no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

MAX_GENRES = 3
MAX_SEEDS = 5
DEFAULT_GENRE_BOOTSTRAP_PER_GENRE = 3

_QUOTED_TITLE_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
_LIKE_TITLE_RE = re.compile(r"\blike\s+([^,.;!?]+)", re.IGNORECASE)
_DECADE_RE = re.compile(r"\b(?:the\s+)?(\d{2})\s*s\b", re.IGNORECASE)
_AFTER_YEAR_RE = re.compile(r"\bafter\s+(19\d{2}|20\d{2})\b", re.IGNORECASE)
_BEFORE_YEAR_RE = re.compile(r"\bbefore\s+(19\d{2}|20\d{2})\b", re.IGNORECASE)
_YEAR_RANGE_RE = re.compile(r"\b(19\d{2}|20\d{2})\s*[-–]\s*(19\d{2}|20\d{2})\b")
_SINGLE_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


class MovieSearchHit(Protocol):
    movie_id: int
    title: str


SearchMoviesFn = Callable[[str], list[MovieSearchHit]]
GenreSeedIdsFn = Callable[[str, int], list[int]]
GetTitleFn = Callable[[int], str]


@dataclass
class ChatContext:
    seed_ids: list[int] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    year_min: int | None = None
    year_max: int | None = None


@dataclass(frozen=True)
class ResolvedSeed:
    movie_id: int
    title: str


@dataclass(frozen=True)
class ResolveReady:
    context: ChatContext
    seed_movies: list[ResolvedSeed]


@dataclass(frozen=True)
class ResolveClarify:
    reason: str


ResolveResult = ResolveReady | ResolveClarify


def resolve_context(
    *,
    message: str,
    genres: list[str] | None,
    prior: ChatContext | None,
    search_movies: SearchMoviesFn,
    genre_seed_ids: GenreSeedIdsFn,
    get_title: GetTitleFn,
    known_movie_ids: set[int] | None = None,
) -> ResolveResult:
    """Merge chips + message + session into the next ranker-ready context."""
    prior_context = prior or ChatContext()
    chip_genres = normalize_genres(genres)
    parsed_ids = extract_movie_ids_from_message(message, search_movies, known_movie_ids)
    year_min, year_max = parse_year_bounds(message, prior_context.year_min, prior_context.year_max)

    merged_genres = chip_genres or list(prior_context.genres)
    seed_ids = dedupe_preserve_order(
        [*prior_context.seed_ids, *parsed_ids],
        limit=MAX_SEEDS,
    )

    if not seed_ids and merged_genres:
        seed_ids = bootstrap_seed_ids(
            merged_genres,
            genre_seed_ids,
            max_seeds=MAX_SEEDS,
            per_genre=DEFAULT_GENRE_BOOTSTRAP_PER_GENRE,
        )

    if not merged_genres and not parsed_ids and not prior_context.seed_ids:
        return ResolveClarify(reason="missing_genre_and_title")

    if not seed_ids:
        return ResolveClarify(reason="no_resolvable_seeds")

    context = ChatContext(
        seed_ids=seed_ids,
        genres=merged_genres,
        year_min=year_min,
        year_max=year_max,
    )
    seed_movies = [
        ResolvedSeed(movie_id=mid, title=get_title(mid))
        for mid in seed_ids
    ]
    return ResolveReady(context=context, seed_movies=seed_movies)


def normalize_genres(genres: list[str] | None) -> list[str]:
    if not genres:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for genre in genres:
        name = genre.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
        if len(ordered) >= MAX_GENRES:
            break
    return ordered


def extract_title_candidates(message: str) -> list[str]:
    candidates: list[str] = []
    for match in _QUOTED_TITLE_RE.finditer(message):
        value = match.group(1) or match.group(2)
        if value and value.strip():
            candidates.append(value.strip())
    for match in _LIKE_TITLE_RE.finditer(message):
        value = match.group(1).strip()
        if value:
            candidates.append(value)
    return candidates


def extract_movie_ids_from_message(
    message: str,
    search_movies: SearchMoviesFn,
    known_movie_ids: set[int] | None,
) -> list[int]:
    resolved: list[int] = []
    for candidate in extract_title_candidates(message):
        movie_id = resolve_title_candidate(candidate, search_movies, known_movie_ids)
        if movie_id is not None:
            resolved.append(movie_id)
    return dedupe_preserve_order(resolved, limit=MAX_SEEDS)


def resolve_title_candidate(
    candidate: str,
    search_movies: SearchMoviesFn,
    known_movie_ids: set[int] | None,
) -> int | None:
    query = candidate.strip().lower()
    if not query:
        return None
    hits = search_movies(candidate)
    for hit in hits:
        if known_movie_ids is not None and hit.movie_id not in known_movie_ids:
            continue
        if query in hit.title.lower():
            return hit.movie_id
    if hits:
        first = hits[0]
        if known_movie_ids is None or first.movie_id in known_movie_ids:
            return first.movie_id
    return None


def bootstrap_seed_ids(
    genres: list[str],
    genre_seed_ids: GenreSeedIdsFn,
    *,
    max_seeds: int,
    per_genre: int,
) -> list[int]:
    collected: list[int] = []
    for genre in genres:
        for movie_id in genre_seed_ids(genre, per_genre):
            if movie_id not in collected:
                collected.append(movie_id)
            if len(collected) >= max_seeds:
                return collected
    return collected


def parse_year_bounds(
    message: str,
    prior_min: int | None,
    prior_max: int | None,
) -> tuple[int | None, int | None]:
    year_min = prior_min
    year_max = prior_max

    decade_match = _DECADE_RE.search(message)
    if decade_match:
        decade = int(decade_match.group(1))
        century = 1900 if decade >= 30 else 2000
        base = century + decade
        return base, base + 9

    range_match = _YEAR_RANGE_RE.search(message)
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2))
        return min(start, end), max(start, end)

    after_match = _AFTER_YEAR_RE.search(message)
    if after_match:
        year_min = int(after_match.group(1))

    before_match = _BEFORE_YEAR_RE.search(message)
    if before_match:
        year_max = int(before_match.group(1))

    if year_min is None and year_max is None:
        years = [int(match.group(1)) for match in _SINGLE_YEAR_RE.finditer(message)]
        if len(years) == 1:
            year = years[0]
            return year, year

    return year_min, year_max


def dedupe_preserve_order(values: list[int], *, limit: int) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
        if len(ordered) >= limit:
            break
    return ordered
