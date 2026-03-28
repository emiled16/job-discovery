"""Create company sources table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_03"
down_revision = "20260328_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=True),
        sa.Column("base_url", sa.String(length=1024), nullable=True),
        sa.Column("configuration", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "source_type IN ('greenhouse', 'lever', 'manual')",
            name="company_sources_source_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_company_sources_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_sources"),
        sa.UniqueConstraint(
            "company_id",
            "source_type",
            name="uq_company_sources_company_source",
        ),
    )


def downgrade() -> None:
    op.drop_table("company_sources")
