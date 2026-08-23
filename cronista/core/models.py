"""Modelos de domínio. Ver docs/08-modelo-de-dados.md.

Quatro tabelas: Meeting, Track, Segment, Summary. `core` não importa nada
de `api`, `client` ou `worker` (docs/07-arquitetura.md §2.2).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import TIMESTAMP, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from cronista.core.ids import uuid7


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(Text, nullable=False)
    audio_dir: Mapped[str] = mapped_column(Text, nullable=False)
    expected_tracks: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_state: Mapped[str] = mapped_column(Text, nullable=False, server_default="original")
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    tracks: Mapped[list["Track"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    segments: Mapped[list["Segment"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["Summary"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("source IN ('capture', 'import')", name="ck_meetings_source"),
        CheckConstraint(
            "audio_state IN ('original', 'compressed', 'removed')",
            name="ck_meetings_audio_state",
        ),
        CheckConstraint(
            "status IN ('registering', 'recorded', 'transcribing', 'transcribed', "
            "'summarized', 'transcription_failed', 'summary_failed')",
            name="ck_meetings_status",
        ),
        Index("meetings_queue_idx", "status", "started_at"),
        Index("meetings_started_idx", sa_text("started_at DESC")),
    )

    def duration(self) -> timedelta | None:
        if self.duration_ms is None:
            return None
        return timedelta(milliseconds=self.duration_ms)

    def has_all_tracks(self) -> bool:
        # UC-10 passo 5: reunião vira 'recorded' só quando todas as trilhas
        # esperadas chegaram. Contagem, não a palavra do cliente sobre qual
        # é "a última" — resiliente a reenvio (UC-11).
        return len(self.tracks) >= self.expected_tracks

    def is_transcribable(self) -> bool:
        # RN-06: só entra em transcrição a partir de 'recorded' ou 'transcription_failed'.
        return self.status in ("recorded", "transcription_failed")

    def is_summarizable(self) -> bool:
        # RN-07: só gera resumo a partir de 'transcribed' ou 'summarized'.
        # 'summary_failed' também entra: é o estado de "nova tentativa"
        # do diagrama (docs/08-modelo-de-dados.md §5) -- sem isso, uma
        # falha de provedor deixaria a reunião sem caminho de volta.
        return self.status in ("transcribed", "summarized", "summary_failed")

    def is_reprocessable(self) -> bool:
        # docs/12-transcricao.md §10: cobre os dois casos em que
        # reprocessar faz sentido -- a tentativa anterior falhou, ou já
        # teve sucesso mas o usuário quer refazer (ex.: vocabulário
        # novo). 'recorded' fica de fora por já estar na fila; 'registering'/
        # 'transcribing'/'summary_failed' ficam de fora por não terem o
        # que reprocessar ainda ou terem outra operação em andamento.
        return self.status in ("transcription_failed", "transcribed", "summarized")


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    speaker: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    channels: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    device: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="tracks")
    segments: Mapped[list["Segment"]] = relationship(back_populates="track")

    __table_args__ = (
        UniqueConstraint("meeting_id", "speaker", name="uq_tracks_meeting_speaker"),
    )

    def absolute_path(self, root: Path) -> Path:
        # path é relativo a meetings.audio_dir, que é relativo a root (docs/08 §7).
        return root / self.meeting.audio_dir / self.path


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE")
    )
    speaker: Mapped[str] = mapped_column(Text, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # pt_br_hunspell: dicionário/configuração criado à parte (docker/initdb
    # /02-busca-portugues-hunspell.sql), não pelo SQLAlchemy -- 'portuguese'
    # puro (snowball) não junta "decisão"/"decisões" nem "decisão"/
    # "decidimos" (medido, não presumido; docs/15-roadmap.md, Fase 5).
    search: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('pt_br_hunspell', text)", persisted=True)
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="segments")
    track: Mapped["Track | None"] = relationship(back_populates="segments")

    __table_args__ = (
        Index("segments_meeting_idx", "meeting_id", "start_ms"),
        Index("segments_search_idx", "search", postgresql_using="gin"),
    )

    def timestamp(self) -> str:
        total_seconds = self.start_ms // 1000
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="summaries")

    __table_args__ = (
        Index("summaries_meeting_idx", "meeting_id", sa_text("generated_at DESC")),
    )
