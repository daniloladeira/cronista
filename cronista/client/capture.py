"""Captura de áudio: microfone e loopback em trilhas separadas.

Ver docs/12-transcricao.md §2, ADR-0001 (duas trilhas, sem diarização),
ADR-0012 (disco antes de qualquer rede) e UC-02/UC-03.
"""

from __future__ import annotations

import ctypes
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundcard as sc
import soundfile as sf

SAMPLE_RATE = 16_000  # o que o Whisper consome (docs/12-transcricao.md)
CHANNELS = 1
BLOCK_FRAMES = 1_600  # ~100ms por bloco: escrita incremental, RNF-P03
SIGNAL_THRESHOLD = 0.01  # heurística inicial; ajustar com uso real

LevelCallback = Callable[[str, float], None]

_COINIT_MULTITHREADED = 0x0


def _ensure_com_initialized() -> None:
    """COM (usado pelo soundcard via WASAPI) é inicializado por thread do
    Windows, não por processo. Sem isto, uma thread de gravação nova pode
    abrir o stream sem lançar erro nenhum e ainda assim devolver amostras
    zeradas — foi exatamente o sintoma observado gravando mic e loopback em
    threads separadas. Seguro chamar mesmo se a thread já estiver
    inicializada com outro modelo: o retorno de erro é ignorado de
    propósito, o mesmo tratamento que o próprio soundcard já faz."""
    if sys.platform != "win32":
        return
    ctypes.windll.ole32.CoInitializeEx(None, _COINIT_MULTITHREADED)


@dataclass
class DeviceInfo:
    name: str
    is_default: bool


def list_input_devices() -> list[DeviceInfo]:
    default = sc.default_microphone()
    return [DeviceInfo(m.name, m.name == default.name) for m in sc.all_microphones()]


def list_output_devices() -> list[DeviceInfo]:
    default = sc.default_speaker()
    return [DeviceInfo(s.name, s.name == default.name) for s in sc.all_speakers()]


@dataclass
class TrackResult:
    speaker: str
    path: Path
    device: str
    duration_ms: int
    size_bytes: int
    had_signal: bool
    error: str | None = None


@dataclass
class RecordingResult:
    tracks: list[TrackResult] = field(default_factory=list)


class _TrackRecorder(threading.Thread):
    """Uma trilha (microfone ou loopback), gravando em thread própria."""

    def __init__(
        self,
        speaker: str,
        device: object,
        path: Path,
        stop_event: threading.Event,
        on_level: LevelCallback | None,
    ) -> None:
        super().__init__(daemon=True)
        self.speaker = speaker
        self.device = device
        self.path = path
        self.stop_event = stop_event
        self.on_level = on_level
        self.had_signal = False
        self.error: str | None = None
        self._frames_written = 0

    def run(self) -> None:
        _ensure_com_initialized()
        try:
            with sf.SoundFile(
                self.path,
                mode="w",
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                subtype="PCM_16",
            ) as wav:
                with self.device.recorder(
                    samplerate=SAMPLE_RATE, channels=CHANNELS
                ) as rec:
                    while not self.stop_event.is_set():
                        block = rec.record(numframes=BLOCK_FRAMES)
                        wav.write(block)
                        self._frames_written += len(block)
                        peak = float(np.abs(block).max()) if len(block) else 0.0
                        if peak > SIGNAL_THRESHOLD:
                            self.had_signal = True
                        if self.on_level is not None:
                            self.on_level(self.speaker, min(peak, 1.0))
        except Exception as exc:  # noqa: BLE001 — UC-03 FE-02: dispositivo cai no meio
            self.error = str(exc)

    @property
    def duration_ms(self) -> int:
        return int(self._frames_written / SAMPLE_RATE * 1000)


def record(
    output_dir: Path,
    mic_device: object | None = None,
    speaker_device: object | None = None,
    stop_event: threading.Event | None = None,
    on_level: LevelCallback | None = None,
) -> RecordingResult:
    """Grava as duas trilhas até stop_event ser sinalizado, ou até Ctrl+C.

    RN-08: os arquivos são escritos em disco local; nenhuma chamada de rede
    acontece aqui. Se uma trilha falhar no meio (dispositivo removido), a
    outra continua (UC-03, FE-02). Ctrl+C é caminho de sucesso, não erro:
    a função retorna normalmente com o que foi gravado até então.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stop_event = stop_event or threading.Event()

    mic = mic_device or sc.default_microphone()
    speaker = speaker_device or sc.default_speaker()
    loopback = sc.get_microphone(speaker.name, include_loopback=True)

    voce = _TrackRecorder("voce", mic, output_dir / "voce.wav", stop_event, on_level)
    outros = _TrackRecorder(
        "outros", loopback, output_dir / "outros.wav", stop_event, on_level
    )

    voce.start()
    outros.start()

    try:
        # join() com timeout, em loop: um join() simples não é interrompido
        # de forma confiável por Ctrl+C em todas as plataformas.
        while voce.is_alive() or outros.is_alive():
            voce.join(timeout=0.2)
            outros.join(timeout=0.2)
    except KeyboardInterrupt:
        stop_event.set()
        voce.join()
        outros.join()

    result = RecordingResult()
    for thread in (voce, outros):
        stat = thread.path.stat() if thread.path.exists() else None
        result.tracks.append(
            TrackResult(
                speaker=thread.speaker,
                path=thread.path,
                device=thread.device.name,
                duration_ms=thread.duration_ms,
                size_bytes=stat.st_size if stat else 0,
                had_signal=thread.had_signal,
                error=thread.error,
            )
        )
    return result
