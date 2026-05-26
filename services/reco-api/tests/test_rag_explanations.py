import importlib
import json
import logging
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
    sys.modules.pop("app.rag", None)
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


def test_rag_explanations_returns_cached_explanation_for_repeated_seed_set(monkeypatch):
    monkeypatch.setenv("RAG_CACHE_ENABLED", "true")
    client = TestClient(load_app(monkeypatch))

    first_response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})
    second_response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["explanation_source"] == "rag"
    assert second_response.json()["explanation_source"] == "rag_cache"
    assert second_response.json()["items"] == first_response.json()["items"]
    assert second_response.json()["evidence_hash"] == first_response.json()["evidence_hash"]


def test_rag_explanations_cache_misses_when_evidence_hash_changes(monkeypatch):
    monkeypatch.setenv("RAG_CACHE_ENABLED", "true")
    client = TestClient(load_app(monkeypatch))

    first_response = client.post("/rag/explanations", json={"seeds": [19, 20, 21], "shuffle": False})
    second_response = client.post("/rag/explanations", json={"seeds": [22, 23, 24], "shuffle": False})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["explanation_source"] == "rag"
    assert second_response.json()["explanation_source"] == "rag"
    assert first_response.json()["evidence_hash"] != second_response.json()["evidence_hash"]


def test_rag_explanations_cache_misses_when_provider_model_changes(monkeypatch):
    monkeypatch.setenv("RAG_CACHE_ENABLED", "true")
    monkeypatch.setenv("RAG_PROVIDER_MODEL", "mock-model-a")
    client = TestClient(load_app(monkeypatch))

    first_response = client.post("/rag/explanations", json={"seeds": [4, 5, 6], "shuffle": False})
    monkeypatch.setenv("RAG_PROVIDER_MODEL", "mock-model-b")
    second_response = client.post("/rag/explanations", json={"seeds": [4, 5, 6], "shuffle": False})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["explanation_source"] == "rag"
    assert second_response.json()["explanation_source"] == "rag"


def test_rag_explanations_cache_misses_when_ttl_expires(monkeypatch):
    monkeypatch.setenv("RAG_CACHE_ENABLED", "true")
    monkeypatch.setenv("RAG_CACHE_TTL_SECONDS", "0")
    client = TestClient(load_app(monkeypatch))

    first_response = client.post("/rag/explanations", json={"seeds": [7, 8, 9], "shuffle": False})
    second_response = client.post("/rag/explanations", json={"seeds": [7, 8, 9], "shuffle": False})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["explanation_source"] == "rag"
    assert second_response.json()["explanation_source"] == "rag"


def test_rag_explanations_ignores_cache_when_ttl_is_invalid(monkeypatch):
    monkeypatch.setenv("RAG_CACHE_ENABLED", "true")
    monkeypatch.setenv("RAG_CACHE_TTL_SECONDS", "not-a-number")
    client = TestClient(load_app(monkeypatch))

    first_response = client.post("/rag/explanations", json={"seeds": [13, 14, 15], "shuffle": False})
    second_response = client.post("/rag/explanations", json={"seeds": [13, 14, 15], "shuffle": False})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["explanation_source"] == "rag"
    assert second_response.json()["explanation_source"] == "rag"


def test_rag_explanations_ignores_cache_when_ttl_is_negative(monkeypatch):
    monkeypatch.setenv("RAG_CACHE_ENABLED", "true")
    monkeypatch.setenv("RAG_CACHE_TTL_SECONDS", "-5")
    client = TestClient(load_app(monkeypatch))

    first_response = client.post("/rag/explanations", json={"seeds": [16, 17, 18], "shuffle": False})
    second_response = client.post("/rag/explanations", json={"seeds": [16, 17, 18], "shuffle": False})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["explanation_source"] == "rag"
    assert second_response.json()["explanation_source"] == "rag"


def test_rag_explanations_cache_misses_when_prompt_version_changes(monkeypatch):
    monkeypatch.setenv("RAG_CACHE_ENABLED", "true")
    monkeypatch.setenv("RAG_PROMPT_VERSION", "rag-exp-test-a")
    client = TestClient(load_app(monkeypatch))

    first_response = client.post("/rag/explanations", json={"seeds": [10, 11, 12], "shuffle": False})
    monkeypatch.setenv("RAG_PROMPT_VERSION", "rag-exp-test-b")
    second_response = client.post("/rag/explanations", json={"seeds": [10, 11, 12], "shuffle": False})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["prompt_version"] == "rag-exp-test-a"
    assert second_response.json()["prompt_version"] == "rag-exp-test-b"
    assert first_response.json()["explanation_source"] == "rag"
    assert second_response.json()["explanation_source"] == "rag"


def test_rag_explanations_logs_safe_metadata_for_successful_rag(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="app.rag")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    log_payloads = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "app.rag" and record.message.startswith("{")
    ]
    assert log_payloads
    metadata_log = log_payloads[-1]
    assert metadata_log["event"] == "rag_explanation"
    assert metadata_log["request_id"] == response.json()["request_id"]
    assert metadata_log["model_version"] == "dev"
    assert metadata_log["rag_evidence_version"] == "structured-v1"
    assert metadata_log["prompt_version"] == "rag-exp-v1"
    assert metadata_log["evidence_hash"] == response.json()["evidence_hash"]
    assert metadata_log["provider"] == "mock"
    assert metadata_log["provider_model"] == "mock"
    assert metadata_log["explanation_source"] == "rag"
    assert metadata_log["cache_hit"] is False
    assert metadata_log["validation_result"] == "passed"
    assert metadata_log["fallback_reason"] is None
    assert metadata_log["error_type"] is None
    assert metadata_log["latency_ms"] >= 0


def test_rag_explanations_logs_safe_metadata_for_cache_hit(monkeypatch, caplog):
    monkeypatch.setenv("RAG_CACHE_ENABLED", "true")
    caplog.set_level(logging.INFO, logger="app.rag")
    client = TestClient(load_app(monkeypatch))

    first_response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})
    second_response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["explanation_source"] == "rag_cache"
    log_payloads = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "app.rag" and record.message.startswith("{")
    ]
    metadata_log = log_payloads[-1]
    assert metadata_log["event"] == "rag_explanation"
    assert metadata_log["request_id"] == second_response.json()["request_id"]
    assert metadata_log["evidence_hash"] == second_response.json()["evidence_hash"]
    assert metadata_log["provider"] == "mock"
    assert metadata_log["provider_model"] == "mock"
    assert metadata_log["explanation_source"] == "rag_cache"
    assert metadata_log["cache_hit"] is True
    assert metadata_log["validation_result"] == "skipped"
    assert metadata_log["fallback_reason"] is None
    assert metadata_log["error_type"] is None
    assert metadata_log["latency_ms"] >= 0


def test_rag_explanations_reuses_seed_set_validation(monkeypatch):
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [], "shuffle": False})

    assert response.status_code == 400
    assert response.json() == {"detail": "seeds must be 1 to 5 items"}


def test_rag_explanations_falls_back_when_provider_returns_invalid_json(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_invalid_json")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "invalid_json"
    assert payload["summary"]
    assert payload["items"]
    assert payload["model_version"] == "dev"
    assert payload["rag_evidence_version"] == "structured-v1"
    assert payload["prompt_version"] == "rag-exp-v1"
    assert payload["request_id"]
    assert payload["evidence_hash"].startswith("sha256:")


def test_rag_explanations_falls_back_when_provider_returns_invalid_schema(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_invalid_schema")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "schema_validation_failed"
    assert payload["summary"]
    assert payload["items"]


def test_rag_explanations_falls_back_when_provider_adds_extra_item_field(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_extra_item_field")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "schema_validation_failed"


def test_rag_explanations_falls_back_when_provider_adds_extra_top_level_field(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_extra_top_level_field")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "schema_validation_failed"


def test_rag_explanations_falls_back_when_provider_changes_item_order(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_wrong_item_order")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "schema_validation_failed"


def test_rag_explanations_falls_back_when_provider_omits_top_three_item(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_missing_top_three_item")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "schema_validation_failed"


def test_rag_explanations_falls_back_when_provider_times_out(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_timeout")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "provider_timeout"
    assert payload["summary"]
    assert payload["items"]


def test_rag_explanations_falls_back_when_provider_errors(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_provider_error")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "provider_error"
    assert payload["summary"]
    assert payload["items"]


def test_rag_explanations_falls_back_when_rag_is_disabled(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "disabled")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "disabled"


def test_rag_explanations_falls_back_when_provider_is_unknown(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "unknown_provider")
    client = TestClient(load_app(monkeypatch))

    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3], "shuffle": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["explanation_source"] == "deterministic_fallback"
    assert payload["fallback_reason"] == "unknown"
