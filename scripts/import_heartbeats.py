"""Импорт heartbeat-файлов с WebDAV в базу.

    python -m scripts.import_heartbeats file1.json [file2.json ...]

Формат файла: список объектов {"serial": "SN-0401", "ts": "2026-08-21T09:05:00+05:00",
"uptime_sec": 123456, "temp_c": 41.5}. Устройства шлют локальное время объекта со смещением.
"""
import json
import sys
from datetime import datetime

from app import db


def parse_ts(ts: str) -> str:
    """Приводит время из heartbeat к формату базы (YYYY-MM-DDTHH:MM:SS)."""
    return datetime.fromisoformat(ts).replace(tzinfo=None).isoformat(timespec="seconds")


def import_file(conn, path: str) -> tuple[int, int]:
    with open(path, encoding="utf-8") as f:
        items = json.load(f)

    imported = skipped = 0
    for hb in items:
        dev = conn.execute("SELECT id FROM devices WHERE serial = ?", (hb["serial"],)).fetchone()
        if dev is None:
            print(f"[skip] unknown device {hb['serial']} in {path}")
            skipped += 1
            continue
        ts = parse_ts(hb["ts"])
        conn.execute(
            "INSERT INTO heartbeats (device_id, received_at, uptime_sec, temp_c) VALUES (?, ?, ?, ?)",
            (dev["id"], ts, hb.get("uptime_sec"), hb.get("temp_c")),
        )
        conn.execute(
            "UPDATE devices SET last_seen = ? WHERE id = ? AND (last_seen IS NULL OR last_seen < ?)",
            (ts, dev["id"], ts),
        )
        imported += 1
    return imported, skipped


def main(paths: list[str]) -> None:
    if not paths:
        print(__doc__)
        sys.exit(2)
    conn = db.connect()
    for path in paths:
        imported, skipped = import_file(conn, path)
        conn.commit()
        print(f"{path}: imported={imported} skipped={skipped}")
    conn.close()


if __name__ == "__main__":
    main(sys.argv[1:])
