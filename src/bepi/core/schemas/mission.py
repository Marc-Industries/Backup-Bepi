from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from bepi.core.enums import Phase


class MissionCreate(BaseModel):
    name: str
    description: str | None = None
    phase: Phase | None = None
    orbit_type: str | None = None
    target_launch_date: date | None = None
    customer: str | None = None
    prime_contractor: str | None = None
    ecss_tailoring: dict | None = None
    metadata_: dict | None = None


class MissionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    phase: Phase | None = None
    orbit_type: str | None = None
    target_launch_date: date | None = None
    customer: str | None = None
    prime_contractor: str | None = None
    ecss_tailoring: dict | None = None
    metadata_: dict | None = None


class MissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    name: str
    description: str | None = None
    phase: Phase | None = None
    orbit_type: str | None = None
    target_launch_date: date | None = None
    customer: str | None = None
    prime_contractor: str | None = None
    ecss_tailoring: dict | None = None
    metadata_: dict | None = None
    created_at: datetime
    updated_at: datetime
