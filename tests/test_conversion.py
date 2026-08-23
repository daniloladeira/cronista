"""Testes de `conversion.py` (UC-04). ffmpeg de verdade, fixtures
sintéticas geradas com `ffmpeg -f lavfi` -- sem binário de mídia
versionado no repo. Ver docs/14-plano-de-testes.md, Fase 6."""

from __future__ import annotations

import subprocess

import pytest
import soundfile as sf

from cronista.client import conversion


def _gerar(*args: str) -> None:
    resultado = subprocess.run(["ffmpeg", "-y", *args], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr


@pytest.fixture(scope="module")
def audio_puro(tmp_path_factory) -> "object":
    caminho = tmp_path_factory.mktemp("conversion") / "audio.mp3"
    # 44.1kHz estéreo de propósito -- prova que a conversão de verdade
    # muda pra 16kHz mono, não só copia um arquivo já nesse formato.
    _gerar(
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2:sample_rate=44100",
        "-ac", "2", str(caminho),
    )
    return caminho


@pytest.fixture(scope="module")
def video_com_audio(tmp_path_factory) -> "object":
    caminho = tmp_path_factory.mktemp("conversion") / "video.mp4"
    _gerar(
        "-f", "lavfi", "-i", "testsrc=size=64x64:rate=5:duration=1",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(caminho),
    )
    return caminho


@pytest.fixture(scope="module")
def video_sem_audio(tmp_path_factory) -> "object":
    caminho = tmp_path_factory.mktemp("conversion") / "video_mudo.mp4"
    _gerar("-f", "lavfi", "-i", "testsrc=size=64x64:rate=5:duration=1", "-an", "-c:v", "libx264", str(caminho))
    return caminho


@pytest.fixture()
def arquivo_corrompido(tmp_path) -> "object":
    caminho = tmp_path / "corrompido.mp3"
    caminho.write_bytes(b"isto nao e um arquivo de midia valido" * 10)
    return caminho


def test_require_ffmpeg_passa_quando_instalado() -> None:
    conversion.require_ffmpeg()  # não levanta -- ffmpeg está instalado nesta máquina


def test_require_ffmpeg_levanta_quando_ausente(monkeypatch: pytest.MonkeyPatch) -> None:
    # FE-03.
    monkeypatch.setattr(conversion.shutil, "which", lambda name: None)

    with pytest.raises(conversion.ConversionError, match="ffmpeg"):
        conversion.require_ffmpeg()


def test_probe_audio_puro_acha_faixa_e_duracao(audio_puro) -> None:
    resultado = conversion.probe(audio_puro)

    assert resultado.has_audio is True
    assert abs(resultado.duration_ms - 2000) < 200


def test_probe_video_sem_audio_levanta_erro(video_sem_audio) -> None:
    # FE-02.
    with pytest.raises(conversion.ConversionError, match="áudio"):
        conversion.probe(video_sem_audio)


def test_probe_arquivo_corrompido_levanta_erro(arquivo_corrompido) -> None:
    # FE-01.
    with pytest.raises(conversion.ConversionError, match="corrompido|não suportado"):
        conversion.probe(arquivo_corrompido)


def test_convert_to_wav_produz_16khz_mono_pcm16(audio_puro, tmp_path) -> None:
    saida = tmp_path / "convertido.wav"

    conversion.convert_to_wav(audio_puro, saida)

    info = sf.info(saida)
    assert info.samplerate == 16_000
    assert info.channels == 1
    assert info.subtype == "PCM_16"
    assert abs(info.duration - 2.0) < 0.3


def test_convert_to_wav_com_video_extrai_so_o_audio(video_com_audio, tmp_path) -> None:
    # FA-01: origem em vídeo, o cliente extrai só a faixa de áudio.
    saida = tmp_path / "convertido.wav"

    conversion.convert_to_wav(video_com_audio, saida)

    info = sf.info(saida)
    assert info.samplerate == 16_000
    assert info.channels == 1


def test_convert_to_wav_arquivo_corrompido_levanta_erro(arquivo_corrompido, tmp_path) -> None:
    saida = tmp_path / "convertido.wav"

    with pytest.raises(conversion.ConversionError):
        conversion.convert_to_wav(arquivo_corrompido, saida)
