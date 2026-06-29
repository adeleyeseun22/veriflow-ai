from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veriflow_api.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from veriflow_api.models.audit_log import AuditLog
    from veriflow_api.models.document import Document
    from veriflow_api.models.organization import Organization
    from veriflow_api.models.workspace import Workspace, WorkspaceMembership


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    organizations_created: Mapped[list[Organization]] = relationship(
        "Organization",
        back_populates="created_by",
        foreign_keys="Organization.created_by_id",
    )
    workspaces_created: Mapped[list[Workspace]] = relationship(
        "Workspace",
        back_populates="created_by",
        foreign_keys="Workspace.created_by_id",
    )
    workspace_memberships: Mapped[list[WorkspaceMembership]] = relationship(
        "WorkspaceMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    documents_uploaded: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="uploaded_by",
        foreign_keys="Document.uploaded_by_id",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="actor")
