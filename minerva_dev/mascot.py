"""Mascote sóbrio da Minerva Dev no terminal: Coruja em blocos geométricos com estilo próprio."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static

_C_OWL = "#38bdf8"
_C_OWL_SOFT = "#0284c7"
_C_BROW = "#7dd3fc"
_C_EYE_GLINT = "#e0f2fe"
_C_BEAK_TOP = "#fbbf24"
_C_BEAK_TIP = "#d97706"

_COLOR_MAP = {
    "M": _C_OWL,
    "S": _C_OWL_SOFT,
    "L": _C_BROW,
    "G": _C_EYE_GLINT,
    "B": _C_BEAK_TOP,
    "T": _C_BEAK_TIP,
}

# Grade 13x10 -> 13 colunas x 5 linhas em half-blocks Unicode:
# Silhueta ovalada com penachos em V, asas curvas e garras empoleiradas (distinta do Clawd)
_POSES: dict[str, tuple[str, ...]] = {
    "default": (
        ".LL.......LL.",
        "..MMM...MMM..",
        ".MMMMMMMMMMM.",
        ".MM..MMM..MM.",
        "SMM..MBM..MMS",
        "SMMMMMTMMMMMS",
        ".SSMMMMMMMSS.",
        "..SSMMMMMSS..",
        "....MM.MM....",
        "...MM...MM...",
    ),
    "blink": (
        ".LL.......LL.",
        "..MMM...MMM..",
        ".MMMMMMMMMMM.",
        ".MMMMMMMMMMM.",
        "SMM..MBM..MMS",
        "SMMMMMTMMMMMS",
        ".SSMMMMMMMSS.",
        "..SSMMMMMSS..",
        "....MM.MM....",
        "...MM...MM...",
    ),
    "closed": (
        ".LL.......LL.",
        "..MMM...MMM..",
        ".MMMMMMMMMMM.",
        ".MMMMMMMMMMM.",
        "SMMMMMBMMMMMS",
        "SMMMMMTMMMMMS",
        ".SSMMMMMMMSS.",
        "..SSMMMMMSS..",
        "....MM.MM....",
        "...MM...MM...",
    ),
    "wink": (
        ".LL.......LL.",
        "..MMM...MMM..",
        ".MMMMMMMMMMM.",
        ".MM..MMMMMMM.",
        "SMM..MBMMMMMS",
        "SMMMMMTMMMMMS",
        ".SSMMMMMMMSS.",
        "..SSMMMMMSS..",
        "....MM.MM....",
        "...MM...MM...",
    ),
    "look_left": (
        ".LL.......LL.",
        "..MMM...MMM..",
        ".MMMMMMMMMMM.",
        ".MMG.MMMG.MM.",
        "SMM..MBM..MMS",
        "SMMMMMTMMMMMS",
        ".SSMMMMMMMSS.",
        "..SSMMMMMSS..",
        "....MM.MM....",
        "...MM...MM...",
    ),
    "look_right": (
        ".LL.......LL.",
        "..MMM...MMM..",
        ".MMMMMMMMMMM.",
        ".MM.GMMMG.MM.",
        "SMM..MBM..MMS",
        "SMMMMMTMMMMMS",
        ".SSMMMMMMMSS.",
        "..SSMMMMMSS..",
        "....MM.MM....",
        "...MM...MM...",
    ),
    "wings_up": (
        "LL.........LL",
        ".MMMM...MMMM.",
        "LMMMMMMMMMMML",
        "SMM..MMM..MMS",
        ".MM..MBM..MM.",
        ".SMMMMTMMMMS.",
        "..SSMMMMMSS..",
        "...MMMMMMM...",
        "....MM.MM....",
        "...MM...MM...",
    ),
    "crouch": (
        ".............",
        ".LL.......LL.",
        "..MMM...MMM..",
        ".MMMMMMMMMMM.",
        ".MM..MMM..MM.",
        "SMM..MBM..MMS",
        "SMMMMMTMMMMMS",
        ".SSMMMMMMMSS.",
        "...MM...MM...",
        ".............",
    ),
}

_SEQUENCES: dict[str, tuple[str, ...]] = {
    "wink": ("default", "wink", "wink", "wink", "default"),
    "boop": ("crouch", "closed", "closed", "blink", "default"),
    "look": ("look_left", "look_left", "default", "look_right", "look_right", "default"),
    "hop": ("crouch", "wings_up", "wings_up", "default"),
}

_INTERACT_ORDER = ("wink", "look", "boop", "hop")


def render_pixel_grid(grid: tuple[str, ...]) -> str:
    """Converte uma grade de pixels (altura par) em half-blocks Unicode estilizados."""
    lines: list[str] = []
    for y in range(0, len(grid), 2):
        top_row = grid[y]
        bot_row = grid[y + 1] if y + 1 < len(grid) else "." * len(top_row)
        chars: list[str] = []
        for top_px, bot_px in zip(top_row, bot_row):
            tc = _COLOR_MAP.get(top_px)
            bc = _COLOR_MAP.get(bot_px)
            if tc and bc:
                if tc == bc:
                    chars.append(f"[{tc}]█[/]")
                else:
                    chars.append(f"[{tc} on {bc}]▀[/]")
            elif tc:
                chars.append(f"[{tc}]▀[/]")
            elif bc:
                chars.append(f"[{bc}]▄[/]")
            else:
                chars.append(" ")
        lines.append("".join(chars))
    return "\n".join(lines)


def get_mascot_frame(state: str, step: int) -> str:
    """Retorna o frame da coruja da Minerva para o estado e passo atuais."""
    if state in _POSES:
        return render_pixel_grid(_POSES[state])
    if state == "happy":
        return render_pixel_grid(_POSES["wink"] if step % 2 == 0 else _POSES["default"])
    if state == "thinking":
        return render_pixel_grid(_POSES["wings_up"] if step % 2 == 1 else _POSES["default"])
    return render_pixel_grid(_POSES["default"])


class MinervaMascot(Static):
    """Mascote estático por padrão que anima ao passar o cursor, clicar ou responder."""

    DEFAULT_CSS = """
    MinervaMascot {
        width: 13;
        height: 5;
        content-align: center middle;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(get_mascot_frame("default", 0), **kwargs)
        self._state = "idle"
        self._active_seq: tuple[str, ...] = ()
        self._seq_idx = 0
        self._interact_idx = 0
        self._think_step = 0
        self._idle_ticks = 0

    def on_mount(self) -> None:
        self.set_interval(0.12, self._tick)

    def play_sequence(self, name: str) -> None:
        """Executa uma sequência curta de animação e retorna ao repouso."""
        seq = _SEQUENCES.get(name)
        if not seq:
            return
        self._active_seq = seq
        self._seq_idx = 0
        self.update(render_pixel_grid(_POSES[seq[0]]))

    def on_enter(self, _event: Any = None) -> None:
        """Ao passar o cursor em cima da coruja, executa uma reação curta."""
        if not self._active_seq and self._state == "idle":
            name = _INTERACT_ORDER[self._interact_idx % len(_INTERACT_ORDER)]
            self._interact_idx += 1
            self.play_sequence(name)

    def on_click(self, _event: Any = None) -> None:
        """Ao clicar na coruja, executa uma reação curta."""
        if self._state == "idle":
            self.play_sequence("boop")

    def set_state(self, state: str) -> None:
        """Alterna o estado da mascote ('idle', 'thinking' ou 'happy')."""
        self._state = state
        self._think_step = 0
        if state == "happy":
            self._state = "idle"
            self.play_sequence("wink")
            return
        if state == "idle":
            self._active_seq = ()
            self.update(get_mascot_frame("default", 0))
            return
        if state == "thinking":
            self._active_seq = ()
            self.update(get_mascot_frame("thinking", 0))

    def _tick(self) -> None:
        if self._active_seq:
            self._seq_idx += 1
            if self._seq_idx >= len(self._active_seq):
                self._active_seq = ()
                self.update(get_mascot_frame(self._state, 0))
                return
            pose = self._active_seq[self._seq_idx]
            self.update(render_pixel_grid(_POSES[pose]))
            return

        if self._state == "thinking":
            self._idle_ticks += 1
            if self._idle_ticks % 6 == 0:
                self._think_step += 1
                self.update(get_mascot_frame("thinking", self._think_step))
            return

        self._idle_ticks += 1
        if self._idle_ticks == 48:
            self.update(render_pixel_grid(_POSES["blink"]))
        elif self._idle_ticks >= 50:
            self._idle_ticks = 0
            self.update(render_pixel_grid(_POSES["default"]))
