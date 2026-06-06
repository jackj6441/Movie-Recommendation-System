"""Truncated SVD on the user–item rating matrix for the served catalog.

Exports ``item_factors_svd.npz`` with ``movie_ids`` (int64, embedding row order)
and ``factors`` (float32, shape N x rank). Movies with no ratings in the input
file get a zero vector so row indices stay aligned with ``content_embeddings``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_TRAINING_DIR = Path(__file__).resolve().parent
if str(_TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(_TRAINING_DIR))

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

from catalog import DEFAULT_MODELS_DIR, load_catalog_movie_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build truncated-SVD item factors")
    parser.add_argument("--ratings_csv", type=str, required=True)
    parser.add_argument(
        "--models_dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help="directory with content_embeddings.npz / content_index.json",
    )
    parser.add_argument("--rank", type=int, default=64, help="SVD latent dimension")
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("services", "reco-api", "models", "item_factors_svd.npz"),
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=1_000_000,
        help="ratings CSV chunk size for large MovieLens files",
    )
    return parser.parse_args()


def _map_ids(series: pd.Series) -> tuple[np.ndarray, dict[int, int]]:
    unique = pd.unique(series.astype(np.int64))
    id_to_index = {int(value): idx for idx, value in enumerate(unique)}
    return unique, id_to_index


def build_user_item_matrix(
    ratings_csv: str,
    movie_ids: np.ndarray,
    chunksize: int,
) -> csr_matrix:
    """CSR matrix (users x items) with raw rating values for catalog columns only."""
    catalog_ids = set(int(mid) for mid in movie_ids.tolist())
    movie_id_to_col = {int(mid): col for col, mid in enumerate(movie_ids)}

    ratings_iter = pd.read_csv(
        ratings_csv,
        usecols=["userId", "movieId", "rating"],
        chunksize=chunksize,
    )

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    user_id_to_row: dict[int, int] | None = None

    for chunk in ratings_iter:
        chunk = chunk[chunk["movieId"].astype(int).isin(catalog_ids)]
        if chunk.empty:
            continue

        if user_id_to_row is None:
            user_ids, user_id_to_row = _map_ids(chunk["userId"])
        else:
            new_users = set(chunk["userId"].astype(int).tolist()) - set(user_id_to_row)
            if new_users:
                start = len(user_id_to_row)
                for offset, user_id in enumerate(sorted(new_users)):
                    user_id_to_row[user_id] = start + offset

        user_rows = chunk["userId"].astype(int).map(user_id_to_row).to_numpy()
        item_cols = chunk["movieId"].astype(int).map(movie_id_to_col).to_numpy()
        rows.extend(user_rows.tolist())
        cols.extend(item_cols.tolist())
        data.extend(chunk["rating"].astype(np.float32).tolist())

    if user_id_to_row is None:
        raise ValueError("No ratings found for movies in the served catalog")

    n_users = len(user_id_to_row)
    n_items = len(movie_ids)
    return csr_matrix(
        (data, (rows, cols)),
        shape=(n_users, n_items),
        dtype=np.float32,
    )


def truncated_svd_item_factors(matrix: csr_matrix, rank: int) -> np.ndarray:
    """Item latent vectors (n_items x rank), L2-normalized per row."""
    n_users, n_items = matrix.shape
    k = min(rank, n_users - 1, n_items - 1)
    if k < 1:
        return np.zeros((n_items, rank), dtype=np.float32)

    _, singular_values, vt = svds(matrix.astype(np.float64), k=k)
    order = np.argsort(-singular_values)
    singular_values = singular_values[order]
    vt = vt[order]

    factors = (vt.T * singular_values).astype(np.float32)
    if factors.shape[1] < rank:
        padded = np.zeros((n_items, rank), dtype=np.float32)
        padded[:, : factors.shape[1]] = factors
        factors = padded

    norms = np.linalg.norm(factors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    factors /= norms
    return factors


def main() -> None:
    args = parse_args()
    movie_ids = load_catalog_movie_ids(args.models_dir)
    matrix = build_user_item_matrix(args.ratings_csv, movie_ids, args.chunksize)

    rated_items = np.asarray(matrix.getnnz(axis=0)).ravel() > 0
    factors = truncated_svd_item_factors(matrix, args.rank)
    factors[~rated_items] = 0.0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        movie_ids=movie_ids.astype(np.int64),
        factors=factors.astype(np.float32),
    )

    reco_api = Path(__file__).resolve().parents[1] / "services" / "reco-api"
    if str(reco_api) not in sys.path:
        sys.path.insert(0, str(reco_api))
    from app.artifact_manifest import record_artifact

    record_artifact(args.models_dir, item_factors_svd=Path(args.output).name)

    nonzero = int(np.count_nonzero(rated_items))
    print(f"catalog_items: {len(movie_ids)}")
    print(f"rated_in_matrix: {nonzero}")
    print(f"users: {matrix.shape[0]}, rank: {factors.shape[1]}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    main()
