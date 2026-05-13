from __future__ import annotations

import datetime
from typing import Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bepi.core.models.base import Base, TimestampMixin, UUIDMixin
from bepi.core.enums import *


class MatlabScript(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "matlab_script"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("mission.id"), nullable=False)

    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    script_path: Mapped[str] = mapped_column(sa.String, nullable=False)
    engine: Mapped[MatlabEngine] = mapped_column(sa.Enum(MatlabEngine, native_enum=False), nullable=False, default=MatlabEngine.OCTAVE)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    input_mapping: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)
    output_mapping: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)
    last_run: Mapped[Optional[datetime.datetime]] = mapped_column(sa.DateTime, nullable=True)
    last_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)

    mission = relationship("Mission", back_populates="matlab_scripts")
