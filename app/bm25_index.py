"""
bm25_index.py — BM25 keyword index over the hadith corpus
==========================================================
Builds a BM25 index from all hadiths in ChromaDB and provides fast
keyword-based retrieval to complement dense vector search.

BM25 excels at exact keyword matches — names, numbers, specific terms —
that semantic embeddings can miss. Combined with dense retrieval via RRF,
it forms the "hybrid search" layer.

Disk persistence
----------------
Pass a `cache_dir` to the constructor (e.g. the same directory as the
ChromaDB persist path).  On the first run the index is built from ChromaDB
and saved to `<cache_dir>/bm25_cache.pkl`.  On every subsequent startup
the cache is loaded in ~1 second instead of rebuilding (~5-10 s).

Usage:
    from bm25_index import BM25HadithIndex
    idx = BM25HadithIndex(vector_store, cache_dir="data/hadith_vectors")
    results = idx.search("বাড়িতে সালাত আদায়", top_k=20)
    # returns list of {"hadith_id", "book", "text", "metadata", "bm25_score"}
"""

import re
import pickle
import os
from pathlib import Path
from typing import List, Dict, Optional

from rank_bm25 import BM25Okapi

_BANGLA_RE  = re.compile(r"[\u0980-\u09FF]+")
_ARABIC_RE  = re.compile(r"[\u0600-\u06FF]+")
_PUNCT_RE   = re.compile(r"[।,;:!?\"'()\[\]{}<>।॥]")

# Cache filename inside cache_dir
_CACHE_FILE = "bm25_cache.pkl"


def _tokenize(text: str) -> List[str]:
    """
    Simple whitespace + punctuation tokenizer that works for Bangla, English,
    and mixed text.  No stemming — BM25 handles frequency weighting instead.
    """
    text = _ARABIC_RE.sub(" ", text)       # drop Arabic script (noisy in hadith)
    text = _PUNCT_RE.sub(" ", text)
    tokens = text.lower().split()
    # Keep tokens that are at least 2 chars and not pure numbers
    return [t for t in tokens if len(t) >= 2 and not t.isdigit()]


class BM25HadithIndex:
    """
    BM25 index over the hadith corpus with optional disk persistence.

    On first build the index is saved to `<cache_dir>/bm25_cache.pkl`.
    On subsequent startups the cache is loaded from disk (~1s) instead of
    rebuilding from ChromaDB (~5-10s).

    Args:
        vector_store: ChromaDB VectorStore instance (used to build the index).
        cache_dir:    Directory to store/load the BM25 cache file.
                      If None, the index is rebuilt every startup (old behaviour).
    """

    def __init__(self, vector_store, cache_dir: Optional[str] = None):
        self._vector_store = vector_store
        self._cache_path   = Path(cache_dir) / _CACHE_FILE if cache_dir else None
        self._bm25:   Optional[BM25Okapi] = None
        self._docs:   List[str]  = []   # raw document texts
        self._metas:  List[dict] = []   # metadata dicts
        self._ids:    List[str]  = []   # ChromaDB IDs
        self._built   = False

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _save_cache(self) -> None:
        """Pickle the index to disk."""
        if self._cache_path is None:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "bm25":  self._bm25,
                "docs":  self._docs,
                "metas": self._metas,
                "ids":   self._ids,
            }
            tmp = self._cache_path.with_suffix(".tmp")
            with open(tmp, "wb") as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
            tmp.replace(self._cache_path)   # atomic rename
            print(f"[BM25] Cache saved → {self._cache_path}", flush=True)
        except Exception as e:
            print(f"[BM25] Warning: could not save cache: {e}", flush=True)

    def _load_cache(self) -> bool:
        """
        Try to load the index from disk.
        Returns True if successful, False if the cache doesn't exist or is stale.
        """
        if self._cache_path is None or not self._cache_path.exists():
            return False
        try:
            print(f"[BM25] Loading cache from {self._cache_path} …", flush=True)
            with open(self._cache_path, "rb") as f:
                payload = pickle.load(f)
            self._bm25  = payload["bm25"]
            self._docs  = payload["docs"]
            self._metas = payload["metas"]
            self._ids   = payload["ids"]
            self._built = True
            print(f"[BM25] Cache loaded — {len(self._docs):,} hadiths, ready.", flush=True)
            return True
        except Exception as e:
            print(f"[BM25] Warning: cache load failed ({e}), rebuilding …", flush=True)
            return False

    # ── Index building ────────────────────────────────────────────────────────

    def _build(self) -> None:
        """Load all hadiths from ChromaDB, build BM25 index, then save to disk."""
        # Try loading from cache first
        if self._load_cache():
            return

        print("[BM25] Building index from ChromaDB …", flush=True)

        # ChromaDB has a 5461-item limit per .get() call — batch it
        BATCH = 5000
        all_docs, all_metas, all_ids = [], [], []
        offset = 0
        total  = self._vector_store.get_collection_count()

        while offset < total:
            batch = self._vector_store.collection.get(
                limit=BATCH, offset=offset,
                include=["documents", "metadatas"]
            )
            all_docs.extend(batch["documents"])
            all_metas.extend(batch["metadatas"])
            all_ids.extend(batch["ids"])
            offset += BATCH

        self._docs  = all_docs
        self._metas = all_metas
        self._ids   = all_ids

        print(f"[BM25] Tokenizing {len(all_docs):,} hadiths …", flush=True)
        tokenized  = [_tokenize(doc) for doc in all_docs]
        self._bm25 = BM25Okapi(tokenized)
        self._built = True
        print("[BM25] Index ready.", flush=True)

        # Persist so the next startup loads from cache
        self._save_cache()

    def _ensure_built(self) -> None:
        if not self._built:
            self._build()

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        BM25 keyword search.

        Args:
            query:  The search query (raw or reframed)
            top_k:  Number of results to return

        Returns:
            List of dicts with hadith_id, book, text, metadata, bm25_score
        """
        self._ensure_built()

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # Get top_k indices by score
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            meta = self._metas[idx]
            results.append({
                "hadith_id":  meta.get("hadith_id", "?"),
                "book":       meta.get("book", "Unknown"),
                "narrator":   meta.get("narrator", ""),
                "grade":      meta.get("grade", ""),
                "text":       self._docs[idx],
                "word_count": meta.get("word_count", 0),
                "filename":   meta.get("filename", ""),
                "bm25_score": score,
                "_chroma_id": self._ids[idx],
            })

        return results

    def search_multi(self, queries: List[str], top_k: int = 20) -> List[Dict]:
        """
        BM25 search with multiple query variants — unions results,
        keeps best BM25 score per hadith.
        """
        self._ensure_built()
        seen: Dict[str, Dict] = {}

        for query in queries:
            for r in self.search(query, top_k=top_k):
                key = f"{r['book']}_{r['hadith_id']}"
                if key not in seen or r["bm25_score"] > seen[key]["bm25_score"]:
                    seen[key] = r

        return sorted(seen.values(), key=lambda x: x["bm25_score"], reverse=True)[:top_k]
