from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from bepi.core.enums import DeliverableStatus, Phase, ReviewStatus, ReviewType


class ReviewGateCreate(BaseModel):
    mission_id: int
    review_type: ReviewType
    phase_before: Phase
    phase_after: Phase
    planned_date: date | None = None
    actual_date: date | None = None
    status: ReviewStatus = ReviewStatus.NOT_READY
    board_members: dict[str, Any] | None = None
    minutes: str | None = None
    entry_criteria: dict[str, Any] | None = None
    action_items: dict[str, Any] | None = None


class ReviewGateUpdate(BaseModel):
    review_type: ReviewType | None = None
    phase_before: Phase | None = None
    phase_after: Phase | None = None
    planned_date: date | None = None
    actual_date: date | None = None
    status: ReviewStatus | None = None
    board_members: dict[str, Any] | None = None
    minutes: str | None = None
    entry_criteria: dict[str, Any] | None = None
    action_items: dict[str, Any] | None = None


class ReviewGateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    review_type: ReviewType
    phase_before: Phase
    phase_after: Phase
    planned_date: date | None = None
    actual_date: date | None = None
    status: ReviewStatus
    board_members: dict[str, Any] | None = None
    minutes: str | None = None
    entry_criteria: dict[str, Any] | None = None
    action_items: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ReviewDeliverableCreate(BaseModel):
    review_gate_id: int
    drd_code: str | None = None
    title: str
    status: DeliverableStatus = DeliverableStatus.NOT_STARTED
    owner: str | None = None
    due_date: date | None = None


class ReviewDeliverableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    review_gate_id: int
    drd_code: str | None = None
    title: str
    status: DeliverableStatus
    owner: str | None = None
    due_date: date | None = None
    created_at: datetime
    updated_at: datetime
