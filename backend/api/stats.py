"""Stats API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.auth import get_current_active_user
from services.stats_service import get_dashboard_stats

router = APIRouter()


@router.get("/dashboard")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await get_dashboard_stats(db)
