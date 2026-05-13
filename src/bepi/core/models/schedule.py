from __future__ import annotations

import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.models.base import Base, TimestampMixin, UUIDMixin
from bepi.core.enums import *


class WBSNode(Base, UUIDMixin):
    __tablename__ = "wbs_node"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("wbs_node.id"), nullable=True)
    node_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("product_node.id"), nullable=True)

    wbs_code: Mapped[str] = mapped_column(sa.String, nullable=False)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    level: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    parent = relationship("WBSNode", remote_side="WBSNode.id", back_populates="children")
    children = relationship("WBSNode", back_populates="parent")
    tasks = relationship("Task", back_populates="wbs_node")
    product_node = relationship("ProductNode", back_populates="wbs_nodes")


class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    wbs_node_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("wbs_node.id"), nullable=False)

    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    start_date: Mapped[Optional[datetime.date]] = mapped_column(sa.Date, nullable=True)
    end_date: Mapped[Optional[datetime.date]] = mapped_column(sa.Date, nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    progress_pct: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0)
    assigned_to: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    effort_person_days: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(sa.Enum(TaskStatus, native_enum=False), nullable=False, default=TaskStatus.NOT_STARTED)
    is_milestone: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    wbs_node = relationship("WBSNode", back_populates="tasks")
    predecessors = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.successor_id",
        back_populates="successor",
    )
    successors = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.predecessor_id",
        back_populates="predecessor",
    )


class TaskDependency(Base):
    __tablename__ = "task_dependency"

    predecessor_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("task.id"), primary_key=True)
    successor_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("task.id"), primary_key=True)
    dependency_type: Mapped[DependencyType] = mapped_column(sa.Enum(DependencyType, native_enum=False), nullable=False, default=DependencyType.FS)
    lag_days: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    predecessor = relationship("Task", foreign_keys=[predecessor_id], back_populates="successors")
    successor = relationship("Task", foreign_keys=[successor_id], back_populates="predecessors")


class Milestone(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "milestone"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)
    review_gate_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("review_gate.id"), nullable=True)

    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    target_date: Mapped[datetime.date] = mapped_column(sa.Date, nullable=False)
    actual_date: Mapped[Optional[datetime.date]] = mapped_column(sa.Date, nullable=True)
    status: Mapped[MilestoneStatus] = mapped_column(sa.Enum(MilestoneStatus, native_enum=False), nullable=False, default=MilestoneStatus.PLANNED)

    review_gate = relationship("ReviewGate", back_populates="milestones")
