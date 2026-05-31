import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate seed-based retrieval quality")
    parser.add_argument("--ratings", default="ml-latest-small/ratings.csv")
    parser.add_argument("--movies", default="ml-latest-small/movies.csv")
    parser.add_argument("--content-embeddings", default="services/reco-api/models/content_embeddings.npz")
    parser.add_argument("--content-index", default="services/reco-api/models/content_index.json")
    parser.add_argument("--max-users", type=int, default=100)
    parser.add_argument("--candidate-pool", type=int, default=500)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--output", default="evaluation/results/retrieval_metrics.json")
    return parser.parse_args()


def load_content(index_path: str, embeddings_path: str) -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    data = np.load(embeddings_path)
    embeddings = data["embeddings"].astype(np.float32)
    movie_ids = data["movie_ids"].astype(np.int64)
    with open(index_path, encoding="utf-8") as index_file:
        raw = json.load(index_file).get("movie_id_to_row", {})
    movie_id_to_row = {int(key): int(value) for key, value in raw.items()}
    return embeddings, movie_ids, movie_id_to_row


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector if norm == 0 else vector / norm


def ranked_candidates(
    seed_ids: list[int],
    popular_ids: list[int],
    embeddings: np.ndarray,
    movie_id_to_row: dict[int, int],
    candidate_pool: int,
    k: int,
) -> list[int]:
    valid_seeds = [mid for mid in seed_ids if mid in movie_id_to_row]
    if not valid_seeds:
        return []
    seed_vectors = [embeddings[movie_id_to_row[mid]] for mid in valid_seeds]
    anchor = normalize(np.mean(seed_vectors, axis=0))
    excluded = set(valid_seeds)
    candidates = [
        mid
        for mid in popular_ids[: candidate_pool * 3]
        if mid not in excluded and mid in movie_id_to_row
    ][:candidate_pool]
    if not candidates:
        return []
    scores = np.array([float(embeddings[movie_id_to_row[mid]] @ anchor) for mid in candidates])
    top_indices = np.argsort(scores)[::-1][:k]
    return [int(candidates[idx]) for idx in top_indices]


def ndcg_for(target: int, recommendations: list[int]) -> float:
    if target not in recommendations:
        return 0.0
    rank = recommendations.index(target) + 1
    return 1.0 / math.log2(rank + 1)


def topk_diversity(recommendations: list[int], genres_by_movie: dict[int, set[str]]) -> float:
    pairs = 0
    total = 0.0
    for left_index, left_id in enumerate(recommendations):
        for right_id in recommendations[left_index + 1 :]:
            left = genres_by_movie.get(left_id, set())
            right = genres_by_movie.get(right_id, set())
            union = left | right
            similarity = (len(left & right) / len(union)) if union else 0.0
            total += 1.0 - similarity
            pairs += 1
    return total / pairs if pairs else 0.0


def evaluate(args: argparse.Namespace) -> dict:
    ratings = pd.read_csv(args.ratings)
    movies = pd.read_csv(args.movies)
    embeddings, _, movie_id_to_row = load_content(args.content_index, args.content_embeddings)

    sort_cols = ["userId"]
    if "timestamp" in ratings.columns:
        sort_cols.append("timestamp")
    ratings = ratings.sort_values(sort_cols)
    popularity = ratings["movieId"].value_counts()
    popular_ids = [int(mid) for mid in popularity.index.tolist()]
    all_movie_ids = set(int(mid) for mid in movies["movieId"].tolist())
    genres_by_movie = {
        int(row.movieId): set(str(row.genres).split("|")) - {"(no genres listed)"}
        for row in movies.itertuples(index=False)
    }

    evaluated = 0
    hits = 0
    popularity_hits = 0
    ndcg_total = 0.0
    diversity_total = 0.0
    unique_recommendations: set[int] = set()

    for _, group in ratings.groupby("userId"):
        if evaluated >= args.max_users:
            break
        rows = list(group.itertuples(index=False))
        if len(rows) < 2:
            continue
        target = int(rows[-1].movieId)
        seed_ids = [int(row.movieId) for row in rows[:-1]][-5:]
        recommendations = ranked_candidates(
            seed_ids,
            popular_ids,
            embeddings,
            movie_id_to_row,
            args.candidate_pool,
            args.k,
        )
        if not recommendations:
            continue
        popularity_recs = [mid for mid in popular_ids if mid not in set(seed_ids)][: args.k]

        evaluated += 1
        unique_recommendations.update(recommendations)
        if target in recommendations:
            hits += 1
        if target in popularity_recs:
            popularity_hits += 1
        ndcg_total += ndcg_for(target, recommendations)
        diversity_total += topk_diversity(recommendations, genres_by_movie)

    if evaluated == 0:
        raise ValueError("no evaluable users with at least two ratings and content-indexed seeds")

    recall = hits / evaluated
    return {
        "ratings": args.ratings,
        "movies": args.movies,
        "content_embeddings": args.content_embeddings,
        "content_index": args.content_index,
        "k": args.k,
        "user_count": evaluated,
        "recall_at_k": recall,
        "ndcg_at_k": ndcg_total / evaluated,
        "recommendation_coverage": len(unique_recommendations) / len(all_movie_ids),
        "topk_diversity": diversity_total / evaluated,
        "popularity_baseline_recall_at_k": popularity_hits / evaluated,
        "content_baseline_recall_at_k": recall,
    }


def main() -> None:
    args = parse_args()
    metrics = evaluate(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
