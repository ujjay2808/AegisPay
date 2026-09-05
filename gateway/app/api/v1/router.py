from fastapi import APIRouter

from app.api.v1.endpoints import mandates

router = APIRouter()
router.include_router(mandates.router)
