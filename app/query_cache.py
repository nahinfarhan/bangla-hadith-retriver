"""
query_cache.py — Disk-backed query/answer cache
================================================
Persists Gemini answers to disk so repeated identical questions skip the
Gemini call entirely and return instantly at zero token cost.

Implementation
--------------
Uses stdlib `shelve` (backed by sqlite/gdbm) — zero extra dependencies.
Cache entries are stored as:
    key   : normalised question string  (lowercased, whitespace-collapsed)
    value : {"answer": str, "sources": list, "ts": float (unix timestamp)}

TTL (default 7 days) is checked on read — stale entries are treated as
misses and overwritten on the next real call.

Thread safety
-------------
shelve is not thread-safe for concurrent writes.  Streamlit runs one
session per thread, so concurrent same-key writes are possible but rare
and the worst case is a duplicate Gemini call (not data corruption) because
we open the shelf in a short-lived `with` block each time.

Usage
-----
    from query_cache import QueryCache
    cache = QueryCache()                    # singleton via @st.cache_resource

    hit = cache.get("কোরবানির নিয়ম কি?")
    if hit:
        answer, sources = hit
    else:
        answer, sources = ... expensive Gemini call ...
        cache.set("কোরবানির নিয়ম কি?", answer, sources)
"""

import re
import shelve
import time
import threading
from pathlib import Path
from typing import Optional, Tuple, List, Dict

# ── Config ────────────────────────────────────────────────────────────────────
_DEFAULT_CACHE_DIR = Path(__file__).parent.parent / "data" / "query_cache"
_CACHE_FILE        = "answers"          # shelve adds its own extension
_DEFAULT_TTL       = 7 * 24 * 3600     # 7 days in seconds
_WHITESPACE_RE     = re.compile(r"\s+")


def _normalize(question: str) -> str:
    """Lowercase and collapse whitespace for a stable cache key."""
    return _WHITESPACE_RE.sub(" ", question.strip().lower())


class QueryCache:
    """
    Disk-backed answer cache with TTL.

    Args:
        cache_dir : Directory where the shelve file is stored.
                    Defaults to data/query_cache/ next to the app.
        ttl       : Seconds before a cached entry is considered stale.
                    Default is 7 days.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl: int = _DEFAULT_TTL,
    ):
        self._dir  = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = str(self._dir / _CACHE_FILE)
        self._ttl  = ttl
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def get(
        self, question: str
    ) -> Optional[Tuple[str, List[Dict]]]:
        """
        Look up a question in the cache.

        Returns:
            (answer, sources) if a valid (non-stale) entry exists, else None.
        """
        key = _normalize(question)
        with self._lock:
            try:
                with shelve.open(self._path, flag="r") as db:
                    entry = db.get(key)
            except Exception:
                # Shelf may not exist yet on first run — treat as miss
                return None

        if entry is None:
            return None

        age = time.time() - entry.get("ts", 0)
        if age > self._ttl:
            return None     # stale — let it be overwritten

        return entry["answer"], entry["sources"]

    def set(
        self, question: str, answer: str, sources: List[Dict]
    ) -> None:
        """
        Store an answer in the cache.

        Only caches non-empty answers that don't look like error fallbacks.
        """
        if not answer or answer.startswith("_(AI answer unavailable"):
            return

        key   = _normalize(question)
        entry = {"answer": answer, "sources": sources, "ts": time.time()}

        with self._lock:
            try:
                with shelve.open(self._path, flag="c") as db:
                    db[key] = entry
            except Exception as e:
                # Non-fatal — a cache write failure just means no caching
                print(f"[QueryCache] Warning: could not write cache: {e}", flush=True)

    def invalidate(self, question: str) -> None:
        """Remove a specific question from the cache."""
        key = _normalize(question)
        with self._lock:
            try:
                with shelve.open(self._path, flag="c") as db:
                    db.pop(key, None)
            except Exception:
                pass

    def clear(self) -> None:
        """Wipe the entire cache."""
        with self._lock:
            try:
                with shelve.open(self._path, flag="n") as _:
                    pass    # opening with flag="n" creates an empty shelf
                print("[QueryCache] Cache cleared.", flush=True)
            except Exception as e:
                print(f"[QueryCache] Warning: could not clear cache: {e}", flush=True)

    def stats(self) -> Dict:
        """Return basic stats: total entries, oldest entry age in hours."""
        with self._lock:
            try:
                with shelve.open(self._path, flag="r") as db:
                    keys  = list(db.keys())
                    now   = time.time()
                    ages  = [now - db[k].get("ts", now) for k in keys]
            except Exception:
                return {"total": 0, "oldest_hours": 0}

        total = len(keys)
        oldest_hours = round(max(ages) / 3600, 1) if ages else 0
        return {"total": total, "oldest_hours": oldest_hours}
