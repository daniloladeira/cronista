"""Ponto de entrada da API. Ver docs/07-arquitetura.md e docs/09-api.md."""

from __future__ import annotations

from fastapi import FastAPI

from cronista.api.routes.auth import router as auth_router
from cronista.api.routes.meetings import router as meetings_router

app = FastAPI(title="Cronista")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(meetings_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    # Sem autenticação, por design (RN-10).
    return {"status": "ok"}
