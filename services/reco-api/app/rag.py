import hashlib
import json
import os
import time
import uuid
from typing import Any

RAG_EVIDENCE_VERSION = "structured-v1"
RAG_PROMPT_VERSION = "rag-exp-v1"
RAG_EVIDENCE_TYPES = ["seed_set", "content_signal", "hybrid_score"]
SUPPORTED_RAG_PROVIDERS = {
    "mock",
    "mock_extra_item_field",
    "mock_extra_top_level_field",
    "mock_invalid_schema",
    "mock_missing_top_three_item",
    "mock_wrong_item_order",
}
RAG_CACHE: dict[str, dict[str, Any]] = {}


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
        "prompt_version": rag_prompt_version(),
        "request_id": str(uuid.uuid4()),
    }


def rag_prompt_version() -> str:
    return os.getenv("RAG_PROMPT_VERSION", RAG_PROMPT_VERSION)


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

    metadata = response_metadata(deterministic, model_version)
    provider_model = rag_provider_model()
    cache_key = rag_cache_key(metadata, model_version, provider, provider_model)
    cached_entry = RAG_CACHE.get(cache_key)
    if is_rag_cache_enabled() and cached_entry and is_rag_cache_entry_fresh(cached_entry):
        return {
            **cached_entry["payload"],
            **metadata,
            "explanation_source": "rag_cache",
        }

    provider_payload = build_provider_payload(deterministic, provider)
    if not is_valid_provider_payload(provider_payload, deterministic):
        return build_deterministic_fallback(
            deterministic,
            model_version,
            "schema_validation_failed",
        )

    response = {
        **provider_payload,
        **metadata,
        "explanation_source": "rag",
    }
    if is_rag_cache_enabled():
        RAG_CACHE[cache_key] = {"payload": provider_payload, "stored_at": time.time()}
    return response


def is_rag_cache_enabled() -> bool:
    return os.getenv("RAG_CACHE_ENABLED", "false").lower() == "true"


def rag_cache_ttl_seconds() -> int:
    try:
        return int(os.getenv("RAG_CACHE_TTL_SECONDS", "3600"))
    except ValueError:
        return 0


def is_rag_cache_entry_fresh(cache_entry: dict[str, Any]) -> bool:
    return time.time() - cache_entry["stored_at"] < rag_cache_ttl_seconds()


def rag_provider_model() -> str:
    return os.getenv("RAG_PROVIDER_MODEL", "mock")


def rag_cache_key(
    metadata: dict[str, str],
    model_version: str,
    provider: str,
    provider_model: str,
) -> str:
    return ":".join(
        [
            model_version,
            metadata["evidence_hash"],
            metadata["prompt_version"],
            provider,
            provider_model,
        ]
    )


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
    if provider == "mock_extra_item_field":
        items[0]["confidence"] = 0.9
    if provider == "mock_wrong_item_order":
        items = list(reversed(items))
    if provider == "mock_missing_top_three_item":
        items = items[:2]

    payload = {"summary": summary, "items": items}
    if provider == "mock_extra_top_level_field":
        payload["debug_notes"] = "provider-only field"
    return payload


def is_valid_provider_payload(
    provider_payload: dict[str, Any],
    deterministic: dict[str, Any],
) -> bool:
    if set(provider_payload) != {"summary", "items"}:
        return False
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

    return item_movie_ids == expected_movie_ids


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
