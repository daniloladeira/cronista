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

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Convenção de layout em disco (docs/08-modelo-de-dados.md §2):
# DATA_ROOT/RECORDINGS_DIRNAME/<audio_dir>/<falante>.wav
# pending.json fica direto em DATA_ROOT, ao lado, não dentro daqui.
RECORDINGS_DIRNAME = "recordings"

# Caminho absoluto, não ".env" relativo -- um relativo resolve contra o
# diretório de trabalho no momento da chamada, o que funcionava sempre que
# tudo rodava de dentro do repo, mas quebra assim que `cronista` é instalado
# globalmente (pipx) e chamado de qualquer pasta (achado rodando de verdade
# fora do repo, não presumido).
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str


class ClientSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

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

    # Resumo automático (docs/07-arquitetura.md §3-4.3): só dispara depois
    # que o Whisper libera a VRAM -- ver ModelManager.is_loaded() em
    # runner.py. Desligado por padrão (False/vazio) até existir um token
    # de verdade -- worker→API é uma chamada HTTP normal (Docker Desktop
    # resolve host.docker.internal pro host Windows sem config extra,
    # medido, não presumido), autenticada com um token de serviço de
    # vida longa (scripts/mint_worker_token.py), não com login de usuário.
    worker_auto_summarize: bool = False
    worker_api_base_url: str = "http://host.docker.internal:8000/api/v1"
    worker_service_token: str = ""


class Settings(DatabaseSettings):
    """Configuração completa, usada pela API (ADR-0011)."""

    auth_username: str
    auth_password_hash: str
    jwt_secret: str
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    data_root: str  # mesma raiz do cliente — RE-01, docs/09-api.md §1

    # Resumo (ADR-0005, docs/13-resumo.md §3). ollama_model fica vazio até
    # etapa 3 medir qual modelo usar em português real -- não é escolhido
    # antes por adivinhação (mesmo espírito de docs/13 §3 e docs/12 §6).
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    # Janela de contexto do Ollama, explícita em vez de deixar o Ollama
    # escolher sozinho -- o padrão dele (4096) forçava reuniões reais de
    # ~20min a dividir em blocos sem precisar de verdade, e a divisão
    # (map-reduce) é justamente o que perdia decisão inteira na
    # consolidação (medido em 2026-08-22, docs/13-resumo.md §5). 8192
    # medido contra llama3.1:8b nesta GPU (RTX 4060, 8GB): coube na
    # VRAM (~6,7GB usados, sem derramar pro CPU -- resposta em ~11s, não
    # os 20-50x mais lento que CPU-offload causaria), com pouca folga
    # sobrando. Ajustar pra baixo se outro modelo/GPU não couber.
    ollama_num_ctx: int = 8192

    # RF-17, docs/13-resumo.md §5: transcrição maior que a janela divide
    # em blocos em vez de truncar. Heurística de caracteres, não contagem
    # exata de token -- pareado com ollama_num_ctx acima (8192 tokens ≈
    # 24.000 caracteres em pt-BR, com folga pro prompt de sistema e pra
    # resposta). "O limiar exato... dependem do modelo escolhido" (docs/13
    # §8) -- ajustar os dois juntos se o modelo ou a janela mudarem.
    summary_context_chars: int = 24_000
    summary_block_overlap_segments: int = 3
