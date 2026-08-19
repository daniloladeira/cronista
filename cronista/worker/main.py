"""Ponto de entrada do worker de transcrição. Ver docs/12-transcricao.md §7."""

from __future__ import annotations

import logging

from cronista.core.config import WorkerSettings
from cronista.core.db import SessionLocal
from cronista.worker.runner import run_forever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if __name__ == "__main__":
    run_forever(SessionLocal, WorkerSettings())
