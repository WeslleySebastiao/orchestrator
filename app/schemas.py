"""
Schemas centrais do A2A Orchestrator.

Princípio: todos os nós (exceto synthesis) se comunicam via dados
estruturados. O Synthesis é o ÚNICO responsável por gerar linguagem
natural para o usuário, usando o tom de voz configurado.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class RouteMode(str, Enum):
    small_talk = "small_talk"
    clarify = "clarify"
    self_serve = "self_serve"
    dispatch = "dispatch"


# ── Structured outputs dos nós ─────────────────────────────────────────

class Classification(BaseModel):
    """Saída estruturada do nó de classificação (JSON da LLM)."""
    mode: RouteMode
    intent: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_slots: list[str] = Field(default_factory=list)
    question_to_ask: Optional[str] = None
    candidate_agents: list[str] = Field(default_factory=list)
    extracted_slots: dict[str, str] = Field(default_factory=dict)


class NodeResult(BaseModel):
    """
    Resultado estruturado produzido por qualquer nó de processamento
    (small_talk, clarify, self_serve, dispatch).
    O synthesis consome isso para gerar a resposta final.
    """
    source_node: str                          # qual nó produziu
    intent: Optional[str] = None
    status: str = "ok"                        # ok, error, pending
    data: dict[str, Any] = Field(default_factory=dict)  # payload do resultado
    slots_collected: dict[str, str] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    question_to_ask: Optional[str] = None     # para clarify
    error_message: Optional[str] = None


# ── Graph State ────────────────────────────────────────────────────────

class GraphState(BaseModel):
    """Estado compartilhado que flui por todos os nós do LangGraph."""

    # Sessão
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Histórico de mensagens (lista de dicts para serialização)
    messages: list[dict[str, str]] = Field(default_factory=list)
    # Formato: [{"role": "user"|"assistant", "content": "..."}, ...]

    # Input do turno atual
    user_input: str = ""

    # Classificação do turno
    classification: Optional[Classification] = None

    # Resultado estruturado do nó de processamento
    node_result: Optional[NodeResult] = None

    # Slots acumulados entre turnos
    slots: dict[str, str] = Field(default_factory=dict)

    # Intent acumulada (persiste entre turnos de clarify)
    current_intent: Optional[str] = None

    # Resposta final (gerada APENAS pelo synthesis)
    response: str = ""

    # Resultado bruto do agente externo (para debug/log)
    agent_result: Optional[dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True


# ── API Contracts ──────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    classification: Optional[Classification] = None
    node_result: Optional[NodeResult] = None
    agent_result: Optional[dict[str, Any]] = None
    debug: Optional[dict[str, Any]] = None


# ── Agent Registry ────────────────────────────────────────────────────

class AgentCard(BaseModel):
    """Agente registrado na API externa."""
    id: str
    name: str
    description: str
    required_slots: list[str] = Field(default_factory=list)
    endpoint: Optional[str] = None
    self_serve: bool = False
