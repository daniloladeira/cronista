"""Testes de `capture.record()` ponta a ponta, sem hardware real. Ver
docs/14-plano-de-testes.md — CT-07, CT-09, CT-10, CT-42.
"""

from __future__ import annotations

import threading
import time

import numpy as np
import soundfile as sf

from cronista.client import capture


class _FakeRecorderCtx:
    def __enter__(self) -> "_FakeRecorderCtx":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def record(self, numframes: int) -> np.ndarray:
        time.sleep(0.005)
        return np.full((numframes, capture.CHANNELS), 0.3, dtype=np.float32)


class _FakeDevice:
    def __init__(self, name: str = "fake") -> None:
        self.name = name

    def recorder(self, samplerate: int, channels: int) -> _FakeRecorderCtx:
        return _FakeRecorderCtx()


class _FailsAfterNCallsRecorderCtx:
    def __init__(self, fail_after: int) -> None:
        self._count = 0
        self._fail_after = fail_after

    def __enter__(self) -> "_FailsAfterNCallsRecorderCtx":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def record(self, numframes: int) -> np.ndarray:
        self._count += 1
        if self._count > self._fail_after:
            raise RuntimeError("dispositivo removido")
        time.sleep(0.005)
        return np.zeros((numframes, capture.CHANNELS), dtype=np.float32)


class _FailsAfterNCallsDevice:
    name = "instavel"

    def __init__(self, fail_after: int) -> None:
        self._fail_after = fail_after

    def recorder(self, samplerate: int, channels: int) -> _FailsAfterNCallsRecorderCtx:
        return _FailsAfterNCallsRecorderCtx(self._fail_after)


class _FailsOnReopenDevice:
    """Abre normalmente na primeira vez; qualquer reabertura (retomada de
    pausa) levanta — simula o dispositivo ter desaparecido durante a pausa."""

    name = "falha-ao-retomar"

    def __init__(self) -> None:
        self._opened = 0

    def recorder(self, samplerate: int, channels: int) -> _FakeRecorderCtx:
        self._opened += 1
        if self._opened > 1:
            raise RuntimeError("dispositivo removido durante a pausa")
        return _FakeRecorderCtx()


def _record_em_thread(**kwargs) -> dict:
    """Roda capture.record() em background e devolve o RecordingResult
    depois de sinalizar stop_event — como o usuário apertando Ctrl+C."""
    result_holder: dict = {}

    def run() -> None:
        result_holder["result"] = capture.record(**kwargs)

    thread = threading.Thread(target=run)
    thread.start()
    return thread, result_holder


def test_record_produz_dois_wav_16khz_mono_com_duracao_coerente(tmp_path):
    # CT-07.
    output_dir = tmp_path / "reuniao"
    stop_event = threading.Event()

    thread, holder = _record_em_thread(
        output_dir=output_dir,
        mic_device=_FakeDevice("Mic"),
        loopback_device=_FakeDevice("Speaker"),
        stop_event=stop_event,
    )
    time.sleep(0.3)
    stop_event.set()
    thread.join(timeout=3)

    result = holder["result"]
    assert len(result.tracks) == 2
    for track in result.tracks:
        assert track.error is None
        info = sf.info(track.path)
        assert info.samplerate == capture.SAMPLE_RATE
        assert info.channels == capture.CHANNELS
        assert info.subtype == "PCM_16"
        # duração reportada e duração real do arquivo batem.
        assert abs(track.duration_ms - info.duration * 1000) < 200


def test_dispositivo_removido_durante_gravacao_ativa_preserva_e_continua_outra(tmp_path):
    # CT-09: não é sobre pausa — o dispositivo cai gravando de verdade.
    output_dir = tmp_path / "reuniao"
    stop_event = threading.Event()

    thread, holder = _record_em_thread(
        output_dir=output_dir,
        mic_device=_FailsAfterNCallsDevice(fail_after=3),
        loopback_device=_FakeDevice("Speaker"),
        stop_event=stop_event,
    )
    time.sleep(0.5)  # dá tempo de 'voce' cair e 'outros' seguir gravando
    stop_event.set()
    thread.join(timeout=3)

    result = holder["result"]
    voce = next(t for t in result.tracks if t.speaker == "voce")
    outros = next(t for t in result.tracks if t.speaker == "outros")

    assert voce.error is not None
    assert sf.info(voce.path).frames > 0  # preservou o que já tinha gravado

    assert outros.error is None
    assert outros.duration_ms > voce.duration_ms  # continuou depois que a outra caiu


def test_falha_de_escrita_preserva_o_que_ja_foi_gravado(tmp_path, monkeypatch):
    # CT-10: disco cheio é um caso particular de "escrever falhou" — o que
    # importa pro sistema é que o já gravado continua íntegro.
    original_write = sf.SoundFile.write
    chamadas = {"n": 0}

    def _escreve_e_depois_falha(self, data, *args, **kwargs):
        chamadas["n"] += 1
        if chamadas["n"] > 6:
            raise OSError("No space left on device")
        return original_write(self, data, *args, **kwargs)

    monkeypatch.setattr(sf.SoundFile, "write", _escreve_e_depois_falha)

    output_dir = tmp_path / "reuniao"
    stop_event = threading.Event()

    thread, holder = _record_em_thread(
        output_dir=output_dir,
        mic_device=_FakeDevice("Mic"),
        loopback_device=_FakeDevice("Speaker"),
        stop_event=stop_event,
    )
    time.sleep(0.3)
    stop_event.set()
    thread.join(timeout=3)

    result = holder["result"]
    for track in result.tracks:
        assert track.error is not None
        info = sf.info(track.path)
        assert info.frames > 0  # o que foi escrito antes da falha continua íntegro


def test_falha_ao_retomar_preserva_trilha_afetada_e_outra_continua(tmp_path):
    # CT-42.
    output_dir = tmp_path / "reuniao"
    stop_event = threading.Event()
    pause_event = threading.Event()

    thread, holder = _record_em_thread(
        output_dir=output_dir,
        mic_device=_FailsOnReopenDevice(),
        loopback_device=_FakeDevice("Speaker"),
        stop_event=stop_event,
        pause_event=pause_event,
    )
    time.sleep(0.2)
    pause_event.set()
    time.sleep(0.2)
    pause_event.clear()  # 'voce' vai falhar ao reabrir; 'outros' reabre normalmente
    time.sleep(0.3)
    stop_event.set()
    thread.join(timeout=3)

    result = holder["result"]
    voce = next(t for t in result.tracks if t.speaker == "voce")
    outros = next(t for t in result.tracks if t.speaker == "outros")

    assert voce.error is not None
    assert sf.info(voce.path).frames > 0  # preservou o que gravou antes da pausa

    assert outros.error is None
    assert sf.info(outros.path).frames > 0
