"""Grid-search Phase 1 fusion weights and write fusion_weights.json."""

from __future__ import annotations

import argparse
import json
import math
from itertools import product
from pathlib import Path

import pandas as pd

from eval_fusion import run_evaluation
from fusion_ranking import MODELS_DIR, configure_artifact_paths, load_eval_catalog


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune fusion weights on held-out seed retrieval")
    parser.add_argument("--ratings", default="ml-latest-small/ratings.csv")
    parser.add_argument("--movies", default=str(MODELS_DIR / "catalog_movies.csv"))
    parser.add_argument("--serving-stats", default=str(MODELS_DIR / "serving_stats.json"))
    parser.add_argument("--content-embeddings", default=str(MODELS_DIR / "content_embeddings.npz"))
    parser.add_argument("--content-index", default=str(MODELS_DIR / "content_index.json"))
    parser.add_argument("--item-factors-svd", default=str(MODELS_DIR / "item_factors_svd.npz"))
    parser.add_argument("--item-neighbors", default=str(MODELS_DIR / "item_neighbors.json"))
    parser.add_argument("--max-users", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=24)
    parser.add_argument(
        "--objective",
        choices=("recall_at_10", "ndcg_at_10", "recall_at_24", "ndcg_at_24"),
        default="recall_at_10",
    )
    parser.add_argument(
        "--grid-values",
        default="0,0.15,0.25,0.35,0.45",
        help="comma-separated weights sampled on the 4-channel simplex",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="use a small fixed candidate set for smoke runs",
    )
    parser.add_argument(
        "--output-weights",
        default=str(MODELS_DIR / "fusion_weights.json"),
    )
    parser.add_argument("--output-report", default="evaluation/results/fusion_tune.json")
    return parser.parse_args()


def default_weight_candidates() -> list[dict[str, float]]:
    return [
        {"content": 0.45, "svd": 0.20, "item_cf": 0.30, "pop": 0.05},
        {"content": 0.50, "svd": 0.20, "item_cf": 0.25, "pop": 0.05},
        {"content": 0.40, "svd": 0.25, "item_cf": 0.30, "pop": 0.05},
        {"content": 0.55, "svd": 0.15, "item_cf": 0.25, "pop": 0.05},
        {"content": 0.35, "svd": 0.25, "item_cf": 0.35, "pop": 0.05},
        {"content": 0.60, "svd": 0.15, "item_cf": 0.20, "pop": 0.05},
    ]


def simplex_grid(raw_values: str) -> list[dict[str, float]]:
    values = [float(part.strip()) for part in raw_values.split(",") if part.strip()]
    candidates: list[dict[str, float]] = []
    for content, svd, item_cf, pop in product(values, repeat=4):
        total = content + svd + item_cf + pop
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            continue
        if pop > 0.10:
            continue
        candidates.append(
            {"content": content, "svd": svd, "item_cf": item_cf, "pop": pop},
        )
    return candidates


def main() -> None:
    args = parse_args()
    configure_artifact_paths(
        content_embeddings=args.content_embeddings,
        content_index=args.content_index,
        item_factors_svd=args.item_factors_svd,
        item_neighbors=args.item_neighbors,
    )

    candidates = default_weight_candidates() if args.quick else simplex_grid(args.grid_values)
    if not candidates:
        raise ValueError("no valid weight candidates; adjust --grid-values or use --quick")

    ratings = pd.read_csv(args.ratings)
    catalog = load_eval_catalog(
        args.movies,
        serving_stats_json=args.serving_stats,
        ratings_csv=args.ratings,
    )
    k_values = [10, 24]

    trials: list[dict] = []
    best_weights = candidates[0]
    best_score = float("-inf")

    for weights in candidates:
        metrics = run_evaluation(
            ratings,
            catalog,
            fusion_weights=weights,
            max_users=args.max_users,
            top_k=args.top_k,
            k_values=k_values,
        )
        score = float(metrics[args.objective])
        trials.append(
            {
                "weights": weights,
                "score": score,
                "objective": args.objective,
                "recall_at_10": metrics["recall_at_10"],
                "ndcg_at_10": metrics["ndcg_at_10"],
                "recall_at_24": metrics["recall_at_24"],
                "ndcg_at_24": metrics["ndcg_at_24"],
            }
        )
        if score > best_score:
            best_score = score
            best_weights = weights

    weights_output = Path(args.output_weights)
    weights_output.parent.mkdir(parents=True, exist_ok=True)
    weights_output.write_text(json.dumps(best_weights, indent=2) + "\n", encoding="utf-8")

    report = {
        "objective": args.objective,
        "best_score": best_score,
        "best_weights": best_weights,
        "candidate_count": len(candidates),
        "trials": trials,
    }
    report_path = Path(args.output_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "best_weights": best_weights,
                "best_score": best_score,
                "objective": args.objective,
                "output_weights": str(weights_output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
