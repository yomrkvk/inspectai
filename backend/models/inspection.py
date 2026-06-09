"""
Inspection, Detection, Violation, Comment models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from core.database import Base


class InspectionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ViolationType(str, enum.Enum):
    SIZE_MISMATCH = "size_mismatch"
    FORBIDDEN_CONTENT = "forbidden_content"
    ILLEGAL_SIGN = "illegal_sign"
    NO_PERMIT = "no_permit"
    TEXT_ERROR = "text_error"
    OTHER = "other"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Image info
    filename = Column(String(256), nullable=False)
    original_filename = Column(String(256), nullable=True)
    image_path = Column(String(512), nullable=False)
    annotated_path = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    mime_type = Column(String(64), nullable=True)

    # EXIF / metadata
    exif_data = Column(JSON, nullable=True)  # all extracted EXIF
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)
    capture_datetime = Column(DateTime, nullable=True)
    camera_make = Column(String(128), nullable=True)
    camera_model = Column(String(128), nullable=True)

    # Location (manual or from EXIF)
    address = Column(String(512), nullable=True)
    district = Column(String(128), nullable=True)
    city = Column(String(128), default="Тюмень")
    
    # Processing
    status = Column(SAEnum(InspectionStatus), default=InspectionStatus.PENDING)
    processing_time_ms = Column(Integer, nullable=True)
    model_version = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Results summary
    total_detections = Column(Integer, default=0)
    total_violations = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = relationship("User", back_populates="inspections")
    detections = relationship("Detection", back_populates="inspection", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="inspection", cascade="all, delete-orphan")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inspection_id = Column(String(36), ForeignKey("inspections.id"), nullable=False)

    bbox_x1 = Column(Integer)
    bbox_y1 = Column(Integer)
    bbox_x2 = Column(Integer)
    bbox_y2 = Column(Integer)
    confidence = Column(Float)
    class_name = Column(String(64))
    banner_type = Column(String(32), nullable=True)   # electronic / billboard
    classifier_conf = Column(Float, nullable=True)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)

    violations = relationship("Violation", back_populates="detection", cascade="all, delete-orphan")
    inspection = relationship("Inspection", back_populates="detections")


class Violation(Base):
    __tablename__ = "violations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    detection_id = Column(String(36), ForeignKey("detections.id"), nullable=False)
    inspection_id = Column(String(36), ForeignKey("inspections.id"), nullable=False)

    violation_type = Column(SAEnum(ViolationType), default=ViolationType.OTHER)
    severity = Column(SAEnum(Severity), default=Severity.MEDIUM)
    description = Column(Text, nullable=True)
    rule_id = Column(String(64), nullable=True)          # e.g. R-SIZE-01
    confidence = Column(Float, default=0.0)
    explanation = Column(Text, nullable=True)
    is_confirmed = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    detection = relationship("Detection", back_populates="violations")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inspection_id = Column(String(36), ForeignKey("inspections.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    text = Column(Text, nullable=False)
    severity = Column(SAEnum(Severity), default=Severity.MEDIUM)
    violation_type = Column(SAEnum(ViolationType), default=ViolationType.OTHER)
    address = Column(String(512), nullable=True)
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)
    photos = Column(JSON, default=list)   # list of file paths
    status = Column(String(32), default="pending")  # pending / review / resolved
    tags = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="comments")
    inspection = relationship("Inspection", back_populates="comments")
