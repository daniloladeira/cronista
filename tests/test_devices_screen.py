"""Testes da tela de `cronista devices` (UC-02, gatilho de reversão do
ADR-0016). `capture.list_input_devices`/`list_output_devices` são
mockados -- comportamento real desses já é coberto onde captura de
áudio é testada de verdade."""

from __future__ import annotations

import html
import re
from collections import defaultdict

import pytest
from textual.color import Color

from cronista.client import capture
from cronista.client.capture import DeviceInfo
from cronista.client.devices_screen import _DOURADO, DevicesApp

_ENTRADA = [DeviceInfo("Microfone Fake", True)]
_SAIDA = [DeviceInfo("Alto-falantes Fake", False), DeviceInfo("Fones Fake", True)]


@pytest.mark.asyncio
async def test_mostra_dispositivos_de_entrada_e_saida(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capture, "list_input_devices", lambda: _ENTRADA)
    monkeypatch.setattr(capture, "list_output_devices", lambda: _SAIDA)

    app = DevicesApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        svg = app.export_screenshot()

    texto = _texto_do_svg(svg)
    assert "Microfone Fake" in texto
    assert "Alto-falantes Fake" in texto
    assert "Fones Fake" in texto
    assert "entrada" in texto.lower()
    assert "saída" in texto.lower()

    # Nome "cronista" pequeno no topo, com o brilho passando -- mesmo
    # efeito do cabeçalho de `cronista rec` (docs/17 §7), não o banner
    # grande de abertura (pedido explícito do usuário).
    assert "cronista" in texto.lower()


@pytest.mark.asyncio
async def test_usa_a_cor_de_identidade_dourada(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regressão: devices usava a borda reta padrão do Rich, sem nenhuma
    # cor de identidade -- mesma lacuna que home.py/panel.py tinham,
    # corrigida à parte.
    monkeypatch.setattr(capture, "list_input_devices", lambda: _ENTRADA)
    monkeypatch.setattr(capture, "list_output_devices", lambda: _SAIDA)

    app = DevicesApp()
    async with app.run_test():
        entrada = app.query_one("#entrada")
        estilo, cor = entrada.styles.border_top
        assert estilo == "round"
        assert cor == Color.parse(_DOURADO)


@pytest.mark.asyncio
async def test_regua_do_titulo_vai_de_ponta_a_ponta(monkeypatch: pytest.MonkeyPatch) -> None:
    # Achado real: a régua sob "cronista" nascia só tão larga quanto os
    # painéis de dispositivo (dentro do mesmo Vertical de largura
    # automática) -- o usuário pediu o mesmo efeito do cabeçalho do
    # `rec`, que vai de ponta a ponta da tela, não só do bloco abaixo.
    monkeypatch.setattr(capture, "list_input_devices", lambda: _ENTRADA)
    monkeypatch.setattr(capture, "list_output_devices", lambda: _SAIDA)

    app = DevicesApp()
    async with app.run_test(size=(100, 25)) as pilot:
        await pilot.pause()
        titulo = app.query_one("#titulo")
        entrada = app.query_one("#entrada")
        assert titulo.size.width > entrada.size.width + 10


@pytest.mark.asyncio
async def test_escape_sai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capture, "list_input_devices", lambda: [])
    monkeypatch.setattr(capture, "list_output_devices", lambda: [])

    app = DevicesApp()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()

    assert app.is_running is False


@pytest.mark.asyncio
async def test_q_tambem_sai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capture, "list_input_devices", lambda: [])
    monkeypatch.setattr(capture, "list_output_devices", lambda: [])

    app = DevicesApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        await pilot.pause()

    assert app.is_running is False


def _texto_do_svg(svg: str) -> str:
    matrix = re.search(r'<g class="terminal-\d+-matrix">(.*?)</g>', svg, re.S).group(1)
    rows: dict[float, list[tuple[float, str]]] = defaultdict(list)
    for m in re.finditer(r'<text[^>]*x="([\d.]+)"\s*y="([\d.]+)"[^>]*>(.*?)</text>', matrix, re.S):
        x, y, ch = float(m.group(1)), float(m.group(2)), m.group(3)
        rows[y].append((x, ch))
    linhas = ["".join(ch for _, ch in sorted(cells)) for cells in rows.values()]
    return html.unescape("\n".join(linhas)).replace("\xa0", " ")
