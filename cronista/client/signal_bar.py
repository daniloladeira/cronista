"""Medidor de sinal por trilha, traço horizontal com histórico.
Ver docs/17-identidade-visual-cli.md §6.

Blocos discretos por altura (▁▂▃▄▅▆▇█), não gradiente suave — mesma
filosofia "pixelizada" aprovada na escada vertical (a primeira versão
deste módulo), agora num traço horizontal compacto, tipo osciloscópio,
inspirado no indicador do Notion durante a gravação.
"""

from __future__ import annotations

import threading
from collections import deque

from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

VOCE_COLOR = "#DFB878"  # dourado — cor principal do sistema
OUTROS_COLOR = "#A6A6A6"  # cinza neutro, sem calor, de propósito

_BLOCKS = "▁▂▃▄▅▆▇█"
_HISTORY = 40  # largura do traço, em amostras

_TRACK_ORDER = ("voce", "outros")
_TRACK_COLOR = {"voce": VOCE_COLOR, "outros": OUTROS_COLOR}
_TRACK_LABEL = {"voce": "voce  ", "outros": "outros"}


def _render_trace(history: deque[float], color: str) -> Text:
    text = Text()
    for level in history:
        idx = min(int(max(0.0, min(level, 1.0)) * len(_BLOCKS)), len(_BLOCKS) - 1)
        text.append(_BLOCKS[idx], style=color)
    return text


class SignalBar:
    """Indicador de sinal por trilha, durante a gravação (RF-05).

    Uso: `signal_bar.update` serve direto como `on_level` de
    `capture.record()` — mesma assinatura, (speaker, level).

    Thread-safe de propósito: as duas trilhas atualizam ao mesmo tempo, de
    threads diferentes. Um único Live desenha; nenhuma thread de captura
    escreve no terminal diretamente.
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()
        self._lock = threading.Lock()
        self._history: dict[str, deque[float]] = {
            track: deque([0.0] * _HISTORY, maxlen=_HISTORY) for track in _TRACK_ORDER
        }
        self._live: Live | None = None

    def __enter__(self) -> SignalBar:
        self._live = Live(self._render(), console=self._console, refresh_per_second=13)
        self._live.__enter__()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._live is not None:
            self._live.__exit__(*exc_info)
            self._live = None

    def update(self, speaker: str, level: float) -> None:
        with self._lock:
            self._history[speaker].append(level)
            if self._live is not None:
                self._live.update(self._render())

    def _render(self) -> Group:
        rows = []
        for track in _TRACK_ORDER:
            row = Text(f"  {_TRACK_LABEL[track]} ")
            row.append(_render_trace(self._history[track], _TRACK_COLOR[track]))
            rows.append(row)
        return Group(*rows)
