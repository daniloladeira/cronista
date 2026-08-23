"""Testes de PATCH /meetings/{id} (UC-07)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from cronista.core.models import Meeting


def _meeting(db_session, **overrides) -> Meeting:
    defaults = dict(
        id=uuid.uuid4(),
        title="Reunião de teste",
        source="capture",
        host="maquina-de-teste",
        audio_dir="2026-08-23_teste",
        expected_tracks=2,
        status="recorded",
        started_at=datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    meeting = Meeting(**defaults)
    db_session.add(meeting)
    db_session.commit()
    return meeting


def test_rename_sem_token_e_recusado(client, db_session):
    meeting = _meeting(db_session)

    resp = client.patch(f"/api/v1/meetings/{meeting.id}", json={"title": "Novo título"})

    assert resp.status_code == 401


def test_rename_reuniao_inexistente_e_404(client, auth_headers):
    resp = client.patch(
        f"/api/v1/meetings/{uuid.uuid4()}", json={"title": "Novo título"}, headers=auth_headers
    )

    assert resp.status_code == 404


@pytest.mark.parametrize(
    "status", ["registering", "recorded", "transcribing", "transcribed", "summarized", "transcription_failed"]
)
def test_rename_muda_o_titulo_em_qualquer_estado(client, auth_headers, db_session, status):
    meeting = _meeting(db_session, status=status)

    resp = client.patch(
        f"/api/v1/meetings/{meeting.id}", json={"title": "Título renomeado"}, headers=auth_headers
    )

    assert resp.status_code == 200
    assert resp.json()["title"] == "Título renomeado"
    db_session.refresh(meeting)
    assert meeting.title == "Título renomeado"
