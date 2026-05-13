from __future__ import annotations

from typing import Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.models.base import Base, TimestampMixin, UUIDMixin
from bepi.core.enums import *


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)

    doc_number: Mapped[str] = mapped_column(sa.String, nullable=False)
    title: Mapped[str] = mapped_column(sa.String, nullable=False)
    doc_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    revision: Mapped[str] = mapped_column(sa.String, nullable=False)
    status: Mapped[DeliverableStatus] = mapped_column(sa.Enum(DeliverableStatus, native_enum=False), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", sa.JSON, nullable=True)

    mission = relationship("Mission", back_populates="documents")
