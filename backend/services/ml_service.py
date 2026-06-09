"""
ML pipeline service — wraps YOLOBannerDetector and applies inference rules.
"""
import sys
import os
import logging
import time
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.config import settings

logger = logging.getLogger(__name__)

# Add ml_pipeline to path
ML_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ml_pipeline", "ml", "detectors")
)
if ML_PATH not in sys.path:
    sys.path.insert(0, ML_PATH)

_detector = None


def get_detector():
    global _detector
    if _detector is None:
        try:
            from yolo_detector import YOLOBannerDetector
            model_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "ml_pipeline", "weights", "best.pt")
            )
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found: {model_path}")
            _detector = YOLOBannerDetector(
                model_path=model_path,
                conf_threshold=settings.ML_CONF_THRESHOLD,
                iou_threshold=settings.ML_IOU_THRESHOLD,
                enable_ocr=settings.ML_ENABLE_OCR,
                enable_segformer=settings.ML_ENABLE_SEGFORMER,
                ocr_min_confidence=0.2,
                roi_padding=15,
            )
            logger.info("YOLOBannerDetector loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load detector: {e}")
            raise
    return _detector


# ── Inference rules (forward chaining) ──────────────────────────

RULES = [
    {
        "id": "R-SIZE-01",
        "description": "Ширина конструкции превышает допустимую (4.0 м)",
        "priority": 10,
        "check": lambda d, img_w, img_h: (
            (d["bbox"][2] - d["bbox"][0]) / img_w * 20 > 4.0  # rough scale at 20m distance
        ),
        "violation_type": "size_mismatch",
        "severity": "high",
        "confidence": 0.85,
    },
    {
        "id": "R-CONT-01",
        "description": "Текст содержит запрещённые слова",
        "priority": 9,
        "check": lambda d, img_w, img_h: _check_forbidden_content(d),
        "violation_type": "forbidden_content",
        "severity": "high",
        "confidence": 0.92,
    },
    {
        "id": "R-PERM-01",
        "description": "Отсутствие разрешения (не идентифицирована в базе)",
        "priority": 8,
        "check": lambda d, img_w, img_h: d.get("confidence", 0) > 0.7 and not d.get("permit_verified", False),
        "violation_type": "no_permit",
        "severity": "medium",
        "confidence": 0.70,
    },
    {
        "id": "R-ELEC-01",
        "description": "Электронный баннер в жилой зоне",
        "priority": 7,
        "check": lambda d, img_w, img_h: d.get("banner_type") == "electronic",
        "violation_type": "illegal_sign",
        "severity": "medium",
        "confidence": 0.75,
    },
]

FORBIDDEN_WORDS = [
    "казино", "ставки", "букмекер", "алкоголь", "водка", "пиво",
    "табак", "сигарет", "кальян", "займ", "кредит без", "мфо",
    "18+", "xxх", "эротик",
]


def _check_forbidden_content(detection: Dict) -> bool:
    ocr = detection.get("ocr", {})
    text = ocr.get("text", "").lower()
    return any(fw in text for fw in FORBIDDEN_WORDS)


def apply_rules(detection: Dict, img_w: int, img_h: int) -> List[Dict]:
    """Apply all rules to a single detection, return list of violations."""
    violations = []
    for rule in sorted(RULES, key=lambda r: -r["priority"]):
        try:
            if rule["check"](detection, img_w, img_h):
                violations.append({
                    "rule_id": rule["id"],
                    "violation_type": rule["violation_type"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "confidence": rule["confidence"],
                    "explanation": _build_explanation(rule, detection),
                })
        except Exception as e:
            logger.warning(f"Rule {rule['id']} check failed: {e}")
    return violations


def _build_explanation(rule: Dict, detection: Dict) -> str:
    rid = rule["id"]
    if rid == "R-SIZE-01":
        return (
            f"Обнаруженная конструкция занимает значительную часть кадра. "
            f"Уверенность детектора: {detection['confidence']:.0%}."
        )
    if rid == "R-CONT-01":
        text = detection.get("ocr", {}).get("text", "")
        return f"Распознанный текст: «{text[:80]}». Содержит слова из реестра запрещённой рекламы."
    if rid == "R-PERM-01":
        return "Конструкция не найдена в базе данных выданных разрешений."
    if rid == "R-ELEC-01":
        return "Электронный баннер обнаружен в зоне с ограничениями на световую рекламу."
    return rule["description"]


# ── Main pipeline ────────────────────────────────────────────────

def run_analysis(image_path: str, annotated_path: str) -> Dict[str, Any]:
    """
    Run full ML pipeline on image.
    Returns dict compatible with Inspection schema.
    """
    t0 = time.time()
    result = {
        "detections": [],
        "violations": [],
        "processing_time_ms": 0,
        "model_version": "YOLOv8+EasyOCR v1.0",
        "error": None,
    }

    try:
        detector = get_detector()
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")

        img_h, img_w = img.shape[:2]
        annotated_img, raw_detections = detector.detect_and_draw(img)
        cv2.imwrite(annotated_path, annotated_img)

        for det in raw_detections:
            violations = apply_rules(det, img_w, img_h)
            result["detections"].append({
                "bbox": det["bbox"],
                "confidence": det["confidence"],
                "class_name": det.get("class_name", "banner"),
                "banner_type": det.get("banner_type", "unknown"),
                "classifier_conf": det.get("classifier_conf", 0.0),
                "ocr_text": det.get("ocr", {}).get("text", ""),
                "ocr_confidence": det.get("ocr", {}).get("confidence", 0.0),
                "violations": violations,
            })
            result["violations"].extend(violations)

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        result["error"] = str(e)

    result["processing_time_ms"] = int((time.time() - t0) * 1000)
    return result
