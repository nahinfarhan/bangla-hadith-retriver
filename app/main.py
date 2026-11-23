"""
Bangla Islamic QA — Streamlit frontend (new UI)

Architecture:
  - app/ui/theme.py     CSS string builder
  - app/ui/components.py  render helpers (logo, top bar, hadith card, etc.)
  - app/ui/scripts.py   injected JS (theme toggle, copy, infinite scroll, aria)
  - app/ui/data.py      browse index + page fetch (read-only, cached)
  - app/main.py         orchestrator: session init, view routing, backend calls

The one rule: change the UI only — backend modules are never modified.
"""
import html as _html
import re as _re
import sys
from pathlib import Path

import streamlit as st

# ── Make app/ importable regardless of cwd ──────────────────────────────────
_APP_DIR = str(Path(__file__).parent.absolute())
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from sentry_init import init_sentry
init_sentry()

# ── UI package ───────────────────────────────────────────────────────────────
from ui import LOGO_MASK_B64
from ui.theme import build_css
from ui.components import (
    logo_html, top_bar, typing_dots_html, cached_tag_html,
    error_state, skeleton_card_html, hadith_card,
    hadith_card_header_body_html, source_cards, feedback_row,
    html_block, parse_hadith,
)
from ui.scripts import (
    theme_toggle_script, copy_handler_script,
    infinite_scroll_script, aria_patch_script, scroll_to_last_question_script,
)
from ui.data import browse_index, fetch_page

# ═══════════════════════════════════════════════════════════════════════════
# Page config  (must be the first Streamlit call)
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Bangla Islamic Q&A",
    page_icon="🕌",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════
# Helpers  (kept from the old main.py, no functional change)
# ═══════════════════════════════════════════════════════════════════════════
_BANGLA_RE = _re.compile(r"[\u0980-\u09FF]")


def is_bangla(text: str) -> bool:
    return bool(_BANGLA_RE.search(text))


def _esc(t: str) -> str:
    return (str(t)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def extract_display_text(text: str, bangla_query: str = "") -> str:
    """Extract the most relevant portion of a stored hadith text blob."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


BOOK_BN = {
    "Sahih_Bukhari":    "সহীহ বুখারী",
    "Sahih_Muslim":     "সহীহ মুসলিম",
    "Sunan_Abu_Dawud":  "সুনান আবু দাউদ",
    "Jami_at_Tirmidhi": "জামে আত-তিরমিযী",
    "Sunan_an_Nasai":   "সুনান আন-নাসায়ী",
    "Sunan_Ibn_Majah":  "সুনান ইবনে মাজাহ",
    "Riyad_as_Salihin": "রিয়াদুস সালিহীন",
}
BOOKS_LIST = list(BOOK_BN.items())
# Books offered in Hadith Books (Riyad as-Salihin is excluded by request).
HADITH_BOOKS_EXCLUDED = {"Riyad_as_Salihin"}
HADITH_BOOKS = {k: v for k, v in BOOK_BN.items() if k not in HADITH_BOOKS_EXCLUDED}


def book_display(raw: str) -> str:
    """Return the Bangla display name for a book key."""
    c = raw.replace(" ", "_")
    if c in BOOK_BN:
        return BOOK_BN[c]
    for k, v in BOOK_BN.items():
        if k.lower() in raw.lower():
            return v
    return raw.replace("_", " ")


def _hadith_to_dict(h: dict) -> dict:
    meta = h.get("metadata", {})
    return {
        "hadith_id": h.get("hadith_id", meta.get("hadith_id", "?")),
        "book":      h.get("book",      meta.get("book", "Unknown")),
        "narrator":  h.get("narrator",  meta.get("narrator", "")),
        "grade":     h.get("grade",     meta.get("grade", "")) or "",
        "text":      h.get("text", ""),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Backend loaders  (cached singletons, never modified)
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def load_query_cache():
    from query_cache import QueryCache
    return QueryCache()


@st.cache_resource(show_spinner=False)
def _init_query_log() -> bool:
    """Create the anonymous query-log DB once per process and prune old rows."""
    try:
        from query_logger import init_log_db, prune_old_logs
        ok = init_log_db()
        if ok:
            prune_old_logs(days=90)
        return ok
    except Exception:
        return False


def _log_query(q: str, answer: str, sources: list, started: float) -> None:
    """Anonymously log one Q&A. Never raises: a log error must not break the answer."""
    try:
        import time as _time
        from query_logger import log_qa, hadith_ids_from_sources
        log_qa(
            q, answer or "", hadith_ids_from_sources(sources),
            int((_time.perf_counter() - started) * 1000),
        )
    except Exception:
        pass


@st.cache_resource(show_spinner=False)
def load_hadith_engine():
    from hybrid_search import HybridHadithSearch
    db_path = str(Path(__file__).parent.parent / "data" / "hadith_vectors")
    return HybridHadithSearch(hadith_db_path=db_path, use_reranker=False)


@st.cache_resource(show_spinner=False)
def load_doc_components():
    """Lazy-load document Q&A components (hidden route ?view=docs)."""
    try:
        from ingest import load_documents  # noqa: F401
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Session state initialisation
# ═══════════════════════════════════════════════════════════════════════════
def _init_session_state() -> None:
    defaults = {
        "view":            "chat",
        "chat_history":    [],
        "chat_sources":    {},
        "feedback_votes":  {},
        "h_book":          "Sahih_Bukhari",
        "h_query":         "",
        "h_loaded":        0,
        "h_results":       [],
        "h_jump_result":   None,
        "_pending_ask":    "",
        "_stream_error":   False,
        "_retry_question": "",
        "_hero_question":  "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════════════
# Query-param sync
# ═══════════════════════════════════════════════════════════════════════════
def _sync_query_params() -> None:
    """Mirror st.session_state["view"] ↔ st.query_params["view"].
    Also reads ?_q= from the hero iframe submit (query-param relay).
    """
    try:
        # --- view param ---
        qp_view = st.query_params.get("view", "")
        if qp_view in ("chat", "hadith", "docs"):
            if st.session_state["view"] != qp_view:
                st.session_state["view"] = qp_view
        else:
            st.query_params["view"] = st.session_state["view"]

        # --- _q param: question submitted from the hero iframe ---
        qp_q = st.query_params.get("_q", "").strip()
        if qp_q:
            # Store as pending question, clear the param so it only fires once
            st.session_state["_hero_question"] = qp_q
            del st.query_params["_q"]
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# Hadith search cache helper
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def _cached_hadith_search(_engine, query: str, book: str) -> list:
    """Wrap engine.search_hadiths in st.cache_data.

    Fetches extra candidates so that, after hiding excluded books, the page
    still gets the top SEARCH_TOP_K results.
    """
    raw = _engine.search_hadiths(
        query, top_k=SEARCH_TOP_K + 10, use_reframing=True, extra_keys_raw=""
    )
    out = [
        _hadith_to_dict(h) for h in raw
        if str(h.get("book", "")).replace(" ", "_") not in HADITH_BOOKS_EXCLUDED
    ]
    return out[:SEARCH_TOP_K]


SEARCH_TOP_K = 15  # results shown on the Hadith Books search page


# ── Hadith-reference questions ("<বই> <n> নম্বর হাদীস …") ────────────────────
# Spelling variants users type for each book (longest first when matching).
_BOOK_ALIASES = {
    "Sahih_Bukhari":    ["সহীহ বুখারী", "সহিহ বুখারী", "সহীহ বুখারি", "বুখারী", "বুখারি", "bukhari"],
    "Sahih_Muslim":     ["সহীহ মুসলিম", "সহিহ মুসলিম", "মুসলিম", "muslim"],
    "Jami_at_Tirmidhi": ["জামে আত-তিরমিযী", "জামে তিরমিযী", "তিরমিযী", "তিরমিজি", "তিরমিযি", "tirmidhi"],
    "Sunan_Abu_Dawud":  ["সুনান আবু দাউদ", "সুনান আবূ দাঊদ", "আবু দাউদ", "আবূ দাঊদ", "আবু দাঊদ", "abu dawud"],
    "Sunan_Ibn_Majah":  ["সুনান ইবনে মাজাহ", "সুনান ইবনু মাজাহ", "ইবনে মাজাহ", "ইবনু মাজাহ", "ইবনে মাজা", "ibn majah"],
    "Sunan_an_Nasai":   ["সুনান আন-নাসায়ী", "সুনান নাসায়ী", "নাসায়ী", "নাসাঈ", "নাসাই", "nasai"],
    "Riyad_as_Salihin": ["রিয়াদুস সালিহীন", "রিয়াদুস সালেহীন", "riyad"],
}
_BN_TO_LATIN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_NEIGHBOURS = 2  # hadiths before and after the asked one (up to 5 total)


def _parse_hadith_reference(q: str):
    """Return (book_key, number) if q names a book and a hadith number, else None.

    The number must come after the book name, e.g. "সহীহ বুখারী 1 নম্বর
    হাদীস", "বুখারী ১ নং হাদিস", "Bukhari 52".  Bangla digits are accepted.
    """
    text = q.translate(_BN_TO_LATIN)
    low = text.lower()
    best = None  # (position, -len(alias), book_key, alias)
    for key, aliases in _BOOK_ALIASES.items():
        for alias in aliases:
            pos = low.find(alias.lower())
            if pos >= 0:
                cand = (pos, -len(alias), key, alias)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return None
    pos, neg_len, key, _ = best
    after = text[pos - neg_len:]
    m = _re.match(r"\s*(?:এর|-এর|,)?\s*(?:হাদীস|হাদিস|hadith|#|no\.?)?\s*(\d{1,5})\b", after, _re.I)
    if not m:
        return None
    n = int(m.group(1))
    return (key, n) if n > 0 else None


def _hadith_reference_context(q: str, engine) -> list:
    """Hadith n of the named book first, then up to 2 neighbours each side.

    Returned dicts use the same fields as engine.search_hadiths results so
    synthesize_answer_stream can use them unchanged.  Empty list if q is not
    a hadith reference or the hadith is not in the database.
    """
    ref = _parse_hadith_reference(q)
    if not ref:
        return []
    book, n = ref

    def _get(num):
        try:
            h = engine.get_hadith_by_number(num, book=book)
        except Exception:
            return None
        if not h:
            return None
        meta = h.get("metadata") or {}
        return {
            "hadith_id":  str(h.get("hadith_id", num)),
            "book":       h.get("book", book),
            "narrator":   meta.get("narrator", ""),
            "grade":      meta.get("grade", "") or "",
            "text":       h.get("text", ""),
            # High scores so the >=40 relevance filter keeps all of them;
            # the asked hadith stays first and becomes source [1].
            "similarity": 100 if num == n else 90 - abs(num - n),
        }

    target = _get(n)
    if target is None:
        return []
    out = [target]
    for d in range(1, _NEIGHBOURS + 1):
        for num in (n - d, n + d):
            if num > 0:
                h = _get(num)
                if h:
                    out.append(h)
    return out


def _bn_digits(n: int) -> str:
    """Convert integer to Bangla-digit string (fix item 8: Bangla digits for counts)."""
    try:
        return str(n).translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
    except Exception:
        return str(n)


# ═══════════════════════════════════════════════════════════════════════════
# Chat flow
# ═══════════════════════════════════════════════════════════════════════════
def _handle_question(q: str, engine, qcache) -> None:
    """Cache-first chat flow (Feature 4).

    Order: qcache.get → hit: render; miss: search → stream → qcache.set
    """
    from hadith_chat import synthesize_answer_stream
    from feedback import log_vote  # noqa: imported here to avoid circular at module level

    import time as _time
    _started = _time.perf_counter()  # end-to-end latency for the query log

    # 1. Cache lookup FIRST (fixes the old bug where retrieval ran first)
    cache_hit = qcache.get(q)

    # Append user message
    st.session_state.chat_history.append(
        {"role": "user", "content": q, "cached": False, "error": False}
    )

    if cache_hit:
        # ── Cache HIT ────────────────────────────────────────────────────
        answer, sources = cache_hit
        msg_idx = len(st.session_state.chat_history)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer, "cached": True, "error": False}
        )
        st.session_state.chat_sources[msg_idx] = sources
        st.session_state.feedback_votes.setdefault(msg_idx, None)
        st.session_state["_scroll_to_question"] = True
        _log_query(q, answer, sources, _started)
        st.rerun()
        return

    # ── Cache MISS: retrieve → stream → store ────────────────────────────
    msg_idx = len(st.session_state.chat_history)

    # Show the user's question immediately (before the slow retrieval),
    # so the UI reacts the moment the question is sent.
    st.markdown(
        html_block(
            f'<div class="iq-msg-user"><p class="iq-bubble">{_esc(q)}</p></div>'
        ),
        unsafe_allow_html=True,
    )
    # Focus the new question (scroll it to the top of the viewport).
    st.components.v1.html(scroll_to_last_question_script(), height=0)
    st.session_state["_scroll_to_question"] = True

    # Typing indicator + status line while retrieval runs (can take a while
    # on the first question, when the model and BM25 index are loaded).
    typing_placeholder = st.empty()
    typing_placeholder.markdown(
        html_block(
            '<div class="iq-msg-ai">'
            '<div class="iq-avatar">✦</div>'
            '<div class="iq-ai-body">'
            + typing_dots_html() +
            '<span class="iq-status">হাদীস খোঁজা হচ্ছে…</span>'
            '</div></div>'
        ),
        unsafe_allow_html=True,
    )

    try:
        # Question about a specific hadith ("সহীহ বুখারী 1 নম্বর হাদীস…"):
        # give the model that hadith plus its neighbours instead of a
        # semantic search, which does not find a hadith by its number.
        raw = _hadith_reference_context(q, engine)
        if not raw:
            raw = engine.search_hadiths(q, top_k=30, use_reframing=True, extra_keys_raw="")
    except Exception:
        typing_placeholder.empty()
        st.session_state.chat_history.append(
            {"role": "assistant", "content": "", "cached": False, "error": True}
        )
        st.session_state["_stream_error"] = True
        st.session_state["_retry_question"] = q
        st.rerun()
        return

    chunk_iter, sources = synthesize_answer_stream(q, raw)

    # Update the status line: retrieval done, waiting for the first token.
    typing_placeholder.markdown(
        html_block(
            '<div class="iq-msg-ai">'
            '<div class="iq-avatar">✦</div>'
            '<div class="iq-ai-body">'
            + typing_dots_html() +
            '<span class="iq-status">উত্তর লেখা হচ্ছে…</span>'
            '</div></div>'
        ),
        unsafe_allow_html=True,
    )

    def _until_first_token(it):
        """Keep the typing dots until the first chunk, then remove them."""
        first = True
        for chunk in it:
            if first:
                typing_placeholder.empty()
                first = False
            yield chunk
        if first:  # stream produced nothing
            typing_placeholder.empty()

    # Stream via st.write_stream, next to the AI avatar
    with st.container():
        col_av, col_body = st.columns([0.06, 0.94])
        with col_av:
            st.markdown(
                html_block('<div class="iq-avatar" style="margin-top:4px">✦</div>'),
                unsafe_allow_html=True,
            )
        with col_body:
            try:
                answer = st.write_stream(_until_first_token(chunk_iter))
            except Exception:
                typing_placeholder.empty()
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": "", "cached": False, "error": True}
                )
                st.session_state["_stream_error"] = True
                st.session_state["_retry_question"] = q
                st.rerun()
                return

    # Successful stream — store in history and cache
    st.session_state.chat_history.append(
        {"role": "assistant", "content": answer, "cached": False, "error": False}
    )
    st.session_state.chat_sources[msg_idx] = sources
    st.session_state.feedback_votes.setdefault(msg_idx, None)
    _log_query(q, answer, sources, _started)
    # Only cache non-empty, non-error answers (Feature 4)
    if answer and not answer.startswith("_(AI answer unavailable"):
        qcache.set(q, answer, sources)

    st.rerun()


def _render_thread(qcache) -> None:
    """Render the full conversation history."""
    from feedback import log_vote

    hist = st.session_state.chat_history
    votes = st.session_state.feedback_votes

    for idx, msg in enumerate(hist):
        if msg["role"] == "user":
            st.markdown(
                html_block(
                    f'<div class="iq-msg-user">'
                    f'<p class="iq-bubble">{_esc(msg["content"])}</p>'
                    f'</div>'
                ),
                unsafe_allow_html=True,
            )
        elif msg.get("error"):
            # Fix item 7: error state with retry button
            error_state(st.session_state.get("_retry_question", ""))
        else:
            # AI message
            cached = msg.get("cached", False)
            with st.container():
                col_av, col_body = st.columns([0.06, 0.94])
                with col_av:
                    st.markdown(
                        html_block(
                            '<div class="iq-avatar" style="margin-top:4px">✦</div>'
                        ),
                        unsafe_allow_html=True,
                    )
                with col_body:
                    if cached:
                        st.markdown(cached_tag_html(), unsafe_allow_html=True)
                    # Render with st.markdown so streamed and replayed look identical
                    st.markdown(msg["content"])
                    srcs = st.session_state.chat_sources.get(idx, [])
                    if srcs:
                        source_cards(srcs, uid=f"m{idx}")
                    feedback_row(idx, msg, srcs, log_vote)

    # Handle retry button (matrix row 7: no duplicate user bubble)
    if st.session_state.get("_stream_error") and st.session_state.get("_retry_question"):
        error_state(st.session_state.get("_retry_question", ""))


# ═══════════════════════════════════════════════════════════════════════════
# Chat view
# ═══════════════════════════════════════════════════════════════════════════
def render_chat_view(engine, engine_ok: bool, err, qcache) -> None:
    hist = st.session_state.chat_history
    in_conversation = len(hist) > 0

    # Top bar (fix item 7: real ghost pill buttons, no stray line)
    top_bar("chat", in_conversation)

    # Handle pending "AI-কে জিজ্ঞেস করুন" pre-fill
    pending = st.session_state.get("_pending_ask", "")

    # A question sent from the Home hero (via ?_q=) switches straight to the
    # conversation layout: no hero, the user bubble + typing dots show at once.
    hero_q = (st.session_state.pop("_hero_question", "") or "").strip()
    if hero_q and not in_conversation:
        if not engine_ok:
            st.error(
                "ডেটাবেস প্রস্তুত নয়। "
                "Run `python3 app/build_hadith_db.py` first."
            )
            return
        _handle_question(hero_q, engine, qcache)
        return

    if not in_conversation:
        # ── HOME STATE ────────────────────────────────────────────────────
        # st.markdown('<div>') open/close wrappers don't work — Streamlit
        # wraps each call in its own element, auto-closing the div.
        # Fix: render hero entirely inside an iframe (st.components.v1.html)
        # which handles layout/glow natively. Question relay uses a hidden
        # st.text_input that the iframe JS fills, followed by a hidden submit.

        import streamlit.components.v1 as _cv1

        mask_url = (
            f"url('data:image/png;base64,{LOGO_MASK_B64}')"
            if LOGO_MASK_B64
            else "none"
        )

        hero_html = f"""<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#F4F7F5;--surface:#FFFFFF;--surface-2:#E8EEEA;--line:#DAE3DD;
  --ink:#13201A;--muted:#5A6A61;--accent:#0D6B51;--logo:#2B5E47;
  --g1:#19B37F;--g2:#35C4C9;--g3:#E8C56A;--glow:0.4;
  --font:'Hind Siliguri',system-ui,sans-serif;
}}
html,body{{background:transparent;font-family:var(--font);color:var(--ink);margin:0;overflow:hidden;height:100%;}}
body.dark{{
  --bg:#0A1210;--surface:#111C17;--line:#1E2D26;--ink:#E6EFE9;
  --muted:#8DA095;--accent:#3FD6A6;--logo:#3FD6A6;
  --g1:#22D69B;--g2:#3FD0E0;--g3:#F0CF73;--glow:0.55;
}}
@property --a{{syntax:"<angle>";inherits:false;initial-value:0deg;}}
.wrap{{display:flex;flex-direction:column;align-items:center;gap:18px;text-align:center;padding:24px 20px 12px;}}
.logo{{display:block;width:min(440px,78vw);aspect-ratio:1000/128;background:var(--logo);
  -webkit-mask:{mask_url} center/contain no-repeat;mask:{mask_url} center/contain no-repeat;
  transition:background-color 0.2s;}}
.sub{{font-size:clamp(16px,3vw,21px);color:var(--muted);}}
.cw{{position:relative;isolation:isolate;width:100%;max-width:680px;border-radius:30px;}}
.cw::before,.cw::after{{content:"";position:absolute;z-index:-1;border-radius:inherit;
  background:conic-gradient(from var(--a),var(--g1),var(--g2),var(--g3),var(--g1));
  animation:spin 9s linear infinite;}}
.cw::before{{inset:-2px;opacity:calc(var(--glow)+0.35);transition:opacity 0.3s;}}
.cw::after{{inset:-2px;filter:blur(18px);opacity:var(--glow);transition:opacity 0.3s,inset 0.3s;}}
.cw:focus-within::before{{opacity:1;}}
.cw:focus-within::after{{opacity:calc(var(--glow)+0.3);inset:-6px;}}
@keyframes spin{{to{{--a:360deg;}}}}
@media(prefers-reduced-motion:reduce){{.cw::before,.cw::after{{animation:none;}}}}
.cf{{display:flex;align-items:center;gap:8px;background:var(--surface);border-radius:28px;padding:10px 10px 10px 22px;min-height:62px;}}
.cf input{{flex:1;min-width:0;border:0;outline:0;background:transparent;font-size:16px;font-family:var(--font);color:var(--ink);line-height:1.6;}}
.cf input::placeholder{{color:var(--muted);}}
.send{{width:42px;height:42px;flex:none;border:0;border-radius:50%;background:var(--accent);color:#fff;
  cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;
  transition:opacity 0.2s,transform 0.2s;font-family:var(--font);}}
.send:hover{{transform:scale(1.06);}}
.pill{{display:inline-flex;align-items:center;gap:8px;height:44px;padding:0 22px;border-radius:999px;
  border:1px solid var(--line);background:var(--surface);font-size:14.5px;font-weight:500;
  font-family:var(--font);color:var(--ink);cursor:pointer;transition:border-color 0.2s,color 0.2s;}}
.pill:hover{{border-color:var(--accent);color:var(--accent);}}
.note{{font-size:12.5px;color:var(--muted);}}
</style></head><body>
<div class="wrap">
  <div class="logo" role="img" aria-label="Bangla Islamic QA"></div>
  <p class="sub">আসসালামু আলাইকুম, আজ আপনি কী জানতে চান?</p>
  <div class="cw"><form class="cf" id="qf" autocomplete="off">
    <input id="qi" type="text" placeholder="আপনার প্রশ্ন লিখুন…" aria-label="প্রশ্ন" value="{_html.escape(pending or '', quote=True)}">
    <button type="submit" class="send" aria-label="পাঠান">↑</button>
  </form></div>
  <button class="pill" id="hpill" type="button">📖 হাদীস গ্রন্থ</button>
  <p class="note">AI ভুল করতে পারে। উৎস যাচাই করে নিন।</p>
</div>
<script>
(function(){{
  var pd = window.parent.document;
  var pw = window.parent;

  // ── Theme sync ──────────────────────────────────────────────────────────
  function syncTheme(){{
    var t = pd.documentElement.getAttribute('data-theme');
    if (!t) t = pw.matchMedia && pw.matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light';
    document.body.classList.toggle('dark', t === 'dark');
  }}
  syncTheme();
  new MutationObserver(syncTheme).observe(pd.documentElement, {{attributes:true, attributeFilter:['data-theme']}});

  // ── Submit handler ──────────────────────────────────────────────────────
  // CANNOT use window.parent.location.assign() from inside a sandboxed iframe
  // (Streamlit's sandbox does NOT include allow-top-navigation).
  // Solution: postMessage to the parent; a parent-page listener (injected via
  // st.html, which is NOT sandboxed) receives it and navigates from there.
  // Run code AS the parent page: a <script> element created in the parent
  // document executes with the parent's (unsandboxed) context, so it may
  // navigate the top window.
  function runInParent(code) {{
    var s = pd.createElement('script');
    s.textContent = code;
    pd.body.appendChild(s);
    pd.body.removeChild(s);
  }}
  function navigate(view, q) {{
    var code = 'var u=new URL(window.location.href);' +
      'u.searchParams.set("view",' + JSON.stringify(view) + ');' +
      (q ? 'u.searchParams.set("_q",' + JSON.stringify(q) + ');'
         : 'u.searchParams.delete("_q");') +
      'window.location.assign(u.toString());';
    runInParent(code);
  }}

  document.getElementById('qf').addEventListener('submit', function(e) {{
    e.preventDefault();
    var q = document.getElementById('qi').value.trim();
    if (!q) return;
    navigate('chat', q);
  }});

  // ── Hadith pill ─────────────────────────────────────────────────────────
  document.getElementById('hpill').addEventListener('click', function() {{
    navigate('hadith', '');
  }});

  // ── Auto-focus ──────────────────────────────────────────────────────────
  setTimeout(function() {{ document.getElementById('qi').focus(); }}, 200);
}})();
</script>
</body></html>"""

        with st.container(key="home_hero"):
            _cv1.html(hero_html, height=320, scrolling=False)

        # The pending "AI-কে জিজ্ঞেস করুন" question is pre-filled into the
        # hero input (see value= above) and is NOT sent automatically.
        if pending:
            st.session_state["_pending_ask"] = ""

    else:
        # ── CONVERSATION STATE ────────────────────────────────────────────
        _render_thread(qcache)

        # After a new question was answered, keep the focus on it.
        if st.session_state.pop("_scroll_to_question", False):
            st.components.v1.html(scroll_to_last_question_script(), height=0)

        # Pre-filled question banner (matrix row 10: pre-fill, not sent)
        if pending:
            st.info(f"প্রশ্ন: {pending}\n\nপাঠাতে নিচের বাক্সে Enter চাপুন।")

        # "হাদীস গ্রন্থ" pill docked under the composer (CSS-positioned)
        with st.container(key="dock_hadith"):
            if st.button("📖 হাদীস গ্রন্থ", key="dock_hadith_btn"):
                st.session_state["view"] = "hadith"
                try:
                    st.query_params["view"] = "hadith"
                except Exception:
                    pass
                st.rerun()

        # Fix item 5: st.chat_input at top level pins to the bottom
        question = st.chat_input(
            placeholder="আপনার প্রশ্ন লিখুন…",
            key="chat_input_conv",
        )

        if pending:
            st.session_state["_pending_ask"] = ""

        # If pending ask and user pressed Enter without typing, use pending
        if question is None and pending:
            question = pending

        if question and question.strip():
            if not engine_ok:
                st.error(
                    "ডেটাবেস প্রস্তুত নয়। "
                    "Run `python3 app/build_hadith_db.py` first."
                )
                return
            _handle_question(question.strip(), engine, qcache)


# ═══════════════════════════════════════════════════════════════════════════
# Hadith Books view
# ═══════════════════════════════════════════════════════════════════════════
def _render_hadith_list(engine) -> None:
    """Render the hadith list fragment (browse or search mode)."""
    PAGE = 3
    h_query   = st.session_state.get("h_query", "")
    h_book    = st.session_state.get("h_book", "Sahih_Bukhari")
    h_loaded  = st.session_state.get("h_loaded", 0)
    h_results = st.session_state.get("h_results", [])
    jump      = st.session_state.get("h_jump_result")

    if h_query:
        # ── SEARCH MODE ──────────────────────────────────────────────────
        if not h_results:
            try:
                h_results = [
                    h for h in _cached_hadith_search(engine, h_query, h_book)
                    if str(h.get("book", "")).replace(" ", "_") not in HADITH_BOOKS_EXCLUDED
                ]
                st.session_state["h_results"] = h_results
            except Exception as e:
                st.error(f"অনুসন্ধান ব্যর্থ হয়েছে: {e}")
                if st.button("আবার চেষ্টা করুন", key="retry_search"):
                    st.session_state["h_results"] = []
                    st.rerun()
                return

        if not h_results:
            # Fix item 5: no results state
            st.markdown(
                html_block(
                    '<div class="iq-error-box">কোনো হাদীস পাওয়া যায়নি</div>'
                    '<p class="iq-note">অন্য শব্দ দিয়ে খুঁজুন।</p>'
                ),
                unsafe_allow_html=True,
            )
            if st.button("সার্চ মুছুন", key="clear_search", type="secondary"):
                st.session_state["h_query"] = ""
                st.session_state["h_results"] = []
                st.session_state["h_loaded"] = 0
                st.rerun()
            return

        # Show all top results at once (search returns SEARCH_TOP_K)
        for i, h in enumerate(h_results):
            book_key = str(h.get("book", "")).replace(" ", "_")
            ask_key = f"ask_{book_key}_{h.get('hadith_id', '?')}"
            hadith_card(h, flash=False, ask_key=ask_key)

        st.caption("সব হাদীস দেখানো হয়েছে")
        return

    # ── BROWSE MODE ──────────────────────────────────────────────────────
    try:
        index = browse_index(_engine=engine, book=h_book)
    except Exception:
        index = []

    if not index:
        st.info("এই গ্রন্থের হাদীস পাওয়া যায়নি।")
        return

    # Number-jump: show jumped hadith first with flash (matrix row 14)
    if jump:
        book_key = str(jump.get("book", "")).replace(" ", "_")
        ask_key = f"ask_jump_{book_key}_{jump.get('hadith_id', '?')}"
        hadith_card(jump, flash=True, ask_key=ask_key)
        st.session_state["h_jump_result"] = None

    end = min(h_loaded + PAGE, len(index))

    page_ids = [vid for _, vid in index[:end]]
    try:
        hadiths = fetch_page(engine, page_ids)
    except Exception:
        hadiths = []

    for h in hadiths:
        book_key = str(h.get("book", "")).replace(" ", "_")
        ask_key = f"ask_{book_key}_{h.get('hadith_id', '?')}"
        hadith_card(h, flash=False, ask_key=ask_key)

    if end < len(index):
        st.markdown(html_block('<div class="iq-loading-more" role="status"><span class="iq-spin"></span>আরও হাদীস লোড হচ্ছে…</div>'), unsafe_allow_html=True)
        st.components.v1.html(infinite_scroll_script("sentinel_load_more"), height=0)
        if st.button("আরও দেখুন", key="load_more", type="secondary"):
            st.session_state["h_loaded"] = end
            st.rerun()
    else:
        st.caption("সব হাদীস দেখানো হয়েছে")


def render_hadith_view(engine, engine_ok: bool, err) -> None:
    if not engine_ok:
        st.error(
            "ডেটাবেস প্রস্তুত নয়। "
            "Run `python3 app/build_hadith_db.py` first."
        )
        return

    # Top bar (fix item 7: back button + title on same row)
    top_bar("hadith", False)

    # ── Search bar (fix item 8: one pill, Enter submits, no emoji button) ──
    with st.container(key="h_search_wrap"), \
            st.form("h_search_form", clear_on_submit=False, border=False):
        search_val = st.text_input(
            "হাদীস খুঁজুন",
            value=st.session_state.get("h_query", ""),
            placeholder="হাদীস খুঁজুন…",
            label_visibility="collapsed",
            key="h_search_input",
        )
        search_submitted = st.form_submit_button("খুঁজুন")  # hidden; Enter submits

    if search_submitted:
        new_q = search_val.strip()
        if new_q != st.session_state.get("h_query", ""):
            st.session_state["h_query"] = new_q
            st.session_state["h_results"] = []
            st.session_state["h_loaded"] = 0
            # Clear cached search so a new query re-runs
            _cached_hadith_search.clear()
            st.rerun()
    elif not search_val.strip() and st.session_state.get("h_query"):
        # Cleared search → back to browse (matrix row 12)
        st.session_state["h_query"] = ""
        st.session_state["h_results"] = []
        st.session_state["h_loaded"] = 0
        st.rerun()

    # ── Book select + number field (fix item 8) ────────────────────────────
    ctrl_col1, ctrl_col2 = st.columns([3, 1.25], gap="small",
                                      vertical_alignment="center")

    with ctrl_col1:
        book_names = list(HADITH_BOOKS.values())
        book_keys  = list(HADITH_BOOKS.keys())
        if st.session_state.get("h_book") not in HADITH_BOOKS:
            st.session_state["h_book"] = "Sahih_Bukhari"
        cur_idx = book_keys.index(st.session_state["h_book"])
        selected_name = st.selectbox(
            "হাদীস গ্রন্থ",
            options=book_names,
            index=cur_idx,
            label_visibility="collapsed",
            key="h_book_select",
        )
        selected_key = book_keys[book_names.index(selected_name)]
        if selected_key != st.session_state.get("h_book"):
            # Matrix row 13: changing book resets search and number
            st.session_state["h_book"] = selected_key
            st.session_state["h_query"] = ""
            st.session_state["h_results"] = []
            st.session_state["h_loaded"] = 0
            st.session_state["h_jump_result"] = None
            _cached_hadith_search.clear()
            st.rerun()

    with ctrl_col2:
        # Fix item 8: number field as form with # prefix and go button inside
        with st.container(key="h_no_wrap"), \
                st.form("h_no_form", clear_on_submit=False, border=False):
            hadith_no_str = st.text_input(
                "হাদীস নম্বর",
                value="",
                placeholder="হাদীস নম্বর",
                label_visibility="collapsed",
                key="h_no_input",
            )
            go_submitted = st.form_submit_button("→")

        if go_submitted and hadith_no_str and hadith_no_str.strip():
            try:
                n = int(hadith_no_str.strip())
            except ValueError:
                n = 0
            if n > 0:
                result = engine.get_hadith_by_number(n, book=st.session_state["h_book"])
                if result is None:
                    bname = book_display(st.session_state["h_book"])
                    st.toast(f"{bname}-এ {n} নম্বর হাদীস পাওয়া যায়নি")
                else:
                    st.session_state["h_jump_result"] = _hadith_to_dict(result)
                    st.session_state["h_loaded"] = 0
                    st.rerun()

    # ── Count line (fix item 8: muted 13px, Bangla digits) ────────────────
    h_query = st.session_state.get("h_query", "")
    h_book  = st.session_state.get("h_book", "Sahih_Bukhari")
    bname   = book_display(h_book)
    if h_query and not st.session_state.get("h_results"):
        # Run the search before the count line so "N টি ফলাফল" shows on the
        # same render.  Errors are left to the list, which shows Retry.
        try:
            st.session_state["h_results"] = [
                h for h in _cached_hadith_search(engine, h_query, h_book)
                if str(h.get("book", "")).replace(" ", "_") not in HADITH_BOOKS_EXCLUDED
            ]
        except Exception:
            pass
    if h_query:
        results_count = len(st.session_state.get("h_results", []))
        if results_count:
            st.markdown(
                html_block(f'<div class="iq-count-line">{_bn_digits(results_count)} টি ফলাফল</div>'),
                unsafe_allow_html=True,
            )
    else:
        try:
            idx = browse_index(_engine=engine, book=h_book)
            total = len(idx)
        except Exception:
            total = 0
        if total:
            st.markdown(
                html_block(
                    f'<div class="iq-count-line">{bname} · {_bn_digits(total)}টি হাদীস</div>'
                ),
                unsafe_allow_html=True,
            )

    # ── List ─────────────────────────────────────────────────────────────
    _render_hadith_list(engine)


# ═══════════════════════════════════════════════════════════════════════════
# Document Q&A  (hidden route — ?view=docs only; NOT deleted)
# ═══════════════════════════════════════════════════════════════════════════
def general_documents_tab():
    """Hidden Document Q&A tab. Only shown via ?view=docs query param."""
    st.info(
        "Document Q&A is a hidden feature. "
        "Upload a PDF or TXT to ask questions about it."
    )
    uploaded = st.file_uploader(
        "Upload document", type=["pdf", "txt"], key="doc_uploader"
    )
    if uploaded:
        st.write(f"Uploaded: {uploaded.name}")
        st.warning(
            "Document Q&A processing is not wired in the new UI. "
            "See UI_NOTES.md."
        )


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    _init_session_state()
    _sync_query_params()

    # Inject CSS + synchronous theme-apply script (runs before first paint)
    st.markdown(
        f"""<style>{build_css(LOGO_MASK_B64)}</style>
<script>
(function(){{
  var t=null;try{{t=localStorage.getItem('theme');}}catch(e){{}}
  if(!t){{t=window.matchMedia&&window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';}}
  document.documentElement.setAttribute('data-theme',t);
}})();
</script>""",
        unsafe_allow_html=True,
    )

    # Inject JS once (theme toggle, copy handler, aria patches)
    import streamlit.components.v1 as _c
    _c.html(theme_toggle_script(), height=0)
    _c.html(copy_handler_script(), height=0)
    _c.html(aria_patch_script(), height=0)

    # Load engine (errors handled in each view)
    _err = None
    engine_ok = False
    engine = None
    try:
        engine = load_hadith_engine()
        engine_ok = True
    except Exception as e:
        _err = e

    qcache = load_query_cache()
    _init_query_log()

    # Route to the active view
    view = st.session_state.get("view", "chat")
    if view == "hadith":
        render_hadith_view(engine, engine_ok, _err)
    elif view == "docs":
        general_documents_tab()
    else:
        render_chat_view(engine, engine_ok, _err, qcache)
        st.caption(
            "Questions are logged anonymously (no personal data or IP addresses) "
            "to help improve search quality. • "
            "সেবার মান উন্নয়নের জন্য প্রশ্নগুলো সম্পূর্ণ বেনামে সংরক্ষণ করা হয়।"
        )


if __name__ == "__main__":
    main()
