"""Testes de UC-01. Ver docs/14-plano-de-testes.md, CT-01 a CT-04.

Não dependem de banco: usam TestClient(app) direto, não a fixture `client`
de conftest.py. CT-40 (endpoint protegido recusa sem token) migrou para
tests/test_meetings.py assim que o primeiro endpoint de negócio real passou
a existir (Fase 2).
"""

from __future__ import annotations

import time

import jwt as pyjwt
from fastapi.testclient import TestClient

from cronista.api import security
from cronista.api.main import app
from tests.conftest import TEST_PASSWORD, TEST_USERNAME


def test_login_com_credenciais_corretas_devolve_tokens(auth_credentials):
    client = TestClient(app)

    resp = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_com_senha_errada_nega_sem_distinguir_motivo(auth_credentials):
    # UC-01, FE-01: não revela se foi usuário ou senha que errou.
    client = TestClient(app)

    resp_senha_errada = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": "errada"}
    )
    resp_usuario_errado = client.post(
        "/api/v1/auth/login", json={"username": "outro", "password": TEST_PASSWORD}
    )

    assert resp_senha_errada.status_code == 401
    assert resp_usuario_errado.status_code == 401
    assert resp_senha_errada.json()["detail"] == resp_usuario_errado.json()["detail"]


def test_refresh_devolve_novo_access_token(auth_credentials):
    client = TestClient(app)

    login_resp = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_refresh_com_access_token_e_recusado(auth_credentials):
    # O tipo do token importa: um access token não serve para renovar.
    client = TestClient(app)

    login_resp = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    access_token = login_resp.json()["access_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})

    assert resp.status_code == 401


def test_refresh_com_token_expirado_e_recusado(auth_credentials):
    expired_payload = {
        "sub": TEST_USERNAME,
        "type": "refresh",
        "iat": int(time.time()) - 100,
        "exp": int(time.time()) - 1,
    }
    expired_token = pyjwt.encode(
        expired_payload, security.settings.jwt_secret, algorithm="HS256"
    )

    resp = TestClient(app).post(
        "/api/v1/auth/refresh", json={"refresh_token": expired_token}
    )

    assert resp.status_code == 401


def test_health_nao_exige_token():
    resp = TestClient(app).get("/api/v1/health")
    assert resp.status_code == 200
