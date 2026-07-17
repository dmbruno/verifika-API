import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verifika.db"),
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS verifications (
            id TEXT PRIMARY KEY,
            image_hash TEXT NOT NULL,
            record_hash TEXT NOT NULL,
            tx_hash TEXT NOT NULL,
            metadata TEXT NOT NULL,
            location_flag TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_verification(verification_id, image_hash, record_hash, tx_hash, metadata, location_flag):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO verifications
            (id, image_hash, record_hash, tx_hash, metadata, location_flag, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            verification_id,
            image_hash,
            record_hash,
            tx_hash,
            json.dumps(metadata, sort_keys=True),
            location_flag,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_verification(verification_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM verifications WHERE id = ?", (verification_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "image_hash": row["image_hash"],
        "record_hash": row["record_hash"],
        "tx_hash": row["tx_hash"],
        "metadata": json.loads(row["metadata"]),
        "location_flag": row["location_flag"],
        "created_at": row["created_at"],
    }
