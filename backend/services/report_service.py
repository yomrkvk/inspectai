"""
PDF report generation using ReportLab.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def generate_pdf_report(inspection: Dict, detections: List, violations: List, output_path: str) -> str:
    """Generate a PDF inspection report. Returns output_path."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.colors import HexColor, black, white, gray
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2.5*cm, bottomMargin=2*cm,
        )

        PRIMARY = HexColor("#1a56db")
        LIGHT_BG = HexColor("#f8fafc")
        RED = HexColor("#dc2626")
        GREEN = HexColor("#16a34a")
        AMBER = HexColor("#d97706")
        GRAY = HexColor("#64748b")
        DARK = HexColor("#0f172a")

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "Title", parent=styles["Normal"],
            fontSize=20, fontName="Helvetica-Bold",
            textColor=DARK, spaceAfter=6, leading=24,
        )
        subtitle_style = ParagraphStyle(
            "Sub", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica",
            textColor=GRAY, spaceAfter=16,
        )
        section_style = ParagraphStyle(
            "Section", parent=styles["Normal"],
            fontSize=13, fontName="Helvetica-Bold",
            textColor=DARK, spaceBefore=16, spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "Body", parent=styles["Normal"],
            fontSize=9.5, fontName="Helvetica",
            textColor=DARK, leading=14,
        )
        mono_style = ParagraphStyle(
            "Mono", parent=styles["Normal"],
            fontSize=8.5, fontName="Courier",
            textColor=GRAY, leading=12,
        )
        small_style = ParagraphStyle(
            "Small", parent=styles["Normal"],
            fontSize=8, fontName="Helvetica",
            textColor=GRAY, leading=11,
        )

        story = []

        # ── Header ──────────────────────────────────────────────
        header_data = [[
            Paragraph("<b>InspectAI</b>", ParagraphStyle(
                "H", fontSize=16, fontName="Helvetica-Bold", textColor=PRIMARY
            )),
            Paragraph(
                f"Отчёт сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}<br/>"
                f"ID: <b>{inspection.get('id', 'N/A')[:8].upper()}</b>",
                ParagraphStyle("HR", fontSize=8.5, fontName="Helvetica",
                               textColor=GRAY, alignment=TA_RIGHT)
            ),
        ]]
        header_table = Table(header_data, colWidths=["60%", "40%"])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=16))

        # ── Title ────────────────────────────────────────────────
        story.append(Paragraph("Акт контроля наружной рекламы", title_style))
        addr = inspection.get("address") or "адрес не указан"
        dt = inspection.get("created_at") or datetime.now().strftime("%d.%m.%Y %H:%M")
        story.append(Paragraph(f"{addr} · {dt}", subtitle_style))

        # ── Summary cards ────────────────────────────────────────
        story.append(Paragraph("Сводка", section_style))

        viol_count = len(violations)
        det_count = len(detections)
        status_color = RED if viol_count > 0 else GREEN
        status_text = f"{viol_count} нарушений выявлено" if viol_count > 0 else "Нарушений не выявлено"

        summary_data = [
            ["Показатель", "Значение"],
            ["Объект", inspection.get("address", "—")],
            ["Город", inspection.get("city", "Тюмень")],
            ["Дата проверки", str(dt)[:16]],
            ["Обнаружено объектов", str(det_count)],
            ["Нарушений", str(viol_count)],
            ["Время обработки", f"{inspection.get('processing_time_ms', 0)} мс"],
            ["Модель", inspection.get("model_version", "YOLOv8+EasyOCR")],
            ["Итог", status_text],
        ]
        t = Table(summary_data, colWidths=["45%", "55%"])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, white]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t)
        story.append(Spacer(1, 16))

        # ── EXIF / metadata ──────────────────────────────────────
        exif = inspection.get("exif_data") or {}
        raw = exif.get("raw", {}) if isinstance(exif, dict) else {}
        if raw or exif.get("has_gps"):
            story.append(Paragraph("Метаданные изображения (EXIF)", section_style))
            exif_rows = [["Тег", "Значение"]]
            if exif.get("camera_make") or exif.get("camera_model"):
                exif_rows.append(["Камера", f"{exif.get('camera_make','')} {exif.get('camera_model','')}".strip()])
            if exif.get("capture_datetime"):
                exif_rows.append(["Дата съёмки", str(exif["capture_datetime"])[:19]])
            if exif.get("has_gps"):
                exif_rows.append(["GPS", f"{exif.get('gps_lat'):.6f}, {exif.get('gps_lon'):.6f}"])
            for k in ("FocalLength", "ExposureTime", "FNumber", "ISOSpeedRatings"):
                if k in raw:
                    exif_rows.append([k, str(raw[k])])
            if len(exif_rows) > 1:
                et = Table(exif_rows, colWidths=["45%", "55%"])
                et.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#475569")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, white]),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                story.append(et)
                story.append(Spacer(1, 16))

        # ── Detections ───────────────────────────────────────────
        if detections:
            story.append(Paragraph(f"Обнаруженные объекты ({det_count})", section_style))
            det_rows = [["#", "Тип", "Баннер", "Уверенность", "OCR текст", "Нарушений"]]
            for i, det in enumerate(detections, 1):
                det_rows.append([
                    str(i),
                    det.get("class_name", "banner"),
                    det.get("banner_type", "—"),
                    f"{det.get('confidence', 0):.0%}",
                    (det.get("ocr_text") or "—")[:40],
                    str(len(det.get("violations", []))),
                ])
            dt_table = Table(det_rows, colWidths=["5%", "15%", "15%", "12%", "40%", "13%"])
            dt_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, white]),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("WORDWRAP", (4, 1), (4, -1), True),
            ]))
            story.append(dt_table)
            story.append(Spacer(1, 16))

        # ── Violations ───────────────────────────────────────────
        if violations:
            story.append(Paragraph(f"Выявленные нарушения ({viol_count})", section_style))
            for i, v in enumerate(violations, 1):
                sev = v.get("severity", "medium")
                sev_color = RED if sev == "high" else (AMBER if sev == "medium" else GREEN)
                sev_labels = {"high": "КРИТИЧЕСКОЕ", "medium": "СРЕДНЕЕ", "low": "НЕЗНАЧИТЕЛЬНОЕ"}
                story.append(Paragraph(
                    f"<b>{i}. {v.get('rule_id','—')} — {v.get('description','')}</b>",
                    ParagraphStyle("VH", parent=body_style, spaceBefore=6, textColor=sev_color)
                ))
                story.append(Paragraph(
                    f"Тип: {v.get('violation_type','—')} · "
                    f"Степень: {sev_labels.get(sev, sev)} · "
                    f"Уверенность: {v.get('confidence', 0):.0%}",
                    small_style
                ))
                if v.get("explanation"):
                    story.append(Paragraph(v["explanation"], body_style))
                story.append(Spacer(1, 6))
        else:
            story.append(Paragraph("Нарушений не выявлено", ParagraphStyle(
                "OK", parent=body_style, textColor=GREEN, spaceBefore=8
            )))

        # ── Signature ────────────────────────────────────────────
        story.append(Spacer(1, 24))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Сформировано автоматически системой InspectAI · "
            f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            small_style
        ))

        doc.build(story)
        logger.info(f"PDF report generated: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise
