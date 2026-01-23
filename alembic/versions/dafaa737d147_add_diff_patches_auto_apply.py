"""Add diff patches auto apply and processor type

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
        batch_op.add_column(
            sa.Column(
                "diff_patch_processor_type",
                sa.Enum("UDIFF_LLM", "CODEX_APPLY", name="patchprocessortype"),
                nullable=False,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("diff_patches_auto_apply")
        batch_op.drop_column("diff_patch_processor_type")
