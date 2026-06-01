import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(monkeypatch, evidence_path: Path | None = None):
    repo_root = Path(__file__).resolve().parents[3]
    api_root = repo_root / "services" / "reco-api"

    monkeypatch.setenv("MOVIES_CSV_PATH", str(repo_root / "ml-latest-small" / "movies.csv"))
    monkeypatch.setenv("RATINGS_CSV_PATH", str(repo_root / "ml-latest-small" / "ratings.csv"))
    monkeypatch.setenv("CONTENT_EMBEDDINGS_PATH", str(api_root / "models" / "content_embeddings.npz"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(api_root / "models" / "content_index.json"))
    monkeypatch.setenv("ONNX_MODEL_PATH", str(api_root / "models" / "ncf.onnx"))
    monkeypatch.setenv("METADATA_PATH", str(api_root / "models" / "metadata.json"))
    if evidence_path is not None:
        monkeypatch.setenv("SYSTEM_EVIDENCE_PATH", str(evidence_path))

    sys.path.insert(0, str(api_root))
    for module_name in ["app.main", "app.content", "app.rag", "app.seed_ranker", "app.metrics"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("app.main").app


def test_system_evidence_returns_portfolio_summary(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    response = client.get("/system/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["system_name"] == "movie-recommendation-system"
    assert payload["deployment"]["platform"] == "AWS EC2"
    assert payload["deployment"]["runtime"] == "Docker Compose"
    assert payload["deployment"]["ui_url"] == "http://34.228.75.214:3000"
    assert payload["serving"]["status"] == "ok"
    assert payload["serving"]["model_version"] == "dev"
    assert payload["model_truth"]["product_ranking_path"] == "Seed Set recommendations driven by Content Signal"
    assert "legacy/debug/evaluation path" in payload["model_truth"]["ncf_onnx_status"]
    assert payload["evaluation"]["recall_at_k"] == 0.05
    assert payload["evaluation"]["popularity_baseline_recall_at_k"] == 0.02
    assert payload["benchmark"]["recommendations_p95_ms"] == 65.459
    assert payload["rag"]["public_provider"] == "mock"


def test_system_evidence_missing_artifact_returns_clear_fallback(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing-system-evidence.json"
    client = TestClient(load_app(monkeypatch, evidence_path=missing_path))

    response = client.get("/system/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["system_name"] == "movie-recommendation-system"
    assert payload["evidence_available"] is False
    assert payload["evidence_error"] == "system evidence artifact not found"
    assert payload["serving"]["status"] == "ok"
    assert payload["model_truth"]["product_ranking_path"] == "Seed Set recommendations driven by Content Signal"
