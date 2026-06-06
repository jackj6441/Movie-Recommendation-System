"""Load the served movie catalog in embedding row order."""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_MODELS_DIR = Path("services") / "reco-api" / "models"
_RECO_API_ROOT = Path(__file__).resolve().parents[1] / "services" / "reco-api"


def _ensure_reco_api_on_path() -> None:
    api_path = str(_RECO_API_ROOT)
    if api_path not in sys.path:
        sys.path.insert(0, api_path)


def load_catalog_movie_ids(models_dir: str | Path = DEFAULT_MODELS_DIR):
    """Return ``movieId`` values in the same order as ``content_embeddings.npz`` rows."""
    _ensure_reco_api_on_path()
    from app.artifact_manifest import load_catalog_movie_ids as load_ids

    return load_ids(models_dir)
