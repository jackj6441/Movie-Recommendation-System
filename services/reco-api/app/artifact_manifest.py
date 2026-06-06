"""Artifact manifest for aligned serving and offline build paths."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

MANIFEST_FILENAME = "artifact_manifest.json"
SCHEMA_VERSION = 1

DEFAULT_CONTENT_EMBEDDINGS = "content_embeddings.npz"
DEFAULT_CONTENT_INDEX = "content_index.json"
DEFAULT_CATALOG_MOVIES = "catalog_movies.csv"
DEFAULT_ITEM_FACTORS_SVD = "item_factors_svd.npz"
DEFAULT_ITEM_NEIGHBORS = "item_neighbors.json"
DEFAULT_FUSION_WEIGHTS = "fusion_weights.json"
DEFAULT_LTR_MODEL = "ltr_model.txt"
DEFAULT_LTR_META = "ltr_meta.json"


@dataclass(frozen=True)
class ArtifactManifest:
    schema_version: int
    models_dir: str
    content_embeddings: str = DEFAULT_CONTENT_EMBEDDINGS
    content_index: str = DEFAULT_CONTENT_INDEX
    catalog_movies: str = DEFAULT_CATALOG_MOVIES
    item_factors_svd: str | None = None
    item_neighbors: str | None = None
    fusion_weights: str = DEFAULT_FUSION_WEIGHTS
    ltr_model: str | None = None
    ltr_meta: str | None = None
    row_count: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def resolve(self, models_dir: str | Path) -> dict[str, Path]:
        root = Path(models_dir)
        paths = {
            "content_embeddings": root / self.content_embeddings,
            "content_index": root / self.content_index,
            "catalog_movies": root / self.catalog_movies,
            "fusion_weights": root / self.fusion_weights,
        }
        if self.item_factors_svd:
            paths["item_factors_svd"] = root / self.item_factors_svd
        if self.item_neighbors:
            paths["item_neighbors"] = root / self.item_neighbors
        if self.ltr_model:
            paths["ltr_model"] = root / self.ltr_model
        if self.ltr_meta:
            paths["ltr_meta"] = root / self.ltr_meta
        return paths

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        extra = payload.pop("extra", {})
        payload.update(extra)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ArtifactManifest:
        known = {
            "schema_version",
            "models_dir",
            "content_embeddings",
            "content_index",
            "catalog_movies",
            "item_factors_svd",
            "item_neighbors",
            "fusion_weights",
            "ltr_model",
            "ltr_meta",
            "row_count",
        }
        extra = {key: value for key, value in payload.items() if key not in known}
        return cls(
            schema_version=int(payload["schema_version"]),
            models_dir=str(payload["models_dir"]),
            content_embeddings=str(payload.get("content_embeddings", DEFAULT_CONTENT_EMBEDDINGS)),
            content_index=str(payload.get("content_index", DEFAULT_CONTENT_INDEX)),
            catalog_movies=str(payload.get("catalog_movies", DEFAULT_CATALOG_MOVIES)),
            item_factors_svd=payload.get("item_factors_svd"),
            item_neighbors=payload.get("item_neighbors"),
            fusion_weights=str(payload.get("fusion_weights", DEFAULT_FUSION_WEIGHTS)),
            ltr_model=payload.get("ltr_model"),
            ltr_meta=payload.get("ltr_meta"),
            row_count=payload.get("row_count"),
            extra=extra,
        )


def manifest_path(models_dir: str | Path) -> Path:
    return Path(models_dir) / MANIFEST_FILENAME


def read_manifest(models_dir: str | Path) -> ArtifactManifest | None:
    path = manifest_path(models_dir)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as manifest_file:
        payload = json.load(manifest_file)
    return ArtifactManifest.from_dict(payload)


def write_manifest(models_dir: str | Path, manifest: ArtifactManifest) -> Path:
    root = Path(models_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = manifest_path(root)
    with open(path, "w", encoding="utf-8") as manifest_file:
        json.dump(manifest.to_dict(), manifest_file, indent=2, sort_keys=True)
        manifest_file.write("\n")
    return path


def default_manifest(models_dir: str | Path, *, row_count: int | None = None) -> ArtifactManifest:
    return ArtifactManifest(
        schema_version=SCHEMA_VERSION,
        models_dir=str(Path(models_dir)),
        row_count=row_count,
    )


def write_content_manifest(models_dir: str | Path, *, row_count: int) -> ArtifactManifest:
    manifest = default_manifest(models_dir, row_count=row_count)
    write_manifest(models_dir, manifest)
    return manifest


def record_artifact(models_dir: str | Path, **updates: str | int | None) -> ArtifactManifest:
    root = Path(models_dir)
    manifest = read_manifest(root) or default_manifest(root)
    data = manifest.to_dict()
    for key, value in updates.items():
        if key in data or key in {
            "content_embeddings",
            "content_index",
            "catalog_movies",
            "item_factors_svd",
            "item_neighbors",
            "fusion_weights",
            "ltr_model",
            "ltr_meta",
            "row_count",
        }:
            data[key] = value
    merged = ArtifactManifest.from_dict(data)
    write_manifest(root, merged)
    return merged


def load_content_row_movie_ids(
    embeddings_path: str | Path,
    index_path: str | Path,
) -> np.ndarray:
    """Return movie ids in embedding row order."""
    npz_path = Path(embeddings_path)
    if npz_path.exists():
        return np.load(npz_path)["movie_ids"].astype(np.int64)

    index_file = Path(index_path)
    if not index_file.exists():
        raise FileNotFoundError(f"Need {npz_path} or {index_file} to resolve embedding row order")

    with open(index_file, encoding="utf-8") as handle:
        movie_id_to_row = json.load(handle)["movie_id_to_row"]

    row_count = len(movie_id_to_row)
    movie_ids = np.empty(row_count, dtype=np.int64)
    for movie_id_str, row in movie_id_to_row.items():
        movie_ids[int(row)] = int(movie_id_str)
    return movie_ids


def load_catalog_movie_ids(models_dir: str | Path = "services/reco-api/models") -> np.ndarray:
    """Load served catalog ids in embedding row order using manifest paths when present."""
    root = Path(models_dir)
    manifest = read_manifest(root)
    if manifest is not None:
        paths = manifest.resolve(root)
        return load_content_row_movie_ids(
            paths["content_embeddings"],
            paths["content_index"],
        )
    return load_content_row_movie_ids(
        root / DEFAULT_CONTENT_EMBEDDINGS,
        root / DEFAULT_CONTENT_INDEX,
    )


def resolve_bundle_paths(
    models_dir: str | Path,
    *,
    content_embeddings_path: str | None = None,
    content_index_path: str | None = None,
    fusion_weights_path: str | None = None,
    item_factors_svd_path: str | None = None,
    item_neighbors_path: str | None = None,
    ltr_model_path: str | None = None,
    ltr_meta_path: str | None = None,
) -> dict[str, str]:
    """Fill missing artifact paths from manifest defaults under ``models_dir``."""
    root = Path(models_dir)
    manifest = read_manifest(root)
    resolved = {
        "content_embeddings_path": content_embeddings_path,
        "content_index_path": content_index_path,
        "fusion_weights_path": fusion_weights_path,
        "item_factors_svd_path": item_factors_svd_path,
        "item_neighbors_path": item_neighbors_path,
        "ltr_model_path": ltr_model_path,
        "ltr_meta_path": ltr_meta_path,
    }
    if manifest is None:
        defaults = {
            "content_embeddings_path": str(root / DEFAULT_CONTENT_EMBEDDINGS),
            "content_index_path": str(root / DEFAULT_CONTENT_INDEX),
            "fusion_weights_path": str(root / DEFAULT_FUSION_WEIGHTS),
            "item_factors_svd_path": str(root / DEFAULT_ITEM_FACTORS_SVD),
            "item_neighbors_path": str(root / DEFAULT_ITEM_NEIGHBORS),
            "ltr_model_path": str(root / DEFAULT_LTR_MODEL),
            "ltr_meta_path": str(root / DEFAULT_LTR_META),
        }
        for key, value in defaults.items():
            if resolved[key] is None:
                resolved[key] = value
        return resolved

    manifest_paths = manifest.resolve(root)
    manifest_defaults = {
        "content_embeddings_path": str(manifest_paths["content_embeddings"]),
        "content_index_path": str(manifest_paths["content_index"]),
        "fusion_weights_path": str(manifest_paths["fusion_weights"]),
        "item_factors_svd_path": str(manifest_paths.get("item_factors_svd", root / DEFAULT_ITEM_FACTORS_SVD)),
        "item_neighbors_path": str(manifest_paths.get("item_neighbors", root / DEFAULT_ITEM_NEIGHBORS)),
        "ltr_model_path": str(manifest_paths.get("ltr_model", root / DEFAULT_LTR_MODEL)),
        "ltr_meta_path": str(manifest_paths.get("ltr_meta", root / DEFAULT_LTR_META)),
    }
    for key, value in manifest_defaults.items():
        if resolved[key] is None:
            resolved[key] = value
    return resolved
