"""Persistent SQLite database layer for DocuMind AI.

Stores sessions, messages, document metadata, analytics events, and admin
configuration so that administrators can monitor and manage the application.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Database location ─────────────────────────────────────────────────────────
_DB_DIR = Path(__file__).parent / "data"
_DB_PATH = _DB_DIR / "documind.db"


def _ensure_dir() -> None:
    _DB_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def _conn():
    _ensure_dir()
    con = sqlite3.connect(_DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ── Schema ────────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    created_at   TEXT NOT NULL,
    last_active  TEXT NOT NULL,
    ip_hint      TEXT,
    model_used   TEXT,
    doc_count    INTEGER DEFAULT 0,
    page_count   INTEGER DEFAULT 0,
    chunk_count  INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    filename    TEXT NOT NULL,
    pages       INTEGER,
    chunks      INTEGER,
    size_bytes  INTEGER,
    uploaded_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS messages (
    msg_id      TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    sources     TEXT,
    model       TEXT,
    latency_ms  INTEGER,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS analytics (
    event_id    TEXT PRIMARY KEY,
    session_id  TEXT,
    event_type  TEXT NOT NULL,
    payload     TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session  ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id);
CREATE INDEX IF NOT EXISTS idx_analytics_type    ON analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_date    ON analytics(created_at);
"""


def init_db() -> None:
    """Create all tables if they do not already exist."""
    with _conn() as con:
        con.executescript(_SCHEMA)
        defaults = {
            "max_upload_size_mb": "15",
            "max_files": "5",
            "max_total_pages": "200",
            "default_model": "gemini-2.5-flash",
            "top_k_default": "4",
            "rate_limit_queries_per_hour": "60",
            "maintenance_mode": "false",
            "welcome_message": "Welcome to DocuMind AI — upload your PDFs and start asking questions!",
        }
        for k, v in defaults.items():
            con.execute(
                "INSERT OR IGNORE INTO admin_settings(key, value, updated_at) VALUES (?,?,?)",
                (k, v, _now()),
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def create_session(model_used: str = "") -> str:
    sid = _uid()
    with _conn() as con:
        con.execute(
            "INSERT INTO sessions(session_id,created_at,last_active,model_used) VALUES(?,?,?,?)",
            (sid, _now(), _now(), model_used),
        )
    return sid


ALLOWED_SESSION_COLS = {
    "last_active", "model_used", "doc_count", "page_count", "chunk_count", "message_count", "ip_hint"
}


def touch_session(session_id: str, **kwargs) -> None:
    kwargs["last_active"] = _now()
    filtered = {k: v for k, v in kwargs.items() if k in ALLOWED_SESSION_COLS}
    if not filtered:
        return
    sets = ", ".join(f"{k}=?" for k in filtered)
    vals = list(filtered.values()) + [session_id]
    with _conn() as con:
        con.execute(f"UPDATE sessions SET {sets} WHERE session_id=?", vals)


def get_session(session_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        return dict(row) if row else None


def list_sessions(limit: int = 100) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM sessions ORDER BY last_active DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def record_document(
    session_id: str,
    filename: str,
    pages: int,
    chunks: int,
    size_bytes: int,
) -> str:
    doc_id = _uid()
    with _conn() as con:
        con.execute(
            "INSERT INTO documents VALUES(?,?,?,?,?,?,?)",
            (doc_id, session_id, filename, pages, chunks, size_bytes, _now()),
        )
    return doc_id


def list_documents(limit: int = 200) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM documents ORDER BY uploaded_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def save_message(
    session_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
    model: str = "",
    latency_ms: int = 0,
) -> str:
    msg_id = _uid()
    with _conn() as con:
        con.execute(
            "INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)",
            (
                msg_id,
                session_id,
                role,
                content,
                json.dumps(sources or []),
                model,
                latency_ms,
                _now(),
            ),
        )
        con.execute(
            "UPDATE sessions SET message_count=message_count+1, last_active=? WHERE session_id=?",
            (_now(), session_id),
        )
    return msg_id


def get_messages(session_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["sources"] = json.loads(d["sources"] or "[]")
            results.append(d)
        return results


def log_event(
    event_type: str,
    payload: dict | None = None,
    session_id: str | None = None,
) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO analytics VALUES(?,?,?,?,?)",
            (_uid(), session_id, event_type, json.dumps(payload or {}), _now()),
        )


def get_analytics_summary() -> dict:
    with _conn() as con:
        total_sessions = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        total_messages = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        total_docs = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        user_msgs = con.execute(
            "SELECT COUNT(*) FROM messages WHERE role='user'"
        ).fetchone()[0]
        daily = con.execute(
            """SELECT DATE(created_at) as day, COUNT(*) as cnt
               FROM messages WHERE role='user'
               GROUP BY day ORDER BY day DESC LIMIT 30"""
        ).fetchall()
        top_models = con.execute(
            """SELECT model, COUNT(*) as cnt FROM messages
               WHERE role='assistant' AND model!=''
               GROUP BY model ORDER BY cnt DESC"""
        ).fetchall()
        errors = con.execute(
            "SELECT COUNT(*) FROM analytics WHERE event_type='error'"
        ).fetchone()[0]
        avg_latency = con.execute(
            "SELECT AVG(latency_ms) FROM messages WHERE role='assistant' AND latency_ms>0"
        ).fetchone()[0]
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_docs": total_docs,
            "user_queries": user_msgs,
            "daily_queries": [dict(r) for r in daily],
            "top_models": [dict(r) for r in top_models],
            "errors": errors,
            "avg_latency_ms": round(avg_latency or 0, 1),
        }


def get_setting(key: str, default: str = "") -> str:
    with _conn() as con:
        row = con.execute(
            "SELECT value FROM admin_settings WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else default


def set_setting(key: str, value: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO admin_settings(key,value,updated_at) VALUES(?,?,?)",
            (key, value, _now()),
        )


def get_all_settings() -> dict[str, str]:
    with _conn() as con:
        rows = con.execute("SELECT key, value FROM admin_settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


def clear_analytics() -> None:
    """Clear all records from analytics table."""
    with _conn() as con:
        con.execute("DELETE FROM analytics")


def reset_settings() -> None:
    """Reset admin settings to defaults."""
    with _conn() as con:
        con.execute("DELETE FROM admin_settings")
    init_db()


init_db()
