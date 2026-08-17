"""Mockup da tela completa de 'cronista rec' -- cabecalho, medidor de sinal,
rodape -- nao so o medidor isolado. Nivel sintetico, sem precisar falar.
Descartavel, so para decidir o layout antes de etapa 5.

    python scripts/preview_rec_screen.py

Ctrl+C para sair.
"""

from __future__ import annotations

import math
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console, Group
from rich.live import Live
from rich.rule import Rule
from rich.text import Text

from cronista.client.signal_bar import OUTROS_COLOR, VOCE_COLOR, SignalBar

console = Console()


def render_header_footer(elapsed_s: int) -> tuple[Rule, Text, Text]:
    header = Rule(Text("cronista rec", style=VOCE_COLOR), style=VOCE_COLOR)
    info = Text()
    info.append("  reuniao  ", style=OUTROS_COLOR)
    info.append(datetime.now().strftime("%Y-%m-%d_%H%M") + "\n")
    info.append("  duracao  ", style=OUTROS_COLOR)
    info.append(f"{elapsed_s // 60:02d}:{elapsed_s % 60:02d}")
    footer = Text("\n  Ctrl+C para encerrar", style="dim")
    return header, info, footer


def main() -> int:
    t = 0.0
    start = time.time()
    bar = SignalBar(console=console)

    with Live(console=console, refresh_per_second=13) as live:
        try:
            while True:
                level_voce = (math.sin(t) + 1) / 2
                level_outros = (math.sin(t + 1.3) + 1) / 2
                bar.update("voce", level_voce)
                bar.update("outros", level_outros)

                elapsed = int(time.time() - start)
                header, info, footer = render_header_footer(elapsed)
                live.update(Group(header, Text(""), info, Text(""), bar._render(), footer))

                t += 0.15
                time.sleep(0.075)
        except KeyboardInterrupt:
            console.print("\n[dim]Encerrado.[/dim]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
