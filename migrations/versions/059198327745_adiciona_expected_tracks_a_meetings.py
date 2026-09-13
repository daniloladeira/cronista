"""adiciona expected_tracks a meetings

Revision ID: 059198327745
Revises: 1a8e165ca1a0
Create Date: 2026-08-17 12:43:52.747569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '059198327745'
down_revision: Union[str, None] = '1a8e165ca1a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona anulável primeiro: reunião existente não tem como saber
    # quantas trilhas eram esperadas, então preenchemos com a contagem
    # real de trilhas já registradas (o melhor palpite disponível) antes
    # de travar em NOT NULL.
    op.add_column("meetings", sa.Column("expected_tracks", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE meetings
        SET expected_tracks = COALESCE(
            (SELECT COUNT(*) FROM tracks WHERE tracks.meeting_id = meetings.id), 1
        )
        """
    )
    op.alter_column("meetings", "expected_tracks", nullable=False)


def downgrade() -> None:
    op.drop_column("meetings", "expected_tracks")
