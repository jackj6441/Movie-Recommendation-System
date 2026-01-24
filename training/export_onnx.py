import argparse
import glob
import json
import os
import re

import numpy as np
import onnxruntime as ort
import pandas as pd
import torch

from lightning_ncf import LightningNCF


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export NCF model to ONNX")
    parser.add_argument("--ckpt_path", type=str, default=None)
    return parser.parse_args()


def find_best_checkpoint(checkpoint_dir: str) -> str:
    pattern = os.path.join(checkpoint_dir, "*.ckpt")
    candidates = glob.glob(pattern)
    if not candidates:
        raise FileNotFoundError(f"No checkpoints found in {checkpoint_dir}")

    def extract_rmse(path: str) -> float:
        match = re.search(r"val_rmse=([0-9]+(?:\.[0-9]+)?)", os.path.basename(path))
        if match:
            return float(match.group(1))
        return float("inf")

    return min(candidates, key=extract_rmse)


def resolve_ratings_path() -> str:
    env_path = os.getenv("RATINGS_CSV_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    default_path = "data/ml-latest-small/ratings.csv"
    if os.path.exists(default_path):
        return default_path
    return "ml-latest-small/ratings.csv"


def build_metadata(ratings_path: str) -> dict:
    ratings = pd.read_csv(ratings_path)
    user_codes, user_uniques = pd.factorize(ratings["userId"], sort=True)
    item_codes, item_uniques = pd.factorize(ratings["movieId"], sort=True)
    user_id_to_idx = {str(uid): int(idx) for idx, uid in enumerate(user_uniques)}
    movie_id_to_idx = {str(mid): int(idx) for idx, mid in enumerate(item_uniques)}
    return {
        "num_users": len(user_uniques),
        "num_items": len(item_uniques),
        "user_id_to_idx": user_id_to_idx,
        "movie_id_to_idx": movie_id_to_idx,
    }


def main() -> None:
    args = parse_args()
    checkpoint_dir = os.path.join("training", "checkpoints")
    ckpt_path = args.ckpt_path or find_best_checkpoint(checkpoint_dir)

    model = LightningNCF.load_from_checkpoint(ckpt_path, map_location="cpu")
    model.eval()
    ncf = model.model.cpu()

    num_users = int(model.hparams.num_users)
    num_items = int(model.hparams.num_items)

    export_dir = os.path.join("services", "reco-api", "models")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "ncf.onnx")
    metadata_path = os.path.join(export_dir, "metadata.json")

    metadata = build_metadata(resolve_ratings_path())
    with open(metadata_path, "w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, ensure_ascii=False)

    dummy_users = torch.randint(0, num_users, (4,), dtype=torch.long, device="cpu")
    dummy_items = torch.randint(0, num_items, (4,), dtype=torch.long, device="cpu")

    torch.onnx.export(
        ncf,
        (dummy_users, dummy_items),
        export_path,
        input_names=["user_idx", "item_idx"],
        output_names=["pred_rating"],
        dynamic_axes={"user_idx": {0: "batch"}, "item_idx": {0: "batch"}, "pred_rating": {0: "batch"}},
        opset_version=13,
        dynamo=False,
    )

    ort_session = ort.InferenceSession(export_path, providers=["CPUExecutionProvider"])
    test_users = torch.randint(0, num_users, (16,), dtype=torch.long, device="cpu")
    test_items = torch.randint(0, num_items, (16,), dtype=torch.long, device="cpu")
    with torch.no_grad():
        torch_out = ncf(test_users, test_items).cpu().numpy()
    ort_inputs = {
        "user_idx": test_users.cpu().numpy().astype(np.int64),
        "item_idx": test_items.cpu().numpy().astype(np.int64),
    }
    ort_out = ort_session.run(["pred_rating"], ort_inputs)[0]
    max_abs_diff = np.max(np.abs(torch_out - ort_out))
    print(f"max_abs_diff: {max_abs_diff}")


if __name__ == "__main__":
    main()
