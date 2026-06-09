"""
Application settings — reads from .env
"""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "InspectAI"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-very-long-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # DB — PostgreSQL (asyncpg driver)
    DATABASE_URL: str = "postgresql+asyncpg://inspectai:inspectai@localhost:5432/inspectai"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"]

    # Storage
    UPLOAD_DIR: str = "media/uploads"
    ANNOTATED_DIR: str = "media/annotated"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB

    # ML
    ML_MODEL_PATH: str = "../ml_pipeline/weights/best.pt"
    ML_CONF_THRESHOLD: float = 0.25
    ML_IOU_THRESHOLD: float = 0.45
    ML_ENABLE_OCR: bool = True
    ML_ENABLE_SEGFORMER: bool = False

    # Yandex Maps (put real key in .env)
    YANDEX_MAPS_KEY: str = "YOUR_YANDEX_MAPS_KEY"

    # Reports
    REPORTS_DIR: str = "media/reports"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
