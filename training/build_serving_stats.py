"""Precompute serving statistics so the API does not scan raw ratings at boot.

For MovieLens 32M the ratings file is ~877MB / 32M rows. Reading it on every
API startup to compute popularity is slow and memory-heavy. This offline script
reads it once and writes a small ``serving_stats.json`` artifact containing the
distinct user/item counts and per-movie popularity for the served catalog.

The catalog is defined exactly like the content-embedding catalog: movies that
appear in ``movies.csv`` with at least ``--min-ratings`` ratings. Keeping the two
in sync guarantees that every popular/candidate movie can also be scored.
"""

import argparse
import json
import os

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build serving stats artifact")
    parser.add_argument("--ratings_csv", type=str, required=True)
    parser.add_argument("--movies_csv", type=str, required=True)
    parser.add_argument(
        "--min-ratings",
        dest="min_ratings",
        type=int,
        default=0,
        help="catalog cap; must match build_content_embeddings.py (0 = all movies)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("services", "reco-api", "models", "serving_stats.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    movies = pd.read_csv(args.movies_csv, usecols=["movieId"])
    catalog_ids = set(movies["movieId"].astype(int).tolist())

    ratings = pd.read_csv(args.ratings_csv, usecols=["userId", "movieId"])
    num_users = int(ratings["userId"].nunique())

    counts = ratings["movieId"].astype(int).value_counts()
    if args.min_ratings > 0:
        counts = counts[counts >= args.min_ratings]

    # Restrict popularity to the served catalog so popular_movie_ids only
    # contains movies that are present in the catalog and can be scored.
    counts = counts[counts.index.isin(catalog_ids)]

    movie_popularity = {str(int(mid)): int(cnt) for mid, cnt in counts.items()}
    popular_movie_ids = [int(mid) for mid in counts.sort_values(ascending=False).index.tolist()]

    stats = {
        "num_users": num_users,
        "num_items": len(popular_movie_ids),
        "min_ratings": args.min_ratings,
        "movie_popularity": movie_popularity,
        "popular_movie_ids": popular_movie_ids,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as stats_file:
        json.dump(stats, stats_file, ensure_ascii=False)

    print(f"num_users: {num_users}")
    print(f"num_items (catalog): {len(popular_movie_ids)}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
