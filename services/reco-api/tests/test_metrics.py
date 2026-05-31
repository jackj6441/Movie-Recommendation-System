import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


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
