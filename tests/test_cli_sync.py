"""Testes de `cronista sync` (UC-11)."""

from __future__ import annotations

from typer.testing import CliRunner

from cronista.client import cli, reconciliation

runner = CliRunner()


def test_sync_sem_pendencia_nao_produz_saida(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    monkeypatch.setattr(
        reconciliation,
        "reconcile",
        lambda data_root: {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 0},
    )

    result = runner.invoke(cli.app, ["sync"])

    assert result.exit_code == 0
    assert result.stdout.strip() == ""  # UC-11 FA-01: encerra silenciosamente


def test_sync_informa_quantas_reconciliou(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    monkeypatch.setattr(
        reconciliation,
        "reconcile",
        lambda data_root: {"reconciliadas": 2, "ainda_pendentes": 1, "inconsistentes": 0},
    )

    result = runner.invoke(cli.app, ["sync"])

    assert result.exit_code == 0
    assert "2" in result.stdout
    assert "1" in result.stdout


def test_sync_avisa_inconsistencia_no_stderr(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    monkeypatch.setattr(
        reconciliation,
        "reconcile",
        lambda data_root: {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 1},
    )

    result = runner.invoke(cli.app, ["sync"])

    assert result.exit_code == 0
    assert "1" in result.output
