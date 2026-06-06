"""Tests for artifact manifest read/write and row-order alignment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app import artifact_bundle, artifact_manifest  # noqa: E402


def _write_tiny_models_dir(models_dir: Path, movie_ids: list[int]) -> None:
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
    artifact_manifest.write_content_manifest(models_dir, row_count=len(movie_ids))


def test_write_and_read_manifest_round_trip(tmp_path: Path):
    _write_tiny_models_dir(tmp_path, [10, 20, 30])
    manifest = artifact_manifest.read_manifest(tmp_path)
    assert manifest is not None
    assert manifest.row_count == 3
    assert manifest.content_embeddings == "content_embeddings.npz"


def test_load_catalog_movie_ids_uses_manifest_paths(tmp_path: Path):
    _write_tiny_models_dir(tmp_path, [10, 20, 30])
    loaded = artifact_manifest.load_catalog_movie_ids(tmp_path).tolist()
    assert loaded == [10, 20, 30]


def test_record_artifact_merges_retrieval_outputs(tmp_path: Path):
    _write_tiny_models_dir(tmp_path, [1, 2, 3])
    artifact_manifest.record_artifact(
        tmp_path,
        item_factors_svd="item_factors_svd.npz",
        item_neighbors="item_neighbors.json",
    )
    manifest = artifact_manifest.read_manifest(tmp_path)
    assert manifest is not None
    assert manifest.item_factors_svd == "item_factors_svd.npz"
    assert manifest.item_neighbors == "item_neighbors.json"


def test_load_artifact_bundle_resolves_paths_from_manifest(tmp_path: Path):
    _write_tiny_models_dir(tmp_path, [1, 2, 3])
    artifact_bundle.reset_default_bundle()
    bundle = artifact_bundle.load_artifact_bundle(
        content_embeddings_path=str(tmp_path / "content_embeddings.npz"),
        content_index_path=str(tmp_path / "content_index.json"),
    )
    assert bundle.content.filter_movie_ids([1, 99]) == [1]


def test_load_catalog_movie_ids_without_manifest_falls_back(tmp_path: Path):
    movie_ids = [5, 6]
    embeddings = np.random.randn(2, 4).astype(np.float32)
    np.savez_compressed(
        tmp_path / "content_embeddings.npz",
        embeddings=embeddings,
        movie_ids=np.array(movie_ids, dtype=np.int64),
    )
    loaded = artifact_manifest.load_catalog_movie_ids(tmp_path).tolist()
    assert loaded == movie_ids
