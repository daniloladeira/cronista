"""Testes de POST /meetings/{id}/transcribe (UC-05, RF-15,
docs/12-transcricao.md §10)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from cronista.core.models import Meeting


def _meeting(db_session, status: str) -> Meeting:
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Reunião de teste",
        source="capture",
        host="maquina-de-teste",
        audio_dir="2026-08-19_teste",
        expected_tracks=2,
        status=status,
        started_at=datetime(2026, 8, 19, 14, 0, tzinfo=timezone.utc),
    )
    db_session.add(meeting)
    db_session.commit()
    return meeting


def test_reprocessar_sem_token_e_recusado(client, db_session):
    meeting = _meeting(db_session, "transcription_failed")

    resp = client.post(f"/api/v1/meetings/{meeting.id}/transcribe")

    assert resp.status_code == 401


def test_reprocessar_reuniao_inexistente_e_404(client, auth_headers):
    resp = client.post(f"/api/v1/meetings/{uuid.uuid4()}/transcribe", headers=auth_headers)

    assert resp.status_code == 404


@pytest.mark.parametrize("status", ["transcription_failed", "transcribed", "summarized"])
def test_reprocessar_devolve_reuniao_pra_recorded(client, auth_headers, db_session, status):
    meeting = _meeting(db_session, status)

    resp = client.post(f"/api/v1/meetings/{meeting.id}/transcribe", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"
    db_session.refresh(meeting)
    assert meeting.status == "recorded"


@pytest.mark.parametrize("status", ["registering", "transcribing", "summary_failed", "recorded"])
def test_reprocessar_estado_incompativel_e_409(client, auth_headers, db_session, status):
    meeting = _meeting(db_session, status)

    resp = client.post(f"/api/v1/meetings/{meeting.id}/transcribe", headers=auth_headers)

    assert resp.status_code == 409
    db_session.refresh(meeting)
    assert meeting.status == status  # não mudou nada
