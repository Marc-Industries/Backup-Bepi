from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from bepi.core.enums import (
    Priority,
    RequirementCategory,
    RequirementLevel,
    RequirementStatus,
    VerificationMethod,
    VerificationStatus,
)


class RequirementCreate(BaseModel):
    mission_id: int
    parent_id: int | None = None
    req_id: str
    level: RequirementLevel
    category: RequirementCategory
    title: str
    text: str
    rationale: str | None = None
    priority: Priority = Priority.MANDATORY
    status: RequirementStatus = RequirementStatus.DRAFT
    ecss_ref: str | None = None
    source: str | None = None
    verification_method: VerificationMethod | None = None
    verification_level: RequirementLevel | None = None
    verification_status: VerificationStatus = VerificationStatus.NOT_STARTED
    verification_evidence: str | None = None


class RequirementUpdate(BaseModel):
    parent_id: int | None = None
    req_id: str | None = None
    level: RequirementLevel | None = None
    category: RequirementCategory | None = None
    title: str | None = None
    text: str | None = None
    rationale: str | None = None
    priority: Priority | None = None
    status: RequirementStatus | None = None
    ecss_ref: str | None = None
    source: str | None = None
    verification_method: VerificationMethod | None = None
    verification_level: RequirementLevel | None = None
    verification_status: VerificationStatus | None = None
    verification_evidence: str | None = None


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    parent_id: int | None = None
    req_id: str
    level: RequirementLevel
    category: RequirementCategory
    title: str
    text: str
    rationale: str | None = None
    priority: Priority
    status: RequirementStatus
    ecss_ref: str | None = None
    source: str | None = None
    verification_method: VerificationMethod | None = None
    verification_level: RequirementLevel | None = None
    verification_status: VerificationStatus
    verification_evidence: str | None = None
    created_at: datetime
    updated_at: datetime


class VerificationMatrixRow(BaseModel):
    req_id: str
    title: str
    verification_method: VerificationMethod | None = None
    verification_level: RequirementLevel | None = None
    verification_status: VerificationStatus
    verification_evidence: str | None = None
    allocated_nodes: list[int]


class VerificationMatrixResponse(BaseModel):
    mission_id: int
    rows: list[VerificationMatrixRow]
    total: int
    passed: int
    failed: int
    not_started: int


class CoverageReportResponse(BaseModel):
    mission_id: int
    total_requirements: int
    allocated: int
    unallocated: int
    verified: int
    coverage_pct: float
    by_level: dict[str, int]
    by_category: dict[str, int]
    by_status: dict[str, int]
