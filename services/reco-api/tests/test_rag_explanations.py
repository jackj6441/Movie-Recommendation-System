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
    sys.modules.pop("app.main", None)
    sys.modules.pop("app.content", None)
    return importlib.import_module("app.main").app


def test_rag_explanations_returns_mock_structured_explanation_for_seed_set(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]
    assert payload["model_version"] == "dev"
    assert payload["rag_evidence_version"] == "structured-v1"
    assert payload["prompt_version"] == "rag-exp-v1"
    assert payload["request_id"]
    assert payload["evidence_hash"].startswith("sha256:")
    assert payload["explanation_source"] == "rag"
    assert 1 <= len(payload["items"]) <= 3
    for item in payload["items"]:
        assert set(item) == {"movie_id", "reason", "evidence"}
        assert item["reason"]
        assert set(item["evidence"]).issubset({"seed_set", "content_signal", "hybrid_score"})


def test_rag_explanations_items_match_deterministic_top_three_order(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    deterministic_response = client.post("/explanations", json={"seeds": [1, 2, 3], "shuffle": False})
    rag_response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert deterministic_response.status_code == 200
    assert rag_response.status_code == 200
    deterministic_top_three = [
        item["movie_id"] for item in deterministic_response.json()["topk"][:3]
    ]
    rag_items = [item["movie_id"] for item in rag_response.json()["items"]]
    assert rag_items == deterministic_top_three


def test_rag_explanations_reuses_seed_set_validation(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [], "shuffle": False})

    assert response.status_code == 400
    assert response.json() == {"detail": "seeds must be 1 to 5 items"}
