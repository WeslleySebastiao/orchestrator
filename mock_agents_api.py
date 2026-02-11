"""
Mock da API externa de agentes — para testes locais.
Serviços genéricos para validar o fluxo de dados.

Roda em porta 8001. Uso: python mock_agents_api.py
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock Agents API", version="0.2.0")


class ExecuteRequest(BaseModel):
    intent: str
    slots: dict


class ExecuteResponse(BaseModel):
    agent_id: str
    status: str
    response: str
    data: dict


# ── Handlers por intent ────────────────────────────────────────────────

def handle_happy_birthday(slots: dict) -> dict:
    nome = slots.get("nome", "Anônimo")
    data = slots.get("data", "hoje")
    return {
        "response": f"Parabéns gerado para {nome} na data {data}.",
        "data": {
            "nome": nome,
            "data": data,
            "mensagem": f"🎂 Feliz aniversário, {nome}! Que seu dia {data} seja incrível!",
        },
    }


def handle_clima(slots: dict) -> dict:
    cidade = slots.get("cidade", "desconhecida")
    return {
        "response": f"Previsão consultada para {cidade}.",
        "data": {
            "cidade": cidade,
            "temperatura": "27°C",
            "condicao": "Parcialmente nublado",
            "umidade": "65%",
        },
    }


def handle_traduzir(slots: dict) -> dict:
    texto = slots.get("texto", "")
    idioma = slots.get("idioma", "inglês")
    return {
        "response": f"Tradução realizada para {idioma}.",
        "data": {
            "texto_original": texto,
            "idioma_destino": idioma,
            "traducao": f"[mock] Tradução de '{texto}' para {idioma}",
        },
    }


def handle_lembrete(slots: dict) -> dict:
    descricao = slots.get("descricao", "")
    horario = slots.get("horario", "")
    return {
        "response": f"Lembrete criado para {horario}.",
        "data": {
            "descricao": descricao,
            "horario": horario,
            "status": "agendado",
            "criado_em": datetime.now(timezone.utc).isoformat(),
        },
    }


HANDLERS = {
    "happy_birthday": handle_happy_birthday,
    "clima": handle_clima,
    "traduzir": handle_traduzir,
    "lembrete": handle_lembrete,
}


# ── Endpoints ──────────────────────────────────────────────────────────

@app.post("/agents/{agent_id}/execute", response_model=ExecuteResponse)
async def execute_agent(agent_id: str, request: ExecuteRequest):
    handler = HANDLERS.get(request.intent)

    if handler:
        result = handler(request.slots)
        return ExecuteResponse(
            agent_id=agent_id, status="success",
            response=result["response"], data=result["data"],
        )

    # Fallback genérico: ecoa parâmetros
    return ExecuteResponse(
        agent_id=agent_id,
        status="success",
        response=f"Agente '{agent_id}' executou intent '{request.intent}' com {len(request.slots)} slot(s).",
        data={
            "echo_intent": request.intent,
            "echo_slots": request.slots,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/agents/registry")
async def list_agents():
    return {
        "agents": [
            {"id": "agent-happy-birthday", "name": "Agente Parabéns", "intents": ["happy_birthday"]},
            {"id": "agent-clima", "name": "Agente Clima", "intents": ["clima"]},
            {"id": "agent-traduzir", "name": "Agente Tradutor", "intents": ["traduzir"]},
            {"id": "agent-lembrete", "name": "Agente Lembrete", "intents": ["lembrete"]},
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-agents-api", "version": "0.2.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)