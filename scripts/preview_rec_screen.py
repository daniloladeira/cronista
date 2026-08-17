"""Mockup da tela completa de 'cronista rec': regua com o nome do app no
topo, cabecalho compacto (titulo + traco fino embutido) logo abaixo,
rodape. Sem bloco de barra grande no conteudo -- o indicador de sinal
vive só no cabecalho. Nivel sintetico, sem precisar falar. Descartavel,
so para decidir o layout antes da etapa 5.

Recuo aplicado uma vez só, via rich.padding.Padding em volta do grupo
inteiro -- nao mais espalhado como prefixo manual em cada Text, que foi
o que desalinhou titulo/rodape/regua um do outro nas correcoes anteriores.

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
from rich.padding import Padding
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from cronista.client.signal_bar import OUTROS_COLOR, VOCE_COLOR, SignalBar

console = Console()

_MARGIN = (0, 2)  # (vertical, horizontal) -- unico lugar que define o recuo


def render_top_rule() -> Rule:
    return Rule(Text("cronista", style=f"bold {VOCE_COLOR}"), style=VOCE_COLOR, align="left")


def render_header(bar: SignalBar, start_dt: datetime) -> Table:
    title = Text()
    title.append("Reunião ", style=f"bold {VOCE_COLOR}")
    title.append("@hoje ", style="dim")
    title.append(start_dt.strftime("%H:%M"), style="dim")

    right = Text()
    right.append("voce ", style=VOCE_COLOR)
    right.append(bar.render_header_trace("voce"))
    right.append("  outros ", style=OUTROS_COLOR)
    right.append(bar.render_header_trace("outros"))

    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row(title, right)
    return grid


def render_footer(elapsed_s: int) -> Text:
    text = Text()
    text.append("duração  ", style=OUTROS_COLOR)
    text.append(f"{elapsed_s // 60:02d}:{elapsed_s % 60:02d}")
    text.append("\n\nCtrl+C para encerrar", style="dim")
    return text


def main() -> int:
    t = 0.0
    start = time.time()
    start_dt = datetime.now()
    bar = SignalBar(console=console)

    with Live(console=console, refresh_per_second=13, screen=True) as live:
        try:
            while True:
                bar.update("voce", (math.sin(t) + 1) / 2)
                bar.update("outros", (math.sin(t + 1.3) + 1) / 2)

                elapsed = int(time.time() - start)
                content = Group(
                    render_top_rule(),
                    Text(""),
                    render_header(bar, start_dt),
                    Text(""),
                    render_footer(elapsed),
                )
                live.update(Padding(content, _MARGIN))

                t += 0.15
                time.sleep(0.075)
        except KeyboardInterrupt:
            console.print("\n[dim]Encerrado.[/dim]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
