from fastapi import APIRouter
from api import auth, inspections, stats, reports, comments, map_api

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["inspections"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(map_api.router, prefix="/map", tags=["map"])
