"""Identidade visual, arte ASCII da Minerva e componentes Rich em PT-BR."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

MINERVA_THEME = Theme(
    {
        "minerva.primary": "bold #38bdf8",
        "minerva.secondary": "#0284c7",
        "minerva.accent": "bold #7dd3fc",
        "minerva.muted": "#94a3b8",
        "minerva.ok": "bold #10b981",
        "minerva.warn": "bold #f59e0b",
        "minerva.err": "bold #ef4444",
        "minerva.tool": "bold #60a5fa",
        "minerva.code": "#e2e8f0",
    }
)

console = Console(theme=MINERVA_THEME, highlight=False)

# Nó triskelion estilizado inspirado no símbolo da Minerva
MINERVA_ART_LINES = [
    "    [rgb(30,201,246)]▄[/][rgb(45,197,238) on rgb(9,153,255)]▀[/][rgb(27,184,252) on rgb(0,116,255)]▀[/][rgb(17,186,250) on rgb(0,118,255)]▀[/][rgb(37,211,250) on rgb(0,128,255)]▀[/][rgb(113,247,251) on rgb(24,178,255)]▀[/][rgb(176,244,244) on rgb(153,252,253)]▀[/][rgb(175,243,245)]▄[/]    ",
    "   [rgb(83,198,247)]▄[/][rgb(0,119,252) on rgb(109,180,255)]▀[/][rgb(0,46,233) on rgb(133,189,238)]▀[/][rgb(0,33,206) on rgb(120,206,242)]▀[/][rgb(0,56,218) on rgb(116,255,249)]▀[/][rgb(6,137,248) on rgb(50,217,244)]▀[/][rgb(0,135,250) on rgb(16,184,250)]▀[/][rgb(94,217,252) on rgb(69,207,251)]▀[/][rgb(125,255,255) on rgb(68,242,255)]▀[/][rgb(92,231,246)]▄[/]   ",
    " [rgb(39,222,249)]▄[/][rgb(121,251,249) on rgb(30,217,255)]▀[/][rgb(133,244,253) on rgb(0,158,246)]▀[/][rgb(133,239,250) on rgb(0,144,248)]▀[/][rgb(127,235,255) on rgb(2,156,252)]▀[/][rgb(104,239,255) on rgb(21,139,251)]▀[/][rgb(52,233,255) on rgb(31,175,250)]▀[/][rgb(8,167,255) on rgb(1,121,249)]▀[/][rgb(17,149,249) on rgb(15,85,249)]▀[/][rgb(82,228,251) on rgb(80,216,247)]▀[/][rgb(45,212,253) on rgb(28,191,252)]▀[/][rgb(60,216,251) on rgb(36,172,239)]▀[/][rgb(5,97,244)]▄[/][rgb(5,141,252)]▄[/] ",
    "[rgb(15,209,247) on rgb(4,172,248)]▀[/][rgb(2,179,255) on rgb(0,110,245)]▀[/][rgb(0,116,240) on rgb(2,122,251)]▀[/][rgb(1,128,250) on rgb(26,183,250)]▀[/][rgb(38,175,255) on rgb(19,103,248)]▀[/][rgb(31,147,248) on rgb(0,82,252)]▀[/][rgb(7,174,249)]▄[/] [rgb(3,109,247)]▀[/][rgb(37,133,249) on rgb(19,162,251)]▀[/][rgb(37,183,250) on rgb(1,119,252)]▀[/][rgb(5,158,255) on rgb(1,130,255)]▀[/][rgb(14,129,221) on rgb(6,120,216)]▀[/][rgb(0,31,189) on rgb(1,26,180)]▀[/][rgb(3,118,255) on rgb(0,105,250)]▀[/][rgb(18,177,245) on rgb(22,186,252)]▀[/]",
    "[rgb(4,146,246) on rgb(3,155,248)]▀[/][rgb(0,97,247) on rgb(1,131,255)]▀[/][rgb(15,163,252) on rgb(13,143,250)]▀[/] [rgb(0,129,248) on rgb(26,249,255)]▀[/][rgb(0,132,255) on rgb(6,178,255)]▀[/][rgb(26,208,255) on rgb(22,171,248)]▀[/][rgb(92,246,247) on rgb(84,243,255)]▀[/][rgb(9,85,246) on rgb(78,201,255)]▀[/][rgb(0,70,254) on rgb(34,118,245)]▀[/][rgb(0,74,255) on rgb(22,108,251)]▀[/][rgb(0,109,249)]▀[/] [rgb(0,57,240) on rgb(75,202,251)]▀[/][rgb(10,149,254) on rgb(67,228,255)]▀[/][rgb(49,215,250) on rgb(104,236,249)]▀[/]",
    "[rgb(8,189,248)]▀[/][rgb(3,181,255) on rgb(12,213,249)]▀[/][rgb(5,101,252) on rgb(4,154,255)]▀[/][rgb(0,54,240) on rgb(0,56,255)]▀[/][rgb(11,62,210) on rgb(0,39,222)]▀[/][rgb(41,187,244) on rgb(26,72,197)]▀[/][rgb(15,173,253) on rgb(53,195,251)]▀[/][rgb(27,172,247) on rgb(2,149,255)]▀[/][rgb(60,213,250) on rgb(9,133,247)]▀[/][rgb(35,192,251) on rgb(13,140,248)]▀[/][rgb(32,190,248) on rgb(0,122,250)]▀[/][rgb(57,206,249) on rgb(0,141,254)]▀[/][rgb(79,219,250) on rgb(0,161,251)]▀[/][rgb(75,229,250) on rgb(0,205,255)]▀[/][rgb(75,254,255) on rgb(22,225,251)]▀[/][rgb(92,241,248)]▀[/]",
    "  [rgb(17,210,249)]▀[/][rgb(5,135,253)]▀[/][rgb(2,91,252) on rgb(6,173,251)]▀[/][rgb(0,62,239) on rgb(6,153,255)]▀[/][rgb(28,113,238)]▀[/][rgb(37,197,252)]▀[/][rgb(1,133,255) on rgb(21,203,249)]▀[/][rgb(0,88,251) on rgb(4,142,251)]▀[/][rgb(2,75,245) on rgb(1,98,249)]▀[/][rgb(2,87,255) on rgb(0,87,251)]▀[/][rgb(3,120,255) on rgb(0,84,249)]▀[/][rgb(11,162,249)]▀[/]  ",
]

PERMISSION_LABELS_PT = {
    "default": "Padrão (confirma ações)",
    "acceptEdits": "Auto-edição (edita sem perguntar)",
    "bypassPermissions": "Sem pausas (execução direta)",
}

TOOL_LABELS_PT: dict[str, tuple[str, str]] = {
    "Read": ("Ler", "📖"),
    "Edit": ("Editar", "✏️"),
    "MultiEdit": ("Editar", "✏️"),
    "Write": ("Escrever", "📝"),
    "Bash": ("Executar", "⚡"),
    "Glob": ("Buscar", "🔍"),
    "Grep": ("Pesquisar", "🔎"),
    "WebFetch": ("Acessar", "🌐"),
    "WebSearch": ("PesquisarWeb", "🌐"),
    "Agent": ("Subagente", "🤖"),
    "Task": ("Subagente", "🤖"),
    "TodoWrite": ("Tarefas", "📋"),
    "NotebookEdit": ("Notebook", "📓"),
}


def translate_tool_name(tool_name: str) -> tuple[str, str]:
    """Retorna (rótulo_em_pt_br, ícone) para uma ferramenta do Claude Code."""
    return TOOL_LABELS_PT.get(tool_name, (f"Ferramenta: {tool_name}", "🔧"))


def format_tool_summary(tool_name: str, tool_input: dict | None) -> str:
    """Extrai um resumo legível em PT-BR dos argumentos da ferramenta."""
    if not isinstance(tool_input, dict):
        return ""
    if tool_name in {"Read", "Edit", "MultiEdit", "Write", "NotebookEdit"}:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        return str(path)
    if tool_name == "Bash":
        cmd = str(tool_input.get("command") or "").strip().replace("\n", " ")
        return cmd[:120] + ("…" if len(cmd) > 120 else "")
    if tool_name in {"Glob", "Grep"}:
        pattern = tool_input.get("pattern") or ""
        path = tool_input.get("path") or ""
        return f"{pattern}" + (f" em {path}" if path else "")
    if tool_name in {"WebFetch", "WebSearch"}:
        return str(tool_input.get("url") or tool_input.get("query") or "")
    if tool_name in {"Agent", "Task"}:
        return str(tool_input.get("description") or tool_input.get("prompt") or "")[:100]
    return ""


def render_banner(
    *,
    cwd: str,
    model: str,
    fcc_online: bool,
    providers_configured: list[str],
    permission_mode: str,
) -> None:
    """Exibe o cabeçalho estilizado da Minerva Dev no terminal."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="center", vertical="middle")
    grid.add_column(vertical="middle")

    art = "\n".join(MINERVA_ART_LINES)

    status_fcc = (
        "[minerva.ok]● Online[/] (127.0.0.1:8082)"
        if fcc_online
        else "[minerva.warn]● Offline[/]"
    )
    prov_text = (
        ", ".join(providers_configured)
        if providers_configured
        else "[minerva.warn]Nenhum provedor com chave configurada[/]"
    )
    perm_label = PERMISSION_LABELS_PT.get(permission_mode, permission_mode)

    info = (
        "[minerva.primary]MINERVA DEV[/] [minerva.muted]· Assistente de Engenharia no Terminal[/]\n"
        f"[minerva.muted]Diretório:[/] [white]{cwd}[/]\n"
        f"[minerva.muted]Motor FCC:[/] {status_fcc}\n"
        f"[minerva.muted]Modelo ativo:[/] [minerva.accent]{model or 'não definido'}[/]\n"
        f"[minerva.muted]Provedores:[/] {prov_text}\n"
        f"[minerva.muted]Modo de permissão:[/] {perm_label}\n"
        "[minerva.muted]Comandos:[/] [minerva.accent]/ajuda[/] · [minerva.accent]/modelo[/] · "
        "[minerva.accent]/provedor[/] · [minerva.accent]/modo[/] · [minerva.accent]/sair[/]"
    )
    grid.add_row(art, info)
    console.print(
        Panel(
            grid,
            border_style="#0284c7",
            padding=(0, 1),
        )
    )


def print_help_pt() -> None:
    """Exibe a tabela de comandos em PT-BR."""
    table = Table(
        title="Comandos da Minerva Dev",
        border_style="#0284c7",
        header_style="bold #7dd3fc",
    )
    table.add_column("Comando", style="bold #38bdf8")
    table.add_column("Descrição", style="white")
    rows = [
        ("/ajuda", "Exibe esta lista de comandos"),
        ("/modelo [id]", "Lista os modelos disponíveis no FCC ou troca o modelo ativo"),
        ("/provedor", "Mostra provedores e configura uma chave gratuita (NVIDIA NIM, Gemini, Groq, etc.)"),
        ("/modo [padrao|editar|livre]", "Alterna a política de permissão para edição e comandos"),
        ("/nova", "Inicia uma nova conversa limpa (zera o contexto da sessão)"),
        ("/sessoes", "Mostra o ID da sessão atual para retomada com --continuar"),
        ("/status", "Verifica o servidor FCC, provedores e versão do Claude Code"),
        ("/limpar", "Limpa a tela do terminal mantendo a conversa"),
        ("/sair", "Encerra a Minerva Dev"),
    ]
    for cmd, desc in rows:
        table.add_row(cmd, desc)
    console.print(table)


def print_error(msg: str) -> None:
    """Exibe erro formatado no padrão Minerva."""
    console.print(Text(f"✖ {msg}", style="minerva.err"))


def print_info(msg: str) -> None:
    """Exibe informação formatada no padrão Minerva."""
    console.print(Text(f"✦ {msg}", style="minerva.accent"))


_MINERVA_ORBIT_FRAMES = (
    "[bold #bae6fd]●[/][#38bdf8]•[/][#0284c7]·[/]",
    "[#38bdf8]•[/][bold #bae6fd]●[/][#38bdf8]•[/]",
    "[#0284c7]·[/][#38bdf8]•[/][bold #bae6fd]●[/]",
    "[#38bdf8]•[/][bold #7dd3fc]●[/][#38bdf8]•[/]",
)


def render_minerva_animation_frame(step: int, label: str, elapsed_seconds: int) -> str:
    """Gera um frame com animação única da Minerva (pulso orbital de 3 pontos)."""
    pulse = _MINERVA_ORBIT_FRAMES[step % len(_MINERVA_ORBIT_FRAMES)]
    return f"{pulse}  [#7dd3fc]{label}[/]  [#64748b]({elapsed_seconds}s · Esc interrompe)[/]"
