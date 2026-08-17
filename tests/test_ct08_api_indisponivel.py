"""CT-08 · API derrubada durante a gravação: áudio íntegro em disco,
pendência registrada, saída com sucesso. Ver docs/14-plano-de-testes.md
§3.2 — "o caso de teste central do sistema" (RNF-R01, RNF-R02, UC-03
FE-01, ADR-0012).

Segue o procedimento descrito na spec: grava, API cai no meio, encerra,
confere integridade e pendência, depois sobe a API e confirma que
`cronista sync` completa o registro.
"""

from __future__ import annotations

import threading
import time

import numpy as np
import soundfile as sf
from typer.testing import CliRunner

from cronista.client import api_client, capture, cli, local_state

runner = CliRunner()


class _FakeRecorderCtx:
    def __enter__(self) -> "_FakeRecorderCtx":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def record(self, numframes: int) -> np.ndarray:
        time.sleep(0.005)
        return np.full((numframes, capture.CHANNELS), 0.5, dtype=np.float32)


class _FakeDevice:
    def __init__(self, name: str) -> None:
        self.name = name

    def recorder(self, samplerate: int, channels: int) -> _FakeRecorderCtx:
        return _FakeRecorderCtx()


def test_ct08_api_derrubada_durante_gravacao(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    monkeypatch.setattr(capture, "get_input_device", lambda name=None: _FakeDevice("Mic Fake"))
    monkeypatch.setattr(
        capture, "get_output_device", lambda name=None: _FakeDevice("Speaker Fake")
    )
    monkeypatch.setattr(capture, "get_loopback_device", lambda speaker: _FakeDevice("Speaker Fake"))

    # A API está fora: qualquer tentativa de registrar a reunião falha.
    monkeypatch.setattr(
        api_client,
        "create_meeting",
        lambda payload: (_ for _ in ()).throw(api_client.ApiError("API fora")),
    )

    # Encerra a gravação como um Ctrl+C real faria, sem precisar de sinal:
    # sinaliza stop_event pouco depois de capture.record() começar a rodar.
    original_record = capture.record

    def _grava_e_encerra_logo(*args, **kwargs):
        threading.Timer(0.3, kwargs["stop_event"].set).start()
        return original_record(*args, **kwargs)

    monkeypatch.setattr(capture, "record", _grava_e_encerra_logo)

    result = runner.invoke(cli.app, ["rec", "--titulo", "Reunião CT-08"])

    # 1. Saída com sucesso — API fora não é erro (RN-08, UC-03 FE-01).
    assert result.exit_code == 0
    assert "pendente" in result.output.lower()

    # 2. Áudio íntegro em disco, reproduzível.
    audio_dirs = list((tmp_path / "recordings").iterdir())
    assert len(audio_dirs) == 1
    wavs = list(audio_dirs[0].glob("*.wav"))
    assert len(wavs) == 2
    for wav in wavs:
        info = sf.info(wav)
        assert info.frames > 0
        assert info.samplerate == capture.SAMPLE_RATE
        assert info.channels == capture.CHANNELS

    # 3. Pendência registrada localmente — o par obrigatório de FE-01 (UC-11).
    pendentes = local_state.list_pending(str(tmp_path))
    assert len(pendentes) == 1
    assert pendentes[0]["title"] == "Reunião CT-08"
    assert pendentes[0]["estado"] == "pendente_envio"
    assert len(pendentes[0]["tracks"]) == 2

    # 4. API volta: `cronista sync` completa o registro.
    monkeypatch.setattr(api_client, "create_meeting", lambda payload: {})
    monkeypatch.setattr(api_client, "register_track", lambda meeting_id, payload: {})

    sync_result = runner.invoke(cli.app, ["sync"])

    assert sync_result.exit_code == 0
    assert "reconciliada" in sync_result.output.lower()
    assert local_state.list_pending(str(tmp_path)) == []
