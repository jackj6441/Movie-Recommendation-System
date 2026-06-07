"""Deterministic Seed Set / filter resolution for conversational RAG (v1, no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

MAX_GENRES = 3
MAX_SEEDS = 10
DEFAULT_GENRE_BOOTSTRAP_PER_GENRE = 3
DEFAULT_RECENCY_YEAR_MIN = 2005

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
YearAwareGenreSeedIdsFn = Callable[[str, int, int | None], list[int]]
GetTitleFn = Callable[[int], str]


@dataclass
class ChatContext:
    """Session context. ``explicit_seed_ids`` are user-visible; bootstrap seeds are not stored."""

    explicit_seed_ids: list[int] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    year_min: int | None = None
    year_max: int | None = None
    recency_opt_out: bool = False


@dataclass(frozen=True)
class ResolvedSeed:
    movie_id: int
    title: str


@dataclass(frozen=True)
class ResolveReady:
    context: ChatContext
    seed_movies: list[ResolvedSeed]
    ranking_seed_ids: list[int]
    resolve_reason: str


@dataclass(frozen=True)
class ResolveClarify:
    reason: str


@dataclass(frozen=True)
class ResolveDisambiguate:
    reason: str
    candidates: list[ResolvedSeed]
    context: ChatContext
    disambiguation_genre_options: tuple[str, ...] = ()
    pending_genres: tuple[str, ...] = ()


ResolveResult = ResolveReady | ResolveClarify | ResolveDisambiguate

PopularMovieIdsFn = Callable[[int], list[int]]


def resolve_context(
    *,
    message: str,
    genres: list[str] | None,
    prior: ChatContext | None,
    search_movies: SearchMoviesFn,
    genre_seed_ids: GenreSeedIdsFn,
    get_title: GetTitleFn,
    known_movie_ids: set[int] | None = None,
    seed_movie_ids: list[int] | None = None,
    seed_update_mode: str = "append",
    popular_movie_ids: PopularMovieIdsFn | None = None,
    known_genres: set[str] | None = None,
    genre_seed_ids_for_year: YearAwareGenreSeedIdsFn | None = None,
) -> ResolveResult:
    """Merge chips + message + session into the next ranker-ready context."""
    prior_context = prior or ChatContext()
    raw_genre_names = [genre.strip() for genre in (genres or []) if genre.strip()]
    chip_genres = normalize_genres(genres, known_genres)
    if raw_genre_names and not chip_genres:
        if not message.strip() and not prior_context.explicit_seed_ids:
            explicit_early = filter_known_seed_ids(seed_movie_ids, known_movie_ids)
            if not explicit_early:
                return ResolveClarify(reason="invalid_genre")

    explicit_ids = filter_known_seed_ids(seed_movie_ids, known_movie_ids)
    stripped = message.strip()
    if not explicit_ids and stripped:
        search_hit_ids = collect_message_search_hit_ids(
            message,
            search_movies,
            known_movie_ids,
        )
        if search_hit_ids:
            year_min, year_max = parse_year_bounds(
                message,
                prior_context.year_min,
                prior_context.year_max,
            )
            merged_genres = chip_genres or list(prior_context.genres)
            explicit_seed_ids = list(prior_context.explicit_seed_ids)
            year_min, year_max = apply_recency_default(
                year_min,
                year_max,
                explicit_seed_ids=explicit_seed_ids,
                recency_opt_out=prior_context.recency_opt_out,
            )
            genre_options = message_disambiguation_genre_options(stripped, known_genres)
            candidates = [
                ResolvedSeed(movie_id=movie_id, title=get_title(movie_id))
                for movie_id in search_hit_ids
            ]
            context = ChatContext(
                explicit_seed_ids=explicit_seed_ids,
                genres=merged_genres,
                year_min=year_min,
                year_max=year_max,
                recency_opt_out=prior_context.recency_opt_out,
            )
            return ResolveDisambiguate(
                reason="ambiguous_message",
                candidates=candidates,
                context=context,
                disambiguation_genre_options=genre_options,
                pending_genres=tuple(chip_genres),
            )

    parsed_ids = extract_movie_ids_from_message(message, search_movies, known_movie_ids)
    year_min, year_max = parse_year_bounds(message, prior_context.year_min, prior_context.year_max)

    merged_genres = chip_genres or list(prior_context.genres)
    if seed_movie_ids is not None and seed_update_mode == "replace":
        explicit_seed_ids = dedupe_preserve_order(explicit_ids, limit=MAX_SEEDS)
    else:
        seed_parts = list(prior_context.explicit_seed_ids)
        if explicit_ids:
            seed_parts.extend(explicit_ids)
        seed_parts.extend(parsed_ids)
        explicit_seed_ids = dedupe_preserve_order(seed_parts, limit=MAX_SEEDS)

    year_min, year_max = apply_recency_default(
        year_min,
        year_max,
        explicit_seed_ids=explicit_seed_ids,
        recency_opt_out=prior_context.recency_opt_out,
    )

    ranking_seed_ids = list(explicit_seed_ids)
    year_aware_genre_fn = genre_seed_ids_for_year or _wrap_genre_seed_ids(genre_seed_ids)
    if not ranking_seed_ids and merged_genres:
        ranking_seed_ids = bootstrap_seed_ids(
            merged_genres,
            year_aware_genre_fn,
            max_seeds=MAX_SEEDS,
            per_genre=DEFAULT_GENRE_BOOTSTRAP_PER_GENRE,
            year_min=year_min,
        )

    has_input_signal = bool(chip_genres) or bool(message.strip()) or bool(explicit_ids)
    if not ranking_seed_ids and not has_input_signal and not prior_context.explicit_seed_ids:
        return ResolveClarify(reason="missing_genre_and_title")

    if not ranking_seed_ids:
        candidates = build_disambiguation_candidates(
            message=message,
            merged_genres=merged_genres,
            search_movies=search_movies,
            genre_seed_ids=genre_seed_ids,
            get_title=get_title,
            popular_movie_ids=popular_movie_ids,
            known_movie_ids=known_movie_ids,
            year_min=year_min,
            genre_seed_ids_for_year=year_aware_genre_fn,
        )
        context = ChatContext(
            explicit_seed_ids=list(prior_context.explicit_seed_ids),
            genres=merged_genres,
            year_min=year_min,
            year_max=year_max,
            recency_opt_out=prior_context.recency_opt_out,
        )
        return ResolveDisambiguate(
            reason="no_resolvable_seeds",
            candidates=candidates,
            context=context,
            pending_genres=tuple(chip_genres),
        )

    context = ChatContext(
        explicit_seed_ids=explicit_seed_ids,
        genres=merged_genres,
        year_min=year_min,
        year_max=year_max,
        recency_opt_out=prior_context.recency_opt_out,
    )
    seed_movies = [
        ResolvedSeed(movie_id=mid, title=get_title(mid))
        for mid in explicit_seed_ids
    ]
    return ResolveReady(
        context=context,
        seed_movies=seed_movies,
        ranking_seed_ids=ranking_seed_ids,
        resolve_reason=infer_ready_resolve_reason(
            explicit_ids=explicit_ids,
            parsed_ids=parsed_ids,
            message=message,
            explicit_seed_ids=explicit_seed_ids,
            ranking_seed_ids=ranking_seed_ids,
            chip_genres=chip_genres,
        ),
    )


def infer_ready_resolve_reason(
    *,
    explicit_ids: list[int],
    parsed_ids: list[int],
    message: str,
    explicit_seed_ids: list[int],
    ranking_seed_ids: list[int],
    chip_genres: list[str],
) -> str:
    if explicit_ids:
        return "explicit_seed"
    if parsed_ids:
        if extract_title_candidates(message):
            return "quoted_title"
        return "whole_message_search"
    if chip_genres and not explicit_seed_ids and ranking_seed_ids:
        return "genre_bootstrap"
    if explicit_seed_ids:
        return "explicit_seed"
    return "genre_bootstrap"


def normalize_genres(
    genres: list[str] | None,
    known_genres: set[str] | None = None,
) -> list[str]:
    if not genres:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for genre in genres:
        name = genre.strip()
        if not name:
            continue
        if known_genres is not None:
            canonical = match_known_genre(name, known_genres)
            if canonical is None:
                continue
            name = canonical
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
        if len(ordered) >= MAX_GENRES:
            break
    return ordered


def match_known_genre(name: str, known_genres: set[str]) -> str | None:
    key = name.strip().lower()
    for genre in known_genres:
        if genre.lower() == key:
            return genre
    return None


def message_disambiguation_genre_options(
    message: str,
    known_genres: set[str] | None,
) -> tuple[str, ...]:
    if known_genres is None:
        return ()
    stripped = message.strip()
    if not stripped:
        return ()
    canonical = match_known_genre(stripped, known_genres)
    return (canonical,) if canonical else ()


def collect_message_search_hit_ids(
    message: str,
    search_movies: SearchMoviesFn,
    known_movie_ids: set[int] | None,
    *,
    limit: int = 10,
) -> list[int]:
    """Search hits from the whole message plus quoted / like-title fragments."""
    collected: list[int] = []
    stripped = message.strip()
    queries: list[str] = []
    if stripped:
        queries.append(stripped)
    for candidate in extract_title_candidates(message):
        if candidate not in queries:
            queries.append(candidate)
    for query in queries:
        for hit in search_movies(query):
            if known_movie_ids is not None and hit.movie_id not in known_movie_ids:
                continue
            if hit.movie_id not in collected:
                collected.append(hit.movie_id)
            if len(collected) >= limit:
                return collected
    return collected


def merge_genre_lists(
    *parts: list[str] | None,
    known_genres: set[str] | None = None,
) -> list[str]:
    combined: list[str] = []
    for part in parts:
        if part:
            combined.extend(part)
    return normalize_genres(combined, known_genres)


def resolve_genre_disambiguation_pick(
    *,
    prior: ChatContext,
    pending_genres: list[str],
    chip_genres: list[str],
    disambiguation_genre: str,
    genre_seed_ids: GenreSeedIdsFn,
    get_title: GetTitleFn,
    known_genres: set[str] | None = None,
    genre_seed_ids_for_year: YearAwareGenreSeedIdsFn | None = None,
) -> ResolveReady | ResolveClarify:
    """Apply a genre choice from message-vs-movie disambiguation."""
    if known_genres is not None:
        canonical = match_known_genre(disambiguation_genre, known_genres)
        if canonical is None:
            return ResolveClarify(reason="invalid_genre")
    else:
        canonical = disambiguation_genre.strip()
        if not canonical:
            return ResolveClarify(reason="invalid_genre")

    merged_genres = merge_genre_lists(
        prior.genres,
        pending_genres,
        chip_genres,
        [canonical],
        known_genres=known_genres,
    )
    explicit_seed_ids = list(prior.explicit_seed_ids)
    year_min, year_max = apply_recency_default(
        prior.year_min,
        prior.year_max,
        explicit_seed_ids=explicit_seed_ids,
        recency_opt_out=prior.recency_opt_out,
    )
    year_aware_genre_fn = genre_seed_ids_for_year or _wrap_genre_seed_ids(genre_seed_ids)
    ranking_seed_ids = list(explicit_seed_ids)
    if not ranking_seed_ids and merged_genres:
        ranking_seed_ids = bootstrap_seed_ids(
            merged_genres,
            year_aware_genre_fn,
            max_seeds=MAX_SEEDS,
            per_genre=DEFAULT_GENRE_BOOTSTRAP_PER_GENRE,
            year_min=year_min,
        )
    if not ranking_seed_ids:
        return ResolveClarify(reason="no_resolvable_seeds")

    context = ChatContext(
        explicit_seed_ids=explicit_seed_ids,
        genres=merged_genres,
        year_min=year_min,
        year_max=year_max,
        recency_opt_out=prior.recency_opt_out,
    )
    seed_movies = [
        ResolvedSeed(movie_id=movie_id, title=get_title(movie_id))
        for movie_id in explicit_seed_ids
    ]
    return ResolveReady(
        context=context,
        seed_movies=seed_movies,
        ranking_seed_ids=ranking_seed_ids,
        resolve_reason="genre_disambiguation_pick",
    )


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
    if not resolved:
        whole = message.strip()
        if whole:
            movie_id = resolve_title_candidate(whole, search_movies, known_movie_ids)
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


def _wrap_genre_seed_ids(genre_seed_ids: GenreSeedIdsFn) -> YearAwareGenreSeedIdsFn:
    def wrapped(genre: str, limit: int, year_min: int | None = None) -> list[int]:
        del year_min
        return genre_seed_ids(genre, limit)

    return wrapped


def apply_recency_default(
    year_min: int | None,
    year_max: int | None,
    *,
    explicit_seed_ids: list[int],
    recency_opt_out: bool,
) -> tuple[int | None, int | None]:
    if recency_opt_out or explicit_seed_ids:
        return year_min, year_max
    if year_min is not None or year_max is not None:
        return year_min, year_max
    return DEFAULT_RECENCY_YEAR_MIN, year_max


def bootstrap_seed_ids(
    genres: list[str],
    genre_seed_ids: YearAwareGenreSeedIdsFn,
    *,
    max_seeds: int,
    per_genre: int,
    year_min: int | None = None,
) -> list[int]:
    collected: list[int] = []
    for genre in genres:
        for movie_id in genre_seed_ids(genre, per_genre, year_min):
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


def build_disambiguation_candidates(
    *,
    message: str,
    merged_genres: list[str],
    search_movies: SearchMoviesFn,
    genre_seed_ids: GenreSeedIdsFn,
    get_title: GetTitleFn,
    popular_movie_ids: PopularMovieIdsFn | None,
    known_movie_ids: set[int] | None,
    limit: int = 10,
    year_min: int | None = None,
    genre_seed_ids_for_year: YearAwareGenreSeedIdsFn | None = None,
) -> list[ResolvedSeed]:
    collected: list[int] = []
    stripped = message.strip()
    if stripped:
        for hit in search_movies(stripped):
            if known_movie_ids is not None and hit.movie_id not in known_movie_ids:
                continue
            if hit.movie_id not in collected:
                collected.append(hit.movie_id)
            if len(collected) >= limit:
                break
    if not collected and merged_genres:
        year_aware_fn = genre_seed_ids_for_year or _wrap_genre_seed_ids(genre_seed_ids)
        for genre in merged_genres:
            for movie_id in year_aware_fn(genre, limit, year_min):
                if known_movie_ids is not None and movie_id not in known_movie_ids:
                    continue
                if movie_id not in collected:
                    collected.append(movie_id)
                if len(collected) >= limit:
                    break
            if len(collected) >= limit:
                break
    if not collected and popular_movie_ids is not None:
        for movie_id in popular_movie_ids(limit):
            if known_movie_ids is not None and movie_id not in known_movie_ids:
                continue
            if movie_id not in collected:
                collected.append(movie_id)
            if len(collected) >= limit:
                break
    return [
        ResolvedSeed(movie_id=movie_id, title=get_title(movie_id))
        for movie_id in collected[:limit]
    ]


def collect_seed_warnings(
    seed_movie_ids: list[int] | None,
    known_movie_ids: set[int],
) -> list[dict[str, int | str]]:
    if not seed_movie_ids:
        return []
    warnings: list[dict[str, int | str]] = []
    for movie_id in seed_movie_ids:
        if movie_id not in known_movie_ids:
            warnings.append({"code": "invalid_seed_movie_id", "movie_id": movie_id})
    return warnings


def filter_known_seed_ids(
    seed_movie_ids: list[int] | None,
    known_movie_ids: set[int] | None,
) -> list[int]:
    if not seed_movie_ids:
        return []
    ordered: list[int] = []
    for movie_id in seed_movie_ids:
        if known_movie_ids is not None and movie_id not in known_movie_ids:
            continue
        if movie_id not in ordered:
            ordered.append(movie_id)
        if len(ordered) >= MAX_SEEDS:
            break
    return ordered


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
