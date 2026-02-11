"""
FastAPI server — expõe o orquestrador A2A via HTTP.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import ChatRequest, ChatResponse, GraphState
from app.session import session_manager
from app.graph import orchestrator_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 A2A Orchestrator started")
    yield
    logger.info("👋 A2A Orchestrator stopped")


app = FastAPI(
    title="A2A Orchestrator",
    description="Agent orchestration with LangGraph + Azure OpenAI",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Endpoint principal de chat."""
    try:
        state = session_manager.get_or_create(request.session_id)
        state.user_input = request.message

        logger.info(f"[{state.session_id}] User: {request.message}")

        # Executa o grafo
        result = orchestrator_graph.invoke(state.model_dump())

        updated_state = GraphState(**result)
        updated_state.session_id = state.session_id
        session_manager.save(updated_state)

        classification = updated_state.classification
        logger.info(
            f"[{state.session_id}] "
            f"Mode={classification.mode if classification else 'N/A'} "
            f"Intent={classification.intent if classification else 'N/A'}"
        )

        return ChatResponse(
            session_id=updated_state.session_id,
            response=updated_state.response,
            classification=updated_state.classification,
            node_result=updated_state.node_result,
            agent_result=updated_state.agent_result,
            debug={
                "slots": updated_state.slots,
                "current_intent": updated_state.current_intent,
                "message_count": len(updated_state.messages),
                "node_path": _get_node_path(updated_state),
            },
        )

    except Exception as e:
        logger.exception(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_node_path(state: GraphState) -> list[str]:
    """Reconstrói o caminho de nós executados."""
    path = ["intake", "classification"]
    if state.classification:
        path.append(state.classification.mode.value)
    path.append("synthesis")
    return path


@app.get("/sessions")
async def list_sessions():
    return {"sessions": session_manager.list_sessions()}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    session_manager.delete(session_id)
    return {"status": "deleted"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "a2a-orchestrator", "version": "0.2.0"}
