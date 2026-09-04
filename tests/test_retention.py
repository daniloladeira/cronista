"""Testes de `apply_retention` (UC-09, RF-29). ffmpeg real (instalado
desde a Fase 6), fixture WAV sintética via `ffmpeg -f lavfi`, mesma
técnica de tests/test_conversion.py. Postgres real (db_session, docs/14
§7)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import soundfile as sf

from cronista.core.config import WorkerSettings
from cronista.core.models import Meeting, Segment, Summary, Track
from cronista.worker.retention import apply_retention

_ANTIGA = datetime.now(UTC) - timedelta(days=200)
_RECENTE = datetime.now(UTC) - timedelta(days=1)


@pytest.fixture()
def worker_settings(tmp_path):
    def _make(**overrides):
        defaults = dict(
            database_url="unused-aqui-a-sessao-de-teste-ja-vem-pronta",
            data_root=str(tmp_path),
            whisper_model="large-v3",
            whisper_compute_type="int8_float16",
            whisper_language="pt",
            whisper_fallback_compute_type="int8",
            keep_audio_days=90,
            audio_policy="compress",
            opus_bitrate="16k",
        )
        defaults.update(overrides)
        return WorkerSettings(**defaults)

    return _make


def _meeting(**overrides) -> Meeting:
    defaults = dict(
        title="Reunião de teste",
        source="capture",
        host="maquina-de-teste",
        audio_dir="teste",
        expected_tracks=1,
        status="transcribed",
        started_at=_ANTIGA,
    )
    defaults.update(overrides)
    return Meeting(**defaults)


def _wav_real(caminho, duracao_s: int = 2) -> None:
    resultado = subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={duracao_s}:sample_rate=16000",
            "-ac", "1", "-sample_fmt", "s16", str(caminho),
        ],
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr


def _com_trilha_real(db_session, worker_settings_factory, meeting: Meeting, audio_dir: str) -> Track:
    settings = worker_settings_factory()
    diretorio = Path(settings.data_root) / "recordings" / audio_dir
    diretorio.mkdir(parents=True, exist_ok=True)
    _wav_real(diretorio / "voce.wav")

    db_session.add(meeting)
    db_session.flush()
    track = Track(meeting_id=meeting.id, speaker="voce", path="voce.wav", sample_rate=16000, channels=1)
    db_session.add(track)
    db_session.commit()
    return track


def test_ct30_reuniao_nao_transcrita_nunca_e_tocada(db_session, worker_settings, tmp_path):
    meeting = _meeting(status="recorded", audio_dir="rec1", started_at=_ANTIGA)
    track = _com_trilha_real(db_session, worker_settings, meeting, "rec1")
    caminho = track.absolute_path(tmp_path / "recordings")
    assert caminho.exists()

    tratadas = apply_retention(db_session, worker_settings())

    assert tratadas == 0
    db_session.refresh(meeting)
    assert meeting.audio_state == "original"
    assert caminho.exists()  # arquivo original intacto


def test_reuniao_transcrita_e_velha_e_comprimida(db_session, worker_settings, tmp_path):
    meeting = _meeting(status="transcribed", audio_dir="rec2", started_at=_ANTIGA)
    track = _com_trilha_real(db_session, worker_settings, meeting, "rec2")
    db_session.add(Segment(meeting_id=meeting.id, speaker="voce", start_ms=0, end_ms=2000, text="oi"))
    db_session.add(
        Summary(
            meeting_id=meeting.id, provider="ollama", model="teste", prompt_version="v1", markdown="## Pauta\nx"
        )
    )
    db_session.commit()
    wav_original = track.absolute_path(tmp_path / "recordings")

    tratadas = apply_retention(db_session, worker_settings(keep_audio_days=90, audio_policy="compress"))

    assert tratadas == 1
    db_session.refresh(meeting)
    db_session.refresh(track)
    assert meeting.audio_state == "compressed"
    assert track.path == "voce.opus"
    assert not wav_original.exists()
    novo = track.absolute_path(tmp_path / "recordings")
    assert novo.exists()
    info = sf.info(novo)  # é mesmo um Opus decodificável, não um arquivo corrompido
    assert info.samplerate == 16000

    # RN-04: segmentos e resumo continuam intactos.
    assert db_session.query(Segment).filter(Segment.meeting_id == meeting.id).count() == 1
    assert db_session.query(Summary).filter(Summary.meeting_id == meeting.id).count() == 1


def test_reuniao_summarized_e_velha_com_policy_delete(db_session, worker_settings, tmp_path):
    meeting = _meeting(status="summarized", audio_dir="rec3", started_at=_ANTIGA)
    track = _com_trilha_real(db_session, worker_settings, meeting, "rec3")
    wav_original = track.absolute_path(tmp_path / "recordings")

    tratadas = apply_retention(db_session, worker_settings(audio_policy="delete"))

    assert tratadas == 1
    db_session.refresh(meeting)
    assert meeting.audio_state == "removed"
    assert not wav_original.exists()


def test_reuniao_transcrita_mas_recente_nao_e_tocada(db_session, worker_settings, tmp_path):
    meeting = _meeting(status="transcribed", audio_dir="rec4", started_at=_RECENTE)
    track = _com_trilha_real(db_session, worker_settings, meeting, "rec4")
    caminho = track.absolute_path(tmp_path / "recordings")

    tratadas = apply_retention(db_session, worker_settings(keep_audio_days=90))

    assert tratadas == 0
    db_session.refresh(meeting)
    assert meeting.audio_state == "original"
    assert caminho.exists()


def test_reuniao_ja_tratada_nao_processa_de_novo(db_session, worker_settings, tmp_path):
    meeting = _meeting(status="transcribed", audio_dir="rec5", started_at=_ANTIGA, audio_state="compressed")
    _com_trilha_real(db_session, worker_settings, meeting, "rec5")

    tratadas = apply_retention(db_session, worker_settings())

    assert tratadas == 0
