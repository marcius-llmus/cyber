"""Add reasoning config to llm settings

Revision ID: 45678cdef456
Revises: 3890cbcf8415
Create Date: 2026-02-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45678cdef456'
down_revision: Union[str, Sequence[str], None] = '3890cbcf8415'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('llm_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reasoning_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('llm_settings', schema=None) as batch_op:
        batch_op.drop_column('reasoning_config')
