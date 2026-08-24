"""Kodex Devices: учёт устройств на объектах и обращений по ним. Подробности в README.md."""
from datetime import datetime, timedelta

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import db
from .config import API_KEY, OFFLINE_AFTER_MIN

app = FastAPI(title="Kodex Devices", version="0.3.1")


@app.on_event("startup")
def startup() -> None:
    # на всякий случай создаём таблицы, если базы ещё нет
    with db.connect() as conn:
        db.init_schema(conn)


def require_key(x_api_key: str | None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

#исправил 
def fmt_ts(value: str) -> str | None:
    # "2026-08-21T04:05:00" -> "2026-08-21 04:05"
    if value:
        return value[:16].replace("T", " ")
    else:
        return None


def device_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "serial": row["serial"],
        "site": row["site"],
        "model": row["model"],
        "installed_at": row["installed_at"],
        "last_seen": fmt_ts(row["last_seen"]),
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


@app.get("/devices")
def list_devices(site: str | None = None):
    sql = "SELECT id, serial, site, model, installed_at, last_seen FROM devices"
    params: list = []
    if site:
        sql += " WHERE site = ?"
        params.append(site)
    sql += " ORDER BY serial"
    with db.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/devices/{device_id}")
def get_device(device_id: int):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="device not found")
        result = device_to_dict(row)
        result["open_tickets"] = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE device_id = ? AND status = 'open'",
            (device_id,),
        ).fetchone()[0]
    return result


class TicketIn(BaseModel):
    serial: str
    title: str
    description: str | None = None


@app.post("/tickets")
def create_ticket(body: TicketIn, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    with db.connect() as conn:
        dev = conn.execute("SELECT id FROM devices WHERE serial = ?", (body.serial,)).fetchone()
        if dev is None:
            raise HTTPException(status_code=422, detail="Uncorrect serial number")
        cur = conn.execute(
            "INSERT INTO tickets (device_id, status, title, description, created_at) "
            "VALUES (?, 'open', ?, ?, ?)",
            (dev["id"], body.title, body.description,
             datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
    return {"id": cur.lastrowid, "status": "open"}


@app.get("/tickets")
def list_tickets(status: str | None = None, site: str | None = None, limit: int = 50):
    sql = """
        SELECT tickets.id, tickets.device_id, tickets.status, tickets.title,
        tickets.description, tickets.created_at, tickets.resolved_at, devices.site
        FROM tickets
        LEFT JOIN devices ON tickets.device_id = devices.id
        WHERE 1=1
    """
    
    params: list = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if site:
        sql += " AND site = ?"
        params.append(site)
    sql += " ORDER BY created_at DESC, tickets.id LIMIT ?"
    params.append(limit)
    with db.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@app.patch("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: int, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    now = datetime.utcnow().isoformat(timespec="seconds")
    with db.connect() as conn:
        conn.execute(
            "UPDATE tickets SET status = 'closed', resolved_at = ? WHERE id = ?",
            (now, ticket_id),
        )
        conn.commit()
    return {"id": ticket_id, "status": "closed", "resolved_at": now}

# 
@app.get("/report/summary")
def report_summary():
    sql = """
        SELECT d.site, d.serial, d.model, COUNT(t.id) AS open_tickets
        FROM devices d
        LEFT JOIN tickets t ON t.device_id = d.id AND t.status = 'open'
        GROUP BY d.id
        ORDER BY d.site, d.serial
    """
    with db.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


@app.get("/report/offline")
def report_offline(minutes: int = OFFLINE_AFTER_MIN):
    cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    sql = """
        SELECT serial, site, model, last_seen
        FROM devices
        WHERE last_seen IS NULL OR last_seen < ?
        ORDER BY site, serial
    """
    with db.connect() as conn:
        rows = conn.execute(sql, (cutoff,)).fetchall()
    return {"cutoff_utc": cutoff, "minutes": minutes, "devices": [dict(r) for r in rows]}
