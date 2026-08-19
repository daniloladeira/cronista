"""POST /meetings, GET /meetings, POST /meetings/{id}/tracks.
Ver docs/09-api.md e UC-10.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from cronista.api.security import require_access_token
from cronista.core.config import RECORDINGS_DIRNAME, Settings
from cronista.core.db import get_db
from cronista.core.models import Meeting, Track

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
