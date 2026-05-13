from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bepi.api.v1.deps import get_db
from bepi.core.models.review import ReviewDeliverable, ReviewGate
from bepi.core.schemas import (
    ReviewDeliverableCreate,
    ReviewDeliverableRead,
    ReviewGateCreate,
    ReviewGateRead,
    ReviewGateUpdate,
)

router = APIRouter(tags=["reviews"])

gate_router = APIRouter(prefix="/review-gates")
deliverable_router = APIRouter(prefix="/review-deliverables")


@gate_router.get("", response_model=list[ReviewGateRead])
async def list_gates(mission_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(ReviewGate)
    if mission_id is not None:
        q = q.where(ReviewGate.mission_id == mission_id)
    result = await db.execute(q.order_by(ReviewGate.planned_date.nullsfirst(), ReviewGate.id))
    return result.scalars().all()


@gate_router.post("", response_model=ReviewGateRead, status_code=status.HTTP_201_CREATED)
async def create_gate(body: ReviewGateCreate, db: AsyncSession = Depends(get_db)):
    gate = ReviewGate(**body.model_dump())
    db.add(gate)
    await db.commit()
    await db.refresh(gate)
    return gate


@gate_router.get("/{gate_id}", response_model=ReviewGateRead)
async def get_gate(gate_id: int, db: AsyncSession = Depends(get_db)):
    gate = await db.get(ReviewGate, gate_id)
    if not gate:
        raise HTTPException(status_code=404, detail="ReviewGate not found")
    return gate


@gate_router.patch("/{gate_id}", response_model=ReviewGateRead)
async def update_gate(gate_id: int, body: ReviewGateUpdate, db: AsyncSession = Depends(get_db)):
    gate = await db.get(ReviewGate, gate_id)
    if not gate:
        raise HTTPException(status_code=404, detail="ReviewGate not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(gate, field, value)
    await db.commit()
    await db.refresh(gate)
    return gate


@gate_router.delete("/{gate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gate(gate_id: int, db: AsyncSession = Depends(get_db)):
    gate = await db.get(ReviewGate, gate_id)
    if not gate:
        raise HTTPException(status_code=404, detail="ReviewGate not found")
    await db.delete(gate)
    await db.commit()


@deliverable_router.get("", response_model=list[ReviewDeliverableRead])
async def list_deliverables(review_gate_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(ReviewDeliverable)
    if review_gate_id is not None:
        q = q.where(ReviewDeliverable.review_gate_id == review_gate_id)
    result = await db.execute(q.order_by(ReviewDeliverable.id))
    return result.scalars().all()


@deliverable_router.post("", response_model=ReviewDeliverableRead, status_code=status.HTTP_201_CREATED)
async def create_deliverable(body: ReviewDeliverableCreate, db: AsyncSession = Depends(get_db)):
    deliv = ReviewDeliverable(**body.model_dump())
    db.add(deliv)
    await db.commit()
    await db.refresh(deliv)
    return deliv


@deliverable_router.get("/{deliv_id}", response_model=ReviewDeliverableRead)
async def get_deliverable(deliv_id: int, db: AsyncSession = Depends(get_db)):
    deliv = await db.get(ReviewDeliverable, deliv_id)
    if not deliv:
        raise HTTPException(status_code=404, detail="ReviewDeliverable not found")
    return deliv


@deliverable_router.delete("/{deliv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deliverable(deliv_id: int, db: AsyncSession = Depends(get_db)):
    deliv = await db.get(ReviewDeliverable, deliv_id)
    if not deliv:
        raise HTTPException(status_code=404, detail="ReviewDeliverable not found")
    await db.delete(deliv)
    await db.commit()


router.include_router(gate_router)
router.include_router(deliverable_router)
