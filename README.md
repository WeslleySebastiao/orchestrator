# A2A Orchestrator

Sistema de orquestração multi-agente com LangGraph. Um chat que classifica mensagens, coleta informações e despacha para agentes externos via API — tudo com LLM real por trás.

## Visão Geral

O A2A funciona como um orquestrador central: recebe mensagens do usuário, entende o que ele precisa, coleta as informações necessárias ao longo da conversa e, quando tudo está pronto, chama o agente especializado via HTTP.

```
Usuário
  │
  ▼
┌────────────────────────────────────────────────────┐
│                 A2A Server (LangGraph)              │
│                                                    │
│  intake → classification ─┬─ small_talk ─┐         │
│           (🧠 LLM)       ├─ clarify    ─┤         │
│                           ├─ self_serve ─┤→ synthesis (🧠 LLM)
│                           └─ dispatch   ─┘         │
│                                 │                  │
└─────────────────────────────────┼──────────────────┘
                                  │
                            ┌─────▼─────┐
                            │    API    │
                            │  Externa  │
                            │ (Agentes) │
                            └───────────┘
```

---

## Princípio Arquitetural

Todos os nós se comunicam via **dados estruturados (JSON)**. O **Synthesis é o único nó que gera linguagem natural**, aplicando o tom de voz configurado.

| Nó | Usa LLM? | O que produz |
|---|---|---|
| `intake` | ❌ | Registra mensagem no histórico |
| `classification` | ✅ | `Classification` JSON — mode, intent, confidence, slots extraídos |
| `small_talk` | ❌ | `NodeResult` JSON — tipo de conversa, contexto |
| `clarify` | ❌ | `NodeResult` JSON — slots pendentes, pergunta a fazer |
| `self_serve` | ❌ | `NodeResult` JSON — resultado de consulta interna |
| `dispatch` | ❌ | `NodeResult` JSON — resposta da API externa ou erro |
| `synthesis` | ✅ | **Texto natural** com tom de voz → resposta ao usuário |

**Chamadas LLM por turno: exatamente 2** (classification + synthesis). Sempre.

---

## Estrutura do Projeto

```
a2a-orchestrator/
├── app/
│   ├── __init__.py
│   ├── config.py              # LLM factory, VOICE_TONE, agent registry
│   ├── graph.py               # Definição do grafo LangGraph
│   ├── schemas.py             # GraphState, Classification, NodeResult, API contracts
│   ├── server.py              # FastAPI endpoints
│   ├── session.py             # Gerenciador de sessões in-memory
│   └── nodes/
│       ├── __init__.py
│       ├── intake.py          # Registra mensagem (sem LLM)
│       ├── classification.py  # LLM classifica → JSON estruturado
│       ├── small_talk.py      # Conversa geral → NodeResult (sem LLM)
│       ├── clarify.py         # Coleta de slots → NodeResult (sem LLM)
│       ├── self_serve.py      # Resolução interna → NodeResult (sem LLM)
│       ├── dispatch.py        # Chama API externa → NodeResult (sem LLM)
│       └── synthesis.py       # NodeResult → linguagem natural (LLM)
├── main.py                    # Entrypoint do server
├── cli.py                     # Cliente CLI para testes
├── mock_agents_api.py         # Mock da API de agentes
├── test_dispatch.py           # Suite de testes automatizados
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Instalar dependências

```bash
git clone <repo-url>
cd a2a-orchestrator
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com sua chave:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 3. Subir o mock de agentes

```bash
python mock_agents_api.py
# Roda na porta 8001
```

### 4. Subir o orquestrador

```bash
python main.py
# Roda na porta 8000
```

### 5. Testar

```bash
# Via CLI interativo
python cli.py

# Ou via curl
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Oi!"}'
```

---

## Configuração

### Variáveis de ambiente

| Variável | Descrição | Default |
|---|---|---|
| `OPENAI_API_KEY` | Chave da API OpenAI | — (obrigatório) |
| `OPENAI_MODEL` | Modelo a usar | `gpt-4o-mini` |
| `VOICE_TONE` | System prompt do Synthesis (tom de voz) | Lia, assistente da Klabin |
| `AGENTS_API_BASE_URL` | URL da API de agentes | `http://localhost:8001` |
| `AGENTS_API_KEY` | Bearer token para API de agentes | — (opcional) |
| `HOST` | Host do server | `0.0.0.0` |
| `PORT` | Porta do server | `8000` |

### Tom de Voz

O tom de voz é controlado pela variável `VOICE_TONE`. É o system prompt que o Synthesis usa para **toda** resposta. Para mudar a personalidade, edite apenas essa variável:

```env
VOICE_TONE=Você é o Max, assistente técnico. Seja direto, use termos técnicos quando necessário, sem emojis.
```

Nenhum código precisa mudar.

### Trocar o LLM Provider

Para usar Azure OpenAI, edite `app/config.py`:

```python
from langchain_openai import AzureChatOpenAI

def get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        temperature=0,
    )
```

Para Anthropic:

```python
from langchain_anthropic import ChatAnthropic

def get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0,
    )
```

---

## API Endpoints

### `POST /chat`

Endpoint principal. Recebe mensagem, executa o grafo, retorna resposta.

**Request:**

```json
{
  "session_id": "uuid-opcional",
  "message": "Preciso de um lembrete"
}
```

Se `session_id` for omitido, cria uma nova sessão.

**Response:**

```json
{
  "session_id": "abc-123",
  "response": "Claro! O que você quer lembrar e pra que horas?",
  "classification": {
    "mode": "clarify",
    "intent": "lembrete",
    "confidence": 0.92,
    "missing_slots": ["descricao", "horario"],
    "question_to_ask": "ask_descricao_horario",
    "candidate_agents": ["agent-lembrete"],
    "extracted_slots": {}
  },
  "node_result": {
    "source_node": "clarify",
    "intent": "lembrete",
    "status": "pending",
    "data": {
      "agent_name": "Agente Lembrete",
      "agent_id": "agent-lembrete"
    },
    "slots_collected": {},
    "missing_slots": ["descricao", "horario"],
    "question_to_ask": "ask_descricao_horario",
    "error_message": null
  },
  "agent_result": null,
  "debug": {
    "slots": {},
    "current_intent": "lembrete",
    "message_count": 2,
    "node_path": ["intake", "classification", "clarify", "synthesis"]
  }
}
```

### `GET /sessions`

Lista sessões ativas.

### `DELETE /sessions/{session_id}`

Remove uma sessão.

### `GET /health`

Health check.

---

## Fluxo de Classificação

A LLM recebe a mensagem do usuário + contexto (histórico, slots coletados, intent acumulada, agentes disponíveis) e retorna um JSON com:

| Campo | Descrição |
|---|---|
| `mode` | Rota: `small_talk`, `clarify`, `self_serve`, `dispatch` |
| `intent` | Intent identificada (ex: `clima`, `lembrete`, `traduzir`) |
| `confidence` | Score 0-1 |
| `missing_slots` | Slots que ainda faltam |
| `question_to_ask` | Indicação do que perguntar |
| `candidate_agents` | IDs dos agentes candidatos |
| `extracted_slots` | Slots extraídos da mensagem atual |

### Regras de roteamento

- **`small_talk`** — Default. Tudo que não corresponde a um agente. Conversa livre.
- **`clarify`** — Intent identificada mas faltam slots. Obrigatório ter `intent` + `missing_slots`.
- **`self_serve`** — Todos os slots preenchidos, agente marcado como `self_serve=True`.
- **`dispatch`** — Todos os slots preenchidos, requer execução externa.

### Hard guards (proteção no código)

Mesmo que a LLM erre, o código força:

- `clarify` sem `intent` ou sem `missing_slots` → vira `small_talk`
- `dispatch` / `self_serve` sem `intent` → vira `small_talk`
- Erro de parse no JSON → vira `small_talk`

Isso garante que o sistema **nunca trava** em loops de clarify sem saída.

### Extração agressiva de slots

O classificador extrai **todos os slots possíveis** de uma única mensagem:

```
"Me lembra de comprar pão às 18h"
→ extracted_slots: {"descricao": "comprar pão", "horario": "18:00"}
→ dispatch direto (sem clarify intermediário)
```

---

## Fluxo de Dados: Exemplo Completo

Cenário: usuário quer um parabéns para o João no dia 15/03.

```
User: "Manda um parabéns pro João dia 15 de março"

1. intake       → registra no histórico
2. classification (LLM) →
   {
     mode: "dispatch",
     intent: "happy_birthday",
     extracted_slots: {"nome": "João", "data": "15/03"},
     missing_slots: []
   }
3. dispatch     → HTTP POST /agents/agent-happy-birthday/execute
                   body: {"intent": "happy_birthday", "slots": {"nome": "João", "data": "15/03"}}
                → NodeResult {status: "ok", data: {mensagem: "🎂 Feliz aniversário, João!"}}
4. synthesis (LLM) → "Pronto! A mensagem de parabéns pro João foi gerada: 🎂 Feliz aniversário, João!"
```

Cenário com coleta de slots:

```
User: "Quero traduzir uma coisa"

1. classification → {mode: "clarify", intent: "traduzir", missing_slots: ["texto", "idioma"]}
2. clarify       → NodeResult {status: "pending", missing_slots: ["texto", "idioma"]}
3. synthesis     → "O que você quer traduzir e pra qual idioma?"

User: "Hello world pro japonês"

1. classification → {mode: "dispatch", intent: "traduzir", extracted_slots: {"texto": "Hello world", "idioma": "japonês"}}
2. dispatch      → HTTP POST → NodeResult {status: "ok", data: {traducao: "..."}}
3. synthesis     → "Aqui está: ..."
```

---

## Gerenciamento de Contexto

### O que persiste entre turnos

O `GraphState` mantém entre mensagens:

| Campo | Descrição | Persiste? |
|---|---|---|
| `messages` | Histórico completo (user + assistant) | ✅ Acumula |
| `slots` | Slots coletados | ✅ Até dispatch/self_serve resetar |
| `current_intent` | Intent em andamento | ✅ Até dispatch/self_serve resetar |
| `session_id` | Identificador da sessão | ✅ Sempre |
| `classification` | Classificação do turno | ❌ Sobrescrito a cada turno |
| `node_result` | Resultado do nó | ❌ Sobrescrito a cada turno |
| `response` | Resposta final | ❌ Sobrescrito a cada turno |

### O que cada LLM vê

**Classification** recebe:
- System prompt com agentes disponíveis, slots coletados e intent acumulada
- Últimas 10 mensagens (user + assistant) como contexto
- Mensagem atual do usuário

**Synthesis** recebe:
- `VOICE_TONE` como system prompt
- Últimas 8 mensagens (user + assistant) para tom e continuidade
- `NodeResult` serializado como JSON
- Mensagem atual do usuário (para espelhar o estilo)

### Sessões

Sessões são armazenadas in-memory (`dict` Python). Para produção, substituir `SessionManager` em `app/session.py` por Redis, PostgreSQL ou outro backend persistente.

---

## Agentes Disponíveis (Mock)

O projeto inclui um mock (`mock_agents_api.py`) com 4 serviços genéricos:

| Intent | Agente | Slots | Descrição |
|---|---|---|---|
| `happy_birthday` | agent-happy-birthday | `nome`, `data` | Gera mensagem de aniversário |
| `clima` | agent-clima | `cidade` | Consulta previsão do tempo |
| `traduzir` | agent-traduzir | `texto`, `idioma` | Traduz texto |
| `lembrete` | agent-lembrete | `descricao`, `horario` | Cria lembrete |

Qualquer intent desconhecida recebe um fallback genérico que ecoa os parâmetros.

### Contrato da API de Agentes

O dispatch chama:

```
POST /agents/{agent_id}/execute
Content-Type: application/json

{
  "intent": "happy_birthday",
  "slots": {
    "nome": "João",
    "data": "15/03"
  }
}
```

Resposta esperada:

```json
{
  "agent_id": "agent-happy-birthday",
  "status": "success",
  "response": "Parabéns gerado para João na data 15/03.",
  "data": {
    "nome": "João",
    "data": "15/03",
    "mensagem": "🎂 Feliz aniversário, João!"
  }
}
```

Para adicionar novos agentes:
1. Adicionar `AgentCard` no `AGENT_REGISTRY` em `app/config.py`
2. Implementar o handler na API de agentes

---

## Testes

### CLI interativo

```bash
python cli.py              # Via HTTP (server rodando)
python cli.py --direct     # Executa grafo direto (sem server)
```

O CLI mostra debug com classificação, node_result e path. Toggle com `debug` no prompt.

### Suite automatizada

```bash
python test_dispatch.py              # Todos os cenários via HTTP
python test_dispatch.py -s clima     # Cenário específico
python test_dispatch.py --direct     # Sem server
```

Cenários incluídos:

| Cenário | O que testa |
|---|---|
| `holerite` | Fluxo completo: small_talk → clarify → clarify → dispatch |
| `chamado` | Dispatch rápido: clarify → dispatch |
| `ferias` | Self-serve: clarify → self_serve |
| `conversa` | 5 mensagens de small_talk variado |

### curl

```bash
# Primeira mensagem (cria sessão)
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Oi!"}' | python -m json.tool

# Mensagem com sessão existente
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SEU-SESSION-ID", "message": "Clima em Curitiba"}' | python -m json.tool
```

---

## Adicionando Novos Agentes

### 1. Registrar no config

Em `app/config.py`, adicione ao `AGENT_REGISTRY`:

```python
"meu_servico": AgentCard(
    id="agent-meu-servico",
    name="Agente Meu Serviço",
    description="Descrição clara do que faz (a LLM usa isso para classificar)",
    required_slots=["param1", "param2"],
    self_serve=False,  # True se resolver internamente
),
```

### 2. Implementar na API externa

Adicione o handler na sua API de agentes que receba `POST /agents/agent-meu-servico/execute` com o payload `{intent, slots}`.

### 3. Testar

```bash
python cli.py --direct
> Preciso do meu serviço com param1=X e param2=Y
```

O classificador vai detectar automaticamente pela descrição no registry. Se não detectar bem, ajuste a `description` para ser mais explícita.

---

## Customização

### Mudar o tom de voz

Apenas edite `VOICE_TONE` no `.env`. Exemplos:

```env
# Formal e técnico
VOICE_TONE=Você é um assistente técnico. Seja preciso, use terminologia correta, sem emojis.

# Casual e jovem
VOICE_TONE=Você é o Léo, assistente da galera. Fala informal, usa gírias, pode usar emoji 😎

# Bilíngue
VOICE_TONE=You are Lia, Klabin's virtual assistant. Respond in the same language the user writes in.
```

### Mudar o modelo

```env
OPENAI_MODEL=gpt-4o         # Mais inteligente, mais caro
OPENAI_MODEL=gpt-4o-mini    # Bom equilíbrio (default)
OPENAI_MODEL=gpt-3.5-turbo  # Mais barato, menos preciso
```
----

## Stack

- **[LangGraph](https://github.com/langchain-ai/langgraph)** — Orquestração de grafos com estado
- **[LangChain](https://github.com/langchain-ai/langchain)** — Abstração de LLMs
- **[FastAPI](https://fastapi.tiangolo.com/)** — API HTTP
- **[Pydantic](https://docs.pydantic.dev/)** — Validação de schemas
- **[OpenAI](https://platform.openai.com/)** — LLM (substituível por Azure OpenAI ou Anthropic)