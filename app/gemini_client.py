"""
gemini_client.py — Shared Gemini API client with key rotation
=============================================================
Single source of truth for all Gemini calls across the app.
Handles:
  - Loading keys from .env (GEMINI_API_KEYS, GEMINI_API_KEY)
  - Round-robin key rotation
  - Per-key cooldown after 429/503 (skips exhausted keys automatically)
  - Retry with next key on quota errors

Usage:
    from gemini_client import call_gemini, get_key_status

    answer = call_gemini("Your prompt here")
    print(get_key_status())  # shows which keys are active/cooling down
"""

import os
import re
import json
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Optional, Tuple

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_MODEL  = "gemini-3.1-flash-lite"
QUOTA_ERRORS  = {429, 503}
COOLDOWN_SECS = 3600  # 1 hour cooldown per key after quota hit


# ── .env loader ───────────────────────────────────────────────────────────────

def _load_dotenv() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


# ── Key pool with rotation & cooldown ─────────────────────────────────────────

class _KeyPool:
    """
    Thread-safe API key pool with round-robin rotation and per-key cooldown.
    Keys that hit quota (429/503) are cooled down for COOLDOWN_SECS before
    being retried — this way a key that's exhausted for the day won't waste
    time on every request.
    """

    def __init__(self):
        self._lock        = threading.Lock()
        self._keys: List[str] = []
        self._cooldowns: dict = {}   # key → timestamp when cooled down
        self._index       = 0        # round-robin pointer
        self._loaded_from = ""       # track if env changed

    def _reload(self, extra_keys_raw: str = "") -> None:
        """Reload keys from env + any extra keys passed in (e.g. from UI)."""
        keys: List[str] = []
        for var in ("GEMINI_API_KEYS", "GEMINI_API_KEY"):
            raw = os.environ.get(var, "")
            for k in re.split(r"[,\n]", raw):
                k = k.strip()
                if k and k not in keys:
                    keys.append(k)
        for k in re.split(r"[,\n]", extra_keys_raw):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
        self._keys = keys

    def get_active_keys(self, extra_keys_raw: str = "") -> List[str]:
        """Return keys not currently in cooldown, reloading from env first."""
        with self._lock:
            self._reload(extra_keys_raw)
            now = time.time()
            active = [
                k for k in self._keys
                if now - self._cooldowns.get(k, 0) >= COOLDOWN_SECS
            ]
            return active

    def mark_quota_hit(self, key: str) -> None:
        """Put a key in cooldown after it hits quota."""
        with self._lock:
            self._cooldowns[key] = time.time()

    def mark_recovered(self, key: str) -> None:
        """Remove cooldown for a key that successfully responded."""
        with self._lock:
            self._cooldowns.pop(key, None)

    def status(self, extra_keys_raw: str = "") -> List[dict]:
        """Return status of all keys for display."""
        with self._lock:
            self._reload(extra_keys_raw)
            now   = time.time()
            result = []
            for k in self._keys:
                hit_at  = self._cooldowns.get(k, 0)
                elapsed = now - hit_at
                cooling = elapsed < COOLDOWN_SECS and hit_at > 0
                result.append({
                    "key_suffix": f"…{k[-8:]}",
                    "status":     "cooling" if cooling else "active",
                    "cooldown_remaining_min": max(0, int((COOLDOWN_SECS - elapsed) / 60)) if cooling else 0,
                })
            return result


_pool = _KeyPool()


# ── Core call ─────────────────────────────────────────────────────────────────

def _call_one(prompt: str, api_key: str,
              max_tokens: int = 1024,
              temperature: float = 0.3) -> str:
    """Call Gemini with one key. Raises RuntimeError on failure."""
    url     = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":    temperature,
            "maxOutputTokens": max_tokens,
            "topP": 0.9,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{url}?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in QUOTA_ERRORS:
            raise _QuotaError(f"Key …{api_key[-8:]} quota hit ({e.code})")
        body = e.read().decode("utf-8", errors="replace")[:200]
        raise RuntimeError(f"HTTP {e.code}: {body}")

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Gemini returned empty content.")
    return parts[0].get("text", "").strip()


class _QuotaError(Exception):
    pass


# ── Public API ────────────────────────────────────────────────────────────────

def call_gemini(
    prompt: str,
    extra_keys_raw: str = "",
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> Tuple[str, str]:
    """
    Call Gemini with automatic key rotation.

    Tries each active (non-cooling) key in order. If a key hits quota,
    it's cooled down and the next key is tried immediately.

    Args:
        prompt:         The prompt to send
        extra_keys_raw: Additional keys from UI (comma/newline separated)
        max_tokens:     Max output tokens
        temperature:    Sampling temperature

    Returns:
        (answer_text, used_key_suffix)  e.g. ("Some answer", "…abcd1234")

    Raises:
        RuntimeError: If all keys are exhausted or unavailable
    """
    active_keys = _pool.get_active_keys(extra_keys_raw)

    if not active_keys:
        # All keys cooling — check if any are close to recovery
        all_status = _pool.status(extra_keys_raw)
        mins = [s["cooldown_remaining_min"] for s in all_status if s["status"] == "cooling"]
        if mins:
            raise RuntimeError(
                f"All {len(all_status)} Gemini key(s) are in cooldown. "
                f"Fastest recovery in ~{min(mins)} min."
            )
        raise RuntimeError("No Gemini API keys configured.")

    last_error = None
    for key in active_keys:
        try:
            text = _call_one(prompt, key, max_tokens=max_tokens, temperature=temperature)
            _pool.mark_recovered(key)
            return text, f"…{key[-8:]}"
        except _QuotaError as e:
            _pool.mark_quota_hit(key)
            last_error = e
            continue   # try next key
        except RuntimeError as e:
            last_error = e
            raise      # non-quota error — don't retry

    raise RuntimeError(
        f"All {len(active_keys)} active Gemini key(s) exhausted. "
        f"Last error: {last_error}"
    )


def get_key_status(extra_keys_raw: str = "") -> str:
    """Return a human-readable status string for all keys."""
    statuses = _pool.status(extra_keys_raw)
    if not statuses:
        return "No keys configured."
    lines = []
    for s in statuses:
        if s["status"] == "active":
            lines.append(f"  {s['key_suffix']} ✅ active")
        else:
            lines.append(f"  {s['key_suffix']} ⏳ cooling (~{s['cooldown_remaining_min']}min left)")
    return "\n".join(lines)


def get_active_key_count(extra_keys_raw: str = "") -> int:
    """Return number of keys currently not in cooldown."""
    return len(_pool.get_active_keys(extra_keys_raw))
