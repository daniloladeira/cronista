"""adiciona estado registering a meetings

Revision ID: 1a8e165ca1a0
Revises: 0c0fd1b97d2f
Create Date: 2026-08-17 10:08:31.847795

"""
from typing import Sequence, Union

from alembic import op

revision: str = '1a8e165ca1a0'
down_revision: Union[str, None] = '0c0fd1b97d2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_STATUSES = (
    "'recorded', 'transcribing', 'transcribed', 'summarized', "
    "'transcription_failed', 'summary_failed'"
)
_NEW_STATUSES = (
    "'registering', 'recorded', 'transcribing', 'transcribed', "
    "'summarized', 'transcription_failed', 'summary_failed'"
)


def upgrade() -> None:
    # Escrito à mão: autogenerate não detecta de forma confiável mudança no
    # texto de um CHECK já existente (docs/08-modelo-de-dados.md §5).
    op.drop_constraint("ck_meetings_status", "meetings", type_="check")
    op.create_check_constraint(
        "ck_meetings_status", "meetings", f"status IN ({_NEW_STATUSES})"
    )


def downgrade() -> None:
    op.drop_constraint("ck_meetings_status", "meetings", type_="check")
    op.create_check_constraint(
        "ck_meetings_status", "meetings", f"status IN ({_OLD_STATUSES})"
    )
