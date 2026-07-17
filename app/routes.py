import hashlib
import json
import uuid
from datetime import datetime, timezone

from flask import jsonify, request

from app import app, db
from app.blockchain import (
    HashAlreadyRegisteredError,
    ImageAlreadyRegisteredError,
    anchor_hash,
    check_registered,
)
from app.location import distance_meters, extract_exif_gps

MAX_DISTANCE_METERS = 500


@app.route("/")
def landing():
    return app.send_static_file("index.html")


@app.route("/verify", methods=["POST"])
def verify():
    if "image" not in request.files:
        return jsonify({"error": "falta el campo 'image'"}), 400

    image_bytes = request.files["image"].read()
    if not image_bytes:
        return jsonify({"error": "imagen vacia"}), 400

    image_hash = hashlib.sha256(image_bytes).hexdigest()

    client_lat = request.form.get("lat", type=float)
    client_lon = request.form.get("lon", type=float)

    exif_gps = extract_exif_gps(image_bytes)
    exif_lat = float(exif_gps["lat"]) if exif_gps else None
    exif_lon = float(exif_gps["lon"]) if exif_gps else None

    location_flag = None
    have_both = None not in (client_lat, client_lon, exif_lat, exif_lon)
    if have_both:
        dist = distance_meters(client_lat, client_lon, exif_lat, exif_lon)
        if dist > MAX_DISTANCE_METERS:
            location_flag = (
                f"distancia entre ubicacion declarada y EXIF: {dist:.1f}m "
                f"(supera el umbral de {MAX_DISTANCE_METERS}m)"
            )

    record = {
        "image_hash": image_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_lat": client_lat,
        "client_lon": client_lon,
        "exif_lat": exif_lat,
        "exif_lon": exif_lon,
    }

    record_hash = hashlib.sha256(
        json.dumps(record, sort_keys=True).encode()
    ).hexdigest()

    try:
        tx_hash = anchor_hash(image_hash, record_hash)
    except ImageAlreadyRegisteredError:
        return jsonify({
            "error": "Esta imagen ya fue verificada anteriormente",
        }), 409
    except HashAlreadyRegisteredError:
        return jsonify({
            "error": "Este registro (imagen + timestamp + ubicacion) ya fue anclado antes",
        }), 409

    verification_id = str(uuid.uuid4())

    db.save_verification(
        verification_id=verification_id,
        image_hash=image_hash,
        record_hash=record_hash,
        tx_hash=tx_hash,
        metadata=record,
        location_flag=location_flag,
    )

    return jsonify({
        "verification_id": verification_id,
        "verify_url": f"/verify/{verification_id}",
    })


@app.route("/verify/<verification_id>", methods=["GET"])
def get_verification_endpoint(verification_id):
    stored = db.get_verification(verification_id)
    if stored is None:
        return jsonify({"error": "verification_id no encontrado"}), 404

    record_hash = hashlib.sha256(
        json.dumps(stored["metadata"], sort_keys=True).encode()
    ).hexdigest()

    registered_at = check_registered(record_hash)
    valid = registered_at > 0

    return jsonify({
        "valid": valid,
        "tx_hash": stored["tx_hash"],
        "location_flag": stored["location_flag"],
    })
