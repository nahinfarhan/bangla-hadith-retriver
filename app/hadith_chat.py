"""
Hadith Chat — RAG-based conversational companion.

Uses Google Gemini via Vertex AI SDK (gemini_client.py) for natural language
generation.  Authentication is handled by Application Default Credentials
(GOOGLE_APPLICATION_CREDENTIALS) — no API key strings needed here.

Falls back to a template-based synthesizer if the Vertex AI call fails.
"""

import re
from typing import List, Dict, Tuple, Iterator

from gemini_client import call_gemini, stream_gemini

_BANGLA_RE = re.compile(r"[\u0980-\u09FF]")


def _is_bangla(text: str) -> bool:
    return bool(_BANGLA_RE.search(text))


# ── Hadith text extraction ────────────────────────────────────────────────────

def _extract_core(text: str, bangla: bool, max_chars: int = 700) -> str:
    """Pull the most content-rich portion of a stored hadith blob.

    max_chars raised from 400 → 700 so the model receives substantially
    more hadith content per source, yielding richer and more accurate answers.
    """
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

def _build_summary_prompt(question: str, snippets: list, bangla: bool) -> str:
    """Short bullet-point summary prompt used by the search page's AI button."""
    context = "\n\n".join(
        f"[{ref}] {book} #{hid}:\n{text}"
        for ref, book, hid, text in snippets
    )
    if bangla:
        return f"""তুমি একজন বিশেষজ্ঞ ইসলামিক পণ্ডিতের সহকারী। নিচের হাদিসগুলোর ভিত্তিতে প্রশ্নের একটি সংক্ষিপ্ত সারসংক্ষেপ লেখো।

নিয়মাবলী:
- শুধুমাত্র নিচের হাদিস থেকে পাওয়া তথ্য ব্যবহার করো, বাইরের জ্ঞান যোগ করো না
- উত্তর বাংলায় লেখো
- প্রথমে এক লাইনের ভূমিকা, তারপর ৩ থেকে ৬টি বুলেট পয়েন্ট; প্রতিটি এক-দুই বাক্যে
- প্রতিটি পয়েন্টের শেষে সূত্র দাও, যেমন [1], [2]
- হাদিসে সরাসরি উল্লেখ না থাকলে সৎভাবে স্বীকার করো

হাদিস:
{context}

প্রশ্ন: {question}

সারসংক্ষেপ:"""
    return f"""You are an expert Islamic knowledge assistant. Write a SHORT summary answering the question using ONLY the hadith excerpts below.

Rules:
- Use ONLY the information in the hadiths; add no external knowledge
- One intro line, then 3 to 6 bullet points of one or two sentences each
- End every bullet with its source, e.g. [1], [2]
- If the hadiths do not address the question, say so honestly

Hadiths:
{context}

Question: {question}

Summary:"""


def _build_prompt(question: str, snippets: list, bangla: bool) -> str:
    context = "\n\n".join(
        f"[{ref}] {book} #{hid}:\n{text}"
        for ref, book, hid, text in snippets
    )
    if bangla:
        return f"""তুমি একজন বিশেষজ্ঞ ইসলামিক পণ্ডিতের সহকারী। নিচের হাদিসগুলোর উপর ভিত্তি করে প্রশ্নের সম্পূর্ণ ও বিস্তারিত উত্তর দাও।

নিয়মাবলী:
- শুধুমাত্র নিচের হাদিস থেকে পাওয়া তথ্য ব্যবহার করো, বাইরের জ্ঞান যোগ করো না
- উত্তর বাংলায় লেখো
- প্রতিটি তথ্যের পাশে সূত্র উল্লেখ করো যেমন [১], [২] ইত্যাদি
- প্রশ্নের সকল দিক কভার করো — একাধিক ধাপ, শর্ত বা নিয়ম থাকলে সব বিস্তারিতভাবে আলোচনা করো
- তালিকা বা ধাপে ধাপে উত্তর দেওয়া যুক্তিযুক্ত হলে সেভাবে দাও
- সংক্ষিপ্ত উত্তরে সীমাবদ্ধ থেকো না — হাদিসে যা আছে তার পূর্ণ বিবরণ দাও
- হাদিসে সরাসরি উল্লেখ না থাকলে সৎভাবে স্বীকার করো

হাদিস:
{context}

প্রশ্ন: {question}

বিস্তারিত উত্তর:"""
    else:
        return f"""You are an expert Islamic knowledge assistant. Answer the question thoroughly and completely using ONLY the hadith excerpts below.

Rules:
- Use ONLY the information from the hadiths provided; do not add external knowledge
- Cite every claim with its source using [1], [2], etc.
- Cover all aspects of the question — list every step, condition, or rule mentioned across the hadiths
- Use bullet points or numbered steps where appropriate for clarity
- Do NOT give a brief summary — provide the full, detailed answer the hadiths support
- If the hadiths don't directly address the question, say so honestly

Hadiths:
{context}

Question: {question}

Detailed Answer:"""


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
        # Looser fallback — use top 10 rather than nothing, so the model
        # still has material to work with even on borderline queries.
        relevant = hadiths[:10]

    # Cap at 20 hadiths. With 700-char excerpts this is a ~14k-char context
    # block — well within the 1M-token context window of flash-lite.
    relevant = relevant[:20]

    sources: List[Dict] = []
    snippets = []

    for i, h in enumerate(relevant, 1):
        book     = h.get("book", "Unknown").replace("_", " ")
        hid      = h.get("hadith_id", "?")
        score    = h.get("similarity", 0)
        raw_text = h.get("text", "")
        core     = _extract_core(raw_text, bangla, max_chars=700)
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
            max_tokens=8192,   # enough for long Bangla answers; matches client default
            temperature=0.25,  # slightly lower → more faithful, less hallucination
        )
        return answer, sources
    except Exception as e:
        answer = (
            _template_answer(question, snippets, bangla)
            + f"\n\n_(AI answer unavailable: {e})_"
        )
        return answer, sources


def synthesize_answer_stream(
    question: str,
    hadiths: List[Dict],
    api_key: str = "",
    api_keys_raw: str = "",
    style: str = "detailed",
) -> Tuple[Iterator[str], List[Dict]]:
    """
    Streaming version of synthesize_answer.

    Builds the prompt and source list identically to synthesize_answer, but
    returns a generator of text chunks instead of a complete string so the
    UI can render the answer token-by-token.

    Returns:
        (chunk_iterator, sources)
            chunk_iterator : Iterator[str] — yields text chunks as they arrive
            sources        : list[dict]    — same source dicts as synthesize_answer

    Falls back to a single-chunk iterator containing the template answer if
    Vertex AI is unavailable or the stream fails.
    """
    bangla = _is_bangla(question)

    relevant = [h for h in hadiths if h.get("similarity", 0) >= 40]
    if not relevant:
        # Increased from 3 → 10 so borderline queries still get meaningful context
        relevant = hadiths[:10]
    relevant = relevant[:20]  # aligned with synthesize_answer cap

    sources: List[Dict] = []
    snippets = []

    for i, h in enumerate(relevant, 1):
        book     = h.get("book", "Unknown").replace("_", " ")
        hid      = h.get("hadith_id", "?")
        score    = h.get("similarity", 0)
        raw_text = h.get("text", "")
        core     = _extract_core(raw_text, bangla, max_chars=700)
        ref      = f"[{i}]"

        sources.append({
            "ref": ref, "idx": i, "book": book,
            "hadith_id": hid, "score": score,
            "text": raw_text, "core": core,
        })
        snippets.append((ref, book, hid, core))

    build = _build_summary_prompt if style == "summary" else _build_prompt
    prompt = build(question, snippets, bangla)

    try:
        chunk_iter = stream_gemini(
            prompt,
            max_tokens=8192,
            temperature=0.25,  # consistent with synthesize_answer
        )
        return chunk_iter, sources
    except Exception as e:
        # Fall back to a single-chunk iterator so the call site stays uniform
        fallback = _template_answer(question, snippets, bangla) + f"\n\n_(AI answer unavailable: {e})_"
        return iter([fallback]), sources
