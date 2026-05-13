from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bepi.api.v1.deps import get_db
from bepi.core.models.requirement import Requirement
from bepi.core.schemas import (
    CoverageReportResponse,
    RequirementCreate,
    RequirementRead,
    RequirementUpdate,
    VerificationMatrixResponse,
    VerificationMatrixRow,
)

router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.get("", response_model=list[RequirementRead])
async def list_requirements(
    mission_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Requirement)
    if mission_id is not None:
        q = q.where(Requirement.mission_id == mission_id)
    result = await db.execute(q.order_by(Requirement.id))
    return result.scalars().all()


@router.post("", response_model=RequirementRead, status_code=status.HTTP_201_CREATED)
async def create_requirement(body: RequirementCreate, db: AsyncSession = Depends(get_db)):
    req = Requirement(**body.model_dump())
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.post("/bulk", response_model=list[RequirementRead], status_code=status.HTTP_201_CREATED)
async def bulk_import_requirements(
    body: list[RequirementCreate] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    reqs = [Requirement(**r.model_dump()) for r in body]
    db.add_all(reqs)
    await db.commit()
    for r in reqs:
        await db.refresh(r)
    return reqs


@router.get("/{req_id}", response_model=RequirementRead)
async def get_requirement(req_id: int, db: AsyncSession = Depends(get_db)):
    req = await db.get(Requirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req


@router.patch("/{req_id}", response_model=RequirementRead)
async def update_requirement(req_id: int, body: RequirementUpdate, db: AsyncSession = Depends(get_db)):
    req = await db.get(Requirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(req, field, value)
    await db.commit()
    await db.refresh(req)
    return req


@router.delete("/{req_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(req_id: int, db: AsyncSession = Depends(get_db)):
    req = await db.get(Requirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    await db.delete(req)
    await db.commit()


@router.get("/{req_id}/trace", response_model=list[RequirementRead])
async def get_requirement_trace(req_id: int, db: AsyncSession = Depends(get_db)):
    req = await db.get(Requirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    result = await db.execute(
        select(Requirement).where(Requirement.parent_id == req_id).order_by(Requirement.id)
    )
    return result.scalars().all()


@router.get("/missions/{mission_id}/verification-matrix", response_model=VerificationMatrixResponse)
async def verification_matrix(mission_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Requirement).where(Requirement.mission_id == mission_id).order_by(Requirement.id)
    )
    reqs = result.scalars().all()

    from bepi.core.enums import VerificationStatus

    rows = []
    passed = failed = not_started = 0
    for r in reqs:
        allocated_nodes = [n.id for n in r.allocated_to] if r.allocated_to else []
        rows.append(
            VerificationMatrixRow(
                req_id=r.req_id,
                title=r.title,
                verification_method=r.verification_method,
                verification_level=r.verification_level,
                verification_status=r.verification_status,
                verification_evidence=r.verification_evidence,
                allocated_nodes=allocated_nodes,
            )
        )
        if r.verification_status == VerificationStatus.PASSED:
            passed += 1
        elif r.verification_status == VerificationStatus.FAILED:
            failed += 1
        elif r.verification_status == VerificationStatus.NOT_STARTED:
            not_started += 1

    return VerificationMatrixResponse(
        mission_id=mission_id,
        rows=rows,
        total=len(rows),
        passed=passed,
        failed=failed,
        not_started=not_started,
    )


@router.get("/missions/{mission_id}/coverage", response_model=CoverageReportResponse)
async def coverage_report(mission_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Requirement).where(Requirement.mission_id == mission_id)
    )
    reqs = result.scalars().all()

    from bepi.core.enums import VerificationStatus

    total = len(reqs)
    allocated = sum(1 for r in reqs if r.allocated_to)
    unallocated = total - allocated
    verified = sum(1 for r in reqs if r.verification_status == VerificationStatus.PASSED)

    by_level: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for r in reqs:
        by_level[r.level.value] = by_level.get(r.level.value, 0) + 1
        by_category[r.category.value] = by_category.get(r.category.value, 0) + 1
        by_status[r.status.value] = by_status.get(r.status.value, 0) + 1

    coverage_pct = (verified / total * 100) if total > 0 else 0.0

    return CoverageReportResponse(
        mission_id=mission_id,
        total_requirements=total,
        allocated=allocated,
        unallocated=unallocated,
        verified=verified,
        coverage_pct=round(coverage_pct, 2),
        by_level=by_level,
        by_category=by_category,
        by_status=by_status,
    )
