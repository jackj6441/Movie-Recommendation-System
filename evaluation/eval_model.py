import argparse
import json
import math
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate ONNX NCF rating model")
    parser.add_argument("--model", required=True, help="Path to ONNX model")
    parser.add_argument("--metadata", default="services/reco-api/models/metadata.json")
    parser.add_argument("--ratings", default="ml-latest-small/ratings.csv")
    parser.add_argument("--max-samples", type=int, default=1000)
    parser.add_argument("--output", default="evaluation/results/model_metrics.json")
    return parser.parse_args()


def load_metadata(path: str) -> tuple[dict[str, int], dict[str, int]]:
    with open(path, encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)
    user_id_to_idx = {str(key): int(value) for key, value in metadata["user_id_to_idx"].items()}
    movie_id_to_idx = {str(key): int(value) for key, value in metadata["movie_id_to_idx"].items()}
    return user_id_to_idx, movie_id_to_idx


def load_test_rows(path: str, max_samples: int) -> pd.DataFrame:
    ratings = pd.read_csv(path)
    required = {"userId", "movieId", "rating"}
    if not required.issubset(ratings.columns):
        raise ValueError("ratings CSV must contain userId, movieId, rating")
    sort_cols = ["userId"]
    if "timestamp" in ratings.columns:
        sort_cols.append("timestamp")
    ratings = ratings.sort_values(sort_cols)
    test_rows = ratings.groupby("userId", as_index=False).tail(1)
    return test_rows.head(max_samples)


def evaluate(args: argparse.Namespace) -> dict:
    user_id_to_idx, movie_id_to_idx = load_metadata(args.metadata)
    test_rows = load_test_rows(args.ratings, args.max_samples)

    user_indices: list[int] = []
    item_indices: list[int] = []
    labels: list[float] = []
    for row in test_rows.itertuples(index=False):
        user_key = str(int(row.userId))
        movie_key = str(int(row.movieId))
        if user_key not in user_id_to_idx or movie_key not in movie_id_to_idx:
            continue
        user_indices.append(user_id_to_idx[user_key])
        item_indices.append(movie_id_to_idx[movie_key])
        labels.append(float(row.rating))

    if not labels:
        raise ValueError("no evaluable rows after applying metadata mappings")

    session = ort.InferenceSession(args.model, providers=["CPUExecutionProvider"])
    outputs = session.run(
        ["pred_rating"],
        {
            "user_idx": np.array(user_indices, dtype=np.int64),
            "item_idx": np.array(item_indices, dtype=np.int64),
        },
    )[0]
    predictions = np.clip(outputs.astype(np.float32), 0.5, 5.0)
    label_array = np.array(labels, dtype=np.float32)
    rmse = math.sqrt(float(np.mean((predictions - label_array) ** 2)))

    return {
        "artifact": args.model,
        "metadata": args.metadata,
        "ratings": args.ratings,
        "split_strategy": "per-user last interaction",
        "sample_count": len(labels),
        "rmse": rmse,
    }


def main() -> None:
    args = parse_args()
    metrics = evaluate(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
