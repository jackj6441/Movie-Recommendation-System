"""Item–item CF retriever: aggregate neighbor scores from each seed."""

from __future__ import annotations

from collections import defaultdict

from app.artifact_bundle import get_default_bundle
from app.fusion import RETRIEVER_TOP_K


def retrieve(
    seed_movie_ids: list[int],
    exclude: set[int],
    top_k: int = RETRIEVER_TOP_K,
) -> list[tuple[int, float]]:
    neighbors = get_default_bundle().fusion.item_neighbors
    if not neighbors:
        return []

    aggregated: dict[int, float] = defaultdict(float)
    for seed_id in seed_movie_ids:
        for entry in neighbors.get(str(seed_id), []):
            if len(entry) < 2:
                continue
            neighbor_id = int(entry[0])
            score = float(entry[1])
            if neighbor_id in exclude:
                continue
            aggregated[neighbor_id] += score

    ranked = sorted(aggregated.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:top_k]
