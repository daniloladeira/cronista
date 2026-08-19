"""Testes de `cronista reprocessar <id>` (UC-05, RF-15). A chamada à API
é mockada -- o comportamento do endpoint em si é coberto em
tests/test_reprocessar.py."""

from __future__ import annotations

from typer.testing import CliRunner

from cronista.client import api_client, cli

runner = CliRunner()


def test_reprocessar_sucesso(monkeypatch):
    monkeypatch.setattr(api_client, "reprocessar", lambda meeting_id: {"status": "recorded"})

    result = runner.invoke(cli.app, ["reprocessar", "algum-id"])

    assert result.exit_code == 0
    assert "reprocessamento" in result.stdout.lower()


def test_reprocessar_reuniao_inexistente_sai_com_codigo_1(monkeypatch):
    def fake(meeting_id):
        raise api_client.ApiError("Reunião não encontrada.", status_code=404)

    monkeypatch.setattr(api_client, "reprocessar", fake)

    result = runner.invoke(cli.app, ["reprocessar", "algum-id"])

    assert result.exit_code == 1


def test_reprocessar_estado_incompativel_sai_com_codigo_5(monkeypatch):
    def fake(meeting_id):
        raise api_client.ApiError("Reunião em 'transcribing' não pode ser reprocessada.", status_code=409)

    monkeypatch.setattr(api_client, "reprocessar", fake)

    result = runner.invoke(cli.app, ["reprocessar", "algum-id"])

    assert result.exit_code == 5


def test_reprocessar_sem_autenticacao_sai_com_codigo_2(monkeypatch):
    def fake(meeting_id):
        raise api_client.ApiError("Não autenticado.", status_code=401)

    monkeypatch.setattr(api_client, "reprocessar", fake)

    result = runner.invoke(cli.app, ["reprocessar", "algum-id"])

    assert result.exit_code == 2


def test_reprocessar_api_fora_do_ar_sai_com_codigo_3(monkeypatch):
    def fake(meeting_id):
        raise api_client.ApiError("Não foi possível conectar à API.")

    monkeypatch.setattr(api_client, "reprocessar", fake)

    result = runner.invoke(cli.app, ["reprocessar", "algum-id"])

    assert result.exit_code == 3
