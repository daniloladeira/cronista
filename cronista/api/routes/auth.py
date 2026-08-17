"""POST /auth/login, POST /auth/refresh. Ver docs/09-api.md e UC-01."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from cronista.api.security import (
    decode_refresh_token,
    issue_access_token,
    issue_refresh_token,
    settings,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    # Usuário único (ADR-0011): não distingue usuário inexistente de senha
    # errada na mensagem de erro (UC-01, FE-01).
    valid = body.username == settings.auth_username and verify_password(
        body.password, settings.auth_password_hash
    )
    if not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário ou senha incorretos.")
    return TokenResponse(
        access_token=issue_access_token(),
        refresh_token=issue_refresh_token(),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(body: RefreshRequest) -> AccessTokenResponse:
    decode_refresh_token(body.refresh_token)  # levanta 401 se inválido ou expirado
    return AccessTokenResponse(access_token=issue_access_token())
