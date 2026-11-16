"""Ponto de entrada CLI e REPL interativo da Minerva Dev (100% PT-BR)."""

from __future__ import annotations

import argparse
import getpass
import os
from dataclasses import dataclass
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from rich.table import Table

from . import __version__
from .claude_harness import launch_native_claude_tui, run_minerva_turn
from .fcc_bridge import (
    DEFAULT_FCC_URL,
    FREE_PROVIDER_PRESETS,
    MINERVA_DEV_MODES,
    FccStatus,
    apply_fcc_config,
    apply_minerva_mode,
    ensure_fcc_running,
    fetch_fcc_models,
    fetch_fcc_status,
    format_model_name,
    format_provider_name,
    test_fcc_provider,
)
from .theme import (
    PERMISSION_LABELS_PT,
    console,
    print_error,
    print_help_pt,
    print_info,
    render_banner,
)

MODE_ALIASES: dict[str, str] = {
    "padrao": "default",
    "padrão": "default",
    "default": "default",
    "editar": "acceptEdits",
    "acceptedits": "acceptEdits",
    "livre": "bypassPermissions",
    "bypasspermissions": "bypassPermissions",
}


@dataclass
class ReplState:
    cwd: str
    session_id: str | None = None
    continue_last: bool = False
    permission_mode: str = "bypassPermissions"
    model: str | None = None
    fcc_url: str = DEFAULT_FCC_URL


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos da CLI Minerva Dev em PT-BR."""
    parser = argparse.ArgumentParser(
        prog="minerva",
        description="Minerva Dev — Assistente de código no terminal (PT-BR) sobre Free Claude Code.",
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="help", help="Mostra esta ajuda e sai")
    parser.add_argument(
        "-v", "--versao", action="version", version=f"Minerva Dev {__version__}", help="Mostra a versão"
    )
    parser.add_argument(
        "prompt", nargs="*", help="Tarefa ou pergunta inicial para a Minerva"
    )
    parser.add_argument(
        "-c", "--continuar", action="store_true", help="Continua a última sessão neste diretório"
    )
    parser.add_argument(
        "-r", "--retomar", metavar="ID", help="Retoma uma sessão específica pelo ID"
    )
    parser.add_argument(
        "-u", "--unica", action="store_true", help="Executa apenas o prompt informado e encerra"
    )
    parser.add_argument(
        "-m", "--modelo", metavar="MODELO", help="Define manualmente o modelo usado pelo harness"
    )
    parser.add_argument(
        "--perfil",
        choices=["harmonia", "sabia", "impeto"],
        help="Ativa um dos 3 modos da Minerva (harmonia, sabia ou impeto)",
    )
    parser.add_argument(
        "--modo",
        choices=["padrao", "editar", "livre"],
        default="livre",
        help="Política de permissão: padrao, editar ou livre (padrão, sem pausas)",
    )
    parser.add_argument(
        "--status", action="store_true", help="Exibe o status do Free Claude Code e sai"
    )
    parser.add_argument(
        "--configurar", action="store_true", help="Configura um provedor gratuito no Free Claude Code"
    )
    parser.add_argument(
        "--claude-nativo",
        action="store_true",
        help="Abre a TUI original do Claude Code conectada ao Free Claude Code",
    )
    parser.add_argument(
        "--simples",
        action="store_true",
        help="Usa o modo linha a linha simples em vez da interface gráfica de terminal (TUI)",
    )
    return parser


def print_status_table(status: FccStatus) -> None:
    """Exibe tabela de diagnóstico em PT-BR."""
    table = Table(title="Diagnóstico Minerva Dev", border_style="#0284c7")
    table.add_column("Componente", style="bold #7dd3fc")
    table.add_column("Estado", style="white")
    table.add_row(
        "Servidor Free Claude Code",
        f"[minerva.ok]Online[/] ({status.url})" if status.online else "[minerva.err]Offline[/]",
    )
    table.add_row(
        "Claude Code CLI",
        "[minerva.ok]Instalado[/]" if status.claude_installed else "[minerva.err]Não encontrado[/]",
    )
    table.add_row(
        "Modelo padrão (FCC)",
        format_model_name(status.active_model) if status.active_model else "[minerva.warn]Não definido[/]",
    )
    table.add_row(
        "Provedores com chave",
        ", ".join(format_provider_name(p) for p in status.configured_providers)
        if status.configured_providers
        else "[minerva.warn]Nenhum configurado[/]",
    )
    console.print(table)


def run_provider_wizard(fcc_url: str = DEFAULT_FCC_URL) -> None:
    """Assistente interativo em PT-BR para configurar chave de API gratuita no FCC."""
    if not ensure_fcc_running(fcc_url):
        print_error("Não foi possível iniciar o servidor fcc-server na porta 8082.")
        return

    console.print("\n[minerva.primary]Configuração de Provedor Gratuito (Free Claude Code)[/]")
    choices = list(FREE_PROVIDER_PRESETS.items())
    for idx, (_pid, info) in enumerate(choices, start=1):
        console.print(f"  [minerva.accent]{idx}[/]. {info['label']}  [minerva.muted]({info['default_model']})[/]")
    console.print("  [minerva.accent]0[/]. Cancelar\n")

    raw = input("Escolha o número do provedor: ").strip()
    if not raw or raw == "0":
        print_info("Configuração cancelada.")
        return
    try:
        selected_idx = int(raw) - 1
        provider_id, info = choices[selected_idx]
    except (ValueError, IndexError):
        print_error("Opção inválida.")
        return

    api_key = getpass.getpass(f"Cole sua chave ({info['env_key']}): ").strip()
    if not api_key:
        print_error("Nenhuma chave informada.")
        return

    ok, msg = apply_fcc_config(
        {
            info["env_key"]: api_key,
            "MODEL": info["default_model"],
        },
        base_url=fcc_url,
    )
    if not ok:
        print_error(msg)
        return
    print_info(msg)

    print_info(f"Testando conexão com {info['label']}…")
    test_ok, test_msg = test_fcc_provider(provider_id, base_url=fcc_url)
    if test_ok:
        print_info(f"Conexão aprovada: {test_msg}")
    else:
        print_error(f"Aviso no teste: {test_msg}")


def handle_slash_command(raw_input: str, state: ReplState) -> str:
    """Processa comandos /... em PT-BR. Retorna 'exit', 'clear', 'handled' ou 'prompt'."""
    text = raw_input.strip()
    if not text.startswith("/"):
        return "prompt"

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"/sair", "/exit", "/quit"}:
        print_info("Até logo!")
        return "exit"

    if cmd in {"/ajuda", "/help"}:
        print_help_pt()
        return "handled"

    if cmd in {"/limpar", "/clear"}:
        console.clear()
        return "clear"

    if cmd in {"/nova", "/new"}:
        state.session_id = None
        state.continue_last = False
        print_info("Nova sessão iniciada. O contexto anterior foi limpo.")
        return "handled"

    if cmd in {"/sessoes", "/sessões", "/session"}:
        if state.session_id:
            print_info(f"Sessão atual: {state.session_id}")
            console.print(
                f"  [minerva.muted]Para retomar depois:[/] minerva --retomar {state.session_id}"
            )
        else:
            print_info("Nenhuma sessão iniciada ainda neste turno.")
        return "handled"

    if cmd == "/status":
        print_status_table(fetch_fcc_status(state.fcc_url))
        return "handled"

    if cmd == "/provedor":
        run_provider_wizard(state.fcc_url)
        return "handled"

    if cmd == "/perfil":
        if not arg:
            for mid, m in MINERVA_DEV_MODES.items():
                print_info(f"{m['label']} ({mid}): {m['description']} -> {m['model']}")
            return "handled"
        ok, primary, msg = apply_minerva_mode(arg, base_url=state.fcc_url)
        if ok:
            state.model = primary
            print_info(msg)
        else:
            print_error(msg)
        return "handled"

    if cmd == "/modo":
        if not arg:
            current_label = PERMISSION_LABELS_PT.get(state.permission_mode, state.permission_mode)
            print_info(f"Modo atual: {current_label}")
            console.print("  [minerva.muted]Use: /modo padrao | /modo editar | /modo livre[/]")
            return "handled"
        mapped = MODE_ALIASES.get(arg.lower())
        if not mapped:
            print_error("Modo inválido. Use: padrao, editar ou livre.")
            return "handled"
        state.permission_mode = mapped
        print_info(f"Modo alterado para: {PERMISSION_LABELS_PT[mapped]}")
        return "handled"

    if cmd == "/modelo":
        if not arg:
            models = fetch_fcc_models(state.fcc_url)
            if not models:
                print_info(
                    f"Modelo ativo no FCC: {state.model or fetch_fcc_status(state.fcc_url).active_model or 'padrão'}"
                )
                return "handled"
            table = Table(title="Modelos disponíveis no FCC", border_style="#0284c7")
            table.add_column("ID do Modelo", style="bold #38bdf8")
            table.add_column("Provedor", style="white")
            for item in models[:25]:
                mid = str(item.get("id") or item.get("model") or "")
                prov = str(item.get("provider") or (mid.split("/")[0] if "/" in mid else ""))
                if mid:
                    table.add_row(mid, prov)
            console.print(table)
            console.print("  [minerva.muted]Para trocar: /modelo <id_do_modelo>[/]")
            return "handled"
        ok, msg = apply_fcc_config({"MODEL": arg}, base_url=state.fcc_url)
        if ok:
            state.model = arg
            print_info(f"Modelo alterado para {arg}.")
        else:
            print_error(msg)
        return "handled"

    print_error(f"Comando desconhecido: {cmd}. Digite /ajuda para ver os comandos.")
    return "handled"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cwd = os.getcwd()

    ensure_fcc_running(DEFAULT_FCC_URL)
    status = fetch_fcc_status(DEFAULT_FCC_URL)

    if args.status:
        print_status_table(status)
        return 0

    if args.configurar:
        run_provider_wizard(DEFAULT_FCC_URL)
        return 0

    if not status.claude_installed:
        print_error("Claude Code CLI (/opt/bin/claude) não encontrado no sistema.")
        return 1

    if args.claude_nativo:
        return launch_native_claude_tui(cwd=cwd, model=args.modelo, fcc_url=DEFAULT_FCC_URL)

    selected_model = args.modelo
    if args.perfil and not selected_model:
        ok, primary, msg = apply_minerva_mode(args.perfil, base_url=DEFAULT_FCC_URL)
        if ok:
            selected_model = primary
        else:
            print_error(msg)

    permission_mode = MODE_ALIASES.get(args.modo, "acceptEdits")
    state = ReplState(
        cwd=cwd,
        session_id=args.retomar,
        continue_last=bool(args.continuar and not args.retomar),
        permission_mode=permission_mode,
        model=selected_model,
    )

    initial_prompt = " ".join(args.prompt).strip()
    if args.unica:
        if not initial_prompt:
            print_error("Informe um prompt ao usar --unica.")
            return 2
        outcome = run_minerva_turn(
            initial_prompt,
            cwd=state.cwd,
            session_id=state.session_id,
            continue_last=state.continue_last,
            permission_mode=state.permission_mode,
            model=state.model,
            fcc_url=state.fcc_url,
        )
        return 0 if outcome.ok else 1

    if not args.simples:
        from .tui import run_tui

        return run_tui(
            cwd=state.cwd,
            initial_prompt=initial_prompt,
            session_id=state.session_id,
            continue_last=state.continue_last,
            permission_mode=state.permission_mode,
            model=state.model,
            fcc_url=state.fcc_url,
        )

    render_banner(
        cwd=state.cwd,
        model=state.model or status.active_model,
        fcc_online=status.online,
        providers_configured=status.configured_providers,
        permission_mode=state.permission_mode,
    )

    if not status.configured_providers:
        console.print(
            "[minerva.warn]⚠ Nenhum provedor com chave de API configurada no Free Claude Code.[/]\n"
            "  [minerva.muted]Digite [minerva.accent]/provedor[/minerva.accent] para configurar "
            "uma chave gratuita (NVIDIA NIM, Gemini, Groq ou OpenRouter) ou acesse "
            "http://127.0.0.1:8082/admin.[/]\n"
        )

    if initial_prompt:
        outcome = run_minerva_turn(
            initial_prompt,
            cwd=state.cwd,
            session_id=state.session_id,
            continue_last=state.continue_last,
            permission_mode=state.permission_mode,
            model=state.model,
            fcc_url=state.fcc_url,
        )
        if outcome.session_id:
            state.session_id = outcome.session_id
            state.continue_last = False

    history_dir = Path.home() / ".local" / "share" / "minerva-dev"
    history_dir.mkdir(parents=True, exist_ok=True)
    prompt_session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_dir / "history"))
    )

    while True:
        try:
            user_text = prompt_session.prompt(
                HTML("<ansicyan><b>minerva</b></ansicyan> <ansibrightblack>❯</ansibrightblack> ")
            )
        except KeyboardInterrupt:
            console.print()
            continue
        except EOFError:
            print_info("Até logo!")
            break

        if not user_text.strip():
            continue

        action = handle_slash_command(user_text, state)
        if action == "exit":
            break
        if action == "clear":
            status = fetch_fcc_status(state.fcc_url)
            render_banner(
                cwd=state.cwd,
                model=state.model or status.active_model,
                fcc_online=status.online,
                providers_configured=status.configured_providers,
                permission_mode=state.permission_mode,
            )
            continue
        if action == "handled":
            continue

        outcome = run_minerva_turn(
            user_text.strip(),
            cwd=state.cwd,
            session_id=state.session_id,
            continue_last=state.continue_last,
            permission_mode=state.permission_mode,
            model=state.model,
            fcc_url=state.fcc_url,
        )
        if outcome.session_id:
            state.session_id = outcome.session_id
            state.continue_last = False

    return 0
