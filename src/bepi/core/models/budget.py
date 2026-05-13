from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.enums import BudgetType, Maturity
from bepi.core.models.base import Base, TimestampMixin, UUIDMixin


class BudgetAllocation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "budget_allocation"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("product_node.id"), nullable=False)
    budget_type: Mapped[BudgetType] = mapped_column(sa.Enum(BudgetType, native_enum=False), nullable=False)
    operating_mode_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer, sa.ForeignKey("operating_mode.id"), nullable=True
    )
    nominal_value: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit: Mapped[str] = mapped_column(sa.String, nullable=False)
    margin_pct: Mapped[float] = mapped_column(sa.Float, default=0.0, nullable=False)
    maturity: Mapped[Maturity] = mapped_column(
        sa.Enum(Maturity, native_enum=False), default=Maturity.ESTIMATE, nullable=False
    )
    source: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    node = relationship("ProductNode", back_populates="allocations")
    operating_mode = relationship(
        "OperatingMode", back_populates="allocations"
    )

    @property
    def value_with_margin(self) -> float:
        return self.nominal_value * (1 + self.margin_pct / 100)


class BudgetLimit(TimestampMixin, Base):
    __tablename__ = "budget_limit"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)
    budget_type: Mapped[BudgetType] = mapped_column(sa.Enum(BudgetType, native_enum=False), nullable=False)
    operating_mode_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer, sa.ForeignKey("operating_mode.id"), nullable=True
    )
    limit_value: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit: Mapped[str] = mapped_column(sa.String, nullable=False)

    mission = relationship("Mission", back_populates="budget_limits")
    operating_mode = relationship(
        "OperatingMode", back_populates="budget_limits"
    )
