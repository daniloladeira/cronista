"""Configuração do cliente -- api_base_url/data_root do .env, sem
pydantic_settings (o import da lib sozinha custa ~1,7s, pago a cada
processo Python que o cronista-tui spawna; API/worker continuam com
pydantic_settings em cronista/core/config.py, processos de vida longa)."""

from __future__ import annotations

import os
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for linha in path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        values[chave.strip()] = valor.strip()
    return values


class ClientSettings:
    """Substitui `cronista.core.config.ClientSettings` do lado do cliente."""

    def __init__(self) -> None:
        do_arquivo = _read_env_file(_ENV_FILE)

        def _obrigatorio(chave: str) -> str:
            if chave in os.environ:
                return os.environ[chave]
            if chave in do_arquivo:
                return do_arquivo[chave]
            raise ValueError(f"{chave} não encontrado em variável de ambiente nem em {_ENV_FILE}")

        self.api_base_url = _obrigatorio("API_BASE_URL")
        self.data_root = _obrigatorio("DATA_ROOT")
