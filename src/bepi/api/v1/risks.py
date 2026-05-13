from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bepi.api.v1.deps import get_db
from bepi.core.models.risk import FMECAEntry, FaultTreeNode, RiskItem
from bepi.core.schemas import (
    FMECAEntryCreate,
    FMECAEntryRead,
    FaultTreeNodeCreate,
    FaultTreeNodeRead,
    RiskItemCreate,
    RiskItemRead,
    RiskItemUpdate,
    RiskMatrixCell,
    RiskMatrixResponse,
)

router = APIRouter(tags=["risks"])

risk_router = APIRouter(prefix="/risks")
fmeca_router = APIRouter(prefix="/fmeca")
fta_router = APIRouter(prefix="/fault-tree-nodes")


@risk_router.get("", response_model=list[RiskItemRead])
async def list_risks(mission_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(RiskItem)
    if mission_id is not None:
        q = q.where(RiskItem.mission_id == mission_id)
    result = await db.execute(q.order_by(RiskItem.id))
    return result.scalars().all()


@risk_router.post("", response_model=RiskItemRead, status_code=status.HTTP_201_CREATED)
async def create_risk(body: RiskItemCreate, db: AsyncSession = Depends(get_db)):
    risk = RiskItem(**body.model_dump())
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    return risk


@risk_router.get("/{risk_id}", response_model=RiskItemRead)
async def get_risk(risk_id: int, db: AsyncSession = Depends(get_db)):
    risk = await db.get(RiskItem, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="RiskItem not found")
    return risk


@risk_router.patch("/{risk_id}", response_model=RiskItemRead)
async def update_risk(risk_id: int, body: RiskItemUpdate, db: AsyncSession = Depends(get_db)):
    risk = await db.get(RiskItem, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="RiskItem not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(risk, field, value)
    await db.commit()
    await db.refresh(risk)
    return risk


@risk_router.delete("/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk(risk_id: int, db: AsyncSession = Depends(get_db)):
    risk = await db.get(RiskItem, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="RiskItem not found")
    await db.delete(risk)
    await db.commit()


@risk_router.get("/missions/{mission_id}/matrix", response_model=RiskMatrixResponse)
async def risk_matrix(mission_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskItem).where(RiskItem.mission_id == mission_id)
    )
    risks = result.scalars().all()

    cells_dict: dict[tuple, RiskMatrixCell] = {}
    by_level: dict[str, int] = {}
    by_status: dict[str, int] = {}

    for r in risks:
        key = (r.likelihood, r.consequence)
        if key not in cells_dict:
            cells_dict[key] = RiskMatrixCell(
                likelihood=r.likelihood,
                consequence=r.consequence,
                risk_level=r.risk_level,
                risk_ids=[],
                count=0,
            )
        cells_dict[key].risk_ids.append(r.risk_id)
        cells_dict[key].count += 1
        by_level[r.risk_level.value] = by_level.get(r.risk_level.value, 0) + 1
        by_status[r.status.value] = by_status.get(r.status.value, 0) + 1

    return RiskMatrixResponse(
        mission_id=mission_id,
        cells=list(cells_dict.values()),
        total_risks=len(risks),
        by_level=by_level,
        by_status=by_status,
    )


@fmeca_router.get("", response_model=list[FMECAEntryRead])
async def list_fmeca(node_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(FMECAEntry)
    if node_id is not None:
        q = q.where(FMECAEntry.node_id == node_id)
    result = await db.execute(q.order_by(FMECAEntry.id))
    return result.scalars().all()


@fmeca_router.post("", response_model=FMECAEntryRead, status_code=status.HTTP_201_CREATED)
async def create_fmeca(body: FMECAEntryCreate, db: AsyncSession = Depends(get_db)):
    entry = FMECAEntry(**body.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@fmeca_router.get("/{entry_id}", response_model=FMECAEntryRead)
async def get_fmeca(entry_id: int, db: AsyncSession = Depends(get_db)):
    entry = await db.get(FMECAEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="FMECAEntry not found")
    return entry


@fmeca_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fmeca(entry_id: int, db: AsyncSession = Depends(get_db)):
    entry = await db.get(FMECAEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="FMECAEntry not found")
    await db.delete(entry)
    await db.commit()


@fta_router.get("", response_model=list[FaultTreeNodeRead])
async def list_fta_nodes(mission_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(FaultTreeNode)
    if mission_id is not None:
        q = q.where(FaultTreeNode.mission_id == mission_id)
    result = await db.execute(q.order_by(FaultTreeNode.id))
    return result.scalars().all()


@fta_router.post("", response_model=FaultTreeNodeRead, status_code=status.HTTP_201_CREATED)
async def create_fta_node(body: FaultTreeNodeCreate, db: AsyncSession = Depends(get_db)):
    node = FaultTreeNode(**body.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


@fta_router.get("/{node_id}", response_model=FaultTreeNodeRead)
async def get_fta_node(node_id: int, db: AsyncSession = Depends(get_db)):
    node = await db.get(FaultTreeNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="FaultTreeNode not found")
    return node


@fta_router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fta_node(node_id: int, db: AsyncSession = Depends(get_db)):
    node = await db.get(FaultTreeNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="FaultTreeNode not found")
    await db.delete(node)
    await db.commit()


router.include_router(risk_router)
router.include_router(fmeca_router)
router.include_router(fta_router)
