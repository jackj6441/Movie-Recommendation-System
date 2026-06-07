"""SSE transport adapter for RAG chat turn events."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, Callable

from app.rag_chat_events import ChatTurnEvent
from app.rag_session import SessionStore
from app.runtime_catalog import RuntimeCatalog


def format_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def encode_chat_turn_event(event: ChatTurnEvent) -> str:
    delta = getattr(event, "delta", None)
    if delta is not None:
        return format_sse("token", {"delta": delta})
    payload = getattr(event, "payload", None)
    if payload is not None:
        return format_sse("final", payload)
    raise TypeError(f"unknown chat turn event: {event!r}")


def run_chat_turn_sse(
    *,
    session_store: SessionStore,
    catalog: RuntimeCatalog,
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
    """Encode chat turn events as SSE wire chunks for FastAPI streaming."""
    from app.rag_chat import run_chat_turn

    for event in run_chat_turn(
        session_store=session_store,
        catalog=catalog,
        model_version=model_version,
        movie_payload_fn=movie_payload_fn,
        message=message,
        genres=genres,
        session_id=session_id,
        shuffle=shuffle,
        seed_movie_ids=seed_movie_ids,
        seed_update_mode=seed_update_mode,
        reset_context=reset_context,
        clear_year_bounds=clear_year_bounds,
        year_min=year_min,
        year_max=year_max,
        disambiguation_genre=disambiguation_genre,
    ):
        yield encode_chat_turn_event(event)
