"""
filter_banners.py — находит все фото с баннерами и копирует их в отдельную папку.
Без маркировок, просто оригинальные фотографии.
"""

import sys
import shutil
import logging
logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")

sys.path.insert(0, "ml/detectors")

from pathlib import Path
from ultralytics import YOLO

# ─── Настройки ───────────────────────────────
INPUT_DIR  = r"D:\VIDEO_FRAMES\ALL_FRAMES"
OUTPUT_DIR = r"D:\VIDEO_FRAMES\WITH_BANNERS"
MODEL_PATH = "weights/best.pt"
CONF       = 0.25   # порог уверенности детекции
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
# ─────────────────────────────────────────────

model = YOLO(MODEL_PATH)

input_path  = Path(INPUT_DIR)
output_path = Path(OUTPUT_DIR)
output_path.mkdir(parents=True, exist_ok=True)

images = sorted([
    f for f in input_path.iterdir()
    if f.suffix.lower() in EXTENSIONS
])

print(f"\nНайдено фотографий: {len(images)}")
print(f"Копирую в:          {OUTPUT_DIR}\n")
print("-" * 50)

found = 0

for idx, img_path in enumerate(images, 1):
    print(f"[{idx}/{len(images)}] {img_path.name}", end=" ... ", flush=True)

    results = model(str(img_path), conf=CONF, verbose=False)[0]

    if len(results.boxes) > 0:
        shutil.copy2(img_path, output_path / img_path.name)
        found += 1
        print(f"✓ баннеров: {len(results.boxes)}")
    else:
        print("нет")

print("-" * 50)
print(f"\nОбработано: {len(images)} фото")
print(f"С баннерами: {found} фото → {OUTPUT_DIR}\n")
