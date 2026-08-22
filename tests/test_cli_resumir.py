"""Testes de `cronista resumir <id>` (UC-06, RF-16). A chamada à API é
mockada -- o comportamento do endpoint em si é coberto em
tests/test_resumir.py."""

from __future__ import annotations

from typer.testing import CliRunner

from cronista.client import api_client, cli

runner = CliRunner()


def test_resumir_sucesso_imprime_o_markdown(monkeypatch):
    monkeypatch.setattr(api_client, "resumir", lambda meeting_id: {"markdown": "## Pauta\nx"})

    result = runner.invoke(cli.app, ["resumir", "algum-id"])

    assert result.exit_code == 0
    assert "## Pauta" in result.stdout


def test_resumir_reuniao_inexistente_sai_com_codigo_1(monkeypatch):
    def fake(meeting_id):
        raise api_client.ApiError("Reunião não encontrada.", status_code=404)

    monkeypatch.setattr(api_client, "resumir", fake)

    result = runner.invoke(cli.app, ["resumir", "algum-id"])

    assert result.exit_code == 1


def test_resumir_estado_incompativel_sai_com_codigo_5(monkeypatch):
    def fake(meeting_id):
        raise api_client.ApiError("Reunião em 'recorded' não pode ser resumida.", status_code=409)

    monkeypatch.setattr(api_client, "resumir", fake)

    result = runner.invoke(cli.app, ["resumir", "algum-id"])

    assert result.exit_code == 5


def test_resumir_sem_autenticacao_sai_com_codigo_2(monkeypatch):
    def fake(meeting_id):
        raise api_client.ApiError("Não autenticado.", status_code=401)

    monkeypatch.setattr(api_client, "resumir", fake)

    result = runner.invoke(cli.app, ["resumir", "algum-id"])

    assert result.exit_code == 2


def test_resumir_provedor_indisponivel_sai_com_codigo_3(monkeypatch):
    def fake(meeting_id):
        raise api_client.ApiError("ollama não respondeu.", status_code=503)

    monkeypatch.setattr(api_client, "resumir", fake)

    result = runner.invoke(cli.app, ["resumir", "algum-id"])

    assert result.exit_code == 3
