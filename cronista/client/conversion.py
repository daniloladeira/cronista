"""Conversão de arquivo de áudio/vídeo preexistente pro formato interno
(UC-04, RN-09). Mesmo papel que `capture.py` tem pra UC-02/UC-03: aqui a
ferramenta externa é o binário `ffmpeg`/`ffprobe`, não `soundcard`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_DICA_INSTALACAO = (
    "ffmpeg não encontrado. Instale com 'winget install Gyan.FFmpeg' "
    "(Windows) ou veja https://ffmpeg.org/download.html."
)


class ConversionError(Exception):
    """Falha convertendo ou inspecionando um arquivo de áudio/vídeo (UC-04)."""


@dataclass
class ProbeResult:
    has_audio: bool
    duration_ms: int


def require_ffmpeg() -> None:
    """FE-03: ferramenta de conversão ausente."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise ConversionError(_DICA_INSTALACAO)


def probe(path: Path) -> ProbeResult:
    """Inspeciona o arquivo sem convertê-lo: existe faixa de áudio? qual a
    duração? Retorno não-zero ou JSON ilegível do ffprobe é o mesmo sinal
    de arquivo corrompido ou formato não suportado (FE-01)."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ConversionError(
            f"Não foi possível ler '{path}': formato não suportado ou arquivo "
            f"corrompido. {result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ConversionError(
            f"Não foi possível ler '{path}': saída do ffprobe inválida."
        ) from exc

    streams = data.get("streams", [])
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not has_audio:
        # FE-02: arquivo sem faixa de áudio.
        raise ConversionError(f"'{path}' não tem nenhuma faixa de áudio.")

    duration_s = data.get("format", {}).get("duration")
    duration_ms = int(float(duration_s) * 1000) if duration_s is not None else 0
    return ProbeResult(has_audio=True, duration_ms=duration_ms)


def convert_to_wav(input_path: Path, output_path: Path) -> None:
    """RN-09: WAV PCM 16 bits, 16 kHz, mono. `-vn` descarta qualquer trilha
    de vídeo (FA-01: origem em vídeo extrai só a faixa de áudio)."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        cauda = "\n".join(result.stderr.strip().splitlines()[-5:])
        raise ConversionError(f"Falha convertendo '{input_path}': {cauda}")
