import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import _configure_test_env, _reload_app


def test_metrics_endpoint_returns_prometheus_text(load_app):
    client = TestClient(load_app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "movie_reco_requests_total" in body
    assert "movie_reco_request_latency_ms" in body
    assert "movie_reco_rag_chat_turns_total" in body
    assert "movie_reco_cache_events_total" in body
    assert "movie_reco_rag_provider_mode" in body


def test_metrics_record_request_count_and_latency(load_app):
    client = TestClient(load_app)

    health_response = client.get("/healthz")
    metrics_response = client.get("/metrics")

    assert health_response.status_code == 200
    assert metrics_response.status_code == 200
    body = metrics_response.text
    assert 'movie_reco_requests_total{endpoint="/healthz",status="200"} 1' in body
    assert 'movie_reco_request_latency_ms_count{endpoint="/healthz",status="200"} 1' in body
    assert 'movie_reco_request_latency_ms_sum{endpoint="/healthz",status="200"}' in body


def test_metrics_record_rag_chat_fallback(monkeypatch, repo_root, api_root):
    _configure_test_env(monkeypatch, repo_root, api_root)
    monkeypatch.setenv("RAG_PROVIDER", "mock_timeout")
    app = _reload_app(api_root)
    metrics_module = importlib.import_module("app.metrics")
    client = TestClient(app)

    rag_response = client.post("/rag/chat", json={"message": "go", "genres": ["Comedy"]})
    assert rag_response.status_code == 200
    assert "event: final" in rag_response.text
    assert metrics_module._rag_chat_outcomes.get("fallback") == 1
    assert metrics_module._rag_chat_reasons.get("provider_timeout") == 1

    metrics_response = client.get("/metrics")
    body = metrics_response.text
    assert 'movie_reco_rag_chat_turns_total{outcome="fallback"}' in body
    assert 'movie_reco_rag_chat_reasons_total{reason="provider_timeout"}' in body


def test_api_docs_explain_healthz_and_metrics_roles(repo_root: Path):
    docs = (repo_root / "docs" / "api.md").read_text(encoding="utf-8").lower()

    assert "/healthz" in docs
    assert "/metrics" in docs
    assert "readiness" in docs
    assert "observability" in docs
    assert "movie_reco_requests_total" in docs
