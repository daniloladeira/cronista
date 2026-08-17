"""Tela de `cronista rec`. Ver docs/17-identidade-visual-cli.md §3/§6, e o
layout decidido em `scripts/preview_rec_screen.py` (commit `9683e85`,
"Consolida medidor de sinal"): régua com o nome do app, cabeçalho compacto
numa linha só (título à esquerda, indicador de sinal embutido à direita),
rodapé com duração — **sem** bloco de barra grande no conteúdo. O indicador
de sinal vive só no cabeçalho, como traço fino por trilha.

RF-31 (pausar/retomar): decidido com preview visual comparado ao vivo com
o usuário. Enquanto pausado, o traço do cabeçalho vira o texto "pausado"
em âmbar, e a duração para de contar (RN-11: tempo pausado não é gravação).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime

from rich.console import Console, Group
from rich.live import Live
from rich.padding import Padding
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

VOCE_COLOR = "#DFB878"  # dourado — cor principal do sistema
OUTROS_COLOR = "#A6A6A6"  # cinza neutro, sem calor, de propósito
PAUSADO_COLOR = "#BA7517"  # âmbar — só aparece durante uma pausa (RF-31)

_HISTORY = 24  # amostras guardadas por trilha
_INLINE_WIDTH = 8  # quantas amostras recentes aparecem no traço do cabeçalho
_MARGIN = (0, 2)  # (vertical, horizontal) — único lugar que define o recuo da tela

_THIN_BLOCKS = "▁▂▃▄▅▆▇█"

_TRACK_ORDER = ("voce", "outros")
_TRACK_COLOR = {"voce": VOCE_COLOR, "outros": OUTROS_COLOR}

_SENSITIVITY = 0.3  # expoente da curva de resposta: <1 realça som baixo sem estourar o alto
_MIN_TONE = 0.35  # tom mínimo do gradiente


def _tone(base_hex: str, intensity: float) -> str:
    r = int(base_hex[1:3], 16)
    g = int(base_hex[3:5], 16)
    b = int(base_hex[5:7], 16)
    frac = _MIN_TONE + (1 - _MIN_TONE) * max(0.0, min(intensity, 1.0))
    return f"#{int(r * frac):02x}{int(g * frac):02x}{int(b * frac):02x}"


class SignalBar:
    """Estado e desenho da tela de `cronista rec` (RF-05 e RF-31).

    Uso: `signal_bar.update` serve direto como `on_level` de
    `capture.record()`, e `signal_bar.set_paused` como `on_pause_toggle` —
    mesma assinatura das duas.

    Thread-safe de propósito: as duas trilhas atualizam ao mesmo tempo, de
    threads diferentes. `render()` é seguro de chamar a qualquer momento;
    nenhuma thread de captura escreve no terminal diretamente.
    """

    def __init__(
        self, title: str, started_at: datetime, console: Console | None = None
    ) -> None:
        self._title = title
        self._started_at = started_at
        self._console = console or Console()
        self._lock = threading.Lock()
        self._history: dict[str, deque[float]] = {
            track: deque([0.0] * _HISTORY, maxlen=_HISTORY) for track in _TRACK_ORDER
        }
        self._paused = False
        self._live: Live | None = None
        # Duração é tempo de gravação ativo, não relógio de parede: soma o
        # que já passou de segmentos anteriores com o segmento em curso, e
        # não avança enquanto pausado (RN-11).
        self._active_seconds = 0.0
        self._segment_started_at = time.monotonic()

    def __enter__(self) -> SignalBar:
        self._segment_started_at = time.monotonic()
        self._live = Live(
            self.render(), console=self._console, refresh_per_second=13, screen=True
        )
        self._live.__enter__()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._live is not None:
            self._live.__exit__(*exc_info)
            self._live = None

    def _elapsed_seconds(self) -> int:
        with self._lock:
            if self._paused:
                return int(self._active_seconds)
            return int(self._active_seconds + (time.monotonic() - self._segment_started_at))

    def update(self, speaker: str, level: float) -> None:
        # `render()` readquire `self._lock` por conta própria (em
        # `render_header_trace`/`_elapsed_seconds`) — chamá-lo AINDA dentro
        # do `with` abaixo autodeadlocaria a thread, já que `threading.Lock`
        # não é reentrante. Por isso a mutação solta o lock antes de desenhar.
        with self._lock:
            self._history[speaker].append(level)
        if self._live is not None:
            self._live.update(self.render())

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            if paused == self._paused:
                return
            now = time.monotonic()
            if paused:
                self._active_seconds += now - self._segment_started_at
            else:
                self._segment_started_at = now
            self._paused = paused
        if self._live is not None:
            self._live.update(self.render())

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

    def render_top_rule(self) -> Rule:
        return Rule(Text("cronista", style=f"bold {VOCE_COLOR}"), style=VOCE_COLOR, align="left")

    def render_header(self) -> Table:
        title = Text()
        title.append(self._title, style=f"bold {VOCE_COLOR}")
        title.append(" @hoje ", style="dim")
        title.append(self._started_at.strftime("%H:%M"), style="dim")

        right = Text()
        if self._paused:
            right.append("pausado", style=PAUSADO_COLOR)
        else:
            right.append("voce ", style=VOCE_COLOR)
            right.append(self.render_header_trace("voce"))
            right.append("  outros ", style=OUTROS_COLOR)
            right.append(self.render_header_trace("outros"))

        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="right")
        grid.add_row(title, right)
        return grid

    def render_footer(self) -> Text:
        elapsed = self._elapsed_seconds()
        color = PAUSADO_COLOR if self._paused else OUTROS_COLOR
        text = Text()
        text.append("duração  ", style=color)
        text.append(f"{elapsed // 60:02d}:{elapsed % 60:02d}", style=color)
        text.append("\n\nespaço pausa/retoma · Ctrl+C encerra", style="dim")
        return text

    def render(self) -> Padding:
        content = Group(
            self.render_top_rule(),
            Text(""),
            self.render_header(),
            Text(""),
            self.render_footer(),
        )
        return Padding(content, _MARGIN)
