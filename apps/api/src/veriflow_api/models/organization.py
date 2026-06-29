from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veriflow_api.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from veriflow_api.models.user import User
    from veriflow_api.models.workspace import Workspace


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_by: Mapped[User] = relationship(
        "User",
        back_populates="organizations_created",
        foreign_keys=[created_by_id],
    )
    workspaces: Mapped[list[Workspace]] = relationship(
        "Workspace",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
