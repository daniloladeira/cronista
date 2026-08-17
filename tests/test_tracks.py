"""Testes de UC-10 (registro de trilha). Ver docs/14-plano-de-testes.md.

RN-08/09-api.md §1: nenhum áudio trafega pela API — o endpoint registra a
referência a um arquivo que já existe em disco, não recebe bytes.
"""

from __future__ import annotations

from pathlib import Path

from cronista.core.config import RECORDINGS_DIRNAME
from tests.test_meetings import make_payload


def _recordings_dir(tmp_path: Path, audio_dir: str) -> Path:
    return tmp_path / RECORDINGS_DIRNAME / audio_dir


def _create_meeting_and_dir(client, auth_headers, tmp_path: Path, **overrides) -> dict:
    payload = make_payload(**overrides)
    _recordings_dir(tmp_path, payload["audio_dir"]).mkdir(parents=True, exist_ok=True)
    resp = client.post("/api/v1/meetings", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return payload


def _track_payload(**overrides: object) -> dict:
    payload = {
        "speaker": "voce",
        "path": "voce.wav",
        "sample_rate": 16000,
        "channels": 1,
        "duration_ms": 60000,
        "size_bytes": 1_920_000,
        "device": "Microfone de teste",
    }
    payload.update(overrides)
    return payload


def test_registrar_trilha_sem_token_e_recusado(client, auth_headers, tmp_path):
    meeting = _create_meeting_and_dir(client, auth_headers, tmp_path)
    resp = client.post(f"/api/v1/meetings/{meeting['id']}/tracks", json=_track_payload())
    assert resp.status_code == 401


def test_registrar_trilha_para_reuniao_inexistente_e_404(client, auth_headers):
    import uuid

    resp = client.post(
        f"/api/v1/meetings/{uuid.uuid4()}/tracks",
        json=_track_payload(),
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_registrar_trilha_sem_arquivo_no_disco_e_422(client, auth_headers, tmp_path):
    meeting = _create_meeting_and_dir(client, auth_headers, tmp_path)
    # Não cria o arquivo — path aponta para nada.
    resp = client.post(
        f"/api/v1/meetings/{meeting['id']}/tracks",
        json=_track_payload(path="nao-existe.wav"),
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_registrar_trilha_com_arquivo_real_e_aceita(client, auth_headers, tmp_path):
    meeting = _create_meeting_and_dir(client, auth_headers, tmp_path, expected_tracks=1)
    (_recordings_dir(tmp_path, meeting["audio_dir"]) / "voce.wav").write_bytes(
        b"conteudo-fake-de-wav"
    )

    resp = client.post(
        f"/api/v1/meetings/{meeting['id']}/tracks",
        json=_track_payload(),
        headers=auth_headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["speaker"] == "voce"
    assert body["meeting_id"] == meeting["id"]


def test_ultima_trilha_esperada_transiciona_para_recorded(client, auth_headers, tmp_path):
    meeting = _create_meeting_and_dir(client, auth_headers, tmp_path, expected_tracks=2)
    recordings = _recordings_dir(tmp_path, meeting["audio_dir"])
    (recordings / "voce.wav").write_bytes(b"fake")
    (recordings / "outros.wav").write_bytes(b"fake")

    client.post(
        f"/api/v1/meetings/{meeting['id']}/tracks",
        json=_track_payload(speaker="voce", path="voce.wav"),
        headers=auth_headers,
    )
    resp = client.post(
        f"/api/v1/meetings/{meeting['id']}/tracks",
        json=_track_payload(speaker="outros", path="outros.wav"),
        headers=auth_headers,
    )
    assert resp.status_code == 201

    listing = client.get("/api/v1/meetings", headers=auth_headers).json()
    updated = next(m for m in listing if m["id"] == meeting["id"])
    assert updated["status"] == "recorded"


def test_uma_trilha_de_duas_mantem_registering(client, auth_headers, tmp_path):
    meeting = _create_meeting_and_dir(client, auth_headers, tmp_path, expected_tracks=2)
    (_recordings_dir(tmp_path, meeting["audio_dir"]) / "voce.wav").write_bytes(b"fake")

    client.post(
        f"/api/v1/meetings/{meeting['id']}/tracks",
        json=_track_payload(speaker="voce", path="voce.wav"),
        headers=auth_headers,
    )

    listing = client.get("/api/v1/meetings", headers=auth_headers).json()
    updated = next(m for m in listing if m["id"] == meeting["id"])
    assert updated["status"] == "registering"


def test_reenviar_mesma_trilha_substitui_sem_duplicar(client, auth_headers, tmp_path):
    # UC-10, FA-01.
    meeting = _create_meeting_and_dir(client, auth_headers, tmp_path, expected_tracks=1)
    recordings = _recordings_dir(tmp_path, meeting["audio_dir"])
    (recordings / "voce.wav").write_bytes(b"fake")
    (recordings / "voce_v2.wav").write_bytes(b"fake-v2")

    first = client.post(
        f"/api/v1/meetings/{meeting['id']}/tracks",
        json=_track_payload(path="voce.wav"),
        headers=auth_headers,
    )
    second = client.post(
        f"/api/v1/meetings/{meeting['id']}/tracks",
        json=_track_payload(path="voce_v2.wav"),
        headers=auth_headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]  # mesma trilha, substituída
    assert second.json()["path"] == "voce_v2.wav"
