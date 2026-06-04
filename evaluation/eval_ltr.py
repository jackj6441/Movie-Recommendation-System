"""Evaluate Phase 2 LTR ranking (Recall / NDCG @10 and @24)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from eval_fusion import evaluate, parse_args as fusion_parse_args
from fusion_ranking import MODELS_DIR, configure_artifact_paths

RECO_API = Path(__file__).resolve().parents[1] / "services" / "reco-api"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate LightGBM LTR vs fusion baseline")
    parser.add_argument("--ratings", default="ml-latest-small/ratings.csv")
    parser.add_argument("--movies", default=str(MODELS_DIR / "catalog_movies.csv"))
    parser.add_argument("--serving-stats", default=str(MODELS_DIR / "serving_stats.json"))
    parser.add_argument("--ltr-model", default=str(MODELS_DIR / "ltr_model.txt"))
    parser.add_argument("--ltr-meta", default=str(MODELS_DIR / "ltr_meta.json"))
    parser.add_argument("--max-users", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=24)
    parser.add_argument("--output", default="evaluation/results/ltr_metrics.json")
    parser.add_argument("--compare-fusion", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not Path(args.ltr_model).exists():
        raise SystemExit(f"LTR model not found: {args.ltr_model}. Run training/train_lambdarank.py first.")

    os.environ["RANKING_MODE"] = "ltr"
    os.environ["LTR_MODEL_PATH"] = args.ltr_model
    os.environ["LTR_META_PATH"] = args.ltr_meta
    configure_artifact_paths()

    ltr_args = fusion_parse_args([])
    ltr_args.ratings = args.ratings
    ltr_args.movies = args.movies
    ltr_args.serving_stats = args.serving_stats
    ltr_args.max_users = args.max_users
    ltr_args.top_k = args.top_k
    ltr_args.metric_ks = "10,24"
    ltr_args.fusion_weights = str(MODELS_DIR / "fusion_weights.json")
    ltr_args.content_embeddings = str(MODELS_DIR / "content_embeddings.npz")
    ltr_args.content_index = str(MODELS_DIR / "content_index.json")
    ltr_args.item_factors_svd = str(MODELS_DIR / "item_factors_svd.npz")
    ltr_args.item_neighbors = str(MODELS_DIR / "item_neighbors.json")

    metrics = evaluate(ltr_args)
    metrics["ranking_mode"] = "multi_retriever_ltr"

    if args.compare_fusion:
        os.environ["RANKING_MODE"] = "fusion"
        fusion_metrics = evaluate(ltr_args)
        metrics["fusion_baseline"] = fusion_metrics

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
