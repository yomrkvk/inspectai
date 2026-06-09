"""
EXIF metadata extraction service.
Extracts GPS, datetime, camera info from uploaded images.
"""
import logging
import struct
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)


def _convert_to_degrees(value) -> float:
    """Convert GPS coordinates from DMS tuple to decimal degrees."""
    try:
        d, m, s = value
        # Handle IFDRational or plain tuples
        d = float(d)
        m = float(m)
        s = float(s)
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return 0.0


def extract_exif(image_path: str) -> Dict[str, Any]:
    """
    Extract all EXIF metadata from image file.
    
    Returns dict with:
      - raw: all EXIF tags as strings
      - gps_lat, gps_lon: decimal degrees or None
      - capture_datetime: datetime or None
      - camera_make, camera_model: str or None
      - has_gps: bool
    """
    result: Dict[str, Any] = {
        "raw": {},
        "gps_lat": None,
        "gps_lon": None,
        "capture_datetime": None,
        "camera_make": None,
        "camera_model": None,
        "has_gps": False,
        "width": None,
        "height": None,
    }

    try:
        img = Image.open(image_path)
        result["width"] = img.width
        result["height"] = img.height

        exif_data = img._getexif()
        if not exif_data:
            return result

        decoded: Dict[str, Any] = {}
        gps_info: Dict[str, Any] = {}

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, str(tag_id))
            if tag == "GPSInfo":
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
                    gps_info[gps_tag] = gps_value
            else:
                try:
                    decoded[tag] = str(value)[:256]
                except Exception:
                    decoded[tag] = repr(value)[:256]

        result["raw"] = decoded

        # Camera
        result["camera_make"] = decoded.get("Make")
        result["camera_model"] = decoded.get("Model")

        # Datetime
        for dt_tag in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
            if dt_tag in decoded:
                try:
                    result["capture_datetime"] = datetime.strptime(
                        decoded[dt_tag], "%Y:%m:%d %H:%M:%S"
                    )
                    break
                except ValueError:
                    pass

        # GPS
        if gps_info:
            lat_val = gps_info.get("GPSLatitude")
            lat_ref = gps_info.get("GPSLatitudeRef", "N")
            lon_val = gps_info.get("GPSLongitude")
            lon_ref = gps_info.get("GPSLongitudeRef", "E")

            if lat_val and lon_val:
                lat = _convert_to_degrees(lat_val)
                lon = _convert_to_degrees(lon_val)
                if lat_ref == "S":
                    lat = -lat
                if lon_ref == "W":
                    lon = -lon
                result["gps_lat"] = round(lat, 7)
                result["gps_lon"] = round(lon, 7)
                result["has_gps"] = True

    except Exception as e:
        logger.warning(f"EXIF extraction failed for {image_path}: {e}")

    return result


def summarize_exif(exif: Dict[str, Any]) -> Dict[str, Any]:
    """Return user-friendly summary of EXIF data for display."""
    summary = []

    if exif.get("camera_make") or exif.get("camera_model"):
        make = exif.get("camera_make", "")
        model = exif.get("camera_model", "")
        summary.append({"key": "Камера", "value": f"{make} {model}".strip()})

    if exif.get("capture_datetime"):
        summary.append({
            "key": "Дата съёмки",
            "value": exif["capture_datetime"].strftime("%d.%m.%Y %H:%M:%S")
        })

    if exif.get("has_gps"):
        summary.append({
            "key": "GPS координаты",
            "value": f"{exif['gps_lat']:.6f}, {exif['gps_lon']:.6f}"
        })

    raw = exif.get("raw", {})
    for key in ("FocalLength", "ExposureTime", "FNumber", "ISOSpeedRatings", "Flash"):
        if key in raw:
            labels = {
                "FocalLength": "Фокусное расстояние",
                "ExposureTime": "Выдержка",
                "FNumber": "Диафрагма",
                "ISOSpeedRatings": "ISO",
                "Flash": "Вспышка",
            }
            summary.append({"key": labels.get(key, key), "value": raw[key]})

    if exif.get("width") and exif.get("height"):
        summary.append({"key": "Разрешение", "value": f"{exif['width']} × {exif['height']} px"})

    return summary
