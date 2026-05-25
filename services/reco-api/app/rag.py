import hashlib
import json
import uuid
from typing import Any

RAG_EVIDENCE_VERSION = "structured-v1"
RAG_PROMPT_VERSION = "rag-exp-v1"
RAG_EVIDENCE_TYPES = ["seed_set", "content_signal", "hybrid_score"]


def build_mock_structured_explanation(
    deterministic: dict[str, Any],
    model_version: str,
) -> dict[str, Any]:
    evidence_hash = hashlib.sha256(
        json.dumps(deterministic, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
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

    return {
        "summary": summary,
        "items": items,
        "model_version": model_version,
        "rag_evidence_version": RAG_EVIDENCE_VERSION,
        "evidence_hash": f"sha256:{evidence_hash}",
        "prompt_version": RAG_PROMPT_VERSION,
        "request_id": str(uuid.uuid4()),
        "explanation_source": "rag",
    }
