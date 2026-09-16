"""
Hadith Search Module
Wraps the pre-built hadith vector database (built from JSON sources).

Query rewriting is applied before embedding to strip question framing
("হাদিস কি আছে", "সম্পর্কে বলুন", etc.) and extract the core topic.
This dramatically improves retrieval quality for natural-language questions.
"""

import os
import re
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Optional

# Make sure sibling modules are importable when running from different cwd
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from vector_store import VectorStore
from embed import EmbeddingModel
from search import SearchEngine
from query_reframer import reframe_query

# ── Bangla question-framing patterns to strip ────────────────────────────────
# These phrases don't add semantic meaning for retrieval but confuse the
# embedding model into matching on question structure instead of topic.
_BANGLA_STRIP = re.compile(
    r"(হাদিস\s*(কি|কী)\s*আছে[?।]?|"
    r"সম্পর্কে\s*(হাদিস\s*)?(কি|কী)\s*(আছে|বলুন|জানান)[?।]?|"
    r"বিষয়ে\s*(হাদিস\s*)?(কি|কী)\s*(আছে|বলুন|জানান)[?।]?|"
    r"বিষয়ের\s*হাদিস\s*(কি|কী)\s*আছে[?।]?|"
    r"সম্পর্কে\s*বলুন[?।]?|"
    r"সম্পর্কিত\s*হাদিস[?।]?|"
    r"নিয়ে\s*(হাদিস\s*)?(কি|কী)\s*(আছে|বলুন)[?।]?|"
    r"কিভাবে\s*(করতে\s*হয়|করা\s*যায়)[?।]?|"
    r"কখন\s*(করতে\s*হয়|করা\s*যায়|পড়া\s*যায়|আদায়\s*করা\s*যায়|রাখতে\s*হয়|রাখা\s*যায়)[?।]?|"
    r"কখন\s*(কি|কী)\s*(করতে|পড়তে|আদায়)\s*(হয়|যায়)[?।]?|"
    r"কার\s*কার\s*উপরে[?।]?|"
    r"কি\s*\d+\s*[উও]য়াক্ত[?।]?|"
    r"\s*হাদিস\s*(কি|কী)[?।]?\s*$"
    r")",
    re.UNICODE
)

_BANGLA_RE = re.compile(r"[\u0980-\u09FF]")

# Common synonym expansions — Bangla/Persian words → Arabic terms used in hadiths
_SYNONYMS = {
    "নামাজ":    "নামাজ সালাত",
    "রোজা":     "রোজা সাওম রমযান",
    "কোরবানি":  "কোরবানি উযহিয়্যা কুরবান",
    "কুরবানি":  "কুরবানি উযহিয়্যা কোরবানি",
    "হজ":       "হজ হাজ্জ",
    "যাকাত":    "যাকাত যকাত",
    "জিহাদ":    "জিহাদ যুদ্ধ",
    "দোয়া":     "দোয়া দু'আ",
    "তওবা":     "তওবা তাওবাহ",
    "জানাজা":   "জানাজা জানাযা",
    "বাসায়":    "বাড়িতে ঘরে",
    "ঘরে":      "বাড়িতে ঘরে",
    "মসজিদে":   "মসজিদ মসজিদে",
    "ওযু":      "ওযু উযু অযু",
    "অজু":      "ওযু উযু অজু",
    "ইফতার":    "ইফতার ইফতারি",
    "সেহরি":    "সেহরি সাহরি",
}


def _expand_synonyms(query: str) -> str:
    """Replace common Bangla words with their Arabic hadith equivalents."""
    seen = set()
    for word, expanded in _SYNONYMS.items():
        if word in query:
            # Avoid duplicating words already present in the expanded form
            new_terms = [t for t in expanded.split() if t not in query and t not in seen]
            seen.update(new_terms)
            if new_terms:
                query = query.replace(word, word + " " + " ".join(new_terms), 1)
    return query


def _rewrite_query(question: str) -> str:
    """
    Strip question framing and expand synonyms before embedding.

    Examples:
      "নামাজ ফরজ হওয়ার বিষয়ের হাদিস কি আছে?" → "নামাজ সালাত ফরজ হওয়ার"
      "কোরবানি কিভাবে করতে হয়?"              → "কোরবানি উযহিয়্যা কুরবান"
      "রোজা সম্পর্কে হাদিস কি আছে?"           → "রোজা সাওম রমযান"
      "prayer in Islam"                        → "prayer in Islam"  (unchanged)
    """
    q = question.strip().rstrip("?।!")

    # Only rewrite Bangla questions
    if not _BANGLA_RE.search(q):
        return q

    # Strip trailing question framing
    cleaned = _BANGLA_STRIP.sub("", q).strip()

    # Strip leading filler words
    filler = re.compile(
        r"^(আমাকে|আমি|আপনি|বলুন|জানান|দয়া\s*করে|please)\s*",
        re.UNICODE | re.IGNORECASE
    )
    cleaned = filler.sub("", cleaned).strip()

    # Strip trailing question words that don't carry semantic meaning for retrieval
    trailing_q = re.compile(
        r"\s*(কখন|কেন|কোথায়|কিভাবে|কীভাবে|কি|কী)[?।]?\s*$",
        re.UNICODE
    )
    cleaned = trailing_q.sub("", cleaned).strip()

    # Strip "কখন X পড়া/করা/আদায় যায়/হয়" style predicates — keep only the topic
    # BUT preserve location/condition words (বাসায়, বাড়িতে, মসজিদে, ঝড়ে etc.)
    predicate = re.compile(
        r"\s*কখন\s+(\S+)\s+(পড়া|করা|আদায়|রাখা)\s+(যায়|হয়)[?।]?\s*$",
        re.UNICODE
    )
    # Replace "কখন X পড়া যায়" with just "X" (preserve location word)
    def _keep_location(m):
        location = m.group(1)
        # Only drop if it's a generic verb/word, keep if it's a place/condition
        generic = {'করা', 'পড়া', 'আদায়', 'রাখা', 'দেওয়া', 'নেওয়া'}
        return f" {location}" if location not in generic else ""
    cleaned = predicate.sub(_keep_location, cleaned).strip()

    # If we stripped everything, fall back to original
    if not cleaned:
        return q

    # Expand synonyms so hadiths using Arabic terms are also retrieved
    expanded = _expand_synonyms(cleaned)

    return expanded


class HadithSearchEngine:
    """Semantic search over the pre-built hadith vector database."""

    def __init__(self, hadith_db_path: str = "data/hadith_vectors"):
        # Resolve relative paths against the project root (two levels up from
        # this file: app/ → vectorqa-app/) so the engine works regardless of
        # which directory Streamlit was launched from.
        if not Path(hadith_db_path).is_absolute():
            project_root = Path(__file__).parent.parent
            hadith_db_path = str(project_root / hadith_db_path)
        self.vector_store  = VectorStore(persist_directory=hadith_db_path)
        self.embed_model   = EmbeddingModel()
        self.search_engine = SearchEngine(self.vector_store, self.embed_model)

    # ── Public API ────────────────────────────────────────────────────────────

    def search_hadiths(self, query: str, top_k: int = 5,
                       use_reframing: bool = True,
                       extra_keys_raw: str = "") -> List[Dict]:
        """Return top_k hadiths semantically matching *query*.

        When use_reframing=True, the query is rewritten into 3 patterns by
        Gemini (text style, chapter style, keyword style). Each pattern is
        searched independently and results are merged by highest score.
        Falls back to raw query if Gemini is unavailable.
        """
        if use_reframing:
            search_queries = reframe_query(query, extra_keys_raw=extra_keys_raw)
        else:
            search_queries = [query]

        # Search with each query pattern, collect all results
        seen_ids: dict = {}  # hadith_id+book → best result dict

        for sq in search_queries:
            raw = self.search_engine.search_documents(sq, top_k=top_k)
            for r in raw:
                if "error" in r:
                    continue
                meta = r.get("metadata", {})
                key  = f"{meta.get('book','')}_{meta.get('hadith_id','')}"
                item = {
                    "hadith_id":  meta.get("hadith_id", "?"),
                    "book":       meta.get("book", "Unknown"),
                    "narrator":   meta.get("narrator", ""),
                    "grade":      meta.get("grade", ""),
                    "text":       r["text"],
                    "similarity": r["similarity_percentage"],
                    "word_count": meta.get("word_count", 0),
                    "filename":   meta.get("filename", ""),
                }
                # Keep only the highest similarity score for each hadith
                if key not in seen_ids or item["similarity"] > seen_ids[key]["similarity"]:
                    seen_ids[key] = item

        # Sort merged results by similarity descending, return top_k
        results = sorted(seen_ids.values(), key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def get_hadith_by_number(self, hadith_number: int,
                             book: str = "Sahih_Bukhari") -> Optional[Dict]:
        """Retrieve a specific hadith by its numeric ID within a book."""
        # Try exact vector ID first
        vec_id = f"{book}_{hadith_number}"
        try:
            res = self.vector_store.collection.get(ids=[vec_id])
            if res and res["documents"]:
                return {
                    "hadith_id": hadith_number,
                    "book":      book,
                    "text":      res["documents"][0],
                    "metadata":  res["metadatas"][0],
                }
        except Exception:
            pass

        # Fallback: metadata filter
        try:
            res = self.vector_store.collection.get(
                where={"hadith_number": hadith_number}
            )
            if res and res["documents"]:
                return {
                    "hadith_id": hadith_number,
                    "book":      res["metadatas"][0].get("book", book),
                    "text":      res["documents"][0],
                    "metadata":  res["metadatas"][0],
                }
        except Exception:
            pass

        return None

    def get_database_stats(self) -> Dict:
        """Return a summary of the loaded database."""
        total = self.vector_store.get_collection_count()
        books: set = set()
        total_words = 0
        sample_size = 0

        try:
            sample = self.vector_store.collection.get(limit=200)
            if sample and sample["metadatas"]:
                for meta in sample["metadatas"]:
                    books.add(meta.get("book", "Unknown"))
                    total_words += meta.get("word_count", 0)
                sample_size = len(sample["metadatas"])
        except Exception:
            pass

        avg_words = int(total_words / sample_size) if sample_size else 0
        return {
            "total_hadiths":      total,
            "books":              sorted(books),
            "avg_words_per_hadith": avg_words,
        }
