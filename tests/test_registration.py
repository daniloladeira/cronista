"""Testes de UC-10 (orquestração cliente-side). Ver docs/05-detalhamento-
casos-de-uso.md, UC-10.

Não fala com a API de verdade — `api_client.create_meeting`/`register_track`
são substituídos, o alvo aqui é só a lógica de estado (FP, FE-01, FE-02).
"""

from __future__ import annotations

import pytest

from cronista.client import api_client, local_state, registration


@pytest.fixture()
def meeting() -> dict:
    return {"id": "reuniao-1", "title": "Reunião de teste"}


@pytest.fixture()
def tracks() -> list[dict]:
    return [{"speaker": "voce"}, {"speaker": "outros"}]


def test_sucesso_completo_devolve_recorded_e_limpa_pendencia(
    monkeypatch, tmp_path, meeting, tracks
):
    monkeypatch.setattr(api_client, "create_meeting", lambda payload: {})
    monkeypatch.setattr(api_client, "register_track", lambda meeting_id, payload: {})
    local_state.mark_falha_envio(tmp_path, meeting, tracks_faltantes=[])  # pendência antiga

    estado = registration.register(meeting, tracks, str(tmp_path))

    assert estado == "recorded"
    assert local_state.list_pending(tmp_path) == []


def test_api_fora_no_registro_da_reuniao_marca_pendente_envio(
    monkeypatch, tmp_path, meeting, tracks
):
    def _falha(payload):
        raise api_client.ApiError("API fora")

    monkeypatch.setattr(api_client, "create_meeting", _falha)

    estado = registration.register(meeting, tracks, str(tmp_path))

    assert estado == "pendente_envio"
    pendentes = local_state.list_pending(tmp_path)
    assert len(pendentes) == 1
    assert pendentes[0]["estado"] == "pendente_envio"
    assert pendentes[0]["tracks"] == tracks


def test_falha_em_uma_trilha_marca_falha_envio_so_com_a_faltante(
    monkeypatch, tmp_path, meeting, tracks
):
    monkeypatch.setattr(api_client, "create_meeting", lambda payload: {})

    def _register_track(meeting_id, payload):
        if payload["speaker"] == "outros":
            raise api_client.ApiError("422")
        return {}

    monkeypatch.setattr(api_client, "register_track", _register_track)

    estado = registration.register(meeting, tracks, str(tmp_path))

    assert estado == "falha_envio"
    entry = local_state.list_pending(tmp_path)[0]
    assert entry["tracks_faltantes"] == [{"speaker": "outros"}]
