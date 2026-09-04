"""Testes de DELETE /meetings/{id} (RF-30, UC-09). Ver
docs/14-plano-de-testes.md CT-31."""

from __future__ import annotations

import uuid
from pathlib import Path

from cronista.core.config import RECORDINGS_DIRNAME
from cronista.core.models import Meeting, Segment, Summary, Track
from tests.test_meetings import make_payload


def _recordings_dir(tmp_path: Path, audio_dir: str) -> Path:
    return tmp_path / RECORDINGS_DIRNAME / audio_dir


def _reuniao_completa(client, auth_headers, db_session, tmp_path: Path) -> dict:
    payload = make_payload(expected_tracks=1)
    recordings = _recordings_dir(tmp_path, payload["audio_dir"])
    recordings.mkdir(parents=True, exist_ok=True)
    (recordings / "voce.wav").write_bytes(b"fake")

    resp = client.post("/api/v1/meetings", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    client.post(
        f"/api/v1/meetings/{payload['id']}/tracks",
        json={
            "speaker": "voce",
            "path": "voce.wav",
            "sample_rate": 16000,
            "channels": 1,
            "duration_ms": 60000,
            "size_bytes": 4,
        },
        headers=auth_headers,
    )

    meeting = db_session.get(Meeting, uuid.UUID(payload["id"]))
    db_session.add(Segment(meeting_id=meeting.id, speaker="voce", start_ms=0, end_ms=2000, text="oi"))
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
    return payload


def test_delete_sem_token_e_recusado(client, db_session):
    resp = client.delete(f"/api/v1/meetings/{uuid.uuid4()}")
    assert resp.status_code == 401


def test_delete_reuniao_inexistente_e_404(client, auth_headers):
    resp = client.delete(f"/api/v1/meetings/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_remove_banco_e_arquivos(client, auth_headers, db_session, tmp_path):
    # CT-31: segmentos, resumos, trilha e arquivo de áudio, tudo some.
    payload = _reuniao_completa(client, auth_headers, db_session, tmp_path)
    diretorio = _recordings_dir(tmp_path, payload["audio_dir"])
    assert diretorio.exists()

    resp = client.delete(f"/api/v1/meetings/{payload['id']}", headers=auth_headers)

    assert resp.status_code == 204
    assert db_session.get(Meeting, uuid.UUID(payload["id"])) is None
    assert db_session.query(Track).filter(Track.meeting_id == uuid.UUID(payload["id"])).count() == 0
    assert db_session.query(Segment).filter(Segment.meeting_id == uuid.UUID(payload["id"])).count() == 0
    assert db_session.query(Summary).filter(Summary.meeting_id == uuid.UUID(payload["id"])).count() == 0
    assert not diretorio.exists()


def test_delete_com_diretorio_ja_ausente_e_idempotente(client, auth_headers, tmp_path):
    # FE-02: arquivo de áudio já ausente -- a operação prossegue e conclui.
    payload = make_payload()
    # audio_dir nunca foi criado em disco.
    resp = client.post("/api/v1/meetings", json=payload, headers=auth_headers)
    assert resp.status_code == 201

    resp = client.delete(f"/api/v1/meetings/{payload['id']}", headers=auth_headers)

    assert resp.status_code == 204


def test_delete_com_falha_ao_remover_arquivo_preserva_o_registro(
    client, auth_headers, db_session, tmp_path, monkeypatch
):
    # FE-03: falha removendo o áudio não apaga o registro do banco, pra
    # não deixar uma reunião "removida" com arquivo ainda ocupando disco.
    payload = make_payload()
    recordings = _recordings_dir(tmp_path, payload["audio_dir"])
    recordings.mkdir(parents=True, exist_ok=True)
    client.post("/api/v1/meetings", json=payload, headers=auth_headers)

    from cronista.api.routes import meetings as meetings_module

    def _falha(path):
        raise PermissionError("acesso negado")

    monkeypatch.setattr(meetings_module.shutil, "rmtree", _falha)

    resp = client.delete(f"/api/v1/meetings/{payload['id']}", headers=auth_headers)

    assert resp.status_code == 500
    assert db_session.get(Meeting, uuid.UUID(payload["id"])) is not None
