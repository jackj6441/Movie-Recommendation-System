import json

from fastapi.testclient import TestClient

from app import rag_chat as rag_chat_service
from app.seed_ranker import RankedList


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data: dict | None = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        if data is not None:
            events.append((event_name, data))
    return events


def final_event(events: list[tuple[str, dict]]) -> dict:
    finals = [payload for name, payload in events if name == "final"]
    assert len(finals) == 1
    return finals[0]


def assert_sse_final_contract(payload: dict) -> None:
    """P0: every chat turn ends with a documented final payload shape."""
    for key in (
        "session_id",
        "turn_id",
        "needs_clarification",
        "needs_disambiguation",
        "context",
        "assistant_message",
        "model_version",
        "explanation_source",
    ):
        assert key in payload, f"missing final field: {key}"
    assert "seeds" in payload["context"]
    assert "genres" in payload["context"]


def test_rag_chat_ready_final_sse_contract(load_app):
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "", "genres": ["Comedy"]}).text,
        ),
    )
    assert_sse_final_contract(final_payload)
    assert final_payload["needs_clarification"] is False
    assert final_payload["needs_disambiguation"] is False
    assert final_payload["recommendations"] is not None


def test_rag_explanations_endpoint_removed(load_app):
    client = TestClient(load_app)
    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3]})
    assert response.status_code == 404


def test_rag_chat_clarifies_without_genre_or_title(load_app):
    client = TestClient(load_app)
    response = client.post(
        "/rag/chat",
        json={"message": "", "genres": []},
    )
    assert response.status_code == 200
    events = parse_sse(response.text)
    assert any(name == "token" for name, _ in events)
    final_payload = final_event(events)
    assert_sse_final_contract(final_payload)
    assert final_payload["needs_clarification"] is True
    assert final_payload["needs_disambiguation"] is False
    assert final_payload["recommendations"] is None
    assert final_payload["clarification_reason"] == "missing_genre_and_title"


def test_rag_chat_disambiguation_final_sse_contract(load_app):
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "zzzznotamovie", "genres": []}).text,
        ),
    )
    assert_sse_final_contract(final_payload)
    assert final_payload["needs_disambiguation"] is True
    assert final_payload["clarification_reason"] == "no_resolvable_seeds"
    assert final_payload["disambiguation_candidates"] is not None


def test_rag_chat_disambiguation_when_title_unresolved(load_app):
    client = TestClient(load_app)
    response = client.post(
        "/rag/chat",
        json={"message": "zzzznotamovie", "genres": []},
    )
    assert response.status_code == 200
    final_payload = final_event(parse_sse(response.text))
    assert_sse_final_contract(final_payload)
    assert final_payload["needs_disambiguation"] is True
    assert final_payload["recommendations"] is None
    candidates = final_payload["disambiguation_candidates"]
    assert len(candidates) > 0
    assert "movie_id" in candidates[0]
    assert "title" in candidates[0]
    assert final_payload["context"]["seeds"] == []


def test_rag_chat_disambiguate_does_not_persist_candidates_as_seeds(load_app):
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "zzzznotamovie", "genres": []}).text,
        ),
    )
    candidate_ids = {row["movie_id"] for row in final_payload["disambiguation_candidates"]}
    session_seed_ids = {seed["movie_id"] for seed in final_payload["context"]["seeds"]}
    assert session_seed_ids.isdisjoint(candidate_ids)


def test_rag_chat_bare_title_toy_story_disambiguates(load_app):
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "Toy Story", "genres": []}).text,
        ),
    )
    assert final_payload["needs_disambiguation"] is True
    assert final_payload["clarification_reason"] == "ambiguous_message"
    assert final_payload["recommendations"] is None
    assert final_payload["context"]["seeds"] == []
    assert len(final_payload["disambiguation_candidates"]) > 0
    assert any("Toy Story" in row["title"] for row in final_payload["disambiguation_candidates"])


def test_rag_chat_drama_message_disambiguates_with_genre_option(load_app):
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "drama", "genres": []}).text,
        ),
    )
    assert final_payload["needs_disambiguation"] is True
    assert final_payload["clarification_reason"] == "ambiguous_message"
    assert final_payload["disambiguation_genre_options"] == ["Drama"]
    assert final_payload["context"]["seeds"] == []
    candidate_titles = [row["title"] for row in final_payload["disambiguation_candidates"]]
    assert any("Drama Queen" in title for title in candidate_titles)


def test_rag_chat_disambiguation_genre_pick_appends_genre(load_app):
    client = TestClient(load_app)
    disambig = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": "drama", "genres": ["Action"]},
            ).text,
        ),
    )
    assert disambig["pending_genres"] == ["Action"]
    session_id = disambig["session_id"]

    ready = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={
                    "message": "",
                    "session_id": session_id,
                    "disambiguation_genre": "Drama",
                    "genres": [],
                },
            ).text,
        ),
    )
    assert ready["needs_disambiguation"] is False
    assert ready["needs_clarification"] is False
    assert ready["context"]["genres"] == ["Action", "Drama"]
    assert ready["context"]["seeds"] == []
    assert ready["recommendations"] is not None


def test_rag_chat_returns_recommendations_with_genre_chips(load_app):
    client = TestClient(load_app)
    response = client.post(
        "/rag/chat",
        json={"message": "something light", "genres": ["Comedy"]},
    )
    assert response.status_code == 200
    final_payload = final_event(parse_sse(response.text))
    assert final_payload["needs_clarification"] is False
    recs = final_payload["recommendations"]
    assert recs is not None
    assert recs["model_version"] == "dev"
    assert len(recs["items"]) > 0
    assert len(recs["seed_movies"]) >= 1


def test_rag_chat_recommendations_match_direct_endpoint(load_app):
    client = TestClient(load_app)
    disambig = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": 'I enjoy "Toy Story (1995)"', "genres": ["Animation"]},
            ).text,
        ),
    )
    pick_id = disambig["disambiguation_candidates"][0]["movie_id"]
    session_id = disambig["session_id"]
    chat_response = client.post(
        "/rag/chat",
        json={
            "message": "",
            "genres": ["Animation"],
            "session_id": session_id,
            "seed_movie_ids": [pick_id],
            "seed_update_mode": "replace",
        },
    )
    chat_final = final_event(parse_sse(chat_response.text))
    seed_ids = [seed["movie_id"] for seed in chat_final["context"]["seeds"]]

    direct = client.post(
        "/recommendations",
        json={
            "seeds": seed_ids,
            "shuffle": False,
            "genres": chat_final["context"]["genres"],
            "year_min": chat_final["context"]["year_min"],
            "year_max": chat_final["context"]["year_max"],
        },
    )
    assert direct.status_code == 200
    direct_ids = [item["movie_id"] for item in direct.json()["items"]]
    chat_ids = [item["movie_id"] for item in chat_final["recommendations"]["items"]]
    assert chat_ids == direct_ids


def test_rag_chat_session_reuse(load_app):
    client = TestClient(load_app)
    first = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "x", "genres": ["Drama"]}).text,
        ),
    )
    session_id = first["session_id"]
    second = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": "keep going", "genres": ["Drama"], "session_id": session_id},
            ).text,
        ),
    )
    assert second["session_id"] == session_id


def test_rag_chat_genre_only_visible_context_excludes_bootstrap_seeds(load_app):
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": "", "genres": ["Comedy"]},
            ).text,
        ),
    )
    assert final_payload["needs_clarification"] is False
    assert final_payload["context"]["seeds"] == []
    assert final_payload["context"]["genres"] == ["Comedy"]
    assert final_payload["context"]["year_min"] == 2005
    assert final_payload["context"]["recency_opt_out"] is False
    assert final_payload["recommendations"] is not None
    assert len(final_payload["recommendations"]["items"]) > 0


def test_rag_chat_clear_year_bounds_sets_recency_opt_out(load_app):
    client = TestClient(load_app)
    genre_only = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": "", "genres": ["Comedy"]},
            ).text,
        ),
    )
    assert genre_only["context"]["year_min"] == 2005
    session_id = genre_only["session_id"]

    cleared = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={
                    "message": "",
                    "genres": ["Comedy"],
                    "session_id": session_id,
                    "clear_year_bounds": True,
                },
            ).text,
        ),
    )
    assert cleared["context"]["year_min"] is None
    assert cleared["context"]["year_max"] is None
    assert cleared["context"]["recency_opt_out"] is True
    assert cleared["needs_clarification"] is False


def test_rag_chat_explicit_year_bounds_from_request(load_app):
    client = TestClient(load_app)
    genre_only = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": "", "genres": ["Comedy"]},
            ).text,
        ),
    )
    assert genre_only["context"]["year_min"] == 2005
    session_id = genre_only["session_id"]

    ranged = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={
                    "message": "",
                    "genres": ["Comedy"],
                    "session_id": session_id,
                    "year_min": 1990,
                    "year_max": 2004,
                },
            ).text,
        ),
    )
    assert ranged["context"]["year_min"] == 1990
    assert ranged["context"]["year_max"] == 2004
    assert ranged["context"]["recency_opt_out"] is False
    assert ranged["needs_clarification"] is False
    assert ranged["recommendations"] is not None


def test_rag_chat_clear_year_bounds_overrides_explicit_years(load_app):
    client = TestClient(load_app)
    genre_only = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": "", "genres": ["Comedy"]},
            ).text,
        ),
    )
    session_id = genre_only["session_id"]

    cleared = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={
                    "message": "",
                    "genres": ["Comedy"],
                    "session_id": session_id,
                    "year_min": 1990,
                    "year_max": 2004,
                    "clear_year_bounds": True,
                },
            ).text,
        ),
    )
    assert cleared["context"]["year_min"] is None
    assert cleared["context"]["year_max"] is None
    assert cleared["context"]["recency_opt_out"] is True


def test_rag_chat_clear_year_bounds_clears_session_years(load_app):
    client = TestClient(load_app)
    first = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": "more from the 90s", "genres": ["Drama"]},
            ).text,
        ),
    )
    assert first["context"]["year_min"] == 1990
    assert first["context"]["year_max"] == 1999
    session_id = first["session_id"]

    second = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={
                    "message": "",
                    "genres": ["Drama"],
                    "session_id": session_id,
                    "clear_year_bounds": True,
                },
            ).text,
        ),
    )
    assert second["context"]["year_min"] is None
    assert second["context"]["year_max"] is None
    assert second["needs_clarification"] is False


def test_rag_chat_explicit_seed_skips_disambiguation(load_app):
    client = TestClient(load_app)
    disambig = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "zzzznotamovie", "genres": []}).text,
        ),
    )
    pick_id = disambig["disambiguation_candidates"][0]["movie_id"]
    session_id = disambig["session_id"]

    ready = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={
                    "message": "",
                    "session_id": session_id,
                    "seed_movie_ids": [pick_id],
                    "seed_update_mode": "replace",
                    "genres": [],
                },
            ).text,
        ),
    )
    assert ready["needs_disambiguation"] is False
    assert ready["recommendations"] is not None
    assert ready["context"]["seeds"][0]["movie_id"] == pick_id


def test_rag_chat_empty_message_reuses_session_seeds(load_app):
    client = TestClient(load_app)
    first = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "go", "genres": ["Comedy"]}).text,
        ),
    )
    session_id = first["session_id"]
    prior_seed_ids = [seed["movie_id"] for seed in first["context"]["seeds"]]

    second = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={"message": "", "genres": [], "session_id": session_id},
            ).text,
        ),
    )
    assert_sse_final_contract(second)
    assert second["needs_clarification"] is False
    assert second["recommendations"] is not None
    assert [seed["movie_id"] for seed in second["context"]["seeds"]] == prior_seed_ids
    assert second["context"]["genres"] == ["Comedy"]


def test_rag_chat_reset_context_clears_session(load_app):
    client = TestClient(load_app)
    first = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "x", "genres": ["Drama"]}).text,
        ),
    )
    session_id = first["session_id"]
    assert first["context"]["genres"]

    second = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={
                    "message": "",
                    "genres": ["Comedy"],
                    "session_id": session_id,
                    "reset_context": True,
                },
            ).text,
        ),
    )
    assert second["context"]["genres"] == ["Comedy"]
    assert second["recommendations"] is not None


def test_rag_chat_warns_on_invalid_seed_movie_id(load_app):
    client = TestClient(load_app)
    seeded = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "Toy Story", "genres": []}).text,
        ),
    )
    valid_id = seeded["disambiguation_candidates"][0]["movie_id"]
    final_payload = final_event(
        parse_sse(
            client.post(
                "/rag/chat",
                json={
                    "message": "",
                    "session_id": seeded["session_id"],
                    "genres": ["Comedy"],
                    "seed_movie_ids": [valid_id, 999999999],
                    "seed_update_mode": "append",
                },
            ).text,
        ),
    )
    assert any(
        warning.get("code") == "invalid_seed_movie_id"
        for warning in final_payload.get("warnings", [])
    )
    assert final_payload["needs_clarification"] is False


def test_rag_chat_caps_recommendations_at_ten(load_app, monkeypatch):
    from app.seed_ranker import RankedItem

    def many_rank(request):
        items = [
            RankedItem(
                movie_id=1000 + index,
                title=f"Movie {index}",
                fusion_score=1.0 - index * 0.01,
                content_score=0.5,
            )
            for index in range(15)
        ]
        anchor = request.seed_movie_ids[0]
        return RankedList(
            items=items,
            seed_movie_ids=list(request.seed_movie_ids),
            anchor_movie_id=anchor,
            similar_movies=[],
        )

    monkeypatch.setattr(rag_chat_service.seed_ranker, "rank_seed_set", many_rank)
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "", "genres": ["Comedy"]}).text,
        ),
    )
    assert final_payload["needs_clarification"] is False
    assert len(final_payload["recommendations"]["items"]) == 10


def test_rag_chat_empty_recommendations_clarifies(load_app, monkeypatch):
    import importlib

    seed_ranker = importlib.import_module("app.seed_ranker")

    def empty_rank(request):
        seeds = list(request.seed_movie_ids)
        return RankedList(
            items=[],
            seed_movie_ids=seeds,
            anchor_movie_id=seeds[0],
            similar_movies=[],
        )

    monkeypatch.setattr(seed_ranker, "rank_seed_set", empty_rank)
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "", "genres": ["Comedy"]}).text,
        ),
    )
    assert final_payload["clarification_reason"] == "empty_recommendations"
    assert final_payload["needs_clarification"] is True
    assert final_payload["recommendations"]["items"] == []


def test_rag_chat_includes_debug_when_enabled(monkeypatch, repo_root, api_root):
    from tests.conftest import _configure_test_env, _reload_app

    _configure_test_env(monkeypatch, repo_root, api_root)
    monkeypatch.setenv("RAG_CHAT_DEBUG", "true")
    client = TestClient(_reload_app(api_root))
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "", "genres": ["Comedy"]}).text,
        ),
    )
    assert "debug" in final_payload
    assert final_payload["debug"]["resolve_outcome"] == "ready"
    assert final_payload["debug"]["seed_source"] == "genre_bootstrap"
    assert final_payload["debug"]["normalized_genres"] == ["Comedy"]
    assert final_payload["debug"]["ranking_mode"]


def test_rag_chat_omits_debug_in_production(monkeypatch, repo_root, api_root):
    from tests.conftest import _configure_test_env, _reload_app

    _configure_test_env(monkeypatch, repo_root, api_root)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("RAG_CHAT_DEBUG", raising=False)
    client = TestClient(_reload_app(api_root))
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "", "genres": ["Comedy"]}).text,
        ),
    )
    assert "debug" not in final_payload


def test_rag_chat_provider_timeout_still_returns_recommendations(load_app, monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_timeout")
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "", "genres": ["Action"]}).text,
        ),
    )
    assert final_payload["explanation_source"] == "deterministic_fallback"
    assert final_payload["chat_fallback_reason"] == "provider_timeout"
    assert final_payload["recommendations"] is not None
    assert len(final_payload["recommendations"]["items"]) > 0


def test_disambiguation_copy_is_concise():
    assert rag_chat_service.disambiguation_copy("ambiguous_message") == "Which did you mean?"
    assert rag_chat_service.disambiguation_copy("title_unresolved") == "Which movie did you mean?"
