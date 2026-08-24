"""Menu inicial de `cronista` sem comando: banner + info de sessão
(`session_info.py`, compartilhado com o fallback estático de `cli.py`),
lista de comandos navegável por seta.

Este app é só um seletor: ao escolher um item, ele termina (`self.exit`)
antes do comando escolhido rodar. Nenhum comando roda dentro dele — em
especial `rec`, que continua fora de qualquer loop de evento, de
propósito (ADR-0006). Quem despacha pro comando de verdade é `cli.py`.

Sem `align`/centralização no CSS -- a primeira tentativa disso, na tela
estática (Rich puro, não Textual), quebrou de verdade no terminal do
usuário (largura/altura mal detectada). Alinhado à esquerda, como o
fallback estático que já funciona."""

from __future__ import annotations

from rich.console import Console, Group
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from cronista.client import banner, session_info

_DOURADO = "#DFB878"  # cor de identidade do sistema (docs/17-identidade-visual-cli.md §4)

_COMMANDS = [
    ("rec", "rec — grava uma reunião"),
    ("devices", "devices — lista dispositivos de entrada e saída"),
    ("sync", "sync — reenvia reuniões pendentes"),
    ("login", "login — autentica e salva o token"),
    ("list", "list — lista reuniões, ler transcrição e resumo"),
]


class HomeApp(App[str]):
    """`app.run()` devolve o id do comando escolhido, ou `None` se o
    usuário saiu sem escolher (Escape/q)."""

    CSS = f"""
    Screen {{
        align: left top;
    }}
    Vertical {{
        width: auto;
        height: auto;
        padding: 1 2;
    }}
    OptionList {{
        width: auto;
        margin-top: 1;
        border: round {_DOURADO};
    }}
    OptionList:focus {{
        border: round {_DOURADO};
    }}
    OptionList > .option-list--option-highlighted {{
        background: {_DOURADO};
        color: #1A1200;
    }}
    """

    BINDINGS = [("escape", "quit_sem_escolher", ""), ("q", "quit_sem_escolher", "")]

    def __init__(self) -> None:
        # ansi_color: usa a paleta/fundo do próprio terminal em vez do
        # tema escuro fixo do Textual (#121212) -- sem isso a tela ficava
        # com um "fundo preto" que não batia com o resto do app (que só
        # imprime, sem pintar fundo nenhum).
        super().__init__(ansi_color=True)

    def compose(self) -> ComposeResult:
        console = Console(width=self.size.width or 80)
        info = Static(Group(*session_info.partes(console)))
        # `width: auto` do Textual não mede direito a linha mais larga de
        # um Text com múltiplas linhas internas (\n embutido) -- sem
        # largura explícita, o banner cortava no meio mesmo com
        # no_wrap=True (achado comparando o SVG exportado, não presumido).
        info.styles.width = max(banner.width(), 40) + 2
        with Vertical():
            yield info
            comandos = OptionList(*(Option(label, id=cmd_id) for cmd_id, label in _COMMANDS))
            comandos.border_title = "comandos"
            yield comandos

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.exit(event.option.id)

    def action_quit_sem_escolher(self) -> None:
        self.exit(None)
