"""Testes de UC-10 (parte de registro). Ver docs/14-plano-de-testes.md, CT-40.

Primeiro endpoint de negócio real do projeto: substitui a rota descartável
que validava CT-40 na Fase 1 (tests/test_auth.py).
"""

from __future__ import annotations

MEETING_PAYLOAD = {
    "title": "Reunião de teste",
    "source": "capture",
    "host": "maquina-de-teste",
    "audio_dir": "2026-08-17_teste",
    "started_at": "2026-08-17T14:00:00Z",
    "ended_at": "2026-08-17T14:30:00Z",
    "duration_ms": 1_800_000,
}


def test_criar_reuniao_sem_token_e_recusado(client):
    # CT-40 / RN-10, agora contra o contrato real da API.
    resp = client.post("/api/v1/meetings", json=MEETING_PAYLOAD)
    assert resp.status_code == 401


def test_listar_reunioes_sem_token_e_recusado(client):
    resp = client.get("/api/v1/meetings")
    assert resp.status_code == 401


def test_criar_reuniao_com_token_devolve_estado_registering(client, auth_headers):
    resp = client.post("/api/v1/meetings", json=MEETING_PAYLOAD, headers=auth_headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["status"] == "registering"
    assert body["title"] == MEETING_PAYLOAD["title"]
    assert body["source"] == MEETING_PAYLOAD["source"]


def test_reuniao_criada_aparece_na_listagem(client, auth_headers):
    create_resp = client.post("/api/v1/meetings", json=MEETING_PAYLOAD, headers=auth_headers)
    created_id = create_resp.json()["id"]

    list_resp = client.get("/api/v1/meetings", headers=auth_headers)

    assert list_resp.status_code == 200
    ids = [m["id"] for m in list_resp.json()]
    assert created_id in ids
