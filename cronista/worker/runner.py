"""Loop do worker: fila sem broker sobre `meetings.status`, ciclo de uma
reunião e recuperação de inicialização (docs/12-transcricao.md §7).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

from faster_whisper import WhisperModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from cronista.core.config import RECORDINGS_DIRNAME, WorkerSettings
from cronista.core.models import Meeting, Segment
from cronista.worker.merge import merge_tracks
from cronista.worker.transcription import transcribe_track

logger = logging.getLogger(__name__)


def recover_interrupted(session: Session) -> None:
    """CT-19: reunião presa em `transcribing` porque um worker anterior
    caiu no meio volta pra `recorded`, elegível de novo (docs/12 §7)."""
    session.execute(text("UPDATE meetings SET status = 'recorded' WHERE status = 'transcribing'"))
    session.commit()


def claim_next_meeting(session: Session) -> Meeting | None:
    """Tira uma reunião da fila com `FOR UPDATE SKIP LOCKED` — a fila é a
    própria coluna `meetings.status`, sem broker (docs/12 §7)."""
    meeting = (
        session.query(Meeting)
        .filter(Meeting.status == "recorded")
        .order_by(Meeting.started_at)
        .with_for_update(skip_locked=True)
        .limit(1)
        .one_or_none()
    )
    if meeting is None:
        return None
    meeting.status = "transcribing"
    session.commit()
    return meeting


def process_meeting(
    session: Session,
    meeting: Meeting,
    model: WhisperModel,
    settings: WorkerSettings,
) -> None:
    """Ciclo de uma reunião: transcreve cada trilha, mescla e persiste
    (docs/12 §7, passos 2 a 6). Falha em qualquer passo marca
    `transcription_failed` e preserva o áudio (RNF-R03) — nada em
    `recordings/` é tocado aqui."""
    recordings_root = Path(settings.data_root) / RECORDINGS_DIRNAME
    try:
        segments_by_speaker = {
            track.speaker: transcribe_track(
                model,
                track.absolute_path(recordings_root),
                language=settings.whisper_language,
                vocabulary=settings.whisper_vocabulary,
            )
            for track in meeting.tracks
        }
        merged = merge_tracks(segments_by_speaker)
    except Exception as exc:
        meeting.status = "transcription_failed"
        meeting.error = str(exc)
        session.commit()
        logger.exception("Falha ao transcrever reunião %s", meeting.id)
        return

    # Substitui os segmentos de uma tentativa anterior, se houver — nunca
    # acumula (docs/12 §7 passo 5, §10).
    session.query(Segment).filter(Segment.meeting_id == meeting.id).delete()
    track_by_speaker = {track.speaker: track for track in meeting.tracks}
    session.add_all(
        Segment(
            meeting_id=meeting.id,
            track_id=track_by_speaker[segment.speaker].id,
            speaker=segment.speaker,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            text=segment.text,
        )
        for segment in merged
    )
    meeting.status = "transcribed"
    meeting.error = None
    session.commit()


def run_once(session: Session, model: WhisperModel, settings: WorkerSettings) -> bool:
    """Processa uma reunião da fila, se houver. Devolve `False` quando a
    fila está vazia — quem chama decide o que fazer (dormir, parar)."""
    meeting = claim_next_meeting(session)
    if meeting is None:
        return False
    process_meeting(session, meeting, model, settings)
    return True


def run_forever(
    session_factory: Callable[[], Session],
    model: WhisperModel,
    settings: WorkerSettings,
) -> None:
    """O `enquanto verdadeiro` de docs/12-transcricao.md §7."""
    with session_factory() as session:
        recover_interrupted(session)

    while True:
        with session_factory() as session:
            processed = run_once(session, model, settings)
        if not processed:
            time.sleep(settings.worker_poll_interval_seconds)
