"""
Add missing deleted_at column to ats_scores.

Revision ID: 003_add_ats_scores_deleted_at
Revises: 002_add_foreign_keys
Create Date: 2026-07-09
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "003_add_ats_scores_deleted_at"
down_revision: str | None = "002_add_foreign_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("ats_scores")}
    if "deleted_at" in columns:
        return

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("ats_scores") as batch_op:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    else:
        op.add_column("ats_scores", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("ats_scores")}
    if "deleted_at" not in columns:
        return

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("ats_scores") as batch_op:
            batch_op.drop_column("deleted_at")
    else:
        op.drop_column("ats_scores", "deleted_at")
