"""
Gerenciador de sessões — mantém GraphState entre turnos.
Em produção, troque por Redis ou PostgreSQL.
"""

from __future__ import annotations

import uuid
from typing import Optional

from app.schemas import GraphState


class SessionManager:
    """In-memory session store."""

    def __init__(self):
        self._sessions: dict[str, GraphState] = {}

    def get_or_create(self, session_id: Optional[str] = None) -> GraphState:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id].model_copy(deep=True)

        sid = session_id or str(uuid.uuid4())
        state = GraphState(session_id=sid)
        self._sessions[sid] = state
        return state

    def save(self, state: GraphState) -> None:
        self._sessions[state.session_id] = state.model_copy(deep=True)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())


session_manager = SessionManager()
