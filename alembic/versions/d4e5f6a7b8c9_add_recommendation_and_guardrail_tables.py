"""add_recommendation_and_guardrail_tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-04 00:00:00.000002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("entity_ref", sa.String(200), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("shown_to_user_id", sa.UUID(), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="SHOWN"),
        sa.Column("action_taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_value", postgresql.JSONB(), nullable=True),
        sa.Column("outcome_measured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome_value", postgresql.JSONB(), nullable=True),
        sa.Column("outcome_delta", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shown_to_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_branch_type_status", "recommendations", ["branch_id", "type", "status"])

    op.create_table(
        "pricing_guardrails",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("room_type_id", sa.UUID(), nullable=True),
        sa.Column("min_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_daily_change_pct", sa.Numeric(5, 2), nullable=False, server_default="25.00"),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_type_id"], ["room_types.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "staffing_guardrails",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("min_headcount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_headcount", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ml_room_type_mappings",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("room_type_id", sa.UUID(), nullable=False),
        sa.Column("ml_room_type_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["room_type_id"], ["room_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ml_room_type_mappings_room_type_id", "ml_room_type_mappings", ["room_type_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_ml_room_type_mappings_room_type_id", table_name="ml_room_type_mappings")
    op.drop_table("ml_room_type_mappings")
    op.drop_table("staffing_guardrails")
    op.drop_table("pricing_guardrails")
    op.drop_index("ix_recommendations_branch_type_status", table_name="recommendations")
    op.drop_table("recommendations")
