"""Configuração central, lida de variáveis de ambiente e do .env local.

Três classes porque nem todo processo precisa de tudo:
- migrations/env.py usa só DatabaseSettings, para não exigir credenciais de
  autenticação apenas para aplicar uma migração.
- client/ usa só ClientSettings, para não exigir segredos do servidor
  (AUTH_PASSWORD_HASH, JWT_SECRET) apenas para saber o endereço da API.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


class ClientSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str


class Settings(DatabaseSettings):
    """Configuração completa, usada pela API (ADR-0011)."""

    auth_username: str
    auth_password_hash: str
    jwt_secret: str
    access_token_minutes: int = 30
    refresh_token_days: int = 30
