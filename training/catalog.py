"""Load the served movie catalog in embedding row order."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DEFAULT_MODELS_DIR = Path("services") / "reco-api" / "models"


def load_catalog_movie_ids(models_dir: str | Path = DEFAULT_MODELS_DIR) -> np.ndarray:
    """Return ``movieId`` values in the same order as ``content_embeddings.npz`` rows.

    Prefer the NPZ ``movie_ids`` array when present; otherwise reconstruct order from
    ``content_index.json`` so offline factor/neighbor builds stay aligned with serving.
    """
    models_dir = Path(models_dir)
    npz_path = models_dir / "content_embeddings.npz"
    if npz_path.exists():
        return np.load(npz_path)["movie_ids"].astype(np.int64)

    index_path = models_dir / "content_index.json"
    if not index_path.exists():
        raise FileNotFoundError(
            f"Need {npz_path} or {index_path} to resolve the served catalog"
        )

    with open(index_path, encoding="utf-8") as index_file:
        movie_id_to_row = json.load(index_file)["movie_id_to_row"]

    n = len(movie_id_to_row)
    movie_ids = np.empty(n, dtype=np.int64)
    for movie_id_str, row in movie_id_to_row.items():
        movie_ids[int(row)] = int(movie_id_str)
    return movie_ids
