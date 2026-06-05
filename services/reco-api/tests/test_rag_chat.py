import json

from fastapi.testclient import TestClient


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


def test_rag_explanations_endpoint_removed(load_app):
    client = TestClient(load_app)
    response = client.post("/rag/explanations", json={"seeds": [1, 2, 3]})
    assert response.status_code == 404


def test_rag_chat_clarifies_without_genre_or_title(load_app):
    client = TestClient(load_app)
    response = client.post(
        "/rag/chat",
        json={"message": "surprise me", "genres": []},
    )
    assert response.status_code == 200
    events = parse_sse(response.text)
    assert any(name == "token" for name, _ in events)
    final_payload = final_event(events)
    assert final_payload["needs_clarification"] is True
    assert final_payload["recommendations"] is None
    assert final_payload["clarification_reason"] == "missing_genre_and_title"


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
    chat_response = client.post(
        "/rag/chat",
        json={"message": 'I enjoy "Toy Story (1995)"', "genres": ["Animation"]},
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


def test_rag_chat_provider_timeout_still_returns_recommendations(load_app, monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "mock_timeout")
    client = TestClient(load_app)
    final_payload = final_event(
        parse_sse(
            client.post("/rag/chat", json={"message": "go", "genres": ["Action"]}).text,
        ),
    )
    assert final_payload["explanation_source"] == "deterministic_fallback"
    assert final_payload["chat_fallback_reason"] == "provider_timeout"
    assert final_payload["recommendations"] is not None
    assert len(final_payload["recommendations"]["items"]) > 0
