"""UC-10 · Enviar trilha de áudio. Incluído por UC-03 (rec), e mais tarde
por UC-04 (importar) e UC-11 (reconciliar) — ver docs/05-detalhamento-
casos-de-uso.md.

Registra a reunião e cada trilha na API; se algo falhar, marca a
pendência local correspondente em vez de propagar erro (RN-08: o envio
nunca é pré-requisito pra gravação ter dado certo).
"""

from __future__ import annotations

from typing import Any, Literal

from cronista.client import api_client, local_state
from cronista.client.api_client import ApiError

Estado = Literal["recorded", "pendente_envio", "falha_envio"]


def register(
    meeting: dict[str, Any], tracks: list[dict[str, Any]], data_root: str
) -> Estado:
    """FP 1-5, FE-01, FE-02. `tracks_faltantes` (FE-02) inclui qualquer
    falha por trilha, seja API fora, seja 422 de referência inválida —
    UC-11 é quem decide como reagir a cada uma depois."""
    try:
        api_client.create_meeting(meeting)
    except ApiError:
        local_state.mark_pendente_envio(data_root, {**meeting, "tracks": tracks})
        return "pendente_envio"

    faltantes = []
    for track in tracks:
        try:
            api_client.register_track(meeting["id"], track)
        except ApiError:
            faltantes.append(track)

    if faltantes:
        local_state.mark_falha_envio(data_root, meeting, faltantes)
        return "falha_envio"

    local_state.clear(data_root, meeting["id"])
    return "recorded"
