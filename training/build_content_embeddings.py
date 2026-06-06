import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build content embeddings")
    parser.add_argument("--movies_csv", type=str, default="ml-latest-small/movies.csv")
    parser.add_argument(
        "--ratings_csv",
        type=str,
        default=None,
        help="ratings CSV used to count per-movie ratings for the --min-ratings cap",
    )
    parser.add_argument(
        "--min-ratings",
        dest="min_ratings",
        type=int,
        default=0,
        help="only embed movies with at least this many ratings (0 = embed all)",
    )
    parser.add_argument("--model_name", type=str, default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--device", type=str, default="cpu")
    return parser.parse_args()


def load_movies(path: str) -> pd.DataFrame:
    movies = pd.read_csv(path)
    if not {"movieId", "title", "genres"}.issubset(movies.columns):
        raise ValueError("movies CSV must contain movieId, title, genres")
    movies = movies.copy()
    movies["movieId"] = movies["movieId"].astype(int)
    return movies


def filter_by_min_ratings(movies: pd.DataFrame, ratings_csv: str | None, min_ratings: int) -> pd.DataFrame:
    """Keep only movies with at least ``min_ratings`` ratings.

    Capping the catalog to movies with enough ratings keeps the committed
    embedding artifact small while still covering popular and recent titles.
    """
    if min_ratings <= 0:
        return movies
    if not ratings_csv:
        raise ValueError("--ratings_csv is required when --min-ratings > 0")
    counts = (
        pd.read_csv(ratings_csv, usecols=["movieId"])["movieId"].astype(int).value_counts()
    )
    keep_ids = set(counts[counts >= min_ratings].index.tolist())
    filtered = movies[movies["movieId"].isin(keep_ids)].reset_index(drop=True)
    print(
        f"min_ratings={min_ratings}: kept {len(filtered)} of {len(movies)} movies"
    )
    return filtered


def main() -> None:
    args = parse_args()
    movies = load_movies(args.movies_csv)
    movies = filter_by_min_ratings(movies, args.ratings_csv, args.min_ratings)

    movie_ids = movies["movieId"].astype(int).tolist()
    texts = (movies["title"].fillna("") + " " + movies["genres"].fillna("")).tolist()

    device = args.device
    if device == "mps" and not torch.backends.mps.is_available():
        device = "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        device = "cpu"

    model = SentenceTransformer(args.model_name, device=device)
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    export_dir = os.path.join("services", "reco-api", "models")
    os.makedirs(export_dir, exist_ok=True)
    npz_path = os.path.join(export_dir, "content_embeddings.npz")
    index_path = os.path.join(export_dir, "content_index.json")
    catalog_path = os.path.join(export_dir, "catalog_movies.csv")

    movie_ids_array = np.array(movie_ids, dtype=np.int64)
    np.savez_compressed(npz_path, embeddings=embeddings, movie_ids=movie_ids_array)

    movie_id_to_row = {str(mid): int(idx) for idx, mid in enumerate(movie_ids)}
    with open(index_path, "w", encoding="utf-8") as index_file:
        json.dump({"movie_id_to_row": movie_id_to_row}, index_file, ensure_ascii=False)

    # The served catalog is exactly the embedded set so search, seeds, and
    # scoring stay consistent (no movie that cannot be scored is shown).
    movies[["movieId", "title", "genres"]].to_csv(catalog_path, index=False)

    reco_api = Path(__file__).resolve().parents[1] / "services" / "reco-api"
    if str(reco_api) not in sys.path:
        sys.path.insert(0, str(reco_api))
    from app.artifact_manifest import write_content_manifest

    write_content_manifest(export_dir, row_count=embeddings.shape[0])

    print(f"N: {embeddings.shape[0]}, D: {embeddings.shape[1]}")
    print(f"npz_path: {npz_path}")
    print(f"catalog_path: {catalog_path}")


if __name__ == "__main__":
    main()
