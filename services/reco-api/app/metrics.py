import os
import sys
from collections import defaultdict

_request_counts: dict[tuple[str, str], int] = defaultdict(int)
_latency_counts: dict[tuple[str, str], int] = defaultdict(int)
_latency_sums: dict[tuple[str, str], float] = defaultdict(float)
_cache_events: dict[tuple[str, str], int] = defaultdict(int)
_rag_chat_outcomes: dict[str, int] = defaultdict(int)
_rag_chat_reasons: dict[str, int] = defaultdict(int)


def reset() -> None:
    """Clear in-memory counters (used by tests between app reloads)."""
    _request_counts.clear()
    _latency_counts.clear()
    _latency_sums.clear()
    _cache_events.clear()
    _rag_chat_outcomes.clear()
    _rag_chat_reasons.clear()


def record_request(endpoint: str, status: int, latency_ms: float) -> None:
    labels = (endpoint, str(status))
    _request_counts[labels] += 1
    _latency_counts[labels] += 1
    _latency_sums[labels] += latency_ms


def record_cache_event(cache: str, event: str) -> None:
    _cache_events[(cache, event)] += 1


def _metrics_state() -> tuple[dict[str, int], dict[str, int]]:
    """Use the canonical module dict so reload-heavy tests stay consistent."""
    mod = sys.modules.get(__name__)
    if mod is None:
        return _rag_chat_outcomes, _rag_chat_reasons
    return mod._rag_chat_outcomes, mod._rag_chat_reasons


def record_rag_chat_turn(outcome: str, reason: str | None = None) -> None:
    outcomes, reasons = _metrics_state()
    outcomes[outcome] += 1
    if reason:
        reasons[reason] += 1


def record_rag_outcome(source: str, fallback_reason: str | None = None) -> None:
    """Deprecated alias for legacy call sites; maps to chat turn metrics."""
    if source in {"rag", "rag_cache"}:
        record_rag_chat_turn("success")
    else:
        record_rag_chat_turn("fallback", fallback_reason)


def _label_text(endpoint: str, status: str) -> str:
    return f'{{endpoint="{endpoint}",status="{status}"}}'


def _cache_label_text(cache: str, event: str) -> str:
    return f'{{cache="{cache}",event="{event}"}}'


def prometheus_text() -> str:
    provider = os.getenv("RAG_PROVIDER", "mock")
    chat_outcomes, chat_reasons = _metrics_state()
    lines = [
        "# HELP movie_reco_requests_total Total HTTP requests observed by the API.",
        "# TYPE movie_reco_requests_total counter",
        *[
            f"movie_reco_requests_total{_label_text(endpoint, status)} {count}"
            for (endpoint, status), count in sorted(_request_counts.items())
        ],
        "# HELP movie_reco_request_latency_ms HTTP request latency in milliseconds.",
        "# TYPE movie_reco_request_latency_ms summary",
        *[
            f"movie_reco_request_latency_ms_count{_label_text(endpoint, status)} {count}"
            for (endpoint, status), count in sorted(_latency_counts.items())
        ],
        *[
            f"movie_reco_request_latency_ms_sum{_label_text(endpoint, status)} {total:.3f}"
            for (endpoint, status), total in sorted(_latency_sums.items())
        ],
        "# HELP movie_reco_cache_events_total Cache hit and miss events.",
        "# TYPE movie_reco_cache_events_total counter",
        *[
            f"movie_reco_cache_events_total{_cache_label_text(cache, event)} {count}"
            for (cache, event), count in sorted(_cache_events.items())
        ],
        "# HELP movie_reco_rag_chat_turns_total Conversational RAG chat turn outcomes.",
        "# TYPE movie_reco_rag_chat_turns_total counter",
        *[
            f'movie_reco_rag_chat_turns_total{{outcome="{outcome}"}} {count}'
            for outcome, count in sorted(chat_outcomes.items())
        ],
        "# HELP movie_reco_rag_chat_reasons_total Chat turn detail reasons (clarify, fallback, rank).",
        "# TYPE movie_reco_rag_chat_reasons_total counter",
        *[
            f'movie_reco_rag_chat_reasons_total{{reason="{reason}"}} {count}'
            for reason, count in sorted(chat_reasons.items())
        ],
        "# HELP movie_reco_rag_provider_mode Current configured RAG provider mode.",
        "# TYPE movie_reco_rag_provider_mode gauge",
        f'movie_reco_rag_provider_mode{{provider="{provider}"}} 1',
    ]
    return "\n".join(lines) + "\n"
