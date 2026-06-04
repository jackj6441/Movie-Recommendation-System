"""Tests for Phase 2 LTR training and serving hooks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "reco-api"
sys.path.insert(0, str(API_ROOT))

from app.fusion import CHANNELS, feature_rows  # noqa: E402
from app.ltr import rating_to_relevance  # noqa: E402


def test_rating_to_relevance_grades():
    assert rating_to_relevance(4.5) == 2
    assert rating_to_relevance(3.0) == 1
    assert rating_to_relevance(2.5) == 0


def test_feature_rows_aligns_with_channels():
    hits = {
        "content": [(1, 0.2), (2, 0.8)],
        "svd": [],
        "item_cf": [],
        "pop": [(2, 100.0)],
    }
    rows = feature_rows([1, 2], hits)
    assert len(rows) == 2
    assert set(rows[0][1].keys()) == set(CHANNELS)
    assert rows[1][1]["content"] == 1.0


def test_train_lambdarank_cli_smoke(tmp_path):
    model_path = tmp_path / "ltr_model.txt"
    meta_path = tmp_path / "ltr_meta.json"
    result = subprocess.run(
        [
            sys.executable,
            "training/train_lambdarank.py",
            "--ratings",
            "ml-latest-small/ratings.csv",
            "--movies",
            "ml-latest-small/movies.csv",
            "--max-users",
            "15",
            "--num-boost-round",
            "10",
            "--output-model",
            str(model_path),
            "--output-meta",
            str(meta_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0 and "libomp" in (result.stderr + result.stdout):
        pytest.skip("lightgbm requires libomp on this host")
    assert result.returncode == 0, result.stderr
    assert model_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["feature_names"] == ["content", "svd", "item_cf", "pop"]
