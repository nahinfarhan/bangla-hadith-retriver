"""
embed.py — EmbeddingModel
=========================
Uses paraphrase-multilingual-mpnet-base-v2 (768-dim, 50+ languages including
Bengali and English) via a subprocess running Python 3.11.

WHY SUBPROCESS?
The system Python (3.13) has free-threading enabled, which causes segfaults
when PyTorch loads BERT-based models.  The hadith_qa conda env (Python 3.11)
is stable.  This module spawns that env's Python as a persistent child process
and communicates via stdin/stdout JSON to avoid the segfault entirely.

The subprocess is created once per process and reused (lazy singleton pattern).
"""

import os
import sys
import json
import subprocess
import threading
import atexit
from pathlib import Path
from typing import List

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ── Python 3.11 interpreter path (conda env) ──────────────────────────────
# Try multiple candidate paths so it works across different machines/setups.
_PY311_CANDIDATES = [
    "/opt/anaconda3/envs/hadith_qa/bin/python3.11",
    "/opt/homebrew/anaconda3/envs/hadith_qa/bin/python3.11",
    os.path.expanduser("~/anaconda3/envs/hadith_qa/bin/python3.11"),
    os.path.expanduser("~/miniconda3/envs/hadith_qa/bin/python3.11"),
    os.path.expanduser("~/opt/anaconda3/envs/hadith_qa/bin/python3.11"),
]

def _find_py311() -> str:
    """Return the first existing Python 3.11 path, or fall back to sys.executable."""
    for p in _PY311_CANDIDATES:
        if os.path.exists(p):
            return p
    # Last resort: ask conda directly
    try:
        result = subprocess.run(
            ["conda", "run", "-n", "hadith_qa", "python", "-c",
             "import sys; print(sys.executable)"],
            capture_output=True, text=True, timeout=10
        )
        exe = result.stdout.strip()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    # In Docker / CI the base image IS Python 3.11 — use the current interpreter
    print(f"[embed] Conda env not found — using current interpreter: {sys.executable}",
          flush=True)
    return sys.executable

_PY311 = _find_py311()
_SERVER_SCRIPT = str(Path(__file__).parent / "embed_server.py")

# Public constant so other modules can reference the model name
DEFAULT_MODEL = "paraphrase-multilingual-mpnet-base-v2"


# ── Subprocess singleton ───────────────────────────────────────────────────

class _EmbedProcess:
    """
    Manages a single long-lived Python 3.11 subprocess that runs embed_server.py.
    Thread-safe via a lock.
    """

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def _start(self):
        self._proc = subprocess.Popen(
            [_PY311, _SERVER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,          # forward model-load logs to console
            text=True,
            bufsize=1,                  # line-buffered
        )
        atexit.register(self._stop)

    def _stop(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
            self._proc = None

    def call(self, texts: List[str]) -> List[List[float]]:
        """Send texts to the subprocess, return embeddings."""
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._start()

            request = json.dumps({"texts": texts}) + "\n"
            self._proc.stdin.write(request)
            self._proc.stdin.flush()

            response_line = self._proc.stdout.readline()
            if not response_line:
                raise RuntimeError("embed_server subprocess died unexpectedly.")

            data = json.loads(response_line)
            if "error" in data:
                raise RuntimeError(f"embed_server error: {data['error']}")
            return data["embeddings"]


_embed_process = _EmbedProcess()


# ── Public API (drop-in replacement for old EmbeddingModel) ───────────────

class EmbeddingModel:
    """
    Multilingual embedding model (paraphrase-multilingual-mpnet-base-v2).
    Supports Bengali, English, Arabic, and 50+ other languages.
    Runs in a Python 3.11 subprocess to avoid free-threading segfaults.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        # model_name is accepted for API compatibility but the subprocess
        # always uses the pre-configured multilingual model.
        self.model_name = DEFAULT_MODEL

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts.  Returns a list of 768-dim float vectors.
        Processes in sub-batches of 32 to keep memory usage reasonable.
        """
        BATCH = 32
        all_embeddings: List[List[float]] = []
        for start in range(0, len(texts), BATCH):
            batch = texts[start : start + BATCH]
            embeddings = _embed_process.call(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query with the correct 'query: ' prefix for e5 models."""
        result = _embed_process.call([f"query: {query}"])
        return result[0]
