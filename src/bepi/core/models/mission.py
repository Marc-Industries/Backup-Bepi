import uuid
from datetime import date, datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.enums import Phase
from bepi.core.models.base import Base, TimestampMixin, UUIDMixin


class Mission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "mission"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    phase: Mapped[Optional[Phase]] = mapped_column(sa.Enum(Phase, native_enum=False), nullable=True)
    orbit_type: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    target_launch_date: Mapped[Optional[date]] = mapped_column(sa.Date, nullable=True)
    customer: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    prime_contractor: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    ecss_tailoring: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    product_nodes = relationship(
        "ProductNode",
        back_populates="mission",
        cascade="all, delete-orphan",
        foreign_keys="ProductNode.mission_id",
    )
    operating_modes = relationship(
        "OperatingMode",
        back_populates="mission",
        cascade="all, delete-orphan",
    )
    budget_limits = relationship(
        "BudgetLimit",
        back_populates="mission",
        cascade="all, delete-orphan",
    )
    requirements = relationship(
        "Requirement",
        back_populates="mission",
        cascade="all, delete-orphan",
    )
    risk_items = relationship(
        "RiskItem",
        back_populates="mission",
        cascade="all, delete-orphan",
    )
    documents = relationship(
        "Document",
        back_populates="mission",
        cascade="all, delete-orphan",
    )
    matlab_scripts = relationship(
        "MatlabScript",
        back_populates="mission",
        cascade="all, delete-orphan",
    )
