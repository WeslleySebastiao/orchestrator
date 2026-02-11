"""
Nó Synthesis — ÚNICO nó que gera linguagem natural.

Recebe o NodeResult estruturado de qualquer nó anterior e transforma
em uma resposta no tom de voz configurado (VOICE_TONE).

Todos os outros nós produzem apenas dados estruturados.
O Synthesis é a "voz" do sistema.
"""

from __future__ import annotations

import json
from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas import GraphState
from app.config import get_llm, VOICE_TONE


SYNTHESIS_PROMPT = """\
{voice_tone}

## Como você funciona

Você é a camada de linguagem do sistema. Recebe dados estruturados (JSON) de um
processamento interno e os transforma em uma mensagem natural para o usuário.

Você deve soar como uma pessoa conversando — não como um sistema executando comandos.

## Histórico da conversa
{conversation_history}

## Dados estruturados do processamento atual
```json
{node_result_json}
```

## Diretrizes de naturalidade

**Conversa geral (source_node = small_talk):**
- Converse como uma pessoa real. Responda o que foi perguntado, comente, brinque.
- Na primeira interação (is_first_interaction=true): se apresente e mencione o que sabe fazer.
- Nas demais: apenas responda. Não fique repetindo o que sabe fazer nem perguntando
  "posso ajudar com algo?" — isso é o oposto de natural.

**Coletando informações (source_node = clarify):**
- Peça o que falta de forma conversacional, não como formulário.
- Ruim: "Por favor, informe o campo 'nome'."
- Bom: "Pra quem é o parabéns?"
- Se faltam 2 slots, pode pedir os dois de uma vez de forma natural:
  "Pra quem é e quando é o aniversário?"
- Não repita informações que o usuário já deu.

**Apresentando resultados (source_node = dispatch/self_serve, status=ok):**
- Apresente de forma limpa e direta. Use os dados do JSON, não invente.
- Integre com o fluxo da conversa. Se o usuário pediu de forma casual,
  responda casualmente. Se pediu de forma formal, responda formalmente.

**Erros (status=error):**
- Seja transparente mas não alarmista. "Não consegui conectar com o serviço
  agora, tenta de novo daqui a pouco?" é melhor que "ERRO: serviço indisponível".

**Regra geral:** Leia o histórico e mantenha o tom da conversa. Se o usuário está
sendo informal, seja informal. Se está sendo direto, seja direto. Espelhe o estilo.

Responda APENAS com a mensagem para o usuário.
"""


def synthesis_node(state: GraphState) -> dict:
    """Transforma NodeResult estruturado em linguagem natural."""
    llm = get_llm()
    node_result = state.node_result

    if node_result is None:
        return {
            "response": "Desculpe, algo deu errado internamente. Pode tentar novamente?",
            "messages": list(state.messages) + [
                {"role": "assistant", "content": "Desculpe, algo deu errado internamente. Pode tentar novamente?"}
            ],
        }

    # Monta histórico resumido (últimas 8 mensagens)
    recent_history = state.messages[-8:] if state.messages else []
    history_text = "\n".join(
        f"{'Usuário' if m['role'] == 'user' else 'Assistente'}: {m['content']}"
        for m in recent_history
    )

    # Serializa o NodeResult para JSON
    node_result_json = node_result.model_dump_json(indent=2)

    system = SystemMessage(content=SYNTHESIS_PROMPT.format(
        voice_tone=VOICE_TONE,
        conversation_history=history_text or "(primeira mensagem)",
        node_result_json=node_result_json,
    ))

    response = llm.invoke([system, HumanMessage(content=state.user_input)])
    response_text = response.content.strip()

    # Registra no histórico
    new_messages = list(state.messages) + [
        {"role": "assistant", "content": response_text}
    ]

    return {
        "response": response_text,
        "messages": new_messages,
    }