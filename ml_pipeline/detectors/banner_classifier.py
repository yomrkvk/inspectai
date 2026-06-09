"""
banner_classifier.py — классификация типа баннера по ROI.
Без EfficientNet — используем визуальные признаки ROI.
Если накопишь 100+ размеченных примеров — можно заменить на EfficientNet.

ml/detectors/banner_classifier.py
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Типы баннеров
ELECTRONIC = "electronic"   # электронный билборд (тёмная рамка, светящийся экран)
BILLBOARD  = "billboard"    # обычный печатный баннер
UNKNOWN    = "unknown"


def classify_banner(roi: np.ndarray, debug: bool = False) -> dict:
    """
    Определяет тип баннера по ROI.

    Признаки ELECTRONIC:
    - Тёмная рамка по краям (пиксели края темнее центра)
    - Высокая насыщенность цветов (яркий экран)
    - Высокий локальный контраст

    Признаки BILLBOARD:
    - Равномерный фон (одноцветный или с низкой вариативностью)
    - Матовая поверхность (низкая насыщенность или специфический цвет фона)
    - Нет тёмной рамки

    Returns:
        {
            "type": "electronic" | "billboard" | "unknown",
            "confidence": float,
            "scores": {...}   # отладочные очки признаков
        }
    """
    if roi is None or roi.size == 0:
        return {"type": UNKNOWN, "confidence": 0.0, "scores": {}}

    h, w = roi.shape[:2]
    if h < 20 or w < 20:
        return {"type": UNKNOWN, "confidence": 0.0, "scores": {}}

    scores = {}

    # ── Признак 1: тёмная рамка по краям ────────────────────────
    # У электронных билбордов края (рамка) заметно темнее центра
    border_w = max(3, int(min(h, w) * 0.08))  # 8% от меньшей стороны

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Яркость краёв
    top    = gray[:border_w, :]
    bottom = gray[-border_w:, :]
    left   = gray[:, :border_w]
    right  = gray[:, -border_w:]
    border_brightness = np.mean([top.mean(), bottom.mean(),
                                  left.mean(), right.mean()])

    # Яркость центра
    center = gray[border_w:-border_w, border_w:-border_w]
    center_brightness = center.mean()

    # Разница: если края темнее центра на >30 — электронный
    dark_frame_score = center_brightness - border_brightness
    scores["dark_frame"] = round(float(dark_frame_score), 1)

    # ── Признак 2: насыщенность (электронные ярче) ───────────────
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].mean()
    scores["saturation"] = round(float(saturation), 1)

    # ── Признак 3: яркость центра (экран светится) ───────────────
    center_value = hsv[border_w:-border_w, border_w:-border_w, 2].mean()
    scores["center_brightness"] = round(float(center_value), 1)

    # ── Признак 4: равномерность фона (billboard = однотонный) ───
    # Стандартное отклонение яркости — у billboard ниже
    bg_std = gray.std()
    scores["bg_std"] = round(float(bg_std), 1)

    # ── Признак 5: тёмность рамки абсолютная ─────────────────────
    # У электронных рамка реально тёмная (<50)
    scores["border_brightness"] = round(float(border_brightness), 1)

    # ── Классификация ─────────────────────────────────────────────
    electronic_score = 0
    billboard_score  = 0

    # Тёмная рамка — сильный признак электронного
    if dark_frame_score > 30:
        electronic_score += 3
    elif dark_frame_score > 15:
        electronic_score += 1
    else:
        billboard_score += 2

    # Абсолютная тёмность краёв
    if border_brightness < 60:
        electronic_score += 2
    elif border_brightness < 90:
        electronic_score += 1
    else:
        billboard_score += 1

    # Высокая насыщенность — электронный (яркий экран)
    if saturation > 80:
        electronic_score += 2
    elif saturation > 50:
        electronic_score += 1
    else:
        billboard_score += 2

    # Высокий контраст — электронный
    if bg_std > 70:
        electronic_score += 1
    else:
        billboard_score += 1

    # Итог
    total = electronic_score + billboard_score
    if total == 0:
        banner_type = UNKNOWN
        confidence  = 0.0
    elif electronic_score > billboard_score:
        banner_type = ELECTRONIC
        confidence  = electronic_score / total
    else:
        banner_type = BILLBOARD
        confidence  = billboard_score / total

    if debug:
        logger.info(
            f"  Классификация: {banner_type} (conf={confidence:.2f}) | "
            f"e={electronic_score} b={billboard_score} | {scores}"
        )

    return {
        "type":       banner_type,
        "confidence": round(confidence, 2),
        "scores":     scores,
    }
