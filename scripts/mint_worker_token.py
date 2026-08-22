"""Gera o token de serviço de vida longa que o worker usa pra chamar
POST /meetings/{id}/summarize sozinho (resumo automático,
docs/07-arquitetura.md §3-4.3). Rodar uma vez, colar a saída em
WORKER_SERVICE_TOKEN no .env. Ver cronista.api.security.issue_service_token.

    python scripts/mint_worker_token.py
"""

from __future__ import annotations

from cronista.api.security import issue_service_token

if __name__ == "__main__":
    print(issue_service_token())
