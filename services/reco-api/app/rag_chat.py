"""Conversational RAG chat turns with SSE streaming and deterministic ranking."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import Iterator
from typing import Any, Callable

from app import metrics, seed_ranker
from app.rag_catalog import CatalogServices
from app.rag_evidence import RAG_CHAT_VERSION, build_evidence
from app.rag_resolve import (
    ChatContext,
    ResolveClarify,
    ResolveDisambiguate,
    ResolveReady,
    collect_seed_warnings,
    normalize_genres,
    resolve_context,
    resolve_genre_disambiguation_pick,
)
from app.rag_session import ChatSession, SessionStore
from app.seed_ranker import RankedList

logger = logging.getLogger(__name__)

RAG_CHAT_PROMPT_VERSION = "rag-chat-v1"
CHAT_TOP_K = 10
EXTERNAL_PROVIDER_TIMEOUT_SECONDS = 8

SUPPORTED_CHAT_PROVIDERS = {
    "mock",
    "mock_sse_slow",
    "mock_timeout",
    "mock_provider_error",
    "disabled",
    "external",
}


def format_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def clarification_copy(reason: str) -> str:
    if reason == "missing_genre_and_title":
        return (
            "To get recommendations, pick up to three genres below or tell me a movie you like "
            '(for example, "Toy Story").'
        )
    if reason == "no_resolvable_seeds":
        return (
            "I could not anchor recommendations to any movies yet. Try a genre chip or name a "
            "specific title."
        )
    if reason == "invalid_genre":
        return (
            "I did not recognize those genre chips. Pick from the supported genres below, "
            "or name a movie you like."
        )
    if reason == "empty_recommendations":
        return (
            "No recommendations matched your current filters. Try removing the year filter "
            "or selecting fewer genres."
        )
    return "Tell me a genre or a movie you enjoy and I will find recommendations."


def disambiguation_copy(reason: str) -> str:
    if reason == "ambiguous_message":
        return (
            "Your message could mean a genre or specific movies. Pick a genre below, "
            "or select 1–5 movies as your Seed Set—these are possible matches, not your "
            "final recommendations."
        )
    return (
        "I could not lock onto a starting movie yet. These are not your final recommendations—"
        "they are possible matches. Pick 1–5 movies to use as your Seed Set."
    )


def deterministic_assistant_copy(evidence: dict[str, Any]) -> str:
    seeds = evidence.get("seed_movies", [])
    seed_titles = ", ".join(item["title"] for item in seeds[:3])
    top = evidence.get("top_items", [])
    if not top:
        return (
            f"Based on your seeds ({seed_titles}), I could not find movies that match your filters. "
            "Try broadening genres or the year range."
        )
    lead = top[0]["title"]
    return (
        f"Based on your Seed Set ({seed_titles}), here are picks led by {lead}. "
        "They align with your seeds through content similarity and fusion ranking signals."
    )


def stream_provider_tokens(
    evidence: dict[str, Any],
    *,
    provider: str,
) -> tuple[str, str]:
    """Return (full_text, explanation_source)."""
    if provider in {"mock_timeout", "mock_provider_error", "disabled"}:
        return deterministic_assistant_copy(evidence), "deterministic_fallback"
    if provider == "external" and not os.getenv("RAG_PROVIDER_API_KEY"):
        return deterministic_assistant_copy(evidence), "deterministic_fallback"

    text = _mock_stream_text(evidence, provider=provider)
    return text, "rag"


def iter_text_chunks(text: str, *, provider: str) -> Iterator[str]:
    if provider == "mock_sse_slow":
        for char in text:
            yield char
        return
    words = text.split(" ")
    for index, word in enumerate(words):
        yield word if index == 0 else f" {word}"


def _mock_stream_text(evidence: dict[str, Any], *, provider: str) -> str:
    del provider
    return deterministic_assistant_copy(evidence)


def recommendations_payload(
    rank_result: RankedList,
    *,
    model_version: str,
    movie_payload_fn: Callable[[int], dict[str, Any]],
) -> dict[str, Any]:
    capped_items = rank_result.items[:CHAT_TOP_K]
    return {
        "items": [
            movie_payload_fn(
                item.movie_id,
                score=item.fusion_score,
            )
            for item in capped_items
        ],
        "seed_movies": [movie_payload_fn(mid) for mid in rank_result.seed_movie_ids],
        "anchor_source": "seed",
        "model_version": model_version,
        "ranking_mode": rank_result.ranking_mode,
    }


def disambiguation_candidates_payload(
    resolved: ResolveDisambiguate,
    *,
    catalog_services: CatalogServices,
    movie_payload_fn: Callable[..., dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in resolved.candidates:
        payload = movie_payload_fn(candidate.movie_id)
        genres = catalog_services.movie_genres.get(candidate.movie_id)
        if genres:
            payload["genres"] = list(genres)
        rows.append(payload)
    return rows


def visible_context_payload(
    context: ChatContext,
    services: CatalogServices | None = None,
    *,
    ready: ResolveReady | None = None,
) -> dict[str, Any]:
    if ready is not None:
        seeds = [
            {"movie_id": seed.movie_id, "title": seed.title}
            for seed in ready.seed_movies
        ]
    elif services is not None:
        seeds = [
            {"movie_id": mid, "title": services.get_title(mid)}
            for mid in context.explicit_seed_ids
        ]
    else:
        seeds = [{"movie_id": mid, "title": f"Movie {mid}"} for mid in context.explicit_seed_ids]
    return {
        "seeds": seeds,
        "genres": list(context.genres),
        "year_min": context.year_min,
        "year_max": context.year_max,
        "recency_opt_out": context.recency_opt_out,
    }


def context_from_chat_context(context: ChatContext, services: CatalogServices) -> dict[str, Any]:
    return visible_context_payload(context, services)


def context_payload(ready: ResolveReady) -> dict[str, Any]:
    return visible_context_payload(ready.context, ready=ready)


def run_chat_turn_sse(
    *,
    session_store: SessionStore,
    catalog_services: CatalogServices,
    catalog: seed_ranker.Catalog,
    model_version: str,
    movie_payload_fn: Callable[..., dict[str, Any]],
    message: str,
    genres: list[str] | None,
    session_id: str | None,
    shuffle: bool,
    seed_movie_ids: list[int] | None = None,
    seed_update_mode: str = "append",
    reset_context: bool = False,
    clear_year_bounds: bool = False,
    year_min: int | None = None,
    year_max: int | None = None,
    disambiguation_genre: str | None = None,
) -> Iterator[str]:
    turn_id = str(uuid.uuid4())
    provider = os.getenv("RAG_PROVIDER", "mock").strip()
    started_at = time.perf_counter()

    session = session_store.get(session_id) if session_id else None
    if session is None:
        session = session_store.create()

    if reset_context:
        session.context = ChatContext()
    if clear_year_bounds:
        session.context = ChatContext(
            explicit_seed_ids=list(session.context.explicit_seed_ids),
            genres=list(session.context.genres),
            year_min=None,
            year_max=None,
            recency_opt_out=True,
        )
    elif year_min is not None or year_max is not None:
        session.context = ChatContext(
            explicit_seed_ids=list(session.context.explicit_seed_ids),
            genres=list(session.context.genres),
            year_min=year_min,
            year_max=year_max,
            recency_opt_out=False,
        )

    session_store.append_message(session, "user", message, turn_id=turn_id)
    search_fn, genre_fn, title_fn = catalog_services.as_resolve_hooks()
    known_genres = catalog_services.known_genres or None
    genre_seed_ids_for_year = lambda genre, limit, year_min=None: catalog_services.genre_seed_ids(
        genre,
        limit,
        year_min=year_min,
    )
    if disambiguation_genre:
        resolved = resolve_genre_disambiguation_pick(
            prior=session.context,
            pending_genres=list(session.pending_genres),
            chip_genres=normalize_genres(genres, known_genres),
            disambiguation_genre=disambiguation_genre,
            genre_seed_ids=genre_fn,
            get_title=title_fn,
            known_genres=known_genres,
            genre_seed_ids_for_year=genre_seed_ids_for_year,
        )
        session.pending_genres = []
    else:
        resolved = resolve_context(
            message=message,
            genres=genres,
            prior=session.context,
            search_movies=search_fn,
            genre_seed_ids=genre_fn,
            get_title=title_fn,
            known_movie_ids=catalog_services.known_movie_ids(),
            seed_movie_ids=seed_movie_ids,
            seed_update_mode=seed_update_mode,
            popular_movie_ids=catalog_services.popular_movie_ids,
            known_genres=known_genres,
            genre_seed_ids_for_year=genre_seed_ids_for_year,
        )
    warnings = collect_seed_warnings(seed_movie_ids, catalog_services.known_movie_ids())

    if isinstance(resolved, ResolveDisambiguate):
        assistant_message = disambiguation_copy(resolved.reason)
        session.context = resolved.context
        session.pending_genres = list(resolved.pending_genres)
        session_store.save(session)
        session_store.append_message(session, "assistant", assistant_message, turn_id=turn_id)
        final_payload = _base_final_payload(
            session=session,
            turn_id=turn_id,
            model_version=model_version,
            needs_clarification=True,
            needs_disambiguation=True,
            clarification_reason=resolved.reason,
        )
        final_payload.update({
            "disambiguation_candidates": disambiguation_candidates_payload(
                resolved,
                catalog_services=catalog_services,
                movie_payload_fn=movie_payload_fn,
            ),
            "context": context_from_chat_context(session.context, catalog_services),
            "recommendations": None,
            "assistant_message": assistant_message,
        })
        if resolved.disambiguation_genre_options:
            final_payload["disambiguation_genre_options"] = list(
                resolved.disambiguation_genre_options,
            )
        if resolved.pending_genres:
            final_payload["pending_genres"] = list(resolved.pending_genres)
        attach_warnings(final_payload, warnings)
        maybe_attach_debug(
            final_payload,
            resolve_outcome="disambiguation",
            resolved=resolved,
            raw_genres=genres,
        )
        metrics.record_rag_chat_turn("disambiguation", resolved.reason)
        metrics.record_disambiguation_candidate_count(len(resolved.candidates))
        log_chat_turn(session.session_id, turn_id, "disambiguation", started_at)
        yield format_sse("final", final_payload)
        return

    if isinstance(resolved, ResolveClarify):
        assistant_message = clarification_copy(resolved.reason)
        for chunk in iter_text_chunks(assistant_message, provider="mock"):
            yield format_sse("token", {"delta": chunk})
        session.context = ChatContext(
            explicit_seed_ids=list(session.context.explicit_seed_ids),
            genres=normalize_session_genres(genres, session.context),
            year_min=session.context.year_min,
            year_max=session.context.year_max,
            recency_opt_out=session.context.recency_opt_out,
        )
        session_store.save(session)
        session_store.append_message(session, "assistant", assistant_message, turn_id=turn_id)
        final_payload = _base_final_payload(
            session=session,
            turn_id=turn_id,
            model_version=model_version,
            needs_clarification=True,
            needs_disambiguation=False,
            clarification_reason=resolved.reason,
        )
        final_payload.update({
            "context": session_context_api(session, catalog_services),
            "recommendations": None,
            "assistant_message": assistant_message,
        })
        attach_warnings(final_payload, warnings)
        maybe_attach_debug(
            final_payload,
            resolve_outcome="clarify",
            resolved=resolved,
            raw_genres=genres,
        )
        metrics.record_rag_chat_turn("clarify", resolved.reason)
        log_chat_turn(session.session_id, turn_id, "clarify", started_at)
        yield format_sse("final", final_payload)
        return

    assert isinstance(resolved, ResolveReady)
    session.context = resolved.context
    session_store.save(session)

    rank_result, rank_error = try_rank(
        resolved.ranking_seed_ids,
        resolved.context,
        shuffle=shuffle,
        catalog=catalog,
    )
    recommendations = None
    evidence: dict[str, Any] | None = None
    chat_fallback_reason: str | None = None

    if rank_error == "content_unavailable":
        metrics.record_rag_chat_turn("error", rank_error)
        final_payload = _base_final_payload(
            session=session,
            turn_id=turn_id,
            model_version=model_version,
            needs_clarification=False,
            needs_disambiguation=False,
        )
        final_payload.update({
            "context": context_payload(resolved),
            "recommendations": None,
            "assistant_message": "Content embeddings are unavailable right now.",
            "explanation_source": "deterministic_fallback",
            "rank_error": rank_error,
        })
        maybe_attach_debug(
            final_payload,
            resolve_outcome="error",
            resolved=resolved,
            raw_genres=genres,
            ranking_mode=seed_ranker.active_ranking_mode_label(),
        )
        log_chat_turn(session.session_id, turn_id, "error", started_at)
        yield format_sse("final", final_payload)
        return

    if rank_result is not None and rank_result.items:
        seed_titles = {mid: catalog_services.get_title(mid) for mid in rank_result.seed_movie_ids}
        evidence = build_evidence(rank_result, seed_titles=seed_titles)
        recommendations = recommendations_payload(
            rank_result,
            model_version=model_version,
            movie_payload_fn=movie_payload_fn,
        )

    if rank_result is not None and not rank_result.items:
        assistant_message = clarification_copy("empty_recommendations")
        for chunk in iter_text_chunks(assistant_message, provider="mock"):
            yield format_sse("token", {"delta": chunk})
        session_store.append_message(session, "assistant", assistant_message, turn_id=turn_id)
        empty_payload = _base_final_payload(
            session=session,
            turn_id=turn_id,
            model_version=model_version,
            needs_clarification=True,
            needs_disambiguation=False,
            clarification_reason="empty_recommendations",
        )
        empty_payload.update({
            "context": context_payload(resolved),
            "recommendations": recommendations_payload(
                rank_result,
                model_version=model_version,
                movie_payload_fn=movie_payload_fn,
            ),
            "assistant_message": assistant_message,
            "explanation_source": "rag",
        })
        attach_warnings(empty_payload, warnings)
        maybe_attach_debug(
            empty_payload,
            resolve_outcome="clarify",
            resolved=resolved,
            raw_genres=genres,
            ranking_mode=rank_result.ranking_mode if rank_result else None,
        )
        metrics.record_rag_chat_turn("clarify", "empty_recommendations")
        log_chat_turn(session.session_id, turn_id, "clarify", started_at)
        yield format_sse("final", empty_payload)
        return

    if evidence is None:
        evidence = {"seed_movies": context_payload(resolved)["seeds"], "top_items": []}

    if provider not in SUPPORTED_CHAT_PROVIDERS:
        provider = "disabled"

    try:
        if provider == "mock_timeout":
            raise ProviderTimeoutError
        if provider == "mock_provider_error":
            raise ProviderError
        assistant_message, explanation_source = stream_provider_tokens(evidence, provider=provider)
    except ProviderTimeoutError:
        assistant_message = deterministic_assistant_copy(evidence)
        explanation_source = "deterministic_fallback"
        chat_fallback_reason = "provider_timeout"
    except ProviderError:
        assistant_message = deterministic_assistant_copy(evidence)
        explanation_source = "deterministic_fallback"
        chat_fallback_reason = "provider_error"

    stream_provider = "mock_sse_slow" if provider == "mock_sse_slow" else "mock"
    for chunk in iter_text_chunks(assistant_message, provider=stream_provider):
        yield format_sse("token", {"delta": chunk})

    session_store.append_message(session, "assistant", assistant_message, turn_id=turn_id)
    final_payload = _base_final_payload(
        session=session,
        turn_id=turn_id,
        model_version=model_version,
        needs_clarification=False,
        needs_disambiguation=False,
    )
    final_payload.update({
        "context": context_payload(resolved),
        "recommendations": recommendations,
        "assistant_message": assistant_message,
        "explanation_source": explanation_source,
    })
    if chat_fallback_reason:
        final_payload["chat_fallback_reason"] = chat_fallback_reason
    attach_warnings(final_payload, warnings)
    ranking_mode = (
        recommendations.get("ranking_mode")
        if recommendations
        else seed_ranker.active_ranking_mode_label()
    )
    maybe_attach_debug(
        final_payload,
        resolve_outcome="ready",
        resolved=resolved,
        raw_genres=genres,
        ranking_mode=ranking_mode,
    )

    if explanation_source == "rag":
        metrics.record_rag_chat_turn("ready", resolved.resolve_reason)
        log_chat_turn(session.session_id, turn_id, "ready", started_at)
    else:
        metrics.record_rag_chat_turn("fallback", chat_fallback_reason)
        log_chat_turn(session.session_id, turn_id, "fallback", started_at)
    yield format_sse("final", final_payload)


def try_rank(
    ranking_seed_ids: list[int],
    context: ChatContext,
    *,
    shuffle: bool,
    catalog: seed_ranker.Catalog,
) -> tuple[RankedList | None, str | None]:
    del shuffle
    try:
        result = seed_ranker.rank(
            ranking_seed_ids,
            False,
            catalog,
            genres=context.genres or None,
            year_min=context.year_min,
            year_max=context.year_max,
        )
        return result, None
    except seed_ranker.ContentUnavailableError:
        return None, "content_unavailable"
    except seed_ranker.InvalidSeedsError:
        return RankedList(
            items=[],
            seed_movie_ids=list(ranking_seed_ids),
            anchor_movie_id=ranking_seed_ids[0],
            similar_movies=[],
        ), None


def normalize_session_genres(
    genres: list[str] | None,
    prior: ChatContext,
) -> list[str]:
    if genres:
        return genres
    return list(prior.genres)


def session_context_api(session: ChatSession, services: CatalogServices) -> dict[str, Any]:
    return visible_context_payload(session.context, services)


def chat_prompt_version() -> str:
    return os.getenv("RAG_PROMPT_VERSION", RAG_CHAT_PROMPT_VERSION)


def _base_final_payload(
    *,
    session: ChatSession,
    turn_id: str,
    model_version: str,
    needs_clarification: bool,
    needs_disambiguation: bool,
    clarification_reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "session_id": session.session_id,
        "turn_id": turn_id,
        "needs_clarification": needs_clarification,
        "needs_disambiguation": needs_disambiguation,
        "model_version": model_version,
        "explanation_source": "rag",
        "rag_chat_version": RAG_CHAT_VERSION,
        "prompt_version": chat_prompt_version(),
    }
    if clarification_reason is not None:
        payload["clarification_reason"] = clarification_reason
    return payload


def chat_debug_enabled() -> bool:
    if os.getenv("RAG_CHAT_DEBUG", "").lower() in {"1", "true", "yes"}:
        return True
    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    return env not in {"production", "prod"}


def build_chat_debug_payload(
    *,
    resolve_outcome: str,
    resolved: ResolveReady | ResolveClarify | ResolveDisambiguate | None = None,
    raw_genres: list[str] | None = None,
    ranking_mode: str | None = None,
) -> dict[str, Any]:
    debug: dict[str, Any] = {"resolve_outcome": resolve_outcome}
    if ranking_mode:
        debug["ranking_mode"] = ranking_mode
    if isinstance(resolved, ResolveReady):
        debug["seed_source"] = resolved.resolve_reason
        debug["normalized_genres"] = list(resolved.context.genres)
    elif isinstance(resolved, ResolveDisambiguate):
        debug["candidate_count"] = len(resolved.candidates)
        debug["normalized_genres"] = list(resolved.context.genres)
    elif isinstance(resolved, ResolveClarify):
        if raw_genres:
            debug["normalized_genres"] = [genre.strip() for genre in raw_genres if genre.strip()]
    return debug


def maybe_attach_debug(
    payload: dict[str, Any],
    *,
    resolve_outcome: str,
    resolved: ResolveReady | ResolveClarify | ResolveDisambiguate | None = None,
    raw_genres: list[str] | None = None,
    ranking_mode: str | None = None,
) -> None:
    if not chat_debug_enabled():
        return
    payload["debug"] = build_chat_debug_payload(
        resolve_outcome=resolve_outcome,
        resolved=resolved,
        raw_genres=raw_genres,
        ranking_mode=ranking_mode,
    )


def attach_warnings(payload: dict[str, Any], warnings: list[dict[str, Any]]) -> None:
    if warnings:
        payload["warnings"] = warnings


class ProviderTimeoutError(Exception):
    pass


class ProviderError(Exception):
    pass


def log_chat_turn(session_id: str, turn_id: str, outcome: str, started_at: float) -> None:
    logger.info(
        json.dumps(
            {
                "event": "rag_chat_turn",
                "session_id": session_id,
                "turn_id": turn_id,
                "outcome": outcome,
                "latency_ms": int((time.perf_counter() - started_at) * 1000),
            },
            sort_keys=True,
        )
    )
