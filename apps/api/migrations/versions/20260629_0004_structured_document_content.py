"""Create structured document content tables.

Revision ID: 20260629_0004
Revises: 20260629_0003
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0004"
down_revision: str | None = "20260629_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("parser_name", sa.String(length=120), nullable=True))
    op.add_column("documents", sa.Column("parser_version", sa.String(length=40), nullable=True))
    op.add_column(
        "documents",
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("page_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("section_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("table_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column(
            "extracted_text_chars",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "nonnegative_page_count",
        "documents",
        "page_count >= 0",
    )
    op.create_check_constraint(
        "nonnegative_section_count",
        "documents",
        "section_count >= 0",
    )
    op.create_check_constraint(
        "nonnegative_table_count",
        "documents",
        "table_count >= 0",
    )
    op.create_check_constraint(
        "nonnegative_extracted_text_chars",
        "documents",
        "extracted_text_chars >= 0",
    )

    op.alter_column(
        "document_processing_jobs",
        "job_type",
        existing_type=sa.String(length=80),
        server_default="structured_ingestion",
        existing_nullable=False,
    )

    op.create_table(
        "document_pages",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), server_default="", nullable=False),
        sa.Column("char_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("word_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "page_metadata",
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
        sa.CheckConstraint("page_number > 0", name="positive_page_number"),
        sa.CheckConstraint("char_count >= 0", name="nonnegative_char_count"),
        sa.CheckConstraint("word_count >= 0", name="nonnegative_word_count"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_pages_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_pages"),
        sa.UniqueConstraint(
            "document_id",
            "page_number",
            name="uq_document_pages_document_page",
        ),
    )
    op.create_index(
        "ix_document_pages_document_id",
        "document_pages",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_pages_document_page",
        "document_pages",
        ["document_id", "page_number"],
        unique=False,
    )

    op.create_table(
        "document_sections",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("heading_level", sa.Integer(), nullable=True),
        sa.Column(
            "section_path",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("char_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("word_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "section_metadata",
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
        sa.CheckConstraint("ordinal >= 0", name="nonnegative_ordinal"),
        sa.CheckConstraint(
            "char_count >= 0",
            name="nonnegative_char_count",
        ),
        sa.CheckConstraint(
            "word_count >= 0",
            name="nonnegative_word_count",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_sections_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_sections"),
        sa.UniqueConstraint(
            "document_id",
            "ordinal",
            name="uq_document_sections_document_ordinal",
        ),
    )
    op.create_index(
        "ix_document_sections_document_id",
        "document_sections",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_sections_document_ordinal",
        "document_sections",
        ["document_id", "ordinal"],
        unique=False,
    )

    op.create_table(
        "document_tables",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("source_label", sa.String(length=500), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column(
            "column_names",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "rows",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("row_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("column_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_truncated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "table_metadata",
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
        sa.CheckConstraint("ordinal >= 0", name="nonnegative_ordinal"),
        sa.CheckConstraint("row_count >= 0", name="nonnegative_row_count"),
        sa.CheckConstraint(
            "column_count >= 0",
            name="nonnegative_column_count",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_tables_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["document_sections.id"],
            name="fk_document_tables_section_id_document_sections",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_tables"),
        sa.UniqueConstraint(
            "document_id",
            "ordinal",
            name="uq_document_tables_document_ordinal",
        ),
    )
    op.create_index(
        "ix_document_tables_document_id",
        "document_tables",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_tables_section_id",
        "document_tables",
        ["section_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_tables_document_ordinal",
        "document_tables",
        ["document_id", "ordinal"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_tables_document_ordinal", table_name="document_tables")
    op.drop_index("ix_document_tables_section_id", table_name="document_tables")
    op.drop_index("ix_document_tables_document_id", table_name="document_tables")
    op.drop_table("document_tables")

    op.drop_index("ix_document_sections_document_ordinal", table_name="document_sections")
    op.drop_index("ix_document_sections_document_id", table_name="document_sections")
    op.drop_table("document_sections")

    op.drop_index("ix_document_pages_document_page", table_name="document_pages")
    op.drop_index("ix_document_pages_document_id", table_name="document_pages")
    op.drop_table("document_pages")

    op.alter_column(
        "document_processing_jobs",
        "job_type",
        existing_type=sa.String(length=80),
        server_default="integrity_check",
        existing_nullable=False,
    )

    op.drop_constraint(
        "ck_documents_nonnegative_extracted_text_chars",
        "documents",
        type_="check",
    )
    op.drop_constraint("ck_documents_nonnegative_table_count", "documents", type_="check")
    op.drop_constraint("ck_documents_nonnegative_section_count", "documents", type_="check")
    op.drop_constraint("ck_documents_nonnegative_page_count", "documents", type_="check")
    op.drop_column("documents", "extracted_text_chars")
    op.drop_column("documents", "table_count")
    op.drop_column("documents", "section_count")
    op.drop_column("documents", "page_count")
    op.drop_column("documents", "parsed_at")
    op.drop_column("documents", "parser_version")
    op.drop_column("documents", "parser_name")
