"""
feedback.py — User feedback logging
===================================
Logs thumbs-up/down votes to a jsonl file for later analysis or fine-tuning.

Each vote is a JSON line with:
    {
      "ts": <unix timestamp>,
      "question": <user question string>,
      "answer": <bot answer string>,
      "vote": "up" | "down",
      "sources": [list of source dicts],
      "search_mode": "hybrid" | "simple"
    }

The log file lives at `data/feedback/votes.jsonl` and appends only — never
overwrites. It's a simple flat file so it can be pulled from the VPS and
analyzed with any JSONL-aware tool (jq, pandas, etc.).

Thread safety: we use a lock + atomic append (open in 'a' mode) so concurrent
votes from different sessions don't corrupt the file.
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Literal

# ── Config ────────────────────────────────────────────────────────────────────
_DEFAULT_LOG_DIR = Path(__file__).parent.parent / "data" / "feedback"
_LOG_FILE        = "votes.jsonl"

_lock = threading.Lock()


def log_vote(
    question: str,
    answer: str,
    vote: Literal["up", "down"],
    sources: List[Dict],
    search_mode: str = "hybrid",
    log_dir: Path = None,
) -> None:
    """
    Append a vote entry to the feedback log.

    Args:
        question:    The user's question.
        answer:      The bot's answer.
        vote:        "up" or "down".
        sources:     List of source dicts (ref, book, hadith_id, ...).
        search_mode: Which search mode was used ("hybrid" or "simple").
        log_dir:     Directory where votes.jsonl is stored.
                     Defaults to data/feedback/.
    """
    log_path = (log_dir or _DEFAULT_LOG_DIR) / _LOG_FILE

    entry = {
        "ts": int(time.time()),
        "question": question,
        "answer": answer,
        "vote": vote,
        "sources": [
            {
                "ref": s.get("ref"),
                "book": s.get("book"),
                "hadith_id": s.get("hadith_id"),
                "score": s.get("score"),
            }
            for s in sources
        ],
        "search_mode": search_mode,
    }

    with _lock:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # Non-fatal — a logging failure shouldn't crash the app
            print(f"[Feedback] Warning: could not log vote: {e}", flush=True)


def get_stats(log_dir: Path = None) -> Dict:
    """
    Read the feedback log and return basic stats: total votes, up/down counts.

    Returns:
        {"total": int, "up": int, "down": int}
    """
    log_path = (log_dir or _DEFAULT_LOG_DIR) / _LOG_FILE
    if not log_path.exists():
        return {"total": 0, "up": 0, "down": 0}

    with _lock:
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                entries = [json.loads(line) for line in f if line.strip()]
        except Exception:
            return {"total": 0, "up": 0, "down": 0}

    up_count   = sum(1 for e in entries if e.get("vote") == "up")
    down_count = sum(1 for e in entries if e.get("vote") == "down")

    return {"total": len(entries), "up": up_count, "down": down_count}
