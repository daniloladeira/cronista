"""Tela de `cronista devices` (UC-02). Absorvido pro modelo de tela
persistente por causa do gatilho de reversão do ADR-0016: o comando
"fechava sozinho" (imprimia e o processo terminava) e usava um estilo
visual diferente do resto (borda reta do Rich, sem a cor de
identidade) -- achado real, reportado pelo usuário duas vezes.

Mesmo estilo de `home.py`/`panel.py`: `App[None]`, `ansi_color=True`.
Sem `ListView`/seleção -- é informativo, não navegável, só Escape/q
pra sair.
"""

from __future__ import annotations

import time

from rich.console import Group
from rich.rule import Rule
from rich.table import Table
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from cronista.client import capture
from cronista.client.colors import shimmer_position, shimmer_text

_DOURADO = "#DFB878"  # cor de identidade do sistema (docs/17-identidade-visual-cli.md §4)
_FLASH_COLOR = "#FFFFFF"  # brilho do shimmer, mesmo valor de signal_bar.py
_FLASH_WIDTH = 2.5
_SWEEP_SECONDS = 2.5
_PAUSE_BETWEEN_SWEEPS = 1.5
_BANNER_WORD = "cronista"
_FRAME_SECONDS = 0.075  # ~13fps (docs/17-identidade-visual-cli.md §1)


def _tabela_dispositivos(dispositivos: list[capture.DeviceInfo]) -> Table:
    # box=None: sem isso, a tabela desenhava a própria borda reta dentro
    # do painel arredondado -- uma caixa dentro da outra (achado real,
    # apontado pelo usuário vendo a tela de verdade). Só o painel externo
    # emoldura; aqui dentro é texto alinhado, sem moldura própria.
    tabela = Table(box=None, header_style=f"bold {_DOURADO}")
    tabela.add_column("Nome")
    tabela.add_column("Padrão")
    for d in dispositivos:
        tabela.add_row(d.name, "sim" if d.is_default else "")
    return tabela


class DevicesApp(App[None]):
    CSS = f"""
    Screen {{
        align: left top;
    }}
    Vertical {{
        width: auto;
        height: auto;
        padding: 1 2;
    }}
    #titulo {{
        margin-bottom: 1;
    }}
    #entrada, #saida {{
        border: round {_DOURADO};
        /* width: auto não mede o Rich Table direito (mesma lacuna
        documentada em home.py pro banner) -- sem largura explícita, as
        colunas colapsavam pro mínimo, cortando o nome dos dispositivos
        (achado exportando SVG de verdade, não presumido). */
        width: 70;
        margin-bottom: 1;
    }}
    """

    BINDINGS = [("escape", "sair", ""), ("q", "sair", "")]

    def __init__(self) -> None:
        # ansi_color: mesma razão de home.py/panel.py -- usa a paleta do
        # terminal real em vez do tema escuro fixo do Textual.
        super().__init__(ansi_color=True)
        self._banner_started_at = time.monotonic()

    def compose(self) -> ComposeResult:
        # Nome pequeno com o brilho passando (docs/17 §7), mesmo efeito
        # do cabeçalho do `rec` -- pedido explícito do usuário, não o
        # banner grande de abertura (essa tela é ferramenta de consulta,
        # não a tela de boas-vindas).
        entrada = Static(_tabela_dispositivos(capture.list_input_devices()), id="entrada")
        entrada.border_title = "entrada (microfone)"
        saida = Static(_tabela_dispositivos(capture.list_output_devices()), id="saida")
        saida.border_title = "saída (loopback)"
        with Vertical():
            yield Static(id="titulo")
            yield entrada
            yield saida

    def on_mount(self) -> None:
        self._atualizar_titulo()
        self.set_interval(_FRAME_SECONDS, self._atualizar_titulo)

    def _atualizar_titulo(self) -> None:
        position = shimmer_position(
            self._banner_started_at, len(_BANNER_WORD), _FLASH_WIDTH, _SWEEP_SECONDS, _PAUSE_BETWEEN_SWEEPS
        )
        word = shimmer_text(_BANNER_WORD, position, _DOURADO, _FLASH_COLOR, _FLASH_WIDTH)
        self.query_one("#titulo", Static).update(Group(word, Rule(style=_DOURADO)))

    def action_sair(self) -> None:
        self.exit()
