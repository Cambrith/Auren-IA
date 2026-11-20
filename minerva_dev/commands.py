"""Registro centralizado de comandos slash da Minerva Dev (adaptados do Claude Code CLI)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlashCommandSpec:
    name: str
    args: str
    category: str
    description: str
    aliases: tuple[str, ...] = ()


MINERVA_COMMANDS: tuple[SlashCommandSpec, ...] = (
    # Sessão e Conversa
    SlashCommandSpec("/ajuda", "", "Geral", "Exibe todos os comandos e atalhos disponíveis", ("/help",)),
    SlashCommandSpec("/nova", "", "Sessão", "Inicia uma sessão limpa (a anterior continua salva)", ("/clear", "/new")),
    SlashCommandSpec("/retomar", "[id]", "Sessão", "Lista sessões recentes neste diretório ou retoma pelo ID", ("/resume",)),
    SlashCommandSpec("/sessoes", "", "Sessão", "Mostra o ID da sessão atual e comando para retomada", ("/sessões", "/session")),
    SlashCommandSpec("/bifurcar", "", "Sessão", "Cria uma ramificação da conversa atual", ("/branch", "/fork")),
    SlashCommandSpec("/compactar", "", "Sessão", "Resume a conversa para liberar espaço de contexto", ("/compact",)),
    SlashCommandSpec("/paralela", "<pergunta>", "Sessão", "Pergunta rápida paralela sem alterar o contexto principal", ("/btw",)),
    SlashCommandSpec("/copiar", "[n]", "Sessão", "Copia a última (ou N-ésima) resposta para a área de transferência", ("/copy",)),
    SlashCommandSpec("/exportar", "[arquivo]", "Sessão", "Exporta a conversa atual para um arquivo Markdown", ("/export",)),
    # Modelo e Execução
    SlashCommandSpec("/perfil", "[harmonia|sabia|impeto]", "Modelo", "Alterna entre os 3 modos da Minerva (Harmonia, Sábia, Ímpeto)"),
    SlashCommandSpec("/modelo", "[id]", "Modelo", "Abre o seletor visual de modos e modelos ou define manualmente", ("/model",)),
    SlashCommandSpec("/provedor", "", "Modelo", "Configura chaves de API no Free Claude Code"),
    SlashCommandSpec("/modo", "[padrao|editar|livre]", "Execução", "Alterna a política de permissão das ferramentas"),
    SlashCommandSpec("/planejar", "[tarefa]", "Execução", "Entra em modo planejamento (somente leitura) ou planeja uma tarefa", ("/plan",)),
    SlashCommandSpec("/esforco", "[baixo|medio|alto]", "Execução", "Ajusta o nível de profundidade do raciocínio", ("/esforço", "/effort")),
    SlashCommandSpec("/revisar", "[alvo]", "Execução", "Revisa alterações Git locais apontando bugs e riscos", ("/review",)),
    # Ambiente e Visualização
    SlashCommandSpec("/cd", "<pasta>", "Ambiente", "Altera o diretório de trabalho da sessão atual"),
    SlashCommandSpec("/add-dir", "<pasta>", "Ambiente", "Adiciona um diretório extra acessível ao agente"),
    SlashCommandSpec("/memoria", "", "Ambiente", "Inspeciona instruções de projeto (CLAUDE.md / MINERVA.md)", ("/memory",)),
    SlashCommandSpec("/contexto", "", "Ambiente", "Visualiza o uso estimado de contexto da sessão", ("/context",)),
    SlashCommandSpec("/status", "", "Ambiente", "Exibe diagnóstico do FCC, provedores, modelo e pastas"),
    SlashCommandSpec("/foco", "", "Visual", "Alterna modo foco (oculta cartão inicial e detalhes)", ("/focus",)),
    SlashCommandSpec("/limpar", "", "Visual", "Limpa a tela mantendo a sessão ativa"),
    SlashCommandSpec("/sair", "", "Geral", "Encerra a Minerva Dev", ("/exit", "/quit")),
)


def match_slash_commands(prefix: str) -> list[SlashCommandSpec]:
    """Filtra comandos slash por prefixo ou substring (em nome ou aliases)."""
    q = prefix.strip().lower()
    if not q.startswith("/"):
        return []
    if q == "/":
        return list(MINERVA_COMMANDS)

    starts: list[SlashCommandSpec] = []
    contains: list[SlashCommandSpec] = []
    for spec in MINERVA_COMMANDS:
        candidates = (spec.name, *spec.aliases)
        if any(c.startswith(q) for c in candidates):
            starts.append(spec)
        elif q[1:] in spec.name or q[1:] in spec.description.lower():
            contains.append(spec)
    return starts + contains


def find_command_spec(cmd: str) -> SlashCommandSpec | None:
    """Encontra a especificação exata de um comando ou alias."""
    low = cmd.strip().lower()
    for spec in MINERVA_COMMANDS:
        if low == spec.name or low in spec.aliases:
            return spec
    return None
