"""
reranker.py — Cross-Encoder Re-ranker for Hadith Retrieval
===========================================================
Uses BAAI/bge-reranker-v2-m3 (multilingual, supports Bengali + English)
to re-score candidate hadiths after hybrid retrieval.

Why cross-encoder?
  Bi-encoder models (like our fine-tuned e5) encode query and document
  independently — fast but less accurate for relevance scoring.
  Cross-encoders see BOTH query and document together — much more accurate
  but too slow for full corpus search.  Solution: retrieve a large candidate
  set (e.g. top-50) cheaply, then re-rank with cross-encoder to get top-k.

Pipeline position:
  Dense retrieval (top-50) ──┐
                              ├─→ RRF merge (top-50) → Cross-Encoder → top-k
  BM25 retrieval  (top-50) ──┘

Usage:
    from reranker import CrossEncoderReranker
    reranker = CrossEncoderReranker()
    ranked = reranker.rerank(query, candidates, top_k=5)
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional

# ── Model selection ───────────────────────────────────────────────────────────
# BAAI/bge-reranker-v2-m3: multilingual cross-encoder, ~2.1GB
# Trained on MS MARCO + multilingual data, supports Bengali/Arabic/English
_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"

# Local fine-tuned reranker path (use if exists — takes priority)
_LOCAL_RERANKER = Path(__file__).parent.parent / "models" / "hadith-reranker-v1"


def _find_reranker_model() -> str:
    if _LOCAL_RERANKER.exists():
        print(f"[Reranker] Using local model: {_LOCAL_RERANKER}", flush=True)
        return str(_LOCAL_RERANKER)
    print(f"[Reranker] Using: {_DEFAULT_MODEL}", flush=True)
    return _DEFAULT_MODEL


class CrossEncoderReranker:
    """
    Cross-encoder re-ranker using BAAI/bge-reranker-v2-m3.

    Runs in the same Python 3.11 process as the embed_server.
    Loaded lazily on first use — model download is ~568MB on first run.
    """

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or _find_reranker_model()
        self._model = None  # lazy load

    def _ensure_loaded(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            print(f"[Reranker] Loading cross-encoder...", flush=True)
            self._model = CrossEncoder(
                self._model_name,
                max_length=512,
                device="cpu",   # CPU-safe; switch to "cuda" if GPU available
            )
            print("[Reranker] Ready.", flush=True)

    def rerank(self, query: str, candidates: List[Dict],
               top_k: int = 5, text_key: str = "text") -> List[Dict]:
        """
        Re-rank candidate hadiths using the cross-encoder.

        Args:
            query:      The original user query (or reframed query)
            candidates: List of hadith dicts from hybrid retrieval
            top_k:      Number of top results to return after re-ranking
            text_key:   Key in each dict that contains the hadith text

        Returns:
            Top-k candidates sorted by cross-encoder score (descending).
            Each dict gets a new "rerank_score" field.
        """
        if not candidates:
            return []

        self._ensure_loaded()

        # Build (query, document) pairs for the cross-encoder
        # Truncate hadith text to avoid exceeding max_length
        pairs = [
            (query, c.get(text_key, "")[:800])
            for c in candidates
        ]

        # Score all pairs at once (batched internally by sentence-transformers)
        scores = self._model.predict(pairs, show_progress_bar=False)

        # Attach scores and sort
        scored = []
        for candidate, score in zip(candidates, scores):
            c = dict(candidate)
            c["rerank_score"] = float(score)
            scored.append(c)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]
