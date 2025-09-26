# modules/session_registry.py
import sqlite3, time, os
from pathlib import Path
from typing import Optional, Tuple

DEFAULT_TTL_SECONDS = 2 * 60 * 60  # 2 hours

class SessionRegistry:
    """
    Shared session store using SQLite.
    Schema:
        username  TEXT PRIMARY KEY
        session_id TEXT
        last_seen  INTEGER (epoch seconds)
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                username  TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                last_seen  INTEGER NOT NULL
            )""")
            conn.commit()

    def upsert(self, username: str, session_id: str):
        now = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT INTO sessions(username, session_id, last_seen)
            VALUES(?,?,?)
            ON CONFLICT(username) DO UPDATE SET
                session_id=excluded.session_id,
                last_seen=excluded.last_seen
            """, (username, session_id, now))
            conn.commit()

    def get(self, username: str) -> Optional[Tuple[str, int]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT session_id, last_seen FROM sessions WHERE username=?", (username,))
            row = cur.fetchone()
            return (row[0], row[1]) if row else None

    def touch(self, username: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE sessions SET last_seen=? WHERE username=?", (int(time.time()), username))
            conn.commit()

    def delete_if_match(self, username: str, session_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE username=? AND session_id=?", (username, session_id))
            conn.commit()

    def cleanup_expired(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        cutoff = int(time.time()) - ttl_seconds
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE last_seen < ?", (cutoff,))
            conn.commit()
