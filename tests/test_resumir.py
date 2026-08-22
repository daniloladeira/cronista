"""Testes de POST /meetings/{id}/summarize (UC-06, RF-16,
docs/13-resumo.md). O BaseChatModel é mockado -- a lógica de
cronista.api.summarize já é coberta em tests/test_summarize.py; aqui só
o contrato HTTP (códigos, estado, corpo da resposta)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from cronista.api import summarize
from cronista.core.models import Meeting

_RESUMO_VALIDO = """## Pauta
Assunto único.

## Decisões
Nenhuma.

## Pendências
Nenhum.

## Pontos em aberto
Nenhum."""


class _RespostaFalsa:
    def __init__(self, content: str) -> None:
        self.content = content


class _ModeloFalso:
    def invoke(self, mensagens: list[object]) -> _RespostaFalsa:
        return _RespostaFalsa(_RESUMO_VALIDO)


def _meeting(db_session, status: str) -> Meeting:
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Reunião de teste",
        source="capture",
        host="maquina-de-teste",
        audio_dir="2026-08-22_teste",
        expected_tracks=2,
        status=status,
        started_at=datetime(2026, 8, 22, 14, 0, tzinfo=timezone.utc),
    )
    db_session.add(meeting)
    db_session.commit()
    return meeting


def test_resumir_sem_token_e_recusado(client, db_session):
    meeting = _meeting(db_session, "transcribed")

    resp = client.post(f"/api/v1/meetings/{meeting.id}/summarize")

    assert resp.status_code == 401


def test_resumir_reuniao_inexistente_e_404(client, auth_headers):
    resp = client.post(f"/api/v1/meetings/{uuid.uuid4()}/summarize", headers=auth_headers)

    assert resp.status_code == 404


@pytest.mark.parametrize("status", ["transcribed", "summarized", "summary_failed"])
def test_resumir_com_sucesso_devolve_o_resumo(client, auth_headers, db_session, monkeypatch, status):
    meeting = _meeting(db_session, status)
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: _ModeloFalso())

    resp = client.post(f"/api/v1/meetings/{meeting.id}/summarize", headers=auth_headers)

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["markdown"] == _RESUMO_VALIDO
    assert corpo["meeting_id"] == str(meeting.id)
    db_session.refresh(meeting)
    assert meeting.status == "summarized"


@pytest.mark.parametrize("status", ["registering", "recorded", "transcribing", "transcription_failed"])
def test_resumir_estado_incompativel_e_409(client, auth_headers, db_session, status):
    meeting = _meeting(db_session, status)

    resp = client.post(f"/api/v1/meetings/{meeting.id}/summarize", headers=auth_headers)

    assert resp.status_code == 409
    db_session.refresh(meeting)
    assert meeting.status == status  # não mudou nada


def test_resumir_provedor_indisponivel_e_503(client, auth_headers, db_session, monkeypatch):
    meeting = _meeting(db_session, "transcribed")

    def _modelo_que_falha(settings, provider):
        class _Falho:
            def invoke(self, mensagens):
                raise RuntimeError("connection refused")

        return _Falho()

    monkeypatch.setattr(summarize, "_modelo", _modelo_que_falha)

    resp = client.post(f"/api/v1/meetings/{meeting.id}/summarize", headers=auth_headers)

    assert resp.status_code == 503
    db_session.refresh(meeting)
    assert meeting.status == "summary_failed"
