"""
Tests end-to-end contra Polygon Amoy real (sin mocks): cada test que llama a
POST /verify ancla una transaccion de verdad y gasta POL de testnet. Correr con:

    pytest tests/ -v
"""
import io
import random
import uuid

from PIL import Image
from PIL.ExifTags import IFD
from PIL.TiffImagePlugin import IFDRational


def _random_image_bytes():
    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    img = Image.new("RGB", (20, 20), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _random_image_with_gps_bytes(lat_ref, lat_dms, lon_ref, lon_dms):
    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    img = Image.new("RGB", (20, 20), color=color)
    exif = img.getexif()
    exif[IFD.GPSInfo] = {
        1: lat_ref,
        2: tuple(IFDRational(v, 1) for v in lat_dms),
        3: lon_ref,
        4: tuple(IFDRational(v, 1) for v in lon_dms),
    }
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def _post_verify(client, image_bytes, lat, lon, filename="test.jpg"):
    return client.post(
        "/verify",
        data={"image": (io.BytesIO(image_bytes), filename), "lat": str(lat), "lon": str(lon)},
        content_type="multipart/form-data",
    )


def test_verify_happy_path(client):
    resp = _post_verify(client, _random_image_bytes(), -34.6037, -58.3816)
    assert resp.status_code == 200

    body = resp.get_json()
    assert "verification_id" in body
    assert body["verify_url"] == f"/verify/{body['verification_id']}"

    get_resp = client.get(body["verify_url"])
    assert get_resp.status_code == 200

    get_body = get_resp.get_json()
    assert get_body["valid"] is True
    assert get_body["location_flag"] is None
    assert get_body["tx_hash"]


def test_verify_missing_image_returns_400(client):
    resp = client.post(
        "/verify",
        data={"lat": "-34.6037", "lon": "-58.3816"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_verify_get_nonexistent_id_returns_404(client):
    resp = client.get(f"/verify/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_verify_duplicate_image_rejected_onchain(client):
    """Misma imagen, distinta ubicacion (y por lo tanto distinto record_hash):
    el contrato debe rechazarla igual por su mapping de image_hash."""
    image_bytes = _random_image_bytes()

    resp1 = _post_verify(client, image_bytes, -34.6037, -58.3816, "dup.jpg")
    assert resp1.status_code == 200

    resp2 = _post_verify(client, image_bytes, 10.0, 20.0, "dup.jpg")
    assert resp2.status_code == 409
    assert "imagen" in resp2.get_json()["error"].lower()


def test_verify_location_mismatch_sets_flag(client):
    # EXIF GPS: Tokio (35.67N, 139.65E). Se declara Buenos Aires como ubicacion.
    image_bytes = _random_image_with_gps_bytes("N", (35, 40, 3), "E", (139, 39, 1))

    resp = _post_verify(client, image_bytes, -34.6037, -58.3816, "tokio.jpg")
    assert resp.status_code == 200

    get_resp = client.get(resp.get_json()["verify_url"])
    get_body = get_resp.get_json()
    assert get_body["location_flag"] is not None
    assert "500m" in get_body["location_flag"]
