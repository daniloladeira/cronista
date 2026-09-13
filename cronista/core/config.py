"""Configuração central, lida de variáveis de ambiente e do .env local.
Três classes porque nem todo processo precisa de tudo: migrations/env.py
usa só DatabaseSettings, worker/ usa WorkerSettings, api/ usa Settings.

`ClientSettings` mora em `cronista/client/settings.py`, sem
pydantic_settings -- ver esse arquivo pro motivo (ADR-0017)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from cronista.core.paths import RECORDINGS_DIRNAME  # noqa: F401 -- reexportado, ver core/paths.py

# Caminho absoluto, não ".env" relativo -- um relativo resolve contra o
# diretório de trabalho no momento da chamada, o que funcionava sempre que
# tudo rodava de dentro do repo, mas quebra assim que `cronista` é instalado
# globalmente (pipx) e chamado de qualquer pasta (achado rodando de verdade
# fora do repo, não presumido).
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str


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
    # que o Whisper libera a VRAM (ModelManager.is_loaded() em runner.py).
    # Token de serviço de vida longa (scripts/mint_worker_token.py), não
    # login de usuário.
    worker_auto_summarize: bool = False
    worker_api_base_url: str = "http://host.docker.internal:8000/api/v1"
    worker_service_token: str = ""

    # Retenção de áudio (UC-09, RF-29, docs/08-modelo-de-dados.md §8).
    # Desligado por padrão -- mesmo espírito de worker_auto_summarize,
    # não presume que todo mundo quer perder qualidade/áudio original
    # sem pedir. keep_audio_days conta a partir de started_at (idade da
    # reunião, não de quando o registro foi criado).
    worker_retention_enabled: bool = False
    keep_audio_days: int = 90
    audio_policy: str = "compress"  # "compress" (Opus) ou "delete"
    # 16kbps medido: ~9,1 MB/hora (docs/08 §8), piso comum pra Opus soar
    # inteligível em voz -- abaixo disso a qualidade cai rápido demais.
    opus_bitrate: str = "16k"


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

    # Janela de contexto do Ollama, explícita -- o padrão dele (4096)
    # forçava reuniões reais a dividir em blocos sem precisar (docs/13 §5).
    # 8192 medido contra llama3.1:8b nesta GPU (RTX 4060): ~6,7GB de VRAM,
    # sem derramar pro CPU. Ajustar pra baixo se outro modelo/GPU não couber.
    ollama_num_ctx: int = 8192

    # RF-17: transcrição maior que a janela divide em blocos em vez de
    # truncar. Pareado com ollama_num_ctx acima (8192 tokens ≈ 24.000
    # caracteres em pt-BR) -- ajustar os dois juntos se um mudar.
    summary_context_chars: int = 24_000
    summary_block_overlap_segments: int = 3
