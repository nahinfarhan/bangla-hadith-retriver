"""
Hadith Chat — RAG-based conversational companion.

Uses Google Gemini via Vertex AI SDK (gemini_client.py) for natural language
generation.  Authentication is handled by Application Default Credentials
(GOOGLE_APPLICATION_CREDENTIALS) — no API key strings needed here.

Falls back to a template-based synthesizer if the Vertex AI call fails.
"""

import re
from typing import List, Dict, Tuple

from gemini_client import call_gemini

_BANGLA_RE = re.compile(r"[\u0980-\u09FF]")


def _is_bangla(text: str) -> bool:
    return bool(_BANGLA_RE.search(text))


# ── Hadith text extraction ────────────────────────────────────────────────────

def _extract_core(text: str, bangla: bool, max_chars: int = 400) -> str:
    """Pull the most content-rich portion of a stored hadith blob."""
    lines = text.splitlines()
    kept  = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("বর্ণনাকারী"):
            kept.append(s)
            continue
        arabic = len(re.findall(r"[\u0600-\u06FF]", s))
        if arabic / max(len(s), 1) > 0.4:
            continue
        if bangla and not _BANGLA_RE.search(s):
            continue
        if not bangla:
            if len(_BANGLA_RE.findall(s)) / max(len(s), 1) > 0.3:
                continue
        kept.append(s)

    result = " ".join(kept)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit(" ", 1)[0] + "…"
    return result


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(question: str, snippets: list, bangla: bool) -> str:
    context = "\n\n".join(
        f"[{ref}] {book} #{hid}:\n{text}"
        for ref, book, hid, text in snippets
    )
    if bangla:
        return f"""তুমি একজন ইসলামিক পণ্ডিতের সহকারী। নিচের হাদিসগুলোর উপর ভিত্তি করে প্রশ্নের উত্তর দাও।

নিয়মাবলী:
- শুধুমাত্র নিচের হাদিস থেকে পাওয়া তথ্য ব্যবহার করো
- উত্তর বাংলায় লেখো
- সূত্র উল্লেখ করো যেমন [১], [২] ইত্যাদি
- প্রশ্নের ধরন অনুযায়ী প্রয়োজনীয় বিস্তারিত উত্তর দাও (একাধিক ধাপ বা নিয়ম থাকলে সব উল্লেখ করো)
- হাদিসে না থাকলে সেটা স্বীকার করো

হাদিস:
{context}

প্রশ্ন: {question}

উত্তর:"""
    else:
        return f"""You are an Islamic knowledge assistant. Answer using ONLY the hadith excerpts below.

Rules:
- Use only information from the hadiths provided, do not add external knowledge
- Cite sources using [1], [2], etc.
- Provide as much detail as the question requires (list all steps or rules if applicable)
- If the hadiths don't directly address the question, say so honestly

Hadiths:
{context}

Question: {question}

Answer:"""


# ── Template fallback ─────────────────────────────────────────────────────────

def _template_answer(question: str, snippets: list, bangla: bool) -> str:
    if bangla:
        intro = f'আপনার প্রশ্ন "{question}" সম্পর্কে হাদিসের আলোকে:\n\n'
        parts = [f"{text} {ref}" for ref, _, _, text in snippets if text]
        body  = "\n\n".join(parts) if parts else "প্রাসঙ্গিক হাদিস পাওয়া যায়নি।"
    else:
        intro = f'Regarding "{question}", from the hadith literature:\n\n'
        parts = [f"{text} {ref}" for ref, _, _, text in snippets if text]
        body  = "\n\n".join(parts) if parts else "No directly relevant hadith found."
    return intro + body


# ── Public API ────────────────────────────────────────────────────────────────

def synthesize_answer(
    question: str,
    hadiths: List[Dict],
    # Legacy keyword arguments retained so existing call sites don't break.
    # They are ignored — auth is now handled by ADC in gemini_client.
    api_key: str = "",
    api_keys_raw: str = "",
) -> Tuple[str, List[Dict]]:
    """
    Build a natural-language answer from retrieved hadiths using Gemini
    (via Vertex AI).

    Falls back to a template answer if the Vertex AI call fails.

    Returns:
        answer  : str        — the synthesized answer
        sources : list[dict] — source dicts (ref, book, hadith_id, score, text)
    """
    bangla = _is_bangla(question)

    # Filter to reasonably relevant results
    relevant = [h for h in hadiths if h.get("similarity", 0) >= 40]
    if not relevant:
        relevant = hadiths[:3]

    # Cap the number of hadiths fed into the prompt to avoid an enormous
    # context block that leaves little room for the generated answer.
    relevant = relevant[:15]

    sources: List[Dict] = []
    snippets = []

    for i, h in enumerate(relevant, 1):
        book     = h.get("book", "Unknown").replace("_", " ")
        hid      = h.get("hadith_id", "?")
        score    = h.get("similarity", 0)
        raw_text = h.get("text", "")
        core     = _extract_core(raw_text, bangla, max_chars=400)
        ref      = f"[{i}]"

        sources.append({
            "ref": ref, "idx": i, "book": book,
            "hadith_id": hid, "score": score,
            "text": raw_text, "core": core,
        })
        snippets.append((ref, book, hid, core))

    # ── Try Gemini via Vertex AI ──────────────────────────────────────────────
    try:
        prompt = _build_prompt(question, snippets, bangla)
        answer, _ = call_gemini(
            prompt,
            max_tokens=4096,   # increased from 1024 — Bangla answers need more tokens
            temperature=0.3,
        )
        return answer, sources
    except Exception as e:
        answer = (
            _template_answer(question, snippets, bangla)
            + f"\n\n_(AI answer unavailable: {e})_"
        )
        return answer, sources
