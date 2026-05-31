import os


def prometheus_text() -> str:
    provider = os.getenv("RAG_PROVIDER", "mock")
    lines = [
        "# HELP movie_reco_requests_total Total HTTP requests observed by the API.",
        "# TYPE movie_reco_requests_total counter",
        "movie_reco_requests_total 0",
        "# HELP movie_reco_request_latency_ms HTTP request latency in milliseconds.",
        "# TYPE movie_reco_request_latency_ms summary",
        "movie_reco_request_latency_ms 0",
        "# HELP movie_reco_cache_events_total Cache hit and miss events.",
        "# TYPE movie_reco_cache_events_total counter",
        "movie_reco_cache_events_total 0",
        "# HELP movie_reco_rag_explanations_total RAG explanation outcomes by source.",
        "# TYPE movie_reco_rag_explanations_total counter",
        "movie_reco_rag_explanations_total 0",
        "# HELP movie_reco_rag_provider_mode Current configured RAG provider mode.",
        "# TYPE movie_reco_rag_provider_mode gauge",
        f'movie_reco_rag_provider_mode{{provider="{provider}"}} 1',
    ]
    return "\n".join(lines) + "\n"
