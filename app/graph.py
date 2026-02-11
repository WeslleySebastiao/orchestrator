"""
Grafo LangGraph do Orquestrador A2A.

PRINCÍPIO: Todos os caminhos terminam no Synthesis.
O Synthesis é o ÚNICO nó que gera linguagem natural.

Fluxo:
  intake → classification → ┬─ small_talk ─┐
                             ├─ clarify    ─┤
                             ├─ self_serve ─┤──→ synthesis → END
                             └─ dispatch   ─┘
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.schemas import GraphState
from app.nodes import (
    intake_node,
    classification_node,
    small_talk_node,
    clarify_node,
    self_serve_node,
    dispatch_node,
    synthesis_node,
)


def route_after_classification(state: GraphState) -> str:
    """Conditional edge: roteia com base no mode da classificação."""
    if state.classification is None:
        return "clarify"
    return state.classification.mode.value


def build_graph() -> StateGraph:
    """Constrói e compila o grafo do orquestrador."""

    graph = StateGraph(GraphState)

    # ── Nós ────────────────────────────────────────────────
    graph.add_node("intake", intake_node)
    graph.add_node("classification", classification_node)
    graph.add_node("small_talk", small_talk_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("self_serve", self_serve_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("synthesis", synthesis_node)

    # ── Arestas ────────────────────────────────────────────

    # Ponto de entrada
    graph.set_entry_point("intake")

    # intake → classification
    graph.add_edge("intake", "classification")

    # classification → [conditional routing]
    graph.add_conditional_edges(
        "classification",
        route_after_classification,
        {
            "small_talk": "small_talk",
            "clarify": "clarify",
            "self_serve": "self_serve",
            "dispatch": "dispatch",
        },
    )

    # TODOS os nós de processamento → synthesis → END
    graph.add_edge("small_talk", "synthesis")
    graph.add_edge("clarify", "synthesis")
    graph.add_edge("self_serve", "synthesis")
    graph.add_edge("dispatch", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()


# Singleton compilado
orchestrator_graph = build_graph()
