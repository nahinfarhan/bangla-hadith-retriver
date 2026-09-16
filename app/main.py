import re as _re
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

# ─────────────────────────────────────────────────────────────────────────────
# Language helpers
# ─────────────────────────────────────────────────────────────────────────────
_BANGLA_RE = _re.compile(r"[\u0980-\u09FF]")

def is_bangla(text: str) -> bool:
    return bool(_BANGLA_RE.search(text))

def extract_display_text(full_text: str, bangla_query: bool) -> str:
    lines = full_text.splitlines()
    if bangla_query:
        kept = [l for l in lines if _BANGLA_RE.search(l) or not l.strip()]
        result = "\n".join(kept).strip()
    else:
        en_lines = []
        for l in lines:
            s = l.strip()
            if not s or s.startswith("বর্ণনাকারী"):
                continue
            if len(_BANGLA_RE.findall(s)) / max(len(s), 1) < 0.2:
                en_lines.append(s)
        result = "\n".join(en_lines).strip()
    return result if result else full_text

def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def book_display(raw: str) -> str:
    return raw.replace("_", " ").replace("Sahih ", "Ṣaḥīḥ ")

def similarity_badge(score: float) -> str:
    cls = "badge-high" if score >= 75 else ("badge-mid" if score >= 55 else "badge-low")
    return f'<span class="result-badge {cls}">● {score:.1f}%</span>'


# ─────────────────────────────────────────────────────────────────────────────
# Theme CSS
# ─────────────────────────────────────────────────────────────────────────────
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@300;400;500;600;700&family=Cinzel:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{font-family:'Inter','Noto Sans Bengali',sans-serif!important}

.stApp{
  background:
    radial-gradient(ellipse at 20% 20%, rgba(120,80,255,.18) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(20,150,220,.15) 0%, transparent 50%),
    linear-gradient(160deg,#070714 0%,#0c0c2a 35%,#08101e 70%,#0a0a1a 100%)!important;
  min-height:100vh!important}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:1.25rem!important;padding-bottom:3rem!important;max-width:1200px!important}

[data-testid="stSidebar"]{
  background:rgba(8,6,28,.85)!important;
  backdrop-filter:blur(24px)!important;
  -webkit-backdrop-filter:blur(24px)!important;
  border-right:1px solid rgba(180,140,255,.14)!important;
  box-shadow:4px 0 40px rgba(0,0,0,.6)!important}

/* Streamlit 1.58 sidebar inner div hierarchy */
[data-testid="stSidebar"]>div,
[data-testid="stSidebar"]>div>div,
[data-testid="stSidebar"] section,
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"]>div{
  background:transparent!important}

/* Force all sidebar text to be visible */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3{
  color:#c4b5fd!important}

[data-testid="stSidebar"] [data-testid="stMetricValue"]{color:#e2d9ff!important;font-size:1.4rem!important}
[data-testid="stSidebar"] [data-testid="stMetricLabel"]{color:#8b7bb5!important}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]{
  background:rgba(167,139,250,.06)!important;
  border:1px dashed rgba(167,139,250,.3)!important;
  border-radius:10px!important}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] p,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span{
  color:#8b7bb5!important}
/* Sidebar scrollbar */
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb{
  background:rgba(167,139,250,.25)!important}

.fancy-divider{height:1px;background:linear-gradient(90deg,transparent,rgba(200,160,80,.4),rgba(167,139,250,.5),rgba(200,160,80,.4),transparent);margin:1.25rem 0}

.hero-banner{
  background:radial-gradient(ellipse at 50% 0%,rgba(200,160,50,.12) 0%,transparent 60%),linear-gradient(135deg,rgba(30,20,70,.8) 0%,rgba(50,40,130,.6) 50%,rgba(20,50,90,.8) 100%);
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border:1px solid rgba(200,160,50,.3);border-radius:20px;
  padding:2.75rem 2rem 2.25rem;margin-bottom:2rem;text-align:center;
  position:relative;overflow:hidden;
  box-shadow:0 8px 40px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.05)}
.hero-banner::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,rgba(200,160,50,.8),rgba(255,215,100,.9),rgba(200,160,50,.8),transparent)}
.hero-banner::after{content:'';position:absolute;top:-60%;left:-50%;width:200%;height:200%;
  background:radial-gradient(ellipse at center,rgba(167,139,250,.06) 0%,transparent 60%);
  animation:pulse-glow 5s ease-in-out infinite;pointer-events:none}
@keyframes pulse-glow{0%,100%{opacity:.4;transform:scale(.95)}50%{opacity:1;transform:scale(1.05)}}
.hero-title{
  font-family:'Cinzel','Inter',serif!important;font-size:2.2rem;font-weight:700;
  background:linear-gradient(135deg,#f0c060,#a78bfa,#60c0f0,#a78bfa,#f0c060);background-size:300% 300%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  margin:0 0 .5rem;position:relative;z-index:1;animation:shimmer 6s ease-in-out infinite}
@keyframes shimmer{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.hero-arabic{font-size:1.3rem;color:rgba(200,160,50,.8);letter-spacing:.1em;margin-bottom:.4rem;position:relative;z-index:1}
.hero-subtitle{color:#94a3b8;font-size:.95rem;position:relative;z-index:1}

.stat-row{display:flex;gap:.65rem;flex-wrap:wrap;margin-bottom:1.5rem}
.stat-pill{background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.2);border-radius:50px;padding:.35rem .9rem;font-size:.82rem;color:#c4b5fd;font-weight:500;backdrop-filter:blur(6px)}

.result-card{
  background:rgba(255,255,255,.04);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border:1px solid rgba(255,255,255,.08);border-radius:16px;
  padding:1.25rem 1.5rem;margin-bottom:.85rem;transition:all .25s ease;position:relative;overflow:hidden}
.result-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(200,160,50,.3),transparent);opacity:0;transition:opacity .25s}
.result-card:hover{border-color:rgba(167,139,250,.35);background:rgba(255,255,255,.06);
  box-shadow:0 4px 20px rgba(0,0,0,.3);transform:translateY(-1px)}
.result-card:hover::before{opacity:1}
.result-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:.75rem;flex-wrap:wrap;gap:.5rem}
.result-badge{display:inline-flex;align-items:center;gap:.35rem;font-size:.8rem;font-weight:600;padding:.25rem .75rem;border-radius:50px;backdrop-filter:blur(8px)}
.badge-high{background:rgba(16,185,129,.15);color:#34d399;border:1px solid rgba(16,185,129,.35);box-shadow:0 0 10px rgba(16,185,129,.2)}
.badge-mid{background:rgba(245,158,11,.12);color:#fbbf24;border:1px solid rgba(245,158,11,.3)}
.badge-low{background:rgba(249,115,22,.12);color:#fb923c;border:1px solid rgba(249,115,22,.3)}
.result-meta{display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:.85rem}
.meta-tag{font-size:.73rem;color:#64748b;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);padding:.2rem .6rem;border-radius:6px}
.meta-tag span{color:#94a3b8;font-weight:500}
.hadith-body{
  font-family:'Noto Sans Bengali','Kalpurush',sans-serif!important;
  font-size:.97rem;line-height:2.1;color:#ddd6fe;
  padding:1rem 1.25rem;background:rgba(0,0,0,.25);
  border-left:3px solid rgba(200,160,50,.5);border-radius:0 10px 10px 0;
  white-space:pre-wrap;word-break:break-word;overflow:visible}

.chat-answer{
  background:rgba(100,50,200,.07);border:1px solid rgba(124,58,237,.2);
  backdrop-filter:blur(12px);border-radius:16px 16px 16px 4px;
  padding:1.25rem 1.5rem;margin-bottom:1rem;
  font-family:'Noto Sans Bengali','Inter',sans-serif!important;
  font-size:1rem;line-height:1.95;color:#e2e8f0;white-space:pre-wrap}
.chat-user{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);
  backdrop-filter:blur(8px);border-radius:16px 16px 4px 16px;
  padding:.75rem 1.1rem;margin-bottom:.5rem;font-size:.95rem;color:#cbd5e1;text-align:right}
.chat-bot-wrap{margin-bottom:1.75rem}
.source-strip{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.75rem}
.src-chip{display:inline-flex;align-items:center;gap:.3rem;background:rgba(167,139,250,.08);
  border:1px solid rgba(167,139,250,.25);border-radius:50px;padding:.2rem .75rem;
  font-size:.73rem;color:#c4b5fd;cursor:pointer;transition:all .2s;backdrop-filter:blur(6px)}
.src-chip:hover{background:rgba(167,139,250,.2);border-color:rgba(167,139,250,.5)}
.source-hadith{background:rgba(16,185,129,.04);border:1px solid rgba(16,185,129,.15);border-radius:12px;padding:1rem 1.25rem;margin:.5rem 0 1rem}

.stTextInput input,[data-testid="stNumberInputField"],[data-baseweb="input"] input{
  background:rgba(255,255,255,.04)!important;border:1px solid rgba(167,139,250,.3)!important;
  border-radius:10px!important;color:#e2e8f0!important;caret-color:#a78bfa!important;
  font-size:.95rem!important;font-family:'Noto Sans Bengali','Inter',sans-serif!important;
  padding:.65rem 1rem!important;transition:border-color .2s,box-shadow .2s,background .2s!important}
.stTextInput input:focus,[data-testid="stNumberInputField"]:focus{
  border-color:#a78bfa!important;background:rgba(255,255,255,.07)!important;box-shadow:0 0 0 3px rgba(167,139,250,.12)!important}
[data-testid="stNumberInputContainer"]{background:rgba(255,255,255,.04)!important;border:1px solid rgba(167,139,250,.3)!important;border-radius:10px!important}
[data-testid="stNumberInput"] button{color:#a78bfa!important}
[data-testid="stSelectbox"]>div>div{background:rgba(255,255,255,.04)!important;border:1px solid rgba(167,139,250,.3)!important;border-radius:10px!important;color:#e2e8f0!important}
div[data-testid="stColumn"]:has(>.stVerticalBlock>.stElementContainer>.stButton){display:flex!important;flex-direction:column!important;justify-content:flex-end!important}
.stButton>button{background:linear-gradient(135deg,#7c3aed,#4f46e5)!important;color:#fff!important;border:none!important;border-radius:10px!important;font-weight:600!important;font-size:.9rem!important;box-shadow:0 4px 15px rgba(124,58,237,.3)!important;transition:all .2s!important;height:42px!important}
.stButton>button:hover{opacity:.9!important;transform:translateY(-1px)!important;box-shadow:0 6px 20px rgba(124,58,237,.45)!important}
.stButton>button[kind="secondary"]{background:rgba(255,255,255,.06)!important;box-shadow:none!important;border:1px solid rgba(255,255,255,.1)!important}
[data-testid="stRadio"] label{color:#94a3b8!important}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;backdrop-filter:blur(10px)!important;border-radius:12px!important;padding:4px!important;gap:4px!important;border-bottom:none!important;border:1px solid rgba(255,255,255,.06)!important}
.stTabs [data-baseweb="tab"]{border-radius:9px!important;font-weight:500!important;padding:.5rem 1.25rem!important;background:transparent!important;border:none!important;color:#64748b!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#7c3aed,#4f46e5)!important;color:#fff!important;box-shadow:0 2px 12px rgba(124,58,237,.4)!important}
.stTabs [data-baseweb="tab-panel"]{padding-top:1.5rem!important}
[data-testid="stMetricValue"]{color:#a78bfa!important;font-size:1.5rem!important}
[data-testid="stMetricLabel"]{color:#64748b!important}
[data-testid="stProgressBar"]>div{background:linear-gradient(90deg,#7c3aed,#a78bfa,#38bdf8)!important;border-radius:4px!important}
[data-testid="stExpander"]{background:rgba(255,255,255,.03)!important;border:1px solid rgba(255,255,255,.07)!important;border-radius:10px!important}
[data-testid="stExpander"] summary{color:#94a3b8!important}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:linear-gradient(180deg,rgba(167,139,250,.4),rgba(56,189,248,.3));border-radius:3px}
.section-label{font-size:.68rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#4a4470;margin-bottom:.75rem}
.lookup-result{background:rgba(16,185,129,.04);border:1px solid rgba(16,185,129,.18);backdrop-filter:blur(10px);border-radius:14px;padding:1.25rem 1.5rem;margin-top:.75rem}
.empty-state{text-align:center;padding:3rem 2rem}
.empty-state .icon{font-size:3.5rem;margin-bottom:.75rem;filter:drop-shadow(0 0 12px rgba(167,139,250,.4))}
.empty-state p{font-size:.95rem;color:#3d3660;line-height:1.6}
.sidebar-brand{text-align:center;padding:1.5rem .5rem 1rem}
.sidebar-brand .mosque-icon{font-size:3rem;filter:drop-shadow(0 0 16px rgba(200,160,50,.5));display:block;margin-bottom:.5rem}
.sidebar-brand .app-name{font-family:'Cinzel',serif!important;font-size:1.15rem;font-weight:600;background:linear-gradient(135deg,#f0c060,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.sidebar-brand .app-sub{font-size:.72rem;color:#4a4470;letter-spacing:.08em;margin-top:.2rem}

/* ── Native sidebar collapse button — hidden (we use custom ☰ toggle instead) */
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
button[kind="header"][aria-label="Close sidebar"],
button[aria-label="Close sidebar"],
[data-testid="stSidebar"] button[kind="header"]{
  display:none!important;visibility:hidden!important}
.book-pill{display:inline-block;background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.2);border-radius:50px;padding:.2rem .65rem;font-size:.71rem;color:#9d8fd4;margin:.15rem}
.ai-status-on{display:flex;align-items:center;gap:.4rem;background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.2);border-radius:8px;padding:.4rem .75rem;font-size:.75rem;color:#34d399}
.ai-status-warn{display:flex;align-items:center;gap:.4rem;background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.2);border-radius:8px;padding:.4rem .75rem;font-size:.75rem;color:#fbbf24}
.ai-status-off{display:flex;align-items:center;gap:.4rem;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:8px;padding:.4rem .75rem;font-size:.75rem;color:#f87171}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hadith QA · Islamic Knowledge Search",
    page_icon="🕌", layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(THEME_CSS, unsafe_allow_html=True)

# Clear any stored collapsed state so sidebar always opens
st.markdown("""
<script>
(function() {
  try {
    // Remove Streamlit's stored sidebar state so it always opens expanded
    const keys = Object.keys(localStorage);
    keys.forEach(k => {
      if (k.includes('sidebar') || k.includes('Sidebar')) {
        localStorage.removeItem(k);
      }
    });
    // Also clear sessionStorage
    const skeys = Object.keys(sessionStorage);
    skeys.forEach(k => {
      if (k.includes('sidebar') || k.includes('Sidebar')) {
        sessionStorage.removeItem(k);
      }
    });
  } catch(e) {}
})();
</script>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Cached loaders
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_hadith_engine():
    app_dir = str(Path(__file__).parent.absolute())
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    from hybrid_search import HybridHadithSearch
    db_path = str(Path(__file__).parent.parent / "data" / "hadith_vectors")
    return HybridHadithSearch(hadith_db_path=db_path, use_reranker=True)

@st.cache_resource(show_spinner=False)
def load_doc_components():
    from ingest import DocumentIngestor
    from embed import EmbeddingModel
    from vector_store import VectorStore
    from search import SearchEngine
    vs = VectorStore(); em = EmbeddingModel()
    di = DocumentIngestor(); se = SearchEngine(vs, em)
    return vs, em, di, se


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar(hadith_stats):
    with st.sidebar:
        st.markdown("""
<div class="sidebar-brand">
  <span class="mosque-icon">🕌</span>
  <div class="app-name">Hadith QA</div>
  <div class="app-sub">✦ Islamic Knowledge Search ✦</div>
</div>""", unsafe_allow_html=True)
        st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
        if hadith_stats:
            total = hadith_stats.get("total_hadiths", 0)
            avg   = hadith_stats.get("avg_words_per_hadith", 0)
            books = hadith_stats.get("books", [])
            st.markdown('<p class="section-label">📊 Hadith Database</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("Hadiths", f"{total:,}")
            c2.metric("Avg Words", avg)
            if books:
                pills = "".join(
                    f'<span class="book-pill">{book_display(b)}</span>' for b in books)
                st.markdown(f'<div style="margin-top:.5rem;">{pills}</div>', unsafe_allow_html=True)
        st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

        import os as _os
        _env_keys = _os.environ.get("GEMINI_API_KEYS", "") or _os.environ.get("GEMINI_API_KEY", "")
        _key_count = len([k for k in _env_keys.replace("\n", ",").split(",") if k.strip()]) if _env_keys else 0
        if _key_count:
            try:
                from gemini_client import get_active_key_count
                active_count = get_active_key_count(_env_keys)
                if active_count == _key_count:
                    st.markdown(f'<div class="ai-status-on">🤖 AI powered · {_key_count} key(s) active</div>', unsafe_allow_html=True)
                elif active_count > 0:
                    st.markdown(f'<div class="ai-status-warn">⚠️ {active_count}/{_key_count} keys active</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="ai-status-off">❌ All keys exhausted</div>', unsafe_allow_html=True)
            except Exception:
                st.markdown(f'<div class="ai-status-on">🤖 {_key_count} key(s) configured</div>', unsafe_allow_html=True)
            gemini_keys_raw = _env_keys
        else:
            gemini_keys_raw = ""
            st.markdown('<div class="ai-status-off">⚠️ No Gemini keys configured</div>', unsafe_allow_html=True)
        st.session_state["gemini_keys_raw"] = gemini_keys_raw

        st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-label">📄 Upload Documents</p>', unsafe_allow_html=True)
        return st.file_uploader("PDF or TXT", type=["pdf","txt"],
                                accept_multiple_files=True, label_visibility="collapsed")


# ─────────────────────────────────────────────────────────────────────────────
# Hadith card
# ─────────────────────────────────────────────────────────────────────────────
def _sigmoid(x: float) -> float:
    """Sigmoid function to map cross-encoder logits to [0, 1]."""
    import math
    return 1.0 / (1.0 + math.exp(-x))


def render_hadith_card(hadith: dict, idx: int, bangla_query: bool,
                       score_override: float = None, score_label: str = None):
    rerank_raw   = hadith.get("rerank_score")   # raw cross-encoder logit (unbounded)
    dense_sim    = hadith.get("similarity", 0)  # dense embedding similarity %
    rrf_score    = hadith.get("rrf_score", 0)   # RRF fusion score (×1000)

    if score_override is not None:
        display_score = score_override
        label = score_label or "score"
        extra_scores = ""
    elif rerank_raw is not None:
        # Sigmoid-normalise the raw logit → meaningful [0–100]% probability
        display_score = _sigmoid(rerank_raw) * 100
        label = "hybrid"
        # Sub-scores shown in meta row
        extra_scores = (
            f'<span class="meta-tag" title="Dense embedding similarity">💠 <span>{dense_sim:.1f}%</span></span>'
            f'<span class="meta-tag" title="RRF fusion score">⚡ <span>{rrf_score:.2f}</span></span>'
        )
    else:
        display_score = dense_sim
        label = "sim"
        extra_scores = ""

    book     = book_display(hadith.get("book", "Unknown"))
    hid      = hadith.get("hadith_id", "?")
    words    = hadith.get("word_count", 0)
    grade    = hadith.get("grade", "")
    narrator = hadith.get("narrator", "")
    raw_text = hadith.get("text", "")
    display  = extract_display_text(raw_text, bangla_query)
    badge    = similarity_badge(display_score)

    meta = (f'<span class="meta-tag">📚 <span>{_esc(book)}</span></span>'
            f'<span class="meta-tag"># <span>{_esc(str(hid))}</span></span>'
            f'<span class="meta-tag">📝 <span>{words} w</span></span>'
            f'{extra_scores}')
    if grade:
        meta += f'<span class="meta-tag">⭐ <span>{_esc(grade)}</span></span>'
    if narrator:
        short = narrator[:55]+"…" if len(narrator)>55 else narrator
        meta += f'<span class="meta-tag">👤 <span>{_esc(short)}</span></span>'

    # Badge label suffix
    badge_label = f'<span style="color:#64748b;font-size:.72rem;margin-left:.3rem;">{label}</span>'

    with st.container():
        st.markdown(
            f'<div class="result-card">'
            f'<div class="result-header">'
            f'<span style="color:#94a3b8;font-size:.8rem;font-weight:600">#{idx}</span>'
            f'{badge}{badge_label}'
            f'</div>'
            f'<div class="result-meta">{meta}</div>'
            f'<div class="hadith-body">{_esc(display)}</div>'
            f'</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — Hadith Search
# ─────────────────────────────────────────────────────────────────────────────
def hadith_search_tab(engine):
    st.markdown('<p class="section-label">🔍 Semantic Search</p>', unsafe_allow_html=True)

    # ── Search mode selector ──────────────────────────────────────────────────
    search_mode = st.radio(
        "search_mode",
        options=["🚀 Hybrid  (BM25 + Dense + RRF + Re-rank)", "⚡ Simple  (Dense only)"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
        key="hadith_search_mode",
    )
    use_hybrid = search_mode.startswith("🚀")
    st.markdown(
        f'<p style="color:#64748b;font-size:.75rem;margin-top:-.5rem;margin-bottom:.75rem;">'
        f'{"BM25 · Dense · RRF · Cross-Encoder re-ranking · Query reframing" if use_hybrid else "Fine-tuned e5 bi-encoder · Query reframing · Fast"}'
        f'</p>',
        unsafe_allow_html=True,
    )

    query = st.text_input("q", placeholder="নামাজ সম্পর্কে হাদিস  ·  Search for prayer, fasting …",
                          label_visibility="collapsed", key="hadith_query")
    col_k, col_btn = st.columns([1, 3])
    with col_k:
        top_k = st.number_input("k", min_value=5, max_value=30, value=15,
                                label_visibility="collapsed", key="hadith_k")
    with col_btn:
        go = st.button("🔍  Search Hadiths", type="primary",
                       use_container_width=True, key="hadith_go")

    if go and query.strip():
        bangla = is_bangla(query)
        spinner_msg = "Searching (hybrid pipeline)…" if use_hybrid else "Searching…"
        with st.spinner(spinner_msg):
            try:
                gemini_keys = st.session_state.get("gemini_keys_raw", "")
                if use_hybrid:
                    results = engine.search_hadiths(
                        query.strip(), top_k=int(top_k),
                        use_reframing=True, extra_keys_raw=gemini_keys)
                else:
                    # Simple dense-only: use HadithSearchEngine directly
                    from hadith_search import HadithSearchEngine
                    if "simple_engine" not in st.session_state:
                        st.session_state["simple_engine"] = HadithSearchEngine()
                    results = st.session_state["simple_engine"].search_hadiths(
                        query.strip(), top_k=int(top_k),
                        use_reframing=True, extra_keys_raw=gemini_keys)
            except Exception as e:
                st.error(f"Search failed: {e}"); return

        if not results:
            st.markdown('<div class="empty-state"><div class="icon">🔭</div>'
                        '<p>No hadiths matched. Try different keywords.</p></div>',
                        unsafe_allow_html=True)
        else:
            lang      = "বাংলা" if bangla else "English"
            retrieval = results[0].get("_retrieval", "dense") if results else "dense"
            st.markdown(f'<div class="stat-row">'
                        f'<span class="stat-pill">✨ {len(results)} results</span>'
                        f'<span class="stat-pill">🌐 {_esc(lang)}</span>'
                        f'<span class="stat-pill">🔍 &ldquo;{_esc(query[:55])}&rdquo;</span>'
                        f'<span class="stat-pill">⚙️ {_esc(retrieval)}</span>'
                        f'</div>', unsafe_allow_html=True)
            for i, h in enumerate(results, 1):
                render_hadith_card(h, i, bangla)
    elif not go:
        st.markdown('<div class="empty-state"><div class="icon">🕌</div>'
                    '<p>Enter a query to search across <strong style="color:#a78bfa">20,505 hadiths</strong><br>'
                    'in Bangla or English · Bukhari · Muslim · Tirmidhi</p></div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-label">🔢 Direct Lookup by Number</p>', unsafe_allow_html=True)

    BOOKS = {"Ṣaḥīḥ al-Bukhārī":"Sahih_Bukhari",
             "Ṣaḥīḥ Muslim":"Sahih_Muslim",
             "Jāmiʿ at-Tirmidhī":"Jami_at_Tirmidhi"}
    col_b, col_n, col_lb = st.columns([3, 2, 2])
    with col_b:
        book_label = st.selectbox("book", list(BOOKS.keys()),
                                  label_visibility="collapsed", key="lookup_book")
    with col_n:
        lookup_num = st.number_input("num", min_value=1, max_value=10000, value=1,
                                     label_visibility="collapsed", key="lookup_num")
    with col_lb:
        go2 = st.button("🔍  Lookup", type="primary",
                        use_container_width=True, key="lookup_go")

    if go2:
        with st.spinner(""):
            try:
                result = engine.get_hadith_by_number(int(lookup_num), book=BOOKS[book_label])
            except Exception as e:
                st.error(f"Lookup failed: {e}"); return
        if result:
            raw = result.get("text","")
            st.markdown(
                f'<div class="lookup-result">'
                f'<div class="result-meta" style="margin-bottom:.75rem;">'
                f'<span class="meta-tag">📚 <span>{_esc(book_label)}</span></span>'
                f'<span class="meta-tag"># <span>{lookup_num}</span></span>'
                f'</div>'
                f'<div class="hadith-body">{_esc(raw)}</div>'
                f'</div>', unsafe_allow_html=True)
        else:
            st.warning(f"Hadith #{lookup_num} not found in {book_label}.")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — Hadith Companion (Chat)
# ─────────────────────────────────────────────────────────────────────────────
def hadith_chat_tab(engine):
    from hadith_chat import synthesize_answer
    _gemini_keys_raw = st.session_state.get("gemini_keys_raw", "")

    st.markdown('<p class="section-label">💬 Ask me anything about Islam</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#64748b;font-size:.85rem;margin-bottom:.5rem;">'
        'I answer based on hadith from Bukhari, Muslim &amp; Tirmidhi. '
        'Ask in Bangla or English.</p>', unsafe_allow_html=True)

    # ── Search mode selector ──────────────────────────────────────────────────
    chat_mode = st.radio(
        "chat_mode",
        options=["🚀 Hybrid  (BM25 + Dense + RRF + Re-rank)", "⚡ Simple  (Dense only)"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
        key="chat_search_mode",
    )
    chat_use_hybrid = chat_mode.startswith("🚀")
    st.markdown(
        f'<p style="color:#64748b;font-size:.75rem;margin-top:-.5rem;margin-bottom:.75rem;">'
        f'{"BM25 · Dense · RRF · Cross-Encoder · Query reframing" if chat_use_hybrid else "Fine-tuned e5 bi-encoder · Fast"}'
        f'</p>',
        unsafe_allow_html=True,
    )

    # Chat history stored in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_sources" not in st.session_state:
        st.session_state.chat_sources = {}   # message_idx -> list of source dicts
    if "expanded_source" not in st.session_state:
        st.session_state.expanded_source = {}  # (msg_idx, src_idx) -> bool

    # ── Render existing conversation ─────────────────────────────────────────
    for msg_idx, msg in enumerate(st.session_state.chat_history):
        role    = msg["role"]
        content = msg["content"]

        if role == "user":
            st.markdown(f'<div class="chat-user">{_esc(content)}</div>',
                        unsafe_allow_html=True)
        else:
            sources = st.session_state.chat_sources.get(msg_idx, [])
            st.markdown('<div class="chat-bot-wrap">', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-answer">{_esc(content)}</div>',
                        unsafe_allow_html=True)

            # Source chips
            if sources:
                chips = "".join(
                    f'<span class="src-chip" title="{_esc(book_display(s["book"]))} #{s["hadith_id"]}">'
                    f'{s["ref"]} {_esc(book_display(s["book"]))} #{s["hadith_id"]}'
                    f'</span>'
                    for s in sources
                )
                st.markdown(f'<div class="source-strip">{chips}</div>', unsafe_allow_html=True)

                # Expandable source detail — use Streamlit expanders (clickable)
                with st.container():
                    for s in sources:
                        key = f"src_{msg_idx}_{s['idx']}"
                        label = (f"{s['ref']} {book_display(s['book'])} "
                                 f"#{s['hadith_id']}")
                        with st.expander(label, expanded=False):
                            bangla_q = is_bangla(
                                st.session_state.chat_history[msg_idx-1]["content"]
                                if msg_idx > 0 else ""
                            )
                            display = extract_display_text(s["text"], bangla_q)
                            st.markdown(
                                f'<div class="source-hadith">'
                                f'<div class="result-meta" style="margin-bottom:.5rem;">'
                                f'<span class="meta-tag">📚 <span>{_esc(book_display(s["book"]))}</span></span>'
                                f'<span class="meta-tag"># <span>{s["hadith_id"]}</span></span>'
                                f'</div>'
                                f'<div class="hadith-body">{_esc(display)}</div>'
                                f'</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

    # ── Input row ─────────────────────────────────────────────────────────────
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    col_q, col_k, col_send = st.columns([5, 1, 1])
    with col_q:
        question = st.text_input(
            "chat_input",
            placeholder="কুরবানি নিজ হাতে দেওয়া উত্তম?  ·  Is it better to slaughter with your own hands?",
            label_visibility="collapsed",
            key="chat_q",
        )
    with col_k:
        chat_k = st.number_input("n", min_value=5, max_value=30, value=30,
                                 label_visibility="collapsed", key="chat_k")
    with col_send:
        send = st.button("Send ➤", type="primary",
                         use_container_width=True, key="chat_send")

    col_clr, _ = st.columns([1, 4])
    with col_clr:
        if st.button("🗑 Clear chat", key="chat_clear"):
            st.session_state.chat_history   = []
            st.session_state.chat_sources   = {}
            st.session_state.expanded_source= {}
            st.rerun()

    # ── Process new message ───────────────────────────────────────────────────
    if send and question.strip():
        q = question.strip()

        # Append user message
        st.session_state.chat_history.append({"role": "user", "content": q})
        user_idx = len(st.session_state.chat_history) - 1

        with st.spinner("Searching hadiths…"):
            try:
                if chat_use_hybrid:
                    raw_results = engine.search_hadiths(
                        q, top_k=int(chat_k),
                        use_reframing=True, extra_keys_raw=_gemini_keys_raw)
                else:
                    from hadith_search import HadithSearchEngine
                    if "simple_engine" not in st.session_state:
                        st.session_state["simple_engine"] = HadithSearchEngine()
                    raw_results = st.session_state["simple_engine"].search_hadiths(
                        q, top_k=int(chat_k),
                        use_reframing=True, extra_keys_raw=_gemini_keys_raw)
            except Exception as e:
                st.error(f"Search failed: {e}")
                return

        # Synthesize answer
        from hadith_chat import synthesize_answer
        with st.spinner("Generating answer…" if _gemini_keys_raw.strip() else "Synthesizing…"):
            answer, sources = synthesize_answer(
                q, raw_results,
                api_keys_raw=_gemini_keys_raw,
            )

        # Append bot message
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        bot_idx = len(st.session_state.chat_history) - 1
        st.session_state.chat_sources[bot_idx] = sources

        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — Document Q&A
# ─────────────────────────────────────────────────────────────────────────────
def general_documents_tab(uploaded_files):
    try:
        vector_store, embedding_model, document_ingestor, search_engine = load_doc_components()
    except Exception as e:
        st.error(f"Failed to load components: {e}"); return

    if uploaded_files:
        with st.sidebar:
            if st.button("⚡ Process Documents", type="primary", use_container_width=True):
                bar = st.progress(0); status = st.empty()
                for idx, uf in enumerate(uploaded_files):
                    status.markdown(f'<p style="color:#94a3b8;font-size:.8rem;">Processing {idx+1}/{len(uploaded_files)}: {uf.name}</p>',
                                    unsafe_allow_html=True)
                    try:
                        fp = document_ingestor.save_uploaded_file(uf)
                        if vector_store.document_exists(uf.name):
                            st.sidebar.warning(f"Already indexed: {uf.name[:28]}")
                        else:
                            chunks, metas, _ = document_ingestor.process_document(fp)
                            embs = embedding_model.embed_texts(chunks)
                            ids  = [f"{uf.name}_{i}" for i in range(len(chunks))]
                            vector_store.add_chunks(chunks, embs, metas, ids)
                            st.sidebar.success(f"✓ {len(chunks)} chunks — {uf.name[:28]}")
                    except Exception as e:
                        st.sidebar.error(f"{uf.name[:28]}: {e}")
                    bar.progress((idx+1)/len(uploaded_files))
                status.markdown('<p style="color:#34d399;font-size:.8rem;">✓ Done</p>', unsafe_allow_html=True)
                st.rerun()
        with st.sidebar:
            st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<p class="section-label">📊 Document Store</p>', unsafe_allow_html=True)
        try:   count = vector_store.get_collection_count()
        except:count = "N/A"
        st.metric("Indexed Chunks", count)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑 Clear", use_container_width=True):
                if st.session_state.get("confirm_clear"):
                    vector_store.clear_all_documents()
                    st.session_state.confirm_clear = False; st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("Click again")
        with c2:
            if st.button("📋 Browse", use_container_width=True):
                st.session_state.show_chunks = not st.session_state.get("show_chunks",False)
                st.rerun()

    st.markdown('<p class="section-label">🔍 Ask Questions</p>', unsafe_allow_html=True)
    query = st.text_input("dq", placeholder="আপনার প্রশ্ন লিখুন · Ask anything about your documents…",
                          label_visibility="collapsed", key="doc_query")
    col_k2, col_btn2 = st.columns([1, 3])
    with col_k2:
        top_k = st.number_input("k2", min_value=1, max_value=20, value=5,
                                label_visibility="collapsed", key="doc_k")
    with col_btn2:
        go3 = st.button("🔍  Search Documents", type="primary",
                        use_container_width=True, key="doc_go")

    if go3 and query.strip():
        with st.spinner(""):
            try:   results = search_engine.search_documents(query.strip(), top_k=int(top_k))
            except Exception as e: st.error(f"Search failed: {e}"); return
        if results and "error" in results[0]:
            st.markdown('<div class="empty-state"><div class="icon">🔭</div>'
                        '<p>No relevant content found.</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="stat-row"><span class="stat-pill">✨ {len(results)} chunks found</span></div>',
                        unsafe_allow_html=True)
            for i, r in enumerate(results, 1):
                score = r["similarity_percentage"]
                fn    = r["metadata"].get("filename","?")
                cid   = r["metadata"].get("chunk_id","?")
                words = r["metadata"].get("word_count",0)
                badge = similarity_badge(score)
                with st.container():
                    st.markdown(
                        f'<div class="result-card">'
                        f'<div class="result-header"><span style="color:#94a3b8;font-size:.8rem;font-weight:600">#{i}</span>{badge}</div>'
                        f'<div class="result-meta">'
                        f'<span class="meta-tag">📄 <span>{_esc(fn)}</span></span>'
                        f'<span class="meta-tag">§ <span>chunk {cid}</span></span>'
                        f'<span class="meta-tag">📝 <span>{words} w</span></span>'
                        f'</div>'
                        f'<div class="hadith-body">{_esc(r["text"])}</div>'
                        f'</div>', unsafe_allow_html=True)
    elif not go3:
        st.markdown('<div class="empty-state"><div class="icon">📄</div>'
                    '<p>Upload PDF or TXT via sidebar, then ask questions.</p></div>',
                    unsafe_allow_html=True)

    if st.session_state.get("show_chunks"):
        st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-label">📋 Document Chunks</p>', unsafe_allow_html=True)
        try:
            all_c = vector_store.get_all_chunks()
            if all_c and all_c.get("documents"):
                st.caption(f"{len(all_c['documents'])} chunks in store")
                for i,(doc,meta,cid) in enumerate(zip(all_c["documents"],all_c["metadatas"],all_c["ids"])):
                    with st.expander(f"📄 {meta.get('filename','?')} — chunk {meta.get('chunk_id',i+1)}"):
                        st.caption(f"ID: `{cid}` · {meta.get('word_count','?')} words")
                        st.text_area("",doc,height=200,disabled=True,key=f"chunk_{i}")
            else:
                st.info("No documents indexed yet.")
        except Exception as e:
            st.error(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Force sidebar open on first visit
    if "sidebar_state" not in st.session_state:
        st.session_state["sidebar_state"] = "expanded"

    hadith_stats = None
    engine_ok    = False
    engine       = None

    # ── Render sidebar FIRST — before any blocking calls ─────────────────────
    # This ensures sidebar is visible immediately on page load.
    # Stats will show as None initially; engine load happens after.
    uploaded_files = render_sidebar(hadith_stats)

    # ── Load engine ───────────────────────────────────────────────────────────
    _engine_error = None
    try:
        engine = load_hadith_engine()   # cached — fast after first load
        hadith_stats = engine.get_database_stats()
        engine_ok    = True
    except Exception as _e:
        _engine_error = _e

    st.markdown("""
<div class="hero-banner">
  <div class="hero-arabic">بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</div>
  <div class="hero-title">🕌 Hadith Knowledge Search</div>
  <div class="hero-subtitle">
    Semantic search · AI companion · 20,499 hadith
    · Bangla &amp; English · Bukhari · Muslim · Tirmidhi
  </div>
</div>""", unsafe_allow_html=True)

    # Inject sidebar toggle button directly into the parent document
    import streamlit.components.v1 as _components
    _components.html("""
<script>
(function() {
  function injectToggle() {
    const parentDoc = window.parent.document;
    if (parentDoc.getElementById('kiro-sidebar-toggle')) return;

    const btn = parentDoc.createElement('button');
    btn.id = 'kiro-sidebar-toggle';
    btn.innerHTML = '&#9776;';
    btn.title = 'Toggle sidebar';
    Object.assign(btn.style, {
      position:       'fixed',
      top:            '0.5rem',
      left:           '0.5rem',
      zIndex:         '999999',
      background:     'rgba(124,58,237,0.88)',
      border:         '1px solid rgba(167,139,250,0.45)',
      borderRadius:   '8px',
      padding:        '0.3rem 0.6rem',
      cursor:         'pointer',
      fontSize:       '1.15rem',
      color:          '#e2d9ff',
      backdropFilter: 'blur(8px)',
      lineHeight:     '1.2',
      transition:     'background 0.2s',
    });
    btn.onmouseover = () => btn.style.background = 'rgba(124,58,237,1)';
    btn.onmouseout  = () => btn.style.background = 'rgba(124,58,237,0.88)';
    btn.onclick = () => {
      const parentDoc = window.parent.document;
      const nativeBtn =
        parentDoc.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
        parentDoc.querySelector('[data-testid="stSidebarCollapsedControl"] button') ||
        parentDoc.querySelector('button[aria-label="Close sidebar"]') ||
        parentDoc.querySelector('button[aria-label="Open sidebar"]');
      if (nativeBtn) { nativeBtn.click(); return; }
      const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');
      if (!sidebar) return;
      const isOpen = sidebar.style.transform !== 'translateX(-100%)';
      sidebar.style.transition = 'transform 0.3s ease';
      sidebar.style.transform  = isOpen ? 'translateX(-100%)' : 'translateX(0)';
    };
    parentDoc.body.appendChild(btn);
  }

  injectToggle();
  const iv = setInterval(() => {
    if (window.parent.document.getElementById('kiro-sidebar-toggle')) {
      clearInterval(iv);
    } else {
      injectToggle();
    }
  }, 500);
})();
</script>
""", height=0)

    tab2, tab1, tab3 = st.tabs([
        "  💬  Hadith Companion  ",
        "  🕌  Hadith Search  ",
        "  📄  Document Q&A  ",
    ])

    with tab1:
        if engine_ok: hadith_search_tab(engine)
        else: st.error(f"Hadith database not ready. Error: {_engine_error}\n\nRun `python3 app/build_hadith_db.py` first.")
    with tab2:
        if engine_ok: hadith_chat_tab(engine)
        else: st.error(f"Hadith database not ready. Error: {_engine_error}")
    with tab3:
        general_documents_tab(uploaded_files)

if __name__ == "__main__":
    main()
