"""Testes de `cronista excluir` (UC-09, RF-30, CT-32). `api_client`
mockado -- o comportamento real do endpoint já é coberto em
tests/test_delete_meeting.py."""

from __future__ import annotations

from typer.testing import CliRunner

from cronista.client import api_client, cli

runner = CliRunner()

_REUNIAO = {
    "id": "1",
    "title": "Reunião de teste",
    "status": "transcribed",
    "tracks": [{"id": "t1"}],
    "summaries": [{"id": "s1"}],
}


def test_excluir_confirmado_chama_delete_meeting(monkeypatch):
    monkeypatch.setattr(api_client, "get_meeting", lambda meeting_id: _REUNIAO)
    chamado = {}
    monkeypatch.setattr(api_client, "delete_meeting", lambda meeting_id: chamado.setdefault("id", meeting_id))

    result = runner.invoke(cli.app, ["excluir", "1"], input="y\n")

    assert result.exit_code == 0
    assert chamado["id"] == "1"
    assert "removida" in result.output.lower()


def test_excluir_recusado_nao_chama_delete_meeting(monkeypatch):
    # CT-32: confirmação recusada, nada é removido -- a API nem é chamada.
    monkeypatch.setattr(api_client, "get_meeting", lambda meeting_id: _REUNIAO)
    chamou = False

    def _delete(meeting_id):
        nonlocal chamou
        chamou = True

    monkeypatch.setattr(api_client, "delete_meeting", _delete)

    result = runner.invoke(cli.app, ["excluir", "1"], input="n\n")

    assert result.exit_code == 0
    assert not chamou
    assert "nada foi removido" in result.output.lower()


def test_excluir_reuniao_inexistente_sai_com_erro(monkeypatch):
    def _falha(meeting_id):
        raise api_client.ApiError("Reunião não encontrada.", status_code=404)

    monkeypatch.setattr(api_client, "get_meeting", _falha)

    result = runner.invoke(cli.app, ["excluir", "inexistente"])

    assert result.exit_code == 3
