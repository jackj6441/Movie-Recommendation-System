"""Evaluate Phase 1 fusion ranking (Recall / NDCG @10 and @24)."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from fusion_ranking import (
    MODELS_DIR,
    RuntimeCatalog,
    configure_artifact_paths,
    load_eval_catalog,
    rank_seed_set,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate multi-retriever fusion ranking")
    parser.add_argument("--ratings", default="ml-latest-small/ratings.csv")
    parser.add_argument("--movies", default=str(MODELS_DIR / "catalog_movies.csv"))
    parser.add_argument(
        "--serving-stats",
        default=str(MODELS_DIR / "serving_stats.json"),
        help="optional popularity artifact; falls back to ratings counts",
    )
    parser.add_argument("--content-embeddings", default=str(MODELS_DIR / "content_embeddings.npz"))
    parser.add_argument("--content-index", default=str(MODELS_DIR / "content_index.json"))
    parser.add_argument("--item-factors-svd", default=str(MODELS_DIR / "item_factors_svd.npz"))
    parser.add_argument("--item-neighbors", default=str(MODELS_DIR / "item_neighbors.json"))
    parser.add_argument("--fusion-weights", default=str(MODELS_DIR / "fusion_weights.json"))
    parser.add_argument("--max-users", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=24, help="ranking depth (serving uses 24)")
    parser.add_argument(
        "--metric-ks",
        default="10,24",
        help="comma-separated K values for Recall@K and NDCG@K",
    )
    parser.add_argument("--output", default="evaluation/results/fusion_metrics.json")
    return parser.parse_args(argv)


def parse_k_values(raw: str, top_k: int) -> list[int]:
    values = sorted({int(part.strip()) for part in raw.split(",") if part.strip()})
    if not values:
        raise ValueError("metric-ks must list at least one K")
    if any(k < 1 for k in values):
        raise ValueError("metric K values must be >= 1")
    if any(k > top_k for k in values):
        raise ValueError(f"metric K values cannot exceed --top-k ({top_k})")
    return values


def recall_at_k(recommendations: list[int], target: int, k: int) -> float:
    return 1.0 if target in recommendations[:k] else 0.0


def ndcg_at_k(recommendations: list[int], target: int, k: int) -> float:
    subset = recommendations[:k]
    if target not in subset:
        return 0.0
    rank = subset.index(target) + 1
    return 1.0 / math.log2(rank + 1)


def popularity_baseline(
    seed_ids: list[int],
    popular_movie_ids: list[int],
    k: int,
) -> list[int]:
    exclude = set(seed_ids)
    return [mid for mid in popular_movie_ids if mid not in exclude][:k]


def run_evaluation(
    ratings: pd.DataFrame,
    catalog: RuntimeCatalog,
    *,
    fusion_weights: dict[str, float] | None,
    max_users: int,
    top_k: int,
    k_values: list[int],
) -> dict[str, Any]:
    evaluated = 0
    fusion_recall = {k: 0.0 for k in k_values}
    fusion_ndcg = {k: 0.0 for k in k_values}
    pop_recall = {k: 0.0 for k in k_values}

    sort_cols = ["userId"]
    if "timestamp" in ratings.columns:
        sort_cols.append("timestamp")
    ratings = ratings.sort_values(sort_cols)

    for _, group in ratings.groupby("userId"):
        if evaluated >= max_users:
            break
        rows = list(group.itertuples(index=False))
        if len(rows) < 2:
            continue

        target = int(rows[-1].movieId)
        seed_ids = [int(row.movieId) for row in rows[:-1]][-5:]
        recommendations = rank_seed_set(
            seed_ids,
            catalog,
            fusion_weights=fusion_weights,
            top_k=top_k,
        )
        if not recommendations:
            continue

        pop_recs = popularity_baseline(seed_ids, catalog.popular_movie_ids, top_k)
        evaluated += 1
        for k in k_values:
            fusion_recall[k] += recall_at_k(recommendations, target, k)
            fusion_ndcg[k] += ndcg_at_k(recommendations, target, k)
            pop_recall[k] += recall_at_k(pop_recs, target, k)

    if evaluated == 0:
        raise ValueError("no evaluable users with at least two ratings and valid fusion seeds")

    metrics: dict[str, Any] = {
        "top_k": top_k,
        "metric_ks": k_values,
        "user_count": evaluated,
        "fusion_weights": fusion_weights,
    }
    for k in k_values:
        metrics[f"recall_at_{k}"] = fusion_recall[k] / evaluated
        metrics[f"ndcg_at_{k}"] = fusion_ndcg[k] / evaluated
        metrics[f"popularity_baseline_recall_at_{k}"] = pop_recall[k] / evaluated
    return metrics


def load_fusion_weights(path: str) -> dict[str, float] | None:
    weights_path = Path(path)
    if not weights_path.exists():
        return None
    with open(weights_path, encoding="utf-8") as weights_file:
        return json.load(weights_file)


def evaluate(args: argparse.Namespace) -> dict:
    configure_artifact_paths(
        content_embeddings=args.content_embeddings,
        content_index=args.content_index,
        item_factors_svd=args.item_factors_svd,
        item_neighbors=args.item_neighbors,
        fusion_weights=args.fusion_weights,
    )

    ratings = pd.read_csv(args.ratings)
    catalog = load_eval_catalog(
        args.movies,
        serving_stats_json=args.serving_stats,
        ratings_csv=args.ratings,
    )
    k_values = parse_k_values(args.metric_ks, args.top_k)
    weights = load_fusion_weights(args.fusion_weights)

    metrics = run_evaluation(
        ratings,
        catalog,
        fusion_weights=weights,
        max_users=args.max_users,
        top_k=args.top_k,
        k_values=k_values,
    )
    metrics.update(
        {
            "ratings": args.ratings,
            "movies": args.movies,
            "fusion_weights_path": args.fusion_weights,
            "artifacts": {
                "content_embeddings": args.content_embeddings,
                "content_index": args.content_index,
                "item_factors_svd": args.item_factors_svd,
                "item_neighbors": args.item_neighbors,
            },
        }
    )
    return metrics


def main() -> None:
    args = parse_args()
    metrics = evaluate(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
