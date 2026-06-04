from pathlib import Path

from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_prometheus_text(load_app):
    client = TestClient(load_app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "movie_reco_requests_total" in body
    assert "movie_reco_request_latency_ms" in body
    assert "movie_reco_rag_explanations_total" in body
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


def test_metrics_record_rag_source_and_fallback_reason(load_app, monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_invalid_json")
    client = TestClient(load_app)

    rag_response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})
    metrics_response = client.get("/metrics")

    assert rag_response.status_code == 200
    assert rag_response.json()["explanation_source"] == "deterministic_fallback"
    body = metrics_response.text
    assert 'movie_reco_rag_explanations_total{source="deterministic_fallback"} 1' in body
    assert 'movie_reco_rag_fallback_reasons_total{reason="invalid_json"} 1' in body


def test_api_docs_explain_healthz_and_metrics_roles():
    docs = Path("docs/api.md").read_text(encoding="utf-8").lower()

    assert "/healthz" in docs
    assert "/metrics" in docs
    assert "readiness" in docs
    assert "observability" in docs
    assert "movie_reco_requests_total" in docs
