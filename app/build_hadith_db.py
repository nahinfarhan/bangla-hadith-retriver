#!/usr/bin/env python3
"""
Hadith Vector Database Builder — JSON-based
Sources: data/hadiths.json (Bukhari), data/muslim_hadiths.json, data/tirmidhi_hadiths.json
Each hadith record becomes one vector entry in ChromaDB.

Run:
    python3 app/build_hadith_db.py              # build (skips if already built)
    python3 app/build_hadith_db.py --force      # rebuild from scratch
    python3 app/build_hadith_db.py --verify     # just check the DB stats
"""

import os
import sys
import json
import argparse
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Tuple, Any

# ── Path setup ──────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent.absolute()
ROOT_DIR = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))

from embed import EmbeddingModel
from vector_store import VectorStore

# ── Config ───────────────────────────────────────────────────────────────────
VECTOR_DB_PATH = str(ROOT_DIR / "data" / "hadith_vectors")
SENTINEL_FILE  = str(ROOT_DIR / "data" / "hadith_vectors" / ".build_complete")

JSON_SOURCES = [
    (str(ROOT_DIR / "data" / "hadiths.json"),        "Sahih_Bukhari"),
    (str(ROOT_DIR / "data" / "muslim_hadiths.json"), "Sahih_Muslim"),
    (str(ROOT_DIR / "data" / "tirmidhi_hadiths.json"), "Jami_at_Tirmidhi"),
]

ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+"
)

# ── Text helpers ─────────────────────────────────────────────────────────────

def clean_text(raw: str) -> str:
    """Remove Arabic script, normalise Unicode, strip junk."""
    text = unicodedata.normalize("NFC", raw)
    text = ARABIC_RE.sub("", text)                           # drop Arabic
    text = re.sub(r"\(cid:\d+\)", "", text)                  # PDF artefacts
    text = re.sub(r"[\ufeff\u200b-\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_embed_text(entry: dict) -> str:
    """
    Build the text that gets EMBEDDED (used for the vector).
    Only the hadith content itself — Bangla translation + English translation.
    Narrator name is intentionally excluded: it adds noise to semantic search
    (two hadiths sharing the same narrator would score higher together even
    when the content is unrelated to the query).
    """
    parts = []
    if entry.get("translation"):
        parts.append(entry["translation"])
    if entry.get("translation_en"):
        parts.append(entry["translation_en"])
    combined = "\n".join(parts)
    return clean_text(combined)


def build_display_text(entry: dict) -> str:
    """
    Build the full text that gets STORED in ChromaDB and shown in the UI.
    Includes the narrator prefix so the UI can display it, but this text
    is NOT used for embedding.
    """
    parts = []
    if entry.get("narrator"):
        parts.append(f"বর্ণনাকারী: {entry['narrator']}")
    if entry.get("translation"):
        parts.append(entry["translation"])
    if entry.get("translation_en"):
        parts.append(entry["translation_en"])
    combined = "\n".join(parts)
    return clean_text(combined)


def make_id(book_name: str, entry_id: str) -> str:
    """Stable, unique vector ID."""
    # sanitise so ChromaDB doesn't choke on special chars
    safe_book = re.sub(r"[^A-Za-z0-9_-]", "_", book_name)
    safe_id   = re.sub(r"[^A-Za-z0-9_-]", "_", str(entry_id))
    return f"{safe_book}_{safe_id}"


# ── Loader ────────────────────────────────────────────────────────────────────

def load_json_source(filepath: str, default_book: str) -> List[Tuple[str, str, str, dict]]:
    """
    Returns list of (vector_id, embed_text, display_text, metadata) tuples.

    embed_text   — hadith content only (no narrator), used to build the vector
    display_text — full text with narrator prefix, stored in ChromaDB and shown in UI

    Skips entries where the embed text is too short to be meaningful.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for entry in data:
        entry_id     = str(entry.get("id", ""))
        book_name    = entry.get("book_name", default_book)
        embed_text   = build_embed_text(entry)
        display_text = build_display_text(entry)

        if len(embed_text.split()) < 5:    # skip near-empty entries
            continue

        vec_id = make_id(book_name, entry_id)

        metadata = {
            "hadith_id":     entry_id,
            "book":          book_name,
            "narrator":      entry.get("narrator", ""),
            "chapter":       str(entry.get("chapter", "")),
            "grade":         entry.get("grade", {}).get("title", ""),
            "word_count":    len(display_text.split()),
            "filename":      Path(filepath).name,
            "hadith_number": _try_int(entry_id),
        }
        records.append((vec_id, embed_text, display_text, metadata))

    return records


def _try_int(val: str) -> int:
    """Return int if possible, else 0."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


# ── Builder ───────────────────────────────────────────────────────────────────

class HadithDatabaseBuilder:
    def __init__(self, vector_db_path: str = VECTOR_DB_PATH):
        self.vector_db_path = vector_db_path
        self.vector_store   = None   # lazy-init
        self.embed_model    = None

    def _init_components(self):
        print("📦  Loading embedding model …")
        self.embed_model  = EmbeddingModel()
        self.vector_store = VectorStore(persist_directory=self.vector_db_path)

    def is_already_built(self) -> bool:
        return os.path.exists(SENTINEL_FILE)

    def build(self, force: bool = False):
        if not force and self.is_already_built():
            count = VectorStore(persist_directory=self.vector_db_path).get_collection_count()
            print(f"✅  Database already built ({count} hadiths). Use --force to rebuild.")
            return

        if force:
            print("🗑️  Clearing old database …")
            import shutil
            if os.path.exists(self.vector_db_path):
                # Volume-mounted dirs can't be rmtree'd; clear contents instead
                for item in os.listdir(self.vector_db_path):
                    item_path = os.path.join(self.vector_db_path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            os.makedirs(self.vector_db_path, exist_ok=True)

        self._init_components()

        total_loaded = 0
        # Batch size for embedding. Long hadiths use more memory per item,
        # so keep this at 32 to avoid OOM on CPU-only Docker containers.
        # Each hadith is embedded in full (no text truncation).
        BATCH = 32

        for filepath, default_book in JSON_SOURCES:
            if not os.path.exists(filepath):
                print(f"⚠️  File not found, skipping: {filepath}")
                continue

            print(f"\n📖  Loading {Path(filepath).name} …")
            records = load_json_source(filepath, default_book)
            print(f"    {len(records)} entries found")

            # Process in batches
            for start in range(0, len(records), BATCH):
                batch      = records[start:start + BATCH]
                ids        = [r[0] for r in batch]
                embed_txts = [r[1] for r in batch]   # content-only, used for vectors
                disp_txts  = [r[2] for r in batch]   # full text with narrator, stored + shown
                metadatas  = [r[3] for r in batch]

                embeddings = self.embed_model.embed_texts(embed_txts)

                # Store display_text in ChromaDB so the UI shows narrator + content,
                # but the vector was built from embed_text (content only).
                self.vector_store.add_chunks(
                    chunks=disp_txts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids,
                )
                total_loaded += len(batch)
                print(f"    ✔  {total_loaded} total indexed …", end="\r")

            print()  # newline after \r

        # Write sentinel so we never re-build unless forced
        with open(SENTINEL_FILE, "w") as f:
            f.write(f"{total_loaded}\n")

        print(f"\n✅  Done. {total_loaded} hadiths indexed → {self.vector_db_path}")

    def verify(self):
        vs    = VectorStore(persist_directory=self.vector_db_path)
        count = vs.get_collection_count()
        print(f"\n📊  Hadith vectors in DB : {count}")
        if count == 0:
            print("⚠️  Database is empty — run without --verify to build it first.")
            return
        sample = vs.collection.get(limit=3)
        print("Sample records:")
        for doc, meta in zip(sample["documents"], sample["metadatas"]):
            print(f"  [{meta['book']} #{meta['hadith_id']}]  {doc[:80]} …")


# ── CLI entry-point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build Hadith vector database from JSON files")
    parser.add_argument("--force",  action="store_true", help="Rebuild even if DB already exists")
    parser.add_argument("--verify", action="store_true", help="Show DB stats and exit")
    args = parser.parse_args()

    builder = HadithDatabaseBuilder()

    if args.verify:
        builder.verify()
    else:
        builder.build(force=args.force)


if __name__ == "__main__":
    main()
