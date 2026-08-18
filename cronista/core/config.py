"""Configuração central, lida de variáveis de ambiente e do .env local.

Quatro classes porque nem todo processo precisa de tudo:
- migrations/env.py usa só DatabaseSettings, para não exigir credenciais de
  autenticação apenas para aplicar uma migração.
- client/ usa só ClientSettings, para não exigir segredos do servidor
  (AUTH_PASSWORD_HASH, JWT_SECRET) apenas para saber o endereço da API.
- worker/ usa só WorkerSettings: banco (fala direto com o Postgres, não com
  a API, docs/12-transcricao.md §7) e DATA_ROOT (lê as trilhas), mas não os
  segredos de autenticação da API nem nada do lado do cliente.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

# Convenção de layout em disco (docs/08-modelo-de-dados.md §2):
# DATA_ROOT/RECORDINGS_DIRNAME/<audio_dir>/<falante>.wav
# pending.json fica direto em DATA_ROOT, ao lado, não dentro daqui.
RECORDINGS_DIRNAME = "recordings"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


class ClientSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str
    data_root: str


class WorkerSettings(DatabaseSettings):
    """Configuração do worker de transcrição (docs/12-transcricao.md §8)."""

    data_root: str  # mesma raiz do cliente e da API — dentro do container, /data
    whisper_model: str
    whisper_compute_type: str
    whisper_language: str
    whisper_idle_unload_seconds: int = 300
    whisper_vocabulary: str = ""
    whisper_fallback_compute_type: str
    worker_poll_interval_seconds: int = 5


class Settings(DatabaseSettings):
    """Configuração completa, usada pela API (ADR-0011)."""

    auth_username: str
    auth_password_hash: str
    jwt_secret: str
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    data_root: str  # mesma raiz do cliente — RE-01, docs/09-api.md §1
