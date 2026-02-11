"""
Nó Clarify — retorna resultado estruturado com os slots faltantes.
NÃO gera linguagem natural. O Synthesis fará isso.
"""

from __future__ import annotations

from app.schemas import GraphState, NodeResult
from app.config import AGENT_REGISTRY


def clarify_node(state: GraphState) -> dict:
    """Produz NodeResult estruturado para clarificação."""
    classification = state.classification
    intent = classification.intent or state.current_intent
    agent_card = AGENT_REGISTRY.get(intent) if intent else None

    node_result = NodeResult(
        source_node="clarify",
        intent=intent,
        status="pending",
        data={
            "agent_name": agent_card.name if agent_card else None,
            "agent_id": agent_card.id if agent_card else None,
        },
        slots_collected=state.slots,
        missing_slots=classification.missing_slots,
        question_to_ask=classification.question_to_ask,
    )

    return {"node_result": node_result}
