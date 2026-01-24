import argparse
import json
import os
from typing import Tuple

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build content embeddings")
    parser.add_argument("--movies_csv", type=str, default="ml-latest-small/movies.csv")
    parser.add_argument("--model_name", type=str, default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--device", type=str, default="cpu")
    return parser.parse_args()


def load_movies(path: str) -> Tuple[list[int], list[str]]:
    movies = pd.read_csv(path)
    if not {"movieId", "title", "genres"}.issubset(movies.columns):
        raise ValueError("movies CSV must contain movieId, title, genres")
    movie_ids = movies["movieId"].astype(int).tolist()
    texts = (movies["title"].fillna("") + " " + movies["genres"].fillna(""))
    return movie_ids, texts.tolist()


def main() -> None:
    args = parse_args()
    movie_ids, texts = load_movies(args.movies_csv)

    device = args.device
    if device == "mps" and not torch.backends.mps.is_available():
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

    movie_ids_array = np.array(movie_ids, dtype=np.int64)
    np.savez_compressed(npz_path, embeddings=embeddings, movie_ids=movie_ids_array)

    movie_id_to_row = {str(mid): int(idx) for idx, mid in enumerate(movie_ids)}
    with open(index_path, "w", encoding="utf-8") as index_file:
        json.dump({"movie_id_to_row": movie_id_to_row}, index_file, ensure_ascii=False)

    print(f"N: {embeddings.shape[0]}, D: {embeddings.shape[1]}")
    print(f"npz_path: {npz_path}")


if __name__ == "__main__":
    main()
