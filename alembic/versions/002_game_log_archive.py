"""game_log_archive table — Phase A raw game-log hoard

Revision ID: 002_game_log_archive
Revises: 001_initial
Create Date: 2026-04-21

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_game_log_archive"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_log_archive",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "uploaded_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("original_name", sa.String(512), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.CHAR(64), nullable=False, unique=True),
        sa.Column("stored_path", sa.Text, nullable=False),
        sa.Column("mtgo_username", sa.String(64), nullable=True),
    )
    op.create_index(
        "idx_gla_uploaded_by",
        "game_log_archive",
        ["uploaded_by_user_id", sa.text("captured_at DESC")],
    )
    op.create_index(
        "idx_gla_mtgo_user",
        "game_log_archive",
        ["mtgo_username"],
        postgresql_where=sa.text("mtgo_username IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_gla_mtgo_user", table_name="game_log_archive")
    op.drop_index("idx_gla_uploaded_by", table_name="game_log_archive")
    op.drop_table("game_log_archive")
