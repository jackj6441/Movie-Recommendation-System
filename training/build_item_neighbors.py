"""Item–item co-occurrence neighbors for the served catalog.

Reads ratings in chunks, accumulates co-rated counts, and writes
``item_neighbors.json`` mapping each movie id to up to ``top_k`` neighbors
``[[neighbor_id, score], ...]`` with cosine-style scores on binary co-rating.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

_TRAINING_DIR = Path(__file__).resolve().parent
if str(_TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(_TRAINING_DIR))

import pandas as pd

from catalog import DEFAULT_MODELS_DIR, load_catalog_movie_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build item–item neighbor lookup")
    parser.add_argument("--ratings_csv", type=str, required=True)
    parser.add_argument(
        "--models_dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help="directory with content_embeddings.npz / content_index.json",
    )
    parser.add_argument("--top_k", type=int, default=50)
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("services", "reco-api", "models", "item_neighbors.json"),
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=1_000_000,
        help="ratings CSV chunk size for large MovieLens files",
    )
    parser.add_argument(
        "--max-movies-per-user",
        type=int,
        default=200,
        help="cap movies per user when computing pairs (limits blow-up for power users)",
    )
    return parser.parse_args()


def accumulate_cooccurrence(
    ratings_csv: str,
    catalog_ids: set[int],
    chunksize: int,
    max_movies_per_user: int,
) -> tuple[dict[int, Counter[int]], Counter[int]]:
    """Return (pair_counts[movie_id][neighbor_id], degree[movie_id])."""
    pair_counts: dict[int, Counter[int]] = defaultdict(Counter)
    degree: Counter[int] = Counter()

    ratings_iter = pd.read_csv(
        ratings_csv,
        usecols=["userId", "movieId"],
        chunksize=chunksize,
    )

    for chunk in ratings_iter:
        for _, group in chunk.groupby("userId", sort=False):
            mids = [
                int(mid)
                for mid in group["movieId"].astype(int).tolist()
                if int(mid) in catalog_ids
            ]
            if len(mids) < 2:
                continue
            if len(mids) > max_movies_per_user:
                mids = mids[:max_movies_per_user]
            unique_mids = list(dict.fromkeys(mids))
            for mid in unique_mids:
                degree[mid] += 1
            for i, left in enumerate(unique_mids):
                for right in unique_mids[i + 1 :]:
                    pair_counts[left][right] += 1
                    pair_counts[right][left] += 1

    return pair_counts, degree


def top_neighbors(
    movie_ids: list[int],
    pair_counts: dict[int, Counter[int]],
    degree: Counter[int],
    top_k: int,
) -> dict[str, list[list[float | int]]]:
    """Build JSON-serializable neighbor lists keyed by movie id string."""
    out: dict[str, list[list[float | int]]] = {}
    for movie_id in movie_ids:
        neighbors = pair_counts.get(movie_id)
        if not neighbors:
            out[str(movie_id)] = []
            continue
        deg_i = degree[movie_id]
        if deg_i <= 0:
            out[str(movie_id)] = []
            continue
        scored: list[tuple[int, float]] = []
        for neighbor_id, count in neighbors.items():
            deg_j = degree[neighbor_id]
            if deg_j <= 0:
                continue
            score = count / math.sqrt(deg_i * deg_j)
            scored.append((neighbor_id, score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        out[str(movie_id)] = [
            [int(neighbor_id), round(score, 6)]
            for neighbor_id, score in scored[:top_k]
        ]
    return out


def main() -> None:
    args = parse_args()
    movie_ids_array = load_catalog_movie_ids(args.models_dir)
    movie_ids = [int(mid) for mid in movie_ids_array.tolist()]
    catalog_ids = set(movie_ids)

    pair_counts, degree = accumulate_cooccurrence(
        args.ratings_csv,
        catalog_ids,
        args.chunksize,
        args.max_movies_per_user,
    )
    neighbors = top_neighbors(movie_ids, pair_counts, degree, args.top_k)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as neighbors_file:
        json.dump(neighbors, neighbors_file, ensure_ascii=False)

    with_neighbors = sum(1 for value in neighbors.values() if value)
    print(f"catalog_items: {len(movie_ids)}")
    print(f"items_with_neighbors: {with_neighbors}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    main()
