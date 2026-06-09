"""
Map API — returns geo points for map display + Yandex Maps key
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from core.database import get_db
from core.auth import get_current_active_user
from core.config import settings
from models.inspection import Inspection

router = APIRouter()


@router.get("/config")
async def map_config(_=Depends(get_current_active_user)):
    """Return Yandex Maps API key for frontend."""
    return {"api_key": settings.YANDEX_MAPS_KEY}


@router.get("/points")
async def map_points(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """All inspections with GPS coordinates."""
    q = await db.execute(
        select(
            Inspection.id,
            Inspection.address,
            Inspection.city,
            Inspection.gps_lat,
            Inspection.gps_lon,
            Inspection.total_violations,
            Inspection.status,
            Inspection.created_at,
        ).where(
            and_(Inspection.gps_lat.isnot(None), Inspection.gps_lon.isnot(None))
        ).order_by(Inspection.created_at.desc())
        .limit(500)
    )
    rows = q.fetchall()
    return [
        {
            "id": str(r[0]),
            "address": r[1],
            "city": r[2],
            "lat": r[3],
            "lon": r[4],
            "violations": r[5] or 0,
            "status": str(r[6]),
            "created_at": r[7].isoformat() if r[7] else None,
        }
        for r in rows
    ]
