"""Preview: titulo a esquerda, indicador de sinal pequeno e embutido a
direita, tudo numa linha so -- layout pedido pelo usuario:

    Reuniao @hoje 11:02                      voce ▃▅▇ outros ▂▄▆

Nivel sintetico, sem precisar falar. Descartavel.

    python scripts/preview_inline_header.py

Ctrl+C para sair.
"""

from __future__ import annotations

import math
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from cronista.client.signal_bar import OUTROS_COLOR, VOCE_COLOR

console = Console()

_BLOCKS = "▁▂▃▄▅▆▇█"
_INLINE_WIDTH = 8  # bem menor que a barra normal (24), pra caber na linha
_SENSITIVITY = 0.3
_MIN_TONE = 0.35


def _tone(base_hex: str, intensity: float) -> str:
    r = int(base_hex[1:3], 16)
    g = int(base_hex[3:5], 16)
    b = int(base_hex[5:7], 16)
    frac = _MIN_TONE + (1 - _MIN_TONE) * max(0.0, min(intensity, 1.0))
    return f"#{int(r * frac):02x}{int(g * frac):02x}{int(b * frac):02x}"


def _inline_trace(history: deque[float], color: str) -> Text:
    text = Text()
    for level in history:
        clamped = max(0.0, min(level, 1.0)) ** _SENSITIVITY
        idx = min(int(clamped * len(_BLOCKS)), len(_BLOCKS) - 1)
        text.append(_BLOCKS[idx], style=_tone(color, clamped))
    return text


def render(voce_hist: deque[float], outros_hist: deque[float]) -> Table:
    title = Text()
    title.append("Reunião ", style=f"bold {VOCE_COLOR}")
    title.append("@hoje ", style="dim")
    title.append(datetime.now().strftime("%H:%M"), style="dim")

    right = Text()
    right.append("voce ", style=VOCE_COLOR)
    right.append(_inline_trace(voce_hist, VOCE_COLOR))
    right.append("  outros ", style=OUTROS_COLOR)
    right.append(_inline_trace(outros_hist, OUTROS_COLOR))

    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row(title, right)
    return grid


def main() -> int:
    voce_hist: deque[float] = deque([0.0] * _INLINE_WIDTH, maxlen=_INLINE_WIDTH)
    outros_hist: deque[float] = deque([0.0] * _INLINE_WIDTH, maxlen=_INLINE_WIDTH)

    t = 0.0
    with Live(console=console, refresh_per_second=13) as live:
        try:
            while True:
                voce_hist.append((math.sin(t) + 1) / 2)
                outros_hist.append((math.sin(t + 1.3) + 1) / 2)
                live.update(render(voce_hist, outros_hist))
                t += 0.15
                time.sleep(0.075)
        except KeyboardInterrupt:
            console.print("\n[dim]Encerrado.[/dim]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
