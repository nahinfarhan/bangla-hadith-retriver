"""
app/ui/components.py — Reusable render helpers for the Bangla Islamic Q&A UI.

Functions either:
  - Return an HTML string (injected via st.markdown(..., unsafe_allow_html=True))
  - Directly call Streamlit widgets (st.button, st.container, etc.)

Key helpers added per KIRO_FIX_AND_QA.md:
  - html_block(s):  dedent + strip blank lines so Markdown doesn't show a code block
  - parse_hadith():  split stored one-line hadith into narrator / Bangla / English
"""
import html as _html
import re as _re
import streamlit as st

from ui import LOGO_MASK_B64

_BANGLA_RE    = _re.compile(r"[\u0980-\u09FF]")
_ARABIC_RE     = _re.compile(r"[\u0600-\u06FF]")
_LATIN_LETTER  = _re.compile(r"[A-Za-z]")


def _is_latin_word(word: str) -> bool:
    """True if word has ≥1 Latin letter and no Bangla characters."""
    return bool(_LATIN_LETTER.search(word)) and not _BANGLA_RE.search(word)

# Words after which empty () should show ﷺ (display-only, no data change)
_SALAW_WORDS  = _re.compile(r"(রাসূল|রসূল|নবী)\s*\(\s*\)")
_SALAW_EN     = _re.compile(r"(Prophet|Messenger)\s*\(\s*\)", _re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _esc_attr(t: str) -> str:
    """HTML-escape for attribute values (escapes &, <, >, \", ')."""
    return _html.escape(str(t), quote=True)


def _esc_text(t: str) -> str:
    """HTML-escape for text content (escapes &, <, > only)."""
    return _html.escape(str(t), quote=False)


def _book_display(raw: str) -> str:
    """Return Bangla name for a book key. Avoids circular import with main."""
    from ui._books import BOOK_BN  # loaded lazily to avoid circular dep
    c = raw.replace(" ", "_")
    if c in BOOK_BN:
        return BOOK_BN[c]
    for k, v in BOOK_BN.items():
        if k.lower() in raw.lower():
            return v
    return raw.replace("_", " ")


# ═══════════════════════════════════════════════════════════════════════════
# html_block — critical helper (fix item 1)
# ═══════════════════════════════════════════════════════════════════════════

def html_block(s: str) -> str:
    """Dedent and strip blank lines so Streamlit Markdown does NOT render the
    string as a code block.

    Streamlit's Markdown treats any line indented 4+ spaces (or text after a
    blank line inside an indented block) as a code block.  This helper removes
    all leading whitespace and empty lines, producing a single-line HTML string
    that Markdown passes through unchanged.

    Usage::

        st.markdown(html_block(snippet), unsafe_allow_html=True)
    """
    lines = s.strip().splitlines()
    parts = [line.strip() for line in lines if line.strip()]
    return "".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# parse_hadith — critical helper (fix item 3)
# ═══════════════════════════════════════════════════════════════════════════

def parse_hadith(text: str, narrator_meta: str = ""):
    """Parse a stored hadith text blob into (narrator, bangla_body, english_body).

    The backend's ``clean_text`` collapses all whitespace, so the stored text is
    typically a single line::

        বর্ণনাকারী: <narrator> <Bangla…> Narrated <name>: <English…>

    Steps:
      1. Remove the leading ``বর্ণনাকারী:`` prefix + narrator string (using
         the ``narrator`` metadata field to cut it exactly).
      2. Split Bangla from English at the first run of 3+ consecutive Latin
         words (typically starting with ``Narrated``).
      3. Display-only: replace empty ``()`` after রাসূল/রসূল/নবী (and
         Prophet/Messenger in English) with ``(ﷺ)``.  Data is never modified.

    Returns:
        (narrator_display, bangla_body, english_body)
    """
    body = text.strip()

    # 1. Remove বর্ণনাকারী: prefix
    if body.startswith("বর্ণনাকারী"):
        rest = body[len("বর্ণনাকারী"):]
        idx = 0
        while idx < len(rest) and rest[idx] in " :\t":
            idx += 1
        body = rest[idx:].strip()

    # 2. Remove narrator string using metadata (exact match at start)
    narrator = narrator_meta.strip()
    if narrator:
        if body.startswith(narrator):
            body = body[len(narrator):].strip()
        else:
            # try whitespace-collapsed match
            bc = _re.sub(r"\s+", " ", body)
            nc = _re.sub(r"\s+", " ", narrator)
            if bc.startswith(nc):
                body = bc[len(nc):].strip()

    # Drop punctuation left at the start after cutting the narrator (e.g. "। ")
    body = body.lstrip(" ।:;,-–—\t").strip()

    # 3. Split Bangla from English at first run of 3+ consecutive Latin words.
    # Use a word-based scan so punctuation between words (colons, parentheses)
    # does not break the chain.  A "Latin word" has ≥1 Latin letter and no
    # Bangla characters.  The English part typically starts with "Narrated".
    bangla_body = body
    english_body = ""
    words = body.split()
    run_start = -1
    run_length = 0
    for i, word in enumerate(words):
        if _is_latin_word(word):
            if run_length == 0:
                run_start = i
            run_length += 1
            if run_length >= 3:
                bangla_part = " ".join(words[:run_start]).strip()
                if bangla_part and _BANGLA_RE.search(bangla_part):
                    bangla_body = bangla_part
                    english_body = " ".join(words[run_start:]).strip()
                break
        else:
            run_length = 0
            run_start = -1

    # If no English found, show everything as Bangla
    if not english_body and not _BANGLA_RE.search(bangla_body):
        # Text is all-English (rare) — show as-is
        bangla_body = body
        english_body = ""

    # 4. Display-only ﷺ replacement
    bangla_body = _SALAW_WORDS.sub(r"\1 (ﷺ)", bangla_body)
    if english_body:
        english_body = _SALAW_EN.sub(r"\1 (ﷺ)", english_body)

    return narrator, bangla_body, english_body


# ═══════════════════════════════════════════════════════════════════════════
# Logo
# ═══════════════════════════════════════════════════════════════════════════

def logo_html(width: str = "min(440px,78vw)") -> str:
    """Return the logo HTML using CSS mask technique (single file, both themes)."""
    mask_url = (
        f"url('data:image/png;base64,{LOGO_MASK_B64}')"
        if LOGO_MASK_B64
        else "none"
    )
    return (
        f'<span class="iq-logo" role="img" aria-label="Bangla Islamic Q&A" '
        f'style="-webkit-mask-image:{mask_url};mask-image:{mask_url};'
        f'background:var(--logo);'
        f'display:block;width:{width};aspect-ratio:1000/128;'
        f'-webkit-mask-size:contain;mask-size:contain;'
        f'-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;'
        f'-webkit-mask-position:center;mask-position:center;'
        f'transition:background-color 0.2s;">'
        f'</span>'
    )


def logo_link_html() -> str:
    """Logo that links back to the Home / new-search page.

    A plain link reloads the app, which starts a fresh session (empty search).
    """
    return html_block(
        '<a class="iq-logo-link" href="?view=chat" target="_self" '
        'aria-label="নতুন অনুসন্ধান">' + logo_html(width="100%") + '</a>'
    )


def summary_source_chips_html(sources: list) -> str:
    """'উৎস: [1] সহীহ বুখারী 597 …' chips under the AI summary."""
    chips = []
    for src in sources or []:
        ref = _esc_text(str(src.get("ref", "")))
        bname = _esc_text(_book_display(str(src.get("book", ""))))
        hid = _esc_text(str(src.get("hadith_id", "?")))
        chips.append(f'<span class="iq-chip"><b>{ref}</b> {bname} {hid}</span>')
    if not chips:
        return ""
    return html_block('<div class="iq-chips"><span class="iq-chips-lbl">উৎস:</span>' + "".join(chips) + '</div>')


# ═══════════════════════════════════════════════════════════════════════════
# Top bar
# ═══════════════════════════════════════════════════════════════════════════

def top_bar(view: str, in_conversation: bool) -> None:
    """Render the 52px top bar with the correct contextual button.

    Uses real ``st.button`` ghost pills (fix item 7).  No border-bottom /
    stray line.  In Hadith Books, "হাদীস গ্রন্থ" sits on the same row as the
    back button.
    """
    if view == "hadith":
        with st.container(key="topbar_hadith"):
            col_back, col_title = st.columns(
                [1, 4], gap="small", vertical_alignment="center"
            )
            with col_back:
                if st.button("অনুসন্ধানে ফিরুন", key="back_to_chat", type="tertiary"):
                    st.session_state["view"] = "chat"
                    # Reset hadith list state so next open starts fresh
                    st.session_state["h_loaded"] = 0
                    st.session_state["h_results"] = []
                    st.session_state["h_query"] = ""
                    try:
                        st.query_params["view"] = "chat"
                    except Exception:
                        pass
                    st.rerun()
            with col_title:
                st.markdown(
                    html_block('<span class="iq-topbar-title">হাদীস গ্রন্থ</span>'),
                    unsafe_allow_html=True,
                )
    # Home state → empty top bar (no button rendered)


# ═══════════════════════════════════════════════════════════════════════════
# Typing dots
# ═══════════════════════════════════════════════════════════════════════════

def typing_dots_html() -> str:
    """Three-dot CSS animation used while waiting for the first stream token."""
    return (
        '<div class="iq-typing" aria-label="উত্তর তৈরি হচ্ছে">'
        '<i></i><i></i><i></i>'
        '</div>'
    )


# ═══════════════════════════════════════════════════════════════════════════
# Cache tag
# ═══════════════════════════════════════════════════════════════════════════

def cached_tag_html() -> str:
    """Small badge shown when an answer came from the query cache."""
    return '<span class="iq-cache-tag">⚡ দ্রুত উত্তর</span>'


# ═══════════════════════════════════════════════════════════════════════════
# Error state
# ═══════════════════════════════════════════════════════════════════════════

def error_state(question: str = "") -> None:
    """Render the AI error state with a Retry button (fix item 7)."""
    st.markdown(
        html_block(
            '<div class="iq-error-box">দুঃখিত, এই মুহূর্তে উত্তর আনা যায়নি।</div>'
        ),
        unsafe_allow_html=True,
    )
    if st.button("আবার চেষ্টা করুন", key="retry", type="secondary"):
        st.session_state["_stream_error"] = False
        st.session_state["_retry_question"] = ""
        # Remove the error assistant message
        hist = st.session_state.get("chat_history", [])
        if hist and hist[-1].get("error"):
            hist.pop()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Skeleton card
# ═══════════════════════════════════════════════════════════════════════════

def skeleton_card_html() -> str:
    """Skeleton placeholder for first-load state."""
    return html_block("""
<div class="hcard-skeleton">
  <div class="skel-line" style="width:40%"></div>
  <div class="skel-line" style="width:90%"></div>
  <div class="skel-line" style="width:75%"></div>
  <div class="skel-line" style="width:60%"></div>
</div>
""")


# ═══════════════════════════════════════════════════════════════════════════
# Copy button HTML (fix item 2 — hidden div, not attribute)
# ═══════════════════════════════════════════════════════════════════════════

def copy_button_html(copy_id: str, text: str) -> str:
    """Return HTML for a copy button with a hidden text div (fix item 2).

    The hadith text is placed in a ``display:none`` div (HTML-escaped) rather
    than in a ``data-`` attribute, so quotes and newlines in the text cannot
    break the markup.  The delegated JS handler reads
    ``document.getElementById(copy_id).textContent``.
    """
    # Newlines as &#10; so html_block (which joins lines) keeps them; the
    # browser decodes them back to "\n" in textContent.
    escaped = _esc_text(text).replace("\r\n", "\n").replace("\n", "&#10;")
    return html_block(f"""
<div id="{_esc_attr(copy_id)}" style="display:none">{escaped}</div>
<button class="act copy-btn" data-copy-id="{_esc_attr(copy_id)}"
        aria-label="হাদীস কপি করুন" type="button">কপি</button>
""")


# ═══════════════════════════════════════════════════════════════════════════
# Hadith card — header + body HTML (used inside st.container)
# ═══════════════════════════════════════════════════════════════════════════

def hadith_card_header_body_html(h: dict, label: str = "", clamp: bool = False) -> str:
    """Return just the header + body HTML for a hadith card.

    Does NOT include the footer (narrator / copy / ask) — those are rendered
    as separate Streamlit widgets inside the container so the Ask button is
    a real ``st.button`` (fix item 4).
    """
    bname    = _book_display(h.get("book", "Unknown"))
    hid      = h.get("hadith_id", "?")
    grade    = (h.get("grade") or "").strip()
    meta_nar = (h.get("narrator") or "").strip()
    text     = h.get("text", "")

    # Parse hadith text (fix item 3)
    narrator, bn_body, en_body = parse_hadith(text, meta_nar)

    # Reference line parts
    ref_parts = []
    if label:
        ref_parts.append(f'<span class="hcard-label">{_esc_text(label)}</span>')
    ref_parts.append(f'<b>{_esc_text(bname)}</b>')
    ref_parts.append(f'<span>· হাদীস {_esc_text(str(hid))}</span>')
    if grade:
        ref_parts.append(f'<span class="grade">{_esc_text(grade)}</span>')

    body_parts = [f'<div class="hcard-ref">{"".join(ref_parts)}</div>']

    # Arabic block only if Arabic characters actually exist
    if _ARABIC_RE.search(text):
        # Extract Arabic text (rare — DB normally strips it)
        ar_parts = []
        for line in text.splitlines():
            s = line.strip()
            if s and _ARABIC_RE.search(s) and len(_ARABIC_RE.findall(s)) / max(len(s), 1) > 0.4:
                ar_parts.append(s)
        if ar_parts:
            body_parts.append(
                f'<p class="ar" dir="rtl" lang="ar">{_esc_text(" ".join(ar_parts))}</p>'
            )

    if clamp:
        # Search results: show the start, put the rest behind "আরও পড়ুন".
        limit = 230
        if len(bn_body) > limit + 40:
            cut = bn_body.rfind(" ", 0, limit)
            cut = cut if cut > limit // 2 else limit
            head, rest = bn_body[:cut].rstrip(), bn_body[cut:].strip()
            body_parts.append(f'<p class="bn">{_esc_text(head)}…</p>')
            more = f'<p class="bn">{_esc_text(rest)}</p>'
            if en_body:
                more += f'<p class="en" lang="en">{_esc_text(en_body)}</p>'
            body_parts.append(
                '<details class="hmore"><summary>আরও পড়ুন</summary>' + more + '</details>'
            )
            return html_block("".join(body_parts))
    # Bangla body
    if bn_body:
        body_parts.append(f'<p class="bn">{_esc_text(bn_body)}</p>')

    # English body (quieter style, fix item 3)
    if en_body:
        body_parts.append(f'<p class="en" lang="en">{_esc_text(en_body)}</p>')

    return html_block("".join(body_parts))


# ═══════════════════════════════════════════════════════════════════════════
# Hadith card — full card as a Streamlit container (fix items 1,2,3,4)
# ═══════════════════════════════════════════════════════════════════════════

def hadith_card(
    h: dict,
    label: str = "",
    flash: bool = False,
    ask_key: str = "",
    uid: str = "",
    clamp: bool = False,
) -> None:
    """Render a full Hadith Card as a ``st.container`` (fix item 4).

    Inside the container:
      - header HTML (book, hadith number, grade)
      - body HTML (Bangla + English)
      - footer row ``st.columns([3, 1, 2])``:
          narrator (muted 13px) · Copy (HTML button) · Ask (``st.button``)

    The container key is ``hcard_<book>_<id>`` so CSS can target
    ``[class*="st-key-hcard_"]`` for card styling (radius 20, etc.).
    """
    bname    = _book_display(h.get("book", "Unknown"))
    hid      = h.get("hadith_id", "?")
    meta_nar = (h.get("narrator") or "").strip()
    text     = h.get("text", "")

    narrator, bn_body, en_body = parse_hadith(text, meta_nar)

    # Narrator display (shown once, in the footer only — fix item 3)
    narrator_display = narrator or meta_nar
    if narrator_display and not narrator_display.startswith("বর্ণনাকারী"):
        narrator_display = f"বর্ণনাকারী: {narrator_display}"
    narrator_display = narrator_display[:120] if narrator_display else ""

    # Copy text: body + book reference (fix item 9 in matrix)
    copy_text = bn_body
    if en_body:
        copy_text += f"\n\n{en_body}"
    copy_text += f"\n\n{bname}, হাদীস {hid}"

    book_key = str(h.get("book", "")).replace(" ", "_")
    # ``uid`` makes keys unique when the same hadith shows in several answers
    sfx = f"_{uid}" if uid else ""
    copy_id  = f"copy_{book_key}_{hid}{sfx}"

    container_key = f"hcard_{book_key}_{hid}{sfx}"
    if flash:
        container_key = f"hcard_jump_{book_key}_{hid}{sfx}"  # avoid duplicate key

    with st.container(border=True, key=container_key):
        # Header + body HTML (fix item 1 — html_block prevents code block)
        st.markdown(
            hadith_card_header_body_html(h, label=label, clamp=clamp),
            unsafe_allow_html=True,
        )

        # Footer row: narrator · Copy · Ask (fix item 4)
        # Narrator gets its own full-width line so the buttons can never overlap it.
        if narrator_display:
            st.markdown(
                html_block(
                    f'<div class="narr">{_esc_text(narrator_display)}</div>'
                ),
                unsafe_allow_html=True,
            )
        # Both actions in one keyed row (styled by [class*="st-key-hfoot_"]):
        # right-aligned, vertically centred, same pill size in both themes.
        with st.container(key="hfoot" + container_key[len("hcard"):]):
            f_copy, f_ask = st.columns(2, gap="small", vertical_alignment="center")
            with f_copy:
                st.markdown(
                    copy_button_html(copy_id, copy_text),
                    unsafe_allow_html=True,
                )
            with f_ask:
                if ask_key and st.button(
                    "AI-কে জিজ্ঞেস করুন",
                    key=ask_key,
                    type="secondary",
                ):
                    _trigger_ask(h)

    # Flash animation for number-jump (fix item 14)
    if flash:
        import streamlit.components.v1 as _cv1
        _cv1.html(
            f"""
<script>
(function() {{
  var pd = window.parent.document;
  var cards = pd.querySelectorAll('[class*="st-key-{container_key}"]');
  if (cards.length > 0) {{
    var card = cards[cards.length - 1];
    card.classList.add('hcard--flash');
    card.addEventListener('animationend', function() {{
      card.classList.remove('hcard--flash');
    }}, {{ once: true }});
  }}
}})();
</script>
            """,
            height=0,
        )


def _trigger_ask(h: dict) -> None:
    """Handle the 'AI-কে জিজ্ঞেস করুন' button click.

    Runs a search for "<বই> <নম্বর> নম্বর হাদীসটির ব্যাখ্যা কী?" and opens the
    AI summary for it right away.
    """
    bname = _book_display(h.get("book", ""))
    hid = h.get("hadith_id", "?")
    st.session_state["_do_search"] = f"{bname} {hid} নম্বর হাদীসটির ব্যাখ্যা কী?"
    st.session_state["_auto_summary"] = True
    st.session_state["view"] = "chat"
    try:
        st.query_params["view"] = "chat"
    except Exception:
        pass
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Source cards (fix item 4, 11)
# ═══════════════════════════════════════════════════════════════════════════

def source_cards(sources: list, uid: str = "") -> None:
    """Render source cards under an AI answer.

    Shows the first 3 inline; wraps the rest in an ``st.expander`` (matrix
    row 8: "আরও N টি সূত্র দেখুন" toggle).
    """
    if not sources:
        return

    def _build_h(src: dict, idx: int) -> dict:
        return {
            "hadith_id": src.get("hadith_id", "?"),
            "book":      src.get("book", "Unknown"),
            "narrator":  src.get("narrator", ""),
            "grade":     src.get("grade", "") or "",
            "text":      src.get("text", src.get("core", "")),
        }

    visible = sources[:3]
    hidden  = sources[3:]

    for i, src in enumerate(visible):
        h = _build_h(src, i)
        ref = src.get("ref", f"[{i + 1}]")
        book_key = str(h.get("book", "")).replace(" ", "_")
        ask_key = f"ask_{book_key}_{h.get('hadith_id', '?')}" + (f"_{uid}" if uid else "")
        hadith_card(h, label=ref + " ", flash=False, ask_key=ask_key, uid=uid)

    if hidden:
        with st.expander(f"আরও {len(hidden)} টি সূত্র দেখুন", expanded=False):
            for i, src in enumerate(hidden, start=3):
                h = _build_h(src, i)
                ref = src.get("ref", f"[{i + 1}]")
                book_key = str(h.get("book", "")).replace(" ", "_")
                ask_key = f"ask_{book_key}_{h.get('hadith_id', '?')}" + (f"_{uid}" if uid else "")
                hadith_card(h, label=ref + " ", flash=False, ask_key=ask_key, uid=uid)


# ═══════════════════════════════════════════════════════════════════════════
# Feedback row (fix item 6, 9 — no emoji, line-icon buttons)
# ═══════════════════════════════════════════════════════════════════════════

def _on_feedback_click(msg_idx: int, vote: str, user_q: str, answer: str,
                       sources: list, log_vote_fn) -> None:
    """on_click callback: runs BEFORE the rerun, so the vote is never lost.

    Records the vote in session state, the JSONL feedback log, and the
    anonymous SQLite query log (row id kept in chat_log_ids[msg_idx]).
    """
    votes = st.session_state.setdefault("feedback_votes", {})
    if votes.get(msg_idx) is not None:
        return  # already voted; ignore duplicate clicks
    votes[msg_idx] = vote
    try:
        log_vote_fn(
            question=user_q, answer=answer, vote=vote,
            sources=sources, search_mode="hybrid",
        )
    except Exception:
        pass
    try:
        from query_logger import save_feedback
        log_id = st.session_state.get("chat_log_ids", {}).get(msg_idx)
        if log_id is not None and log_id >= 0:
            save_feedback(log_id, vote)
    except Exception:
        pass
    st.toast("ধন্যবাদ, মতামত জমা হয়েছে")


def feedback_row(msg_idx: int, msg: dict, sources: list, log_vote_fn) -> None:
    """Render 👍 / 👎 feedback buttons under an AI answer.

    Rendered from the stored chat history (outside the question-handling
    block), with on_click callbacks, so a click is processed before the page
    reruns and the answer never disappears. Each answer accepts one vote.
    """
    # Only show feedback on complete, non-error answers
    if msg.get("error") or not msg.get("content"):
        return

    votes = st.session_state.setdefault("feedback_votes", {})
    current_vote = votes.get(msg_idx)
    voted = current_vote is not None

    # Find the user question (the message just before this assistant message)
    hist = st.session_state.get("chat_history", [])
    user_q = ""
    for i in range(msg_idx - 1, -1, -1):
        if i < len(hist) and hist[i].get("role") == "user":
            user_q = hist[i].get("content", "")
            break

    col_up, col_down, _spacer = st.columns([3, 3, 4])

    with col_up:
        up_selected = current_vote == "up"
        st.button(
            "সহায়ক" + (" ✓" if up_selected else ""),
            key=f"vote_up_{msg_idx}_selected" if up_selected else f"vote_up_{msg_idx}",
            help="উত্তরটি সহায়ক",
            type="primary" if up_selected else "secondary",
            on_click=_on_feedback_click,
            args=(msg_idx, "up", user_q, msg["content"], sources, log_vote_fn),
            disabled=voted,
        )

    with col_down:
        down_selected = current_vote == "down"
        st.button(
            "সহায়ক নয়" + (" ✓" if down_selected else ""),
            key=f"vote_down_{msg_idx}_selected" if down_selected else f"vote_down_{msg_idx}",
            help="উত্তরটি সহায়ক নয়",
            type="primary" if down_selected else "secondary",
            on_click=_on_feedback_click,
            args=(msg_idx, "down", user_q, msg["content"], sources, log_vote_fn),
            disabled=voted,
        )
