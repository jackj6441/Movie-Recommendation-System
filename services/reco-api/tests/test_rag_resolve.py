from dataclasses import dataclass

from app.rag_resolve import (
    ChatContext,
    ResolveClarify,
    ResolveDisambiguate,
    ResolveReady,
    resolve_context,
    resolve_genre_disambiguation_pick,
)


@dataclass
class Hit:
    movie_id: int
    title: str


def _search_factory(catalog: dict[str, int]):
    def search_movies(query: str) -> list[Hit]:
        query_lower = query.strip().lower()
        hits = []
        for title, movie_id in catalog.items():
            if query_lower in title.lower():
                hits.append(Hit(movie_id=movie_id, title=title))
        return hits

    return search_movies


def _genre_seeds_factory(mapping: dict[str, list[int]]):
    def genre_seed_ids(genre: str, limit: int, year_min: int | None = None) -> list[int]:
        del year_min
        return mapping.get(genre, [])[:limit]

    return genre_seed_ids


def test_no_resolvable_seeds_returns_disambiguation_candidates():
    result = resolve_context(
        message="zzzznotamovie",
        genres=[],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Movie {mid}",
        popular_movie_ids=lambda limit: [101, 102, 103][:limit],
    )
    assert isinstance(result, ResolveDisambiguate)
    assert result.reason == "no_resolvable_seeds"
    assert len(result.candidates) == 3
    assert result.candidates[0].movie_id == 101


def test_invalid_genre_clarifies_when_only_unknown_chips():
    result = resolve_context(
        message="",
        genres=["NotARealGenre"],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Movie {mid}",
        known_genres={"Comedy", "Drama"},
    )
    assert hasattr(result, "reason")
    assert result.reason == "invalid_genre"


def test_invalid_genre_skipped_when_message_has_title():
    catalog = {"Toy Story (1995)": 1}
    result = resolve_context(
        message="Toy Story",
        genres=["NotARealGenre"],
        prior=None,
        search_movies=_search_factory(catalog),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: next(k for k, v in catalog.items() if v == mid),
        known_genres={"Comedy"},
    )
    assert isinstance(result, ResolveDisambiguate)
    assert result.reason == "ambiguous_message"


def test_clarify_when_no_genre_no_title_no_prior_seeds():
    result = resolve_context(
        message="",
        genres=[],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Movie {mid}",
    )
    assert hasattr(result, "reason")
    assert result.reason == "missing_genre_and_title"


def test_message_without_seeds_disambiguates_not_missing_input():
    result = resolve_context(
        message="surprise me",
        genres=[],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Movie {mid}",
        popular_movie_ids=lambda limit: [201][:limit],
    )
    assert isinstance(result, ResolveDisambiguate)


def test_genre_only_empty_message_bootstraps_ranking_seeds_not_explicit():
    result = resolve_context(
        message="",
        genres=["Comedy"],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({"Comedy": [10, 11, 12]}),
        get_title=lambda mid: f"Title {mid}",
    )
    assert isinstance(result, ResolveReady)
    assert result.context.explicit_seed_ids == []
    assert result.ranking_seed_ids == [10, 11, 12]
    assert result.context.genres == ["Comedy"]
    assert result.resolve_reason == "genre_bootstrap"


def test_genre_only_applies_default_recency_year_min():
    result = resolve_context(
        message="",
        genres=["Comedy"],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({"Comedy": [10, 11, 12]}),
        get_title=lambda mid: f"Title {mid}",
    )
    assert isinstance(result, ResolveReady)
    assert result.context.year_min == 2005
    assert result.context.year_max is None


def test_explicit_seed_skips_default_recency_year_min():
    catalog = {"Toy Story (1995)": 1}
    result = resolve_context(
        message="",
        genres=[],
        prior=None,
        search_movies=_search_factory(catalog),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: next(k for k, v in catalog.items() if v == mid),
        seed_movie_ids=[1],
        seed_update_mode="replace",
    )
    assert isinstance(result, ResolveReady)
    assert result.context.explicit_seed_ids == [1]
    assert result.context.year_min is None
    assert result.resolve_reason == "explicit_seed"


def test_recency_opt_out_skips_default_year_min():
    result = resolve_context(
        message="",
        genres=["Comedy"],
        prior=ChatContext(recency_opt_out=True),
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({"Comedy": [10, 11, 12]}),
        get_title=lambda mid: f"Title {mid}",
    )
    assert isinstance(result, ResolveReady)
    assert result.context.year_min is None
    assert result.context.recency_opt_out is True


def test_genre_only_bootstraps_seeds():
    result = resolve_context(
        message="something light",
        genres=["Comedy"],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({"Comedy": [10, 11, 12]}),
        get_title=lambda mid: f"Title {mid}",
    )
    assert hasattr(result, "context")
    assert result.context.explicit_seed_ids == []
    assert result.ranking_seed_ids == [10, 11, 12]
    assert result.context.genres == ["Comedy"]
    assert len(result.seed_movies) == 0


def test_explicit_seed_replace_mode_drops_prior_seeds():
    result = resolve_context(
        message="",
        genres=[],
        prior=ChatContext(explicit_seed_ids=[1], genres=["Drama"]),
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Title {mid}",
        seed_movie_ids=[42],
        seed_update_mode="replace",
    )
    assert result.context.explicit_seed_ids == [42]


def test_explicit_seed_ids_win_over_conflicting_message():
    catalog = {"Toy Story (1995)": 1, "Other Film (2000)": 99}
    result = resolve_context(
        message="Toy Story",
        genres=[],
        prior=None,
        search_movies=_search_factory(catalog),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: next(k for k, v in catalog.items() if v == mid),
        seed_movie_ids=[99],
        seed_update_mode="replace",
    )
    assert isinstance(result, ResolveReady)
    assert result.context.explicit_seed_ids == [99]


def test_replace_with_empty_seed_list_clears_prior_for_genre_bootstrap():
    result = resolve_context(
        message="",
        genres=["Comedy"],
        prior=ChatContext(explicit_seed_ids=[7], genres=["Drama"]),
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({"Comedy": [10, 11, 12]}),
        get_title=lambda mid: f"Title {mid}",
        seed_movie_ids=[],
        seed_update_mode="replace",
    )
    assert isinstance(result, ResolveReady)
    assert result.context.explicit_seed_ids == []
    assert result.ranking_seed_ids == [10, 11, 12]
    assert 7 not in result.ranking_seed_ids


def test_explicit_seed_ids_ready_with_empty_message():
    result = resolve_context(
        message="",
        genres=[],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Title {mid}",
        seed_movie_ids=[42],
    )
    assert result.context.explicit_seed_ids == [42]


def test_bare_title_disambiguates_instead_of_silent_seed():
    catalog = {"Toy Story (1995)": 1, "Toy Story 2 (1999)": 2}
    result = resolve_context(
        message="Toy Story",
        genres=[],
        prior=None,
        search_movies=_search_factory(catalog),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: next(k for k, v in catalog.items() if v == mid),
    )
    assert isinstance(result, ResolveDisambiguate)
    assert result.reason == "ambiguous_message"
    assert result.context.explicit_seed_ids == []
    assert {candidate.movie_id for candidate in result.candidates} == {1, 2}


def test_quoted_title_disambiguates_instead_of_silent_seed():
    catalog = {"Toy Story (1995)": 1, "Toy Story 2 (1999)": 2}
    result = resolve_context(
        message='I liked "Toy Story"',
        genres=["Animation"],
        prior=None,
        search_movies=_search_factory(catalog),
        genre_seed_ids=_genre_seeds_factory({"Animation": [99]}),
        get_title=lambda mid: catalog.get(next(k for k, v in catalog.items() if v == mid), f"Movie {mid}"),
        known_genres={"Animation"},
    )
    assert isinstance(result, ResolveDisambiguate)
    assert result.reason == "ambiguous_message"
    assert result.context.explicit_seed_ids == []
    assert "Animation" in result.context.genres
    assert result.pending_genres == ("Animation",)


def test_drama_message_disambiguates_with_genre_option():
    catalog = {
        "Confessions of a Teenage Drama Queen (2004)": 7316,
        "Drama/Mystery Film (2010)": 42,
    }
    result = resolve_context(
        message="drama",
        genres=[],
        prior=None,
        search_movies=_search_factory(catalog),
        genre_seed_ids=_genre_seeds_factory({"Drama": [10, 11, 12]}),
        get_title=lambda mid: next(k for k, v in catalog.items() if v == mid),
        known_genres={"Drama", "Comedy"},
    )
    assert isinstance(result, ResolveDisambiguate)
    assert result.reason == "ambiguous_message"
    assert result.context.explicit_seed_ids == []
    assert result.disambiguation_genre_options == ("Drama",)
    assert 7316 in {candidate.movie_id for candidate in result.candidates}


def test_genre_disambiguation_pick_merges_pending_and_chip_genres():
    result = resolve_genre_disambiguation_pick(
        prior=ChatContext(genres=["Comedy"]),
        pending_genres=["Action"],
        chip_genres=[],
        disambiguation_genre="Drama",
        genre_seed_ids=_genre_seeds_factory({"Drama": [20, 21, 22]}),
        get_title=lambda mid: f"Title {mid}",
        known_genres={"Comedy", "Action", "Drama"},
    )
    assert isinstance(result, ResolveReady)
    assert result.context.genres == ["Comedy", "Action", "Drama"]
    assert result.context.explicit_seed_ids == []
    assert result.resolve_reason == "genre_disambiguation_pick"


def test_genre_disambiguation_pick_rejects_unknown_genre():
    result = resolve_genre_disambiguation_pick(
        prior=ChatContext(),
        pending_genres=[],
        chip_genres=[],
        disambiguation_genre="NotARealGenre",
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Title {mid}",
        known_genres={"Drama"},
    )
    assert isinstance(result, ResolveClarify)
    assert result.reason == "invalid_genre"


def test_prior_seeds_kept_when_message_only_adds_years():
    result = resolve_context(
        message="more from the 90s",
        genres=[],
        prior=ChatContext(explicit_seed_ids=[5], genres=["Drama"]),
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Movie {mid}",
    )
    assert result.context.explicit_seed_ids == [5]
    assert result.context.year_min == 1990
    assert result.context.year_max == 1999


def test_genres_capped_at_three():
    result = resolve_context(
        message="",
        genres=["A", "B", "C", "D"],
        prior=None,
        search_movies=_search_factory({}),
        genre_seed_ids=_genre_seeds_factory(
            {"A": [1], "B": [2], "C": [3], "D": [4]},
        ),
        get_title=lambda mid: f"Movie {mid}",
    )
    assert len(result.context.genres) == 3
    assert result.context.genres == ["A", "B", "C"]


def test_merge_dedupes_and_caps_seeds():
    result = resolve_context(
        message='add "Alpha" and "Beta"',
        genres=[],
        prior=ChatContext(explicit_seed_ids=[1]),
        search_movies=_search_factory(
            {
                "Alpha (2000)": 1,
                "Beta (2001)": 2,
                "Gamma (2002)": 3,
                "Delta (2003)": 4,
                "Epsilon (2004)": 5,
                "Zeta (2005)": 6,
            },
        ),
        genre_seed_ids=_genre_seeds_factory({}),
        get_title=lambda mid: f"Movie {mid}",
    )
    assert isinstance(result, ResolveDisambiguate)
    assert result.context.explicit_seed_ids == [1]
    assert {candidate.movie_id for candidate in result.candidates} >= {1, 2}
