"""Testes de `cronista` sem comando, em terminal interativo (ADR-0017).

`home.py` foi apagado -- o antigo dispatch pós-menu (escolheu X, roda a
função X) não existe mais: quem decide o que rodar depois de "Gravar"/
"Sincronizar"/"Login" é o próprio subprocess Python que o cronista-tui
invoca (`pythonBridge.js`), não este callback. O que sobra pra testar
aqui, com `cronista_tui.run` mockado (não dá pra rodar Node de verdade
num teste unitário): abre o cronista-tui em terminal interativo, e
Node/dependência ausente vira erro claro, não traceback."""

from __future__ import annotations

from unittest.mock import MagicMock

import typer

from cronista.client import cli, cronista_tui


class _FakeConsole:
    """`Console.is_terminal` é uma property sem setter -- pra testar o
    caminho "é terminal" fora de um terminal de verdade, precisamos de
    um console falso no lugar do real."""

    is_terminal = True

    def print(self, *args: object, **kwargs: object) -> None:
        pass


def test_terminal_interativo_abre_o_cronista_tui(monkeypatch):
    monkeypatch.setattr(cli, "_console", _FakeConsole())
    fake_run = MagicMock()
    monkeypatch.setattr(cronista_tui, "run", fake_run)

    cli._callback(MagicMock(invoked_subcommand=None))

    fake_run.assert_called_once_with()


def test_cronista_tui_ausente_sai_com_erro_claro(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_console", _FakeConsole())

    def _falha():
        raise cronista_tui.TuiError("Node.js não encontrado no PATH.")

    monkeypatch.setattr(cronista_tui, "run", _falha)

    try:
        cli._callback(MagicMock(invoked_subcommand=None))
    except typer.Exit as exc:
        assert exc.exit_code == 4
    else:
        raise AssertionError("esperava typer.Exit(code=4)")

    assert "Node.js" in capsys.readouterr().err
