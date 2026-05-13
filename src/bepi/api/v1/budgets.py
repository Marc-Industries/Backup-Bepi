from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bepi.api.v1.deps import get_db
from bepi.core.enums import BudgetType, MarginStatus
from bepi.core.models.budget import BudgetAllocation, BudgetLimit
from bepi.core.models.product_tree import ProductNode
from bepi.core.schemas import (
    BudgetAllocationCreate,
    BudgetAllocationRead,
    BudgetAllocationUpdate,
    BudgetLimitCreate,
    BudgetLimitRead,
    BudgetLineItem,
    BudgetRollupNode,
    BudgetRollupResponse,
    BudgetSummaryResponse,
)

router = APIRouter(tags=["budgets"])

alloc_router = APIRouter(prefix="/budget-allocations")
limit_router = APIRouter(prefix="/budget-limits")
rollup_router = APIRouter(prefix="/missions/{mission_id}/budget")


@alloc_router.get("", response_model=list[BudgetAllocationRead])
async def list_allocations(node_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(BudgetAllocation)
    if node_id is not None:
        q = q.where(BudgetAllocation.node_id == node_id)
    result = await db.execute(q.order_by(BudgetAllocation.id))
    return result.scalars().all()


@alloc_router.post("", response_model=BudgetAllocationRead, status_code=status.HTTP_201_CREATED)
async def create_allocation(body: BudgetAllocationCreate, db: AsyncSession = Depends(get_db)):
    alloc = BudgetAllocation(**body.model_dump())
    db.add(alloc)
    await db.commit()
    await db.refresh(alloc)
    return alloc


@alloc_router.get("/{alloc_id}", response_model=BudgetAllocationRead)
async def get_allocation(alloc_id: int, db: AsyncSession = Depends(get_db)):
    alloc = await db.get(BudgetAllocation, alloc_id)
    if not alloc:
        raise HTTPException(status_code=404, detail="BudgetAllocation not found")
    return alloc


@alloc_router.patch("/{alloc_id}", response_model=BudgetAllocationRead)
async def update_allocation(alloc_id: int, body: BudgetAllocationUpdate, db: AsyncSession = Depends(get_db)):
    alloc = await db.get(BudgetAllocation, alloc_id)
    if not alloc:
        raise HTTPException(status_code=404, detail="BudgetAllocation not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(alloc, field, value)
    await db.commit()
    await db.refresh(alloc)
    return alloc


@alloc_router.delete("/{alloc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_allocation(alloc_id: int, db: AsyncSession = Depends(get_db)):
    alloc = await db.get(BudgetAllocation, alloc_id)
    if not alloc:
        raise HTTPException(status_code=404, detail="BudgetAllocation not found")
    await db.delete(alloc)
    await db.commit()


@limit_router.get("", response_model=list[BudgetLimitRead])
async def list_limits(mission_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(BudgetLimit)
    if mission_id is not None:
        q = q.where(BudgetLimit.mission_id == mission_id)
    result = await db.execute(q.order_by(BudgetLimit.id))
    return result.scalars().all()


@limit_router.post("", response_model=BudgetLimitRead, status_code=status.HTTP_201_CREATED)
async def create_limit(body: BudgetLimitCreate, db: AsyncSession = Depends(get_db)):
    limit = BudgetLimit(**body.model_dump())
    db.add(limit)
    await db.commit()
    await db.refresh(limit)
    return limit


@limit_router.get("/{limit_id}", response_model=BudgetLimitRead)
async def get_limit(limit_id: int, db: AsyncSession = Depends(get_db)):
    limit = await db.get(BudgetLimit, limit_id)
    if not limit:
        raise HTTPException(status_code=404, detail="BudgetLimit not found")
    return limit


@limit_router.delete("/{limit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_limit(limit_id: int, db: AsyncSession = Depends(get_db)):
    limit = await db.get(BudgetLimit, limit_id)
    if not limit:
        raise HTTPException(status_code=404, detail="BudgetLimit not found")
    await db.delete(limit)
    await db.commit()


@rollup_router.get("/summary", response_model=BudgetSummaryResponse)
async def budget_summary(
    mission_id: int,
    budget_type: BudgetType = Query(...),
    operating_mode_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    nodes_result = await db.execute(
        select(ProductNode).where(ProductNode.mission_id == mission_id)
    )
    nodes = {n.id: n for n in nodes_result.scalars().all()}

    q = select(BudgetAllocation).where(
        BudgetAllocation.node_id.in_(nodes.keys()),
        BudgetAllocation.budget_type == budget_type,
    )
    if operating_mode_id is not None:
        q = q.where(BudgetAllocation.operating_mode_id == operating_mode_id)
    allocs_result = await db.execute(q)
    allocs = allocs_result.scalars().all()

    unit = allocs[0].unit if allocs else ""
    total_nominal = sum(a.nominal_value for a in allocs)
    total_with_margin = sum(a.value_with_margin for a in allocs)

    limit_q = select(BudgetLimit).where(
        BudgetLimit.mission_id == mission_id,
        BudgetLimit.budget_type == budget_type,
    )
    if operating_mode_id is not None:
        limit_q = limit_q.where(BudgetLimit.operating_mode_id == operating_mode_id)
    limit_result = await db.execute(limit_q)
    limit_row = limit_result.scalar_one_or_none()
    limit_value = limit_row.limit_value if limit_row else None

    margin_status = None
    if limit_value and limit_value > 0:
        pct_remaining = (limit_value - total_with_margin) / limit_value * 100
        if pct_remaining < 10:
            margin_status = MarginStatus.RED
        elif pct_remaining < 20:
            margin_status = MarginStatus.YELLOW
        else:
            margin_status = MarginStatus.GREEN

    items = [
        BudgetLineItem(
            node_id=a.node_id,
            node_code=nodes[a.node_id].code,
            node_name=nodes[a.node_id].name,
            nominal_value=a.nominal_value,
            value_with_margin=a.value_with_margin,
            unit=a.unit,
            margin_pct=a.margin_pct,
            maturity=a.maturity,
        )
        for a in allocs
        if a.node_id in nodes
    ]

    return BudgetSummaryResponse(
        mission_id=mission_id,
        budget_type=budget_type,
        operating_mode_id=operating_mode_id,
        unit=unit,
        total_nominal=total_nominal,
        total_with_margin=total_with_margin,
        limit_value=limit_value,
        margin_status=margin_status,
        items=items,
    )


def _build_rollup_node(node: ProductNode, allocs_by_node: dict, nodes_by_parent: dict) -> BudgetRollupNode:
    children_nodes = nodes_by_parent.get(node.id, [])
    if children_nodes:
        children = [_build_rollup_node(c, allocs_by_node, nodes_by_parent) for c in children_nodes]
        nominal = sum(c.nominal_value for c in children)
        with_margin = sum(c.value_with_margin for c in children)
        unit = children[0].unit if children else ""
    else:
        node_allocs = allocs_by_node.get(node.id, [])
        nominal = sum(a.nominal_value for a in node_allocs)
        with_margin = sum(a.value_with_margin for a in node_allocs)
        unit = node_allocs[0].unit if node_allocs else ""
        children = []

    return BudgetRollupNode(
        node_id=node.id,
        node_code=node.code,
        node_name=node.name,
        nominal_value=nominal,
        value_with_margin=with_margin,
        unit=unit,
        children=children,
    )


@rollup_router.get("/rollup", response_model=BudgetRollupResponse)
async def budget_rollup(
    mission_id: int,
    budget_type: BudgetType = Query(...),
    operating_mode_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    nodes_result = await db.execute(
        select(ProductNode).where(ProductNode.mission_id == mission_id)
    )
    all_nodes = nodes_result.scalars().all()
    nodes_by_parent: dict[int | None, list] = {}
    for n in all_nodes:
        nodes_by_parent.setdefault(n.parent_id, []).append(n)

    q = select(BudgetAllocation).where(
        BudgetAllocation.node_id.in_([n.id for n in all_nodes]),
        BudgetAllocation.budget_type == budget_type,
    )
    if operating_mode_id is not None:
        q = q.where(BudgetAllocation.operating_mode_id == operating_mode_id)
    allocs_result = await db.execute(q)
    allocs_by_node: dict[int, list] = {}
    unit = ""
    for a in allocs_result.scalars().all():
        allocs_by_node.setdefault(a.node_id, []).append(a)
        unit = a.unit

    roots = nodes_by_parent.get(None, [])
    tree = [_build_rollup_node(r, allocs_by_node, nodes_by_parent) for r in roots]

    return BudgetRollupResponse(
        mission_id=mission_id,
        budget_type=budget_type,
        operating_mode_id=operating_mode_id,
        unit=unit,
        tree=tree,
    )


router.include_router(alloc_router)
router.include_router(limit_router)
router.include_router(rollup_router)
