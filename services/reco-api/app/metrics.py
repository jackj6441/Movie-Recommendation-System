import os
from collections import defaultdict

_request_counts: dict[tuple[str, str], int] = defaultdict(int)
_latency_counts: dict[tuple[str, str], int] = defaultdict(int)
_latency_sums: dict[tuple[str, str], float] = defaultdict(float)
_cache_events: dict[tuple[str, str], int] = defaultdict(int)


def record_request(endpoint: str, status: int, latency_ms: float) -> None:
    labels = (endpoint, str(status))
    _request_counts[labels] += 1
    _latency_counts[labels] += 1
    _latency_sums[labels] += latency_ms


def record_cache_event(cache: str, event: str) -> None:
    _cache_events[(cache, event)] += 1


def _label_text(endpoint: str, status: str) -> str:
    return f'{{endpoint="{endpoint}",status="{status}"}}'


def _cache_label_text(cache: str, event: str) -> str:
    return f'{{cache="{cache}",event="{event}"}}'


def prometheus_text() -> str:
    provider = os.getenv("RAG_PROVIDER", "mock")
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
        "# HELP movie_reco_rag_explanations_total RAG explanation outcomes by source.",
        "# TYPE movie_reco_rag_explanations_total counter",
        "movie_reco_rag_explanations_total 0",
        "# HELP movie_reco_rag_provider_mode Current configured RAG provider mode.",
        "# TYPE movie_reco_rag_provider_mode gauge",
        f'movie_reco_rag_provider_mode{{provider="{provider}"}} 1',
    ]
    return "\n".join(lines) + "\n"
