"""Preview ao vivo da tela de `cronista rec`, usando a classe SignalBar de
verdade (não uma reimplementação) — nível sintético, sem precisar falar.

    python scripts/preview_rec_screen.py

Ctrl+C encerra.
"""

from __future__ import annotations

import math
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from cronista.client.signal_bar import SignalBar

console = Console()


def main() -> int:
    t = 0.0
    bar = SignalBar(title="Reunião", started_at=datetime.now(), console=console)

    with bar:
        try:
            while True:
                bar.update("voce", (math.sin(t) + 1) / 2)
                bar.update("outros", (math.sin(t + 1.3) + 1) / 2)
                t += 0.15
                time.sleep(0.075)
        except KeyboardInterrupt:
            pass

    console.print("\n[dim]Encerrado.[/dim]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
