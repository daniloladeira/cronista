"""UC-11 · Reconciliar reuniões pendentes. Ver docs/05-detalhamento-
casos-de-uso.md.

Inclui UC-10 (`registration.register`) pra cada pendência — reaproveita
o mesmo id (UC-10 FA-01) e a mesma idempotência que já protege o envio
contra duplicata, então é seguro chamar de novo mesmo que a tentativa
anterior tenha parado no meio (`falha_envio`) ou nem começado
(`pendente_envio`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from cronista.client import local_state, registration
from cronista.core.paths import RECORDINGS_DIRNAME

_MEETING_FIELDS = (
    "id",
    "title",
    "source",
    "host",
    "audio_dir",
    "expected_tracks",
    "started_at",
    "ended_at",
    "duration_ms",
)


class ReconcileResult(TypedDict):
    reconciliadas: int
    ainda_pendentes: int
    inconsistentes: int


def _tracks_com_arquivo_ausente(
    data_root: str, audio_dir: str, tracks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    base = Path(data_root) / RECORDINGS_DIRNAME / audio_dir
    return [t for t in tracks if not (base / t["path"]).is_file()]


def reconcile(data_root: str) -> ReconcileResult:
    """FP 1-5. `pendente_envio` reenvia a reunião inteira; `falha_envio`
    reenvia só as trilhas que faltaram (o resto já está confirmado na API).
    """
    resultado: ReconcileResult = {
        "reconciliadas": 0,
        "ainda_pendentes": 0,
        "inconsistentes": 0,
    }

    for entry in local_state.list_pending(data_root):
        meeting = {field: entry[field] for field in _MEETING_FIELDS}
        tracks = entry.get("tracks") or entry.get("tracks_faltantes") or []

        # FE-02: confere integridade antes de tentar de novo — não remove
        # a pendência sozinho, a remoção exige decisão humana.
        if _tracks_com_arquivo_ausente(data_root, meeting["audio_dir"], tracks):
            resultado["inconsistentes"] += 1
            continue

        estado = registration.register(meeting, tracks, data_root)
        if estado == "recorded":
            resultado["reconciliadas"] += 1
        else:
            resultado["ainda_pendentes"] += 1  # FE-01: API ainda fora, tenta de novo depois

    return resultado
