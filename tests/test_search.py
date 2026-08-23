"""Testes de GET /search (RF-23, RF-24, UC-08). Roda contra Postgres real
(mesma fixture db_session da API, docs/14-plano-de-testes.md §7) --
stemming de português (CT-27) só se prova contra o banco de verdade."""

from __future__ import annotations

import time
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


def test_search_sem_token_e_recusado(client):
    resp = client.get("/api/v1/search", params={"q": "decisão"})

    assert resp.status_code == 401


def test_search_por_decisao_encontra_decidimos_stemming_portugues(client, auth_headers, db_session):
    # CT-27: o caso central deste endpoint.
    meeting = _meeting(db_session)
    db_session.add(
        Segment(meeting_id=meeting.id, speaker="voce", start_ms=0, end_ms=2000, text="decidimos usar Postgres")
    )
    db_session.commit()

    resp = client.get("/api/v1/search", params={"q": "decisão"}, headers=auth_headers)

    assert resp.status_code == 200
    corpo = resp.json()
    assert len(corpo) == 1
    assert corpo[0]["text"] == "decidimos usar Postgres"
    assert corpo[0]["meeting_id"] == str(meeting.id)
    assert corpo[0]["speaker"] == "voce"


def test_search_sem_resultado_devolve_lista_vazia_com_200(client, auth_headers, db_session):
    # CT-29: sem resultado é lista vazia, nunca erro.
    _meeting(db_session)

    resp = client.get("/api/v1/search", params={"q": "termo-que-nao-existe-em-nenhum-lugar"}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []


def test_search_filtra_por_falante(client, auth_headers, db_session):
    meeting = _meeting(db_session)
    db_session.add_all(
        [
            Segment(meeting_id=meeting.id, speaker="voce", start_ms=0, end_ms=2000, text="decidimos migrar"),
            Segment(meeting_id=meeting.id, speaker="outros", start_ms=2000, end_ms=4000, text="decidimos parar"),
        ]
    )
    db_session.commit()

    resp = client.get("/api/v1/search", params={"q": "decisão", "speaker": "voce"}, headers=auth_headers)

    assert resp.status_code == 200
    corpo = resp.json()
    assert len(corpo) == 1
    assert corpo[0]["speaker"] == "voce"


def test_search_filtra_por_periodo(client, auth_headers, db_session):
    antiga = _meeting(db_session, id=uuid.uuid4(), started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    recente = _meeting(db_session, id=uuid.uuid4(), started_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
    db_session.add_all(
        [
            Segment(meeting_id=antiga.id, speaker="voce", start_ms=0, end_ms=2000, text="decidimos antigamente"),
            Segment(meeting_id=recente.id, speaker="voce", start_ms=0, end_ms=2000, text="decidimos recentemente"),
        ]
    )
    db_session.commit()

    resp = client.get(
        "/api/v1/search",
        params={"q": "decisão", "since": "2026-06-01T00:00:00Z"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert len(corpo) == 1
    assert corpo[0]["meeting_id"] == str(recente.id)


def test_search_responde_em_menos_de_1_segundo_com_volume_realista(client, auth_headers, db_session):
    # CT-28. 1136 segmentos é o que o banco de dev real tem hoje (medido em
    # 2026-08-22, GET /search real: ~220ms) -- 5000 dá margem sem depender
    # do estado do banco de dev, que só cresce. O índice GIN é quem faz o
    # trabalho aqui, não o volume pequeno de linhas em si.
    reunioes = [_meeting(db_session, id=uuid.uuid4()) for _ in range(20)]
    palavras = ["decidimos", "pauta", "próximo", "cliente", "prazo", "revisão", "equipe", "processo"]
    db_session.bulk_insert_mappings(
        Segment,
        [
            {
                "id": uuid.uuid4(),
                "meeting_id": reunioes[i % len(reunioes)].id,
                "speaker": "voce" if i % 2 == 0 else "outros",
                "start_ms": i * 2000,
                "end_ms": i * 2000 + 2000,
                "text": f"{palavras[i % len(palavras)]} sobre o assunto número {i}",
            }
            for i in range(5000)
        ],
    )
    db_session.commit()

    inicio = time.perf_counter()
    resp = client.get("/api/v1/search", params={"q": "decisão"}, headers=auth_headers)
    duracao = time.perf_counter() - inicio

    assert resp.status_code == 200
    assert len(resp.json()) > 0
    assert duracao < 1.0
