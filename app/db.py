import sqlite3

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id           INTEGER PRIMARY KEY,
    serial       TEXT NOT NULL UNIQUE,
    site         TEXT NOT NULL,
    model        TEXT NOT NULL,
    installed_at TEXT NOT NULL,
    last_seen    TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   INTEGER NOT NULL REFERENCES devices(id),
    status      TEXT NOT NULL DEFAULT 'open',
    title       TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS heartbeats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   INTEGER NOT NULL REFERENCES devices(id),
    received_at TEXT NOT NULL,
    uptime_sec  INTEGER,
    temp_c      REAL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
