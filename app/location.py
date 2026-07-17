from PIL import Image
from PIL.ExifTags import GPSTAGS
import io
from math import radians, sin, cos, sqrt, atan2


def extract_exif_gps(image_bytes: bytes) -> dict | None:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img._getexif()
        if not exif:
            return None
        gps_info = {GPSTAGS.get(k, k): v for k, v in exif.get(34853, {}).items()}
        if not gps_info:
            return None

        def to_decimal(dms, ref):
            deg, min_, sec = dms
            val = deg + min_/60 + sec/3600
            return -val if ref in ("S", "W") else val

        lat = to_decimal(gps_info["GPSLatitude"], gps_info["GPSLatitudeRef"])
        lon = to_decimal(gps_info["GPSLongitude"], gps_info["GPSLongitudeRef"])
        return {"lat": lat, "lon": lon}
    except Exception:
        return None


def distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))
