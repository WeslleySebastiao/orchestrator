"""
Nó Small Talk — retorna resultado estruturado para conversa geral.
NÃO gera linguagem natural. O Synthesis fará isso.

Cobre TUDO que não é intent de agente: cumprimentos, perguntas gerais,
conversa casual, reflexões, piadas, perguntas sobre a empresa, etc.
"""

from __future__ import annotations

from app.schemas import GraphState, NodeResult


def small_talk_node(state: GraphState) -> dict:
    """Produz NodeResult estruturado para conversa geral."""

    # Detecta se é a primeira mensagem da sessão
    user_messages = [m for m in state.messages if m.get("role") == "user"]
    is_first_interaction = len(user_messages) <= 1

    node_result = NodeResult(
        source_node="small_talk",
        intent=None,
        status="ok",
        data={
            "type": "general_conversation",
            "user_said": state.user_input,
            "is_first_interaction": is_first_interaction,
        },
    )

    return {"node_result": node_result}