"""Add pgvector embeddings and semantic-search indexes.

Revision ID: 20260629_0006
Revises: 20260629_0005
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260629_0006"
down_revision: str | None = "20260629_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "documents",
        sa.Column("embedding_provider", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "embedding_dimension",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "embedding_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "nonnegative_embedding_dimension",
        "documents",
        "embedding_dimension >= 0",
    )
    op.create_check_constraint(
        "nonnegative_embedding_count",
        "documents",
        "embedding_count >= 0",
    )

    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(dim=384), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_provider", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_document_chunks_embedding_namespace",
        "document_chunks",
        ["embedding_provider", "embedding_model"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_where=sa.text("embedding IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunks_embedding_hnsw",
        table_name="document_chunks",
        postgresql_using="hnsw",
    )
    op.drop_index(
        "ix_document_chunks_embedding_namespace",
        table_name="document_chunks",
    )
    op.drop_column("document_chunks", "embedded_at")
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "embedding_provider")
    op.drop_column("document_chunks", "embedding")

    op.drop_constraint(
        "ck_documents_nonnegative_embedding_count",
        "documents",
        type_="check",
    )
    op.drop_constraint(
        "ck_documents_nonnegative_embedding_dimension",
        "documents",
        type_="check",
    )
    op.drop_column("documents", "embedded_at")
    op.drop_column("documents", "embedding_count")
    op.drop_column("documents", "embedding_dimension")
    op.drop_column("documents", "embedding_model")
    op.drop_column("documents", "embedding_provider")
