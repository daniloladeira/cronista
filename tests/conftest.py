"""Fixtures compartilhadas.

Banco de teste: cronista_test, separado do banco de desenvolvimento no mesmo
container (docs/14-plano-de-testes.md §7). Cada teste roda dentro de uma
transação que é desfeita ao final, então a ordem de execução não importa e
nada precisa ser limpo manualmente.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from cronista.api import security
from cronista.api.main import app
from cronista.api.routes.meetings import get_data_root
from cronista.core.config import DatabaseSettings
from cronista.core.db import get_db
from cronista.core.models import Base

TEST_USERNAME = "teste"
TEST_PASSWORD = "senha-de-teste"


def _test_database_url() -> str:
    dev_url = DatabaseSettings().database_url
    base, _, _ = dev_url.rpartition("/")
    return f"{base}/cronista_test"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(_test_database_url())
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session, tmp_path) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # data_root aponta pro diretório temporário do teste, não pro real do
    # usuário — register_track confere existência de arquivo, e o teste
    # não deve depender nem sujar o acervo de verdade.
    app.dependency_overrides[get_data_root] = lambda: str(tmp_path)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_data_root, None)


@pytest.fixture()
def auth_credentials(monkeypatch) -> None:
    monkeypatch.setattr(security.settings, "auth_username", TEST_USERNAME)
    monkeypatch.setattr(
        security.settings, "auth_password_hash", PasswordHasher().hash(TEST_PASSWORD)
    )
    # 32+ bytes para não disparar InsecureKeyLengthWarning do PyJWT (RFC 7518 §3.2).
    monkeypatch.setattr(
        security.settings, "jwt_secret", "segredo-de-teste-com-comprimento-adequado"
    )
    monkeypatch.setattr(security.settings, "access_token_minutes", 30)
    monkeypatch.setattr(security.settings, "refresh_token_days", 30)


@pytest.fixture()
def auth_headers(auth_credentials: None, client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
