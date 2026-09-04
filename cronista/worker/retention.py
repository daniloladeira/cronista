"""Retenção de áudio por idade (UC-09, RF-29, docs/08-modelo-de-dados.md
§8). Roda no worker, não na API: acesso direto a banco e disco, mesmo
padrão de `recover_interrupted`/`claim_next_meeting` em `runner.py` --
diferente de `trigger_pending_summaries`, que precisa sair pra API por
causa da VRAM do LLM (docs/07-arquitetura.md §3), aqui não tem GPU
envolvida, não tem motivo pra sair do processo.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from cronista.core.config import RECORDINGS_DIRNAME, WorkerSettings
from cronista.core.models import Meeting, Track

logger = logging.getLogger(__name__)


def _trilha_ja_tratada(track: Track, recordings_root: Path, policy: str) -> bool:
    # Idempotência entre rodadas: se uma reunião com várias trilhas falha
    # na metade (trilha 2 quebra depois da 1 já ter sido convertida e
    # persistida), a próxima rodada não deve reprocessar a trilha 1 --
    # reconverter um .opus já pronto, ou tentar apagar um .wav que já
    # não existe mais, seria trabalho perdido na melhor hipótese e
    # corrupção na pior (ffmpeg com entrada == saída).
    if policy == "delete":
        return not track.absolute_path(recordings_root).exists()
    return track.path.endswith(".opus")


def _tratar_trilha(track: Track, recordings_root: Path, policy: str, opus_bitrate: str) -> None:
    caminho = track.absolute_path(recordings_root)
    if policy == "delete":
        caminho.unlink(missing_ok=True)
        return

    # "compress": converte pra Opus, só apaga o WAV original depois do
    # ffmpeg confirmar sucesso -- nunca fica sem nenhuma cópia por um
    # instante sequer se a conversão falhar no meio (RNF-R03, mesmo
    # espírito de nunca arriscar a única cópia existente).
    destino = caminho.with_suffix(".opus")
    resultado = subprocess.run(
        ["ffmpeg", "-y", "-i", str(caminho), "-c:a", "libopus", "-b:a", opus_bitrate, str(destino)],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou comprimindo '{caminho}': {resultado.stderr.strip()}")
    caminho.unlink()
    track.path = destino.name


def apply_retention(session: Session, settings: WorkerSettings) -> int:
    """Devolve quantas reuniões tratou nesta rodada (mesmo formato de
    retorno de `recover_interrupted`).

    Salvaguarda 1 (CT-30, UC-09 FA-01): o filtro de status abaixo já
    exclui qualquer coisa fora de `transcribed`/`summarized` -- uma
    reunião `recorded`/`transcribing` nunca entra na seleção, não
    importa a idade. Salvaguarda 2 (RN-04): esta função nunca toca
    `Segment` nem `Summary`, só `Track.path` e `Meeting.audio_state`.
    """
    recordings_root = Path(settings.data_root) / RECORDINGS_DIRNAME
    limite = datetime.now(UTC) - timedelta(days=settings.keep_audio_days)

    candidatas = (
        session.query(Meeting)
        .filter(
            Meeting.status.in_(("transcribed", "summarized")),
            Meeting.audio_state == "original",
            Meeting.started_at < limite,
        )
        .all()
    )

    tratadas = 0
    for meeting in candidatas:
        sucesso = True
        for track in meeting.tracks:
            if _trilha_ja_tratada(track, recordings_root, settings.audio_policy):
                continue
            try:
                _tratar_trilha(track, recordings_root, settings.audio_policy, settings.opus_bitrate)
                # Persiste por trilha, não só no fim da reunião -- se a
                # próxima trilha falhar, esta já fica segura (disco e
                # banco em sincronia) em vez de depender de um rollback
                # que desfaria a mudança no banco sem desfazer o arquivo
                # já convertido/apagado em disco.
                session.commit()
            except Exception:
                logger.exception(
                    "Falha aplicando retenção na trilha %s (reunião %s).", track.id, meeting.id
                )
                session.rollback()
                sucesso = False

        if sucesso:
            meeting.audio_state = "compressed" if settings.audio_policy == "compress" else "removed"
            session.commit()
            tratadas += 1

    return tratadas
