from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from bepi.core.enums import ComponentStatus, ProductLevel, SubsystemType


class OperatingModeCreate(BaseModel):
    mission_id: int
    name: str
    description: str | None = None
    is_default: bool = False


class OperatingModeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    name: str
    description: str | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ProductNodeCreate(BaseModel):
    mission_id: int
    parent_id: int | None = None
    level: ProductLevel
    code: str
    name: str
    subsystem_type: SubsystemType | None = None
    description: str | None = None
    is_leaf: bool = False
    quantity: int = 1
    manufacturer: str | None = None
    part_number: str | None = None
    trl: int | None = None
    heritage: str | None = None
    status: ComponentStatus = ComponentStatus.PROPOSED
    notes: str | None = None
    metadata_: dict | None = None


class ProductNodeUpdate(BaseModel):
    parent_id: int | None = None
    level: ProductLevel | None = None
    code: str | None = None
    name: str | None = None
    subsystem_type: SubsystemType | None = None
    description: str | None = None
    is_leaf: bool | None = None
    quantity: int | None = None
    manufacturer: str | None = None
    part_number: str | None = None
    trl: int | None = None
    heritage: str | None = None
    status: ComponentStatus | None = None
    notes: str | None = None
    metadata_: dict | None = None


class ProductNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    parent_id: int | None = None
    level: ProductLevel
    code: str
    name: str
    subsystem_type: SubsystemType | None = None
    description: str | None = None
    is_leaf: bool
    quantity: int
    manufacturer: str | None = None
    part_number: str | None = None
    trl: int | None = None
    heritage: str | None = None
    status: ComponentStatus
    notes: str | None = None
    metadata_: dict | None = None
    children: list[ProductNodeRead] = []
    created_at: datetime
    updated_at: datetime


ProductNodeRead.model_rebuild()
