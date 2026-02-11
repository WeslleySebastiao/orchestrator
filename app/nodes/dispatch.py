"""
Nó Dispatch — despacha para agente externo via HTTP.
Retorna resultado estruturado. NÃO gera linguagem natural.

Se a API falhar, retorna NodeResult com status="error".
O Synthesis decide como comunicar o erro ao usuário.
"""

from __future__ import annotations

import logging
import httpx

from app.schemas import GraphState, NodeResult
from app.config import AGENT_REGISTRY, AGENTS_API_BASE_URL, AGENTS_API_KEY

logger = logging.getLogger(__name__)


def _call_agent_api_sync(agent_id: str, intent: str, slots: dict) -> dict:
    """Chama a API externa de agentes (síncrono)."""
    url = f"{AGENTS_API_BASE_URL}/agents/{agent_id}/execute"
    headers = {"Content-Type": "application/json"}
    if AGENTS_API_KEY:
        headers["Authorization"] = f"Bearer {AGENTS_API_KEY}"

    payload = {"intent": intent, "slots": slots}

    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def dispatch_node(state: GraphState) -> dict:
    """Despacha para agente externo. Retorna NodeResult estruturado."""
    intent = state.current_intent
    agent_card = AGENT_REGISTRY.get(intent)

    if not agent_card:
        node_result = NodeResult(
            source_node="dispatch",
            intent=intent,
            status="error",
            error_message=f"Agente não encontrado para intent '{intent}'",
        )
        return {"node_result": node_result}

    agent_id = agent_card.id
    slots = state.slots

    try:
        api_response = _call_agent_api_sync(agent_id, intent, slots)
        logger.info(f"Agente {agent_id} executado via API com sucesso.")

        node_result = NodeResult(
            source_node="dispatch",
            intent=intent,
            status=api_response.get("status", "ok"),
            data={
                "agent_name": agent_card.name,
                "agent_id": agent_id,
                "agent_response": api_response.get("response", ""),
                "agent_data": api_response.get("data", {}),
            },
            slots_collected=slots,
        )

        return {
            "node_result": node_result,
            "agent_result": api_response,
            # Reset para próximo turno
            "current_intent": None,
            "slots": {},
        }

    except httpx.ConnectError as e:
        logger.warning(f"API indisponível para {agent_id}: {e}")
        node_result = NodeResult(
            source_node="dispatch",
            intent=intent,
            status="error",
            data={"agent_name": agent_card.name, "agent_id": agent_id},
            slots_collected=slots,
            error_message=f"API do agente indisponível: {agent_card.name}",
        )
        return {"node_result": node_result}

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro HTTP do agente {agent_id}: {e.response.status_code}")
        node_result = NodeResult(
            source_node="dispatch",
            intent=intent,
            status="error",
            data={"agent_name": agent_card.name, "agent_id": agent_id, "http_status": e.response.status_code},
            slots_collected=slots,
            error_message=f"Agente retornou erro HTTP {e.response.status_code}",
        )
        return {"node_result": node_result}

    except Exception as e:
        logger.exception(f"Erro inesperado ao chamar {agent_id}")
        node_result = NodeResult(
            source_node="dispatch",
            intent=intent,
            status="error",
            data={"agent_name": agent_card.name, "agent_id": agent_id},
            slots_collected=slots,
            error_message=f"Erro inesperado: {str(e)}",
        )
        return {"node_result": node_result}
