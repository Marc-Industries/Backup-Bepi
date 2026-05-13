from __future__ import annotations

from typing import Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.models.base import Base, TimestampMixin, UUIDMixin
from bepi.core.enums import *


class RiskItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_item"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)

    risk_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    title: Mapped[str] = mapped_column(sa.String, nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    category: Mapped[RiskCategory] = mapped_column(sa.Enum(RiskCategory, native_enum=False), nullable=False)
    likelihood: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    consequence: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(sa.Enum(RiskLevel, native_enum=False), nullable=False)
    status: Mapped[RiskStatus] = mapped_column(sa.Enum(RiskStatus, native_enum=False), nullable=False, default=RiskStatus.OPEN)
    owner: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    mitigation_strategy: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    mitigation_actions: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)
    residual_likelihood: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    residual_consequence: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)

    @property
    def risk_score(self) -> int:
        return self.likelihood * self.consequence

    mission = relationship("Mission", back_populates="risk_items")
    fmeca_entries = relationship("FMECAEntry", back_populates="risk_item")


class FMECAEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "fmeca_entry"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("product_node.id"), nullable=False)
    risk_item_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("risk_item.id"), nullable=True)

    failure_mode: Mapped[str] = mapped_column(sa.String, nullable=False)
    failure_cause: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    local_effect: Mapped[str] = mapped_column(sa.String, nullable=False)
    system_effect: Mapped[str] = mapped_column(sa.String, nullable=False)
    severity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    occurrence: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    detection: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    mitigation: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    criticality: Mapped[Optional[Criticality]] = mapped_column(sa.Enum(Criticality, native_enum=False), nullable=True)

    @property
    def rpn(self) -> int:
        return self.severity * self.occurrence * self.detection

    product_node = relationship("ProductNode", back_populates="fmeca_entries")
    risk_item = relationship("RiskItem", back_populates="fmeca_entries")


class FaultTreeNode(Base, UUIDMixin):
    __tablename__ = "fault_tree_node"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("fault_tree_node.id"), nullable=True)
    node_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("product_node.id"), nullable=True)

    gate_type: Mapped[Optional[FTGateType]] = mapped_column(sa.Enum(FTGateType, native_enum=False), nullable=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    probability: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    k_of_n: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)

    parent = relationship("FaultTreeNode", remote_side="FaultTreeNode.id", back_populates="children")
    children = relationship("FaultTreeNode", back_populates="parent")
    product_node = relationship("ProductNode", back_populates="fault_tree_nodes")
