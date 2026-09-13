"""busca em portugues com hunspell

Revision ID: 4a76601d7800
Revises: 059198327745
Create Date: 2026-08-22 21:37:59.211911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '4a76601d7800'
down_revision: Union[str, None] = '059198327745'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # O dicionário/configuração pt_br_hunspell é objeto de banco, criado
    # em docker/initdb/02-busca-portugues-hunspell.sql (cluster novo) ou
    # à mão uma vez (cluster existente) -- esta migração só reaponta a
    # coluna gerada pra usar o dicionário novo (docs/15-roadmap.md, Fase 5).
    op.drop_index('segments_search_idx', table_name='segments', postgresql_using='gin')
    op.drop_column('segments', 'search')
    op.add_column(
        'segments',
        sa.Column(
            'search',
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('pt_br_hunspell', text)", persisted=True),
            nullable=True,
        ),
    )
    op.create_index('segments_search_idx', 'segments', ['search'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('segments_search_idx', table_name='segments', postgresql_using='gin')
    op.drop_column('segments', 'search')
    op.add_column(
        'segments',
        sa.Column(
            'search',
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('portuguese', text)", persisted=True),
            nullable=True,
        ),
    )
    op.create_index('segments_search_idx', 'segments', ['search'], unique=False, postgresql_using='gin')
