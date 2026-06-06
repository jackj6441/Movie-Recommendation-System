import json
import os
from typing import Tuple

import numpy as np

from app.artifact_bundle import get_default_bundle, load_artifact_bundle


def _load_embeddings() -> Tuple[np.ndarray, np.ndarray, dict[int, int]]:
    content = get_default_bundle().content
    return content.embeddings, content.movie_ids, content.movie_id_to_row


def get_similar(movie_id: int, topn: int = 10) -> list[tuple[int, float]]:
    return get_default_bundle().content.get_similar(movie_id, topn=topn)


def get_similarity_scores(anchor_movie_id: int, candidate_movie_ids: list[int]) -> list[float]:
    return get_default_bundle().content.get_similarity_scores(anchor_movie_id, candidate_movie_ids)


def filter_movie_ids(movie_ids: list[int]) -> list[int]:
    return get_default_bundle().content.filter_movie_ids(movie_ids)


def get_embeddings_for_movies(movie_ids: list[int]) -> list[np.ndarray]:
    return get_default_bundle().content.get_embeddings_for_movies(movie_ids)


def get_similarity_scores_from_vector(anchor_vec: np.ndarray, candidate_movie_ids: list[int]) -> list[float]:
    return get_default_bundle().content.get_similarity_scores_from_vector(anchor_vec, candidate_movie_ids)
