"""Direct tests for run_chat_turn (transport-agnostic) and SSE adapter."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app import rag_chat as rag_chat_service  # noqa: E402
from app.rag_chat_events import ChatTurnFinal, ChatTurnToken  # noqa: E402
from app.rag_chat_sse import encode_chat_turn_event, format_sse, run_chat_turn_sse  # noqa: E402
from app.rag_session import GLOBAL_SESSION_STORE  # noqa: E402
from app.runtime_catalog import RuntimeCatalog  # noqa: E402


def _turn_kwargs(catalog, **overrides):
    base = {
        "session_store": GLOBAL_SESSION_STORE,
        "catalog": catalog,
        "model_version": "test-model",
        "movie_payload_fn": lambda movie_id, **extra: {"movie_id": movie_id, **extra},
        "message": "",
        "genres": ["Comedy"],
        "session_id": None,
        "shuffle": False,
    }
    base.update(overrides)
    return base


def _collect_turn_events(catalog, **kwargs):
    return list(rag_chat_service.run_chat_turn(**_turn_kwargs(catalog, **kwargs)))


def _final_payload(events) -> dict:
    finals = [event.payload for event in events if isinstance(event, ChatTurnFinal)]
    assert len(finals) == 1
    return finals[0]


def test_run_chat_turn_accepts_runtime_catalog_only():
    params = inspect.signature(rag_chat_service.run_chat_turn).parameters
    assert "catalog" in params
    assert "catalog_services" not in params
    assert params["catalog"].annotation in (RuntimeCatalog, "RuntimeCatalog")


def test_run_chat_turn_clarify_emits_tokens_and_final(load_app):
    del load_app
    import importlib

    catalog = importlib.import_module("app.main").runtime_catalog
    events = _collect_turn_events(catalog, message="", genres=[])
    assert any(isinstance(event, ChatTurnToken) for event in events)
    final_payload = _final_payload(events)
    assert final_payload["needs_clarification"] is True
    assert final_payload["clarification_reason"] == "missing_genre_and_title"


def test_run_chat_turn_disambiguation_emits_final_only(load_app):
    del load_app
    import importlib

    catalog = importlib.import_module("app.main").runtime_catalog
    events = _collect_turn_events(catalog, message="zzzznotamovie", genres=[])
    assert not any(isinstance(event, ChatTurnToken) for event in events)
    final_payload = _final_payload(events)
    assert final_payload["needs_disambiguation"] is True
    assert final_payload["disambiguation_candidates"]


def test_run_chat_turn_ready_emits_tokens_and_final(load_app):
    del load_app
    import importlib

    catalog = importlib.import_module("app.main").runtime_catalog
    events = _collect_turn_events(catalog, message="", genres=["Comedy"])
    assert any(isinstance(event, ChatTurnToken) for event in events)
    final_payload = _final_payload(events)
    assert final_payload["needs_clarification"] is False
    assert final_payload["recommendations"] is not None


def test_sse_adapter_encodes_token_and_final():
    token_wire = encode_chat_turn_event(ChatTurnToken(delta="hello"))
    assert token_wire.startswith("event: token\n")
    assert json.loads(token_wire.split("data: ", 1)[1]) == {"delta": "hello"}

    final_wire = encode_chat_turn_event(ChatTurnFinal(payload={"session_id": "s1", "ok": True}))
    assert final_wire.startswith("event: final\n")
    assert json.loads(final_wire.split("data: ", 1)[1])["session_id"] == "s1"


def test_run_chat_turn_sse_matches_turn_events(load_app):
    del load_app
    import importlib
    import json

    catalog = importlib.import_module("app.main").runtime_catalog
    kwargs = _turn_kwargs(catalog, message="", genres=["Comedy"])
    turn_events = list(rag_chat_service.run_chat_turn(**kwargs))
    sse_chunks = list(run_chat_turn_sse(**kwargs))
    assert len(sse_chunks) == len(turn_events)

    def decode(chunk: str) -> tuple[str, dict]:
        event_name = chunk.split("\n", 1)[0].removeprefix("event: ").strip()
        payload = json.loads(chunk.split("data: ", 1)[1])
        return event_name, payload

    for chunk, event in zip(sse_chunks, turn_events):
        event_name, payload = decode(chunk)
        delta = getattr(event, "delta", None)
        if delta is not None:
            assert event_name == "token"
            assert payload == {"delta": delta}
            continue
        final_payload = getattr(event, "payload", None)
        assert event_name == "final"
        assert payload.keys() == final_payload.keys()
        for key, value in payload.items():
            if key in {"session_id", "turn_id"}:
                continue
            assert payload[key] == final_payload[key]


def test_format_sse_roundtrip_shape():
    wire = format_sse("final", {"turn_id": "abc", "needs_clarification": False})
    assert wire == 'event: final\ndata: {"turn_id":"abc","needs_clarification":false}\n\n'
