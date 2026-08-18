"""Testes da tela de `cronista rec`. Ver scripts/preview_rec_screen.py (layout
de referência) e docs/17-identidade-visual-cli.md §3/§6 — o estado pausado
foi decidido com preview visual comparado com o usuário, registrado aqui.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

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
    # Relógio mutável, não uma sequência fixa de valores: desde que o
    # shimmer do banner (§7) passou a redesenhar sozinho numa thread do
    # Rich (`get_renderable`, __enter__), o número de chamadas a
    # time.monotonic() durante o `with` deixou de ser previsível — mas
    # todas elas leem o mesmo "agora" corrente, então não importa quantas
    # vezes chamam enquanto o valor não muda.
    clock = {"now": 100.0}
    monkeypatch.setattr(signal_bar.time, "monotonic", lambda: clock["now"])

    bar = _bar()
    with bar:  # segment_started_at = 100.0
        pass
    clock["now"] = 105.0
    bar.set_paused(True)  # agora = 105.0 -> active_seconds = 5.0
    assert bar._elapsed_seconds() == 5  # agora = 105.0, pausado -> congelado

    clock["now"] = 130.0
    bar.set_paused(False)  # agora = 130.0 -> segment_started_at = 130.0


def test_footer_mostra_duracao_e_dica_de_teclas():
    footer = _bar().render_footer().plain
    assert "duração" in footer
    assert "00:00" in footer
    assert "espaço" in footer.lower()
    assert "ctrl+c" in footer.lower()


def _fake_stdout(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr(signal_bar.sys, "__stdout__", fake)
    return fake


def test_entrar_no_rec_poe_titulo_gravando_na_aba(monkeypatch):
    stdout = _fake_stdout(monkeypatch)
    monkeypatch.setattr(signal_bar, "ctypes", MagicMock())

    with _bar():
        pass

    written = "".join(call.args[0] for call in stdout.write.call_args_list)
    assert "\x1b]0;gravando · Reunião Teste\x07" in written


def test_sair_do_rec_restaura_titulo_neutro(monkeypatch):
    stdout = _fake_stdout(monkeypatch)
    monkeypatch.setattr(signal_bar, "ctypes", MagicMock())

    with _bar():
        pass

    written = "".join(call.args[0] for call in stdout.write.call_args_list)
    assert written.endswith("\x1b]0;cronista\x07")


def test_pausar_troca_titulo_da_aba(monkeypatch):
    _fake_stdout(monkeypatch)
    fake_ctypes = MagicMock()
    monkeypatch.setattr(signal_bar, "ctypes", fake_ctypes)

    bar = _bar()
    bar.set_paused(True)

    fake_ctypes.windll.kernel32.SetConsoleTitleW.assert_called_with("pausado · Reunião Teste")

    bar.set_paused(False)

    fake_ctypes.windll.kernel32.SetConsoleTitleW.assert_called_with("gravando · Reunião Teste")
