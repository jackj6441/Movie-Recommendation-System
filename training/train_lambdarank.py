"""Train LightGBM Lambdarank on four-channel retrieval features."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ltr_dataset import build_training_arrays

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODELS = REPO_ROOT / "services" / "reco-api" / "models"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Phase 2 LightGBM Lambdarank model")
    parser.add_argument("--ratings", default="ml-latest-small/ratings.csv")
    parser.add_argument("--movies", default=str(DEFAULT_MODELS / "catalog_movies.csv"))
    parser.add_argument("--serving-stats", default=str(DEFAULT_MODELS / "serving_stats.json"))
    parser.add_argument("--max-users", type=int, default=500)
    parser.add_argument("--num-boost-round", type=int, default=80)
    parser.add_argument("--output-model", default=str(DEFAULT_MODELS / "ltr_model.txt"))
    parser.add_argument("--output-meta", default=str(DEFAULT_MODELS / "ltr_meta.json"))
    parser.add_argument(
        "--output-dataset",
        default="",
        help="optional path to save feature matrix npz for debugging",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import lightgbm as lgb
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("lightgbm is required: pip install lightgbm") from exc

    features, labels, group_sizes = build_training_arrays(
        args.ratings,
        args.movies,
        args.serving_stats,
        args.max_users,
    )

    if args.output_dataset:
        out = Path(args.output_dataset)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            out,
            features=features,
            labels=labels,
            group_sizes=group_sizes,
        )

    feature_names = ["content", "svd", "item_cf", "pop"]
    train_set = lgb.Dataset(
        features,
        label=labels,
        group=group_sizes.tolist(),
        feature_name=feature_names,
    )

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "eval_at": [10, 24],
        "label_gain": [0, 1, 3],
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_data_in_leaf": 20,
        "verbosity": -1,
    }

    booster = lgb.train(params, train_set, num_boost_round=args.num_boost_round)

    model_path = Path(args.output_model)
    meta_path = Path(args.output_meta)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(model_path))

    meta = {
        "feature_names": feature_names,
        "trained_at": datetime.now(UTC).isoformat(),
        "ratings": args.ratings,
        "movies": args.movies,
        "max_users": args.max_users,
        "num_groups": int(len(group_sizes)),
        "num_rows": int(len(labels)),
        "params": params,
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(meta, sort_keys=True))


if __name__ == "__main__":
    main()
