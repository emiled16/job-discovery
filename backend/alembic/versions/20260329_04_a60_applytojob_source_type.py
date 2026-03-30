"""Allow applytojob as a supported company source type."""

from __future__ import annotations

from alembic import op


revision = "20260329_04"
down_revision = "20260329_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("company_sources") as batch_op:
        batch_op.drop_constraint("company_sources_source_type_valid", type_="check")
        batch_op.create_check_constraint(
            "company_sources_source_type_valid",
            "source_type IN ('applytojob', 'ashby', 'greenhouse', 'lever', 'manual', 'smartrecruiters', 'workday')",
        )


def downgrade() -> None:
    with op.batch_alter_table("company_sources") as batch_op:
        batch_op.drop_constraint("company_sources_source_type_valid", type_="check")
        batch_op.create_check_constraint(
            "company_sources_source_type_valid",
            "source_type IN ('ashby', 'greenhouse', 'lever', 'manual', 'smartrecruiters', 'workday')",
        )
