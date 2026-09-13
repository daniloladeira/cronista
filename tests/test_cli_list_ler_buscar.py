"""Testes do fallback não-interativo de `list`/`ler`/`buscar` (fora de
terminal, mesmo caminho que `CliRunner` sempre exercita -- o painel de
navegação em si, hoje `cronista-tui` (ADR-0017), não é testado por aqui).
Foco aqui: a API fora do ar tem que sair com mensagem e código de saída,
não um traceback cru (achado real, RNF-U02)."""

from __future__ import annotations

from typer.testing import CliRunner

from cronista.client import api_client, cli

runner = CliRunner()


def _falha(*args: object, **kwargs: object):
    raise api_client.ApiError("Não foi possível conectar à API.")


def test_list_com_api_fora_do_ar_sai_com_erro_claro(monkeypatch):
    monkeypatch.setattr(api_client, "list_meetings", _falha)

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 3
    assert "conectar" in result.output.lower()


def test_ler_com_api_fora_do_ar_sai_com_erro_claro(monkeypatch):
    monkeypatch.setattr(api_client, "get_meeting", _falha)

    result = runner.invoke(cli.app, ["ler", "algum-id"])

    assert result.exit_code == 3
    assert "conectar" in result.output.lower()


def test_buscar_com_api_fora_do_ar_sai_com_erro_claro(monkeypatch):
    monkeypatch.setattr(api_client, "search", _falha)

    result = runner.invoke(cli.app, ["buscar", "decisão"])

    assert result.exit_code == 3
    assert "conectar" in result.output.lower()


def test_list_com_sucesso_imprime_tabela(monkeypatch):
    monkeypatch.setattr(
        api_client,
        "list_meetings",
        lambda: [{"title": "Reunião A", "status": "transcribed", "started_at": "2026-08-23T10:00:00Z"}],
    )

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "Reunião A" in result.output
