"""
Nó Classification — LLM classifica a mensagem e retorna JSON estruturado.

Única responsabilidade: determinar mode, intent, confidence, missing_slots,
extrair slots da mensagem atual. NÃO gera linguagem natural.
"""

from __future__ import annotations

import json
from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas import Classification, GraphState
from app.config import get_llm, AGENT_REGISTRY


CLASSIFICATION_PROMPT = """\
Você é o classificador do assistente virtual Lia (Klabin). Analise a mensagem
do usuário e retorne APENAS um JSON válido. Sem markdown, sem explicações.

## Agentes disponíveis (LISTA EXAUSTIVA — não existe nenhum outro)
{agents_description}

## Slots já coletados nesta sessão
{current_slots}

## Intent acumulada (de turnos anteriores)
{current_intent}

## Regras de classificação

### 1. small_talk (PADRÃO)
Use quando a mensagem NÃO corresponde a NENHUM intent dos agentes acima.
Inclui: cumprimentos, conversa casual, perguntas gerais, qualquer pedido fora
do escopo dos agentes. **Se intent for null → mode DEVE ser small_talk.**

### 2. clarify
SOMENTE quando a mensagem indica uma intent dos agentes acima, mas faltam slots.
Obrigatório: `intent` preenchido, `missing_slots` com pelo menos 1 item.

### 3. self_serve / dispatch
Todos os slots preenchidos. Intent DEVE estar preenchido.

## Extração agressiva de slots
EXTRAIA O MÁXIMO DE SLOTS POSSÍVEL de uma única mensagem. O usuário frequentemente
fornece múltiplas informações de uma vez. Exemplos:

- "Parabéns pro João dia 15/03" → extracted_slots: {{"nome": "João", "data": "15/03"}} → dispatch
- "Traduz 'hello world' pro japonês" → extracted_slots: {{"texto": "hello world", "idioma": "japonês"}} → dispatch
- "Me lembra de comprar pão às 18h" → extracted_slots: {{"descricao": "comprar pão", "horario": "18:00"}} → dispatch
- "Clima em Curitiba" → extracted_slots: {{"cidade": "Curitiba"}} → dispatch

NÃO peça um slot por vez se o usuário já deu tudo. Combine extracted_slots com
current_slots para decidir se vai para clarify (ainda falta algo) ou dispatch/self_serve
(tudo preenchido).

## Referências ao histórico
Se o usuário referencia algo da conversa anterior (ex: "aquele mesmo", "de novo",
"o que eu falei"), use o histórico para resolver a referência e extrair os slots.

## REGRAS INVIOLÁVEIS
- clarify/self_serve/dispatch EXIGEM intent válida. Sem intent → small_talk.
- clarify EXIGE missing_slots não vazio. Sem missing_slots → small_talk.
- Pedido fora do escopo dos agentes → small_talk. Sem exceção.

## Formato (JSON puro)
{{
  "mode": "small_talk|clarify|self_serve|dispatch",
  "intent": "string ou null",
  "confidence": 0.0 a 1.0,
  "missing_slots": ["slot1"],
  "question_to_ask": "string ou null",
  "candidate_agents": ["agent-id"],
  "extracted_slots": {{"slot_name": "valor"}}
}}
"""


def _build_agents_description() -> str:
    lines = []
    for intent, card in AGENT_REGISTRY.items():
        lines.append(
            f"- intent='{intent}' → {card.name} (id={card.id}, "
            f"required_slots={card.required_slots}, self_serve={card.self_serve}): "
            f"{card.description}"
        )
    return "\n".join(lines)


def classification_node(state: GraphState) -> dict:
    """Classifica a mensagem via LLM. Retorna dados estruturados."""
    llm = get_llm()

    system = SystemMessage(content=CLASSIFICATION_PROMPT.format(
        agents_description=_build_agents_description(),
        current_slots=state.slots or {},
        current_intent=state.current_intent or "nenhuma",
    ))

    # Inclui histórico recente para contexto (últimas 10 mensagens, user + assistant)
    from langchain_core.messages import AIMessage
    history_msgs = []
    for msg in state.messages[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            history_msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            history_msgs.append(AIMessage(content=content))

    human = HumanMessage(content=f"Mensagem atual do usuário: {state.user_input}")

    response = llm.invoke([system] + history_msgs + [human])

    # Parse JSON
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "mode": "small_talk",
            "intent": None,
            "confidence": 0.5,
            "missing_slots": [],
            "question_to_ask": None,
            "candidate_agents": [],
            "extracted_slots": {},
        }

    # Merge slots extraídos com os existentes
    extracted = data.get("extracted_slots", {})
    merged_slots = {**state.slots, **extracted}

    mode = data["mode"]
    intent = data.get("intent")
    missing_slots = data.get("missing_slots", [])

    # ── Hard guard: clarify sem intent ou sem missing_slots → small_talk ──
    if mode == "clarify" and (not intent or not missing_slots):
        mode = "small_talk"
        intent = None
        missing_slots = []

    # ── Hard guard: dispatch/self_serve sem intent → small_talk ──
    if mode in ("dispatch", "self_serve") and not intent:
        mode = "small_talk"

    classification = Classification(
        mode=mode,
        intent=intent,
        confidence=data.get("confidence", 0.5),
        missing_slots=missing_slots,
        question_to_ask=data.get("question_to_ask"),
        candidate_agents=data.get("candidate_agents", []),
        extracted_slots=extracted,
    )

    return {
        "classification": classification,
        "slots": merged_slots,
        "current_intent": classification.intent or state.current_intent,
    }