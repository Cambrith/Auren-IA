"""Executor e parser stream-json do harness Claude Code (/opt/bin/claude) em PT-BR."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from .fcc_bridge import DEFAULT_FCC_TOKEN, DEFAULT_FCC_URL, build_claude_env
from .theme import console, format_tool_summary, print_error, translate_tool_name

MINERVA_PTBR_SYSTEM_PROMPT = (
    "Você é a Minerva Dev, assistente de engenharia de software no terminal do usuário. "
    "Responda, explique, planeje e converse SEMPRE em Português do Brasil (PT-BR) claro e natural. "
    "Mantenha identificadores de código, nomes de símbolos, caminhos de arquivos e comandos exatos "
    "conforme aparecem no projeto."
)


@dataclass
class ParsedEvent:
    kind: str  # init | text_delta | thinking_delta | tool_use | tool_result | result | ignored
    session_id: str | None = None
    text: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    is_error: bool = False
    duration_ms: int | None = None
    cost_usd: float | None = None


def parse_stream_event(raw_line: str) -> list[ParsedEvent]:
    """Converte uma linha NDJSON de `claude --output-format stream-json` em eventos tipados."""
    line = raw_line.strip()
    if not line:
        return []
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []

    ev_type = payload.get("type")

    if ev_type == "system" and payload.get("subtype") == "init":
        return [
            ParsedEvent(
                kind="init",
                session_id=payload.get("session_id"),
            )
        ]

    if ev_type == "stream_event":
        inner = payload.get("event")
        if not isinstance(inner, dict):
            return []
        if inner.get("type") == "content_block_delta":
            delta = inner.get("delta")
            if not isinstance(delta, dict):
                return []
            d_type = delta.get("type")
            if d_type == "text_delta":
                return [ParsedEvent(kind="text_delta", text=str(delta.get("text") or ""))]
            if d_type == "thinking_delta":
                return [
                    ParsedEvent(
                        kind="thinking_delta",
                        text=str(delta.get("thinking") or ""),
                    )
                ]
        return []

    if ev_type == "assistant":
        msg = payload.get("message")
        if not isinstance(msg, dict):
            return []
        content = msg.get("content")
        if not isinstance(content, list):
            return []
        events: list[ParsedEvent] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            b_type = block.get("type")
            if b_type == "tool_use":
                events.append(
                    ParsedEvent(
                        kind="tool_use",
                        tool_name=str(block.get("name") or "Ferramenta"),
                        tool_input=block.get("input")
                        if isinstance(block.get("input"), dict)
                        else {},
                    )
                )
        return events

    if ev_type == "user":
        msg = payload.get("message")
        if not isinstance(msg, dict):
            return []
        content = msg.get("content")
        if not isinstance(content, list):
            return []
        events = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                raw_res = block.get("content")
                if isinstance(raw_res, list):
                    text_parts = [
                        str(item.get("text") or "")
                        for item in raw_res
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                    res_text = "\n".join(p for p in text_parts if p)
                else:
                    res_text = str(raw_res or "")
                events.append(
                    ParsedEvent(
                        kind="tool_result",
                        text=res_text,
                        is_error=bool(block.get("is_error")),
                    )
                )
        return events

    if ev_type == "result":
        return [
            ParsedEvent(
                kind="result",
                session_id=payload.get("session_id"),
                text=str(payload.get("result") or ""),
                is_error=bool(payload.get("is_error") or payload.get("subtype") == "error"),
                duration_ms=payload.get("duration_ms"),
                cost_usd=payload.get("total_cost_usd"),
            )
        ]

    return []


def resolve_claude_binary() -> str:
    """Retorna o caminho do executável Claude Code CLI."""
    found = shutil.which("claude")
    if found:
        return found
    if os.path.exists("/opt/bin/claude"):
        return "/opt/bin/claude"
    raise FileNotFoundError("Executável 'claude' não encontrado em /opt/bin/claude nem no PATH.")


def build_claude_command(
    prompt: str,
    *,
    session_id: str | None = None,
    continue_last: bool = False,
    permission_mode: str = "bypassPermissions",
    model: str | None = None,
    extra_dirs: list[str] | None = None,
    effort: str | None = None,
) -> list[str]:
    """Monta os argumentos de linha de comando para o harness Claude Code."""
    cmd = [
        resolve_claude_binary(),
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--append-system-prompt",
        MINERVA_PTBR_SYSTEM_PROMPT,
    ]
    if session_id:
        cmd.extend(["--resume", session_id])
    elif continue_last:
        cmd.append("--continue")

    if permission_mode == "bypassPermissions":
        cmd.append("--dangerously-skip-permissions")
    elif permission_mode:
        cmd.extend(["--permission-mode", permission_mode])

    if model:
        cmd.extend(["--model", model])

    if extra_dirs:
        for d in extra_dirs:
            if d:
                cmd.extend(["--add-dir", d])

    if effort in {"low", "medium", "high"}:
        cmd.extend(["--effort", effort])

    return cmd


def list_recent_sessions(cwd: str, limit: int = 8) -> list[dict[str, str]]:
    """Lista sessões recentes do Claude Code salvas em ~/.claude/projects para a pasta atual."""
    encoded = "-" + cwd.lstrip("/").replace("/", "-").replace(" ", "-")
    proj_dir = Path.home() / ".claude" / "projects" / encoded
    if not proj_dir.is_dir():
        return []
    files = sorted(
        (p for p in proj_dir.glob("*.jsonl") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    sessions: list[dict[str, str]] = []
    for p in files[:limit]:
        sid = p.stem
        preview = ""
        try:
            with p.open("r", encoding="utf-8", errors="replace") as fh:
                for raw in fh:
                    if '"type":"user"' in raw or '"type": "user"' in raw:
                        obj = json.loads(raw)
                        msg = obj.get("message") or {}
                        content = msg.get("content")
                        if isinstance(content, str) and content.strip():
                            preview = content.strip().splitlines()[0][:70]
                            break
                        if isinstance(content, list):
                            for blk in content:
                                if isinstance(blk, dict) and blk.get("type") == "text":
                                    txt = str(blk.get("text") or "").strip()
                                    if txt:
                                        preview = txt.splitlines()[0][:70]
                                        break
                            if preview:
                                break
        except Exception:
            pass
        sessions.append({"id": sid, "preview": preview or "(sem prévia)"})
    return sessions


def quick_side_question(
    question: str,
    *,
    model: str,
    fcc_url: str = DEFAULT_FCC_URL,
    fcc_token: str = DEFAULT_FCC_TOKEN,
) -> tuple[bool, str]:
    """Executa uma pergunta paralela (/paralela) sem afetar o contexto da sessão principal."""
    try:
        resp = httpx.post(
            f"{fcc_url.rstrip('/')}/v1/messages",
            headers={"x-api-key": fcc_token, "anthropic-version": "2023-06-01"},
            json={
                "model": model,
                "max_tokens": 1024,
                "system": MINERVA_PTBR_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": question}],
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            return False, f"Erro HTTP {resp.status_code}: {resp.text[:180]}"
        blocks = resp.json().get("content") or []
        texts = [str(b.get("text") or "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
        return True, "\n".join(texts).strip() or "(sem resposta)"
    except httpx.HTTPError as exc:
        return False, f"Falha de conexão: {exc}"


def copy_to_clipboard(text: str) -> bool:
    """Copia texto para a área de transferência do sistema (Wayland/X11)."""
    for cmd in (
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ):
        exe = shutil.which(cmd[0])
        if not exe:
            continue
        try:
            proc = subprocess.run([exe, *cmd[1:]], input=text, text=True, timeout=3.0)
            if proc.returncode == 0:
                return True
        except Exception:
            continue
    return False


@dataclass
class TurnOutcome:
    session_id: str | None
    ok: bool
    duration_ms: int | None = None


def run_minerva_turn(
    prompt: str,
    *,
    cwd: str,
    session_id: str | None = None,
    continue_last: bool = False,
    permission_mode: str = "bypassPermissions",
    model: str | None = None,
    fcc_url: str = DEFAULT_FCC_URL,
    fcc_token: str = DEFAULT_FCC_TOKEN,
) -> TurnOutcome:
    """Executa um turno completo no harness Claude Code com renderização 100% PT-BR."""
    cmd = build_claude_command(
        prompt,
        session_id=session_id,
        continue_last=continue_last,
        permission_mode=permission_mode,
        model=model,
    )
    env = build_claude_env(proxy_url=fcc_url, auth_token=fcc_token)

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    active_session = session_id
    accumulated_text = ""
    final_result_text = ""
    is_error = False
    duration_ms: int | None = None
    phase_label = "Minerva está pensando…"

    def _render_live() -> Group:
        parts: list[Any] = []
        if accumulated_text.strip():
            parts.append(
                Panel(
                    Markdown(accumulated_text),
                    title="[minerva.primary]Minerva[/]",
                    title_align="left",
                    border_style="#0284c7",
                    padding=(0, 1),
                )
            )
        if phase_label:
            parts.append(
                Spinner("dots", text=Text(f" {phase_label}", style="minerva.accent"))
            )
        return Group(*parts) if parts else Group(Text(""))

    try:
        assert proc.stdout is not None
        with Live(_render_live(), console=console, refresh_per_second=12, transient=True) as live:
            for line in proc.stdout:
                for ev in parse_stream_event(line):
                    if ev.kind == "init" and ev.session_id:
                        active_session = ev.session_id
                    elif ev.kind == "thinking_delta":
                        phase_label = "Minerva está raciocinando…"
                        live.update(_render_live())
                    elif ev.kind == "text_delta":
                        accumulated_text += ev.text
                        phase_label = "Minerva está respondendo…"
                        live.update(_render_live())
                    elif ev.kind == "tool_use":
                        label, icon = translate_tool_name(ev.tool_name)
                        summary = format_tool_summary(ev.tool_name, ev.tool_input)
                        phase_label = f"{label}…"
                        live.update(_render_live())
                        detail = f" [minerva.muted]{summary}[/]" if summary else ""
                        live.console.print(
                            f"  {icon} [minerva.tool]{label}[/]{detail}"
                        )
                    elif ev.kind == "tool_result":
                        if ev.is_error and ev.text.strip():
                            snippet = ev.text.strip().splitlines()[0][:140]
                            live.console.print(
                                f"     [minerva.err]↳ erro:[/] [minerva.muted]{snippet}[/]"
                            )
                        phase_label = "Analisando resultado…"
                        live.update(_render_live())
                    elif ev.kind == "result":
                        if ev.session_id:
                            active_session = ev.session_id
                        final_result_text = ev.text
                        is_error = ev.is_error
                        duration_ms = ev.duration_ms
                        phase_label = ""
                        live.update(_render_live())

        stderr_output = proc.stderr.read().strip() if proc.stderr else ""
        rc = proc.wait()

        output_to_show = (accumulated_text or final_result_text).strip()
        if output_to_show:
            console.print(
                Panel(
                    Markdown(output_to_show),
                    title="[minerva.primary]Minerva[/]",
                    title_align="left",
                    border_style="#ef4444" if is_error else "#0284c7",
                    padding=(0, 1),
                )
            )
        elif rc != 0 or is_error:
            print_error(stderr_output or f"O processo retornou código {rc}.")

        if duration_ms is not None:
            secs = duration_ms / 1000.0
            console.print(
                Text(f"  ✓ Concluído em {secs:.1f}s", style="minerva.muted")
            )

        return TurnOutcome(
            session_id=active_session,
            ok=(rc == 0 and not is_error),
            duration_ms=duration_ms,
        )
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        console.print()
        print_error("Execução interrompida pelo usuário.")
        return TurnOutcome(session_id=active_session, ok=False)


def launch_native_claude_tui(
    *,
    cwd: str,
    model: str | None = None,
    fcc_url: str = DEFAULT_FCC_URL,
    fcc_token: str = DEFAULT_FCC_TOKEN,
) -> int:
    """Inicia a TUI original do Claude Code já conectada ao Free Claude Code."""
    cmd = [
        resolve_claude_binary(),
        "--append-system-prompt",
        MINERVA_PTBR_SYSTEM_PROMPT,
    ]
    if model:
        cmd.extend(["--model", model])
    env = build_claude_env(proxy_url=fcc_url, auth_token=fcc_token)
    return subprocess.call(cmd, cwd=cwd, env=env)
