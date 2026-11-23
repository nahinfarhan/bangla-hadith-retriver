"""
query_logger.py — Anonymous first-party query log (SQLite)
==========================================================
Stores each question, the generated answer, the retrieved hadith IDs and the
end-to-end latency in a local SQLite file so search quality can be reviewed.

Privacy: strictly anonymous. No IP address, user ID, session ID or cookie is
ever written. Nothing from this module is sent to a third party.

Location: <project root>/data/query_logs.db  (/app/data/query_logs.db in
Docker, /opt/hadith-app/data/query_logs.db on the VPS). Override with the
QUERY_LOG_DB environment variable.

Every public function swallows its own errors: logging must never break the
user's answer.
"""
import json
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

_DEFAULT_DB = Path(__file__).parent.parent / "data" / "query_logs.db"
DB_PATH = Path(os.environ.get("QUERY_LOG_DB", str(_DEFAULT_DB)))

_TIMEOUT_S = 10  # wait up to 10 s for a write lock

_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_logs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp            TEXT    NOT NULL,
    query                TEXT    NOT NULL,
    answer               TEXT    NOT NULL,
    retrieved_hadith_ids TEXT    NOT NULL,
    latency_ms           INTEGER NOT NULL,
    feedback             TEXT    DEFAULT NULL
)
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=_TIMEOUT_S)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _warn(what: str, exc: Exception) -> None:
    print(f"[query_logger] {what} failed: {exc}", file=sys.stderr, flush=True)


def init_log_db() -> bool:
    """Create the database and table if missing. Returns True on success."""
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with closing(_connect()) as conn, conn:
            conn.execute(_SCHEMA)
        return True
    except Exception as exc:
        _warn("init_log_db", exc)
        return False


def log_qa(query: str, answer: str, hadith_ids: Iterable, latency_ms: int) -> int:
    """Insert one question/answer record. Returns the new row id, or -1 on error."""
    try:
        ids_json = json.dumps([str(i) for i in (hadith_ids or [])], ensure_ascii=False)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with closing(_connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO query_logs "
                "(timestamp, query, answer, retrieved_hadith_ids, latency_ms) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts, query or "", answer or "", ids_json, int(latency_ms)),
            )
            return int(cur.lastrowid)
    except Exception as exc:
        _warn("log_qa", exc)
        return -1


def save_feedback(log_id: int, feedback: str) -> None:
    """Attach 'up' or 'down' feedback to a logged row (reserved for future use)."""
    if feedback not in ("up", "down") or log_id is None or log_id < 0:
        return
    try:
        with closing(_connect()) as conn, conn:
            conn.execute(
                "UPDATE query_logs SET feedback = ? WHERE id = ?", (feedback, log_id)
            )
    except Exception as exc:
        _warn("save_feedback", exc)


def prune_old_logs(days: int = 90) -> int:
    """Delete rows older than `days`. Returns the number of rows removed."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(
            timespec="seconds"
        )
        with closing(_connect()) as conn, conn:
            cur = conn.execute("DELETE FROM query_logs WHERE timestamp < ?", (cutoff,))
            return cur.rowcount
    except Exception as exc:
        _warn("prune_old_logs", exc)
        return 0


def hadith_ids_from_sources(sources: Optional[Iterable[dict]]) -> list:
    """Turn retrieval source dicts into stable IDs like 'Sahih_Bukhari:123'."""
    out = []
    for s in sources or []:
        book = str(s.get("book", "")).replace(" ", "_")
        out.append(f"{book}:{s.get('hadith_id', '?')}")
    return out
