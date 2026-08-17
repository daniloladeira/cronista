"""Testes de UC-10 (parte de registro). Ver docs/14-plano-de-testes.md, CT-40.

Primeiro endpoint de negócio real do projeto: substitui a rota descartável
que validava CT-40 na Fase 1 (tests/test_auth.py).
"""

from __future__ import annotations

import uuid


def make_payload(**overrides: object) -> dict:
    payload = {
        "id": str(uuid.uuid4()),
        "title": "Reunião de teste",
        "source": "capture",
        "host": "maquina-de-teste",
        "audio_dir": "2026-08-17_teste",
        "expected_tracks": 2,
        "started_at": "2026-08-17T14:00:00Z",
        "ended_at": "2026-08-17T14:30:00Z",
        "duration_ms": 1_800_000,
    }
    payload.update(overrides)
    return payload


def test_criar_reuniao_sem_token_e_recusado(client):
    # CT-40 / RN-10, agora contra o contrato real da API.
    resp = client.post("/api/v1/meetings", json=make_payload())
    assert resp.status_code == 401


def test_listar_reunioes_sem_token_e_recusado(client):
    resp = client.get("/api/v1/meetings")
    assert resp.status_code == 401


def test_criar_reuniao_com_token_devolve_estado_registering(client, auth_headers):
    payload = make_payload()
    resp = client.post("/api/v1/meetings", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == payload["id"]
    assert body["status"] == "registering"
    assert body["title"] == payload["title"]
    assert body["source"] == payload["source"]
    assert body["expected_tracks"] == payload["expected_tracks"]


def test_reenviar_mesmo_id_e_idempotente(client, auth_headers):
    # UC-11: se a resposta original se perder, reenviar o mesmo id não
    # duplica a reunião.
    payload = make_payload()
    first = client.post("/api/v1/meetings", json=payload, headers=auth_headers)
    second = client.post("/api/v1/meetings", json=payload, headers=auth_headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    list_resp = client.get("/api/v1/meetings", headers=auth_headers)
    ids = [m["id"] for m in list_resp.json()]
    assert ids.count(payload["id"]) == 1


def test_reuniao_criada_aparece_na_listagem(client, auth_headers):
    payload = make_payload()
    create_resp = client.post("/api/v1/meetings", json=payload, headers=auth_headers)
    created_id = create_resp.json()["id"]

    list_resp = client.get("/api/v1/meetings", headers=auth_headers)

    assert list_resp.status_code == 200
    ids = [m["id"] for m in list_resp.json()]
    assert created_id in ids
