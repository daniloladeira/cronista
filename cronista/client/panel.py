"""Painel navegável que unifica `list`, `ler` e `buscar` (ADR-0016):
lista de reuniões à esquerda, leitura com abas Transcrição/Resumo à
direita, busca embutida (tecla `/`) que repopula a lista sem sair da
tela. Três comandos, um app só -- `cli.py` só escolhe o ponto de
entrada (`meeting_id` pra `ler`, `search_term` pra `buscar`, nenhum dos
dois pra `list`).

Mesmo estilo de `home.py`: `App[None]`, `ansi_color=True` pra não
pintar fundo escuro por cima do terminal real. Sem o banner/session_info
completo daqui -- esta tela é ferramenta de trabalho (maximizar espaço
pra conteúdo), não a tela de boas-vindas."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, ListItem, ListView, Markdown, Static, TabbedContent, TabPane

from cronista.client import api_client

_DOURADO = "#DFB878"  # cor de identidade do sistema (docs/17-identidade-visual-cli.md §4)

_SEM_TRANSCRICAO = "(sem transcrição ainda)"
_SEM_RESUMO = "(sem resumo ainda)"


def _rotulo_reuniao(reuniao: dict) -> str:
    return f"{reuniao['title']} · {reuniao['status']}"


def _texto_transcricao(segmentos: list[dict]) -> str:
    if not segmentos:
        return _SEM_TRANSCRICAO
    return "\n".join(f"[{s['timestamp']}] {s['speaker']}: {s['text']}" for s in segmentos)


def _markdown_resumo(reuniao: dict) -> str:
    resumos = reuniao.get("summaries") or []
    if not resumos:
        return _SEM_RESUMO
    mais_recente = sorted(resumos, key=lambda r: r["generated_at"])[-1]
    return mais_recente["markdown"]


class PanelApp(App[None]):
    """`app.run()` não devolve nada relevante -- ao contrário de
    `HomeApp`, este painel não despacha pra outro comando ao sair, ele É
    o destino final da navegação (docs/11-cli.md §1-2)."""

    CSS = f"""
    Screen {{
        layout: horizontal;
    }}
    #lista {{
        width: 40;
        border-right: solid {_DOURADO};
    }}
    #lista ListItem {{
        /* Título de reunião longo quebra em 2 linhas dentro do item --
        sem respiro embaixo, o item seguinte cola direto nele e as duas
        linhas parecem itens soltos, não um título de dois. Achado
        exportando SVG de verdade e lendo linha por linha, não só
        olhando por cima (ADR-0016). */
        margin-bottom: 1;
    }}
    #lista ListItem.-highlight {{
        background: {_DOURADO};
        color: #1A1200;
    }}
    #lista:focus ListItem.-highlight {{
        background: {_DOURADO};
        color: #1A1200;
    }}
    Underline > .underline--bar {{
        color: {_DOURADO};
    }}
    #leitura {{
        width: 1fr;
    }}
    #busca {{
        dock: bottom;
        display: none;
    }}
    #busca.visivel {{
        display: block;
    }}
    #busca:focus {{
        border: tall {_DOURADO};
    }}
    """

    BINDINGS = [
        ("escape", "sair", ""),
        ("q", "sair", ""),
        ("slash", "focar_busca", "Buscar"),
    ]

    def __init__(self, meeting_id: str | None = None, search_term: str | None = None) -> None:
        super().__init__(ansi_color=True)
        self._meeting_id_inicial = meeting_id
        self._search_term_inicial = search_term
        self._reunioes_na_lista: list[dict] = []

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ListView(id="lista")
            with Vertical(id="leitura"):
                with TabbedContent():
                    with TabPane("Transcrição", id="aba-transcricao"):
                        yield VerticalScroll(Static(_SEM_TRANSCRICAO, id="conteudo-transcricao"))
                    with TabPane("Resumo", id="aba-resumo"):
                        yield Markdown(_SEM_RESUMO, id="conteudo-resumo")
        yield Input(placeholder="Buscar…", id="busca")

    def on_mount(self) -> None:
        if self._search_term_inicial:
            self._buscar(self._search_term_inicial)
        else:
            self._carregar_lista()
        if self._meeting_id_inicial:
            self._abrir_reuniao(self._meeting_id_inicial)
        # Sem isto, o foco inicial cai no Input de busca (escondido,
        # display: none) em vez da lista -- achado real depurando por que
        # o destaque dourado do item selecionado não aparecia na tela de
        # abertura: nada estava com foco pra receber a classe -highlight.
        self.query_one("#lista", ListView).focus()

    def _carregar_lista(self) -> None:
        try:
            self._reunioes_na_lista = api_client.list_meetings()
        except api_client.ApiError as exc:
            # RNF-U02: erro é hora de clareza, não de estourar a tela toda
            # com traceback (achado real: API fora do ar derrubava o
            # painel inteiro com stack trace, em vez de avisar e deixar
            # o usuário tentar de novo).
            self.notify(str(exc), title="Erro", severity="error", timeout=8)
            return
        self._preencher_lista()

    def _buscar(self, termo: str) -> None:
        try:
            resultados = api_client.search(termo)
        except api_client.ApiError as exc:
            self.notify(str(exc), title="Erro", severity="error", timeout=8)
            return
        # Um resultado de busca é um trecho, não uma reunião -- agrupa por
        # reunião (mantendo a primeira ocorrência, já vem ordenado por
        # relevância) pra reaproveitar a mesma lista/seleção de sempre.
        vistas: dict[str, dict] = {}
        for r in resultados:
            if r["meeting_id"] not in vistas:
                vistas[r["meeting_id"]] = {
                    "id": r["meeting_id"],
                    "title": r["meeting_title"],
                    "status": f'trecho: "{r["text"][:40]}"',
                }
        self._reunioes_na_lista = list(vistas.values())
        self._preencher_lista()

    def _preencher_lista(self) -> None:
        lista = self.query_one("#lista", ListView)
        lista.clear()
        for reuniao in self._reunioes_na_lista:
            item = ListItem(Static(_rotulo_reuniao(reuniao)))
            item.data = reuniao["id"]  # type: ignore[attr-defined]
            lista.append(item)
        if self._reunioes_na_lista:
            # Sem isto, `index` fica None até o usuário apertar uma seta --
            # nenhum item nasce destacado, então a cor dourada do cursor
            # (achado real depurando por que não aparecia em tela) só se
            # provaria depois de uma interação, nunca na abertura.
            lista.index = 0

    def _abrir_reuniao(self, meeting_id: str) -> None:
        try:
            reuniao = api_client.get_meeting(meeting_id)
            segmentos = api_client.get_transcript(meeting_id)
        except api_client.ApiError as exc:
            self.notify(str(exc), title="Erro", severity="error", timeout=8)
            return
        self.query_one("#conteudo-transcricao", Static).update(_texto_transcricao(segmentos))
        self.query_one("#conteudo-resumo", Markdown).update(_markdown_resumo(reuniao))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        meeting_id = getattr(event.item, "data", None)
        if meeting_id:
            self._abrir_reuniao(meeting_id)

    def action_focar_busca(self) -> None:
        campo = self.query_one("#busca", Input)
        campo.add_class("visivel")
        campo.value = ""
        campo.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        campo = self.query_one("#busca", Input)
        campo.remove_class("visivel")
        # A tecla "/" que abre a busca (action_focar_busca) chega no Input
        # como primeiro caractere digitado, mesmo limpando o valor no
        # momento do foco -- achado testando de verdade (Pilot.press),
        # não presumido. Mais confiável tirar aqui, no submit, do que
        # tentar vencer a ordem exata dos eventos do Textual.
        termo = event.value.strip().removeprefix("/").strip()
        if termo:
            self._buscar(termo)
        self.query_one("#lista", ListView).focus()

    def action_sair(self) -> None:
        self.exit()
