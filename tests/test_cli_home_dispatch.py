"""Testes do despacho pós-menu em `cronista` sem comando (ADR-0016,
extensão). O menu Textual em si é testado em tests/test_home.py -- aqui
só a lógica de "escolheu X, roda a função X de verdade" no callback do
CLI, com o HomeApp mockado (CliRunner nunca é terminal de verdade)."""

from __future__ import annotations

from unittest.mock import MagicMock

from cronista.client import cli


class _FakeConsole:
    """`Console.is_terminal` é uma property sem setter -- pra testar o
    caminho "é terminal" fora de um terminal de verdade, precisamos de
    um console falso no lugar do real."""

    is_terminal = True

    def print(self, *args: object, **kwargs: object) -> None:
        pass


def _prepara(monkeypatch, escolha: str | None) -> MagicMock:
    monkeypatch.setattr(cli, "_console", _FakeConsole())
    fake_app = MagicMock()
    fake_app.run.return_value = escolha
    monkeypatch.setattr(cli.home, "HomeApp", lambda: fake_app)
    return fake_app


def test_menu_sem_escolha_nao_roda_nada(monkeypatch):
    _prepara(monkeypatch, None)
    for nome in ("rec", "devices", "sync"):
        monkeypatch.setattr(cli, nome, MagicMock())
    do_login = MagicMock()
    monkeypatch.setattr(cli, "_do_login", do_login)

    cli._callback(MagicMock(invoked_subcommand=None))

    cli.rec.assert_not_called()
    cli.devices.assert_not_called()
    cli.sync.assert_not_called()
    do_login.assert_not_called()


def test_menu_escolhendo_devices_chama_o_comando_devices(monkeypatch):
    _prepara(monkeypatch, "devices")
    fake_devices = MagicMock()
    monkeypatch.setattr(cli, "devices", fake_devices)
    monkeypatch.setattr(cli, "rec", MagicMock())
    monkeypatch.setattr(cli, "sync", MagicMock())

    cli._callback(MagicMock(invoked_subcommand=None))

    fake_devices.assert_called_once()


def test_menu_escolhendo_rec_chama_o_comando_rec(monkeypatch):
    _prepara(monkeypatch, "rec")
    fake_rec = MagicMock()
    monkeypatch.setattr(cli, "rec", fake_rec)
    monkeypatch.setattr(cli, "devices", MagicMock())
    monkeypatch.setattr(cli, "sync", MagicMock())

    cli._callback(MagicMock(invoked_subcommand=None))

    # Regressão: rec() chamado fora do Click não resolve typer.Option(None,
    # ...) pra None sozinho -- precisa vir explícito no dispatch, senão
    # capture.get_input_device recebe o objeto OptionInfo cru (bug real,
    # reproduzido pelo usuário: "Dispositivo de entrada '<typer.models.
    # OptionInfo object...>' não encontrado").
    fake_rec.assert_called_once_with(titulo=None, mic=None, saida=None)


def test_menu_escolhendo_sync_chama_o_comando_sync(monkeypatch):
    _prepara(monkeypatch, "sync")
    fake_sync = MagicMock()
    monkeypatch.setattr(cli, "sync", fake_sync)
    monkeypatch.setattr(cli, "rec", MagicMock())
    monkeypatch.setattr(cli, "devices", MagicMock())

    cli._callback(MagicMock(invoked_subcommand=None))

    fake_sync.assert_called_once()


def test_menu_escolhendo_login_prompta_e_chama_do_login(monkeypatch):
    _prepara(monkeypatch, "login")
    do_login = MagicMock()
    monkeypatch.setattr(cli, "_do_login", do_login)
    monkeypatch.setattr("typer.prompt", lambda *a, **k: "valor")

    cli._callback(MagicMock(invoked_subcommand=None))

    do_login.assert_called_once_with("valor", "valor")
