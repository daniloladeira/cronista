"""Medidor de sinal por trilha. Ver docs/17-identidade-visual-cli.md §6.

Duas representações da MESMA história de nível, não dois indicadores
independentes: um traço fino de uma linha (para o cabeçalho, embutido ao
lado do título) e uma barra de algumas linhas com gradiente fixo por
posição (o indicador principal, mais abaixo na tela). `capture.py`
alimenta um único `SignalBar` via `update()`; as duas vistas leem do
mesmo histórico.

O gradiente da barra principal é FIXO por posição — a linha de baixo
sempre um tom mais escuro, a de cima sempre mais clara, igual em toda
coluna — não varia por nível como numa tentativa anterior (rejeitada:
"uma cor diferente em cada barra"). Só a altura acesa de cada coluna
muda com o volume, não a cor de cada linha. O traço fino do cabeçalho,
por ter uma linha só, não tem como ter gradiente de posição — nele o
tom varia por coluna mesmo, é a única forma de mostrar volume numa
única linha de altura.
"""

from __future__ import annotations

import threading
from collections import deque

from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

VOCE_COLOR = "#DFB878"  # dourado — cor principal do sistema
OUTROS_COLOR = "#A6A6A6"  # cinza neutro, sem calor, de propósito

_CELL = "█"
_OFF_COLOR = "#2A2A2A"  # célula apagada — quase invisível, nunca preto puro
_BAR_ROWS = 3  # altura da barra principal, poucas linhas pra ficar compacto
_HISTORY = 24  # largura do histórico guardado, em amostras
_INLINE_WIDTH = 8  # quantas amostras recentes aparecem no traço do cabeçalho

_THIN_BLOCKS = "▁▂▃▄▅▆▇█"

_TRACK_ORDER = ("voce", "outros")
_TRACK_COLOR = {"voce": VOCE_COLOR, "outros": OUTROS_COLOR}
_TRACK_LABEL = {"voce": "voce", "outros": "outros"}

_SENSITIVITY = 0.3  # expoente da curva de resposta: <1 realça som baixo sem estourar o alto
_MIN_TONE = 0.35  # tom mínimo do gradiente


def _tone(base_hex: str, intensity: float) -> str:
    r = int(base_hex[1:3], 16)
    g = int(base_hex[3:5], 16)
    b = int(base_hex[5:7], 16)
    frac = _MIN_TONE + (1 - _MIN_TONE) * max(0.0, min(intensity, 1.0))
    return f"#{int(r * frac):02x}{int(g * frac):02x}{int(b * frac):02x}"


def _render_track_rows(history: deque[float], color: str) -> list[Text]:
    lit_counts = []
    for level in history:
        clamped = max(0.0, min(level, 1.0)) ** _SENSITIVITY
        lit_counts.append(round(clamped * _BAR_ROWS))

    rows = []
    for h in range(_BAR_ROWS - 1, -1, -1):  # topo primeiro
        # Gradiente fixo por posição: esta linha tem sempre o mesmo tom,
        # em toda coluna, esteja ela acesa ou não.
        row_color = _tone(color, (h + 1) / _BAR_ROWS)
        text = Text("  ")
        for lit in lit_counts:
            text.append(_CELL, style=row_color if h < lit else _OFF_COLOR)
        rows.append(text)
    return rows


class SignalBar:
    """Indicador de sinal por trilha, durante a gravação (RF-05).

    Uso: `signal_bar.update` serve direto como `on_level` de
    `capture.record()` — mesma assinatura, (speaker, level).

    Thread-safe de propósito: as duas trilhas atualizam ao mesmo tempo, de
    threads diferentes. `render_header_trace()` e `render_bars()` são
    seguras de chamar a qualquer momento; nenhuma thread de captura
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
        self._live = Live(self.render_bars(), console=self._console, refresh_per_second=13)
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
                self._live.update(self.render_bars())

    def render_header_trace(self, track: str, width: int = _INLINE_WIDTH) -> Text:
        """Traço fino de uma linha, para embutir ao lado do título."""
        with self._lock:
            recent = list(self._history[track])[-width:]
        color = _TRACK_COLOR[track]
        text = Text()
        for level in recent:
            clamped = max(0.0, min(level, 1.0)) ** _SENSITIVITY
            idx = min(int(clamped * len(_THIN_BLOCKS)), len(_THIN_BLOCKS) - 1)
            text.append(_THIN_BLOCKS[idx], style=_tone(color, clamped))
        return text

    def render_bars(self) -> Group:
        """A barra principal, com gradiente fixo por posição."""
        parts: list[Text] = []
        for i, track in enumerate(_TRACK_ORDER):
            if i > 0:
                parts.append(Text(""))
            parts.extend(_render_track_rows(self._history[track], _TRACK_COLOR[track]))
            parts.append(Text(f"  {_TRACK_LABEL[track]}", style=_TRACK_COLOR[track]))
        return Group(*parts)
