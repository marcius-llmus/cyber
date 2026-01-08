"""Add missing foreing keys

Revision ID: dafaa737d147
Revises: c2d757907f05
Create Date: 2025-12-27 22:07:19.160497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dafaa737d147'
down_revision: Union[str, Sequence[str], None] = 'c2d757907f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("diff_patches_auto_apply", sa.Boolean(), server_default="t", nullable=False)
        )

    with op.batch_alter_table("diff_patches", schema=None) as batch_op:
        batch_op.add_column(sa.Column("turn_id", sa.String(), nullable=False))
        batch_op.create_index(batch_op.f("ix_diff_patches_turn_id"), ["turn_id"], unique=False)
        batch_op.drop_constraint(batch_op.f("fk_diff_patches_message_id_messages"), type_="foreignkey")
        batch_op.drop_column("tool_run_id")
        batch_op.drop_column("message_id")
        batch_op.drop_column("tool_call_id")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("diff_patches", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tool_call_id", sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column("message_id", sa.INTEGER(), nullable=False))
        batch_op.add_column(sa.Column("tool_run_id", sa.VARCHAR(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_diff_patches_message_id_messages"),
            "messages",
            ["message_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_index(batch_op.f("ix_diff_patches_turn_id"))
        batch_op.drop_column("turn_id")

    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("diff_patches_auto_apply")