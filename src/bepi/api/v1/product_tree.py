from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bepi.api.v1.deps import get_db
from bepi.core.models.product_tree import OperatingMode, ProductNode
from bepi.core.schemas import (
    OperatingModeCreate,
    OperatingModeRead,
    ProductNodeCreate,
    ProductNodeRead,
    ProductNodeUpdate,
)

router = APIRouter(tags=["product_tree"])

nodes_router = APIRouter(prefix="/product-nodes")
modes_router = APIRouter(prefix="/missions/{mission_id}/operating-modes")


def _load_children(node: ProductNode) -> ProductNodeRead:
    return ProductNodeRead.model_validate(node)


@nodes_router.get("", response_model=list[ProductNodeRead])
async def list_nodes(mission_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(ProductNode)
    if mission_id is not None:
        q = q.where(ProductNode.mission_id == mission_id)
    result = await db.execute(q.order_by(ProductNode.id))
    return result.scalars().all()


@nodes_router.post("", response_model=ProductNodeRead, status_code=status.HTTP_201_CREATED)
async def create_node(body: ProductNodeCreate, db: AsyncSession = Depends(get_db)):
    node = ProductNode(**body.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


@nodes_router.get("/{node_id}", response_model=ProductNodeRead)
async def get_node(node_id: int, db: AsyncSession = Depends(get_db)):
    node = await db.get(ProductNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="ProductNode not found")
    return node


@nodes_router.patch("/{node_id}", response_model=ProductNodeRead)
async def update_node(node_id: int, body: ProductNodeUpdate, db: AsyncSession = Depends(get_db)):
    node = await db.get(ProductNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="ProductNode not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    await db.commit()
    await db.refresh(node)
    return node


@nodes_router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(node_id: int, db: AsyncSession = Depends(get_db)):
    node = await db.get(ProductNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="ProductNode not found")
    await db.delete(node)
    await db.commit()


@nodes_router.get("/{node_id}/tree", response_model=ProductNodeRead)
async def get_node_tree(node_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProductNode)
        .where(ProductNode.id == node_id)
        .options(selectinload(ProductNode.children).selectinload(ProductNode.children))
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="ProductNode not found")
    return node


@nodes_router.post("/{node_id}/move", response_model=ProductNodeRead)
async def move_node(node_id: int, new_parent_id: int | None = None, db: AsyncSession = Depends(get_db)):
    node = await db.get(ProductNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="ProductNode not found")
    if new_parent_id is not None:
        parent = await db.get(ProductNode, new_parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent node not found")
    node.parent_id = new_parent_id
    await db.commit()
    await db.refresh(node)
    return node


@modes_router.get("", response_model=list[OperatingModeRead])
async def list_operating_modes(mission_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OperatingMode).where(OperatingMode.mission_id == mission_id).order_by(OperatingMode.id)
    )
    return result.scalars().all()


@modes_router.post("", response_model=OperatingModeRead, status_code=status.HTTP_201_CREATED)
async def create_operating_mode(mission_id: int, body: OperatingModeCreate, db: AsyncSession = Depends(get_db)):
    mode = OperatingMode(**body.model_dump())
    db.add(mode)
    await db.commit()
    await db.refresh(mode)
    return mode


@modes_router.get("/{mode_id}", response_model=OperatingModeRead)
async def get_operating_mode(mission_id: int, mode_id: int, db: AsyncSession = Depends(get_db)):
    mode = await db.get(OperatingMode, mode_id)
    if not mode or mode.mission_id != mission_id:
        raise HTTPException(status_code=404, detail="OperatingMode not found")
    return mode


@modes_router.delete("/{mode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operating_mode(mission_id: int, mode_id: int, db: AsyncSession = Depends(get_db)):
    mode = await db.get(OperatingMode, mode_id)
    if not mode or mode.mission_id != mission_id:
        raise HTTPException(status_code=404, detail="OperatingMode not found")
    await db.delete(mode)
    await db.commit()


router.include_router(nodes_router)
router.include_router(modes_router)
