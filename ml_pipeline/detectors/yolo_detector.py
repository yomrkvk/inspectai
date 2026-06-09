"""
YOLOv8 детектор — финальная версия.
Пайплайн: YOLO → SegFormer → Classifier → OCR
ml/detectors/yolo_detector.py
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)


class YOLOBannerDetector:
    def __init__(
        self,
        model_path: str = "weights/best.pt",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        enable_ocr: bool = True,
        enable_segformer: bool = False,
        ocr_min_confidence: float = 0.2,
        roi_padding: int = 15,
        ocr_debug: bool = False,
        classifier_debug: bool = False,
    ):
        from ultralytics import YOLO
        self.model             = YOLO(model_path)
        self.conf_threshold    = conf_threshold
        self.iou_threshold     = iou_threshold
        self.enable_ocr        = enable_ocr
        self.enable_segformer  = enable_segformer
        self.ocr_min_confidence = ocr_min_confidence
        self.roi_padding       = roi_padding
        self.ocr_debug         = ocr_debug
        self.classifier_debug  = classifier_debug

        logger.info(
            f"Детектор: {model_path} | "
            f"OCR={'вкл' if enable_ocr else 'выкл'} | "
            f"SegFormer={'вкл' if enable_segformer else 'выкл'}"
        )

    def _load_image(self, image):
        if isinstance(image, (str, Path)):
            img = cv2.imread(str(image))
            if img is None:
                raise ValueError(f"Не удалось загрузить: {image}")
            return img
        return image.copy()

    def _get_roi(self, img, bbox):
        from segformer_service import get_clean_roi_for_ocr
        x1, y1, x2, y2 = bbox
        h, w = img.shape[:2]
        if self.enable_segformer:
            return get_clean_roi_for_ocr(
                img, bbox=bbox,
                padding=self.roi_padding,
                use_segformer=True,
            )
        rx1 = max(0, x1 - self.roi_padding)
        ry1 = max(0, y1 - self.roi_padding)
        rx2 = min(w, x2 + self.roi_padding)
        ry2 = min(h, y2 + self.roi_padding)
        return img[ry1:ry2, rx1:rx2]

    def detect(self, image) -> list:
        """
        Пайплайн: YOLO → SegFormer (opt) → Classifier → OCR

        Returns список dict:
        {
            bbox, confidence, class_id, class_name,
            banner_type,      ← "electronic" | "billboard" | "unknown"
            classifier_conf,  ← уверенность классификатора
            ocr: { text, confidence, words }
        }
        """
        from ocr_service import read_text_from_roi
        from banner_classifier import classify_banner

        img = self._load_image(image)

        results = self.model(
            img,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )[0]

        detections = []

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf      = float(box.conf[0])
            class_id  = int(box.cls[0])
            class_name = self.model.names.get(class_id, str(class_id))

            detection = {
                "bbox":       [x1, y1, x2, y2],
                "confidence": round(conf, 3),
                "class_id":   class_id,
                "class_name": class_name,
            }

            if self.enable_ocr:
                roi = self._get_roi(img, [x1, y1, x2, y2])

                # Классификация типа баннера
                cls_result = classify_banner(roi, debug=self.classifier_debug)
                banner_type = cls_result["type"]
                detection["banner_type"]     = banner_type
                detection["classifier_conf"] = cls_result["confidence"]

                if self.ocr_debug:
                    logger.info(
                        f"bbox={[x1,y1,x2,y2]} → тип={banner_type} "
                        f"(conf={cls_result['confidence']:.2f})"
                    )

                # OCR со стратегией под тип
                detection["ocr"] = read_text_from_roi(
                    roi,
                    banner_type=banner_type,
                    min_confidence=self.ocr_min_confidence,
                    debug=self.ocr_debug,
                )

            detections.append(detection)

        return detections

    def detect_and_draw(self, image, show_ocr_text: bool = True) -> tuple:
        img        = self._load_image(image)
        detections = self.detect(img)

        # Цвет bbox по типу
        TYPE_COLORS = {
            "electronic": (0, 140, 255),   # оранжевый
            "billboard":  (0, 220, 0),     # зелёный
            "unknown":    (180, 180, 180), # серый
        }

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            banner_type = det.get("banner_type", "unknown")
            color = TYPE_COLORS.get(banner_type, (0, 220, 0))

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            ocr_text = ""
            ocr_conf = 0.0
            if show_ocr_text and "ocr" in det:
                ocr_text = det["ocr"].get("text", "")
                ocr_conf = det["ocr"].get("confidence", 0.0)

            type_label = f"[{banner_type}]"
            if ocr_text:
                display = ocr_text[:60] + ("…" if len(ocr_text) > 60 else "")
                label = (f"{det['class_name']} {det['confidence']:.2f} "
                         f"{type_label} | \"{display}\" ({ocr_conf:.2f})")
            else:
                label = (f"{det['class_name']} {det['confidence']:.2f} "
                         f"{type_label}")

            font = cv2.FONT_HERSHEY_SIMPLEX
            fs, th = 0.42, 1
            (tw, lh), _ = cv2.getTextSize(label, font, fs, th)
            cv2.rectangle(img, (x1, y1 - lh - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(img, label, (x1 + 2, y1 - 4), font, fs, (0, 0, 0), th)

        return img, detections
