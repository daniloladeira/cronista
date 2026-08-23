"""Testes de GET /meetings/{id} (RF-20, RF-22, UC-07)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from cronista.core.models import Meeting, Summary, Track


def _meeting(db_session, **overrides) -> Meeting:
    defaults = dict(
        id=uuid.uuid4(),
        title="Reunião de teste",
        source="capture",
        host="maquina-de-teste",
        audio_dir="2026-08-23_teste",
        expected_tracks=2,
        status="transcribed",
        started_at=datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    meeting = Meeting(**defaults)
    db_session.add(meeting)
    db_session.commit()
    return meeting


def test_get_meeting_sem_token_e_recusado(client, db_session):
    meeting = _meeting(db_session)

    resp = client.get(f"/api/v1/meetings/{meeting.id}")

    assert resp.status_code == 401


def test_get_meeting_inexistente_e_404(client, auth_headers):
    resp = client.get(f"/api/v1/meetings/{uuid.uuid4()}", headers=auth_headers)

    assert resp.status_code == 404


def test_get_meeting_sem_trilha_nem_resumo_devolve_listas_vazias(client, auth_headers, db_session):
    meeting = _meeting(db_session, status="recorded")

    resp = client.get(f"/api/v1/meetings/{meeting.id}", headers=auth_headers)

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["tracks"] == []
    assert corpo["summaries"] == []


def test_get_meeting_com_trilha_e_resumo_devolve_os_dois(client, auth_headers, db_session):
    meeting = _meeting(db_session)
    db_session.add(Track(meeting_id=meeting.id, speaker="voce", path="voce.wav", sample_rate=16000, channels=1))
    db_session.add(
        Summary(
            meeting_id=meeting.id,
            provider="ollama",
            model="teste",
            prompt_version="v1",
            markdown="## Pauta\nx\n\n## Decisões\nx\n\n## Pendências\nx\n\n## Pontos em aberto\nx",
        )
    )
    db_session.commit()

    resp = client.get(f"/api/v1/meetings/{meeting.id}", headers=auth_headers)

    assert resp.status_code == 200
    corpo = resp.json()
    assert len(corpo["tracks"]) == 1
    assert corpo["tracks"][0]["speaker"] == "voce"
    assert len(corpo["summaries"]) == 1
    assert corpo["summaries"][0]["provider"] == "ollama"
