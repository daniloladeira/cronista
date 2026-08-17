"""Testes da tela de `cronista rec`. Ver scripts/preview_rec_screen.py (layout
de referência) e docs/17-identidade-visual-cli.md §3/§6 — o estado pausado
foi decidido com preview visual comparado com o usuário, registrado aqui.
"""

from __future__ import annotations

from datetime import datetime

from cronista.client import signal_bar

_STARTED_AT = datetime(2026, 8, 17, 14, 32)


def _bar() -> signal_bar.SignalBar:
    return signal_bar.SignalBar("Reunião Teste", _STARTED_AT)


def _cell(grid, column: int):
    return next(iter(grid.columns[column].cells))


def test_header_mostra_titulo_e_hora_de_inicio():
    left = _cell(_bar().render_header(), 0)
    assert "Reunião Teste" in left.plain
    assert "14:32" in left.plain


def test_header_mostra_tracos_por_trilha_enquanto_grava():
    bar = _bar()
    bar.update("voce", 0.8)

    right = _cell(bar.render_header(), 1)
    assert "voce" in right.plain
    assert "outros" in right.plain
    assert "pausado" not in right.plain


def test_header_troca_traco_por_texto_pausado():
    bar = _bar()
    bar.update("voce", 0.8)
    bar.set_paused(True)

    right = _cell(bar.render_header(), 1)
    assert right.plain == "pausado"
    assert right.spans[0].style == signal_bar.PAUSADO_COLOR


def test_duracao_para_de_contar_durante_a_pausa(monkeypatch):
    bar = _bar()
    relogio = iter([100.0, 100.0, 105.0, 105.0, 130.0, 130.0])
    monkeypatch.setattr(signal_bar.time, "monotonic", lambda: next(relogio))

    with bar:  # segment_started_at = 100.0
        pass
    bar.set_paused(True)  # agora = 105.0 -> active_seconds = 5.0
    assert bar._elapsed_seconds() == 5  # agora = 105.0, pausado -> congelado

    bar.set_paused(False)  # agora = 130.0 -> segment_started_at = 130.0


def test_footer_mostra_duracao_e_dica_de_teclas():
    footer = _bar().render_footer().plain
    assert "duração" in footer
    assert "00:00" in footer
    assert "espaço" in footer.lower()
    assert "ctrl+c" in footer.lower()
