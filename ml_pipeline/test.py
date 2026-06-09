"""
test.py — проверка финального пайплайна.
city-vision-control-new0404/ml/test.py
"""

import sys, logging
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

sys.path.insert(0, "ml/detectors")

import cv2
from yolo_detector import YOLOBannerDetector

IMG_PATH = r"D:\VIDEO_FRAMES\ALL_FRAMES\3.256.jpg"  # ← меняй
OUTPUT   = "result.jpg"

detector = YOLOBannerDetector(
    model_path="weights/best.pt",
    enable_ocr=True,
    enable_segformer=False,
    ocr_min_confidence=0.2,
    roi_padding=15,
    ocr_debug=True,
    classifier_debug=True,
)
import cv2, sys
sys.path.insert(0, "ml/detectors")

img = cv2.imread(r"D:\VIDEO_FRAMES\ALL_FRAMES\1.1031.jpg")  # фото с этажами
x1, y1, x2, y2 = 1054, 157, 1413, 368
pad = 15
roi = img[max(0,y1-pad):y2+pad, max(0,x1-pad):x2+pad]
cv2.imwrite("roi_etagi.jpg", roi)
print(f"ROI size: {roi.shape}")

annotated, detections = detector.detect_and_draw(IMG_PATH)
cv2.imwrite(OUTPUT, annotated)
print(f"\nРезультат: {OUTPUT}")
print(f"Баннеров: {len(detections)}\n")

for i, d in enumerate(detections, 1):
    print(f"[{i}] bbox={d['bbox']} det={d['confidence']:.2f}")
    print(f"     тип: {d.get('banner_type','?')} "
          f"(conf={d.get('classifier_conf',0):.2f})")
    if "ocr" in d:
        print(f"     текст: '{d['ocr']['text']}'")
        print(f"     OCR conf: {d['ocr']['confidence']:.2f}")
    print()
