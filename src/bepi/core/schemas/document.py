from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from bepi.core.enums import DeliverableStatus


class DocumentCreate(BaseModel):
    mission_id: int
    doc_number: str
    title: str
    doc_type: str
    revision: str
    status: DeliverableStatus
    author: str | None = None
    file_path: str | None = None
    metadata_: dict[str, Any] | None = None


class DocumentUpdate(BaseModel):
    doc_number: str | None = None
    title: str | None = None
    doc_type: str | None = None
    revision: str | None = None
    status: DeliverableStatus | None = None
    author: str | None = None
    file_path: str | None = None
    metadata_: dict[str, Any] | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    doc_number: str
    title: str
    doc_type: str
    revision: str
    status: DeliverableStatus
    author: str | None = None
    file_path: str | None = None
    metadata_: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
