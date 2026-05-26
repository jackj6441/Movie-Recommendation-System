import hashlib
import json
import os
import uuid
from typing import Any

RAG_EVIDENCE_VERSION = "structured-v1"
RAG_PROMPT_VERSION = "rag-exp-v1"
RAG_EVIDENCE_TYPES = ["seed_set", "content_signal", "hybrid_score"]
SUPPORTED_RAG_PROVIDERS = {"mock", "mock_invalid_schema", "mock_wrong_item_order"}


def evidence_hash_for(deterministic: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(deterministic, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def response_metadata(deterministic: dict[str, Any], model_version: str) -> dict[str, str]:
    return {
        "model_version": model_version,
        "rag_evidence_version": RAG_EVIDENCE_VERSION,
        "evidence_hash": evidence_hash_for(deterministic),
        "prompt_version": RAG_PROMPT_VERSION,
        "request_id": str(uuid.uuid4()),
    }


def build_mock_structured_explanation(
    deterministic: dict[str, Any],
    model_version: str,
) -> dict[str, Any]:
    provider = os.getenv("RAG_PROVIDER", "mock")
    if provider == "mock_invalid_json":
        return build_deterministic_fallback(deterministic, model_version, "invalid_json")
    if provider == "mock_timeout":
        return build_deterministic_fallback(deterministic, model_version, "provider_timeout")
    if provider == "mock_provider_error":
        return build_deterministic_fallback(deterministic, model_version, "provider_error")
    if provider == "disabled":
        return build_deterministic_fallback(deterministic, model_version, "disabled")
    if provider not in SUPPORTED_RAG_PROVIDERS:
        return build_deterministic_fallback(deterministic, model_version, "unknown")

    provider_payload = build_provider_payload(deterministic, provider)
    if not is_valid_provider_payload(provider_payload, deterministic):
        return build_deterministic_fallback(
            deterministic,
            model_version,
            "schema_validation_failed",
        )

    return {
        **provider_payload,
        **response_metadata(deterministic, model_version),
        "explanation_source": "rag",
    }


def build_provider_payload(deterministic: dict[str, Any], provider: str) -> dict[str, Any]:
    if provider == "mock_invalid_schema":
        return {
            "summary": "",
            "items": [{"movie_id": "not-an-int", "evidence": ["unsupported"]}],
        }

    top_items = deterministic.get("topk", [])[:3]
    seed_movies = deterministic.get("seed_movies", [])
    seed_titles = ", ".join(seed["title"] for seed in seed_movies[:3])
    if seed_titles:
        summary = (
            f"Based on your Seed Set ({seed_titles}), these Recommendations emphasize "
            "movies with similar content signals and strong hybrid scores."
        )
    else:
        summary = "These Recommendations emphasize similar content signals and strong hybrid scores."

    items = [
        {
            "movie_id": item["movie_id"],
            "reason": (
                f"{item['title']} is recommended because it aligns with your Seed Set "
                "through content similarity and its Hybrid Score."
            ),
            "evidence": RAG_EVIDENCE_TYPES,
        }
        for item in top_items
    ]
    if provider == "mock_wrong_item_order":
        items = list(reversed(items))

    return {"summary": summary, "items": items}


def is_valid_provider_payload(
    provider_payload: dict[str, Any],
    deterministic: dict[str, Any],
) -> bool:
    if not isinstance(provider_payload.get("summary"), str) or not provider_payload["summary"]:
        return False

    items = provider_payload.get("items")
    if not isinstance(items, list):
        return False

    expected_movie_ids = [item["movie_id"] for item in deterministic.get("topk", [])[:3]]
    item_movie_ids: list[int] = []
    for item in items:
        if not isinstance(item, dict):
            return False
        if set(item) != {"movie_id", "reason", "evidence"}:
            return False
        if not isinstance(item["movie_id"], int):
            return False
        if not isinstance(item["reason"], str) or not item["reason"]:
            return False
        if not isinstance(item["evidence"], list) or not item["evidence"]:
            return False
        if not set(item["evidence"]).issubset(RAG_EVIDENCE_TYPES):
            return False
        item_movie_ids.append(item["movie_id"])

    return item_movie_ids == expected_movie_ids[: len(item_movie_ids)]


def build_deterministic_fallback(
    deterministic: dict[str, Any],
    model_version: str,
    fallback_reason: str,
) -> dict[str, Any]:
    top_items = deterministic.get("topk", [])[:3]
    items = [
        {
            "movie_id": item["movie_id"],
            "reason": "This Recommendation is based on your Seed Set and existing scoring signals.",
            "evidence": RAG_EVIDENCE_TYPES,
        }
        for item in top_items
    ]
    return {
        "summary": "These Recommendations are based on your Seed Set and existing scoring signals.",
        "items": items,
        **response_metadata(deterministic, model_version),
        "explanation_source": "deterministic_fallback",
        "fallback_reason": fallback_reason,
    }
