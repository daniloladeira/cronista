"""Testes de UC-11 (reconciliação). Ver docs/05-detalhamento-casos-de-uso.md.

Não fala com a API de verdade — `api_client.create_meeting`/`register_track`
são substituídos, como em test_registration.py. O alvo aqui é como
`reconcile()` decide o que reenviar e o que reportar.
"""

from __future__ import annotations

import pytest

from cronista.client import api_client, local_state, reconciliation


@pytest.fixture()
def meeting() -> dict:
    return {
        "id": "reuniao-1",
        "title": "Reunião",
        "source": "capture",
        "host": "maquina-de-teste",
        "audio_dir": "2026-08-17_reuniao",
        "expected_tracks": 1,
        "started_at": "2026-08-17T14:00:00Z",
        "ended_at": "2026-08-17T14:30:00Z",
        "duration_ms": 1_800_000,
    }


def _cria_arquivo_de_trilha(tmp_path, audio_dir: str, path: str) -> None:
    from cronista.core.config import RECORDINGS_DIRNAME

    full = tmp_path / RECORDINGS_DIRNAME / audio_dir
    full.mkdir(parents=True, exist_ok=True)
    (full / path).write_bytes(b"fake")


def test_sem_pendencia_nao_faz_nada(tmp_path):
    resultado = reconciliation.reconcile(str(tmp_path))
    assert resultado == {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 0}


def test_pendente_envio_reconciliado_com_sucesso(monkeypatch, tmp_path, meeting):
    tracks = [{"speaker": "voce", "path": "voce.wav"}]
    _cria_arquivo_de_trilha(tmp_path, meeting["audio_dir"], "voce.wav")
    local_state.mark_pendente_envio(str(tmp_path), {**meeting, "tracks": tracks})

    monkeypatch.setattr(api_client, "create_meeting", lambda payload: {})
    monkeypatch.setattr(api_client, "register_track", lambda meeting_id, payload: {})

    resultado = reconciliation.reconcile(str(tmp_path))

    assert resultado == {"reconciliadas": 1, "ainda_pendentes": 0, "inconsistentes": 0}
    assert local_state.list_pending(str(tmp_path)) == []


def test_falha_envio_reenvia_so_as_trilhas_faltantes(monkeypatch, tmp_path, meeting):
    faltantes = [{"speaker": "outros", "path": "outros.wav"}]
    _cria_arquivo_de_trilha(tmp_path, meeting["audio_dir"], "outros.wav")
    local_state.mark_falha_envio(str(tmp_path), meeting, tracks_faltantes=faltantes)

    chamadas = []
    monkeypatch.setattr(api_client, "create_meeting", lambda payload: {})

    def _register_track(meeting_id, payload):
        chamadas.append(payload["speaker"])
        return {}

    monkeypatch.setattr(api_client, "register_track", _register_track)

    resultado = reconciliation.reconcile(str(tmp_path))

    assert resultado["reconciliadas"] == 1
    assert chamadas == ["outros"]  # só a que faltava, não reenvia as já confirmadas


def test_api_ainda_fora_mantem_pendencia(monkeypatch, tmp_path, meeting):
    tracks = [{"speaker": "voce", "path": "voce.wav"}]
    _cria_arquivo_de_trilha(tmp_path, meeting["audio_dir"], "voce.wav")
    local_state.mark_pendente_envio(str(tmp_path), {**meeting, "tracks": tracks})

    def _falha(payload):
        raise api_client.ApiError("API fora")

    monkeypatch.setattr(api_client, "create_meeting", _falha)

    resultado = reconciliation.reconcile(str(tmp_path))

    assert resultado == {"reconciliadas": 0, "ainda_pendentes": 1, "inconsistentes": 0}
    assert len(local_state.list_pending(str(tmp_path))) == 1  # não descarta (UC-11 FE-01)


def test_arquivo_ausente_conta_como_inconsistente_e_preserva_pendencia(
    monkeypatch, tmp_path, meeting
):
    # Não cria o arquivo em disco — UC-11 FE-02.
    tracks = [{"speaker": "voce", "path": "voce.wav"}]
    local_state.mark_pendente_envio(str(tmp_path), {**meeting, "tracks": tracks})

    chamou_api = False

    def _create(payload):
        nonlocal chamou_api
        chamou_api = True
        return {}

    monkeypatch.setattr(api_client, "create_meeting", _create)

    resultado = reconciliation.reconcile(str(tmp_path))

    assert resultado == {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 1}
    assert not chamou_api  # nem tenta: a inconsistência é detectada antes
    assert len(local_state.list_pending(str(tmp_path))) == 1  # pendência não é removida sozinha


def test_reconcilia_varias_pendencias_independentes(monkeypatch, tmp_path, meeting):
    outra = {**meeting, "id": "reuniao-2", "audio_dir": "2026-08-17_outra"}
    tracks = [{"speaker": "voce", "path": "voce.wav"}]

    _cria_arquivo_de_trilha(tmp_path, meeting["audio_dir"], "voce.wav")
    _cria_arquivo_de_trilha(tmp_path, outra["audio_dir"], "voce.wav")
    local_state.mark_pendente_envio(str(tmp_path), {**meeting, "tracks": tracks})
    local_state.mark_pendente_envio(str(tmp_path), {**outra, "tracks": tracks})

    monkeypatch.setattr(api_client, "create_meeting", lambda payload: {})
    monkeypatch.setattr(api_client, "register_track", lambda meeting_id, payload: {})

    resultado = reconciliation.reconcile(str(tmp_path))

    assert resultado["reconciliadas"] == 2
    assert local_state.list_pending(str(tmp_path)) == []
