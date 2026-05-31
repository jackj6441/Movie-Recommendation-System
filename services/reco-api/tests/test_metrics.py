import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value


def load_app(monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    api_root = repo_root / "services" / "reco-api"

    monkeypatch.setenv("MOVIES_CSV_PATH", str(repo_root / "ml-latest-small" / "movies.csv"))
    monkeypatch.setenv("RATINGS_CSV_PATH", str(repo_root / "ml-latest-small" / "ratings.csv"))
    monkeypatch.setenv("CONTENT_EMBEDDINGS_PATH", str(api_root / "models" / "content_embeddings.npz"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(api_root / "models" / "content_index.json"))
    monkeypatch.setenv("ONNX_MODEL_PATH", str(api_root / "models" / "ncf.onnx"))
    monkeypatch.setenv("METADATA_PATH", str(api_root / "models" / "metadata.json"))

    sys.path.insert(0, str(api_root))
    for module_name in ["app.main", "app.content", "app.rag", "app.seed_ranker", "app.metrics"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("app.main").app


def test_metrics_endpoint_returns_prometheus_text(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "movie_reco_requests_total" in body
    assert "movie_reco_request_latency_ms" in body
    assert "movie_reco_rag_explanations_total" in body
    assert "movie_reco_cache_events_total" in body
    assert "movie_reco_rag_provider_mode" in body


def test_metrics_record_request_count_and_latency(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    health_response = client.get("/healthz")
    metrics_response = client.get("/metrics")

    assert health_response.status_code == 200
    assert metrics_response.status_code == 200
    body = metrics_response.text
    assert 'movie_reco_requests_total{endpoint="/healthz",status="200"} 1' in body
    assert 'movie_reco_request_latency_ms_count{endpoint="/healthz",status="200"} 1' in body
    assert 'movie_reco_request_latency_ms_sum{endpoint="/healthz",status="200"}' in body


def test_metrics_record_redis_cache_hit_and_miss(monkeypatch):
    app = load_app(monkeypatch)
    main_module = sys.modules["app.main"]
    main_module.redis_client = FakeRedis()
    client = TestClient(app)

    first_response = client.get("/recommend", params={"user_id": 1, "k": 5})
    second_response = client.get("/recommend", params={"user_id": 1, "k": 5})
    metrics_response = client.get("/metrics")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    body = metrics_response.text
    assert 'movie_reco_cache_events_total{cache="redis",event="miss"} 1' in body
    assert 'movie_reco_cache_events_total{cache="redis",event="hit"} 1' in body


def test_metrics_record_rag_source_and_fallback_reason(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_invalid_json")
    client = TestClient(load_app(monkeypatch))

    rag_response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})
    metrics_response = client.get("/metrics")

    assert rag_response.status_code == 200
    assert rag_response.json()["explanation_source"] == "deterministic_fallback"
    body = metrics_response.text
    assert 'movie_reco_rag_explanations_total{source="deterministic_fallback"} 1' in body
    assert 'movie_reco_rag_fallback_reasons_total{reason="invalid_json"} 1' in body
