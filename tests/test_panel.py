"""Testes do painel navegável (list/ler/buscar, ADR-0016).
`api_client` é mockado -- o comportamento real dos endpoints já é
coberto em tests/test_meeting_detail.py, test_transcript.py,
test_search.py."""

from __future__ import annotations

import html
import re
from collections import defaultdict

import pytest
from textual.widgets import ListView, Markdown, Static

from cronista.client import api_client, panel
from cronista.client.panel import PanelApp

_REUNIOES = [
    {"id": "1", "title": "Reunião A", "status": "transcribed"},
    {"id": "2", "title": "Reunião B", "status": "recorded"},
]

_SEGMENTOS = [
    {"speaker": "voce", "start_ms": 0, "end_ms": 2000, "text": "oi", "timestamp": "00:00:00"},
    {"speaker": "outros", "start_ms": 2000, "end_ms": 4000, "text": "tudo bem", "timestamp": "00:00:02"},
]

_REUNIAO_DETALHE = {
    "id": "1",
    "title": "Reunião A",
    "status": "transcribed",
    "summaries": [
        {"markdown": "## Pauta\nantigo", "generated_at": "2026-08-20T10:00:00Z"},
        {"markdown": "## Pauta\nrecente", "generated_at": "2026-08-22T10:00:00Z"},
    ],
}


@pytest.mark.asyncio
async def test_lista_mostra_as_reunioes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_client, "list_meetings", lambda: _REUNIOES)

    app = PanelApp()
    async with app.run_test():
        lista = app.query_one("#lista", ListView)
        assert len(lista.children) == 2


@pytest.mark.asyncio
async def test_selecionar_reuniao_popula_transcricao_e_resumo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_client, "list_meetings", lambda: _REUNIOES)
    monkeypatch.setattr(api_client, "get_meeting", lambda meeting_id: _REUNIAO_DETALHE)
    monkeypatch.setattr(api_client, "get_transcript", lambda meeting_id: _SEGMENTOS)

    app = PanelApp()
    async with app.run_test() as pilot:
        lista = app.query_one("#lista", ListView)
        lista.focus()
        lista.index = 0
        await pilot.press("enter")
        await pilot.pause()

        transcricao = app.query_one("#conteudo-transcricao", Static).content
        assert "oi" in str(transcricao)
        assert "tudo bem" in str(transcricao)

        resumo = app.query_one("#conteudo-resumo", Markdown)
        # pega o resumo mais recente por generated_at, não o último da lista
        assert "recente" in resumo._markdown


@pytest.mark.asyncio
async def test_abre_ja_com_reuniao_focada_para_ler(monkeypatch: pytest.MonkeyPatch) -> None:
    # on_mount carrega a lista geral mesmo com meeting_id_inicial (o painel
    # de lista à esquerda continua populado) -- sem mockar list_meetings
    # aqui, o teste tentava uma conexão de rede real (achado real: só deu
    # pra ver depois que a API parou de estar sempre de pé no ambiente).
    monkeypatch.setattr(api_client, "list_meetings", lambda: _REUNIOES)
    monkeypatch.setattr(api_client, "get_meeting", lambda meeting_id: _REUNIAO_DETALHE)
    monkeypatch.setattr(api_client, "get_transcript", lambda meeting_id: _SEGMENTOS)

    app = PanelApp(meeting_id="1")
    async with app.run_test() as pilot:
        await pilot.pause()
        transcricao = app.query_one("#conteudo-transcricao", Static).content
        assert "oi" in str(transcricao)


@pytest.mark.asyncio
async def test_abre_ja_com_busca_rodada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api_client,
        "search",
        lambda q, **kw: [{"meeting_id": "1", "meeting_title": "Reunião A", "text": "decidimos migrar"}],
    )

    app = PanelApp(search_term="decisão")
    async with app.run_test() as pilot:
        await pilot.pause()
        lista = app.query_one("#lista", ListView)
        assert len(lista.children) == 1


@pytest.mark.asyncio
async def test_tecla_barra_abre_busca_e_enter_roda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_client, "list_meetings", lambda: _REUNIOES)
    chamadas = []
    monkeypatch.setattr(api_client, "search", lambda q, **kw: (chamadas.append(q), [])[1])

    app = PanelApp()
    async with app.run_test() as pilot:
        await pilot.press("slash")
        await pilot.pause()
        await pilot.press(*"decisão")
        await pilot.press("enter")
        await pilot.pause()

    assert chamadas == ["decisão"]


@pytest.mark.asyncio
async def test_escape_sai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_client, "list_meetings", lambda: [])

    app = PanelApp()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()

    assert app.is_running is False


@pytest.mark.asyncio
async def test_layout_nao_quebra_no_svg_exportado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mesma técnica de tests/test_home.py -- exporta e inspeciona de
    verdade antes de confiar visualmente no painel (ADR-0016, nota
    2026-08-18: "a lição foi entregar um preview de verdade... não só
    descrever em texto")."""
    monkeypatch.setattr(api_client, "list_meetings", lambda: _REUNIOES)
    monkeypatch.setattr(api_client, "get_meeting", lambda meeting_id: _REUNIAO_DETALHE)
    monkeypatch.setattr(api_client, "get_transcript", lambda meeting_id: _SEGMENTOS)

    app = PanelApp(meeting_id="1")
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        svg = app.export_screenshot()

    matrix = re.search(r'<g class="terminal-\d+-matrix">(.*?)</g>', svg, re.S).group(1)
    rows: dict[float, list[tuple[float, str]]] = defaultdict(list)
    for m in re.finditer(r'<text[^>]*x="([\d.]+)"\s*y="([\d.]+)"[^>]*>(.*?)</text>', matrix, re.S):
        x, y, ch = float(m.group(1)), float(m.group(2)), m.group(3)
        rows[y].append((x, ch))
    linhas = ["".join(ch for _, ch in sorted(cells)) for cells in rows.values()]
    texto = html.unescape("\n".join(linhas)).replace("\xa0", " ")

    assert "Reunião A" in texto
    assert "Transcrição" in texto
    assert "Resumo" in texto


@pytest.mark.asyncio
async def test_api_fora_do_ar_ao_carregar_lista_notifica_sem_derrubar_o_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Achado real: API fora do ar derrubava o painel inteiro com um
    # traceback bruto no terminal do usuário, em vez de avisar (RNF-U02).
    def _falha() -> list[dict]:
        raise api_client.ApiError("Não foi possível conectar à API.")

    monkeypatch.setattr(api_client, "list_meetings", _falha)
    avisos: list[str] = []
    monkeypatch.setattr(panel.PanelApp, "notify", lambda self, msg, **kw: avisos.append(msg))

    app = PanelApp()
    async with app.run_test() as pilot:
        await pilot.pause()

    assert avisos and "conectar" in avisos[0].lower()


@pytest.mark.asyncio
async def test_api_fora_do_ar_ao_abrir_reuniao_notifica_sem_derrubar_o_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_client, "list_meetings", lambda: _REUNIOES)

    def _falha(meeting_id: str) -> dict:
        raise api_client.ApiError("Não foi possível conectar à API.")

    monkeypatch.setattr(api_client, "get_meeting", _falha)
    avisos: list[str] = []
    monkeypatch.setattr(panel.PanelApp, "notify", lambda self, msg, **kw: avisos.append(msg))

    app = PanelApp(meeting_id="1")
    async with app.run_test() as pilot:
        await pilot.pause()

    assert avisos and "conectar" in avisos[0].lower()


@pytest.mark.asyncio
async def test_api_fora_do_ar_ao_buscar_notifica_sem_derrubar_o_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _falha(q: str, **kw: object) -> list[dict]:
        raise api_client.ApiError("Não foi possível conectar à API.")

    monkeypatch.setattr(api_client, "search", _falha)
    avisos: list[str] = []
    monkeypatch.setattr(panel.PanelApp, "notify", lambda self, msg, **kw: avisos.append(msg))

    app = PanelApp(search_term="decisão")
    async with app.run_test() as pilot:
        await pilot.pause()

    assert avisos and "conectar" in avisos[0].lower()
