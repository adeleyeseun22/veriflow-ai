"""Create structure-aware document chunks.

Revision ID: 20260629_0005
Revises: 20260629_0004
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0005"
down_revision: str | None = "20260629_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("chunker_name", sa.String(length=120), nullable=True))
    op.add_column("documents", sa.Column("chunker_version", sa.String(length=40), nullable=True))
    op.add_column(
        "documents",
        sa.Column("chunked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("chunk_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column(
            "chunk_token_estimate",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "nonnegative_chunk_count",
        "documents",
        "chunk_count >= 0",
    )
    op.create_check_constraint(
        "nonnegative_chunk_token_estimate",
        "documents",
        "chunk_token_estimate >= 0",
    )

    chunk_source_type = postgresql.ENUM(
        "SECTION",
        "PAGE",
        "TABLE",
        name="chunk_source_type",
        create_type=False,
    )
    chunk_source_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "document_chunks",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=True),
        sa.Column("table_id", sa.Uuid(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("source_type", chunk_source_type, nullable=False),
        sa.Column("source_label", sa.String(length=500), nullable=True),
        sa.Column(
            "heading_path",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column(
            "overlap_chars",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "chunk_metadata",
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
        sa.CheckConstraint("char_count >= 0", name="nonnegative_char_count"),
        sa.CheckConstraint("word_count >= 0", name="nonnegative_word_count"),
        sa.CheckConstraint("token_estimate >= 0", name="nonnegative_token_estimate"),
        sa.CheckConstraint("overlap_chars >= 0", name="nonnegative_overlap_chars"),
        sa.CheckConstraint(
            "char_length(fingerprint) = 64",
            name="valid_fingerprint_length",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["document_sections.id"],
            name="fk_document_chunks_section_id_document_sections",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["table_id"],
            ["document_tables.id"],
            name="fk_document_chunks_table_id_document_tables",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_chunks"),
        sa.UniqueConstraint(
            "document_id",
            "ordinal",
            name="uq_document_chunks_document_ordinal",
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_section_id",
        "document_chunks",
        ["section_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_table_id",
        "document_chunks",
        ["table_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_document_source",
        "document_chunks",
        ["document_id", "source_type"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_fingerprint",
        "document_chunks",
        ["fingerprint"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_fingerprint", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_source", table_name="document_chunks")
    op.drop_index("ix_document_chunks_table_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_section_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    postgresql.ENUM(name="chunk_source_type").drop(op.get_bind(), checkfirst=True)

    op.drop_constraint(
        "nonnegative_chunk_token_estimate",
        "documents",
        type_="check",
    )
    op.drop_constraint(
        "nonnegative_chunk_count",
        "documents",
        type_="check",
    )
    op.drop_column("documents", "chunk_token_estimate")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "chunked_at")
    op.drop_column("documents", "chunker_version")
    op.drop_column("documents", "chunker_name")
