import time

from app.rag_resolve import ChatContext
from app.rag_session import SessionStore


def test_create_and_get_session():
    store = SessionStore(ttl_seconds=3600)
    session = store.create()
    loaded = store.get(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.context.seed_ids == []


def test_session_expires_after_ttl():
    store = SessionStore(ttl_seconds=1)
    session = store.create()
    session.updated_at = time.time() - 2
    store._sessions[session.session_id] = session
    assert store.get(session.session_id) is None


def test_append_message_updates_context():
    store = SessionStore(ttl_seconds=3600)
    session = store.create()
    session.context = ChatContext(seed_ids=[1], genres=["Comedy"])
    store.save(session)
    store.append_message(session, "user", "more sci-fi", turn_id="t1")
    loaded = store.get(session.session_id)
    assert loaded is not None
    assert len(loaded.messages) == 1
    assert loaded.messages[0].role == "user"
    assert loaded.messages[0].content == "more sci-fi"
    assert loaded.context.seed_ids == [1]


def test_clear_removes_all_sessions():
    store = SessionStore(ttl_seconds=3600)
    store.create()
    store.clear()
    store.purge_expired()
    assert len(store._sessions) == 0
