"""Banner de abertura "cronista" (docs/17-identidade-visual-cli.md §7).

Gradiente adaptado da técnica real do projeto torlink (baairon/torlink,
`src/ui/components/Logo.tsx` + `src/ui/theme.ts`): não é degradê por
letra, é por CARACTERE, numa grade 2D (linha e coluna combinadas),
passando por paradas de cor — aqui em tons dourados (cor de identidade
do Cronista) em vez da paleta roxa original.
"""

from __future__ import annotations

import pyfiglet
from rich.console import Console
from rich.text import Text

from cronista.client.colors import lerp_color
from cronista.client.signal_bar import VOCE_COLOR

_WORD = "CRONISTA"
_FONT = "ansi_shadow"

_HIGHLIGHT = "#FFFFFF"
_TOP = "#F7ECDA"
_ACCENT = VOCE_COLOR  # #DFB878
_BASE = "#C9A968"
_SHADE = "#B8934F"  # ponto mais escuro do degradê -- ainda dourado, nunca marrom apagado


def _sheen(t: float) -> str:
    """Mesmos 4 patamares do `getSheen` do torlink, com a paleta trocada."""
    if t < 0.15:
        return lerp_color(_HIGHLIGHT, _TOP, t / 0.15)
    if t < 0.4:
        return lerp_color(_TOP, _ACCENT, (t - 0.15) / 0.25)
    if t < 0.7:
        return lerp_color(_ACCENT, _BASE, (t - 0.4) / 0.3)
    return lerp_color(_BASE, _SHADE, (t - 0.7) / 0.3)


def _rows() -> list[str]:
    return [r for r in pyfiglet.figlet_format(_WORD, font=_FONT).splitlines() if r.strip()]


def width() -> int:
    return max((len(r) for r in _rows()), default=0)


def _big() -> Text:
    rows = _rows()
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)

    text = Text()
    for row_idx, row in enumerate(rows):
        t_y = row_idx / max(1, n_rows - 1)
        for col_idx, ch in enumerate(row):
            if ch == " ":
                text.append(" ")
                continue
            t_x = col_idx / max(1, n_cols - 1)
            text.append(ch, style=f"bold {_sheen((t_x + t_y) / 2)}")
        text.append("\n")
    return text


def render(console: Console) -> Text:
    """Banner grande se couber na largura do terminal; senão, cai pro
    nome simples colorido -- mesmo padrão do torlink (`Splash.tsx`,
    `showLogo = cols >= LOGO_WIDTH + 2`). Sem cor nenhuma se a saída não
    for um terminal interativo (docs/17 §5)."""
    if not console.is_terminal:
        return Text(_WORD.lower())
    if console.width >= width() + 2:
        return _big()
    return Text(_WORD.lower(), style=f"bold {VOCE_COLOR}")
