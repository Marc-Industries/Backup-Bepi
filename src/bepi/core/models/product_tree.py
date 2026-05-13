import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.enums import ComponentStatus, ProductLevel, SubsystemType
from bepi.core.models.base import Base, TimestampMixin, UUIDMixin


node_requirement_association = sa.Table(
    "requirement_product_node",
    Base.metadata,
    sa.Column("node_id", sa.Integer, sa.ForeignKey("product_node.id"), primary_key=True),
    sa.Column("requirement_id", sa.Integer, sa.ForeignKey("requirement.id"), primary_key=True),
    extend_existing=True,
)


class ProductNode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_node"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("product_node.id"), nullable=True)
    level: Mapped[ProductLevel] = mapped_column(sa.Enum(ProductLevel, native_enum=False), nullable=False)
    code: Mapped[str] = mapped_column(sa.String, nullable=False)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    subsystem_type: Mapped[Optional[SubsystemType]] = mapped_column(
        sa.Enum(SubsystemType, native_enum=False), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    is_leaf: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    quantity: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    part_number: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    trl: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    heritage: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    status: Mapped[ComponentStatus] = mapped_column(
        sa.Enum(ComponentStatus, native_enum=False), default=ComponentStatus.PROPOSED, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    mission = relationship(
        "Mission",
        back_populates="product_nodes",
        foreign_keys=[mission_id],
    )
    parent = relationship(
        "ProductNode",
        back_populates="children",
        remote_side="ProductNode.id",
    )
    children = relationship(
        "ProductNode",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    allocations = relationship(
        "BudgetAllocation",
        back_populates="node",
        cascade="all, delete-orphan",
    )
    requirements = relationship(
        "Requirement",
        secondary=node_requirement_association,
        back_populates="allocated_to",
    )
    fmeca_entries = relationship(
        "FMECAEntry",
        back_populates="product_node",
        cascade="all, delete-orphan",
    )
    fault_tree_nodes = relationship(
        "FaultTreeNode",
        back_populates="product_node",
    )
    wbs_nodes = relationship(
        "WBSNode",
        back_populates="product_node",
    )


class OperatingMode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "operating_mode"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    mission = relationship("Mission", back_populates="operating_modes")
    allocations = relationship(
        "BudgetAllocation",
        back_populates="operating_mode",
    )
    budget_limits = relationship(
        "BudgetLimit",
        back_populates="operating_mode",
    )
