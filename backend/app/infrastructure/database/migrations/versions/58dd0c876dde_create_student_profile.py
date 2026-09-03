"""create student profile

Revision ID: 58dd0c876dde
Revises: 
Create Date: 2026-08-16 10:41:53.211125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '58dd0c876dde'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("academic_level", sa.String(length=100), nullable=True),
        sa.Column("current_degree", sa.String(length=255), nullable=True),
        sa.Column("field_of_study", sa.String(length=255), nullable=True),
        sa.Column("university", sa.String(length=255), nullable=True),
        sa.Column("gpa", sa.Numeric(3, 2), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("target_degree", sa.String(length=100), nullable=True),
        sa.Column("target_countries", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("research_interests", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("skills", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("publications", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("projects", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("work_experience", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("preferred_funding", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("email", name="uq_student_profiles_email"),
    )

    op.create_table(
        "universities",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("website_url", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "professors",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("university", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("research_interests", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("publications", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("profile_url", sa.String(length=512), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
    )

    op.create_table(
        "programs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("university_id", sa.Uuid(), sa.ForeignKey("universities.id"), nullable=True),
        sa.Column("degree_level", sa.String(length=100), nullable=True),
        sa.Column("field", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=True),
        sa.Column("university", sa.String(length=255), nullable=True),
        sa.Column("degree_level", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("field", sa.String(length=255), nullable=True),
        sa.Column("funding_type", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("eligibility", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("application_url", sa.String(length=512), nullable=True),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("student_profiles.id"), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), sa.ForeignKey("opportunities.id"), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "sop_documents",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("student_profiles.id"), nullable=True),
        sa.Column("application_id", sa.Uuid(), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("draft_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(length=100), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("student_profiles.id"), nullable=True),
        sa.Column("workflow_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("user_request", sa.Text(), nullable=False),
        sa.Column("result", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("token_usage", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "agent_executions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("workflow_executions.id"), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("token_usage", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("estimated_cost", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("error", sa.Text(), nullable=True),
    )

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("workflow_executions.id"), nullable=False),
        sa.Column("sender", sa.String(length=100), nullable=False),
        sa.Column("receiver", sa.String(length=100), nullable=False),
        sa.Column("message_type", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "memory_entries",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("student_profiles.id"), nullable=True),
        sa.Column("memory_type", sa.String(length=100), nullable=False),
        sa.Column("scope", sa.String(length=100), nullable=False),
        sa.Column("content", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("profile_id", "memory_type", "scope", name="uq_memory_profile_type_scope"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("memory_entries")
    op.drop_table("agent_messages")
    op.drop_table("agent_executions")
    op.drop_table("workflow_executions")
    op.drop_table("sop_documents")
    op.drop_table("applications")
    op.drop_table("opportunities")
    op.drop_table("programs")
    op.drop_table("professors")
    op.drop_table("universities")
    op.drop_table("student_profiles")
