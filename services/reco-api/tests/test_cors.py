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


def test_cors_allows_configured_ec2_frontend_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://34.228.75.214:3000")
    client = TestClient(load_app(monkeypatch))

    response = client.options(
        "/recommendations",
        headers={
            "Origin": "http://34.228.75.214:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://34.228.75.214:3000"
