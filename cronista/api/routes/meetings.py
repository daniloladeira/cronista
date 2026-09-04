"""POST /meetings, GET /meetings, POST /meetings/{id}/tracks.
Ver docs/09-api.md e UC-10.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from cronista.api import summarize
from cronista.api.security import require_access_token
from cronista.core.config import RECORDINGS_DIRNAME, Settings
from cronista.core.db import get_db
from cronista.core.models import Meeting, Segment, Summary, Track

router = APIRouter(
    prefix="/meetings",
    tags=["meetings"],
    dependencies=[Depends(require_access_token)],
)

_settings = Settings()


def get_data_root() -> str:
    """Dependência do FastAPI, não acesso direto — permite override em teste
    (app.dependency_overrides), do mesmo jeito que get_db."""
    return _settings.data_root


class MeetingCreate(BaseModel):
    # O cliente fornece o id (ADR-0004: ids nascem na aplicação, não no
    # banco). É o que torna o registro idempotente de verdade: se a
    # resposta se perder na rede, reenviar o MESMO id não duplica —
    # devolve a reunião já criada (UC-11, UC-10 FA-01).
    id: UUID
    title: str
    source: str
    host: str
    audio_dir: str
    expected_tracks: int
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None


class MeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    source: str
    host: str
    status: str
    expected_tracks: int
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None


class TrackCreate(BaseModel):
    speaker: str
    path: str  # relativo a meetings.audio_dir (docs/08 §7)
    sample_rate: int
    channels: int
    duration_ms: int | None = None
    size_bytes: int | None = None
    device: str | None = None


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    speaker: str
    path: str
    sample_rate: int
    channels: int
    duration_ms: int | None
    size_bytes: int | None
    device: str | None


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    provider: str
    model: str
    prompt_version: str
    markdown: str
    generated_at: datetime


class MeetingDetailOut(MeetingOut):
    # RF-20/RF-22, UC-07: "dados de uma reunião, suas trilhas e resumos"
    # (docs/09-api.md §2) -- estende MeetingOut em vez de duplicar campo.
    tracks: list[TrackOut]
    summaries: list[SummaryOut]


class SegmentOut(BaseModel):
    # Construído explícito no handler, não via from_attributes: `timestamp`
    # é um método em Segment (core/models.py), não um atributo -- precisa
    # ser chamado, não só lido.
    speaker: str
    start_ms: int
    end_ms: int
    text: str
    timestamp: str


class MeetingRename(BaseModel):
    title: str


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(body: MeetingCreate, db: Session = Depends(get_db)) -> Meeting:
    # Idempotente por id (UC-11): se já existe, devolve a existente em vez
    # de criar duplicata — cobre o caso da resposta original ter se perdido.
    existing = db.get(Meeting, body.id)
    if existing is not None:
        return existing

    # 'registering': a reunião existe, as trilhas ainda não chegaram (UC-10).
    meeting = Meeting(
        id=body.id,
        title=body.title,
        source=body.source,
        host=body.host,
        audio_dir=body.audio_dir,
        expected_tracks=body.expected_tracks,
        status="registering",
        started_at=body.started_at,
        ended_at=body.ended_at,
        duration_ms=body.duration_ms,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("", response_model=list[MeetingOut])
def list_meetings(db: Session = Depends(get_db)) -> list[Meeting]:
    return db.query(Meeting).order_by(Meeting.started_at.desc()).all()


@router.get("/{meeting_id}", response_model=MeetingDetailOut)
def get_meeting(meeting_id: UUID, db: Session = Depends(get_db)) -> Meeting:
    """RF-20/RF-22, UC-07: dados da reunião com trilhas e resumos."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada.")
    return meeting


@router.get("/{meeting_id}/transcript", response_model=list[SegmentOut])
def get_transcript(meeting_id: UUID, db: Session = Depends(get_db)) -> list[SegmentOut]:
    """RF-21, UC-07: transcrição mesclada e ordenada -- a mesclagem é do
    servidor (docs/09-api.md §3), o cliente nunca recebe trilha separada.
    Reunião ainda não transcrita devolve lista vazia, não erro (CT-26) --
    RF-21 não exige status `transcribed`."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada.")

    segments = db.query(Segment).filter(Segment.meeting_id == meeting_id).order_by(Segment.start_ms)
    return [
        SegmentOut(
            speaker=s.speaker, start_ms=s.start_ms, end_ms=s.end_ms, text=s.text, timestamp=s.timestamp()
        )
        for s in segments
    ]


@router.patch("/{meeting_id}", response_model=MeetingOut)
def rename_meeting(meeting_id: UUID, body: MeetingRename, db: Session = Depends(get_db)) -> Meeting:
    """UC-07: altera o título. Sem restrição de estado -- renomear não
    interfere com o pipeline de transcrição/resumo."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada.")

    meeting.title = body.title
    db.commit()
    db.refresh(meeting)
    return meeting


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: UUID, db: Session = Depends(get_db), data_root: str = Depends(get_data_root)
) -> None:
    """RF-30, UC-09: remove a reunião e tudo que dela deriva. A
    confirmação (FE-01) é responsabilidade do cliente -- este endpoint,
    uma vez chamado, remove sem mais perguntas, como qualquer DELETE."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada.")

    diretorio = Path(data_root) / RECORDINGS_DIRNAME / meeting.audio_dir
    try:
        shutil.rmtree(diretorio)
    except FileNotFoundError:
        pass  # FE-02: diretório já ausente, remoção é idempotente.
    except OSError as exc:
        # FE-03: não apaga o registro sem confirmar que o áudio saiu do
        # disco, senão a próxima consulta acha uma reunião "removida"
        # com arquivo ainda ocupando espaço, sem jeito de saber disso.
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"Falha removendo áudio em {diretorio}: {exc}"
        ) from exc

    # tracks/segments/summaries têm ForeignKey(..., ondelete="CASCADE")
    # (core/models.py) -- o Postgres cuida da cascata (RN-05), não é
    # preciso apagar cada tabela na mão aqui.
    db.delete(meeting)
    db.commit()


@router.post(
    "/{meeting_id}/tracks", response_model=TrackOut, status_code=status.HTTP_201_CREATED
)
def register_track(
    meeting_id: UUID,
    body: TrackCreate,
    db: Session = Depends(get_db),
    data_root: str = Depends(get_data_root),
) -> Track:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada.")

    # RN-08/§1: nenhum áudio trafega pela API. Confere que o arquivo já
    # existe onde o cliente diz que gravou, antes de aceitar a referência.
    absolute_path = Path(data_root) / RECORDINGS_DIRNAME / meeting.audio_dir / body.path
    if not absolute_path.is_file():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Arquivo não encontrado em {absolute_path}.",
        )

    # UC-10, FA-01: reenviar trilha já registrada substitui, não duplica.
    existing = (
        db.query(Track)
        .filter(Track.meeting_id == meeting_id, Track.speaker == body.speaker)
        .one_or_none()
    )
    if existing is not None:
        existing.path = body.path
        existing.sample_rate = body.sample_rate
        existing.channels = body.channels
        existing.duration_ms = body.duration_ms
        existing.size_bytes = body.size_bytes
        existing.device = body.device
        track = existing
    else:
        track = Track(
            meeting_id=meeting_id,
            speaker=body.speaker,
            path=body.path,
            sample_rate=body.sample_rate,
            channels=body.channels,
            duration_ms=body.duration_ms,
            size_bytes=body.size_bytes,
            device=body.device,
        )
        db.add(track)

    db.flush()  # garante meeting.tracks refletindo a trilha recém-gravada
    db.refresh(meeting)
    if meeting.status == "registering" and meeting.has_all_tracks():
        meeting.status = "recorded"

    db.commit()
    db.refresh(track)
    return track


@router.post("/{meeting_id}/transcribe", response_model=MeetingOut)
def reprocess_meeting(meeting_id: UUID, db: Session = Depends(get_db)) -> Meeting:
    """Recoloca a reunião na fila de transcrição (UC-05, RF-15,
    docs/12-transcricao.md §10). Cobre falha anterior e "refazer" numa
    reunião já transcrita/resumida -- não é retentativa automática, é
    sempre um pedido explícito do usuário."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada.")

    if not meeting.is_reprocessable():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Reunião em '{meeting.status}' não pode ser reprocessada agora.",
        )

    meeting.status = "recorded"
    db.commit()
    db.refresh(meeting)
    return meeting


@router.post("/{meeting_id}/summarize", response_model=SummaryOut)
def summarize_meeting(meeting_id: UUID, db: Session = Depends(get_db)) -> Summary:
    """Gera um novo resumo (UC-06, RF-16, docs/13-resumo.md). Ao contrário
    de /transcribe, não recoloca numa fila -- bloqueia até o provedor
    responder (docs/09-api.md §5)."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada.")

    if not meeting.is_summarizable():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Reunião em '{meeting.status}' não pode ser resumida agora.",
        )

    try:
        return summarize.summarize(db, meeting, _settings)
    except (summarize.ProviderUnavailable, summarize.RespostaMalformada) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
