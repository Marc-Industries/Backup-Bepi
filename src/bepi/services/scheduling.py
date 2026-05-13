"""Scheduling: WBS, Gantt, CPM/PERT."""
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class TaskData:
    id: str
    name: str
    duration_days: int
    predecessors: list[str] = field(default_factory=list)  # task IDs
    start_date: date | None = None
    end_date: date | None = None
    progress_pct: float = 0
    is_milestone: bool = False
    wbs_code: str = ""
    assigned_to: str = ""


@dataclass
class CPMResult:
    """Result of Critical Path Method analysis."""
    tasks: dict[str, dict]  # task_id → {ES, EF, LS, LF, slack}
    critical_path: list[str]  # ordered list of task IDs on critical path
    project_duration: int  # days
    project_end_date: date | None


def compute_cpm(tasks: list[TaskData], project_start: date | None = None) -> CPMResult:
    """Compute Critical Path Method.

    Forward pass: compute ES (Early Start) and EF (Early Finish)
    Backward pass: compute LS (Late Start) and LF (Late Finish)
    Slack = LS - ES (or LF - EF)
    Critical path = tasks with slack == 0
    """
    task_map = {t.id: t for t in tasks}
    info = {}

    # Initialize
    for t in tasks:
        info[t.id] = {"ES": 0, "EF": 0, "LS": 0, "LF": 0, "slack": 0}

    # Forward pass (topological order)
    visited = set()
    order = []

    def topo_visit(tid):
        if tid in visited:
            return
        visited.add(tid)
        for pred_id in task_map[tid].predecessors:
            if pred_id in task_map:
                topo_visit(pred_id)
        order.append(tid)

    for t in tasks:
        topo_visit(t.id)

    for tid in order:
        t = task_map[tid]
        es = 0
        for pred_id in t.predecessors:
            if pred_id in info:
                es = max(es, info[pred_id]["EF"])
        info[tid]["ES"] = es
        info[tid]["EF"] = es + t.duration_days

    # Project duration
    project_duration = max(info[tid]["EF"] for tid in info) if info else 0

    # Backward pass
    for tid in info:
        info[tid]["LF"] = project_duration

    for tid in reversed(order):
        t = task_map[tid]
        # Find successors
        successors = [t2.id for t2 in tasks if tid in t2.predecessors]
        if successors:
            info[tid]["LF"] = min(info[s]["LS"] for s in successors)
        else:
            info[tid]["LF"] = project_duration
        info[tid]["LS"] = info[tid]["LF"] - t.duration_days
        info[tid]["slack"] = info[tid]["LS"] - info[tid]["ES"]

    # Critical path
    critical = [tid for tid in order if info[tid]["slack"] == 0]

    # Compute dates if project_start given
    project_end = None
    if project_start:
        for tid in info:
            info[tid]["start_date"] = project_start + timedelta(days=info[tid]["ES"])
            info[tid]["end_date"] = project_start + timedelta(days=info[tid]["EF"])
        project_end = project_start + timedelta(days=project_duration)

    return CPMResult(
        tasks=info,
        critical_path=critical,
        project_duration=project_duration,
        project_end_date=project_end,
    )


def gantt_data(tasks: list[TaskData], cpm_result: CPMResult, project_start: date) -> list[dict]:
    """Generate Gantt chart data for Plotly.
    Returns list of dicts with: Task, Start, Finish, Progress, Critical, WBS, Resource
    """
    result = []
    for t in tasks:
        info = cpm_result.tasks.get(t.id, {})
        start = project_start + timedelta(days=info.get("ES", 0))
        end = project_start + timedelta(days=info.get("EF", 0))
        is_critical = t.id in cpm_result.critical_path

        result.append({
            "Task": t.name,
            "Start": start.isoformat(),
            "Finish": end.isoformat(),
            "Progress": t.progress_pct,
            "Critical": is_critical,
            "WBS": t.wbs_code,
            "Resource": t.assigned_to,
        })
    return result
