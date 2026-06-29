"""Create document processing jobs.

Revision ID: 20260629_0003
Revises: 20260629_0002
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0003"
down_revision: str | None = "20260629_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

processing_job_status = postgresql.ENUM(
    "QUEUED",
    "PROCESSING",
    "RETRYING",
    "SUCCEEDED",
    "FAILED",
    name="processing_job_status",
    create_type=False,
)


def upgrade() -> None:
    processing_job_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "document_processing_jobs",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_id", sa.Uuid(), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column(
            "job_type",
            sa.String(length=80),
            server_default="integrity_check",
            nullable=False,
        ),
        sa.Column(
            "status",
            processing_job_status,
            server_default=sa.text("'QUEUED'::processing_job_status"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("4"), nullable=False),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_document_processing_jobs_nonnegative_attempts",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="ck_document_processing_jobs_positive_max_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_processing_jobs_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["users.id"],
            name="fk_document_processing_jobs_requested_by_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_processing_jobs"),
    )
    op.create_index(
        "ix_document_processing_jobs_celery_task_id",
        "document_processing_jobs",
        ["celery_task_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_processing_jobs_document_id",
        "document_processing_jobs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_processing_jobs_document_status",
        "document_processing_jobs",
        ["document_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_document_processing_jobs_requested_by_id",
        "document_processing_jobs",
        ["requested_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_processing_jobs_status",
        "document_processing_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_processing_jobs_status", table_name="document_processing_jobs")
    op.drop_index(
        "ix_document_processing_jobs_requested_by_id",
        table_name="document_processing_jobs",
    )
    op.drop_index(
        "ix_document_processing_jobs_document_status",
        table_name="document_processing_jobs",
    )
    op.drop_index(
        "ix_document_processing_jobs_document_id",
        table_name="document_processing_jobs",
    )
    op.drop_index(
        "ix_document_processing_jobs_celery_task_id",
        table_name="document_processing_jobs",
    )
    op.drop_table("document_processing_jobs")
    processing_job_status.drop(op.get_bind(), checkfirst=True)
