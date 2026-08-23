"""GET /search. Ver docs/09-api.md e UC-08."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from cronista.api.security import require_access_token
from cronista.core.db import get_db
from cronista.core.models import Meeting, Segment

router = APIRouter(tags=["search"], dependencies=[Depends(require_access_token)])


class SearchResultOut(BaseModel):
    meeting_id: UUID
    meeting_title: str
    speaker: str
    start_ms: int
    timestamp: str
    text: str


@router.get("/search", response_model=list[SearchResultOut])
def search(
    q: str = Query(..., min_length=1),
    speaker: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db: Session = Depends(get_db),
) -> list[SearchResultOut]:
    """RF-23/RF-24, UC-08: busca textual com tratamento morfológico de
    português (stemming), usando o índice GIN já existente em
    `Segment.search` (core/models.py) -- infra pronta desde a migração
    inicial, não é decisão nova. Sem resultado devolve lista vazia com
    200, nunca erro (CT-29)."""
    # pt_br_hunspell, não 'portuguese' puro -- ver core/models.py Segment.search.
    tsquery = func.plainto_tsquery("pt_br_hunspell", q)
    query = (
        db.query(Segment, Meeting)
        .join(Meeting, Segment.meeting_id == Meeting.id)
        .filter(Segment.search.op("@@")(tsquery))
    )
    if speaker is not None:
        query = query.filter(Segment.speaker == speaker)
    if since is not None:
        query = query.filter(Meeting.started_at >= since)
    if until is not None:
        query = query.filter(Meeting.started_at <= until)

    query = query.order_by(func.ts_rank(Segment.search, tsquery).desc())

    return [
        SearchResultOut(
            meeting_id=meeting.id,
            meeting_title=meeting.title,
            speaker=segment.speaker,
            start_ms=segment.start_ms,
            timestamp=segment.timestamp(),
            text=segment.text,
        )
        for segment, meeting in query.all()
    ]
