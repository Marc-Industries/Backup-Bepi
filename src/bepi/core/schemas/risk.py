from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from bepi.core.enums import Criticality, FTGateType, RiskCategory, RiskLevel, RiskStatus


class RiskItemCreate(BaseModel):
    mission_id: int
    risk_id: str
    title: str
    description: str
    category: RiskCategory
    likelihood: int
    consequence: int
    risk_level: RiskLevel
    status: RiskStatus = RiskStatus.OPEN
    owner: str | None = None
    mitigation_strategy: str | None = None
    mitigation_actions: dict[str, Any] | None = None
    residual_likelihood: int | None = None
    residual_consequence: int | None = None


class RiskItemUpdate(BaseModel):
    risk_id: str | None = None
    title: str | None = None
    description: str | None = None
    category: RiskCategory | None = None
    likelihood: int | None = None
    consequence: int | None = None
    risk_level: RiskLevel | None = None
    status: RiskStatus | None = None
    owner: str | None = None
    mitigation_strategy: str | None = None
    mitigation_actions: dict[str, Any] | None = None
    residual_likelihood: int | None = None
    residual_consequence: int | None = None


class RiskItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    risk_id: str
    title: str
    description: str
    category: RiskCategory
    likelihood: int
    consequence: int
    risk_level: RiskLevel
    risk_score: int
    status: RiskStatus
    owner: str | None = None
    mitigation_strategy: str | None = None
    mitigation_actions: dict[str, Any] | None = None
    residual_likelihood: int | None = None
    residual_consequence: int | None = None
    created_at: datetime
    updated_at: datetime


class FMECAEntryCreate(BaseModel):
    node_id: int
    risk_item_id: int | None = None
    failure_mode: str
    failure_cause: str | None = None
    local_effect: str
    system_effect: str
    severity: int
    occurrence: int
    detection: int
    mitigation: str | None = None
    criticality: Criticality | None = None


class FMECAEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    node_id: int
    risk_item_id: int | None = None
    failure_mode: str
    failure_cause: str | None = None
    local_effect: str
    system_effect: str
    severity: int
    occurrence: int
    detection: int
    rpn: int
    mitigation: str | None = None
    criticality: Criticality | None = None
    created_at: datetime
    updated_at: datetime


class FaultTreeNodeCreate(BaseModel):
    mission_id: int
    parent_id: int | None = None
    node_id: int | None = None
    gate_type: FTGateType | None = None
    name: str
    description: str | None = None
    probability: float | None = None
    k_of_n: int | None = None


class FaultTreeNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    parent_id: int | None = None
    node_id: int | None = None
    gate_type: FTGateType | None = None
    name: str
    description: str | None = None
    probability: float | None = None
    k_of_n: int | None = None
    children: list[FaultTreeNodeRead] = []


FaultTreeNodeRead.model_rebuild()


class RiskMatrixCell(BaseModel):
    likelihood: int
    consequence: int
    risk_level: RiskLevel
    risk_ids: list[str]
    count: int


class RiskMatrixResponse(BaseModel):
    mission_id: int
    cells: list[RiskMatrixCell]
    total_risks: int
    by_level: dict[str, int]
    by_status: dict[str, int]
