"""
CLI interativo para testar o orquestrador.

  python cli.py                # Via HTTP (server rodando)
  python cli.py --direct       # Executa grafo diretamente
"""

from __future__ import annotations

import argparse
import json


def _print_debug(data: dict):
    """Imprime debug info de forma legível."""
    classification = data.get("classification")
    node_result = data.get("node_result")
    debug = data.get("debug", {})

    if classification:
        c = classification if isinstance(classification, dict) else classification.model_dump()
        print(f"\033[90m  ┌─ classification: mode={c['mode']} intent={c.get('intent', '-')} "
              f"conf={c.get('confidence', 0):.2f} missing={c.get('missing_slots', [])}\033[0m")
        if c.get("extracted_slots"):
            print(f"\033[90m  │  extracted_slots: {c['extracted_slots']}\033[0m")

    if node_result:
        nr = node_result if isinstance(node_result, dict) else node_result.model_dump()
        print(f"\033[90m  ├─ node_result: source={nr['source_node']} status={nr['status']}\033[0m")
        if nr.get("data"):
            for k, v in nr["data"].items():
                print(f"\033[90m  │    {k}: {v}\033[0m")
        if nr.get("error_message"):
            print(f"\033[91m  │  error: {nr['error_message']}\033[0m")

    if debug:
        path = debug.get("node_path", [])
        print(f"\033[90m  └─ path: {' → '.join(path)}  slots={debug.get('slots', {})}\033[0m")


def run_via_api():
    """Testa via HTTP."""
    import httpx

    base_url = "http://localhost:8000"
    session_id = None

    print("\n╔══════════════════════════════════════════════╗")
    print("║    A2A Orchestrator v0.2 — CLI (API)         ║")
    print("║    Todos os nós → JSON → Synthesis → Resposta║")
    print("╚══════════════════════════════════════════════╝")
    print("  'sair' para encerrar | 'debug' para toggle\n")

    show_debug = True

    while True:
        try:
            user_input = input("\033[92mVocê:\033[0m ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAté logo!")
            break

        if user_input.lower() in ("sair", "exit", "quit"):
            break
        if user_input.lower() == "debug":
            show_debug = not show_debug
            print(f"  Debug {'ON' if show_debug else 'OFF'}")
            continue
        if not user_input:
            continue

        try:
            resp = httpx.post(
                f"{base_url}/chat",
                json={"session_id": session_id, "message": user_input},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            session_id = data["session_id"]

            if show_debug:
                _print_debug(data)

            print(f"\033[94mAava:\033[0m {data['response']}\n")

        except httpx.ConnectError:
            print("\033[91m  ✗ Server não rodando. Use: python main.py\033[0m")
        except Exception as e:
            print(f"\033[91m  ✗ Erro: {e}\033[0m")


def run_direct():
    """Executa grafo diretamente."""
    from app.graph import orchestrator_graph
    from app.schemas import GraphState
    from app.session import session_manager

    print("\n╔══════════════════════════════════════════════╗")
    print("║  A2A Orchestrator v0.2 — CLI (Direto)        ║")
    print("║  Todos os nós → JSON → Synthesis → Resposta   ║")
    print("╚══════════════════════════════════════════════╝")
    print("  'sair' para encerrar | 'debug' para toggle\n")

    state = session_manager.get_or_create()
    print(f"  Session: {state.session_id}\n")
    show_debug = True

    while True:
        try:
            user_input = input("\033[92mVocê:\033[0m ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAté logo!")
            break

        if user_input.lower() in ("sair", "exit", "quit"):
            break
        if user_input.lower() == "debug":
            show_debug = not show_debug
            print(f"  Debug {'ON' if show_debug else 'OFF'}")
            continue
        if not user_input:
            continue

        state.user_input = user_input

        try:
            result = orchestrator_graph.invoke(state.model_dump())
            state = GraphState(**result)

            if show_debug:
                _print_debug({
                    "classification": state.classification.model_dump() if state.classification else None,
                    "node_result": state.node_result.model_dump() if state.node_result else None,
                    "debug": {
                        "slots": state.slots,
                        "current_intent": state.current_intent,
                        "node_path": ["intake", "classification",
                                      state.classification.mode.value if state.classification else "?",
                                      "synthesis"],
                    },
                })

            print(f"\033[94mAava:\033[0m {state.response}\n")
            session_manager.save(state)

        except Exception as e:
            print(f"\033[91m  ✗ Erro: {e}\033[0m")
            import traceback
            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="A2A Orchestrator CLI")
    parser.add_argument("--direct", action="store_true", help="Executa grafo diretamente")
    args = parser.parse_args()

    if args.direct:
        run_direct()
    else:
        run_via_api()


if __name__ == "__main__":
    main()
