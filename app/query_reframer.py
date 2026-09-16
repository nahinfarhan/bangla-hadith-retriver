"""
query_reframer.py — LLM-based Query Reframing for Hadith Retrieval
===================================================================
Uses Gemini (via gemini_client.py) to rewrite a user's natural-language
question into 3 different retrieval query patterns that closely match
hadith text and chapter styles.

Pattern 1: Direct hadith text style   — "যে ব্যক্তি ঝড়ের রাতে বাড়িতে সালাত আদায় করে..."
Pattern 2: Chapter/Babu name style    — "বাড়িতে সালাত আদায়ের বিধান পরিচ্ছেদ"
Pattern 3: Keyword/summary style      — "সালাত বাড়ি ঝড় বৃষ্টি ওজর রুখসত"

All 3 are used for vector search; results are merged by best score.
Gracefully falls back to [original_query] when Gemini is unavailable.
"""

import re
import json
from typing import List

from gemini_client import call_gemini


_BANGLA_RE = re.compile(r"[\u0980-\u09FF]")


# ── Prompt ────────────────────────────────────────────────────────────────────

def _build_prompt(user_query: str) -> str:
    return f"""তুমি একটি ইসলামিক 'Semantic Search Engine'-এর 'Query Reframing Agent'। তোমার কাজ হলো ব্যবহারকারীর সাধারণ ও কথ্য ভাষার প্রশ্নকে (Raw Query) এমনভাবে পুনরায় লেখা (Reframe) যেন তা সরাসরি হাদিসের মূল টেক্সট বা হাদিস গ্রন্থের অধ্যায়ের (Chapter/Babu) নাম ও বাক্য গঠনের সাথে হুবহু মিলে যায়।

ব্যবহারকারীর ইনপুট: "{user_query}"

কোয়েরি রিফ্রেমিংয়ের কঠোর নিয়মাবলী:
১. পরিভাষা পরিবর্তন (Terminology Shift): সাধারণ শব্দগুলোকে বিশুদ্ধ ইসলামিক ও হাদিসের পরিভাষায় রূপান্তর করবে। (যেমন: নামাজ -> সালাত, রোজা -> সিয়াম, ওজু -> উযু, গুনাহ -> পাপ, বেহেশত -> জান্নাত)।
২. বাক্যের গঠন (Sentence Structure): প্রশ্নবোধক বাক্যকে হাদিসের বর্ণনামূলক (Declarative) বা শর্তমূলক (Conditional) বাক্য গঠনে রূপান্তর করবে।
৩. অর্থের বিশুদ্ধতা: ব্যবহারকারীর মূল উদ্দেশ্য (Intent) কোনোভাবেই পরিবর্তন করা যাবে না।
৪. ৩টি ভিন্ন প্যাটার্নের রিফ্রেমড কোয়েরি তৈরি করবে।

ঠিক এই JSON ফরম্যাটে উত্তর দাও (অন্য কিছু লিখবে না):
{{
  "pattern1": "<হাদিসের সরাসরি টেক্সট স্টাইল>",
  "pattern2": "<হাদিসের অধ্যায় বা পরিচ্ছেদের নাম স্টাইল>",
  "pattern3": "<সারমর্ম বা কি-ওয়ার্ড ভিত্তিক স্টাইল — ৫-১০টি মূল কীওয়ার্ড>"
}}"""


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_patterns(raw: str) -> List[str]:
    """Extract the 3 pattern strings from Gemini's JSON response."""
    try:
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(cleaned)
        p1 = data.get("pattern1", "").strip()
        p2 = data.get("pattern2", "").strip()
        p3 = data.get("pattern3", "").strip()
        if p1 and p2 and p3:
            return [p1, p2, p3]
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: regex extraction if JSON is malformed
    patterns = []
    for key in ("pattern1", "pattern2", "pattern3"):
        m = re.search(rf'"{key}"\s*:\s*"([^"]+)"', raw)
        if m:
            patterns.append(m.group(1).strip())
    return patterns if len(patterns) == 3 else []


# ── Public API ────────────────────────────────────────────────────────────────

def reframe_query(query: str, extra_keys_raw: str = "") -> List[str]:
    """
    Reframe a user query into 3 retrieval-optimised patterns via Gemini.

    Args:
        query:          The user's original question
        extra_keys_raw: Additional Gemini keys from UI (comma/newline separated)

    Returns:
        List of 3 reframed query strings, or [original_query] on any failure.
    """
    query = query.strip()
    if not query:
        return [query]

    try:
        prompt = _build_prompt(query)
        raw, _ = call_gemini(
            prompt,
            extra_keys_raw=extra_keys_raw,
            max_tokens=256,
            temperature=0.2,
        )
        patterns = _parse_patterns(raw)
        if patterns:
            return patterns
    except Exception:
        pass  # any failure → graceful fallback

    return [query]


def reframe_query_with_debug(query: str, extra_keys_raw: str = "") -> dict:
    """Same as reframe_query but returns debug metadata for the UI."""
    original = query.strip()
    patterns = reframe_query(original, extra_keys_raw=extra_keys_raw)
    return {
        "original": original,
        "patterns": patterns,
        "reframed": len(patterns) == 3 and patterns[0] != original,
    }
