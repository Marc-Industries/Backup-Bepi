from __future__ import annotations

import datetime
from typing import Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.models.base import Base, TimestampMixin, UUIDMixin
from bepi.core.enums import *


class ReviewGate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_gate"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)

    review_type: Mapped[ReviewType] = mapped_column(sa.Enum(ReviewType, native_enum=False), nullable=False)
    phase_before: Mapped[Phase] = mapped_column(sa.Enum(Phase, native_enum=False), nullable=False)
    phase_after: Mapped[Phase] = mapped_column(sa.Enum(Phase, native_enum=False), nullable=False)
    planned_date: Mapped[Optional[datetime.date]] = mapped_column(sa.Date, nullable=True)
    actual_date: Mapped[Optional[datetime.date]] = mapped_column(sa.Date, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(sa.Enum(ReviewStatus, native_enum=False), nullable=False, default=ReviewStatus.NOT_READY)
    board_members: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)
    minutes: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    entry_criteria: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)
    action_items: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)

    deliverables = relationship("ReviewDeliverable", back_populates="review_gate")
    milestones = relationship("Milestone", back_populates="review_gate")


class ReviewDeliverable(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_deliverable"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    review_gate_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("review_gate.id"), nullable=False)

    drd_code: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    title: Mapped[str] = mapped_column(sa.String, nullable=False)
    status: Mapped[DeliverableStatus] = mapped_column(sa.Enum(DeliverableStatus, native_enum=False), nullable=False, default=DeliverableStatus.NOT_STARTED)
    owner: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    due_date: Mapped[Optional[datetime.date]] = mapped_column(sa.Date, nullable=True)

    review_gate = relationship("ReviewGate", back_populates="deliverables")
