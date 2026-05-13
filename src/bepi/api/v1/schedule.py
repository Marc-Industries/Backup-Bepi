import datetime
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bepi.api.v1.deps import get_db
from bepi.core.models.schedule import Milestone, Task, TaskDependency, WBSNode
from bepi.core.schemas import (
    CPMResponse,
    CPMTaskResult,
    GanttResponse,
    GanttTask,
    MilestoneCreate,
    MilestoneRead,
    TaskCreate,
    TaskDependencyCreate,
    TaskRead,
    TaskUpdate,
    WBSNodeCreate,
    WBSNodeRead,
)

router = APIRouter(tags=["schedule"])

wbs_router = APIRouter(prefix="/wbs-nodes")
task_router = APIRouter(prefix="/tasks")
milestone_router = APIRouter(prefix="/milestones")
schedule_router = APIRouter(prefix="/missions/{mission_id}/schedule")


@wbs_router.get("", response_model=list[WBSNodeRead])
async def list_wbs(mission_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(WBSNode)
    if mission_id is not None:
        q = q.where(WBSNode.mission_id == mission_id)
    result = await db.execute(q.order_by(WBSNode.id))
    return result.scalars().all()


@wbs_router.post("", response_model=WBSNodeRead, status_code=status.HTTP_201_CREATED)
async def create_wbs(body: WBSNodeCreate, db: AsyncSession = Depends(get_db)):
    node = WBSNode(**body.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


@wbs_router.get("/{node_id}", response_model=WBSNodeRead)
async def get_wbs(node_id: int, db: AsyncSession = Depends(get_db)):
    node = await db.get(WBSNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="WBSNode not found")
    return node


@wbs_router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wbs(node_id: int, db: AsyncSession = Depends(get_db)):
    node = await db.get(WBSNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="WBSNode not found")
    await db.delete(node)
    await db.commit()


@task_router.get("", response_model=list[TaskRead])
async def list_tasks(wbs_node_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Task)
    if wbs_node_id is not None:
        q = q.where(Task.wbs_node_id == wbs_node_id)
    result = await db.execute(q.order_by(Task.id))
    return result.scalars().all()


@task_router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**body.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@task_router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@task_router.patch("/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, body: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@task_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()


@task_router.post("/{task_id}/dependencies", status_code=status.HTTP_201_CREATED)
async def add_dependency(task_id: int, body: TaskDependencyCreate, db: AsyncSession = Depends(get_db)):
    dep = TaskDependency(**body.model_dump())
    db.add(dep)
    await db.commit()
    return {"predecessor_id": dep.predecessor_id, "successor_id": dep.successor_id}


@milestone_router.get("", response_model=list[MilestoneRead])
async def list_milestones(mission_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Milestone)
    if mission_id is not None:
        q = q.where(Milestone.mission_id == mission_id)
    result = await db.execute(q.order_by(Milestone.target_date))
    return result.scalars().all()


@milestone_router.post("", response_model=MilestoneRead, status_code=status.HTTP_201_CREATED)
async def create_milestone(body: MilestoneCreate, db: AsyncSession = Depends(get_db)):
    ms = Milestone(**body.model_dump())
    db.add(ms)
    await db.commit()
    await db.refresh(ms)
    return ms


@milestone_router.get("/{ms_id}", response_model=MilestoneRead)
async def get_milestone(ms_id: int, db: AsyncSession = Depends(get_db)):
    ms = await db.get(Milestone, ms_id)
    if not ms:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return ms


@milestone_router.delete("/{ms_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_milestone(ms_id: int, db: AsyncSession = Depends(get_db)):
    ms = await db.get(Milestone, ms_id)
    if not ms:
        raise HTTPException(status_code=404, detail="Milestone not found")
    await db.delete(ms)
    await db.commit()


@schedule_router.get("/gantt", response_model=GanttResponse)
async def gantt_data(mission_id: int, db: AsyncSession = Depends(get_db)):
    wbs_result = await db.execute(
        select(WBSNode).where(WBSNode.mission_id == mission_id)
    )
    wbs_nodes = {n.id: n for n in wbs_result.scalars().all()}

    task_result = await db.execute(
        select(Task).where(Task.wbs_node_id.in_(wbs_nodes.keys()))
    )
    all_tasks = task_result.scalars().all()

    dep_result = await db.execute(
        select(TaskDependency).where(
            TaskDependency.successor_id.in_([t.id for t in all_tasks])
        )
    )
    preds_by_task: dict[int, list[int]] = defaultdict(list)
    for dep in dep_result.scalars().all():
        preds_by_task[dep.successor_id].append(dep.predecessor_id)

    ms_result = await db.execute(
        select(Milestone).where(Milestone.mission_id == mission_id)
    )
    milestones = ms_result.scalars().all()

    starts = [t.start_date for t in all_tasks if t.start_date]
    ends = [t.end_date for t in all_tasks if t.end_date]

    gantt_tasks = [
        GanttTask(
            task_id=t.id,
            wbs_code=wbs_nodes[t.wbs_node_id].wbs_code,
            name=t.name,
            start_date=t.start_date,
            end_date=t.end_date,
            duration_days=t.duration_days,
            progress_pct=t.progress_pct,
            status=t.status,
            assigned_to=t.assigned_to,
            predecessors=preds_by_task.get(t.id, []),
            is_milestone=t.is_milestone,
            is_critical=False,
        )
        for t in all_tasks
    ]

    return GanttResponse(
        mission_id=mission_id,
        tasks=gantt_tasks,
        milestones=[MilestoneRead.model_validate(m) for m in milestones],
        project_start=min(starts) if starts else None,
        project_end=max(ends) if ends else None,
    )


@schedule_router.get("/cpm", response_model=CPMResponse)
async def cpm(mission_id: int, db: AsyncSession = Depends(get_db)):
    wbs_result = await db.execute(
        select(WBSNode).where(WBSNode.mission_id == mission_id)
    )
    wbs_ids = [n.id for n in wbs_result.scalars().all()]

    task_result = await db.execute(
        select(Task).where(Task.wbs_node_id.in_(wbs_ids))
    )
    tasks = {t.id: t for t in task_result.scalars().all()}

    dep_result = await db.execute(
        select(TaskDependency).where(
            TaskDependency.predecessor_id.in_(tasks.keys())
        )
    )
    deps = dep_result.scalars().all()

    successors: dict[int, list[int]] = defaultdict(list)
    predecessors: dict[int, list[int]] = defaultdict(list)
    for d in deps:
        if d.predecessor_id in tasks and d.successor_id in tasks:
            successors[d.predecessor_id].append(d.successor_id)
            predecessors[d.successor_id].append(d.predecessor_id)

    in_degree = {tid: len(predecessors.get(tid, [])) for tid in tasks}
    queue = deque(tid for tid, deg in in_degree.items() if deg == 0)

    es: dict[int, datetime.date | None] = {}
    ef: dict[int, datetime.date | None] = {}
    for tid, t in tasks.items():
        es[tid] = t.start_date
        ef[tid] = t.end_date

    topo_order = []
    while queue:
        tid = queue.popleft()
        topo_order.append(tid)
        for sid in successors.get(tid, []):
            in_degree[sid] -= 1
            if in_degree[sid] == 0:
                queue.append(sid)

    for tid in topo_order:
        t = tasks[tid]
        if predecessors.get(tid):
            pred_efs = [ef[p] for p in predecessors[tid] if ef.get(p)]
            if pred_efs:
                es[tid] = max(pred_efs)
                if t.duration_days and es[tid]:
                    ef[tid] = es[tid] + datetime.timedelta(days=t.duration_days)

    ls: dict[int, datetime.date | None] = {tid: None for tid in tasks}
    lf: dict[int, datetime.date | None] = {tid: None for tid in tasks}
    project_end = max((d for d in ef.values() if d), default=None)
    for tid in reversed(topo_order):
        t = tasks[tid]
        if not successors.get(tid):
            lf[tid] = project_end
        else:
            succ_ls = [ls[s] for s in successors[tid] if ls.get(s)]
            lf[tid] = min(succ_ls) if succ_ls else project_end
        if lf[tid] and t.duration_days:
            ls[tid] = lf[tid] - datetime.timedelta(days=t.duration_days)

    def _days(a: datetime.date | None, b: datetime.date | None) -> int | None:
        if a is None or b is None:
            return None
        return (b - a).days

    cpm_tasks = []
    critical_ids = []
    for tid, t in tasks.items():
        tf = _days(es.get(tid), ls.get(tid))
        is_crit = tf == 0 if tf is not None else False
        if is_crit:
            critical_ids.append(tid)
        cpm_tasks.append(
            CPMTaskResult(
                task_id=tid,
                name=t.name,
                early_start=es.get(tid),
                early_finish=ef.get(tid),
                late_start=ls.get(tid),
                late_finish=lf.get(tid),
                total_float=tf,
                free_float=None,
                is_critical=is_crit,
            )
        )

    project_start = min((d for d in es.values() if d), default=None)
    duration = _days(project_start, project_end)

    return CPMResponse(
        mission_id=mission_id,
        tasks=cpm_tasks,
        critical_path_task_ids=critical_ids,
        project_duration_days=duration,
    )


router.include_router(wbs_router)
router.include_router(task_router)
router.include_router(milestone_router)
router.include_router(schedule_router)
