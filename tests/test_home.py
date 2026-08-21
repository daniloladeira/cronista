"""Testes do menu inicial (docs/17-identidade-visual-cli.md §7, ADR-0016
extensão). `HomeApp` é só um seletor -- nenhum comando roda dentro dele,
ver cronista/client/cli.py pro despacho de verdade."""

from __future__ import annotations

import pytest

from cronista.client.home import _COMMANDS, HomeApp


@pytest.mark.asyncio
async def test_mostra_os_quatro_comandos() -> None:
    app = HomeApp()
    async with app.run_test():
        option_list = app.query_one("OptionList")
        assert [o.id for o in option_list._options] == [cmd_id for cmd_id, _ in _COMMANDS]


@pytest.mark.asyncio
async def test_selecionar_devolve_o_id_escolhido() -> None:
    app = HomeApp()
    async with app.run_test() as pilot:
        await pilot.press("down")  # rec -> devices
        await pilot.press("enter")
        await pilot.pause()

    assert app.return_value == "devices"


@pytest.mark.asyncio
async def test_escape_sai_sem_escolher() -> None:
    app = HomeApp()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()

    assert app.return_value is None


@pytest.mark.asyncio
async def test_q_tambem_sai_sem_escolher() -> None:
    app = HomeApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        await pilot.pause()

    assert app.return_value is None


@pytest.mark.asyncio
async def test_banner_nao_quebra_no_meio_da_linha() -> None:
    """Regressão: dentro do `Static`, o banner grande quebrava no meio de
    cada linha por falta de largura explícita -- descoberto exportando a
    tela pra SVG e comparando linha por linha, não só olhando o texto
    bruto (que não revela quebra de linha visual)."""
    import re
    from collections import defaultdict

    app = HomeApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        svg = app.export_screenshot()

    matrix = re.search(r'<g class="terminal-\d+-matrix">(.*?)</g>', svg, re.S).group(1)
    rows: dict[float, list[tuple[float, str]]] = defaultdict(list)
    for m in re.finditer(r'<text[^>]*x="([\d.]+)"\s*y="([\d.]+)"[^>]*>(.*?)</text>', matrix, re.S):
        x, y, ch = float(m.group(1)), float(m.group(2)), m.group(3)
        rows[y].append((x, ch))

    linhas = ["".join(ch for _, ch in sorted(cells)) for cells in rows.values()]
    # linha real do banner grande (sem espaço) tem ~54-62 caracteres --
    # se alguma linha com conteúdo saiu bem mais curta, quebrou no meio.
    linhas_de_banner = [l for l in linhas if l.count("█") > 5]
    assert linhas_de_banner, "nenhuma linha de banner encontrada no SVG exportado"
    assert all(len(l) > 40 for l in linhas_de_banner), linhas_de_banner
