"""Testes de GET /meetings/{id}/transcript (RF-21, UC-07)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from cronista.core.models import Meeting, Segment


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


def test_get_transcript_sem_token_e_recusado(client, db_session):
    meeting = _meeting(db_session)

    resp = client.get(f"/api/v1/meetings/{meeting.id}/transcript")

    assert resp.status_code == 401


def test_get_transcript_reuniao_inexistente_e_404(client, auth_headers):
    resp = client.get(f"/api/v1/meetings/{uuid.uuid4()}/transcript", headers=auth_headers)

    assert resp.status_code == 404


def test_get_transcript_sem_segmento_devolve_lista_vazia_nao_erro(client, auth_headers, db_session):
    # CT-26: reunião ainda em processamento é consultável sem erro.
    meeting = _meeting(db_session, status="recorded")

    resp = client.get(f"/api/v1/meetings/{meeting.id}/transcript", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_transcript_vem_ordenado_por_instante(client, auth_headers, db_session):
    meeting = _meeting(db_session)
    db_session.add_all(
        [
            Segment(meeting_id=meeting.id, speaker="voce", start_ms=6000, end_ms=8000, text="terceira"),
            Segment(meeting_id=meeting.id, speaker="outros", start_ms=0, end_ms=2000, text="primeira"),
            Segment(meeting_id=meeting.id, speaker="voce", start_ms=3000, end_ms=5000, text="segunda"),
        ]
    )
    db_session.commit()

    resp = client.get(f"/api/v1/meetings/{meeting.id}/transcript", headers=auth_headers)

    assert resp.status_code == 200
    corpo = resp.json()
    assert [s["text"] for s in corpo] == ["primeira", "segunda", "terceira"]
    assert corpo[0]["timestamp"] == "00:00:00"
