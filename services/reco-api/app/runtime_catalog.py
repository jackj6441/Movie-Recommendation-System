"""Runtime movie catalog: one startup load, focused views for ranking and resolver."""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app import posters, seed_ranker
from app.rag_resolve import GenreSeedIdsFn, GetTitleFn, SearchMoviesFn

_YEAR_RE = re.compile(r"\((\d{4})\)")

_default_catalog: RuntimeCatalog | None = None


@dataclass(frozen=True)
class SearchHit:
    movie_id: int
    title: str


def parse_year(title: str) -> int | None:
    matches = _YEAR_RE.findall(title)
    return int(matches[-1]) if matches else None


@dataclass(frozen=True)
class RuntimeCatalog:
    movie_titles: dict[int, str]
    movie_genres: dict[int, list[str]]
    movie_years: dict[int, int]
    movie_popularity: dict[int, int]
    popular_movie_ids: list[int]
    known_genres: set[str]
    candidate_pool: int
    num_users: int = 0
    num_items: int = 0

    def get_popular_movies(self, movie_ids: list[int], limit: int) -> list[int]:
        ranked = sorted(movie_ids, key=lambda mid: self.movie_popularity.get(mid, 0), reverse=True)
        return ranked[:limit]

    def get_title(self, movie_id: int) -> str:
        return self.movie_titles.get(movie_id, f"Movie {movie_id}")

    def known_movie_ids(self) -> set[int]:
        return set(self.movie_titles)

    def search_movies(self, query: str) -> list[SearchHit]:
        q = query.strip().lower()
        if not q:
            return []
        hits: list[SearchHit] = []
        for movie_id, title in self.movie_titles.items():
            if q in title.lower():
                hits.append(SearchHit(movie_id=movie_id, title=title))
                if len(hits) >= 20:
                    break
        return hits

    def genre_seed_ids(
        self,
        genre: str,
        limit: int,
        *,
        year_min: int | None = None,
    ) -> list[int]:
        genre_key = genre.strip().lower()
        if not genre_key:
            return []
        if genre_key == "all":
            movie_ids = list(self.movie_titles.keys())
        else:
            movie_ids = [
                movie_id
                for movie_id, genres in self.movie_genres.items()
                if any(g.lower() == genre_key for g in genres)
            ]
        if year_min is not None:
            movie_ids = [
                movie_id
                for movie_id in movie_ids
                if self.movie_years.get(movie_id, 0) >= year_min
            ]
        return self.get_popular_movies(movie_ids, limit)

    def popular_movie_ids_limited(self, limit: int) -> list[int]:
        return self.get_popular_movies(list(self.movie_titles.keys()), limit)

    def as_resolve_hooks(self) -> tuple[SearchMoviesFn, GenreSeedIdsFn, GetTitleFn]:
        return self.search_movies, self.genre_seed_ids, self.get_title

    def for_ranking(self) -> seed_ranker.Catalog:
        return seed_ranker.Catalog(
            movie_titles=self.movie_titles,
            popular_movie_ids=self.popular_movie_ids,
            candidate_pool=self.candidate_pool,
            movie_genres=self.movie_genres,
            movie_years=self.movie_years,
            movie_popularity=self.movie_popularity,
        )

    def movie_payload(
        self,
        movie_id: int,
        poster_lookup: dict[int, dict[str, str]],
        **fields: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"movie_id": movie_id, "title": self.get_title(movie_id), **fields}
        return posters.enrich_movie(movie_id, payload, poster_lookup)

    def search_payloads(
        self,
        query: str,
        poster_lookup: dict[int, dict[str, str]],
    ) -> list[dict[str, Any]]:
        return [
            posters.enrich_movie(
                hit.movie_id,
                {"movie_id": hit.movie_id, "title": hit.title},
                poster_lookup,
            )
            for hit in self.search_movies(query)
        ]

    def health_fields(self) -> dict[str, Any]:
        return {
            "catalog_ok": bool(self.movie_titles),
            "num_users": self.num_users,
            "num_items": self.num_items,
            "candidate_pool": self.candidate_pool,
        }


def _load_movies_csv(movies_csv_path: str | Path) -> tuple[
    dict[int, str],
    dict[int, list[str]],
    dict[int, int],
    set[str],
]:
    movie_titles: dict[int, str] = {}
    movie_genres: dict[int, list[str]] = {}
    movie_years: dict[int, int] = {}
    known_genres: set[str] = set()

    try:
        with open(movies_csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                movie_id = int(row.get("movieId", "0"))
                title = row.get("title", "").strip()
                genres_value = row.get("genres", "")
                if movie_id and title:
                    movie_titles[movie_id] = title
                    genre_list = [g for g in genres_value.split("|") if g and g != "(no genres listed)"]
                    movie_genres[movie_id] = genre_list
                    known_genres.update(genre_list)
                    year = parse_year(title)
                    if year is not None:
                        movie_years[movie_id] = year
    except OSError:
        print(f"Warning: failed to load movies CSV at {movies_csv_path}")

    return movie_titles, movie_genres, movie_years, known_genres


def _load_serving_stats(
    serving_stats_path: str | Path,
    *,
    num_users: int,
    num_items: int,
) -> tuple[dict[int, int], list[int], int, int, bool]:
    if not os.path.exists(serving_stats_path):
        return {}, [], num_users, num_items, False

    try:
        with open(serving_stats_path, encoding="utf-8") as stats_file:
            stats = json.load(stats_file)
        movie_popularity = {
            int(key): int(value) for key, value in stats.get("movie_popularity", {}).items()
        }
        popular_movie_ids = [int(mid) for mid in stats.get("popular_movie_ids", [])]
        loaded_users = int(stats.get("num_users", num_users))
        loaded_items = int(stats.get("num_items", num_items))
        return movie_popularity, popular_movie_ids, loaded_users, loaded_items, True
    except (OSError, ValueError):
        print(f"Warning: failed to load serving stats at {serving_stats_path}")
        return {}, [], num_users, num_items, False


def _load_popularity_from_ratings(
    ratings_csv_path: str | Path,
    *,
    num_users: int,
    num_items: int,
) -> tuple[dict[int, int], list[int], int, int]:
    movie_popularity: dict[int, int] = {}
    ratings_user_ids: set[int] = set()
    ratings_movie_ids: set[int] = set()

    try:
        with open(ratings_csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                user_id = int(row.get("userId", "0"))
                movie_id = int(row.get("movieId", "0"))
                if user_id:
                    ratings_user_ids.add(user_id)
                if movie_id:
                    ratings_movie_ids.add(movie_id)
                    movie_popularity[movie_id] = movie_popularity.get(movie_id, 0) + 1
    except OSError:
        print(f"Warning: failed to load ratings CSV at {ratings_csv_path}")

    if ratings_user_ids:
        num_users = len(ratings_user_ids)
    if ratings_movie_ids:
        num_items = len(ratings_movie_ids)

    popular_movie_ids = [
        movie_id
        for movie_id, _ in sorted(movie_popularity.items(), key=lambda item: item[1], reverse=True)
    ]
    return movie_popularity, popular_movie_ids, num_users, num_items


def load_runtime_catalog(
    *,
    movies_csv_path: str | Path = "models/catalog_movies.csv",
    ratings_csv_path: str | Path = "ml-latest-small/ratings.csv",
    serving_stats_path: str | Path = "models/serving_stats.json",
    candidate_pool: int = 500,
    num_users: int = 0,
    num_items: int = 0,
) -> RuntimeCatalog:
    movie_titles, movie_genres, movie_years, known_genres = _load_movies_csv(movies_csv_path)

    movie_popularity, popular_movie_ids, num_users, num_items, stats_loaded = _load_serving_stats(
        serving_stats_path,
        num_users=num_users,
        num_items=num_items,
    )

    if not stats_loaded:
        movie_popularity, popular_movie_ids, num_users, num_items = _load_popularity_from_ratings(
            ratings_csv_path,
            num_users=num_users,
            num_items=num_items,
        )

    return RuntimeCatalog(
        movie_titles=movie_titles,
        movie_genres=movie_genres,
        movie_years=movie_years,
        movie_popularity=movie_popularity,
        popular_movie_ids=popular_movie_ids,
        known_genres=known_genres,
        candidate_pool=candidate_pool,
        num_users=num_users,
        num_items=num_items,
    )


def load_runtime_catalog_from_env() -> RuntimeCatalog:
    return load_runtime_catalog(
        movies_csv_path=os.getenv("MOVIES_CSV_PATH", "models/catalog_movies.csv"),
        ratings_csv_path=os.getenv("RATINGS_CSV_PATH", "ml-latest-small/ratings.csv"),
        serving_stats_path=os.getenv("SERVING_STATS_PATH", "models/serving_stats.json"),
        candidate_pool=int(os.getenv("CANDIDATE_POOL", "500")),
        num_users=int(os.getenv("NUM_USERS", "0")),
        num_items=int(os.getenv("NUM_ITEMS", "0")),
    )


def get_default_catalog() -> RuntimeCatalog:
    global _default_catalog
    if _default_catalog is None:
        _default_catalog = load_runtime_catalog_from_env()
    return _default_catalog


def reset_default_catalog() -> None:
    global _default_catalog
    _default_catalog = None


def set_default_catalog(catalog: RuntimeCatalog) -> None:
    global _default_catalog
    _default_catalog = catalog
