from fastapi import APIRouter

from bepi.api.v1 import budgets, missions, product_tree, requirements, reviews, risks, schedule

router = APIRouter()

router.include_router(missions.router)
router.include_router(product_tree.router)
router.include_router(budgets.router)
router.include_router(requirements.router)
router.include_router(risks.router)
router.include_router(schedule.router)
router.include_router(reviews.router)
