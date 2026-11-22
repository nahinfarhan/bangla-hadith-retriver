"""
app/ui/data.py — Browse index and page fetch for Hadith Books view.

All operations are READ-ONLY. No writes to the ChromaDB collection.
Results are cached at the @st.cache_resource level (once per engine + book).
"""
import streamlit as st


# ttl: a browse index fetched while the DB is being (re)built is partial;
# let it expire instead of freezing the partial result until restart.
@st.cache_data(show_spinner=False, ttl=300)
def browse_index(_engine, book: str) -> list:
    """
    Return a sorted list of (hadith_number: int, vector_id: str) for a book.

    Uses @st.cache_data with underscore-prefixed _engine so Streamlit skips
    hashing the engine object (same pattern as _cached_hadith_search).
    Never calls add/update/upsert/delete.

    Returns [] if the book has no entries.
    """
    engine = _engine
    try:
        engine._init_components()  # ensure components are ready
        res = engine._vector_store.collection.get(
            where={"book": book},
            include=["metadatas"],
        )
        if not res or not res.get("metadatas"):
            return []

        pairs = []
        for i, meta in enumerate(res["metadatas"]):
            try:
                hnum = int(meta.get("hadith_number") or meta.get("hadith_id") or 0)
            except (TypeError, ValueError):
                hnum = 0
            vid = res["ids"][i] if res.get("ids") else f"{book}_{hnum}"
            pairs.append((hnum, vid))

        # Sort ascending by hadith number
        pairs.sort(key=lambda x: x[0])
        return pairs
    except Exception:
        return []


def fetch_page(engine, ids: list) -> list:
    """
    Fetch documents + metadatas for a list of vector IDs.

    Returns a list of dicts with keys: hadith_id, book, narrator, grade, text.
    Never writes to the collection.
    """
    if not ids:
        return []
    try:
        engine._init_components()
        res = engine._vector_store.collection.get(
            ids=ids,
            include=["documents", "metadatas"],
        )
        if not res or not res.get("documents"):
            return []

        out = []
        for doc, meta in zip(res["documents"], res["metadatas"]):
            out.append({
                "hadith_id": meta.get("hadith_id", "?"),
                "book":      meta.get("book", "Unknown"),
                "narrator":  meta.get("narrator", ""),
                "grade":     meta.get("grade", "") or "",
                "text":      doc or "",
            })
        return out
    except Exception:
        return []
