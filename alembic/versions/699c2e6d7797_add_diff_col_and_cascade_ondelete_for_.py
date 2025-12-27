"""Add diff col and cascade ondelete for message relateds

Revision ID: 699c2e6d7797
Revises: c2d757907f05
Create Date: 2025-12-26 14:30:58.371966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '699c2e6d7797'
down_revision: Union[str, Sequence[str], None] = 'c2d757907f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_CHAT_SESSIONS_PROJECT_ID = "fk_chat_sessions_project_id"
FK_CHAT_SESSIONS_PROJECT_ID_OLD = "fk_chat_sessions_project_id_old"
FK_CONTEXT_FILES_SESSION_ID = "fk_context_files_session_id"
FK_CONTEXT_FILES_SESSION_ID_OLD = "fk_context_files_session_id_old"
FK_DIFF_PATCHES_MESSAGE_ID = "fk_diff_patches_message_id"
FK_DIFF_PATCHES_MESSAGE_ID_OLD = "fk_diff_patches_message_id_old"
FK_DIFF_PATCHES_SESSION_ID = "fk_diff_patches_session_id"
FK_DIFF_PATCHES_SESSION_ID_OLD = "fk_diff_patches_session_id_old"
FK_MESSAGES_SESSION_ID = "fk_messages_session_id"
FK_MESSAGES_SESSION_ID_OLD = "fk_messages_session_id_old"
FK_PROJECT_PROMPT_ATTACHMENTS_PROJECT_ID = "fk_project_prompt_attachments_project_id"
FK_PROJECT_PROMPT_ATTACHMENTS_PROJECT_ID_OLD = "fk_project_prompt_attachments_project_id_old"
FK_PROJECT_PROMPT_ATTACHMENTS_PROMPT_ID = "fk_project_prompt_attachments_prompt_id"
FK_PROJECT_PROMPT_ATTACHMENTS_PROMPT_ID_OLD = "fk_project_prompt_attachments_prompt_id_old"
FK_PROMPTS_PROJECT_ID = "fk_prompts_project_id"
FK_PROMPTS_PROJECT_ID_OLD = "fk_prompts_project_id_old"
FK_SESSION_PROMPT_ATTACHMENTS_PROMPT_ID = "fk_session_prompt_attachments_prompt_id"
FK_SESSION_PROMPT_ATTACHMENTS_PROMPT_ID_OLD = "fk_session_prompt_attachments_prompt_id_old"
FK_SESSION_PROMPT_ATTACHMENTS_SESSION_ID = "fk_session_prompt_attachments_session_id"
FK_SESSION_PROMPT_ATTACHMENTS_SESSION_ID_OLD = "fk_session_prompt_attachments_session_id_old"
FK_SESSION_USAGE_SESSION_ID = "fk_session_usage_session_id"
FK_SESSION_USAGE_SESSION_ID_OLD = "fk_session_usage_session_id_old"
FK_WORKFLOW_STATES_SESSION_ID = "fk_workflow_states_session_id"
FK_WORKFLOW_STATES_SESSION_ID_OLD = "fk_workflow_states_session_id_old"


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("chat_sessions", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_CHAT_SESSIONS_PROJECT_ID_OLD,
            "projects",
            ["project_id"],
            ["id"],
        )
        batch_op.drop_constraint(FK_CHAT_SESSIONS_PROJECT_ID_OLD, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_CHAT_SESSIONS_PROJECT_ID,
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("context_files", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_CONTEXT_FILES_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )
        batch_op.drop_constraint(FK_CONTEXT_FILES_SESSION_ID_OLD, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_CONTEXT_FILES_SESSION_ID,
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("diff_patches", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_DIFF_PATCHES_MESSAGE_ID_OLD,
            "messages",
            ["message_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            FK_DIFF_PATCHES_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )
        batch_op.drop_constraint(FK_DIFF_PATCHES_MESSAGE_ID_OLD, type_="foreignkey")
        batch_op.drop_constraint(FK_DIFF_PATCHES_SESSION_ID_OLD, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_DIFF_PATCHES_MESSAGE_ID,
            "messages",
            ["message_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            FK_DIFF_PATCHES_SESSION_ID,
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_MESSAGES_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )
        batch_op.drop_constraint(FK_MESSAGES_SESSION_ID_OLD, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_MESSAGES_SESSION_ID,
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("project_prompt_attachments", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_PROJECT_PROMPT_ATTACHMENTS_PROJECT_ID_OLD,
            "projects",
            ["project_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            FK_PROJECT_PROMPT_ATTACHMENTS_PROMPT_ID_OLD,
            "prompts",
            ["prompt_id"],
            ["id"],
        )
        batch_op.drop_constraint(
            FK_PROJECT_PROMPT_ATTACHMENTS_PROJECT_ID_OLD, type_="foreignkey"
        )
        batch_op.drop_constraint(
            FK_PROJECT_PROMPT_ATTACHMENTS_PROMPT_ID_OLD, type_="foreignkey"
        )
        batch_op.create_foreign_key(
            FK_PROJECT_PROMPT_ATTACHMENTS_PROJECT_ID,
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            FK_PROJECT_PROMPT_ATTACHMENTS_PROMPT_ID,
            "prompts",
            ["prompt_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("prompts", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_PROMPTS_PROJECT_ID_OLD,
            "projects",
            ["project_id"],
            ["id"],
        )
        batch_op.drop_constraint(FK_PROMPTS_PROJECT_ID_OLD, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_PROMPTS_PROJECT_ID,
            "projects",
            ["project_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("session_prompt_attachments", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_SESSION_PROMPT_ATTACHMENTS_PROMPT_ID_OLD,
            "prompts",
            ["prompt_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            FK_SESSION_PROMPT_ATTACHMENTS_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )
        batch_op.drop_constraint(
            FK_SESSION_PROMPT_ATTACHMENTS_PROMPT_ID_OLD, type_="foreignkey"
        )
        batch_op.drop_constraint(
            FK_SESSION_PROMPT_ATTACHMENTS_SESSION_ID_OLD, type_="foreignkey"
        )
        batch_op.create_foreign_key(
            FK_SESSION_PROMPT_ATTACHMENTS_PROMPT_ID,
            "prompts",
            ["prompt_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            FK_SESSION_PROMPT_ATTACHMENTS_SESSION_ID,
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("session_usage", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_SESSION_USAGE_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )
        batch_op.drop_constraint(FK_SESSION_USAGE_SESSION_ID_OLD, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_SESSION_USAGE_SESSION_ID,
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "diff_patches_auto_apply",
                sa.Boolean(),
                server_default="f",
                nullable=False,
            )
        )

    with op.batch_alter_table("workflow_states", schema=None) as batch_op:
        batch_op.create_foreign_key(
            FK_WORKFLOW_STATES_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )
        batch_op.drop_constraint(FK_WORKFLOW_STATES_SESSION_ID_OLD, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_WORKFLOW_STATES_SESSION_ID,
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("workflow_states", schema=None) as batch_op:
        batch_op.drop_constraint(FK_WORKFLOW_STATES_SESSION_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_WORKFLOW_STATES_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )

    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("diff_patches_auto_apply")

    with op.batch_alter_table("session_usage", schema=None) as batch_op:
        batch_op.drop_constraint(FK_SESSION_USAGE_SESSION_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_SESSION_USAGE_SESSION_ID_OLD, "chat_sessions", ["session_id"], ["id"]
        )

    with op.batch_alter_table("session_prompt_attachments", schema=None) as batch_op:
        batch_op.drop_constraint(FK_SESSION_PROMPT_ATTACHMENTS_PROMPT_ID, type_="foreignkey")
        batch_op.drop_constraint(FK_SESSION_PROMPT_ATTACHMENTS_SESSION_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_SESSION_PROMPT_ATTACHMENTS_PROMPT_ID_OLD,
            "prompts",
            ["prompt_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            FK_SESSION_PROMPT_ATTACHMENTS_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )

    with op.batch_alter_table("prompts", schema=None) as batch_op:
        batch_op.drop_constraint(FK_PROMPTS_PROJECT_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_PROMPTS_PROJECT_ID_OLD, "projects", ["project_id"], ["id"]
        )

    with op.batch_alter_table("project_prompt_attachments", schema=None) as batch_op:
        batch_op.drop_constraint(FK_PROJECT_PROMPT_ATTACHMENTS_PROJECT_ID, type_="foreignkey")
        batch_op.drop_constraint(FK_PROJECT_PROMPT_ATTACHMENTS_PROMPT_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_PROJECT_PROMPT_ATTACHMENTS_PROJECT_ID_OLD,
            "projects",
            ["project_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            FK_PROJECT_PROMPT_ATTACHMENTS_PROMPT_ID_OLD,
            "prompts",
            ["prompt_id"],
            ["id"],
        )

    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_constraint(FK_MESSAGES_SESSION_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_MESSAGES_SESSION_ID_OLD, "chat_sessions", ["session_id"], ["id"]
        )

    with op.batch_alter_table("diff_patches", schema=None) as batch_op:
        batch_op.drop_constraint(FK_DIFF_PATCHES_MESSAGE_ID, type_="foreignkey")
        batch_op.drop_constraint(FK_DIFF_PATCHES_SESSION_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_DIFF_PATCHES_MESSAGE_ID_OLD,
            "messages",
            ["message_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            FK_DIFF_PATCHES_SESSION_ID_OLD,
            "chat_sessions",
            ["session_id"],
            ["id"],
        )

    with op.batch_alter_table("context_files", schema=None) as batch_op:
        batch_op.drop_constraint(FK_CONTEXT_FILES_SESSION_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_CONTEXT_FILES_SESSION_ID_OLD, "chat_sessions", ["session_id"], ["id"]
        )

    with op.batch_alter_table("chat_sessions", schema=None) as batch_op:
        batch_op.drop_constraint(FK_CHAT_SESSIONS_PROJECT_ID, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_CHAT_SESSIONS_PROJECT_ID_OLD, "projects", ["project_id"], ["id"]
        )