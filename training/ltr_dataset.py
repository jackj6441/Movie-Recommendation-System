"""Build Lambdarank training rows from MovieLens ratings (same protocol as eval_fusion)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "evaluation"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from fusion_ranking import RECO_API_ROOT, configure_artifact_paths, load_eval_catalog  # noqa: E402

# Import serving feature builder after path setup
if str(RECO_API_ROOT) not in sys.path:
    sys.path.insert(0, str(RECO_API_ROOT))

from app.fusion import CHANNELS, feature_rows, merge_candidate_ids  # noqa: E402
from app.ltr import rating_to_relevance  # noqa: E402
from app.seed_ranker import collect_channel_hits  # noqa: E402
from app import content  # noqa: E402


def relevance_for_candidate(
    movie_id: int,
    target_id: int,
    target_rating: float,
    user_ratings: dict[int, float],
) -> int:
    if movie_id == target_id:
        return rating_to_relevance(target_rating)
    if movie_id in user_ratings:
        return rating_to_relevance(user_ratings[movie_id])
    return 0


def build_training_arrays(
    ratings_csv: str,
    movies_csv: str,
    serving_stats_json: str | None,
    max_users: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (features, labels, group_sizes) for LightGBM lambdarank."""
    configure_artifact_paths()
    ratings = pd.read_csv(ratings_csv)
    sort_cols = ["userId"]
    if "timestamp" in ratings.columns:
        sort_cols.append("timestamp")
    ratings = ratings.sort_values(sort_cols)

    eval_catalog = load_eval_catalog(movies_csv, serving_stats_json, ratings_csv)

    feature_rows_list: list[list[float]] = []
    labels: list[int] = []
    group_sizes: list[int] = []

    for user_id, group in ratings.groupby("userId"):
        if len(group_sizes) >= max_users:
            break
        rows = list(group.itertuples(index=False))
        if len(rows) < 2:
            continue

        target = int(rows[-1].movieId)
        target_rating = float(rows[-1].rating)
        seed_ids = [int(row.movieId) for row in rows[:-1]][-5:]
        user_ratings = {int(row.movieId): float(row.rating) for row in rows}

        valid_seeds = [mid for mid in seed_ids if mid in eval_catalog.movie_titles]
        valid_seeds = content.filter_movie_ids(valid_seeds)
        if not valid_seeds:
            continue

        exclude = set(valid_seeds)
        channel_hits = collect_channel_hits(valid_seeds, exclude, eval_catalog)
        merged_ids = merge_candidate_ids(channel_hits)
        if target not in merged_ids:
            continue

        rows_features = feature_rows(merged_ids, channel_hits)
        if not rows_features:
            continue

        group_sizes.append(len(rows_features))
        for movie_id, breakdown in rows_features:
            feature_rows_list.append([float(breakdown[ch]) for ch in CHANNELS])
            labels.append(
                relevance_for_candidate(movie_id, target, target_rating, user_ratings)
            )

    if not group_sizes:
        raise ValueError("no LTR training groups produced")

    return (
        np.asarray(feature_rows_list, dtype=np.float32),
        np.asarray(labels, dtype=np.int32),
        np.asarray(group_sizes, dtype=np.int32),
    )
