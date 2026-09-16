"""
hybrid_search.py — BM25 + Dense Hybrid Search with Cross-Encoder Re-ranking
=============================================================================
Full pipeline:

  1. Query Reframing  → 3 optimised query variants (via Gemini)
  2. Dense Search     → top-N per variant via fine-tuned e5 embeddings
  3. BM25 Search      → top-N per variant via keyword index
  4. RRF Fusion       → merge dense + BM25 lists using Reciprocal Rank Fusion
  5. Cross-Encoder    → re-score fused candidates and return final top-k

RRF formula:  score(d) = Σ 1 / (k + rank(d))   where k=60 (standard)

Usage:
    from hybrid_search import HybridHadithSearch
    hs = HybridHadithSearch()
    results = hs.search("নামাজ কখন বাসায় পড়া যায়?", top_k=5)
"""

from typing import List, Dict, Optional
from pathlib import Path
import sys

# Make sure app/ is on path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from vector_store  import VectorStore
from embed         import EmbeddingModel
from search        import SearchEngine
from bm25_index    import BM25HadithIndex
from reranker      import CrossEncoderReranker
from query_reframer import reframe_query


# ── RRF fusion ────────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict]],
    id_key: str  = "_doc_key",
    k: int       = 60,
) -> List[Dict]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.

    Args:
        ranked_lists: Each list is already sorted by relevance (best first).
        id_key:       Key used to identify the same document across lists.
        k:            RRF constant (60 is the standard from the original paper).

    Returns:
        Merged list sorted by combined RRF score (descending).
        Each item gets a "_rrf_score" field.
    """
    rrf_scores: Dict[str, float]  = {}
    doc_store:  Dict[str, Dict]   = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list, start=1):
            doc_id = doc.get(id_key, "")
            if not doc_id:
                continue
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            # Keep the doc with best original score (for display)
            if doc_id not in doc_store:
                doc_store[doc_id] = doc

    merged = []
    for doc_id, rrf_score in sorted(rrf_scores.items(), key=lambda x: -x[1]):
        entry = dict(doc_store[doc_id])
        entry["_rrf_score"] = round(rrf_score, 6)
        merged.append(entry)

    return merged


# ── Main hybrid search class ──────────────────────────────────────────────────

class HybridHadithSearch:
    """
    Full hybrid search: Dense + BM25 + RRF + Cross-Encoder re-ranking.

    Components are initialised lazily:
    - VectorStore + EmbeddingModel: loaded on first search
    - BM25 index: built on first search (~5-10s for 20k docs)
    - CrossEncoder: loaded on first search (~5s + 568MB download on first run)

    Args:
        hadith_db_path:     Path to ChromaDB hadith vectors
        use_reranker:       Whether to apply cross-encoder re-ranking (default True)
        dense_candidate_k:  How many dense candidates to fetch per query variant
        bm25_candidate_k:   How many BM25 candidates to fetch per query variant
    """

    def __init__(
        self,
        hadith_db_path: str      = "data/hadith_vectors",
        use_reranker:   bool     = True,
        dense_candidate_k: int   = 30,
        bm25_candidate_k:  int   = 30,
    ):
        # Resolve path
        if not Path(hadith_db_path).is_absolute():
            project_root   = Path(__file__).parent.parent
            hadith_db_path = str(project_root / hadith_db_path)

        self._db_path          = hadith_db_path
        self._use_reranker     = use_reranker
        self._dense_k          = dense_candidate_k
        self._bm25_k           = bm25_candidate_k

        # Lazy-initialised components
        self._vector_store: Optional[VectorStore]       = None
        self._embed_model:  Optional[EmbeddingModel]    = None
        self._search_engine: Optional[SearchEngine]     = None
        self._bm25_index:   Optional[BM25HadithIndex]   = None
        self._reranker:     Optional[CrossEncoderReranker] = None

    def _init_components(self):
        if self._vector_store is None:
            self._vector_store  = VectorStore(persist_directory=self._db_path)
            self._embed_model   = EmbeddingModel()
            self._search_engine = SearchEngine(self._vector_store, self._embed_model)
            self._bm25_index    = BM25HadithIndex(self._vector_store)
        if self._use_reranker and self._reranker is None:
            try:
                self._reranker = CrossEncoderReranker()
            except Exception as e:
                print(f"[HybridSearch] Reranker init failed: {e} — running without re-ranking", flush=True)
                self._use_reranker = False

    # ── Dense retrieval ───────────────────────────────────────────────────────

    def _dense_search(self, queries: List[str], top_k: int) -> List[Dict]:
        """Dense vector search over multiple query variants, merged by best score."""
        seen: Dict[str, Dict] = {}
        for q in queries:
            raw = self._search_engine.search_documents(q, top_k=top_k)
            for r in raw:
                if "error" in r:
                    continue
                meta   = r.get("metadata", {})
                doc_key = f"{meta.get('book','')}_{meta.get('hadith_id','')}"
                item = {
                    "_doc_key":   doc_key,
                    "hadith_id":  meta.get("hadith_id", "?"),
                    "book":       meta.get("book", "Unknown"),
                    "narrator":   meta.get("narrator", ""),
                    "grade":      meta.get("grade", ""),
                    "text":       r["text"],
                    "similarity": r["similarity_percentage"],
                    "word_count": meta.get("word_count", 0),
                    "filename":   meta.get("filename", ""),
                    "_source":    "dense",
                }
                if doc_key not in seen or item["similarity"] > seen[doc_key]["similarity"]:
                    seen[doc_key] = item

        return sorted(seen.values(), key=lambda x: x["similarity"], reverse=True)

    # ── BM25 retrieval ────────────────────────────────────────────────────────

    def _bm25_search(self, queries: List[str], top_k: int) -> List[Dict]:
        """BM25 keyword search over multiple query variants."""
        raw = self._bm25_index.search_multi(queries, top_k=top_k)
        results = []
        for r in raw:
            doc_key = f"{r['book']}_{r['hadith_id']}"
            results.append({
                "_doc_key":   doc_key,
                "hadith_id":  r["hadith_id"],
                "book":       r["book"],
                "narrator":   r.get("narrator", ""),
                "grade":      r.get("grade", ""),
                "text":       r["text"],
                "similarity": 0.0,        # BM25 score not percentage-based
                "bm25_score": r["bm25_score"],
                "word_count": r.get("word_count", 0),
                "filename":   r.get("filename", ""),
                "_source":    "bm25",
            })
        return results

    # ── Public API ────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k:           int  = 5,
        use_reframing:   bool = True,
        extra_keys_raw:  str  = "",
    ) -> List[Dict]:
        """
        Full hybrid search pipeline.

        Args:
            query:          User's natural language question
            top_k:          Number of final results to return
            use_reframing:  Use Gemini query reframing (default True)
            extra_keys_raw: Extra Gemini API keys from UI

        Returns:
            List of top-k hadith dicts, each with:
              - hadith_id, book, narrator, grade, text, word_count
              - similarity    (dense score %)
              - bm25_score    (BM25 raw score, if sourced from BM25)
              - _rrf_score    (RRF fusion score)
              - rerank_score  (cross-encoder score, if reranker enabled)
              - _retrieval    ("dense+bm25+rerank" etc.)
        """
        self._init_components()

        # Step 1: Query reframing → multiple variants
        if use_reframing:
            query_variants = reframe_query(query, extra_keys_raw=extra_keys_raw)
        else:
            query_variants = [query]

        # Step 2: Dense retrieval — fetch more candidates than top_k for re-ranking
        fetch_k = max(top_k * 4, self._dense_k)   # scales with user's top_k
        dense_results = self._dense_search(query_variants, top_k=fetch_k)

        # Step 3: BM25 retrieval
        bm25_results  = self._bm25_search(query_variants, top_k=fetch_k)

        # Step 4: RRF fusion
        fused = reciprocal_rank_fusion(
            [dense_results, bm25_results],
            id_key="_doc_key",
            k=60,
        )

        # Take top candidates for re-ranking — scales with user's top_k
        candidates = fused[: max(top_k * 4, 30)]

        # Step 5: Cross-encoder re-ranking (optional — skipped if model not available)
        if self._use_reranker and self._reranker and candidates:
            try:
                final = self._reranker.rerank(query, candidates, top_k=top_k)
                retrieval_tag = "dense+bm25+rerank"
            except Exception as e:
                print(f"[HybridSearch] Reranker failed ({e}), using RRF order", flush=True)
                final = candidates[:top_k]
                retrieval_tag = "dense+bm25+rrf"
        else:
            final = candidates[:top_k]
            retrieval_tag = "dense+bm25+rrf"

        # Clean up internal keys, add retrieval tag
        clean = []
        for r in final:
            c = {k: v for k, v in r.items() if not k.startswith("_")}
            c["_retrieval"] = retrieval_tag
            # Normalise _rrf_score to percentage for display (multiply by 1000 for readability)
            c["rrf_score"] = round(r.get("_rrf_score", 0) * 1000, 3)
            clean.append(c)

        return clean

    def search_hadiths(self, query: str, top_k: int = 5,
                       use_reframing: bool = True,
                       extra_keys_raw: str = "") -> List[Dict]:
        """Alias for search() — keeps compatibility with main.py."""
        return self.search(query, top_k=top_k,
                           use_reframing=use_reframing,
                           extra_keys_raw=extra_keys_raw)

    def search_dense_only(
        self,
        query: str,
        top_k: int = 5,
        use_reframing: bool = False,
        extra_keys_raw: str = "",
    ) -> List[Dict]:
        """
        Dense-only retrieval — no BM25, no RRF, no cross-encoder re-ranking.
        Useful as an ablation baseline to isolate the contribution of BM25
        and re-ranking components.

        Args:
            query:          User's natural language question
            top_k:          Number of final results to return
            use_reframing:  Apply Gemini query reframing before dense search
            extra_keys_raw: Extra Gemini API keys from UI

        Returns:
            List of top-k hadith dicts sorted by dense similarity score.
        """
        self._init_components()

        # Optional query reframing
        if use_reframing:
            query_variants = reframe_query(query, extra_keys_raw=extra_keys_raw)
        else:
            query_variants = [query]

        # Dense retrieval only — fetch top_k * 2 to have a bit of headroom
        fetch_k = max(top_k * 2, 30)
        dense_results = self._dense_search(query_variants, top_k=fetch_k)

        # Trim to top_k and clean internal keys
        clean = []
        for r in dense_results[:top_k]:
            c = {k: v for k, v in r.items() if not k.startswith("_")}
            c["_retrieval"] = "dense_only"
            clean.append(c)

        return clean

    def get_database_stats(self) -> Dict:
        """Return DB stats (compatible with HadithSearchEngine interface)."""
        self._init_components()
        total = self._vector_store.get_collection_count()
        books: set = set()
        total_words = 0
        sample_size = 0
        try:
            sample = self._vector_store.collection.get(limit=200)
            if sample and sample["metadatas"]:
                for meta in sample["metadatas"]:
                    books.add(meta.get("book", "Unknown"))
                    total_words += meta.get("word_count", 0)
                sample_size = len(sample["metadatas"])
        except Exception:
            pass
        avg_words = int(total_words / sample_size) if sample_size else 0
        return {
            "total_hadiths":        total,
            "books":                sorted(books),
            "avg_words_per_hadith": avg_words,
        }

    def get_hadith_by_number(self, hadith_number: int,
                              book: str = "Sahih_Bukhari"):
        """Direct lookup by hadith number (delegates to VectorStore)."""
        self._init_components()
        vec_id = f"{book}_{hadith_number}"
        try:
            res = self._vector_store.collection.get(ids=[vec_id])
            if res and res["documents"]:
                return {
                    "hadith_id": hadith_number,
                    "book":      book,
                    "text":      res["documents"][0],
                    "metadata":  res["metadatas"][0],
                }
        except Exception:
            pass
        return None
