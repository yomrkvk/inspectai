"""
OCR сервис — финальная версия с классификацией типа баннера.
Разные стратегии для electronic и billboard.
ml/detectors/ocr_service.py
"""

import cv2
import numpy as np
import logging
import difflib

logger = logging.getLogger(__name__)

_reader = None


def get_ocr_reader():
    global _reader
    if _reader is None:
        import easyocr
        logger.info("Инициализация EasyOCR...")
        _reader = easyocr.Reader(['ru', 'en'], gpu=False)
    return _reader


# ─────────────────────────────────────────────
#  Постобработка
# ─────────────────────────────────────────────

_CONFUSABLE = {
    'A': 'А', 'B': 'В', 'E': 'Е', 'K': 'К', 'M': 'М',
    'H': 'Н', 'O': 'О', 'P': 'Р', 'C': 'С', 'T': 'Т',
    'Y': 'У', 'X': 'Х',
    'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с',
    'y': 'у', 'x': 'х',
}

def fix_mixed_text(text: str) -> str:
    words = text.split()
    result = []
    for word in words:
        cyr = sum(1 for c in word if '\u0400' <= c <= '\u04FF')
        lat = sum(1 for c in word if c.isalpha() and c.isascii())
        if cyr > 0 and lat > 0 and cyr >= lat:
            word = ''.join(_CONFUSABLE.get(c, c) for c in word)
        result.append(word)
    return ' '.join(result)


def deduplicate_words(words: list) -> list:
    seen, result = [], []
    for w in words:
        tl = w["text"].lower().strip()
        if not any(difflib.SequenceMatcher(None, tl, s).ratio() > 0.85
                   for s in seen):
            seen.append(tl)
            result.append(w)
    return result


# ─────────────────────────────────────────────
#  Предобработка — стратегии по типу баннера
# ─────────────────────────────────────────────

def _upscale(img: np.ndarray, min_h=220, min_w=350) -> np.ndarray:
    h, w = img.shape[:2]
    scale = max(1.0, min_h / h, min_w / w)
    return img if scale <= 1.0 else cv2.resize(
        img, (int(w * scale), int(h * scale)),
        interpolation=cv2.INTER_LANCZOS4
    )


def get_variants_electronic(roi: np.ndarray) -> list:
    """
    Электронный билборд:
    - Тёмный фон с яркими пикселями
    - Инверсия идёт первой
    - Убираем тёмную рамку перед OCR
    """
    big = _upscale(roi)
    h, w = big.shape[:2]

    # Обрезаем рамку (8% с каждой стороны)
    crop = int(min(h, w) * 0.08)
    if crop > 0 and h > crop*3 and w > crop*3:
        big = big[crop:-crop, crop:-crop]

    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))

    return [
        ("e_inv_clahe", clahe.apply(cv2.bitwise_not(gray))),
        ("e_inverted",  cv2.bitwise_not(gray)),
        ("e_color",     big),
        ("e_clahe",     clahe.apply(gray)),
    ]


def get_variants_billboard(roi: np.ndarray) -> list:
    """
    Обычный печатный баннер:
    - Определяем доминирующий цвет фона
    - Красный фон → синий канал
    - Светлый фон → резкость + цвет
    """
    big = _upscale(roi)
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])

    # Проверяем красный фон
    hsv = cv2.cvtColor(big, cv2.COLOR_BGR2HSV)
    h, w = big.shape[:2]
    mask1 = cv2.inRange(hsv, (0, 80, 80), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (160, 80, 80), (180, 255, 255))
    red_ratio = (cv2.countNonZero(mask1) + cv2.countNonZero(mask2)) / (h * w)

    if red_ratio > 0.15:
        # Красный фон — синий канал даёт лучший контраст
        b_ch = big[:, :, 0]
        return [
            ("b_blue_ch",  b_ch),
            ("b_inv_blue", cv2.bitwise_not(b_ch)),
            ("b_color",    big),
            ("b_clahe",    clahe.apply(gray)),
        ]
    else:
        # Обычный фон
        return [
            ("b_color",    big),
            ("b_clahe",    clahe.apply(gray)),
            ("b_sharp",    cv2.filter2D(gray, -1, kernel)),
            ("b_inv_clahe", clahe.apply(cv2.bitwise_not(gray))),
        ]


def get_variants_auto(roi: np.ndarray) -> list:
    """Авто — когда тип неизвестен, пробуем всё."""
    big = _upscale(roi)
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return [
        ("auto_color",     big),
        ("auto_clahe",     clahe.apply(gray)),
        ("auto_inv_clahe", clahe.apply(cv2.bitwise_not(gray))),
        ("auto_inverted",  cv2.bitwise_not(gray)),
        ("auto_sharp",     cv2.filter2D(gray, -1, kernel)),
    ]


# ─────────────────────────────────────────────
#  EasyOCR runner
# ─────────────────────────────────────────────

def _run_ocr(reader, img: np.ndarray, min_conf: float) -> list:
    if len(img.shape) == 2:
        pass  # grayscale — ок
    results = reader.readtext(
        img,
        detail=1,
        paragraph=False,
        width_ths=0.7,
        contrast_ths=0.1,
        adjust_contrast=0.5,
        text_threshold=0.5,
        low_text=0.3,
    )
    words = []
    for item in results:
        if len(item) != 3:
            continue
        bbox, text, conf = item
        text = text.strip()
        if conf >= min_conf and text:
            text = fix_mixed_text(text)
            words.append({
                "text":       text,
                "confidence": round(float(conf), 3),
                "bbox":       bbox,
            })
    return words


def _build_output(words: list, extra: dict = None) -> dict:
    words = deduplicate_words(words)
    full_text = " ".join(w["text"] for w in words)
    avg_conf  = sum(w["confidence"] for w in words) / len(words) if words else 0.0
    result = {"text": full_text, "words": words, "confidence": round(avg_conf, 3)}
    if extra:
        result.update(extra)
    return result


def _score(out: dict) -> tuple:
    return (len(out.get("words", [])), out.get("confidence", 0.0))


def _read_with_strips(reader, img: np.ndarray, min_conf: float,
                      n_strips: int = 3, debug: bool = False) -> list:
    h = img.shape[0]
    strip_h  = h // n_strips
    overlap  = int(strip_h * 0.15)
    all_words = []
    for i in range(n_strips):
        y1 = max(0, i * strip_h - overlap)
        y2 = min(h, (i + 1) * strip_h + overlap)
        words = _run_ocr(reader, img[y1:y2], min_conf)
        if debug and words:
            logger.info(f"    полоса {i}: {[w['text'] for w in words]}")
        all_words.extend(words)
    return deduplicate_words(all_words)


# ─────────────────────────────────────────────
#  Публичный API
# ─────────────────────────────────────────────

def read_text_from_roi(
    roi: np.ndarray,
    banner_type: str = "unknown",   # "electronic" | "billboard" | "unknown"
    min_confidence: float = 0.2,
    debug: bool = False,
) -> dict:
    """
    Читает текст с баннера, используя стратегию под тип.

    Args:
        roi:          numpy BGR array
        banner_type:  тип от banner_classifier
        min_confidence: порог уверенности OCR
        debug:        подробный лог
    """
    if roi is None or roi.size == 0:
        return {"text": "", "words": [], "confidence": 0.0}

    try:
        reader = get_ocr_reader()

        # Выбираем стратегию по типу
        if banner_type == "electronic":
            variants     = get_variants_electronic(roi)
            min_conf_use = min_confidence        # электронные — стандартный порог
        elif banner_type == "billboard":
            variants     = get_variants_billboard(roi)
            min_conf_use = min_confidence + 0.05  # billboard — чуть строже
        else:
            variants     = get_variants_auto(roi)
            min_conf_use = min_confidence

        if debug:
            logger.info(f"  OCR стратегия: '{banner_type}' | вариантов: {len(variants)}")

        best = {"text": "", "words": [], "confidence": 0.0}

        for name, img_var in variants:
            words = _run_ocr(reader, img_var, min_conf_use)
            out   = _build_output(words)

            if debug:
                logger.info(
                    f"  [{name:18s}] '{out['text']}' "
                    f"conf={out['confidence']:.2f} words={len(out['words'])}"
                )

            if _score(out) > _score(best):
                best = out

        # Полосы если мало слов (только для не-маленьких ROI)
        h, w = roi.shape[:2]
        is_small = min(h, w) < 100
        needs_strips = (
            not is_small and (
                len(best.get("words", [])) < 2 or
                (len(best.get("words", [])) < 4 and
                 best.get("confidence", 0) < 0.5)
            )
        )

        if needs_strips:
            if debug:
                logger.info("  → Стратегия полос...")
            best_img = _upscale(variants[0][1])
            if len(best_img.shape) == 2:
                best_img = cv2.cvtColor(best_img, cv2.COLOR_GRAY2BGR)
            strip_words = _read_with_strips(reader, best_img, min_conf_use, debug=debug)
            strip_out   = _build_output(strip_words)
            if _score(strip_out) > _score(best):
                best = strip_out
                if debug:
                    logger.info(f"  → Полосы лучше: '{best['text']}'")

        best["banner_type"] = banner_type
        return best

    except Exception as e:
        logger.error(f"OCR ошибка: {e}")
        return {"text": "", "words": [], "confidence": 0.0, "error": str(e)}
