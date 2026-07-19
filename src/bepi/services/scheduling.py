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


def _as_date(v) -> date | None:
    """Coerce a task date (may be a date, an ISO string from the DB, or None)."""
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v:
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


def infer_predecessors_from_dates(tasks: list[TaskData]) -> None:
    """Reconstruct task dependencies from real start/end dates, in place.

    The schedule_tasks table stores no dependency column, so tasks loaded from the
    DB have empty `predecessors` and CPM degenerates (every task starts at t0 →
    critical path = just the longest tasks, project duration = longest single task).
    When tasks carry real dates, each task's driving predecessor is whichever
    task(s) finish latest at or before its start; wiring those makes CPM reproduce
    the real schedule (correct critical path, duration, end date). No-op if any
    explicit dependency already exists (don't override real data)."""
    if any(t.predecessors for t in tasks):
        return
    dated = [(t, _as_date(t.start_date), _as_date(t.end_date)) for t in tasks]
    for t, ts, _ in dated:
        if not ts:
            continue
        ends = [(o, oe) for o, os, oe in dated if o is not t and oe and oe <= ts]
        if ends:
            latest = max(oe for _, oe in ends)
            t.predecessors = [o.id for o, oe in ends if oe == latest]


def project_start_from_tasks(tasks: list[TaskData], default: date) -> date:
    """Earliest real task start, or `default` when no dates are present."""
    starts = [d for d in (_as_date(t.start_date) for t in tasks) if d]
    return min(starts) if starts else default


def gantt_data(tasks: list[TaskData], cpm_result: CPMResult, project_start: date) -> list[dict]:
    """Generate Gantt chart data for Plotly.
    Returns list of dicts with: Task, Start, Finish, Progress, Critical, WBS, Resource
    """
    result = []
    for t in tasks:
        info = cpm_result.tasks.get(t.id, {})
        # Prefer the task's own planned dates (from the DB) so the bars reflect the
        # real schedule; fall back to the CPM early-start/finish when dates are absent
        # (e.g. mock data, or tasks with no stored dates -> everything at project_start).
        ts, te = _as_date(t.start_date), _as_date(t.end_date)
        if ts and te:
            start, end = ts, te
        else:
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
