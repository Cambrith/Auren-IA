"""Interface gráfica de terminal (TUI) da Minerva Dev — réplica do Claude Code CLI em 100% PT-BR com identidade Minerva."""

from __future__ import annotations

import datetime
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from rich.markdown import Markdown as RichMarkdown
from rich.table import Table
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from . import __version__
from .claude_harness import (
    build_claude_command,
    copy_to_clipboard,
    list_recent_sessions,
    parse_stream_event,
    quick_side_question,
)
from .commands import MINERVA_COMMANDS, find_command_spec, match_slash_commands
from .fcc_bridge import (
    DEFAULT_FCC_TOKEN,
    DEFAULT_FCC_URL,
    FREE_PROVIDER_PRESETS,
    MINERVA_DEV_MODES,
    apply_fcc_config,
    apply_minerva_mode,
    build_claude_env,
    detect_minerva_mode,
    ensure_fcc_running,
    fetch_fcc_models,
    fetch_fcc_status,
    format_model_name,
    format_provider_name,
    test_fcc_provider,
)
from .mascot import MinervaMascot
from .theme import (
    MINERVA_ART_LINES,
    PERMISSION_LABELS_PT,
    format_tool_summary,
    render_minerva_animation_frame,
    translate_tool_name,
)

MODE_ORDER = ["bypassPermissions", "acceptEdits", "default", "plan"]
MODE_SHORT_PT = {
    "bypassPermissions": "Sem pausas",
    "acceptEdits": "Auto-edição",
    "default": "Padrão",
    "plan": "Planejar",
}
MODE_ALIASES_TUI = {
    "padrao": "default",
    "padrão": "default",
    "default": "default",
    "editar": "acceptEdits",
    "acceptedits": "acceptEdits",
    "livre": "bypassPermissions",
    "bypasspermissions": "bypassPermissions",
    "plan": "plan",
    "planejar": "plan",
}

EFFORT_ALIASES_PT = {
    "baixo": "low",
    "low": "low",
    "medio": "medium",
    "médio": "medium",
    "medium": "medium",
    "alto": "high",
    "high": "high",
}


def _short_cwd(cwd: str) -> str:
    return os.path.basename(cwd.rstrip(os.sep)) or cwd


def _short_model(model: str) -> str:
    return format_model_name(model)


class ProviderConfigModal(ModalScreen[bool]):
    """Modal em PT-BR para configurar chave de API no Free Claude Code."""

    CSS = """
    ProviderConfigModal {
        align: center middle;
        background: rgba(4, 7, 15, 0.80);
    }
    #prov-dialog {
        width: 68;
        height: auto;
        background: #0f172a;
        border: tall #38bdf8;
        padding: 1 2;
    }
    #prov-title {
        color: #7dd3fc;
        text-style: bold;
        margin-bottom: 1;
    }
    #prov-list {
        height: 7;
        border: none;
        background: #090e1a;
        margin-bottom: 1;
    }
    #prov-key-label {
        color: #94a3b8;
    }
    #prov-key-input {
        margin-bottom: 1;
        border: tall #1e3a5f;
        background: #090e1a;
    }
    #prov-key-input:focus {
        border: tall #38bdf8;
    }
    #prov-feedback {
        color: #94a3b8;
        height: auto;
        margin-bottom: 1;
    }
    #prov-buttons {
        height: auto;
        align: right middle;
    }
    #prov-buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS = [Binding("escape", "dismiss(False)", "Fechar")]

    def __init__(self, fcc_url: str = DEFAULT_FCC_URL) -> None:
        super().__init__()
        self.fcc_url = fcc_url
        self._preset_ids = list(FREE_PROVIDER_PRESETS.keys())
        self._selected_provider = self._preset_ids[0]

    def compose(self) -> ComposeResult:
        with Vertical(id="prov-dialog"):
            yield Label("✦ Provedores · Free Claude Code", id="prov-title")
            options = [
                Option(f"{info['label']}  ·  {info['default_model']}", id=pid)
                for pid, info in FREE_PROVIDER_PRESETS.items()
            ]
            yield OptionList(*options, id="prov-list")
            yield Label("Chave de API:", id="prov-key-label")
            yield Input(
                placeholder="Cole a chave do provedor selecionado…",
                password=True,
                id="prov-key-input",
            )
            yield Static("", id="prov-feedback")
            with Horizontal(id="prov-buttons"):
                yield Button("Cancelar", id="prov-cancel")
                yield Button("Salvar e Testar", variant="primary", id="prov-save")

    def on_mount(self) -> None:
        self.query_one("#prov-list", OptionList).highlighted = 0

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option.id:
            self._selected_provider = str(event.option.id)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self._selected_provider = str(event.option.id)
        self.query_one("#prov-key-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "prov-cancel":
            self.dismiss(False)
            return
        if event.button.id == "prov-save":
            self._save_and_test()

    def _save_and_test(self) -> None:
        key_val = self.query_one("#prov-key-input", Input).value.strip()
        feedback = self.query_one("#prov-feedback", Static)
        if not key_val:
            feedback.update("[bold #ef4444]Informe uma chave de API antes de salvar.[/]")
            return

        info = FREE_PROVIDER_PRESETS[self._selected_provider]
        ok, msg = apply_fcc_config(
            {
                info["env_key"]: key_val,
                "MODEL": info["default_model"],
            },
            base_url=self.fcc_url,
        )
        if not ok:
            feedback.update(f"[bold #ef4444]{msg}[/]")
            return

        feedback.update("[#7dd3fc]Chave salva. Testando conexão…[/]")
        test_ok, test_msg = test_fcc_provider(self._selected_provider, base_url=self.fcc_url)
        if test_ok:
            self.dismiss(True)
        else:
            feedback.update(f"[bold #f59e0b]Salvo, mas o teste retornou aviso:[/] {test_msg}")


class ModelPickerModal(ModalScreen[str | None]):
    """Modal em PT-BR para selecionar o modelo ativo."""

    CSS = """
    ModelPickerModal {
        align: center middle;
        background: rgba(4, 7, 15, 0.80);
    }
    #model-dialog {
        width: 74;
        height: 20;
        background: #0f172a;
        border: tall #38bdf8;
        padding: 1 2;
    }
    #model-title {
        color: #7dd3fc;
        text-style: bold;
        margin-bottom: 1;
    }
    #model-list {
        height: 1fr;
        border: none;
        background: #090e1a;
        margin-bottom: 1;
    }
    #model-buttons {
        height: auto;
        align: right middle;
    }
    """

    BINDINGS = [Binding("escape", "dismiss(None)", "Fechar")]

    def __init__(self, fcc_url: str = DEFAULT_FCC_URL, current_model: str = "") -> None:
        super().__init__()
        self.fcc_url = fcc_url
        self.current_model = current_model

    def compose(self) -> ComposeResult:
        models = fetch_fcc_models(self.fcc_url)
        options: list[Option] = []
        active_mode = detect_minerva_mode(self.current_model)

        for mode_id, cfg in MINERVA_DEV_MODES.items():
            mark = "  ★" if active_mode == mode_id else ""
            options.append(
                Option(
                    f"✦ Modo {cfg['label']} — {cfg['description']}{mark}",
                    id=f"mode:{mode_id}",
                )
            )

        seen: set[str] = set()
        for item in models:
            mid = str(item.get("id") or item.get("model") or "")
            if mid and mid not in seen:
                seen.add(mid)
                prov = format_provider_name(str(item.get("provider") or (mid.split("/")[0] if "/" in mid else "")))
                label = f"{prov} · {format_model_name(mid)}"
                mark = "  ★" if mid == self.current_model else ""
                options.append(Option(f"{label}{mark}", id=mid))

        for pid, info in FREE_PROVIDER_PRESETS.items():
            mid = info["default_model"]
            if mid not in seen:
                seen.add(mid)
                prov = format_provider_name(pid)
                label = f"{prov} · {format_model_name(mid)}"
                mark = "  ★" if mid == self.current_model else ""
                options.append(Option(f"{label}{mark}", id=mid))

        with Vertical(id="model-dialog"):
            yield Label("✦ Modo Minerva ou Modelo Manual · Free Claude Code", id="model-title")
            yield OptionList(*options, id="model-list")
            with Horizontal(id="model-buttons"):
                yield Button("Cancelar", id="model-cancel")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.dismiss(str(event.option.id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "model-cancel":
            self.dismiss(None)


class MinervaApp(App[int]):
    """Réplica do Claude Code CLI em 100% PT-BR com paleta e marca Minerva."""

    TITLE = "Minerva Dev"
    ENABLE_COMMAND_PALETTE = False
    CSS = """
    Screen {
        background: transparent;
        color: #e2e8f0;
    }
    #header-bar {
        height: 1;
        background: transparent;
        color: #64748b;
        padding: 0 2;
    }
    #chat-scroll {
        height: 1fr;
        background: transparent;
        padding: 0 2 1 2;
        scrollbar-size: 1 1;
        scrollbar-color: #1e3a5f transparent;
        scrollbar-color-hover: #38bdf8 transparent;
    }
    .welcome-card {
        height: auto;
        background: #070e1c;
        border: round #1e3a5f;
        padding: 1 2;
        margin: 1 0;
        align: left middle;
    }
    #welcome-meta {
        width: 1fr;
        height: auto;
        padding-left: 2;
    }
    .user-msg {
        height: auto;
        background: #0b1629;
        color: #f8fafc;
        padding: 0 1;
        margin: 1 0 0 0;
    }
    .assistant-card {
        height: auto;
        background: transparent;
        padding: 1 0 0 0;
        margin: 0 0 1 0;
    }
    .assistant-card-err {
        height: auto;
        background: #1a0f14;
        border-left: wide #ef4444;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    .tools-box {
        height: auto;
    }
    .tools-box.has-tools {
        margin-bottom: 1;
    }
    .tool-line {
        height: auto;
        color: #e2e8f0;
        padding-left: 0;
    }
    .tool-subline {
        height: auto;
        color: #64748b;
        padding-left: 2;
        margin-bottom: 1;
    }
    .assistant-body {
        height: auto;
        padding-left: 2;
        margin-top: 0;
    }
    .status-line {
        height: auto;
        color: #38bdf8;
        padding-left: 2;
        margin-top: 0;
    }
    .info-card {
        height: auto;
        background: #070e1c;
        border-left: tall #38bdf8;
        padding: 0 2;
        margin: 1 0 0 0;
    }
    #composer-wrap {
        height: auto;
        background: transparent;
        padding: 0 2;
    }
    #composer-box {
        height: auto;
        background: transparent;
        border-top: solid #1e3a5f;
        border-bottom: solid #1e3a5f;
        padding: 0;
        align: left middle;
    }
    #composer-box:focus-within {
        border-top: solid #38bdf8;
        border-bottom: solid #38bdf8;
    }
    #composer-glyph {
        width: 2;
        color: #38bdf8;
        text-style: bold;
        content-align: left middle;
        height: 1;
    }
    #prompt-input {
        width: 1fr;
        background: transparent;
        border: none;
        padding: 0;
        height: 1;
        color: #f8fafc;
    }
    #prompt-input:focus {
        border: none;
    }
    #slash-menu {
        height: auto;
        max-height: 10;
        background: #070e1c;
        border: solid #1e3a5f;
        margin-bottom: 0;
        display: none;
    }
    #slash-menu:focus {
        border: solid #38bdf8;
    }
    #status-footer {
        height: 1;
        background: transparent;
        color: #64748b;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit_app", "Sair", priority=True),
        Binding("ctrl+n", "new_session", "Nova sessão", priority=True),
        Binding("ctrl+m", "pick_model", "Modelo", priority=True),
        Binding("ctrl+p", "config_provider", "Provedor", priority=True),
        Binding("ctrl+t", "cycle_mode", "Modo", priority=True),
        Binding("shift+tab", "cycle_mode", "Modo", priority=True),
        Binding("ctrl+l", "clear_feed", "Limpar", priority=True),
        Binding("escape", "cancel_run", "Interromper"),
    ]

    def __init__(
        self,
        *,
        cwd: str,
        initial_prompt: str = "",
        session_id: str | None = None,
        continue_last: bool = False,
        permission_mode: str = "bypassPermissions",
        model: str | None = None,
        fcc_url: str = DEFAULT_FCC_URL,
    ) -> None:
        super().__init__()
        self.cwd = cwd
        self.initial_prompt = initial_prompt
        self.session_id = session_id
        self.continue_last = continue_last
        self.permission_mode = permission_mode
        self.model = model
        self.fcc_url = fcc_url
        self.extra_dirs: list[str] = []
        self.effort: str | None = None
        self.focus_mode = False
        self._active_proc: subprocess.Popen[str] | None = None
        self._busy = False
        self._history: list[str] = []
        self._history_idx = -1
        self._assistant_responses: list[str] = []
        self._transcript: list[tuple[str, str]] = []
        self._branches: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="header-bar")
        yield VerticalScroll(id="chat-scroll")
        with Vertical(id="composer-wrap"):
            yield OptionList(id="slash-menu")
            with Horizontal(id="composer-box"):
                yield Static(">", id="composer-glyph")
                yield Input(
                    placeholder="Pergunte ou peça uma tarefa à Minerva… (/ajuda)",
                    id="prompt-input",
                )
        yield Static("", id="status-footer")

    def on_mount(self) -> None:
        ensure_fcc_running(self.fcc_url)
        self._refresh_chrome()
        self._append_welcome()
        self.query_one("#prompt-input", Input).focus()
        if self.initial_prompt:
            self._submit_text(self.initial_prompt)

    def _refresh_chrome(self) -> None:
        status = fetch_fcc_status(self.fcc_url)
        full_model = self.model or status.active_model
        active_model = _short_model(full_model)
        mode_id = detect_minerva_mode(full_model)
        minerva_mode_label = (
            MINERVA_DEV_MODES[mode_id]["label"] if mode_id else "Manual"
        )
        fcc_dot = "[#10b981]●[/]" if status.online else "[#ef4444]●[/]"
        mode_badge = MODE_SHORT_PT.get(self.permission_mode, self.permission_mode)

        self.query_one("#header-bar", Static).update(
            f"[bold #38bdf8]✦ Minerva Dev[/] [#475569]v{__version__}[/]  {fcc_dot}  "
            f"[bold #38bdf8]{minerva_mode_label}[/] [#7dd3fc]({active_model})[/]"
        )

        sess_txt = f"  [#334155]·[/]  [#475569]{self.session_id[:8]}[/]" if self.session_id else ""
        busy_txt = "  [#38bdf8]em andamento (Esc interrompe)[/]" if self._busy else ""
        self.query_one("#status-footer", Static).update(
            f"[#38bdf8]⏵⏵ {mode_badge}[/] [#475569](Shift+Tab)[/]  "
            f"[#475569]Ctrl+M[/] modelo  "
            f"[#475569]Ctrl+P[/] provedores  "
            f"[#475569]Ctrl+N[/] nova  "
            f"[#475569]Ctrl+Q[/] sair"
            f"{sess_txt}{busy_txt}"
        )

    def _append_welcome(self) -> None:
        status = fetch_fcc_status(self.fcc_url)
        full_model = self.model or status.active_model
        active_model = _short_model(full_model)
        raw_provider = full_model.split("/")[0] if "/" in full_model else ""
        active_provider = format_provider_name(raw_provider)
        mode_id = detect_minerva_mode(full_model)
        if mode_id:
            mcfg = MINERVA_DEV_MODES[mode_id]
            mode_line = f"[bold #38bdf8]{mcfg['label']}[/] [#64748b]· {mcfg['description']}[/]"
        else:
            mode_line = "[bold #7dd3fc]Manual[/] [#64748b]· modelo selecionado manualmente[/]"

        n_prov = len(status.configured_providers)
        prov_count = (
            f"[#10b981]{n_prov} provedores ativos[/]"
            if n_prov
            else "[#f59e0b]nenhum provedor ativo — use Ctrl+P[/]"
        )

        meta_lines = [
            f"[bold #38bdf8]Bem-vindo à Minerva Dev[/] [#64748b]v{__version__}[/]",
            "",
            f"[#64748b]Modo:[/]      {mode_line}",
            f"[#64748b]Provedor:[/]  [#e2e8f0]{active_provider}[/] · {prov_count}",
            f"[#64748b]Modelo:[/]    [#7dd3fc]{active_model}[/]",
            f"[#64748b]Pasta:[/]     [#94a3b8]{self.cwd}[/]",
            f"[#64748b]Comandos:[/]  [#7dd3fc]/ajuda · /perfil · /modelo · /modo · /provedor · /sair[/]",
        ]

        scroll = self.query_one("#chat-scroll", VerticalScroll)
        card = Horizontal(classes="welcome-card")
        scroll.mount(card)
        card.mount(
            MinervaMascot(id="minerva-mascot"),
            Static("\n".join(meta_lines), id="welcome-meta"),
        )
        scroll.scroll_end(animate=False)

    def _append_info(self, renderable: Any) -> None:
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.mount(Static(renderable, classes="info-card"))
        scroll.scroll_end(animate=False)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "prompt-input":
            return
        menu = self.query_one("#slash-menu", OptionList)
        val = event.value
        stripped = val.strip()
        if stripped.startswith("/") and " " not in stripped:
            matches = match_slash_commands(stripped)
            if matches:
                menu.clear_options()
                for spec in matches[:10]:
                    cmd_txt = f"{spec.name} {spec.args}".strip()
                    menu.add_option(
                        Option(
                            f"[bold #38bdf8]{cmd_txt:<28}[/] [#94a3b8]{spec.description}[/]",
                            id=spec.name,
                        )
                    )
                menu.highlighted = 0
                menu.display = True
                return
        menu.display = False

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id != "slash-menu" or not event.option.id:
            return
        cmd_name = str(event.option.id)
        spec = find_command_spec(cmd_name)
        inp = self.query_one("#prompt-input", Input)
        event.option_list.display = False
        if spec and spec.args.startswith("<"):
            inp.value = f"{cmd_name} "
            inp.cursor_position = len(inp.value)
            inp.focus()
            return
        inp.value = ""
        self._history.append(cmd_name)
        self._submit_text(cmd_name)
        inp.focus()

    def on_key(self, event: Any) -> None:
        inp = self.query_one("#prompt-input", Input)
        menu = self.query_one("#slash-menu", OptionList)
        if inp.has_focus and menu.display:
            if event.key == "down":
                if menu.option_count:
                    cur = 0 if menu.highlighted is None else menu.highlighted
                    menu.highlighted = (cur + 1) % menu.option_count
                event.prevent_default()
                return
            if event.key == "up":
                if menu.option_count:
                    cur = 0 if menu.highlighted is None else menu.highlighted
                    menu.highlighted = (cur - 1) % menu.option_count
                event.prevent_default()
                return
            if event.key == "tab" and menu.option_count:
                idx = 0 if menu.highlighted is None else menu.highlighted
                opt = menu.get_option_at_index(idx)
                if opt.id:
                    inp.value = f"{opt.id} "
                    inp.cursor_position = len(inp.value)
                    menu.display = False
                event.prevent_default()
                return
            if event.key == "escape":
                menu.display = False
                event.prevent_default()
                return

        if not inp.has_focus or not self._history:
            return
        if event.key == "up":
            if self._history_idx == -1:
                self._history_idx = len(self._history) - 1
            elif self._history_idx > 0:
                self._history_idx -= 1
            inp.value = self._history[self._history_idx]
            inp.cursor_position = len(inp.value)
            event.prevent_default()
        elif event.key == "down":
            if self._history_idx != -1:
                if self._history_idx < len(self._history) - 1:
                    self._history_idx += 1
                    inp.value = self._history[self._history_idx]
                else:
                    self._history_idx = -1
                    inp.value = ""
                inp.cursor_position = len(inp.value)
                event.prevent_default()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        menu = self.query_one("#slash-menu", OptionList)
        text = event.value.strip()
        if menu.display and text.startswith("/") and " " not in text and not find_command_spec(text):
            if menu.option_count:
                idx = 0 if menu.highlighted is None else menu.highlighted
                opt = menu.get_option_at_index(idx)
                if opt.id:
                    text = str(opt.id)
        event.input.value = ""
        menu.display = False
        self._history_idx = -1
        if not text:
            return
        self._history.append(text)
        self._submit_text(text)

    def _submit_text(self, text: str) -> None:
        if text.startswith("/"):
            self._handle_slash(text)
            return
        if self._busy:
            self._append_info(
                "[#f59e0b]Aguarde a resposta atual terminar ou pressione Esc para interromper.[/]"
            )
            return
        self._transcript.append(("Você", text))
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.mount(Static(f"[bold #38bdf8]>[/] {text}", classes="user-msg"))
        scroll.scroll_end(animate=False)
        self._run_claude_turn(text)

    @work(thread=True)
    def _run_side_question(self, question: str) -> None:
        st = fetch_fcc_status(self.fcc_url)
        model = self.model or st.active_model
        ok, ans = quick_side_question(question, model=model, fcc_url=self.fcc_url)
        prefix = "[bold #38bdf8]✦ Resposta paralela[/]" if ok else "[bold #ef4444]✖ Falha[/]"
        self.call_from_thread(self._append_info, f"{prefix}\n\n{ans}")

    def _handle_slash(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in {"/sair", "/exit", "/quit"}:
            self.action_quit_app()
            return
        if cmd in {"/ajuda", "/help"}:
            table = Table(
                title="Comandos · Minerva Dev",
                border_style="#1e3a5f",
                header_style="bold #7dd3fc",
                box=None,
            )
            table.add_column("Categoria", style="#64748b")
            table.add_column("Comando", style="bold #38bdf8")
            table.add_column("Ação", style="#e2e8f0")
            for spec in MINERVA_COMMANDS:
                cmd_col = f"{spec.name} {spec.args}".strip()
                table.add_row(spec.category, cmd_col, spec.description)
            self._append_info(table)
            return
        if cmd in {"/compactar", "/compact"}:
            self._submit_text(
                "Faça um resumo curto e objetivo em PT-BR do que já fizemos nesta sessão até agora para mantermos o foco."
            )
            return
        if cmd == "/limpar":
            self.action_clear_feed()
            return
        if cmd in {"/nova", "/clear", "/new"}:
            self.action_new_session()
            return
        if cmd in {"/retomar", "/resume"}:
            if arg:
                self.session_id = arg
                self.continue_last = False
                self._refresh_chrome()
                self._append_info(f"[#10b981]✓ Sessão retomada:[/] {arg}")
                return
            recent = list_recent_sessions(self.cwd)
            if not recent:
                self._append_info("Nenhuma sessão anterior encontrada para esta pasta.")
                return
            lines = [
                f"  [bold #38bdf8]{s['id'][:12]}[/]  [#94a3b8]{s['preview']}[/]"
                for s in recent
            ]
            self._append_info(
                "[bold #7dd3fc]Sessões recentes nesta pasta:[/]\n"
                + "\n".join(lines)
                + "\n[#64748b]Use: /retomar <id> (ou clique com --retomar)[/]"
            )
            return
        if cmd in {"/bifurcar", "/branch", "/fork"}:
            if self.session_id:
                self._branches.append(self.session_id)
            prev = self.session_id
            self.session_id = None
            self.continue_last = False
            self._refresh_chrome()
            self._append_info(
                f"✦ Ramificação criada (sessão anterior salva: {prev[:10] if prev else 'nenhuma'})."
            )
            return
        if cmd in {"/paralela", "/btw"}:
            if not arg:
                self._append_info("[#f59e0b]Uso: /paralela <sua pergunta rápida>[/]")
                return
            self._append_info(f"[#7dd3fc]↳ Pergunta paralela:[/] {arg}")
            self._run_side_question(arg)
            return
        if cmd in {"/copiar", "/copy"}:
            if not self._assistant_responses:
                self._append_info("Ainda não há resposta da Minerva para copiar.")
                return
            idx = 1
            if arg:
                try:
                    idx = max(1, int(arg))
                except ValueError:
                    self._append_info("[#ef4444]Informe um número válido (ex.: /copiar 2).[/]")
                    return
            if idx > len(self._assistant_responses):
                self._append_info(f"Só existem {len(self._assistant_responses)} respostas nesta sessão.")
                return
            target_text = self._assistant_responses[-idx]
            if copy_to_clipboard(target_text):
                self._append_info("[#10b981]✓ Resposta copiada para a área de transferência.[/]")
            else:
                self._append_info("[#f59e0b]Não encontrei wl-copy/xclip/xsel para copiar.[/]")
            return
        if cmd in {"/exportar", "/export"}:
            if not self._transcript:
                self._append_info("Ainda não há conversa para exportar.")
                return
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            out_path = Path(arg).expanduser() if arg else Path(self.cwd) / f"minerva-dev-{stamp}.md"
            lines = [f"# Minerva Dev — {stamp}\n", f"Pasta: `{self.cwd}`\n"]
            for who, msg in self._transcript:
                lines.append(f"\n## {who}\n\n{msg}\n")
            out_path.write_text("\n".join(lines), encoding="utf-8")
            self._append_info(f"[#10b981]✓ Conversa exportada para:[/] {out_path}")
            return
        if cmd in {"/sessoes", "/sessões", "/session"}:
            if self.session_id:
                self._append_info(
                    f"[#7dd3fc]Sessão atual:[/] {self.session_id}\n"
                    f"[#64748b]Retomar:[/] minerva --retomar {self.session_id}"
                )
            else:
                self._append_info("Nenhuma sessão iniciada ainda.")
            return
        if cmd == "/status":
            st = fetch_fcc_status(self.fcc_url)
            table = Table(border_style="#1e3a5f", box=None)
            table.add_column("Item", style="bold #7dd3fc")
            table.add_column("Estado", style="#e2e8f0")
            table.add_row("FCC Proxy", f"Online ({st.url})" if st.online else "Offline")
            table.add_row("Claude CLI", "Instalado" if st.claude_installed else "Ausente")
            table.add_row("Modelo", format_model_name(st.active_model) if st.active_model else "Não definido")
            table.add_row(
                "Provedores",
                ", ".join(format_provider_name(p) for p in st.configured_providers)
                if st.configured_providers
                else "Nenhum",
            )
            table.add_row("Pasta", self.cwd)
            if self.extra_dirs:
                table.add_row("Pastas extras", ", ".join(self.extra_dirs))
            if self.effort:
                table.add_row("Esforço", self.effort)
            self._append_info(table)
            return
        if cmd == "/provedor":
            self.action_config_provider()
            return
        if cmd == "/perfil":
            if not arg:
                lines = [
                    f"  [bold #38bdf8]{m['label']}[/] ([white]{mid}[/]) — {m['description']} "
                    f"[#64748b]({_short_model(m['model'])})[/]"
                    for mid, m in MINERVA_DEV_MODES.items()
                ]
                self._append_info(
                    "[bold #7dd3fc]Modos da Minerva Dev:[/]\n"
                    + "\n".join(lines)
                    + "\n[#64748b]Use: /perfil harmonia | /perfil sabia | /perfil impeto[/]"
                )
                return
            ok, primary, msg = apply_minerva_mode(arg, base_url=self.fcc_url)
            if ok:
                self.model = primary
                self._refresh_chrome()
                self._append_info(f"[#10b981]✓ {msg}[/]")
            else:
                self._append_info(f"[#ef4444]{msg}[/]")
            return
        if cmd in {"/modelo", "/model"}:
            if not arg:
                self.action_pick_model()
                return
            ok, msg = apply_fcc_config({"MODEL": arg}, base_url=self.fcc_url)
            if ok:
                self.model = arg
                self._refresh_chrome()
                self._append_info(f"[#10b981]✓ Modelo ativo:[/] {format_model_name(arg)}")
            else:
                self._append_info(f"[#ef4444]{msg}[/]")
            return
        if cmd == "/modo":
            if not arg:
                self.action_cycle_mode()
                return
            mapped = MODE_ALIASES_TUI.get(arg.lower())
            if not mapped:
                self._append_info("[#ef4444]Modo inválido. Use: padrao, editar, livre ou planejar.[/]")
                return
            self.permission_mode = mapped
            self._refresh_chrome()
            self._append_info(f"✦ Modo: [#7dd3fc]{PERMISSION_LABELS_PT.get(mapped, MODE_SHORT_PT.get(mapped, mapped))}[/]")
            return
        if cmd in {"/planejar", "/plan"}:
            self.permission_mode = "plan"
            self._refresh_chrome()
            if arg:
                self._submit_text(arg)
            else:
                self._append_info("✦ Modo planejamento ativado (somente leitura antes de editar).")
            return
        if cmd in {"/esforco", "/esforço", "/effort"}:
            if not arg:
                self._append_info(f"Esforço atual: {self.effort or 'padrão'} · use baixo, medio ou alto.")
                return
            mapped_eff = EFFORT_ALIASES_PT.get(arg.lower())
            if not mapped_eff:
                self._append_info("[#ef4444]Use: /esforco baixo | medio | alto[/]")
                return
            self.effort = mapped_eff
            self._append_info(f"[#10b981]✓ Esforço ajustado para:[/] {arg.lower()}")
            return
        if cmd in {"/revisar", "/review"}:
            target = f" ({arg})" if arg else ""
            self._submit_text(
                f"Revise as alterações Git locais{target} verificando bugs, regressões, segurança e qualidade de código em PT-BR."
            )
            return
        if cmd == "/cd":
            if not arg:
                self._append_info(f"Pasta atual: {self.cwd}")
                return
            new_dir = os.path.abspath(os.path.expanduser(arg))
            if not os.path.isdir(new_dir):
                self._append_info(f"[#ef4444]Pasta não encontrada:[/] {new_dir}")
                return
            self.cwd = new_dir
            os.chdir(new_dir)
            self._refresh_chrome()
            self._append_info(f"[#10b981]✓ Pasta alterada para:[/] {new_dir}")
            return
        if cmd == "/add-dir":
            if not arg:
                self._append_info(
                    f"Pastas extras: {', '.join(self.extra_dirs) if self.extra_dirs else 'nenhuma'}"
                )
                return
            extra = os.path.abspath(os.path.expanduser(arg))
            if not os.path.isdir(extra):
                self._append_info(f"[#ef4444]Pasta não encontrada:[/] {extra}")
                return
            if extra not in self.extra_dirs:
                self.extra_dirs.append(extra)
            self._append_info(f"[#10b981]✓ Diretório adicionado:[/] {extra}")
            return
        if cmd in {"/memoria", "/memory"}:
            found = []
            for fname in ("CLAUDE.md", "MINERVA.md", "AGENTS.md"):
                p = Path(self.cwd) / fname
                if p.is_file():
                    found.append(f"  [bold #38bdf8]{fname}[/] ({p.stat().st_size} bytes)")
            if found:
                self._append_info("[bold #7dd3fc]Arquivos de memória encontrados:[/]\n" + "\n".join(found))
            else:
                self._append_info("Nenhum arquivo CLAUDE.md, MINERVA.md ou AGENTS.md nesta pasta.")
            return
        if cmd in {"/contexto", "/context"}:
            total_chars = sum(len(w) + len(m) for w, m in self._transcript)
            est_tokens = max(0, total_chars // 4)
            cap = 190_000
            pct = min(100, int((est_tokens / cap) * 100))
            filled = min(20, max(1 if est_tokens else 0, pct // 5))
            bar = "[#38bdf8]" + ("█" * filled) + "[/][#1e293b]" + ("░" * (20 - filled)) + "[/]"
            self._append_info(
                f"[bold #7dd3fc]Uso estimado de contexto[/]\n"
                f"  {bar}  {pct}% (~{est_tokens:,} / {cap:,} tokens)\n"
                f"  [#64748b]Turnos na tela: {len(self._transcript)} · Use /compactar ou /nova se crescer muito.[/]"
            )
            return
        if cmd in {"/foco", "/focus"}:
            self.focus_mode = not self.focus_mode
            self.query_one("#header-bar", Static).display = not self.focus_mode
            for wc in self.query(".welcome-card"):
                wc.display = not self.focus_mode
            self._append_info(
                f"✦ Modo foco: {'ativado' if self.focus_mode else 'desativado'}."
            )
            return

        self._append_info(f"[#ef4444]Comando desconhecido:[/] {cmd} · digite /ajuda")

    def _set_mascot_state(self, state: str) -> None:
        for mascot in self.query(MinervaMascot):
            mascot.set_state(state)

    @work(thread=True)
    def _run_claude_turn(self, prompt: str) -> None:
        self._busy = True
        self.call_from_thread(self._refresh_chrome)
        self.call_from_thread(self._set_mascot_state, "thinking")
        started_at = time.monotonic()

        card = Vertical(classes="assistant-card")
        tools_box = Vertical(classes="tools-box")
        md_view = Static("", classes="assistant-body")
        status_lbl = Static(
            render_minerva_animation_frame(0, "Minerva está pensando…", 0),
            classes="status-line",
        )

        def _mount_card() -> None:
            scroll = self.query_one("#chat-scroll", VerticalScroll)
            scroll.mount(card)
            card.mount(tools_box, md_view, status_lbl)
            scroll.scroll_end(animate=False)

        self.call_from_thread(_mount_card)

        cmd = build_claude_command(
            prompt,
            session_id=self.session_id,
            continue_last=self.continue_last,
            permission_mode=self.permission_mode,
            model=self.model,
            extra_dirs=self.extra_dirs,
            effort=self.effort,
        )
        env = build_claude_env(proxy_url=self.fcc_url, auth_token=DEFAULT_FCC_TOKEN)

        proc = subprocess.Popen(
            cmd,
            cwd=self.cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._active_proc = proc

        stderr_chunks: list[str] = []

        def _drain_stderr() -> None:
            if proc.stderr is None:
                return
            for line in proc.stderr:
                stderr_chunks.append(line)

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        phase_base = "Minerva está pensando…"
        stop_ticker = threading.Event()

        def _ticker() -> None:
            step = 1
            while not stop_ticker.wait(0.18):
                elapsed = int(time.monotonic() - started_at)
                frame_text = render_minerva_animation_frame(step, phase_base, elapsed)
                step += 1
                self.call_from_thread(_update_ui, status_text=frame_text)

        accumulated = ""
        final_text = ""
        is_error = False
        duration_ms: int | None = None
        last_tool_name = ""
        last_md_flush = 0.0

        def _update_ui(
            *,
            md_text: str | None = None,
            status_text: str | None = None,
            tool_line: str | None = None,
            tool_sub: str | None = None,
            err_style: bool = False,
        ) -> None:
            if tool_line is not None:
                tools_box.add_class("has-tools")
                tools_box.mount(Static(tool_line, classes="tool-line"))
            if tool_sub is not None:
                tools_box.mount(Static(tool_sub, classes="tool-subline"))
            if md_text is not None:
                md_view.update(RichMarkdown(md_text))
            if status_text is not None:
                status_lbl.update(status_text)
                status_lbl.display = bool(status_text)
            if err_style:
                card.set_classes("assistant-card-err")
            self.query_one("#chat-scroll", VerticalScroll).scroll_end(animate=False)

        ticker_thread = threading.Thread(target=_ticker, daemon=True)
        ticker_thread.start()

        try:
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                for ev in parse_stream_event(raw_line):
                    if ev.kind == "init" and ev.session_id:
                        self.session_id = ev.session_id
                        self.continue_last = False
                    elif ev.kind == "thinking_delta":
                        phase_base = "Minerva está raciocinando…"
                    elif ev.kind == "text_delta":
                        accumulated += ev.text
                        phase_base = "Minerva está respondendo…"
                        now = time.monotonic()
                        if now - last_md_flush >= 0.10:
                            last_md_flush = now
                            self.call_from_thread(_update_ui, md_text=accumulated)
                    elif ev.kind == "tool_use":
                        if accumulated and not accumulated.endswith("\n\n"):
                            accumulated += "\n" if accumulated.endswith("\n") else "\n\n"
                        last_tool_name = ev.tool_name
                        label, _icon = translate_tool_name(ev.tool_name)
                        summary = format_tool_summary(ev.tool_name, ev.tool_input)
                        arg_txt = f"({summary})" if summary else ""
                        phase_base = f"{label}{arg_txt}…"
                        self.call_from_thread(
                            _update_ui,
                            tool_line=f"[bold #38bdf8]●[/] [bold #7dd3fc]{label}[/][#94a3b8]{arg_txt}[/]",
                        )
                    elif ev.kind == "tool_result":
                        if ev.is_error and ev.text.strip():
                            snippet = ev.text.strip().splitlines()[0][:120]
                            self.call_from_thread(
                                _update_ui,
                                tool_sub=f"⎿  [#ef4444]erro: {snippet}[/]",
                            )
                        elif ev.text.strip():
                            first_line = ev.text.strip().splitlines()[0][:100]
                            self.call_from_thread(
                                _update_ui,
                                tool_sub=f"⎿  {first_line}",
                            )
                        elif last_tool_name:
                            self.call_from_thread(
                                _update_ui,
                                tool_sub="⎿  concluído",
                            )
                        phase_base = "Analisando resultado…"
                    elif ev.kind == "result":
                        if ev.session_id:
                            self.session_id = ev.session_id
                            self.continue_last = False
                        final_text = ev.text
                        is_error = ev.is_error
                        duration_ms = ev.duration_ms

            stop_ticker.set()
            ticker_thread.join(timeout=1.0)
            stderr_thread.join(timeout=1.0)
            rc = proc.wait()
            stderr_text = "".join(stderr_chunks).strip()
            body = (accumulated or final_text).strip()

            if body:
                self._assistant_responses.append(body)
                self._transcript.append(("Minerva", body))
                dur_note = (
                    f"\n[#475569]✓ {duration_ms / 1000.0:.1f}s[/]"
                    if duration_ms is not None
                    else ""
                )
                self.call_from_thread(
                    _update_ui,
                    md_text=body,
                    status_text=dur_note,
                    err_style=is_error,
                )
            elif rc != 0 or is_error:
                err_msg = stderr_text or f"O processo encerrou com código {rc}."
                self.call_from_thread(
                    _update_ui,
                    md_text=f"**Erro:** {err_msg}",
                    status_text="",
                    err_style=True,
                )
            else:
                self.call_from_thread(_update_ui, status_text="")
        finally:
            stop_ticker.set()
            self._active_proc = None
            self._busy = False
            self.call_from_thread(self._set_mascot_state, "happy" if not is_error else "idle")
            self.call_from_thread(self._refresh_chrome)

    def action_quit_app(self) -> None:
        if self._active_proc is not None:
            self._active_proc.terminate()
        self.exit(0)

    def action_cancel_run(self) -> None:
        if self._active_proc is not None:
            self._active_proc.terminate()
            self._append_info("[#f59e0b]Execução interrompida pelo usuário.[/]")

    def action_new_session(self) -> None:
        self.session_id = None
        self.continue_last = False
        self._refresh_chrome()
        self._append_info("✦ Nova sessão iniciada.")

    def action_cycle_mode(self) -> None:
        idx = MODE_ORDER.index(self.permission_mode) if self.permission_mode in MODE_ORDER else 0
        self.permission_mode = MODE_ORDER[(idx + 1) % len(MODE_ORDER)]
        self._refresh_chrome()
        self._append_info(
            f"✦ Modo: [#7dd3fc]{PERMISSION_LABELS_PT[self.permission_mode]}[/]"
        )

    def action_clear_feed(self) -> None:
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        for child in list(scroll.children):
            child.remove()
        self._append_welcome()

    def action_config_provider(self) -> None:
        def _on_done(saved: bool | None) -> None:
            self._refresh_chrome()
            if saved:
                self._append_info("[#10b981]✓ Provedor configurado e validado no FCC![/]")

        self.push_screen(ProviderConfigModal(self.fcc_url), _on_done)

    def action_pick_model(self) -> None:
        st = fetch_fcc_status(self.fcc_url)
        current = self.model or st.active_model

        def _on_pick(selected: str | None) -> None:
            if not selected:
                return
            if selected.startswith("mode:"):
                mode_id = selected.split(":", 1)[1]
                ok, primary, msg = apply_minerva_mode(mode_id, base_url=self.fcc_url)
                if ok:
                    self.model = primary
                    self._refresh_chrome()
                    self._append_info(f"[#10b981]✓ {msg}[/]")
                else:
                    self._append_info(f"[#ef4444]{msg}[/]")
                return
            ok, msg = apply_fcc_config({"MODEL": selected}, base_url=self.fcc_url)
            if ok:
                self.model = selected
                self._refresh_chrome()
                self._append_info(f"[#10b981]✓ Modelo manual ativo:[/] {selected}")
            else:
                self._append_info(f"[#ef4444]{msg}[/]")

        self.push_screen(ModelPickerModal(self.fcc_url, current), _on_pick)


def run_tui(
    *,
    cwd: str,
    initial_prompt: str = "",
    session_id: str | None = None,
    continue_last: bool = False,
    permission_mode: str = "bypassPermissions",
    model: str | None = None,
    fcc_url: str = DEFAULT_FCC_URL,
) -> int:
    """Inicia a TUI em tela cheia da Minerva Dev."""
    app = MinervaApp(
        cwd=cwd,
        initial_prompt=initial_prompt,
        session_id=session_id,
        continue_last=continue_last,
        permission_mode=permission_mode,
        model=model,
        fcc_url=fcc_url,
    )
    result = app.run()
    return int(result or 0)
