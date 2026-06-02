"""Create a small committed sample of MovieLens 32M for CI / eval smoke tests.

The full 32M ratings file (~877MB) cannot be committed. This script samples a
handful of users and writes a tiny ``data/ml-32m-sample/{ratings.csv,movies.csv}``
fixture in the same id space as the 32M-trained artifacts, so the evaluation
smoke tests run against data consistent with the committed model and embeddings.

Run this during the offline pipeline (after picking --min-ratings) and commit
the output alongside the 32M artifacts.
"""

import argparse
import os

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a committed ml-32m sample")
    parser.add_argument("--ratings_csv", type=str, default="ml-32m/ratings.csv")
    parser.add_argument("--movies_csv", type=str, default="ml-32m/movies.csv")
    parser.add_argument("--num-users", dest="num_users", type=int, default=300)
    parser.add_argument(
        "--min-ratings",
        dest="min_ratings",
        type=int,
        default=20,
        help="restrict sampled movies to the served catalog cap (match embeddings)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output_dir", type=str, default=os.path.join("data", "ml-32m-sample"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ratings = pd.read_csv(args.ratings_csv)

    # Restrict to catalog movies (>= min_ratings) so the sample matches the
    # committed content embeddings / catalog.
    if args.min_ratings > 0:
        counts = ratings["movieId"].value_counts()
        keep_ids = set(counts[counts >= args.min_ratings].index.tolist())
        ratings = ratings[ratings["movieId"].isin(keep_ids)]

    rng = pd.Series(ratings["userId"].unique()).sample(
        n=min(args.num_users, ratings["userId"].nunique()),
        random_state=args.seed,
    )
    sampled_users = set(rng.tolist())
    sample_ratings = ratings[ratings["userId"].isin(sampled_users)].copy()

    movies = pd.read_csv(args.movies_csv)
    sample_movie_ids = set(sample_ratings["movieId"].astype(int).tolist())
    sample_movies = movies[movies["movieId"].isin(sample_movie_ids)].copy()

    os.makedirs(args.output_dir, exist_ok=True)
    sample_ratings.to_csv(os.path.join(args.output_dir, "ratings.csv"), index=False)
    sample_movies.to_csv(os.path.join(args.output_dir, "movies.csv"), index=False)

    print(f"users: {len(sampled_users)}")
    print(f"ratings: {len(sample_ratings)}")
    print(f"movies: {len(sample_movies)}")
    print(f"output_dir: {args.output_dir}")


if __name__ == "__main__":
    main()
