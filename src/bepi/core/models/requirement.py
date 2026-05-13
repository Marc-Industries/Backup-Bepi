from __future__ import annotations

from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.models.base import Base, TimestampMixin, UUIDMixin
from bepi.core.enums import *

requirement_product_node = sa.Table(
    "requirement_product_node",
    Base.metadata,
    sa.Column("requirement_id", sa.Integer, sa.ForeignKey("requirement.id"), primary_key=True),
    sa.Column("node_id", sa.Integer, sa.ForeignKey("product_node.id"), primary_key=True),
    extend_existing=True,
)


class Requirement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "requirement"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("requirement.id"), nullable=True)

    req_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    level: Mapped[RequirementLevel] = mapped_column(sa.Enum(RequirementLevel, native_enum=False), nullable=False)
    category: Mapped[RequirementCategory] = mapped_column(sa.Enum(RequirementCategory, native_enum=False), nullable=False)
    title: Mapped[str] = mapped_column(sa.String, nullable=False)
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    priority: Mapped[Priority] = mapped_column(sa.Enum(Priority, native_enum=False), nullable=False, default=Priority.MANDATORY)
    status: Mapped[RequirementStatus] = mapped_column(sa.Enum(RequirementStatus, native_enum=False), nullable=False, default=RequirementStatus.DRAFT)
    ecss_ref: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    verification_method: Mapped[Optional[VerificationMethod]] = mapped_column(sa.Enum(VerificationMethod, native_enum=False), nullable=True)
    verification_level: Mapped[Optional[RequirementLevel]] = mapped_column(sa.Enum(RequirementLevel, native_enum=False), nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(sa.Enum(VerificationStatus, native_enum=False), nullable=False, default=VerificationStatus.NOT_STARTED)
    verification_evidence: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

    parent = relationship("Requirement", remote_side="Requirement.id", back_populates="children")
    children = relationship("Requirement", back_populates="parent")
    allocated_to = relationship("ProductNode", secondary=requirement_product_node, back_populates="requirements")
    mission = relationship("Mission", back_populates="requirements")
