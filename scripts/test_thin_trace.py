"""Verificacao manual da versao 'fina' do traco -- uma linha so por trilha,
um glifo por amostra (▁▂▃▄▅▆▇█), tom variando por coluna conforme o nivel
daquele instante. Versao anterior a barra de 4 linhas com gradiente fixo
por posicao que existe hoje em cronista/client/signal_bar.py -- recriada
aqui a parte, para comparar as duas com audio real antes de decidir qual
fica no signal_bar.py.

    python scripts/test_thin_trace.py

Grava 8 segundos. Fale e deixe algo tocando.
"""

from __future__ import annotations

import sys
import tempfile
import threading
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

from cronista.client import capture
from cronista.client.signal_bar import OUTROS_COLOR, VOCE_COLOR

console = Console()

_BLOCKS = "▁▂▃▄▅▆▇█"
_HISTORY = 40
_SENSITIVITY = 0.3
_MIN_TONE = 0.35
DURATION_SECONDS = 8


def _tone(base_hex: str, intensity: float) -> str:
    r = int(base_hex[1:3], 16)
    g = int(base_hex[3:5], 16)
    b = int(base_hex[5:7], 16)
    frac = _MIN_TONE + (1 - _MIN_TONE) * max(0.0, min(intensity, 1.0))
    return f"#{int(r * frac):02x}{int(g * frac):02x}{int(b * frac):02x}"


def _render_trace(history: deque[float], color: str) -> Text:
    text = Text()
    for level in history:
        clamped = max(0.0, min(level, 1.0)) ** _SENSITIVITY
        idx = min(int(clamped * len(_BLOCKS)), len(_BLOCKS) - 1)
        text.append(_BLOCKS[idx], style=_tone(color, clamped))
    return text


def main() -> int:
    voce_hist: deque[float] = deque([0.0] * _HISTORY, maxlen=_HISTORY)
    outros_hist: deque[float] = deque([0.0] * _HISTORY, maxlen=_HISTORY)
    lock = threading.Lock()
    live_ref: list[Live] = []

    def render() -> Group:
        row_voce = Text("  voce   ")
        row_voce.append(_render_trace(voce_hist, VOCE_COLOR))
        row_outros = Text("  outros ")
        row_outros.append(_render_trace(outros_hist, OUTROS_COLOR))
        return Group(row_voce, row_outros)

    def on_level(speaker: str, level: float) -> None:
        with lock:
            (voce_hist if speaker == "voce" else outros_hist).append(level)
            if live_ref:
                live_ref[0].update(render())

    with tempfile.TemporaryDirectory(prefix="cronista_test_thin_") as tmp:
        output_dir = Path(tmp)
        stop_event = threading.Event()

        def stop_after_a_while() -> None:
            time.sleep(DURATION_SECONDS)
            stop_event.set()

        threading.Thread(target=stop_after_a_while, daemon=True).start()

        print(f"Gravando {DURATION_SECONDS}s. Fale e deixe algo tocando...\n")
        with Live(render(), console=console, refresh_per_second=13) as live:
            live_ref.append(live)
            result = capture.record(output_dir, stop_event=stop_event, on_level=on_level)

        print("\nResultado:")
        for track in result.tracks:
            sinal = "com sinal" if track.had_signal else "SEM SINAL"
            print(f"  {track.speaker:>7} | {sinal:10} | {track.duration_ms}ms")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
