"""Build offline TMDB poster URLs for the served movie catalog.

Reads MovieLens links (movieId -> tmdbId), fetches poster_path from TMDB, and
writes poster_urls.json plus poster_meta.json for reco-api serving.

Requires TMDB_API_KEY in the environment. Run locally; commit the outputs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{tmdb_id}"
TMDB_ENV_KEYS = ("TMDB_API_KEY", "TMDB_V3_API_KEY")


def load_local_env() -> None:
    """Load repo-root .env into os.environ.

    TMDB_* keys always come from .env when present so a stale shell export
    cannot override the read access token stored locally.
    """
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    parsed: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            parsed[key] = value
    for key, value in parsed.items():
        if key in TMDB_ENV_KEYS or key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build TMDB poster lookup artifact")
    parser.add_argument(
        "--catalog",
        type=str,
        default=os.path.join("services", "reco-api", "models", "catalog_movies.csv"),
    )
    parser.add_argument("--links", type=str, default=os.path.join("ml-32m", "links.csv"))
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("services", "reco-api", "models", "poster_urls.json"),
    )
    parser.add_argument(
        "--meta-output",
        type=str,
        default=os.path.join("services", "reco-api", "models", "poster_meta.json"),
    )
    parser.add_argument("--sleep", type=float, default=0.25, help="seconds between TMDB calls")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="max TMDB fetches (0 = all catalog movies with tmdb ids)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="skip movie ids already present in --output",
    )
    return parser.parse_args()


def poster_urls_from_path(poster_path: str) -> dict[str, str]:
    return {
        "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}",
        "poster_thumb_url": f"https://image.tmdb.org/t/p/w185{poster_path}",
    }


def fetch_poster_path(
    session: requests.Session,
    tmdb_id: int,
    *,
    max_retries: int,
) -> str | None:
    url = TMDB_MOVIE_URL.format(tmdb_id=tmdb_id)
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue

        if response.status_code == 401:
            raise RuntimeError(
                "TMDB returned 401 Unauthorized. Check TMDB_API_KEY in .env "
                "(must be the read access token JWT, not the v3 API key)."
            )
        if response.status_code == 404:
            return None
        if response.status_code == 429:
            time.sleep(min(60, 2 ** (attempt + 2)))
            continue
        if response.status_code >= 500 or not response.text.strip():
            time.sleep(2 ** attempt)
            continue

        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.HTTPError, ValueError, requests.exceptions.JSONDecodeError):
            time.sleep(2 ** attempt)
            continue

        poster_path = payload.get("poster_path")
        if poster_path:
            return str(poster_path)
        return None
    return None


def main() -> None:
    load_local_env()
    args = parse_args()
    api_key = os.getenv("TMDB_API_KEY", "").strip()
    if not api_key:
        print("Error: set TMDB_API_KEY before running this script.", file=sys.stderr)
        sys.exit(1)

    catalog_path = Path(args.catalog)
    links_path = Path(args.links)
    if not catalog_path.is_file():
        print(f"Error: catalog not found at {catalog_path}", file=sys.stderr)
        sys.exit(1)
    if not links_path.is_file():
        print(f"Error: links not found at {links_path}", file=sys.stderr)
        sys.exit(1)

    catalog_ids = set(pd.read_csv(catalog_path, usecols=["movieId"])["movieId"].astype(int).tolist())
    links = pd.read_csv(links_path, usecols=["movieId", "tmdbId"])
    links = links[links["movieId"].astype(int).isin(catalog_ids)]
    links = links.dropna(subset=["tmdbId"])
    links["movieId"] = links["movieId"].astype(int)
    links["tmdbId"] = links["tmdbId"].astype(int)
    links = links[links["tmdbId"] > 0].drop_duplicates(subset=["movieId"])

    output_path = Path(args.output)
    existing: dict[str, dict[str, str]] = {}
    if args.resume and output_path.is_file():
        with output_path.open(encoding="utf-8") as output_file:
            raw = json.load(output_file)
            if isinstance(raw, dict):
                existing = {str(k): v for k, v in raw.items() if isinstance(v, dict)}

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {api_key}"
    session.headers["Accept"] = "application/json"

    candidates = [(int(row.movieId), int(row.tmdbId)) for row in links.itertuples(index=False)]
    if args.limit > 0:
        candidates = candidates[: args.limit]

    def write_artifacts() -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as output_file:
            json.dump(existing, output_file, ensure_ascii=False, indent=2)

    fetched = 0
    api_calls = 0
    for movie_id, tmdb_id in candidates:
        key = str(movie_id)
        if args.resume and key in existing:
            continue

        poster_path = fetch_poster_path(session, tmdb_id, max_retries=args.max_retries)
        api_calls += 1
        if poster_path:
            existing[key] = poster_urls_from_path(poster_path)

        fetched += 1
        if args.sleep > 0:
            time.sleep(args.sleep)

        if api_calls > 0 and api_calls % 100 == 0:
            write_artifacts()
            print(
                f"checkpoint: api_calls={api_calls} processed={fetched}/{len(candidates)} "
                f"posters={len(existing)}",
                flush=True,
            )

    write_artifacts()

    catalog_movies = len(catalog_ids)
    linked_movies = len(links)
    poster_count = len(existing)
    coverage = poster_count / catalog_movies if catalog_movies else 0.0
    meta = {
        "catalog_movies": catalog_movies,
        "linked_movies": int(linked_movies),
        "poster_count": poster_count,
        "poster_coverage": round(coverage, 6),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "links_path": str(links_path),
    }
    meta_path = Path(args.meta_output)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as meta_file:
        json.dump(meta, meta_file, ensure_ascii=False, indent=2)

    print(f"catalog_movies: {catalog_movies}")
    print(f"linked_movies: {linked_movies}")
    print(f"poster_count: {poster_count}")
    print(f"poster_coverage: {coverage:.4f}")
    print(f"output: {output_path}")
    print(f"meta: {meta_path}")


if __name__ == "__main__":
    main()
