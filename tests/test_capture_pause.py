"""Testes de pausar/retomar (RF-31, RN-11) sem depender de hardware de áudio.

`_FakeDevice` substitui o dispositivo WASAPI real: o que se testa aqui é
que _TrackRecorder libera e reabre o arquivo corretamente, não a captura
em si (isso exige hardware e não é testável em CI/máquina qualquer).
"""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest
import soundfile as sf

from cronista.client import capture

_POLL_TIMEOUT = 3.0
_POLL_INTERVAL = 0.02


def _wait_until(predicate, timeout: float = _POLL_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(_POLL_INTERVAL)
    assert predicate(), f"condição não satisfeita em {timeout}s"


class _FakeRecorderCtx:
    def __enter__(self) -> "_FakeRecorderCtx":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def record(self, numframes: int) -> np.ndarray:
        time.sleep(0.005)  # simula o tempo real de um bloco, sem esperar 100ms de verdade
        return np.zeros((numframes, capture.CHANNELS), dtype=np.float32)


class _FakeDevice:
    name = "fake"

    def recorder(self, samplerate: int, channels: int) -> _FakeRecorderCtx:
        return _FakeRecorderCtx()


class _FailsOnReopenDevice:
    """Grava normalmente na primeira abertura; qualquer reabertura (retomada
    de pausa) levanta, simulando FE-05 (dispositivo sumiu durante a pausa)."""

    name = "falha-ao-retomar"

    def __init__(self) -> None:
        self._opened_once = False

    def recorder(self, samplerate: int, channels: int) -> _FakeRecorderCtx:
        if not self._opened_once:
            self._opened_once = True
            return _FakeRecorderCtx()
        raise RuntimeError("dispositivo removido durante a pausa")


def test_pausar_libera_arquivo_e_retomar_acrescenta_sem_truncar(tmp_path):
    path = tmp_path / "voce.wav"
    stop_event = threading.Event()
    pause_event = threading.Event()

    thread = capture._TrackRecorder(
        "voce", _FakeDevice(), path, stop_event, pause_event, on_level=None
    )
    thread.start()
    try:
        # Observa o contador em memória da própria thread (_frames_written),
        # não o arquivo em disco: abrir o WAV por fora pra ler enquanto a
        # thread pode estar no meio de reabri-lo em 'r+' cria disputa real
        # de lock no Windows e trava a escrita — não é bug de produção
        # (nada mais abre o arquivo durante uma gravação de verdade), é
        # artefato do próprio teste tentando espiar.
        _wait_until(lambda: thread._frames_written > 0)

        pause_event.set()
        time.sleep(0.1)  # margem pro loop notar a pausa e fechar o arquivo
        assert thread.error is None

        frames_pausado = thread._frames_written
        time.sleep(0.1)
        assert thread._frames_written == frames_pausado  # nada escrito durante a pausa

        pause_event.clear()
        _wait_until(lambda: thread._frames_written > frames_pausado)  # acrescentou, não truncou
        assert thread.error is None
    finally:
        stop_event.set()
        thread.join(timeout=2)

    assert not thread.is_alive()
    assert thread.error is None
    # Só agora, com a thread parada de vez, confere em disco: o header final
    # reflete TUDO que foi escrito nas duas aberturas ('w' + 'r+'), prova de
    # que reabrir realmente acrescentou em vez de recomeçar do zero.
    assert sf.info(path).frames == thread._frames_written


def test_falha_ao_retomar_marca_erro_sem_travar_a_thread(tmp_path):
    path = tmp_path / "voce.wav"
    stop_event = threading.Event()
    pause_event = threading.Event()

    thread = capture._TrackRecorder(
        "voce", _FailsOnReopenDevice(), path, stop_event, pause_event, on_level=None
    )
    thread.start()
    time.sleep(0.1)
    pause_event.set()
    time.sleep(0.1)
    pause_event.clear()  # a próxima reabertura do device levanta

    thread.join(timeout=2)

    assert not thread.is_alive()
    assert thread.error is not None
    assert sf.info(path).frames > 0  # o que já tinha sido gravado continua íntegro


def test_get_input_device_nome_explicito_e_falha_propaga_device_error(monkeypatch):
    # FA-02: o usuário pediu um dispositivo específico que não existe — erro.
    def _raise(*_args, **_kwargs):
        raise RuntimeError("sem dispositivo")

    monkeypatch.setattr(capture.sc, "get_microphone", _raise)

    with pytest.raises(capture.DeviceError):
        capture.get_input_device("Fantasma")


def test_get_input_device_sem_nome_e_sem_microfone_devolve_none(monkeypatch):
    # UC-02 FE-01: ausência de microfone é degradação esperada, não erro —
    # cronista rec segue só com a trilha 'outros' (quem chama avisa disso).
    def _raise(*_args, **_kwargs):
        raise RuntimeError("sem dispositivo")

    monkeypatch.setattr(capture.sc, "default_microphone", _raise)

    assert capture.get_input_device(None) is None


def test_get_output_device_por_nome_usa_get_speaker(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(capture.sc, "get_speaker", lambda name: sentinel)

    assert capture.get_output_device("Fone") is sentinel


def test_get_input_device_sem_nome_usa_padrao_do_sistema(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(capture.sc, "default_microphone", lambda: sentinel)

    assert capture.get_input_device(None) is sentinel


def test_get_output_device_nome_inexistente_e_device_error(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise RuntimeError("sem dispositivo")

    monkeypatch.setattr(capture.sc, "get_speaker", _raise)

    with pytest.raises(capture.DeviceError):
        capture.get_output_device("Fantasma")


def test_get_loopback_device_indisponivel_e_device_error(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise RuntimeError("sem loopback")

    monkeypatch.setattr(capture.sc, "get_microphone", _raise)
    speaker = capture.DeviceInfo(name="Alto-falantes", is_default=True)

    with pytest.raises(capture.DeviceError):
        capture.get_loopback_device(speaker)


def test_get_loopback_device_disponivel_devolve_o_microfone_de_loopback(monkeypatch):
    sentinel = object()
    recebido = {}

    def _get_microphone(name, include_loopback):
        recebido["name"] = name
        recebido["include_loopback"] = include_loopback
        return sentinel

    monkeypatch.setattr(capture.sc, "get_microphone", _get_microphone)
    speaker = capture.DeviceInfo(name="Alto-falantes", is_default=True)

    assert capture.get_loopback_device(speaker) is sentinel
    assert recebido == {"name": "Alto-falantes", "include_loopback": True}
