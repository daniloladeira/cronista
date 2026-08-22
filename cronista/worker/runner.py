"""Loop do worker: fila sem broker sobre `meetings.status`, ciclo de uma
reunião e recuperação de inicialização (docs/12-transcricao.md §7).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

import httpx2
from sqlalchemy import text
from sqlalchemy.orm import Session

from cronista.core.config import RECORDINGS_DIRNAME, WorkerSettings
from cronista.core.models import Meeting, Segment
from cronista.worker.merge import merge_tracks
from cronista.worker.model_manager import ModelManager, is_out_of_memory
from cronista.worker.transcription import transcribe_track

logger = logging.getLogger(__name__)


def recover_interrupted(session: Session) -> int:
    """CT-19: reunião presa em `transcribing` porque um worker anterior
    caiu no meio volta pra `recorded`, elegível de novo (docs/12 §7).

    Devolve quantas reuniões foram recuperadas, pra quem chama decidir se
    avisa alguém. Sem aviso nenhum quando não há nada a recuperar -- o
    silêncio é a resposta esperada na maioria das inicializações, e um
    aviso a cada partida do worker viraria ruído (mesmo espírito do
    "recovered from a crashed start" do torlink, exibido só quando
    relevante)."""
    result = session.execute(
        text("UPDATE meetings SET status = 'recorded' WHERE status = 'transcribing'")
    )
    session.commit()
    return result.rowcount


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


def _transcribe_meeting_tracks(
    meeting: Meeting,
    model_manager: ModelManager,
    settings: WorkerSettings,
    recordings_root: Path,
) -> dict[str, list]:
    def _transcrever_com(model) -> dict[str, list]:
        return {
            track.speaker: transcribe_track(
                model,
                track.absolute_path(recordings_root),
                language=settings.whisper_language,
                vocabulary=settings.whisper_vocabulary,
            )
            for track in meeting.tracks
        }

    model = model_manager.acquire()
    try:
        return _transcrever_com(model)
    except Exception as exc:
        if not is_out_of_memory(exc):
            raise
        logger.warning(
            "Falta de memória transcrevendo reunião %s; tentando de novo com %s (docs/12 §9).",
            meeting.id,
            settings.whisper_fallback_compute_type,
        )
        model = model_manager.reload_with_fallback()  # levanta FallbackExhausted se já era o fallback
        return _transcrever_com(model)


def process_meeting(
    session: Session,
    meeting: Meeting,
    model_manager: ModelManager,
    settings: WorkerSettings,
) -> None:
    """Ciclo de uma reunião: transcreve cada trilha, mescla e persiste
    (docs/12 §7, passos 2 a 6). Falha em qualquer passo marca
    `transcription_failed` e preserva o áudio (RNF-R03) — nada em
    `recordings/` é tocado aqui."""
    recordings_root = Path(settings.data_root) / RECORDINGS_DIRNAME
    try:
        segments_by_speaker = _transcribe_meeting_tracks(
            meeting, model_manager, settings, recordings_root
        )
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


def run_once(session: Session, model_manager: ModelManager, settings: WorkerSettings) -> bool:
    """Processa uma reunião da fila, se houver. Devolve `False` quando a
    fila está vazia — quem chama decide o que fazer (dormir, parar)."""
    meeting = claim_next_meeting(session)
    if meeting is None:
        return False
    process_meeting(session, meeting, model_manager, settings)
    return True


def trigger_pending_summaries(session: Session, settings: WorkerSettings) -> None:
    """Resumo automático (docs/07-arquitetura.md §3-4.3): dispara
    `POST /summarize` na API pra cada reunião `transcribed` pendente.
    Chamado só quando a fila de transcrição está vazia e o Whisper não
    está carregado (`run_forever`), pra não disputar VRAM com o LLM.

    Só pega `transcribed`, nunca `summary_failed` -- retentar sozinho a
    cada ciclo de poll (a cada `worker_poll_interval_seconds`) bombardearia
    um provedor fora do ar. Recuperar de `summary_failed` continua sendo
    `cronista resumir <id>`, pedido explícito do usuário (UC-06).

    Desligado por padrão (`worker_auto_summarize=False` ou sem token) --
    só roda de verdade quando o operador configurou os dois."""
    if not settings.worker_auto_summarize or not settings.worker_service_token:
        return

    pendentes = (
        session.query(Meeting).filter(Meeting.status == "transcribed").order_by(Meeting.started_at)
    ).all()
    for meeting in pendentes:
        try:
            resposta = httpx2.post(
                f"{settings.worker_api_base_url}/meetings/{meeting.id}/summarize",
                headers={"Authorization": f"Bearer {settings.worker_service_token}"},
                timeout=300.0,
            )
            resposta.raise_for_status()
            logger.info("Resumo automático gerado pra reunião %s.", meeting.id)
        except Exception:
            # Não propaga -- uma reunião com resumo automático falho não
            # pode travar o loop do worker nem impedir a próxima
            # transcrição. A API já marca `summary_failed` do lado dela;
            # aqui só registra, pra quem estiver acompanhando o log ver.
            logger.exception("Resumo automático falhou pra reunião %s.", meeting.id)


def run_forever(
    session_factory: Callable[[], Session],
    settings: WorkerSettings,
) -> None:
    """O `enquanto verdadeiro` de docs/12-transcricao.md §7. O modelo é
    carregado sob demanda e descarregado por ociosidade pelo
    `ModelManager` (§8) — não é mais recebido pronto de fora."""
    model_manager = ModelManager(settings)

    with session_factory() as session:
        recovered = recover_interrupted(session)
    if recovered:
        logger.info(
            "Recuperada(s) %d reunião(ões) presa(s) em 'transcribing' (worker anterior caiu no meio).",
            recovered,
        )

    while True:
        with session_factory() as session:
            processed = run_once(session, model_manager, settings)
        if not processed:
            if model_manager.release_if_idle():
                logger.info(
                    "Modelo descarregado por %ds de ociosidade (docs/12 §8).",
                    settings.whisper_idle_unload_seconds,
                )
            if not model_manager.is_loaded():
                with session_factory() as session:
                    trigger_pending_summaries(session, settings)
            time.sleep(settings.worker_poll_interval_seconds)
