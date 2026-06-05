"""Catalog-backed hooks for the conversational context resolver."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from app.rag_resolve import GenreSeedIdsFn, GetTitleFn, SearchMoviesFn


@dataclass(frozen=True)
class SearchHit:
    movie_id: int
    title: str


@dataclass
class CatalogServices:
    movie_titles: dict[int, str]
    movie_genres: dict[int, list[str]]
    movie_popularity: dict[int, int]
    get_popular_movies: Callable[[list[int], int], list[int]]
    known_genres: set[str] = field(default_factory=set)

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

    def genre_seed_ids(self, genre: str, limit: int) -> list[int]:
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
        return self.get_popular_movies(movie_ids, limit)

    def get_title(self, movie_id: int) -> str:
        return self.movie_titles.get(movie_id, f"Movie {movie_id}")

    def known_movie_ids(self) -> set[int]:
        return set(self.movie_titles)

    def popular_movie_ids(self, limit: int) -> list[int]:
        return self.get_popular_movies(list(self.movie_titles.keys()), limit)

    def as_resolve_hooks(self) -> tuple[SearchMoviesFn, GenreSeedIdsFn, GetTitleFn]:
        return self.search_movies, self.genre_seed_ids, self.get_title
