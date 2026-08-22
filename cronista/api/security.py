"""Hash de senha e JWT. Ver docs/10-autenticacao.md e ADR-0011.

Usuário único: não há tabela de usuários. A credencial vem de variável de
ambiente (AUTH_USERNAME / AUTH_PASSWORD_HASH); o token carrega apenas o tipo
(access ou refresh) e a expiração.
"""

from __future__ import annotations

import time
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cronista.core.config import Settings

settings = Settings()
_hasher = PasswordHasher()
_bearer_scheme = HTTPBearer(auto_error=False)

TokenType = Literal["access", "refresh"]


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _issue_token(token_type: TokenType, *, seconds_valid: int) -> str:
    now = int(time.time())
    payload = {
        "sub": settings.auth_username,
        "type": token_type,
        "iat": now,
        "exp": now + seconds_valid,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def issue_access_token() -> str:
    return _issue_token("access", seconds_valid=settings.access_token_minutes * 60)


def issue_refresh_token() -> str:
    return _issue_token("refresh", seconds_valid=settings.refresh_token_days * 86400)


def issue_service_token(days_valid: int = 3650) -> str:
    """Token de vida longa pro worker chamar POST /summarize sozinho
    (docs/07-arquitetura.md §3-4.3, "resumo automático"). Continua tipo
    "access" de propósito -- valida contra `require_access_token` sem
    precisar de um tipo de token novo nem mudar nada na dependência do
    FastAPI. Gerado uma vez com scripts/mint_worker_token.py, guardado
    como segredo do worker (WORKER_SERVICE_TOKEN), não é login de
    usuário nem fica preso a uma sessão."""
    return _issue_token("access", seconds_valid=days_valid * 86400)


def _decode(token: str, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido.")
    if payload.get("type") != expected_type:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tipo de token incorreto.")
    return payload


def decode_refresh_token(token: str) -> dict:
    return _decode(token, "refresh")


def require_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """Dependência FastAPI: exige Bearer token de acesso válido (RN-10).

    Uso nos routers de negócio (a partir da Fase 2):
        router = APIRouter(dependencies=[Depends(require_access_token)])
    """
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ausente.")
    return _decode(credentials.credentials, "access")
