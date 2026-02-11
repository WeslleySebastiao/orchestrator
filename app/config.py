"""
Configuração central: OpenAI, registry de agentes, tom de voz.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from app.schemas import AgentCard

load_dotenv()


def get_llm() -> ChatOpenAI:
    """Retorna a LLM OpenAI configurada."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0,
    )


# ── Tom de voz (usado exclusivamente pelo Synthesis) ──────────────────

VOICE_TONE = os.getenv(
    "VOICE_TONE",
    (
        "Você é a Aava, assistente virtual pessoal. "
        "Fale de forma profissional, acolhedora e direta. "
        "Use português brasileiro. Seja breve (2-4 frases). "
        "Nunca invente dados — use apenas o que recebeu nos resultados estruturados."
    ),
)


# ── Registry de Agentes ────────────────────────────────────────────────

AGENT_REGISTRY: dict[str, AgentCard] = {
    "happy_birthday": AgentCard(
        id="agent-happy-birthday",
        name="Agente Parabéns",
        description="Gera uma mensagem de feliz aniversário personalizada",
        required_slots=["nome", "data"],
    ),
    "clima": AgentCard(
        id="agent-clima",
        name="Agente Clima",
        description="Consulta a previsão do tempo para uma cidade",
        required_slots=["cidade"],
    ),
    "traduzir": AgentCard(
        id="agent-traduzir",
        name="Agente Tradutor",
        description="Traduz um texto para outro idioma",
        required_slots=["texto", "idioma"],
    ),
    "lembrete": AgentCard(
        id="agent-lembrete",
        name="Agente Lembrete",
        description="Cria um lembrete com descrição e horário",
        required_slots=["descricao", "horario"],
    ),
}

AGENTS_API_BASE_URL = os.getenv("AGENTS_API_BASE_URL", "http://localhost:8001")
AGENTS_API_KEY = os.getenv("AGENTS_API_KEY", "")