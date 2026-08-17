"""Captura de áudio: microfone e loopback em trilhas separadas.

Ver docs/12-transcricao.md §2, ADR-0001 (duas trilhas, sem diarização),
ADR-0012 (disco antes de qualquer rede) e UC-02/UC-03.
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundcard as sc
import soundfile as sf

if sys.platform == "win32":
    import msvcrt

SAMPLE_RATE = 16_000  # o que o Whisper consome (docs/12-transcricao.md)
CHANNELS = 1
BLOCK_FRAMES = 1_600  # ~100ms por bloco: escrita incremental, RNF-P03
SIGNAL_THRESHOLD = 0.01  # heurística inicial; ajustar com uso real
PAUSE_KEY = b" "  # RF-31: "nome exato da tecla é detalhe de implementação" (docs/11-cli.md §3)

LevelCallback = Callable[[str, float], None]
PauseCallback = Callable[[bool], None]

_COINIT_MULTITHREADED = 0x0


class DeviceError(Exception):
    """Dispositivo de áudio pedido por nome não existe, ou nenhum disponível."""


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


def get_input_device(name: str | None = None) -> object | None:
    """Nome explícito e não encontrado é erro (UC-03 FA-02: o usuário pediu
    algo que não existe). Sem nome e sem microfone algum é degradação
    esperada, não erro — devolve `None` (UC-02 FE-01): `rec` segue só com
    a trilha `outros`, e é responsabilidade de quem chama avisar disso."""
    if name is None:
        try:
            return sc.default_microphone()
        except Exception:  # noqa: BLE001 — soundcard não documenta a exceção exata
            return None
    try:
        return sc.get_microphone(name)
    except Exception as exc:  # noqa: BLE001
        raise DeviceError(f"Dispositivo de entrada '{name}' não encontrado.") from exc


def get_output_device(name: str | None = None) -> object:
    if name is None:
        try:
            return sc.default_speaker()
        except Exception as exc:  # noqa: BLE001
            raise DeviceError("Nenhum dispositivo de saída disponível.") from exc
    try:
        return sc.get_speaker(name)
    except Exception as exc:  # noqa: BLE001
        raise DeviceError(f"Dispositivo de saída '{name}' não encontrado.") from exc


def get_loopback_device(speaker: object) -> object:
    """UC-02 FE-02: sem loopback não há trilha `outros` — inviabiliza a
    gravação, então isso é erro (diferente da ausência de microfone)."""
    try:
        return sc.get_microphone(speaker.name, include_loopback=True)
    except Exception as exc:  # noqa: BLE001
        raise DeviceError(
            f"'{speaker.name}' não expõe captura de loopback. Selecione outra saída com --saida."
        ) from exc


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
        pause_event: threading.Event,
        on_level: LevelCallback | None,
    ) -> None:
        super().__init__(daemon=True)
        self.speaker = speaker
        self.device = device
        self.path = path
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.on_level = on_level
        self.had_signal = False
        self.error: str | None = None
        self._frames_written = 0

    def run(self) -> None:
        # RN-11: pausar libera o dispositivo (sai do `with` do recorder e do
        # SoundFile) em vez de só parar de escrever. Retomar reabre os dois
        # e escreve nos MESMOS arquivos, em sequência (FA-03, FE-05) — por
        # isso a reabertura usa 'r+' com seek pro fim, nunca 'w' de novo
        # (que truncaria o que já foi gravado).
        _ensure_com_initialized()
        first_open = True
        try:
            while not self.stop_event.is_set():
                if self.pause_event.is_set():
                    time.sleep(0.05)
                    continue

                # soundfile recusa samplerate/channels/subtype num arquivo já
                # existente ('r+') — só valem na criação ('w'), senão levanta
                # TypeError e a trilha morreria silenciosamente ao retomar.
                if first_open:
                    wav_ctx = sf.SoundFile(
                        self.path,
                        mode="w",
                        samplerate=SAMPLE_RATE,
                        channels=CHANNELS,
                        subtype="PCM_16",
                    )
                else:
                    wav_ctx = sf.SoundFile(self.path, mode="r+")
                with wav_ctx as wav:
                    if not first_open:
                        wav.seek(0, sf.SEEK_END)
                    first_open = False
                    with self.device.recorder(
                        samplerate=SAMPLE_RATE, channels=CHANNELS
                    ) as rec:
                        while not self.stop_event.is_set() and not self.pause_event.is_set():
                            block = rec.record(numframes=BLOCK_FRAMES)
                            wav.write(block)
                            self._frames_written += len(block)
                            peak = float(np.abs(block).max()) if len(block) else 0.0
                            if peak > SIGNAL_THRESHOLD:
                                self.had_signal = True
                            if self.on_level is not None:
                                self.on_level(self.speaker, min(peak, 1.0))
        except Exception as exc:  # noqa: BLE001 — UC-03 FE-02/FE-05: dispositivo cai,
            # ao gravar ou ao retomar de uma pausa. O que já foi escrito (fechado
            # de forma limpa a cada pausa) continua válido; só esta trilha para.
            self.error = str(exc)

    @property
    def duration_ms(self) -> int:
        return int(self._frames_written / SAMPLE_RATE * 1000)


def record(
    output_dir: Path,
    mic_device: object | None,
    loopback_device: object,
    stop_event: threading.Event | None = None,
    pause_event: threading.Event | None = None,
    on_level: LevelCallback | None = None,
    on_pause_toggle: PauseCallback | None = None,
) -> RecordingResult:
    """Grava até stop_event ser sinalizado, ou até Ctrl+C.

    `mic_device=None` grava só `outros` (UC-02 FE-01: sem microfone
    disponível, degradação esperada — quem chama já decidiu isso e avisou
    o usuário). `loopback_device` é obrigatório: sem ele não há propósito
    em gravar (UC-02 FE-02).

    RN-08: os arquivos são escritos em disco local; nenhuma chamada de rede
    acontece aqui. Se uma trilha falhar no meio (dispositivo removido), a
    outra continua (UC-03, FE-02). Ctrl+C é caminho de sucesso, não erro:
    a função retorna normalmente com o que foi gravado até então.

    `PAUSE_KEY` alterna pause_event (RF-31) — lida aqui, não em cada
    thread de trilha, pra ter um único ponto que fala com o terminal.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stop_event = stop_event or threading.Event()
    pause_event = pause_event or threading.Event()

    threads: list[_TrackRecorder] = []
    if mic_device is not None:
        threads.append(
            _TrackRecorder(
                "voce", mic_device, output_dir / "voce.wav", stop_event, pause_event, on_level
            )
        )
    threads.append(
        _TrackRecorder(
            "outros",
            loopback_device,
            output_dir / "outros.wav",
            stop_event,
            pause_event,
            on_level,
        )
    )

    for thread in threads:
        thread.start()

    try:
        # join() com timeout, em loop: um join() simples não é interrompido
        # de forma confiável por Ctrl+C em todas as plataformas. O mesmo
        # intervalo serve pra checar a tecla de pausa sem thread à parte.
        while any(thread.is_alive() for thread in threads):
            if sys.platform == "win32":
                while msvcrt.kbhit():
                    if msvcrt.getch() == PAUSE_KEY:
                        if pause_event.is_set():
                            pause_event.clear()
                        else:
                            pause_event.set()
                        if on_pause_toggle is not None:
                            on_pause_toggle(pause_event.is_set())
            for thread in threads:
                thread.join(timeout=0.1)
    except KeyboardInterrupt:
        stop_event.set()
        for thread in threads:
            thread.join()

    result = RecordingResult()
    for thread in threads:
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
