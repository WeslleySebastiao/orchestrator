"""
Nó Intake — ponto de entrada. Registra mensagem no histórico.
Sem LLM. Apenas estrutura dados.
"""

from __future__ import annotations
from app.schemas import GraphState


def intake_node(state: GraphState) -> dict:
    """Registra a mensagem do usuário no histórico."""
    new_messages = list(state.messages) + [
        {"role": "user", "content": state.user_input}
    ]
    return {
        "messages": new_messages,
        "node_result": None,
        "response": "",
        "agent_result": None,
    }
