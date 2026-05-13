from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bepi.api.v1.deps import get_db
from bepi.core.models.mission import Mission
from bepi.core.schemas import MissionCreate, MissionRead, MissionUpdate

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("", response_model=list[MissionRead])
async def list_missions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Mission).order_by(Mission.id))
    return result.scalars().all()


@router.post("", response_model=MissionRead, status_code=status.HTTP_201_CREATED)
async def create_mission(body: MissionCreate, db: AsyncSession = Depends(get_db)):
    mission = Mission(**body.model_dump())
    db.add(mission)
    await db.commit()
    await db.refresh(mission)
    return mission


@router.get("/{mission_id}", response_model=MissionRead)
async def get_mission(mission_id: int, db: AsyncSession = Depends(get_db)):
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.patch("/{mission_id}", response_model=MissionRead)
async def update_mission(mission_id: int, body: MissionUpdate, db: AsyncSession = Depends(get_db)):
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(mission, field, value)
    await db.commit()
    await db.refresh(mission)
    return mission


@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mission(mission_id: int, db: AsyncSession = Depends(get_db)):
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    await db.delete(mission)
    await db.commit()
