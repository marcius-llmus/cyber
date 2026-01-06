"""Add active field to chat session

Revision ID: 123a789273fe
Revises: 91b3671b1f87
Create Date: 2025-11-10 10:35:53.458676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '123a789273fe'
down_revision: Union[str, Sequence[str], None] = '91b3671b1f87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), server_default='f', nullable=False))
        batch_op.add_column(sa.Column('name', sa.String(), server_default='Session', nullable=False))

    # No-op: prompt type values are defined in the initial migration.
 

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.drop_column('name')
        batch_op.drop_column('is_active')
