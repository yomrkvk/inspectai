"""
Comments / citizen requests API
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from core.database import get_db
from core.auth import get_current_active_user
from models.inspection import Comment, Severity, ViolationType
from models.user import User

router = APIRouter()


class CommentCreate(BaseModel):
    text: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    severity: Severity = Severity.MEDIUM
    violation_type: ViolationType = ViolationType.OTHER
    tags: list = []
    inspection_id: Optional[str] = None


@router.post("/", status_code=201)
async def create_comment(
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    comment = Comment(
        user_id=current_user.id,
        text=data.text,
        address=data.address,
        gps_lat=data.lat,
        gps_lon=data.lon,
        severity=data.severity,
        violation_type=data.violation_type,
        tags=data.tags,
        inspection_id=data.inspection_id,
    )
    db.add(comment)
    await db.flush()
    return _comment_dict(comment, current_user)


@router.get("/")
async def list_comments(
    skip: int = 0,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    q = await db.execute(
        select(Comment, User)
        .join(User, Comment.user_id == User.id)
        .order_by(desc(Comment.created_at))
        .offset(skip).limit(limit)
    )
    rows = q.fetchall()
    return [_comment_dict(c, u) for c, u in rows]


def _comment_dict(c: Comment, u: User) -> dict:
    return {
        "id": c.id,
        "text": c.text,
        "address": c.address,
        "gps_lat": c.gps_lat,
        "gps_lon": c.gps_lon,
        "severity": str(c.severity),
        "violation_type": str(c.violation_type),
        "status": c.status,
        "tags": c.tags or [],
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "author": {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": str(u.role),
        },
    }
