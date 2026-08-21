"""Testes do banner de abertura em `cronista` sem comando (docs/17-identidade-visual-cli.md §3, §7).
`_usuario_logado` mora em `session_info.py` agora (compartilhado com o
menu navegável) -- testado em tests/test_session_info.py."""

from __future__ import annotations

from typer.testing import CliRunner

from cronista.client import cli, session_info

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


def test_tela_mostra_usuario_e_maquina(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    monkeypatch.setattr(session_info, "usuario_logado", lambda: "cronista")
    monkeypatch.setattr(session_info.socket, "gethostname", lambda: "maquina-de-teste")

    result = runner.invoke(cli.app, [])

    assert "cronista · maquina-de-teste" in result.stdout.replace("\n", "")
