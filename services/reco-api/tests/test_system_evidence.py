from pathlib import Path

from fastapi.testclient import TestClient


def test_system_evidence_returns_portfolio_summary(load_app):
    client = TestClient(load_app)

    response = client.get("/system/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["system_name"] == "movie-recommendation-system"
    assert payload["deployment"]["platform"] == "AWS EC2"
    assert payload["deployment"]["runtime"] == "Docker Compose"
    assert payload["deployment"]["ui_url"] == "http://34.228.75.214:3000"
    assert payload["serving"]["status"] == "ok"
    assert payload["serving"]["model_version"] == "dev"
    assert "content" in payload["model_truth"]["product_ranking_path"].lower()
    assert payload["evaluation"]["recall_at_k"] == 0.04
    assert payload["evaluation"]["popularity_baseline_recall_at_k"] == 0.03
    assert payload["evaluation"]["dataset"] == "MovieLens 32M (served catalog, min 20 ratings)"
    assert payload["benchmark"]["recommendations_p95_ms"] == 65.459
    assert payload["rag"]["public_provider"] == "mock"


def test_system_evidence_missing_artifact_returns_clear_fallback(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing-system-evidence.json"
    monkeypatch.setenv("SYSTEM_EVIDENCE_PATH", str(missing_path))
    import importlib
    import sys

    api_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(api_root))
    for module_name in ["app.main", "app.content", "app.rag", "app.seed_ranker", "app.metrics", "app.posters"]:
        sys.modules.pop(module_name, None)
    app = importlib.import_module("app.main").app
    client = TestClient(app)

    response = client.get("/system/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["system_name"] == "movie-recommendation-system"
    assert payload["evidence_available"] is False
    assert payload["evidence_error"] == "system evidence artifact not found"
    assert payload["serving"]["status"] == "ok"
    assert "content" in payload["model_truth"]["product_ranking_path"].lower()
