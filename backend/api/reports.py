"""
Reports API — generate PDF or JSON report for an inspection
"""
import os
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth import get_current_active_user
from core.config import settings
from models.inspection import Inspection, Detection, Violation
from services.report_service import generate_pdf_report
from api.inspections import _inspection_summary, _violation_dict

router = APIRouter()


@router.get("/{inspection_id}/pdf")
async def download_pdf(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    insp_q = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    insp = insp_q.scalar_one_or_none()
    if not insp:
        raise HTTPException(404)

    det_q = await db.execute(select(Detection).where(Detection.inspection_id == inspection_id))
    detections = det_q.scalars().all()

    all_violations = []
    det_dicts = []
    for det in detections:
        v_q = await db.execute(select(Violation).where(Violation.detection_id == det.id))
        viols = v_q.scalars().all()
        viol_dicts = [_violation_dict(v) for v in viols]
        all_violations.extend(viol_dicts)
        det_dicts.append({
            "class_name": det.class_name,
            "banner_type": det.banner_type,
            "confidence": det.confidence,
            "ocr_text": det.ocr_text,
            "violations": viol_dicts,
        })

    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    out = os.path.join(settings.REPORTS_DIR, f"report_{inspection_id[:8]}.pdf")

    insp_dict = _inspection_summary(insp)
    insp_dict["exif_data"] = insp.exif_data
    generate_pdf_report(insp_dict, det_dicts, all_violations, out)

    return FileResponse(
        out,
        media_type="application/pdf",
        filename=f"InspectAI_report_{inspection_id[:8]}.pdf",
    )


@router.get("/{inspection_id}/json")
async def download_json(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    insp_q = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    insp = insp_q.scalar_one_or_none()
    if not insp:
        raise HTTPException(404)

    det_q = await db.execute(select(Detection).where(Detection.inspection_id == inspection_id))
    detections = det_q.scalars().all()

    det_dicts = []
    for det in detections:
        v_q = await db.execute(select(Violation).where(Violation.detection_id == det.id))
        viols = v_q.scalars().all()
        det_dicts.append({
            "id": det.id,
            "bbox": [det.bbox_x1, det.bbox_y1, det.bbox_x2, det.bbox_y2],
            "class_name": det.class_name,
            "banner_type": det.banner_type,
            "confidence": det.confidence,
            "ocr_text": det.ocr_text,
            "ocr_confidence": det.ocr_confidence,
            "violations": [_violation_dict(v) for v in viols],
        })

    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "inspection": _inspection_summary(insp),
        "exif": insp.exif_data,
        "detections": det_dicts,
    }

    from fastapi.responses import Response
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="InspectAI_{inspection_id[:8]}.json"'},
    )
