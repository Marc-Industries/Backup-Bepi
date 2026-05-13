from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from bepi.core.enums import DependencyType, MilestoneStatus, TaskStatus


class WBSNodeCreate(BaseModel):
    mission_id: int
    parent_id: int | None = None
    node_id: int | None = None
    wbs_code: str
    name: str
    level: int


class WBSNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    parent_id: int | None = None
    node_id: int | None = None
    wbs_code: str
    name: str
    level: int
    children: list[WBSNodeRead] = []


WBSNodeRead.model_rebuild()


class TaskCreate(BaseModel):
    wbs_node_id: int
    name: str
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    progress_pct: float = 0.0
    assigned_to: str | None = None
    effort_person_days: float | None = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    is_milestone: bool = False
    notes: str | None = None


class TaskUpdate(BaseModel):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    progress_pct: float | None = None
    assigned_to: str | None = None
    effort_person_days: float | None = None
    status: TaskStatus | None = None
    is_milestone: bool | None = None
    notes: str | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    wbs_node_id: int
    name: str
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    progress_pct: float
    assigned_to: str | None = None
    effort_person_days: float | None = None
    status: TaskStatus
    is_milestone: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskDependencyCreate(BaseModel):
    predecessor_id: int
    successor_id: int
    dependency_type: DependencyType = DependencyType.FS
    lag_days: int = 0


class MilestoneCreate(BaseModel):
    mission_id: int
    review_gate_id: int | None = None
    name: str
    target_date: date
    actual_date: date | None = None
    status: MilestoneStatus = MilestoneStatus.PLANNED


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    mission_id: int
    review_gate_id: int | None = None
    name: str
    target_date: date
    actual_date: date | None = None
    status: MilestoneStatus
    created_at: datetime
    updated_at: datetime


class GanttTask(BaseModel):
    task_id: int
    wbs_code: str
    name: str
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    progress_pct: float
    status: TaskStatus
    assigned_to: str | None = None
    predecessors: list[int]
    is_milestone: bool
    is_critical: bool


class GanttResponse(BaseModel):
    mission_id: int
    tasks: list[GanttTask]
    milestones: list[MilestoneRead]
    project_start: date | None = None
    project_end: date | None = None


class CPMTaskResult(BaseModel):
    task_id: int
    name: str
    early_start: date | None = None
    early_finish: date | None = None
    late_start: date | None = None
    late_finish: date | None = None
    total_float: int | None = None
    free_float: int | None = None
    is_critical: bool


class CPMResponse(BaseModel):
    mission_id: int
    tasks: list[CPMTaskResult]
    critical_path_task_ids: list[int]
    project_duration_days: int | None = None
