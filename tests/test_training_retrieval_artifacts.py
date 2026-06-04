"""Smoke tests for offline SVD and item-neighbor build scripts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
TRAINING_DIR = REPO_ROOT / "training"
sys.path.insert(0, str(TRAINING_DIR))

from build_item_neighbors import accumulate_cooccurrence, top_neighbors  # noqa: E402
from build_svd_factors import build_user_item_matrix, truncated_svd_item_factors  # noqa: E402
from catalog import load_catalog_movie_ids  # noqa: E402


def _write_tiny_catalog(models_dir: Path, movie_ids: list[int]) -> None:
    models_dir.mkdir(parents=True, exist_ok=True)
    embeddings = np.random.randn(len(movie_ids), 8).astype(np.float32)
    np.savez_compressed(
        models_dir / "content_embeddings.npz",
        embeddings=embeddings,
        movie_ids=np.array(movie_ids, dtype=np.int64),
    )
    movie_id_to_row = {str(mid): idx for idx, mid in enumerate(movie_ids)}
    with open(models_dir / "content_index.json", "w", encoding="utf-8") as index_file:
        json.dump({"movie_id_to_row": movie_id_to_row}, index_file)


def test_catalog_load_order(tmp_path: Path) -> None:
    movie_ids = [10, 20, 30]
    _write_tiny_catalog(tmp_path, movie_ids)
    loaded = load_catalog_movie_ids(tmp_path).tolist()
    assert loaded == movie_ids


def test_svd_factors_shape_and_alignment(tmp_path: Path) -> None:
    movie_ids = [1, 2, 3, 4]
    _write_tiny_catalog(tmp_path, movie_ids)
    ratings = pd.DataFrame(
        {
            "userId": [1, 1, 2, 2, 3],
            "movieId": [1, 2, 2, 3, 4],
            "rating": [4.0, 3.0, 5.0, 4.0, 2.0],
        }
    )
    ratings_path = tmp_path / "ratings.csv"
    ratings.to_csv(ratings_path, index=False)

    catalog = load_catalog_movie_ids(tmp_path)
    matrix = build_user_item_matrix(str(ratings_path), catalog, chunksize=10_000)
    factors = truncated_svd_item_factors(matrix, rank=2)

    assert factors.shape == (4, 2)
    assert matrix.shape == (3, 4)
    assert np.isfinite(factors).all()


def test_item_neighbors_scores(tmp_path: Path) -> None:
    catalog_ids = {1, 2, 3}
    ratings = pd.DataFrame(
        {
            "userId": [1, 1, 1, 2, 2],
            "movieId": [1, 2, 3, 1, 2],
        }
    )
    ratings_path = tmp_path / "ratings.csv"
    ratings.to_csv(ratings_path, index=False)

    pair_counts, degree = accumulate_cooccurrence(
        str(ratings_path),
        catalog_ids,
        chunksize=10_000,
        max_movies_per_user=200,
    )
    neighbors = top_neighbors([1, 2, 3], pair_counts, degree, top_k=2)

    assert neighbors["1"][0][0] in (2, 3)
    assert neighbors["1"][0][1] > 0
    assert {entry[0] for entry in neighbors["3"]} == {1, 2}
