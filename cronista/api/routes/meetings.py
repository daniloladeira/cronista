"""POST /meetings, GET /meetings. Ver docs/09-api.md e UC-10."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from cronista.api.security import require_access_token
from cronista.core.db import get_db
from cronista.core.models import Meeting

router = APIRouter(
    prefix="/meetings",
    tags=["meetings"],
    dependencies=[Depends(require_access_token)],
)


class MeetingCreate(BaseModel):
    title: str
    source: str
    host: str
    audio_dir: str
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
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(body: MeetingCreate, db: Session = Depends(get_db)) -> Meeting:
    # 'registering': a reunião existe, as trilhas ainda não chegaram (UC-10).
    meeting = Meeting(
        title=body.title,
        source=body.source,
        host=body.host,
        audio_dir=body.audio_dir,
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
