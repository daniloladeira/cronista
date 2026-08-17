"""Testes de UC-01. Ver docs/14-plano-de-testes.md, CT-01 a CT-04 e CT-40."""

from __future__ import annotations

import time

import jwt as pyjwt
from argon2 import PasswordHasher
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from cronista.api import security
from cronista.api.main import app

TEST_USERNAME = "teste"
TEST_PASSWORD = "senha-de-teste"


def _configure_test_credentials(monkeypatch) -> None:
    monkeypatch.setattr(security.settings, "auth_username", TEST_USERNAME)
    monkeypatch.setattr(
        security.settings, "auth_password_hash", PasswordHasher().hash(TEST_PASSWORD)
    )
    # 32+ bytes para não disparar InsecureKeyLengthWarning do PyJWT (RFC 7518 §3.2).
    monkeypatch.setattr(security.settings, "jwt_secret", "segredo-de-teste-com-comprimento-adequado")
    monkeypatch.setattr(security.settings, "access_token_minutes", 30)
    monkeypatch.setattr(security.settings, "refresh_token_days", 30)


def test_login_com_credenciais_corretas_devolve_tokens(monkeypatch):
    _configure_test_credentials(monkeypatch)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_com_senha_errada_nega_sem_distinguir_motivo(monkeypatch):
    # UC-01, FE-01: não revela se foi usuário ou senha que errou.
    _configure_test_credentials(monkeypatch)
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


def test_refresh_devolve_novo_access_token(monkeypatch):
    _configure_test_credentials(monkeypatch)
    client = TestClient(app)

    login_resp = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_refresh_com_access_token_e_recusado(monkeypatch):
    # O tipo do token importa: um access token não serve para renovar.
    _configure_test_credentials(monkeypatch)
    client = TestClient(app)

    login_resp = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    access_token = login_resp.json()["access_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})

    assert resp.status_code == 401


def test_refresh_com_token_expirado_e_recusado(monkeypatch):
    _configure_test_credentials(monkeypatch)
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


def test_endpoint_protegido_recusa_sem_token(monkeypatch):
    # CT-40 / RN-10. Ainda não há endpoint de negócio (chega na Fase 2), então
    # a dependência é validada isolada, numa rota descartável só desta função.
    _configure_test_credentials(monkeypatch)

    test_router = APIRouter()

    @test_router.get("/protegido", dependencies=[Depends(security.require_access_token)])
    def _protegido() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(test_router, prefix="/api/v1/_teste")
    client = TestClient(app)

    sem_token = client.get("/api/v1/_teste/protegido")
    com_token_invalido = client.get(
        "/api/v1/_teste/protegido", headers={"Authorization": "Bearer lixo"}
    )
    login_resp = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    access_token = login_resp.json()["access_token"]
    com_token_valido = client.get(
        "/api/v1/_teste/protegido", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert sem_token.status_code == 401
    assert com_token_invalido.status_code == 401
    assert com_token_valido.status_code == 200
