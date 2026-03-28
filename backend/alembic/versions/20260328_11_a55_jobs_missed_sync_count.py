"""Add jobs missed sync count."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260328_11"
down_revision: Union[str, Sequence[str], None] = "20260328_10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("missed_sync_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("jobs", "missed_sync_count")
