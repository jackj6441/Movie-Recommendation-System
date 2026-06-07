"""Internal events emitted by the RAG chat turn orchestrator (transport-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union


@dataclass(frozen=True)
class ChatTurnToken:
    delta: str


@dataclass(frozen=True)
class ChatTurnFinal:
    payload: dict[str, Any]


ChatTurnEvent = Union[ChatTurnToken, ChatTurnFinal]
