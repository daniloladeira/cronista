"""Índice local de reuniões pendentes. Ver docs/08-modelo-de-dados.md §2/§5.1,
UC-10 FE-01/FE-02, UC-11.

`pending.json` fica em DATA_ROOT, ao lado de `recordings/` — não dentro.
É a fonte de verdade pros estados que só existem no cliente (`pendente_envio`,
`falha_envio`); o banco não sabe que a reunião existe enquanto ela não for
registrada (RN-08), então sem este arquivo uma queda de API faria a
reunião gravada virar inencontrável.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FILENAME = "pending.json"


def _path(data_root: str | Path) -> Path:
    return Path(data_root) / _FILENAME


def _load(data_root: str | Path) -> dict[str, dict[str, Any]]:
    path = _path(data_root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(data_root: str | Path, data: dict[str, dict[str, Any]]) -> None:
    _path(data_root).write_text(json.dumps(data, indent=2), encoding="utf-8")


def mark_pendente_envio(data_root: str | Path, meeting: dict[str, Any]) -> None:
    """UC-10 FE-01: API indisponível antes de a reunião existir no banco.
    `meeting` inclui as trilhas (`tracks`), pra UC-11 reenviar tudo do zero."""
    data = _load(data_root)
    data[str(meeting["id"])] = {**meeting, "estado": "pendente_envio"}
    _save(data_root, data)


def mark_falha_envio(
    data_root: str | Path, meeting: dict[str, Any], tracks_faltantes: list[dict[str, Any]]
) -> None:
    """UC-10 FE-02: a reunião já existe no banco, faltou registrar alguma
    trilha. Distinto de pendente_envio porque UC-11 reaproveita o id
    (UC-10 FA-01) em vez de recomeçar do zero."""
    data = _load(data_root)
    data[str(meeting["id"])] = {
        **meeting,
        "estado": "falha_envio",
        "tracks_faltantes": tracks_faltantes,
    }
    _save(data_root, data)


def clear(data_root: str | Path, meeting_id: object) -> None:
    """UC-10 concluído com sucesso: a pendência, se existia, não faz mais sentido."""
    data = _load(data_root)
    if data.pop(str(meeting_id), None) is not None:
        _save(data_root, data)


def list_pending(data_root: str | Path) -> list[dict[str, Any]]:
    return list(_load(data_root).values())
