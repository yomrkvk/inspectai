"""
Inspections API — upload, analyze, list, detail
"""
import os
import uuid
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from core.database import get_db
from core.auth import get_current_active_user
from core.config import settings
from models.user import User
from models.inspection import Inspection, Detection, Violation, InspectionStatus
from services.exif_service import extract_exif, summarize_exif
from services.ml_service import run_analysis

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/tiff"}


class ExifConfirm(BaseModel):
    use_gps: bool = True
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


# ── EXIF preview (step 1 of 2-step upload) ──────────────────────

@router.post("/exif-preview")
async def exif_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """Preview EXIF data before full upload. Returns metadata for user confirmation."""
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File too large (max 50 MB)")

    # Temp save to extract EXIF
    tmp_path = f"/tmp/exif_{uuid.uuid4().hex}_{file.filename}"
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        exif = extract_exif(tmp_path)
        summary = summarize_exif(exif)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return {
        "filename": file.filename,
        "size": len(content),
        "exif": exif,
        "exif_summary": summary,
        "has_gps": exif.get("has_gps", False),
        "gps_lat": exif.get("gps_lat"),
        "gps_lon": exif.get("gps_lon"),
        "capture_datetime": exif.get("capture_datetime"),
    }


# ── Full upload + analyze ────────────────────────────────────────

@router.post("/upload", status_code=201)
async def upload_and_analyze(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    address: Optional[str] = Form(None),
    city: str = Form("Тюмень"),
    district: Optional[str] = Form(None),
    use_exif_gps: bool = Form(True),
    manual_lat: Optional[float] = Form(None),
    manual_lon: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File too large")

    if file.content_type and file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")

    # Save original
    ext = Path(file.filename).suffix or ".jpg"
    uid = uuid.uuid4().hex
    filename = f"{uid}{ext}"
    image_path = os.path.join(settings.UPLOAD_DIR, filename)
    annotated_path = os.path.join(settings.ANNOTATED_DIR, f"ann_{filename}")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.ANNOTATED_DIR, exist_ok=True)

    with open(image_path, "wb") as f:
        f.write(content)

    # EXIF
    exif = extract_exif(image_path)
    gps_lat = exif.get("gps_lat") if use_exif_gps else None
    gps_lon = exif.get("gps_lon") if use_exif_gps else None
    if manual_lat is not None:
        gps_lat = manual_lat
    if manual_lon is not None:
        gps_lon = manual_lon

    inspection = Inspection(
        user_id=current_user.id,
        filename=filename,
        original_filename=file.filename,
        image_path=image_path,
        annotated_path=annotated_path,
        file_size=len(content),
        image_width=exif.get("width"),
        image_height=exif.get("height"),
        mime_type=file.content_type,
        exif_data=exif,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        capture_datetime=exif.get("capture_datetime"),
        camera_make=exif.get("camera_make"),
        camera_model=exif.get("camera_model"),
        address=address,
        city=city,
        district=district,
        status=InspectionStatus.PENDING,
    )
    db.add(inspection)
    await db.flush()
    inspection_id = inspection.id

    # Run analysis in background
    background_tasks.add_task(_run_analysis_bg, inspection_id, image_path, annotated_path)

    return {
        "id": inspection_id,
        "status": "pending",
        "message": "Анализ запущен",
    }


async def _run_analysis_bg(inspection_id: str, image_path: str, annotated_path: str):
    """Background task: run ML analysis and update DB."""
    from core.database import AsyncSessionLocal
    from models.inspection import Inspection, Detection, Violation, InspectionStatus

    async with AsyncSessionLocal() as db:
        try:
            result_q = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
            insp = result_q.scalar_one_or_none()
            if not insp:
                return

            insp.status = InspectionStatus.PROCESSING
            await db.flush()

            ml_result = run_analysis(image_path, annotated_path)

            insp.processing_time_ms = ml_result["processing_time_ms"]
            insp.model_version = ml_result["model_version"]

            if ml_result.get("error"):
                insp.status = InspectionStatus.ERROR
                insp.error_message = ml_result["error"]
                await db.commit()
                return

            total_violations = 0
            for det_data in ml_result["detections"]:
                det = Detection(
                    inspection_id=inspection_id,
                    bbox_x1=det_data["bbox"][0],
                    bbox_y1=det_data["bbox"][1],
                    bbox_x2=det_data["bbox"][2],
                    bbox_y2=det_data["bbox"][3],
                    confidence=det_data["confidence"],
                    class_name=det_data["class_name"],
                    banner_type=det_data.get("banner_type"),
                    classifier_conf=det_data.get("classifier_conf"),
                    ocr_text=det_data.get("ocr_text"),
                    ocr_confidence=det_data.get("ocr_confidence"),
                )
                db.add(det)
                await db.flush()

                for v_data in det_data.get("violations", []):
                    from models.inspection import ViolationType, Severity
                    try:
                        vt = ViolationType(v_data["violation_type"])
                    except ValueError:
                        vt = ViolationType.OTHER
                    try:
                        sv = Severity(v_data["severity"])
                    except ValueError:
                        sv = Severity.MEDIUM

                    viol = Violation(
                        detection_id=det.id,
                        inspection_id=inspection_id,
                        violation_type=vt,
                        severity=sv,
                        description=v_data.get("description"),
                        rule_id=v_data.get("rule_id"),
                        confidence=v_data.get("confidence", 0.0),
                        explanation=v_data.get("explanation"),
                    )
                    db.add(viol)
                    total_violations += 1

            insp.total_detections = len(ml_result["detections"])
            insp.total_violations = total_violations
            insp.status = InspectionStatus.COMPLETED
            await db.commit()

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Background analysis failed: {e}", exc_info=True)
            async with AsyncSessionLocal() as db2:
                q = await db2.execute(select(Inspection).where(Inspection.id == inspection_id))
                insp = q.scalar_one_or_none()
                if insp:
                    insp.status = InspectionStatus.ERROR
                    insp.error_message = str(e)
                    await db2.commit()


# ── List ─────────────────────────────────────────────────────────

@router.get("/")
async def list_inspections(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    q = select(Inspection).order_by(desc(Inspection.created_at)).offset(skip).limit(limit)
    if status:
        try:
            q = q.where(Inspection.status == InspectionStatus(status))
        except ValueError:
            pass
    result = await db.execute(q)
    items = result.scalars().all()
    return [_inspection_summary(i) for i in items]


# ── Detail ────────────────────────────────────────────────────────

@router.get("/{inspection_id}")
async def get_inspection(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    q = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    insp = q.scalar_one_or_none()
    if not insp:
        raise HTTPException(404, "Inspection not found")

    # Fetch detections + violations
    det_q = await db.execute(select(Detection).where(Detection.inspection_id == inspection_id))
    detections = det_q.scalars().all()

    result_detections = []
    for det in detections:
        viol_q = await db.execute(select(Violation).where(Violation.detection_id == det.id))
        violations = viol_q.scalars().all()
        result_detections.append({
            "id": det.id,
            "bbox": [det.bbox_x1, det.bbox_y1, det.bbox_x2, det.bbox_y2],
            "confidence": det.confidence,
            "class_name": det.class_name,
            "banner_type": det.banner_type,
            "classifier_conf": det.classifier_conf,
            "ocr_text": det.ocr_text,
            "ocr_confidence": det.ocr_confidence,
            "violations": [_violation_dict(v) for v in violations],
        })

    return {
        **_inspection_summary(insp),
        "detections": result_detections,
        "exif_data": insp.exif_data,
        "exif_summary": summarize_exif(insp.exif_data or {}),
        "error_message": insp.error_message,
    }


# ── Status polling ────────────────────────────────────────────────

@router.get("/{inspection_id}/status")
async def get_status(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    q = await db.execute(select(Inspection.status, Inspection.total_violations, Inspection.processing_time_ms)
                          .where(Inspection.id == inspection_id))
    row = q.one_or_none()
    if not row:
        raise HTTPException(404)
    return {"status": str(row[0]), "violations": row[1], "processing_ms": row[2]}


# ── Helpers ───────────────────────────────────────────────────────

def _inspection_summary(insp: Inspection) -> dict:
    return {
        "id": insp.id,
        "filename": insp.filename,
        "original_filename": insp.original_filename,
        "image_url": f"/uploads/{insp.filename}",
        "annotated_url": f"/annotated/ann_{insp.filename}" if insp.annotated_path else None,
        "address": insp.address,
        "city": insp.city,
        "district": insp.district,
        "gps_lat": insp.gps_lat,
        "gps_lon": insp.gps_lon,
        "status": str(insp.status),
        "total_detections": insp.total_detections,
        "total_violations": insp.total_violations,
        "processing_time_ms": insp.processing_time_ms,
        "model_version": insp.model_version,
        "created_at": insp.created_at.isoformat() if insp.created_at else None,
        "capture_datetime": insp.capture_datetime.isoformat() if insp.capture_datetime else None,
        "camera_make": insp.camera_make,
        "camera_model": insp.camera_model,
        "file_size": insp.file_size,
        "image_width": insp.image_width,
        "image_height": insp.image_height,
    }


def _violation_dict(v: Violation) -> dict:
    return {
        "id": v.id,
        "violation_type": str(v.violation_type),
        "severity": str(v.severity),
        "description": v.description,
        "rule_id": v.rule_id,
        "confidence": v.confidence,
        "explanation": v.explanation,
        "is_confirmed": v.is_confirmed,
        "resolved": v.resolved,
    }
