"""Grounded RAG evidence from ranker output (prompt-only, not exposed as Structured Explanation)."""

from __future__ import annotations

from typing import Any

from app.seed_ranker import RankedList

RAG_CHAT_VERSION = "conversational-v1"


def build_evidence(
    rank_result: RankedList,
    *,
    seed_titles: dict[int, str],
) -> dict[str, Any]:
    top_items = [
        {
            "movie_id": item.movie_id,
            "title": item.title,
            "content_signal": round(item.content_score, 3),
            "fusion_score": round(item.fusion_score, 3),
            "channel_scores": dict(item.channel_scores),
        }
        for item in rank_result.items[:8]
    ]
    return {
        "rag_chat_version": RAG_CHAT_VERSION,
        "seed_movies": [
            {"movie_id": mid, "title": seed_titles.get(mid, f"Movie {mid}")}
            for mid in rank_result.seed_movie_ids
        ],
        "anchor_movie_id": rank_result.anchor_movie_id,
        "ranking_mode": rank_result.ranking_mode,
        "top_items": top_items,
        "similar_movies": [
            {"movie_id": mid, "similarity": round(sim, 3)}
            for mid, sim in rank_result.similar_movies
        ],
    }
