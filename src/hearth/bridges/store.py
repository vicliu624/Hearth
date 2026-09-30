"""Durable bridge queue and explicit Matrix-to-LXMF routing."""

from __future__ import annotations
from contextlib import contextmanager
import json
import re
import sqlite3
import time
from pathlib import Path

MAX_TEXT_BYTES = 8192


def parse_message(body: str, reply_peer: str | None = None) -> tuple[str, str] | None:
    if reply_peer:
        lines = body.splitlines()
        while lines and lines[0].startswith(">"):
            lines.pop(0)
        text = "\n".join(lines).strip()
        peer = reply_peer
    else:
        match = re.fullmatch(r"!lxmf\s+([0-9a-fA-F]{32})\s+([\s\S]+)", body.strip())
        if not match:
            return None
        peer, text = match.group(1).lower(), match.group(2).strip()
    if not re.fullmatch(r"[0-9a-f]{32}", peer) or not text:
        return None
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("Message exceeds 8192 UTF-8 bytes")
    return peer, text


class BridgeStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, direction TEXT NOT NULL, peer TEXT NOT NULL,
              body TEXT NOT NULL, created REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
              attempts INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0,
              matrix_event TEXT, error TEXT);
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS replies (event TEXT PRIMARY KEY, peer TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS encrypted (id TEXT PRIMARY KEY, payload TEXT NOT NULL, retry_at REAL NOT NULL DEFAULT 0);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(self, key, direction, peer, body):
        with self.connect() as db:
            return (
                db.execute(
                    "INSERT OR IGNORE INTO jobs(id,direction,peer,body,created) VALUES(?,?,?,?,?)",
                    (key, direction, peer, body, time.time()),
                ).rowcount
                > 0
            )

    def ready(self, direction):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE direction=? AND status='pending' AND retry_at<=? ORDER BY created LIMIT 1",
                (direction, time.time()),
            ).fetchone()
            return dict(row) if row else None

    def claim(self, key):
        with self.connect() as db:
            return (
                db.execute(
                    "UPDATE jobs SET status='sending',attempts=attempts+1 WHERE id=? AND status='pending'",
                    (key,),
                ).rowcount
                > 0
            )

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE jobs SET status='pending' WHERE status='sending'")

    def complete(self, key, event=None):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET status='delivered',matrix_event=?,error=NULL WHERE id=?",
                (event, key),
            )
            row = db.execute("SELECT peer FROM jobs WHERE id=?", (key,)).fetchone()
            if event and row and row["peer"]:
                db.execute(
                    "INSERT OR REPLACE INTO replies VALUES(?,?)", (event, row["peer"])
                )

    def retry(self, key, error):
        with self.connect() as db:
            row = db.execute("SELECT attempts FROM jobs WHERE id=?", (key,)).fetchone()
            attempts = row["attempts"] if row else 1
            db.execute(
                "UPDATE jobs SET status=?,retry_at=?,error=? WHERE id=?",
                (
                    "failed" if attempts >= 5 else "pending",
                    time.time() + min(300, 2**attempts * 5),
                    error,
                    key,
                ),
            )

    def peer_for_reply(self, event):
        with self.connect() as db:
            row = db.execute(
                "SELECT peer FROM replies WHERE event=?", (event,)
            ).fetchone()
            return row["peer"] if row else None

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return json.loads(row["value"]) if row else default

    def set(self, key, value):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO meta VALUES(?,?)", (key, json.dumps(value))
            )

    def counts(self):
        with self.connect() as db:
            result = {
                row["status"]: row["n"]
                for row in db.execute(
                    "SELECT status,count(*) AS n FROM jobs GROUP BY status"
                )
            }
            result["awaiting_keys"] = db.execute(
                "SELECT count(*) FROM encrypted"
            ).fetchone()[0]
            return result

    def save_encrypted(self, event_id, payload):
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO encrypted(id,payload) VALUES(?,?)",
                (event_id, json.dumps(payload)),
            )

    def encrypted_ready(self):
        with self.connect() as db:
            rows = db.execute(
                "SELECT id,payload FROM encrypted WHERE retry_at<=? LIMIT 50",
                (time.time(),),
            ).fetchall()
            for row in rows:
                db.execute(
                    "UPDATE encrypted SET retry_at=? WHERE id=?",
                    (time.time() + 15, row["id"]),
                )
            return [(row["id"], json.loads(row["payload"])) for row in rows]

    def remove_encrypted(self, event_id):
        with self.connect() as db:
            db.execute("DELETE FROM encrypted WHERE id=?", (event_id,))

    def retry_failed(self):
        with self.connect() as db:
            return db.execute(
                "UPDATE jobs SET status='pending',attempts=0,retry_at=0 WHERE status='failed'"
            ).rowcount
