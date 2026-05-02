"""Add copied byte count to quarantine records for WP-07.

This migration closes SL-VAL-022 for existing durable-state databases by
persisting the copied byte count when a quarantine copy succeeds. It is
intentionally column-aware so development databases created while the WP-07
review patch was in flight do not fail on duplicate column creation.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260502_01"
down_revision = "20260430_01"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    """Return whether *table_name* currently has *column_name*."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("quarantine_records", "copied_size_bytes"):
        op.add_column(
            "quarantine_records",
            sa.Column("copied_size_bytes", sa.BigInteger(), nullable=True),
        )


def downgrade() -> None:
    if _has_column("quarantine_records", "copied_size_bytes"):
        op.drop_column("quarantine_records", "copied_size_bytes")
