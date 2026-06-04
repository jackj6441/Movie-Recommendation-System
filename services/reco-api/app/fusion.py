"""Merge multi-retriever hits and compute weighted Phase 1 fusion scores."""

from __future__ import annotations

from typing import Iterable

from app.artifacts import DEFAULT_FUSION_WEIGHTS

CHANNELS = ("content", "svd", "item_cf", "pop")
RETRIEVER_TOP_K = 200
CANDIDATE_CAP = 400
TOP_K = 24


def minmax_normalize(hits: list[tuple[int, float]]) -> dict[int, float]:
    """Min-max each channel's Top-K list to [0, 1]; ties at the max map to 1."""
    if not hits:
        return {}
    scores = [score for _, score in hits]
    lo = min(scores)
    hi = max(scores)
    if hi == lo:
        return {movie_id: 1.0 for movie_id, _ in hits}
    span = hi - lo
    return {movie_id: (score - lo) / span for movie_id, score in hits}


def merge_candidate_ids(
    channel_hits: dict[str, list[tuple[int, float]]],
    cap: int = CANDIDATE_CAP,
) -> list[int]:
    """Union retriever lists, dedupe, and cap by best raw score across channels."""
    pre_score: dict[int, float] = {}
    for hits in channel_hits.values():
        for movie_id, score in hits:
            pre_score[movie_id] = max(pre_score.get(movie_id, float("-inf")), score)
    ordered = sorted(pre_score, key=lambda movie_id: -pre_score[movie_id])
    return ordered[:cap]


def fuse(
    candidate_ids: Iterable[int],
    channel_hits: dict[str, list[tuple[int, float]]],
    weights: dict[str, float] | None = None,
) -> list[tuple[int, float, dict[str, float]]]:
    """Return (movie_id, fusion_score, normalized_channel_scores) sorted by fusion desc."""
    weight_map = weights or DEFAULT_FUSION_WEIGHTS
    normalized = {channel: minmax_normalize(channel_hits.get(channel, [])) for channel in CHANNELS}

    fused: list[tuple[int, float, dict[str, float]]] = []
    for movie_id in candidate_ids:
        breakdown = {channel: normalized[channel].get(movie_id, 0.0) for channel in CHANNELS}
        score = sum(weight_map.get(channel, 0.0) * breakdown[channel] for channel in CHANNELS)
        fused.append((movie_id, score, breakdown))

    fused.sort(key=lambda item: (-item[1], item[0]))
    return fused
