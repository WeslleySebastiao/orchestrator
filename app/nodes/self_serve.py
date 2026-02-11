"""
Nó Self-Serve — resolve internamente e retorna resultado estruturado.
NÃO gera linguagem natural. O Synthesis fará isso.

Em produção, aqui você executaria lógica interna (consulta DB, regras
de negócio, MCP tools) e retornaria o resultado como dados.
"""

from __future__ import annotations

from app.schemas import GraphState, NodeResult
from app.config import AGENT_REGISTRY


def self_serve_node(state: GraphState) -> dict:
    """Resolve internamente e retorna NodeResult estruturado."""
    intent = state.current_intent
    agent_card = AGENT_REGISTRY.get(intent)

    # Aqui entraria lógica real: consulta DB, MCP tools, etc.
    # Por enquanto, retorna os slots como "resultado da consulta".
    result_data = {
        "agent_name": agent_card.name if agent_card else None,
        "agent_id": agent_card.id if agent_card else None,
        "resolved_internally": True,
        "query_params": state.slots,
        # Em produção, aqui viria o resultado real:
        # "saldo_ferias": 15, "proximo_periodo": "01/03/2025 — 15/03/2025", etc.
    }

    node_result = NodeResult(
        source_node="self_serve",
        intent=intent,
        status="ok",
        data=result_data,
        slots_collected=state.slots,
    )

    return {
        "node_result": node_result,
        # Reset para próximo turno
        "current_intent": None,
        "slots": {},
    }
