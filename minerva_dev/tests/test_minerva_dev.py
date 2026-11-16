"""Testes unitários da Minerva Dev CLI."""

from __future__ import annotations

import json

from minerva_dev.claude_harness import build_claude_command, parse_stream_event
from minerva_dev.cli import ReplState, build_parser, handle_slash_command
from minerva_dev.fcc_bridge import build_claude_env
from minerva_dev.theme import format_tool_summary, translate_tool_name


def test_build_claude_env_overrides_anthropic_vars():
    env = build_claude_env(
        base_env={
            "PATH": "/usr/bin",
            "ANTHROPIC_API_KEY": "old-secret",
            "ANTHROPIC_MODEL": "old-model",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
        proxy_url="http://127.0.0.1:8082/",
        auth_token="fcc-proxy",
    )
    assert env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:8082"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "fcc-proxy"
    assert "ANTHROPIC_API_KEY" not in env
    assert "ANTHROPIC_MODEL" not in env
    assert "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" not in env
    assert env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] == "1"


def test_parse_stream_event_init_delta_tool_result():
    init_events = parse_stream_event(
        json.dumps({"type": "system", "subtype": "init", "session_id": "sess-123"})
    )
    assert len(init_events) == 1
    assert init_events[0].kind == "init"
    assert init_events[0].session_id == "sess-123"

    delta_events = parse_stream_event(
        json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "Olá!"},
                },
            }
        )
    )
    assert len(delta_events) == 1
    assert delta_events[0].kind == "text_delta"
    assert delta_events[0].text == "Olá!"

    tool_events = parse_stream_event(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "app.py"},
                        }
                    ]
                },
            }
        )
    )
    assert len(tool_events) == 1
    assert tool_events[0].kind == "tool_use"
    assert tool_events[0].tool_name == "Read"
    assert tool_events[0].tool_input == {"file_path": "app.py"}

    res_events = parse_stream_event(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "session_id": "sess-123",
                "result": "Pronto.",
                "duration_ms": 1450,
            }
        )
    )
    assert len(res_events) == 1
    assert res_events[0].kind == "result"
    assert res_events[0].duration_ms == 1450


def test_parse_stream_event_ignores_invalid_json():
    assert parse_stream_event("not-json") == []
    assert parse_stream_event("   ") == []


def test_ptbr_tool_translations_and_summaries():
    from minerva_dev.theme import render_minerva_animation_frame

    label, icon = translate_tool_name("Edit")
    assert label == "Editar"
    assert icon == "✏️"
    assert format_tool_summary("Bash", {"command": "pytest -q"}) == "pytest -q"
    assert format_tool_summary("Grep", {"pattern": "TODO", "path": "src"}) == "TODO em src"

    f0 = render_minerva_animation_frame(0, "Minerva está pensando…", 0)
    f3 = render_minerva_animation_frame(3, "Minerva está pensando…", 2)
    assert f0 != f3
    assert "0s" in f0 and "2s" in f3
    assert "Esc interrompe" in f3


def test_minerva_mascot_frames_and_states():
    from minerva_dev.mascot import MinervaMascot, get_mascot_frame

    idle_open = get_mascot_frame("idle", 0)
    idle_blink = get_mascot_frame("blink", 0)
    think_a = get_mascot_frame("thinking", 0)
    think_b = get_mascot_frame("thinking", 1)
    happy = get_mascot_frame("happy", 0)
    assert len(idle_open.splitlines()) == 5
    assert "#fbbf24" in idle_open and "#d97706" in idle_open  # Bico em dois tons
    assert idle_open != idle_blink
    assert think_a != think_b
    assert happy != idle_open

    mascot = MinervaMascot()
    assert mascot._active_seq == ()
    mascot.on_enter()
    assert len(mascot._active_seq) > 0
    for _ in range(10):
        mascot._tick()
    assert mascot._active_seq == ()


def test_slash_commands_ptbr():
    state = ReplState(cwd="/tmp", session_id="abc-123")
    assert handle_slash_command("/modo livre", state) == "handled"
    assert state.permission_mode == "bypassPermissions"

    assert handle_slash_command("/nova", state) == "handled"
    assert state.session_id is None

    assert handle_slash_command("/sair", state) == "exit"
    assert handle_slash_command("corrija o bug", state) == "prompt"


def test_build_claude_command_flags():
    from minerva_dev.commands import find_command_spec, match_slash_commands

    cmd = build_claude_command(
        "olá",
        session_id="s1",
        permission_mode="bypassPermissions",
        model="nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",
        extra_dirs=["/tmp"],
        effort="high",
    )
    assert "--resume" in cmd and "s1" in cmd
    assert "--dangerously-skip-permissions" in cmd
    assert "--model" in cmd
    assert "--add-dir" in cmd and "/tmp" in cmd
    assert "--effort" in cmd and "high" in cmd
    assert "--output-format" in cmd and "stream-json" in cmd

    assert len(match_slash_commands("/")) >= 20
    assert any(s.name == "/modelo" for s in match_slash_commands("/mod"))
    assert find_command_spec("/btw").name == "/paralela"
    assert find_command_spec("/plan").name == "/planejar"


def test_cli_parser_defaults():
    from minerva_dev.fcc_bridge import (
        MINERVA_DEV_MODES,
        detect_minerva_mode,
        format_model_name,
        format_provider_name,
    )

    args = build_parser().parse_args(["--continuar", "--modo", "livre", "--perfil", "sabia", "analise", "isso"])
    assert args.continuar is True
    assert args.modo == "livre"
    assert args.perfil == "sabia"
    assert args.prompt == ["analise", "isso"]

    assert set(MINERVA_DEV_MODES.keys()) == {"harmonia", "sabia", "impeto"}
    for cfg in MINERVA_DEV_MODES.values():
        assert len(cfg["fallbacks"]) == 2
    assert detect_minerva_mode(MINERVA_DEV_MODES["harmonia"]["model"]) == "harmonia"
    assert detect_minerva_mode("cohere/command-a-plus-05-2026") is None

    assert format_provider_name("nvidia_nim") == "NVIDIA"
    assert format_provider_name("open_router") == "OpenRouter"
    assert format_provider_name("gemini") == "Google Gemini"
    assert "_" not in format_provider_name("meu_provedor_custom")
    assert format_model_name("nvidia_nim/mistralai/mistral-large-4-1t-a52b") == "Mistral Large 4 1T A52B"
    assert format_model_name("gemini/models/gemini-4-hydrogen") == "Gemini 4 Hydrogen"
    assert format_model_name("open_router/cohere/north-mini-code:free") == "North Mini Code (Gratuito)"


def test_tui_interactive_layout_and_modals():
    import asyncio
    from minerva_dev.tui import MinervaApp, ModelPickerModal, ProviderConfigModal

    async def _exercise():
        app = MinervaApp(cwd="/tmp")
        assert app.permission_mode == "bypassPermissions"
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one("#header-bar") is not None
            assert app.query_one("#minerva-mascot") is not None
            assert app.query_one("#chat-scroll") is not None
            assert app.query_one("#prompt-input") is not None
            assert app.query_one("#status-footer") is not None

            # Testa abertura do menu interativo de slash commands ao digitar "/"
            from textual.widgets import OptionList

            inp = app.query_one("#prompt-input")
            menu = app.query_one("#slash-menu", OptionList)
            inp.value = "/mod"
            await pilot.pause()
            assert menu.display is True
            assert menu.option_count >= 2
            await pilot.press("escape")
            await pilot.pause()
            assert menu.display is False

            # Testa comandos adaptados do Claude Code dentro da TUI
            for cmd_str in ("/ajuda", "/contexto", "/memoria", "/esforco alto", "/foco", "/foco"):
                inp.value = cmd_str
                await pilot.press("enter")
                await pilot.pause()
            assert app.effort == "high"
            assert app.focus_mode is False

            # Testa alternância de modo via /modo livre
            inp.value = "/modo livre"
            await pilot.press("enter")
            await pilot.pause()
            assert app.permission_mode == "bypassPermissions"

            # Testa abertura e fechamento do modal de Provedor (Ctrl+P -> Esc)
            await pilot.press("ctrl+p")
            await pilot.pause()
            assert isinstance(app.screen, ProviderConfigModal)
            await pilot.press("escape")
            await pilot.pause()

            # Testa abertura e fechamento do modal de Modelo (Ctrl+M -> Esc)
            await pilot.press("ctrl+m")
            await pilot.pause()
            assert isinstance(app.screen, ModelPickerModal)
            await pilot.press("escape")
            await pilot.pause()

            # Testa que respostas longas em Markdown expandem corretamente (sem corte de altura)
            from rich.markdown import Markdown as RichMarkdown
            from textual.containers import Vertical, VerticalScroll
            from textual.widgets import Static

            scroll = app.query_one("#chat-scroll", VerticalScroll)
            long_card = Vertical(classes="assistant-card")
            long_body = Static("", classes="assistant-body")
            await scroll.mount(long_card)
            await long_card.mount(long_body)
            long_md = "\n".join(f"- Item {i}: linha longa de resposta da Minerva Dev" for i in range(1, 36))
            long_body.update(RichMarkdown(long_md))
            await pilot.pause()
            assert long_body.region.height >= 30
            assert long_card.region.height >= 30

    asyncio.run(_exercise())
