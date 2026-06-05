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
    ResolveReady,
    resolve_context,
)
from app.rag_session import ChatSession, SessionStore
from app.seed_ranker import RankedList

logger = logging.getLogger(__name__)

RAG_CHAT_PROMPT_VERSION = "rag-chat-v1"
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
    return "Tell me a genre or a movie you enjoy and I will find recommendations."


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
    return {
        "items": [
            movie_payload_fn(
                item.movie_id,
                score=item.fusion_score,
            )
            for item in rank_result.items
        ],
        "seed_movies": [movie_payload_fn(mid) for mid in rank_result.seed_movie_ids],
        "anchor_source": "seed",
        "model_version": model_version,
        "ranking_mode": rank_result.ranking_mode,
    }


def context_payload(ready: ResolveReady) -> dict[str, Any]:
    return {
        "seeds": [
            {"movie_id": seed.movie_id, "title": seed.title}
            for seed in ready.seed_movies
        ],
        "genres": list(ready.context.genres),
        "year_min": ready.context.year_min,
        "year_max": ready.context.year_max,
    }


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
) -> Iterator[str]:
    turn_id = str(uuid.uuid4())
    provider = os.getenv("RAG_PROVIDER", "mock").strip()
    started_at = time.perf_counter()

    session = session_store.get(session_id) if session_id else None
    if session is None:
        session = session_store.create()

    session_store.append_message(session, "user", message, turn_id=turn_id)
    search_fn, genre_fn, title_fn = catalog_services.as_resolve_hooks()
    resolved = resolve_context(
        message=message,
        genres=genres,
        prior=session.context,
        search_movies=search_fn,
        genre_seed_ids=genre_fn,
        get_title=title_fn,
        known_movie_ids=catalog_services.known_movie_ids(),
    )

    if isinstance(resolved, ResolveClarify):
        assistant_message = clarification_copy(resolved.reason)
        for chunk in iter_text_chunks(assistant_message, provider="mock"):
            yield format_sse("token", {"delta": chunk})
        session.context = ChatContext(
            seed_ids=list(session.context.seed_ids),
            genres=normalize_session_genres(genres, session.context),
        )
        session_store.save(session)
        session_store.append_message(session, "assistant", assistant_message, turn_id=turn_id)
        final_payload = {
            "session_id": session.session_id,
            "turn_id": turn_id,
            "needs_clarification": True,
            "clarification_reason": resolved.reason,
            "context": session_context_api(session, catalog_services),
            "recommendations": None,
            "assistant_message": assistant_message,
            "explanation_source": "rag",
            "model_version": model_version,
            "rag_chat_version": RAG_CHAT_VERSION,
            "prompt_version": chat_prompt_version(),
        }
        metrics.record_rag_chat_turn("clarification", resolved.reason)
        log_chat_turn(session.session_id, turn_id, "clarification", started_at)
        yield format_sse("final", final_payload)
        return

    assert isinstance(resolved, ResolveReady)
    session.context = resolved.context
    session_store.save(session)

    rank_result, rank_error = try_rank(
        resolved.context,
        shuffle=shuffle,
        catalog=catalog,
    )
    recommendations = None
    evidence: dict[str, Any] | None = None
    chat_fallback_reason: str | None = None

    if rank_error == "content_unavailable":
        metrics.record_rag_chat_turn("rank_error", rank_error)
        final_payload = {
            "session_id": session.session_id,
            "turn_id": turn_id,
            "needs_clarification": False,
            "context": context_payload(resolved),
            "recommendations": None,
            "assistant_message": "Content embeddings are unavailable right now.",
            "explanation_source": "deterministic_fallback",
            "rank_error": rank_error,
            "model_version": model_version,
            "rag_chat_version": RAG_CHAT_VERSION,
            "prompt_version": chat_prompt_version(),
        }
        yield format_sse("final", final_payload)
        return

    if rank_result is not None:
        seed_titles = {mid: catalog_services.get_title(mid) for mid in rank_result.seed_movie_ids}
        evidence = build_evidence(rank_result, seed_titles=seed_titles)
        recommendations = recommendations_payload(
            rank_result,
            model_version=model_version,
            movie_payload_fn=movie_payload_fn,
        )

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
    final_payload: dict[str, Any] = {
        "session_id": session.session_id,
        "turn_id": turn_id,
        "needs_clarification": False,
        "context": context_payload(resolved),
        "recommendations": recommendations,
        "assistant_message": assistant_message,
        "explanation_source": explanation_source,
        "model_version": model_version,
        "rag_chat_version": RAG_CHAT_VERSION,
        "prompt_version": chat_prompt_version(),
    }
    if chat_fallback_reason:
        final_payload["chat_fallback_reason"] = chat_fallback_reason

    outcome = "success" if explanation_source == "rag" else "fallback"
    metrics.record_rag_chat_turn(outcome, chat_fallback_reason)
    log_chat_turn(session.session_id, turn_id, outcome, started_at)
    yield format_sse("final", final_payload)


def try_rank(
    context: ChatContext,
    *,
    shuffle: bool,
    catalog: seed_ranker.Catalog,
) -> tuple[RankedList | None, str | None]:
    del shuffle
    try:
        result = seed_ranker.rank(
            context.seed_ids,
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
            seed_movie_ids=list(context.seed_ids),
            anchor_movie_id=context.seed_ids[0],
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
    return {
        "seeds": [
            {"movie_id": mid, "title": services.get_title(mid)}
            for mid in session.context.seed_ids
        ],
        "genres": list(session.context.genres),
        "year_min": session.context.year_min,
        "year_max": session.context.year_max,
    }


def chat_prompt_version() -> str:
    return os.getenv("RAG_PROMPT_VERSION", RAG_CHAT_PROMPT_VERSION)


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
