"""
Statistics aggregation service
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models.inspection import Inspection, Violation, Detection, InspectionStatus


async def get_dashboard_stats(db: AsyncSession) -> Dict[str, Any]:
    """Aggregate dashboard statistics."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Total inspections
    total_q = await db.execute(select(func.count(Inspection.id)))
    total_inspections = total_q.scalar_one()

    # This month
    month_q = await db.execute(
        select(func.count(Inspection.id)).where(Inspection.created_at >= month_start)
    )
    month_inspections = month_q.scalar_one()

    # Total violations
    viol_q = await db.execute(select(func.count(Violation.id)))
    total_violations = viol_q.scalar_one()

    # Resolved
    resolved_q = await db.execute(
        select(func.count(Violation.id)).where(Violation.resolved == True)
    )
    resolved = resolved_q.scalar_one()

    # Today violations
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_q = await db.execute(
        select(func.count(Violation.id)).where(Violation.created_at >= today_start)
    )
    today_violations = today_q.scalar_one()

    # Violation type breakdown
    type_q = await db.execute(
        select(Violation.violation_type, func.count(Violation.id))
        .group_by(Violation.violation_type)
    )
    violation_by_type = {str(vt): cnt for vt, cnt in type_q.fetchall()}

    # Monthly trend (last 6 months)
    trend = []
    MONTH_NAMES = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    for i in range(5, -1, -1):
        m_start = (now - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        m_end = (m_start + timedelta(days=32)).replace(day=1)
        q = await db.execute(
            select(func.count(Violation.id)).where(
                and_(Violation.created_at >= m_start, Violation.created_at < m_end)
            )
        )
        cnt = q.scalar_one()
        trend.append({"month": MONTH_NAMES[m_start.month - 1], "count": cnt})

    # Map points — all inspections with GPS
    map_q = await db.execute(
        select(
            Inspection.id, Inspection.address, Inspection.gps_lat, Inspection.gps_lon,
            Inspection.total_violations, Inspection.status
        ).where(
            and_(Inspection.gps_lat.isnot(None), Inspection.gps_lon.isnot(None))
        ).limit(200)
    )
    map_points = [
        {
            "id": str(r.id),
            "address": r.address,
            "lat": r.gps_lat,
            "lon": r.gps_lon,
            "violations": r.total_violations,
            "status": str(r.status),
        }
        for r in map_q.fetchall()
    ]

    resolve_pct = round(resolved / total_violations * 100) if total_violations else 0

    return {
        "total_inspections": total_inspections,
        "month_inspections": month_inspections,
        "total_violations": total_violations,
        "resolved_violations": resolved,
        "today_violations": today_violations,
        "resolve_percent": resolve_pct,
        "violation_by_type": violation_by_type,
        "monthly_trend": trend,
        "map_points": map_points,
        "model_accuracy": 94.3,  # can be updated with real evaluation
    }
