"""In-memory chat sessions for conversational RAG (TTL-bound)."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from app.rag_resolve import ChatContext

MessageRole = Literal["user", "assistant"]


@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    turn_id: str | None = None


@dataclass
class ChatSession:
    session_id: str
    created_at: float
    updated_at: float
    messages: list[ChatMessage] = field(default_factory=list)
    context: ChatContext = field(default_factory=ChatContext)


class SessionStore:
    """Process-local session map with TTL expiry (single-instance v1)."""

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else default_ttl_seconds()
        self._sessions: dict[str, ChatSession] = {}

    def create(self) -> ChatSession:
        self.purge_expired()
        now = time.time()
        session = ChatSession(
            session_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> ChatSession | None:
        self.purge_expired()
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if self._is_expired(session):
            del self._sessions[session_id]
            return None
        return session

    def save(self, session: ChatSession) -> None:
        session.updated_at = time.time()
        self._sessions[session.session_id] = session

    def append_message(
        self,
        session: ChatSession,
        role: MessageRole,
        content: str,
        *,
        turn_id: str | None = None,
    ) -> None:
        session.messages.append(ChatMessage(role=role, content=content, turn_id=turn_id))
        self.save(session)

    def purge_expired(self) -> None:
        expired = [sid for sid, sess in self._sessions.items() if self._is_expired(sess)]
        for sid in expired:
            del self._sessions[sid]

    def clear(self) -> None:
        self._sessions.clear()

    def _is_expired(self, session: ChatSession) -> bool:
        return time.time() - session.updated_at >= self._ttl_seconds


def default_ttl_seconds() -> int:
    try:
        return int(os.getenv("RAG_SESSION_TTL_SECONDS", "3600"))
    except ValueError:
        return 3600


# Shared store for the API process (R2 chat endpoint will use this).
GLOBAL_SESSION_STORE = SessionStore()
