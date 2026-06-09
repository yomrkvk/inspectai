"""
SegFormer сервис — сегментация баннеров для уточнения контура перед OCR.
ml/detectors/segformer_service.py

Использует nvidia/segformer-b4-finetuned-ade-512-512 из HuggingFace
как базу, дообученную на уличных сценах (ADE20K содержит billboard класс).

Если дообучить на своих данных — заменить MODEL_NAME на путь к своим весам.
"""

import cv2
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Модель из HuggingFace — скачается автоматически при первом запуске (~350MB)
MODEL_NAME = "nvidia/segformer-b4-finetuned-ade-512-512"

# ID классов в ADE20K которые относятся к баннерам/рекламе
# 6  = billboard, 22 = signboard, 93 = placard
BANNER_CLASS_IDS = {6, 22, 93}

_model = None
_processor = None


def get_segformer():
    global _model, _processor
    if _model is None:
        from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
        import torch
        logger.info(f"Загрузка SegFormer: {MODEL_NAME}...")
        _processor = SegformerImageProcessor.from_pretrained(MODEL_NAME)
        _model = SegformerForSemanticSegmentation.from_pretrained(MODEL_NAME)
        _model.eval()
        logger.info("SegFormer загружен.")
    return _model, _processor


# ─────────────────────────────────────────────
#  Основная функция — уточнение маски баннера
# ─────────────────────────────────────────────

def refine_banner_mask(
    image: np.ndarray,
    bbox: list[int],
    padding: int = 10,
    min_mask_ratio: float = 0.1,
) -> Optional[np.ndarray]:
    """
    Запускает SegFormer на ROI из bbox и возвращает бинарную маску баннера.

    Args:
        image:          полное изображение BGR
        bbox:           [x1, y1, x2, y2] от YOLOv8
        padding:        отступ вокруг bbox для контекста
        min_mask_ratio: если маска меньше X% ROI — возвращаем None (фолбэк на bbox)

    Returns:
        mask (np.ndarray uint8, 0/255) того же размера что ROI,
        или None если сегментация не нашла баннер.
    """
    try:
        import torch
        from PIL import Image as PILImage

        model, processor = get_segformer()

        x1, y1, x2, y2 = bbox
        h_img, w_img = image.shape[:2]

        # Вырезаем с паддингом
        rx1 = max(0, x1 - padding)
        ry1 = max(0, y1 - padding)
        rx2 = min(w_img, x2 + padding)
        ry2 = min(h_img, y2 + padding)
        roi_bgr = image[ry1:ry2, rx1:rx2]

        roi_h, roi_w = roi_bgr.shape[:2]
        if roi_h < 10 or roi_w < 10:
            return None

        # BGR → RGB → PIL
        roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(roi_rgb)

        # Инференс
        inputs = processor(images=pil_img, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)

        # Апскейл логитов до размера ROI
        logits = outputs.logits  # (1, num_classes, H/4, W/4)
        upsampled = torch.nn.functional.interpolate(
            logits,
            size=(roi_h, roi_w),
            mode="bilinear",
            align_corners=False,
        )
        pred = upsampled.argmax(dim=1)[0].numpy()  # (H, W)

        # Собираем маску по классам баннеров
        mask = np.zeros((roi_h, roi_w), dtype=np.uint8)
        for class_id in BANNER_CLASS_IDS:
            mask[pred == class_id] = 255

        # Морфология — убираем шум, заполняем дыры
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Проверяем что маска достаточно большая
        mask_ratio = mask.sum() / 255 / (roi_h * roi_w)
        if mask_ratio < min_mask_ratio:
            logger.debug(f"SegFormer: маска слишком мала ({mask_ratio:.2%}), фолбэк на bbox")
            return None

        logger.debug(f"SegFormer: маска {mask_ratio:.2%} ROI")
        return mask

    except Exception as e:
        logger.error(f"SegFormer ошибка: {e}")
        return None


def apply_mask_to_roi(roi: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Применяет маску к ROI — фон закрашивается нейтральным серым.
    Это убирает фоновый шум который мешает OCR.
    """
    if mask is None or mask.shape[:2] != roi.shape[:2]:
        return roi

    result = roi.copy()

    # Заполняем фон средним цветом баннера (меньше контраста на краях)
    mean_color = cv2.mean(roi, mask=mask)[:3]
    bg_color = tuple(int(c) for c in mean_color)

    # Инвертированная маска — это фон
    bg_mask = cv2.bitwise_not(mask)
    result[bg_mask > 0] = bg_color

    return result


def get_clean_roi_for_ocr(
    image: np.ndarray,
    bbox: list[int],
    padding: int = 15,
    use_segformer: bool = True,
) -> np.ndarray:
    """
    Главная функция — возвращает чистый ROI для OCR.

    Если SegFormer нашёл маску — применяет её (убирает фон).
    Если нет — возвращает простой bbox с паддингом (как раньше).

    Args:
        image:          полное изображение BGR
        bbox:           [x1, y1, x2, y2]
        padding:        отступ вокруг bbox
        use_segformer:  False = отключить SegFormer (только bbox)

    Returns:
        roi numpy array BGR
    """
    x1, y1, x2, y2 = bbox
    h_img, w_img = image.shape[:2]

    rx1 = max(0, x1 - padding)
    ry1 = max(0, y1 - padding)
    rx2 = min(w_img, x2 + padding)
    ry2 = min(h_img, y2 + padding)
    roi = image[ry1:ry2, rx1:rx2]

    if not use_segformer:
        return roi

    mask = refine_banner_mask(image, bbox, padding=padding)
    if mask is not None:
        roi = apply_mask_to_roi(roi, mask)

    return roi
