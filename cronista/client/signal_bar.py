"""Tela de `cronista rec` (docs/17-identidade-visual-cli.md §3/§6): régua
com o nome do app, cabeçalho compacto numa linha só (título à esquerda,
indicador de sinal embutido à direita), rodapé com duração.

RF-31 (pausar/retomar): enquanto pausado, o traço do cabeçalho vira o
texto "pausado" em âmbar, e a duração para de contar (RN-11).
"""

from __future__ import annotations

import ctypes
import sys
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

from cronista.client.colors import shimmer_position, shimmer_text

VOCE_COLOR = "#DFB878"  # dourado — cor principal do sistema
OUTROS_COLOR = "#A6A6A6"  # cinza neutro, sem calor, de propósito
PAUSADO_COLOR = "#BA7517"  # âmbar — só aparece durante uma pausa (RF-31)

_FLASH_COLOR = "#FFFFFF"  # brilho do shimmer no nome "cronista" (docs/17 §7)
_FLASH_WIDTH = 2.5  # largura do brilho, em "caracteres"
_SWEEP_SECONDS = 2.5  # tempo pra atravessar a palavra inteira
_PAUSE_BETWEEN_SWEEPS = 1.5  # pausa apagada entre uma varredura e a próxima
_BANNER_WORD = "cronista"

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
        # Relógio do shimmer do banner (§7): roda sempre, inclusive
        # pausado — é decoração da marca, não indicação de gravação.
        self._banner_started_at = time.monotonic()

    def __enter__(self) -> SignalBar:
        self._segment_started_at = time.monotonic()
        # `get_renderable` faz o Live redesenhar sozinho a 13fps (o refresh
        # já existia pro medidor de sinal); é o que dá vida ao shimmer sem
        # depender de callback de áudio chegando — inclusive durante pausa,
        # quando as threads de captura param de chamar update().
        self._live = Live(
            console=self._console,
            get_renderable=self.render,
            refresh_per_second=13,
            screen=True,
        )
        self._live.__enter__()
        self._set_tab_title(f"gravando · {self._title}")
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._live is not None:
            self._live.__exit__(*exc_info)
            self._live = None
        self._set_tab_title("cronista")

    def _set_tab_title(self, title: str) -> None:
        """Título da aba/janela do terminal. A sequência OSC funciona na
        maioria dos terminais modernos; no Windows, complementa com a API
        nativa porque o console legado nem sempre processa OSC.

        Duas armadilhas:

        1. `Live` redireciona `sys.stdout` sozinho enquanto ativo
           (`redirect_stdout=True`, padrão) — escrever em `sys.stdout`
           aqui dentro passaria pelo próprio realce de sintaxe do Rich e
           saía corrompido. `sys.__stdout__` é o fluxo original, imune a
           esse redirecionamento.
        2. A escrita usa o mesmo lock do Console (`console._lock`, o que
           o Live usa por baixo pro próprio redesenho) — sem isso, a
           thread de auto-refresh do shimmer (§7, `get_renderable`) pode
           escrever no terminal ao mesmo tempo que esta chamada,
           intercalando bytes.

        Decorativo, então qualquer falha aqui (encoding do console legado,
        stream fechado) é engolida — nunca pode derrubar a gravação por
        causa do título da aba."""
        try:
            stream = sys.__stdout__ or sys.stdout
            with self._console._lock:
                stream.write(f"\x1b]0;{title}\x07")
                stream.flush()
            if sys.platform == "win32":
                ctypes.windll.kernel32.SetConsoleTitleW(title)
        except (UnicodeEncodeError, OSError, ValueError):
            pass

    def _elapsed_seconds(self) -> int:
        with self._lock:
            if self._paused:
                return int(self._active_seconds)
            return int(self._active_seconds + (time.monotonic() - self._segment_started_at))

    def update(self, speaker: str, level: float) -> None:
        # O Live redesenha sozinho a 13fps (`get_renderable`, __enter__) —
        # só precisa mutar o estado aqui, sem forçar um render extra.
        with self._lock:
            self._history[speaker].append(level)

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
        self._set_tab_title(
            f"pausado · {self._title}" if paused else f"gravando · {self._title}"
        )

    def render_header_trace(self, track: str, width: int = _INLINE_WIDTH, frozen: bool = False) -> Text:
        """Traço fino de uma linha, para embutir ao lado do título.

        `frozen=True` (pausado): as threads de captura já param de chamar
        `update()` durante a pausa (capture.py), então o desenho por si só
        já para de mudar -- isto só troca a cor viva (gradiente por nível)
        por um tom único e apagado, reforçando visualmente o "parado"."""
        with self._lock:
            recent = list(self._history[track])[-width:]
        color = _TRACK_COLOR[track]
        static_color = _tone(color, 0.0)
        text = Text()
        for level in recent:
            clamped = max(0.0, min(level, 1.0)) ** _SENSITIVITY
            idx = min(int(clamped * len(_THIN_BLOCKS)), len(_THIN_BLOCKS) - 1)
            text.append(_THIN_BLOCKS[idx], style=static_color if frozen else _tone(color, clamped))
        return text

    def render_banner(self) -> Group:
        """Nome "cronista" acima da régua, com um brilho branco varrendo o
        dourado em loop (docs/17-identidade-visual-cli.md §7)."""
        position = shimmer_position(
            self._banner_started_at, len(_BANNER_WORD), _FLASH_WIDTH, _SWEEP_SECONDS, _PAUSE_BETWEEN_SWEEPS
        )
        word = shimmer_text(_BANNER_WORD, position, VOCE_COLOR, _FLASH_COLOR, _FLASH_WIDTH)
        return Group(word, Rule(style=VOCE_COLOR))

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
            self.render_banner(),
            Text(""),
            self.render_header(),
            Text(""),
            self.render_footer(),
        )
        return Padding(content, _MARGIN)
