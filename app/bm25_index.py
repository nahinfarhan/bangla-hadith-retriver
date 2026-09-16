"""
bm25_index.py — BM25 keyword index over the hadith corpus
==========================================================
Builds an in-memory BM25 index from all hadiths in ChromaDB and provides
fast keyword-based retrieval to complement dense vector search.

BM25 excels at exact keyword matches — names, numbers, specific terms —
that semantic embeddings can miss. Combined with dense retrieval via RRF,
it forms the "hybrid search" layer.

Usage:
    from bm25_index import BM25HadithIndex
    idx = BM25HadithIndex(vector_store)
    results = idx.search("বাড়িতে সালাত আদায়", top_k=20)
    # returns list of {"hadith_id", "book", "text", "metadata", "bm25_score"}
"""

import re
from typing import List, Dict, Optional

from rank_bm25 import BM25Okapi

_BANGLA_RE  = re.compile(r"[\u0980-\u09FF]+")
_ARABIC_RE  = re.compile(r"[\u0600-\u06FF]+")
_PUNCT_RE   = re.compile(r"[।,;:!?\"'()\[\]{}<>।॥]")


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
    In-memory BM25 index over the hadith corpus.

    Loads all documents from ChromaDB once and builds the BM25 index.
    This is done lazily on first search call and cached for the session.
    Building takes ~5-10 seconds for 20k hadiths.
    """

    def __init__(self, vector_store):
        self._vector_store = vector_store
        self._bm25:   Optional[BM25Okapi] = None
        self._docs:   List[str]  = []   # raw document texts
        self._metas:  List[dict] = []   # metadata dicts
        self._ids:    List[str]  = []   # ChromaDB IDs
        self._built   = False

    # ── Index building ────────────────────────────────────────────────────────

    def _build(self):
        """Load all hadiths from ChromaDB and build BM25 index."""
        print("[BM25] Loading corpus from ChromaDB...", flush=True)

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

        print(f"[BM25] Tokenizing {len(all_docs):,} hadiths...", flush=True)
        tokenized = [_tokenize(doc) for doc in all_docs]
        self._bm25 = BM25Okapi(tokenized)
        self._built = True
        print("[BM25] Index ready.", flush=True)

    def _ensure_built(self):
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
