"""Testes do banner de abertura em `cronista` sem comando (docs/17-identidade-visual-cli.md §3, §7)."""

from __future__ import annotations

import jwt
from typer.testing import CliRunner

from cronista.client import cli

runner = CliRunner()


def test_mostra_banner(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 0
    assert "cronista" in result.stdout


def test_segunda_chamada_tambem_mostra_banner(monkeypatch, tmp_path):
    # Não é mais throttle de uma vez por dia -- é tela alternativa, some
    # ao sair sem poluir o histórico, então repetir é o esperado.
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))

    runner.invoke(cli.app, [])
    second = runner.invoke(cli.app, [])

    assert "cronista" in second.stdout


def test_sem_comando_mostra_resumo_minimo(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))

    result = runner.invoke(cli.app, [])

    assert "rec" in result.stdout
    assert "devices" in result.stdout
    assert "sync" in result.stdout
    assert "login" in result.stdout


def test_comando_real_nao_aciona_o_resumo_minimo(monkeypatch, tmp_path):
    # Passar um subcomando não deve imprimir o resumo nem banner extra --
    # só o próprio comando roda.
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))

    result = runner.invoke(cli.app, ["devices"])

    assert "transcreva" not in result.stdout


def test_help_explicito_continua_mostrando_ajuda_completa(monkeypatch, tmp_path):
    # `--help` é interceptado pelo Click antes do callback -- continua
    # mostrando opções e descrições, só o `cronista` sem nada que mudou.
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))

    result = runner.invoke(cli.app, ["--help"])

    assert "Usage" in result.stdout or "Uso" in result.stdout


def test_usuario_logado_sem_token_salvo(monkeypatch):
    monkeypatch.setattr(cli.token_store, "load_tokens", lambda: None)

    assert cli._usuario_logado() == "não autenticado"


def test_usuario_logado_decodifica_sub_do_token(monkeypatch):
    token = jwt.encode(
        {"sub": "cronista"}, "segredo-de-teste-com-comprimento-adequado", algorithm="HS256"
    )
    monkeypatch.setattr(
        cli.token_store,
        "load_tokens",
        lambda: {"access_token": token, "refresh_token": "x"},
    )

    assert cli._usuario_logado() == "cronista"


def test_usuario_logado_token_corrompido_nao_quebra(monkeypatch):
    monkeypatch.setattr(
        cli.token_store,
        "load_tokens",
        lambda: {"access_token": "isso-nao-e-um-jwt", "refresh_token": "x"},
    )

    assert cli._usuario_logado() == "autenticado"


def test_tela_mostra_usuario_e_maquina(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    monkeypatch.setattr(cli, "_usuario_logado", lambda: "cronista")
    monkeypatch.setattr(cli.socket, "gethostname", lambda: "maquina-de-teste")

    result = runner.invoke(cli.app, [])

    assert "cronista · maquina-de-teste" in result.stdout.replace("\n", "")
