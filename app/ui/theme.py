"""
app/ui/theme.py — CSS string builder for the Bangla Islamic Q&A UI.

Call build_css(logo_mask_b64) to get the full stylesheet string.
Inject it once per session with:
    st.markdown(f"<style>{build_css(mask_b64)}</style>", unsafe_allow_html=True)
"""


def build_css(logo_mask_b64: str = "") -> str:
    """Return the complete stylesheet for the new UI."""
    mask_url = (
        f"url('data:image/png;base64,{logo_mask_b64}')"
        if logo_mask_b64
        else "none"
    )

    # ── SVG icon data URIs for CSS masks (fix item 9) ──────────────────────
    ic_back = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "stroke-linejoin='round'%3E%3Cpath d='M19 12H5M11 6l-6 6 6 6'/%3E%3C/svg%3E"
    )
    ic_plus = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "%3E%3Cpath d='M12 5v14M5 12h14'/%3E%3C/svg%3E"
    )
    ic_search = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E"
    )
    ic_chevron = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E"
    )
    ic_arrow = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "stroke-linejoin='round'%3E%3Cpath d='M5 12h14M13 6l6 6-6 6'/%3E%3C/svg%3E"
    )
    ic_book = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='1.9' stroke-linecap='round' "
        "stroke-linejoin='round'%3E%3Cpath d='M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20'/%3E%3C/svg%3E"
    )
    ic_thumb_up = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "stroke-linejoin='round'%3E%3Cpath d='M7 10v12M15 5.5L14 10h5.5a2 2 0 0 1 2 2.2l-1 5a2 2 0 0 1-2 1.8H14a2 2 0 0 1-2-2v-1l-1-5a2 2 0 0 1 .5-2z'/%3E%3C/svg%3E"
    )
    ic_thumb_down = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "stroke-linejoin='round'%3E%3Cpath d='M17 14V2M9 18.5L10 14H4.5a2 2 0 0 1-2-2.2l1-5a2 2 0 0 1 2-1.8H10a2 2 0 0 1 2 2v1l1 5a2 2 0 0 1-.5 2z'/%3E%3C/svg%3E"
    )

    ic_copy = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "stroke-linejoin='round'%3E%3Crect x='9' y='9' width='12' height='12' rx='2'/%3E"
        "%3Cpath d='M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1'/%3E%3C/svg%3E"
    )
    ic_ask = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "stroke-linejoin='round'%3E%3Cpath d='M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z'/%3E%3C/svg%3E"
    )

    return f"""
/* ═══════════════════════════════════════════════════════════════════
   0.  Google Fonts
═══════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Amiri:wght@400;700&display=swap');

/* ═══════════════════════════════════════════════════════════════════
   1.  Design-system tokens
═══════════════════════════════════════════════════════════════════ */
:root {{
  --bg:          #F4F7F5;
  --surface:     #FFFFFF;
  --surface-2:   #E8EEEA;
  --line:        #DAE3DD;
  --ink:         #13201A;
  --muted:       #5A6A61;
  --accent:      #0D6B51;
  --accent-ink:  #FFFFFF;
  --gold:        #8F6B1F;
  --logo:        #2B5E47;
  --g1:          #19B37F;
  --g2:          #35C4C9;
  --g3:          #E8C56A;
  --glow:        0.4;
  --shadow:      0 8px 24px rgba(13,60,45,.08);
  --font:        'Hind Siliguri', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-ar:     'Amiri', 'Noto Naskh Arabic', serif;
  --logo-mask:   {mask_url};
}}

:root[data-theme="dark"] {{
  --bg:          #0A1210;
  --surface:     #111C17;
  --surface-2:   #182720;
  --line:        #1E2D26;
  --ink:         #E6EFE9;
  --muted:       #8DA095;
  --accent:      #3FD6A6;
  --accent-ink:  #05241A;
  --gold:        #E3C77A;
  --logo:        #3FD6A6;
  --g1:          #22D69B;
  --g2:          #3FD0E0;
  --g3:          #F0CF73;
  --glow:        0.55;
  --shadow:      0 8px 24px rgba(0,0,0,.45);
  color-scheme:  dark;
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:          #0A1210;
    --surface:     #111C17;
    --surface-2:   #182720;
    --line:        #1E2D26;
    --ink:         #E6EFE9;
    --muted:       #8DA095;
    --accent:      #3FD6A6;
    --accent-ink:  #05241A;
    --gold:        #E3C77A;
    --logo:        #3FD6A6;
    --g1:          #22D69B;
    --g2:          #3FD0E0;
    --g3:          #F0CF73;
    --glow:        0.55;
    --shadow:      0 8px 24px rgba(0,0,0,.45);
    color-scheme:  dark;
  }}
}}

/* ═══════════════════════════════════════════════════════════════════
   2.  Colour transitions
═══════════════════════════════════════════════════════════════════ */
body,
.hcard,
.composer-wrap,
.pill,
[data-testid="stChatInput"],
.stButton button,
[data-baseweb="input"] input,
[data-baseweb="select"] {{
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}}

/* ═══════════════════════════════════════════════════════════════════
   3.  Streamlit chrome suppression
═══════════════════════════════════════════════════════════════════ */
#MainMenu,
header[data-testid="stHeader"],
[data-testid="stHeader"],
footer,
[data-testid="stDecoration"],
[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stToolbar"],
[data-testid="stStatusWidget"] {{
  display: none !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   4.  Global layout
═══════════════════════════════════════════════════════════════════ */
html, body {{
  background: var(--bg) !important;
  color: var(--ink) !important;
  font-family: var(--font) !important;
  font-size: 16px;
  line-height: 1.6;
}}
/* Streamlit's built-in light theme paints all text dark grey on .stApp and
   markdown. Re-point it at our token so dark mode text is readable.
   Children inherit, so card classes (.narr, .hcard-ref, …) keep their colours. */
.stApp,
[data-testid="stMarkdownContainer"],
[data-testid="stText"] {{
  color: var(--ink) !important;
}}
[data-testid="stMarkdownContainer"] :is(h1, h2, h3, h4, h5, h6) {{
  color: var(--ink) !important;
}}
[data-testid="stMarkdownContainer"] a {{ color: var(--accent) !important; }}
[data-testid="stMarkdownContainer"] code {{
  color: var(--ink) !important;
  background: var(--surface-2) !important;
}}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {{
  color: var(--muted) !important;
}}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
  background: var(--bg) !important;
  font-family: var(--font) !important;
}}

/* Fix item 7: reduce top padding, hide header bar */
[data-testid="stAppViewContainer"] > section[data-testid="stMain"] > div {{
  padding-top: 0 !important;
}}
.stMain .block-container {{
  padding-top: 1rem !important;
  padding-bottom: 120px !important;  /* fix item 11: space for docked composer */
}}

/* Single centred column, max 760 px */
[data-testid="stAppViewContainer"] > .main .block-container,
section.main > div.block-container {{
  max-width: 760px !important;
  padding-left: 20px !important;
  padding-right: 20px !important;
  margin: 0 auto !important;
}}

iframe {{ border: 0 !important; display: block !important; }}

/* ═══════════════════════════════════════════════════════════════════
   5.  Fix item 6: bottom strip / stBottom dark-mode coverage
═══════════════════════════════════════════════════════════════════ */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div,
[data-testid="stBottomBlockContainer"] iframe {{
  background: var(--bg) !important;
  border: 0 !important;
}}
[data-testid="stBottom"] > div {{
  border-top: 0 !important;
  box-shadow: none !important;
}}
[data-testid="stChatInput"] {{
  background: var(--surface) !important;
  border-color: var(--line) !important;
  color: var(--ink) !important;
}}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input {{
  color: var(--ink) !important;
  background: transparent !important;
}}
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInput"] input::placeholder {{
  color: var(--muted) !important;
}}
[data-testid="stChatInput"] button {{
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
}}
/* Overflow visible so the glow isn't clipped (fix item 5).
   NOT on stMain: stMain is Streamlit's page scroll container and must keep
   overflow:auto, otherwise the page cannot be scrolled at all. */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"] {{
  overflow: visible !important;
}}
[data-testid="stMain"] {{
  overflow-y: auto !important;
}}
/* Streamlit footer */
footer[data-testid="stFooter"],
[data-testid="stToolbar"] {{
  background: var(--bg) !important;
  color: var(--muted) !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   6.  Native widget colour overrides (fix item 10: dark coverage)
═══════════════════════════════════════════════════════════════════ */
/* Generic buttons */
.stButton button {{
  background: transparent !important;
  color: var(--muted) !important;
  border: 1px solid var(--line) !important;
  border-radius: 999px !important;
  font-family: var(--font) !important;
  min-height: 44px !important;
  transition: background 0.2s, color 0.2s, border-color 0.2s !important;
}}
.stButton button:hover {{
  background: var(--surface-2) !important;
  color: var(--ink) !important;
  border-color: var(--accent) !important;
}}
/* Tertiary (ghost) buttons used in top bar */
.stButton button[kind="tertiary"],
.stButton button[data-testid="stBaseButton-tertiary"] {{
  border: 0 !important;
  background: transparent !important;
  color: var(--muted) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  min-height: 44px !important;
  padding: 8px 14px !important;
  border-radius: 999px !important;
}}
.stButton button[kind="tertiary"]:hover,
.stButton button[data-testid="stBaseButton-tertiary"]:hover {{
  background: var(--surface-2) !important;
  color: var(--ink) !important;
}}
/* Secondary buttons */
.stButton button[kind="secondary"],
.stButton button[data-testid="stBaseButton-secondary"] {{
  border: 1px solid var(--line) !important;
  background: var(--surface) !important;
  color: var(--muted) !important;
  border-radius: 999px !important;
  font-size: 13px !important;
  min-height: 36px !important;
  padding: 6px 14px !important;
}}
.stButton button[kind="secondary"]:hover,
.stButton button[data-testid="stBaseButton-secondary"]:hover {{
  border-color: var(--accent) !important;
  color: var(--accent) !important;
  background: var(--surface) !important;
}}
/* Primary buttons (selected vote state) */
.stButton button[kind="primary"],
.stButton button[data-testid="stBaseButton-primary"] {{
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
  border: 1px solid var(--accent) !important;
  border-radius: 999px !important;
  font-size: 13px !important;
  min-height: 36px !important;
  padding: 6px 14px !important;
}}

/* Text inputs */
.stTextInput input,
[data-baseweb="input"] input,
[data-baseweb="base-input"] input {{
  background: var(--surface) !important;
  color: var(--ink) !important;
  border-color: var(--line) !important;
  font-family: var(--font) !important;
}}
.stTextInput input:focus,
[data-baseweb="input"] input:focus,
[data-baseweb="base-input"] input:focus {{
  border-color: var(--accent) !important;
  box-shadow: none !important;
}}
.stTextInput input::placeholder,
[data-baseweb="input"] input::placeholder,
[data-baseweb="base-input"] input::placeholder {{
  color: var(--muted) !important;
}}

/* Number inputs — hide steppers (fix item 8) */
[data-testid="stNumberInputStepUp"],
[data-testid="stNumberInputStepDown"] {{
  display: none !important;
}}
.stNumberInput,
[data-baseweb="input"]:has(input[type="number"]) {{
  background: var(--surface) !important;
  border-color: var(--line) !important;
  border-radius: 14px !important;
}}
.stNumberInput input {{
  background: var(--surface) !important;
  color: var(--ink) !important;
  border-color: var(--line) !important;
  font-family: var(--font) !important;
}}

/* Selectbox (fix item 8) */
[data-baseweb="select"] > div,
.stSelectbox [data-baseweb="select"] > div {{
  background: var(--surface) !important;
  border-color: var(--line) !important;
  color: var(--ink) !important;
  font-family: var(--font) !important;
  min-height: 44px !important;
  border-radius: 14px !important;
}}
[data-baseweb="select"] [data-baseweb="select-value"],
[data-baseweb="select"] [role="combobox"] {{
  color: var(--ink) !important;
  font-family: var(--font) !important;
}}

/* Expander */
.stExpander,
[data-testid="stExpander"] {{
  background: var(--surface) !important;
  border-color: var(--line) !important;
  border-radius: 14px !important;
}}
.stExpander > details > summary,
[data-testid="stExpander"] summary {{
  color: var(--ink) !important;
  font-family: var(--font) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
}}
.stExpander > details > summary:hover,
[data-testid="stExpander"] summary:hover {{
  color: var(--accent) !important;
}}
[data-testid="stExpander"] > div > div {{
  background: var(--surface) !important;
}}

/* BaseWeb popovers / menus */
[data-baseweb="popover"],
[data-baseweb="menu"] {{
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  color: var(--ink) !important;
  font-family: var(--font) !important;
}}
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"] {{
  color: var(--ink) !important;
  font-family: var(--font) !important;
}}
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] [role="option"]:hover {{
  background: var(--surface-2) !important;
}}

/* Spinner */
.stSpinner > div,
[data-testid="stSpinner"] > div {{
  border-color: var(--accent) transparent transparent transparent !important;
}}

/* Error / info / alert boxes (fix item 10) */
[data-testid="stAlert"],
.stAlert {{
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  color: var(--ink) !important;
  border-radius: 14px !important;
}}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div {{
  color: var(--ink) !important;
  font-family: var(--font) !important;
}}
[data-testid="stAlert"] svg,
[data-testid="stAlert"] [data-icon] {{
  color: var(--accent) !important;
}}

/* Toast */
[data-testid="stToast"],
[data-testid="stStatusWidget"] {{
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  color: var(--ink) !important;
  font-family: var(--font) !important;
}}

/* Chat messages (fix item 10) */
[data-testid="stChatMessage"] {{
  background: transparent !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   7.  Logo
═══════════════════════════════════════════════════════════════════ */
.iq-logo {{
  display: block;
  width: min(440px, 78vw);
  aspect-ratio: 1000 / 128;
  background: var(--logo);
  -webkit-mask: var(--logo-mask) center / contain no-repeat;
          mask: var(--logo-mask) center / contain no-repeat;
  transition: background-color 0.2s;
}}

/* ═══════════════════════════════════════════════════════════════════
   8.  Top bar (fix item 7: no border / stray line, ghost pills)
═══════════════════════════════════════════════════════════════════ */
.iq-topbar {{
  display: flex;
  align-items: center;
  height: 52px;
  gap: 8px;
  border-bottom: 0 !important;  /* fix item 7: remove stray line */
  background: transparent;
  padding: 0 4px;
  flex: none;
}}
.iq-topbar-title {{
  font-size: 14px;
  color: var(--muted);
  padding-left: 4px;
  font-weight: 500;
  font-family: var(--font);
}}

/* Fix item 7 + 9: icon via CSS mask on st-key- buttons */
.st-key-back_to_chat button::before,
.st-key-new_chat button::before {{
  content: "";
  display: inline-block;
  width: 16px;
  height: 16px;
  flex: none;
  margin-right: 6px;
  vertical-align: middle;
  background: currentColor;
  -webkit-mask-size: contain;
  mask-size: contain;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
}}
.st-key-back_to_chat button::before {{
  -webkit-mask-image: url("{ic_back}");
  mask-image: url("{ic_back}");
}}
.st-key-new_chat button::before {{
  -webkit-mask-image: url("{ic_plus}");
  mask-image: url("{ic_plus}");
}}

/* ═══════════════════════════════════════════════════════════════════
   9.  Composer glow (fix item 5: both home_composer and stChatInput)
═══════════════════════════════════════════════════════════════════ */
@property --iq-a {{
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}}

.iq-composer-wrap {{
  position: relative;
  isolation: isolate;
  border-radius: 30px;
  width: 100%;
}}

.iq-composer-wrap::before,
.iq-composer-wrap::after {{
  content: "";
  position: absolute;
  z-index: -1;
  border-radius: inherit;
  background: conic-gradient(from var(--iq-a), var(--g1), var(--g2), var(--g3), var(--g1));
  animation: iq-spin 9s linear infinite;
}}
.iq-composer-wrap::before {{
  inset: -2px;
  opacity: calc(var(--glow) + 0.35);
  transition: opacity 0.3s;
}}
.iq-composer-wrap::after {{
  inset: -2px;
  filter: blur(18px);
  opacity: var(--glow);
  transition: opacity 0.3s, inset 0.3s;
}}
.iq-composer-wrap:focus-within::before {{ opacity: 1; }}
.iq-composer-wrap:focus-within::after {{
  opacity: calc(var(--glow) + 0.3);
  inset: -6px;
}}
@keyframes iq-spin {{ to {{ --iq-a: 360deg; }} }}

[data-testid="stChatInput"] {{
  border-radius: 28px !important;
}}

/* Fix item 5: glow on native st.chat_input too */
@property --iq-ci {{
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}}
[data-testid="stChatInputContainer"] {{
  position: relative !important;
  isolation: isolate !important;
  border-radius: 30px !important;
  background: var(--surface) !important;
}}
[data-testid="stChatInputContainer"]::before,
[data-testid="stChatInputContainer"]::after {{
  content: "" !important;
  position: absolute !important;
  z-index: -1 !important;
  border-radius: inherit !important;
  background: conic-gradient(from var(--iq-ci), var(--g1), var(--g2), var(--g3), var(--g1)) !important;
  animation: iq-ci-spin 9s linear infinite !important;
}}
[data-testid="stChatInputContainer"]::before {{
  inset: -2px !important;
  opacity: calc(var(--glow) + 0.35) !important;
}}
[data-testid="stChatInputContainer"]::after {{
  inset: -2px !important;
  filter: blur(18px) !important;
  opacity: var(--glow) !important;
}}
[data-testid="stChatInputContainer"]:focus-within::before {{
  opacity: 1 !important;
}}
[data-testid="stChatInputContainer"]:focus-within::after {{
  opacity: calc(var(--glow) + 0.3) !important;
  inset: -6px !important;
}}
@keyframes iq-ci-spin {{ to {{ --iq-ci: 360deg; }} }}
@media (prefers-reduced-motion: reduce) {{
  [data-testid="stChatInputContainer"]::before,
  [data-testid="stChatInputContainer"]::after {{ animation: none !important; }}
}}

/* Fix item 5: home composer as st.form */
.iq-home-composer [data-testid="stForm"] {{
  background: var(--surface) !important;
  border-radius: 28px !important;
  border: 0 !important;
  padding: 0 !important;
  box-shadow: none !important;
  position: relative;
  isolation: isolate;
}}
.iq-home-composer [data-testid="stForm"]::before,
.iq-home-composer [data-testid="stForm"]::after {{
  content: "";
  position: absolute;
  z-index: -1;
  border-radius: 30px;
  background: conic-gradient(from var(--iq-ci), var(--g1), var(--g2), var(--g3), var(--g1));
  animation: iq-ci-spin 9s linear infinite;
}}
.iq-home-composer [data-testid="stForm"]::before {{
  inset: -2px;
  opacity: calc(var(--glow) + 0.35);
}}
.iq-home-composer [data-testid="stForm"]::after {{
  inset: -2px;
  filter: blur(18px);
  opacity: var(--glow);
}}
.iq-home-composer:focus-within [data-testid="stForm"]::before {{ opacity: 1; }}
.iq-home-composer:focus-within [data-testid="stForm"]::after {{
  opacity: calc(var(--glow) + 0.3);
  inset: -6px;
}}
.iq-home-composer .stTextArea textarea,
.iq-home-composer .stTextInput input {{
  background: transparent !important;
  color: var(--ink) !important;
  border: 0 !important;
  padding: 14px 22px 8px !important;
  font-size: 16px !important;
  font-family: var(--font) !important;
  line-height: 1.6 !important;
  box-shadow: none !important;
  outline: 0 !important;
}}
.iq-home-composer .stTextArea textarea::placeholder,
.iq-home-composer .stTextInput input::placeholder {{
  color: var(--muted) !important;
}}
.iq-home-composer [data-baseweb="textarea"],
.iq-home-composer [data-baseweb="input"],
.iq-home-composer [data-baseweb="base-input"] {{
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}}
.iq-home-composer [data-testid="stFormSubmitButton"] button {{
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
  border: 0 !important;
  border-radius: 50% !important;
  width: 42px !important;
  height: 42px !important;
  min-height: 42px !important;
  font-size: 18px !important;
  font-family: var(--font) !important;
  font-weight: 600 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: opacity 0.2s !important;
}}
.iq-home-composer [data-testid="stFormSubmitButton"] button:hover {{
  opacity: 0.88 !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   10.  Chat thread components
═══════════════════════════════════════════════════════════════════ */
.iq-thread {{
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 760px;
  margin: 0 auto;
}}

/* User bubble */
.iq-msg-user {{
  display: flex;
  justify-content: flex-end;
}}
.iq-bubble {{
  max-width: 82%;
  padding: 10px 18px;
  border-radius: 20px 20px 6px 20px;
  background: var(--surface-2);
  font-size: 15px;
  line-height: 1.65;
  overflow-wrap: anywhere;
  color: var(--ink);
}}

/* AI message */
.iq-msg-ai {{
  display: flex;
  gap: 12px;
  align-items: flex-start;
}}
.iq-avatar {{
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
  background: var(--surface);
  box-shadow: inset 0 0 0 1px var(--line);
  margin-top: 2px;
  font-size: 14px;
}}
.iq-ai-body {{
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}}
.iq-ai-text {{
  font-size: 15px;
  line-height: 1.85;
  overflow-wrap: anywhere;
  color: var(--ink);
}}

/* Status line next to the typing dots */
.iq-status {{
  font-size: 13px;
  color: var(--muted);
  margin-left: 4px;
}}

/* Typing indicator */
.iq-typing {{
  display: inline-flex;
  gap: 5px;
  padding: 12px 0;
}}
.iq-typing i {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  opacity: 0.35;
  animation: iq-blink 1.1s infinite ease-in-out;
}}
.iq-typing i:nth-child(2) {{ animation-delay: 0.18s; }}
.iq-typing i:nth-child(3) {{ animation-delay: 0.36s; }}
@keyframes iq-blink {{
  0%, 100% {{ opacity: 0.25; transform: translateY(0); }}
  50%       {{ opacity: 1;    transform: translateY(-3px); }}
}}

/* Cache tag */
.iq-cache-tag {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--accent);
  background: rgba(13,107,81,.08);
  border: 1px solid rgba(13,107,81,.2);
  border-radius: 999px;
  padding: 2px 10px;
  font-weight: 600;
}}
:root[data-theme="dark"] .iq-cache-tag {{
  background: rgba(63,214,166,.1);
  border-color: rgba(63,214,166,.25);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) .iq-cache-tag {{
    background: rgba(63,214,166,.1);
    border-color: rgba(63,214,166,.25);
  }}
}}

/* ═══════════════════════════════════════════════════════════════════
   11.  Hadith card (fix item 4: st-key-hcard_ container styling)
═══════════════════════════════════════════════════════════════════ */
[class*="st-key-hcard_"] {{
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  border-radius: 20px !important;
  padding: 20px 22px 16px !important;
  box-shadow: var(--shadow) !important;
  scroll-margin-top: 12px;
}}
[class*="st-key-hcard_"]:hover {{
  border-color: rgba(13,107,81,.35);
}}
:root[data-theme="dark"] [class*="st-key-hcard_"]:hover {{
  border-color: rgba(63,214,166,.35);
}}

.hcard-ref {{
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}}
.hcard-ref b {{
  color: var(--accent);
  font-size: 14px;
  font-weight: 700;
}}
.hcard-ref span {{
  color: var(--muted);
  font-size: 13px;
}}
.hcard-label {{
  color: var(--muted);
  font-size: 13px;
}}
.grade {{
  margin-left: auto;
  font-size: 11px;
  color: var(--gold);
  background: rgba(143,107,31,.08);
  border: 1px solid rgba(143,107,31,.25);
  border-radius: 6px;
  padding: 2px 9px;
  font-weight: 600;
  white-space: nowrap;
}}
:root[data-theme="dark"] .grade {{
  background: rgba(227,199,122,.08);
  border-color: rgba(227,199,122,.25);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) .grade {{
    background: rgba(227,199,122,.08);
    border-color: rgba(227,199,122,.25);
  }}
}}

.ar {{
  font-family: var(--font-ar);
  font-size: 28px;
  line-height: 2.2;
  text-align: right;
  direction: rtl;
  color: var(--ink);
  background: var(--surface-2);
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 14px;
  word-break: break-word;
}}
.bn {{
  font-size: 16px;
  line-height: 1.85;
  color: var(--ink);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin-bottom: 8px;
}}
.en {{
  font-size: 15px;
  line-height: 1.7;
  color: var(--muted);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin-bottom: 12px;
}}

.hcard-foot {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}}
.narr {{
  font-size: 13px;
  color: var(--muted);
  display: block;
  width: 100%;
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.5;
  margin-bottom: 6px;
}}
[class*="st-key-hcard_"] [data-testid="stHorizontalBlock"] {{
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}}
[class*="st-key-hcard_"] [data-testid="stHorizontalBlock"] button {{
  white-space: nowrap;
}}
.acts {{
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}}

/* Copy button (HTML, fix item 2) */
.act, .copy-btn {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font);
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
  white-space: nowrap;
}}
.act:hover, .copy-btn:hover {{
  border-color: var(--accent);
  color: var(--accent);
}}

/* Flash animation for number-jump */
.hcard--flash {{
  animation: hadith-flash 1.8s ease-out forwards;
}}
@keyframes hadith-flash {{
  0%   {{ box-shadow: 0 0 0 3px var(--accent), var(--shadow); }}
  100% {{ box-shadow: 0 0 0 3px transparent, var(--shadow); }}
}}

/* Skeleton placeholder */
.hcard-skeleton {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 20px 22px 16px;
  animation: iq-pulse 1.2s ease-in-out infinite;
}}
.hcard-skeleton .skel-line {{
  height: 12px;
  border-radius: 6px;
  background: var(--surface-2);
  margin-bottom: 10px;
}}
@keyframes iq-pulse {{
  0%, 100% {{ opacity: 1; }}
  50%       {{ opacity: 0.55; }}
}}

/* ═══════════════════════════════════════════════════════════════════
   12.  Home / hero area (fix item 5: vertical centering)
═══════════════════════════════════════════════════════════════════ */
.iq-hero {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 0 20px 12px;
  text-align: center;
}}
.iq-hero-sub {{
  font-size: clamp(16px, 3vw, 21px);
  color: var(--muted);
  text-wrap: balance;
  margin: 0;
}}
.iq-note {{
  font-size: 12px;
  color: var(--muted);
  text-align: center;
  margin: 0;
}}

/* Fix item 5: Home is vertically centred */
.iq-home-wrap {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  gap: 18px;
  width: 100%;
}}

/* Hadith Books pill (fix item 9: icon via CSS mask) */
.st-key-pill_hadith button::before {{
  content: "";
  display: inline-block;
  width: 18px;
  height: 18px;
  flex: none;
  margin-right: 6px;
  vertical-align: middle;
  background: currentColor;
  -webkit-mask-image: url("{ic_book}");
  mask-image: url("{ic_book}");
  -webkit-mask-size: contain;
  mask-size: contain;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
}}
.st-key-pill_hadith button {{
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  border-radius: 999px !important;
  color: var(--ink) !important;
  font-size: 14.5px !important;
  font-weight: 500 !important;
  min-height: 44px !important;
  padding: 9px 18px !important;
}}
.st-key-pill_hadith button:hover {{
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   13.  Hadith Books controls (fix item 8)
═══════════════════════════════════════════════════════════════════ */
.iq-hbar {{
  padding: 4px 0 10px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 760px;
  margin: 0 auto;
}}

/* ── Hadith Books header (prototype .hbar) ─────────────────────────────
   Forms get no st-key class in Streamlit, so each form is wrapped in a
   keyed st.container (st-key-h_search_wrap / st-key-h_no_wrap) and the
   form is laid out as one row: input + (hidden or inline) submit. */

/* Shared: strip BaseWeb's own box so the wrapper is the only outline */
.st-key-h_search_wrap [data-baseweb="input"],
.st-key-h_search_wrap [data-baseweb="base-input"],
.st-key-h_no_wrap [data-baseweb="input"],
.st-key-h_no_wrap [data-baseweb="base-input"] {{
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}}
.st-key-h_search_wrap input,
.st-key-h_no_wrap input {{
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  color: var(--ink) !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}}
.st-key-h_search_wrap input::placeholder,
.st-key-h_no_wrap input::placeholder {{ color: var(--muted) !important; }}
.st-key-h_search_wrap [data-testid="InputInstructions"],
.st-key-h_no_wrap [data-testid="InputInstructions"] {{ display: none !important; }}
.st-key-h_search_wrap [data-testid="stForm"],
.st-key-h_no_wrap [data-testid="stForm"] {{
  border: 0 !important;
  padding: 0 !important;
  background: transparent !important;
}}
/* One row inside each form */
.st-key-h_search_wrap [data-testid="stForm"] [data-testid="stVerticalBlock"],
.st-key-h_no_wrap [data-testid="stForm"] [data-testid="stVerticalBlock"] {{
  flex-direction: row !important;
  align-items: center !important;
  gap: 6px !important;
}}
.st-key-h_search_wrap .stElementContainer:has(.stTextInput),
.st-key-h_no_wrap .stElementContainer:has(.stTextInput) {{
  flex: 1 1 auto !important;
  width: auto !important;
  min-width: 0 !important;
}}

/* The keyed container is a column flexbox by default; make it a row whose
   single child (the form) fills the whole width, so the input starts at the
   left edge and the go button sits at the right end. */
.st-key-h_search_wrap,
.st-key-h_no_wrap {{
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  gap: 0 !important;
}}
.st-key-h_search_wrap > *,
.st-key-h_no_wrap > *,
.st-key-h_search_wrap [data-testid="stForm"],
.st-key-h_no_wrap [data-testid="stForm"],
.st-key-h_search_wrap [data-testid="stForm"] > *,
.st-key-h_no_wrap [data-testid="stForm"] > * {{
  flex: 1 1 auto !important;
  width: 100% !important;
  min-width: 0 !important;
}}
.st-key-h_search_wrap input,
.st-key-h_no_wrap input {{ text-align: left !important; }}

/* Search pill: height 50, radius 999, search icon inside at the left */
.st-key-h_search_wrap {{
  position: relative;
  display: flex !important;
  align-items: center;
  height: 50px;
  padding: 0 16px 0 44px !important;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--line);
  transition: border-color 0.2s, background-color 0.2s;
}}
.st-key-h_search_wrap:focus-within {{ border-color: var(--accent); }}
.st-key-h_search_wrap::before {{
  content: "";
  position: absolute;
  left: 17px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  background: var(--muted);
  -webkit-mask: url("{ic_search}") center / contain no-repeat;
          mask: url("{ic_search}") center / contain no-repeat;
  pointer-events: none;
}}
.st-key-h_search_wrap input {{ font-size: 16px !important; }}
/* Enter submits the form; the submit button itself is never shown */
.st-key-h_search_wrap .stElementContainer:has([data-testid="stFormSubmitButton"]) {{
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}}

/* Book select: height 44, radius 14 */
.stSelectbox [data-baseweb="select"] > div {{
  min-height: 44px !important;
  border-radius: 14px !important;
  border: 1px solid var(--line) !important;
  background: var(--surface) !important;
}}
.stSelectbox [data-baseweb="select"] > div:focus-within {{ border-color: var(--accent) !important; }}
.stSelectbox [data-baseweb="select"] svg {{ color: var(--muted) !important; }}

/* Number field: height 44, radius 14, "#" prefix, go button inside */
.st-key-h_no_wrap {{
  display: flex !important;
  align-items: center;
  height: 44px;
  padding: 0 6px 0 30px !important;
  border-radius: 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  position: relative;
  transition: border-color 0.2s, background-color 0.2s;
}}
.st-key-h_no_wrap:focus-within {{ border-color: var(--accent); }}
.st-key-h_no_wrap::before {{
  content: "#";
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--muted);
  font-size: 15px;
  pointer-events: none;
}}
.st-key-h_no_wrap input {{
  font-size: 15px !important;
  font-variant-numeric: tabular-nums;
}}
.st-key-h_no_wrap .stElementContainer:has([data-testid="stFormSubmitButton"]) {{
  flex: 0 0 auto !important;
  width: auto !important;
}}
.st-key-h_no_wrap [data-testid="stFormSubmitButton"] button {{
  width: 32px !important;
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 10px !important;
  background: var(--surface-2) !important;
  color: transparent !important;          /* hide the "→" glyph; icon below */
  position: relative;
}}
.st-key-h_no_wrap [data-testid="stFormSubmitButton"] button::after {{
  content: "";
  position: absolute;
  inset: 0;
  margin: auto;
  width: 16px;
  height: 16px;
  background: var(--ink);
  -webkit-mask: url("{ic_arrow}") center / contain no-repeat;
          mask: url("{ic_arrow}") center / contain no-repeat;
}}
.st-key-h_no_wrap [data-testid="stFormSubmitButton"] button:hover {{
  background: var(--accent) !important;
}}
.st-key-h_no_wrap [data-testid="stFormSubmitButton"] button:hover::after {{
  background: var(--accent-ink);
}}

/* Invisible helpers (CSS-injection blocks, zero-height script iframes)
   still take a row of Streamlit's 1rem gap each, which pushed the page
   ~70px down.  Collapse them; <style> still applies and the iframes still
   run their scripts while display:none. */
[data-testid="stMain"] .stElementContainer:has(style),
[data-testid="stMain"] .stElementContainer:has(iframe[height="0"]) {{
  display: none !important;
}}

/* Top bar: back button and title on one compact row */
.st-key-topbar_hadith [data-testid="stHorizontalBlock"] {{
  gap: 4px !important;
  flex-wrap: nowrap !important;
}}
.st-key-topbar_hadith [data-testid="stColumn"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
}}
.st-key-topbar_hadith .iq-topbar-title {{ padding-left: 0; }}
.st-key-topbar_hadith {{ padding-top: 6px; }}

@media (max-width: 899px) {{
  .st-key-h_no_wrap [data-testid="stFormSubmitButton"] button {{
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
  }}
}}

/* Count line (fix item 8: muted, 13px, readable in dark) */
.iq-count-line {{
  font-size: 13px;
  color: var(--muted);
  padding-left: 4px;
  font-family: var(--font);
}}

/* ═══════════════════════════════════════════════════════════════════
   14.  Feedback row (fix item 9: line icons via CSS mask)
═══════════════════════════════════════════════════════════════════ */
[class*="st-key-vote_up_"] button::before,
[class*="st-key-vote_down_"] button::before {{
  content: "";
  display: inline-block;
  width: 16px;
  height: 16px;
  flex: none;
  margin-right: 4px;
  vertical-align: middle;
  background: currentColor;
  -webkit-mask-size: contain;
  mask-size: contain;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
}}
[class*="st-key-vote_up_"] button::before {{
  -webkit-mask-image: url("{ic_thumb_up}");
  mask-image: url("{ic_thumb_up}");
}}
[class*="st-key-vote_down_"] button::before {{
  -webkit-mask-image: url("{ic_thumb_down}");
  mask-image: url("{ic_thumb_down}");
}}
[class*="st-key-vote_up_"] button,
[class*="st-key-vote_down_"] button {{
  font-size: 13px !important;
  min-height: 34px !important;
  padding: 6px 12px !important;
  border-radius: 999px !important;
  white-space: nowrap !important;
  min-width: 80px !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   15.  Other contextual buttons
═══════════════════════════════════════════════════════════════════ */
/* Retry button */
[class*="st-key-retry"] button {{
  border: 1px solid var(--accent) !important;
  color: var(--accent) !important;
  font-size: 14px !important;
  min-height: 40px !important;
}}

/* Load-more / clear-search */
[class*="st-key-load_more"] button,
[class*="st-key-clear_search"] button {{
  background: var(--surface-2) !important;
  border: 1px solid var(--line) !important;
  border-radius: 999px !important;
  color: var(--muted) !important;
  font-size: 13.5px !important;
  min-height: 40px !important;
}}


/* ── Hadith card actions: কপি + AI-কে জিজ্ঞেস করুন ────────────────────
   One right-aligned row, vertically centred; both buttons share one pill
   style (36px, radius 999, --line border, --muted text) in both themes. */
[class*="st-key-hfoot_"] [data-testid="stHorizontalBlock"] {{
  justify-content: flex-end !important;
  align-items: center !important;
  flex-wrap: nowrap !important;
  gap: 8px !important;
}}
[class*="st-key-hfoot_"] [data-testid="stColumn"] {{
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
}}
[class*="st-key-hfoot_"] [data-testid="stMarkdown"],
[class*="st-key-hfoot_"] [data-testid="stMarkdownContainer"],
[class*="st-key-hfoot_"] .stElementContainer,
[class*="st-key-hfoot_"] .stButton {{
  margin: 0 !important;
  padding: 0 !important;
  width: auto !important;
}}
[class*="st-key-hfoot_"] .copy-btn,
[class*="st-key-hfoot_"] .stButton > button {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 6px !important;
  box-sizing: border-box !important;
  height: 36px !important;
  min-height: 36px !important;
  margin: 0 !important;
  padding: 0 14px !important;
  border: 1px solid var(--line) !important;
  border-radius: 999px !important;
  background: transparent !important;
  color: var(--muted) !important;
  font-family: var(--font) !important;
  font-size: 13.5px !important;
  font-weight: 500 !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  box-shadow: none !important;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s, background-color 0.2s;
}}
[class*="st-key-hfoot_"] .stButton > button p,
[class*="st-key-hfoot_"] .stButton > button div {{
  color: inherit !important;
  font-weight: inherit !important;
  margin: 0 !important;
  font-size: 13.5px !important;
  line-height: 1 !important;
}}
[class*="st-key-hfoot_"] .copy-btn:hover,
[class*="st-key-hfoot_"] .stButton > button:hover {{
  border-color: var(--accent) !important;
  color: var(--accent) !important;
  background: var(--surface-2) !important;
}}
[class*="st-key-hfoot_"] .copy-btn::before,
[class*="st-key-hfoot_"] .stButton > button::before {{
  content: "";
  flex: none;
  width: 15px;
  height: 15px;
  background: currentColor;
  -webkit-mask: var(--ic) center / contain no-repeat;
          mask: var(--ic) center / contain no-repeat;
}}
[class*="st-key-hfoot_"] .copy-btn {{ --ic: url("{ic_copy}"); }}
[class*="st-key-hfoot_"] .stButton > button {{ --ic: url("{ic_ask}"); }}

/* ═══════════════════════════════════════════════════════════════════
   16.  Accessibility — focus ring
═══════════════════════════════════════════════════════════════════ */
*:focus-visible {{
  outline: 2px solid var(--accent) !important;
  outline-offset: 2px !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   17.  Responsive
═══════════════════════════════════════════════════════════════════ */
@media (max-width: 899px) {{
  .iq-topbar {{ padding-right: 68px; }}
  .ar {{ font-size: 25px; }}
}}
@media (max-width: 480px) {{
  .ar {{ font-size: 22px; }}
}}

/* ═══════════════════════════════════════════════════════════════════
   17b. Conversation dock (matches prototype: glowing pill composer,
        round send button, "হাদীস গ্রন্থ" pill and note under it)
═══════════════════════════════════════════════════════════════════ */
[data-testid="stBottomBlockContainer"] {{
  max-width: 760px !important;
  margin: 0 auto !important;
  padding: 8px 20px 84px !important;   /* room for pill + note */
  position: relative;
}}
/* Native chat input = composer. Glow lives on the element itself. */
[data-testid="stChatInput"] {{
  position: relative !important;
  isolation: isolate !important;
  min-height: 62px !important;
  border: 0 !important;
  border-radius: 30px !important;
  background: transparent !important;   /* surface is on the inner wrapper so the glow ring shows */
  box-shadow: none !important;
  padding: 0 !important;
}}
[data-testid="stChatInput"] > div {{
  background: var(--surface) !important;
  border: 0 !important;
  border-radius: 28px !important;
  box-shadow: none !important;
  min-height: 62px !important;
  align-items: center !important;
  position: relative !important;
  padding: 10px 64px 10px 22px !important;   /* right gap reserved for the send button */
}}
/* Send button wrapper: centred vertically, 10px from the right edge */
[data-testid="stChatInput"] div:has(> [data-testid="stChatInputSubmitButton"]) {{
  position: absolute !important;
  right: 10px !important;
  top: 50% !important;
  bottom: auto !important;
  transform: translateY(-50%) !important;
  display: flex !important;
  align-items: center !important;
  margin: 0 !important;
  padding: 0 !important;
}}
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"] {{
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}}
[data-testid="stChatInput"]::before,
[data-testid="stChatInput"]::after {{
  content: "" !important;
  position: absolute !important;
  z-index: -1 !important;
  border-radius: 30px !important;
  background: conic-gradient(from var(--iq-ci), var(--g1), var(--g2), var(--g3), var(--g1)) !important;
  animation: iq-ci-spin 9s linear infinite !important;
  pointer-events: none;
}}
[data-testid="stChatInput"]::before {{
  inset: -2px !important;
  opacity: 1 !important;                 /* crisp, fully saturated ring */
}}
[data-testid="stChatInput"]::after {{
  inset: -4px !important;
  filter: blur(22px) !important;
  opacity: calc(var(--glow) + 0.25) !important;
  transition: opacity .3s, inset .3s;
}}
[data-testid="stChatInput"]:focus-within::after {{
  opacity: calc(var(--glow) + 0.4) !important;
  inset: -8px !important;
}}
[data-testid="stChatInput"] textarea {{
  font-size: 16px !important;
  line-height: 1.6 !important;
  font-family: var(--font) !important;
  padding: 9px 0 !important;
  width: 100% !important;
  caret-color: var(--ink);
}}
/* Send button: solid accent circle with an up arrow, same as the home hero */
[data-testid="stChatInputSubmitButton"],
[data-testid="stChatInputSubmitButton"]:disabled {{
  width: 46px !important;
  height: 46px !important;
  min-width: 46px !important;
  border: 0 !important;
  border-radius: 50% !important;
  background: var(--accent) !important;
  color: #fff !important;
  opacity: 1 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: transform .2s !important;
}}
[data-testid="stChatInputSubmitButton"]:disabled {{ cursor: default !important; }}
[data-testid="stChatInputSubmitButton"] > * {{ display: none !important; }}
[data-testid="stChatInputSubmitButton"]::before {{
  content: "";
  width: 20px;
  height: 20px;
  background: #fff;
  -webkit-mask: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'><path d='M12 19V5M5 12l7-7 7 7'/></svg>") center/contain no-repeat;
          mask: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'><path d='M12 19V5M5 12l7-7 7 7'/></svg>") center/contain no-repeat;
}}
[data-testid="stChatInputSubmitButton"]:not(:disabled):hover {{
  transform: scale(1.06);
}}
/* Note under the composer */
[data-testid="stBottomBlockContainer"]::after {{
  content: "AI ভুল করতে পারে। উৎস যাচাই করে নিন।";
  position: absolute;
  left: 0; right: 0; bottom: 14px;
  text-align: center;
  font-size: 12.5px;
  color: var(--muted);
  pointer-events: none;
}}
/* "হাদীস গ্রন্থ" pill docked between composer and note */
.st-key-dock_hadith {{
  position: fixed;
  left: 50%;
  bottom: 38px;
  transform: translateX(-50%);
  z-index: 1000;
  width: auto !important;
}}
.st-key-dock_hadith button {{
  min-height: 44px;
  padding: 9px 18px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink);
  font-size: 14.5px;
  font-weight: 500;
  font-family: var(--font);
  white-space: nowrap;
}}
.st-key-dock_hadith button:hover {{
  border-color: var(--accent);
  color: var(--accent);
}}
/* Top bar: "নতুন চ্যাট" sits at the far left like the prototype */
.st-key-new_chat {{
  position: fixed;
  top: 0;
  left: 16px;
  z-index: 999;
  height: 52px;
  display: flex;
  align-items: center;
  width: auto !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   18.  prefers-reduced-motion
═══════════════════════════════════════════════════════════════════ */
@media (prefers-reduced-motion: reduce) {{
  .iq-composer-wrap::before,
  .iq-composer-wrap::after,
  .iq-home-composer [data-testid="stForm"]::before,
  .iq-home-composer [data-testid="stForm"]::after,
  [data-testid="stChatInputContainer"]::before,
  [data-testid="stChatInputContainer"]::after {{
    animation: none !important;
  }}
  .iq-typing i {{ animation: none !important; }}
  .stSpinner > div {{ animation: none !important; }}
  .hcard--flash {{ animation: none !important; }}
  .hcard-skeleton {{ animation: none !important; }}
}}

/* ═══════════════════════════════════════════════════════════════════
   19.  Home viewport centering
═══════════════════════════════════════════════════════════════════ */
[data-testid="stMain"],
[data-testid="stAppViewContainer"] > section[data-testid="stMain"] {{
  min-height: 100vh;
}}
[data-testid="stMain"] .stElementContainer:has(iframe) {{
  margin: 0 !important;
  padding: 0 !important;
}}
/* Centre the Home hero vertically. Scoped to the hero container ONLY:
   a page-wide :has(iframe) rule also matched Hadith Books (which has
   script iframes) and, with justify-content:center on overflowing content,
   pushed the top of the list out of reach. */
.st-key-home_hero {{
  min-height: calc(100vh - 140px) !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
}}

/* Infinite scroll: the load-more buttons stay in the DOM (the scroll
   listener clicks them) but are never visible. */
.st-key-load_more,
.st-key-load_more_search {{
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.iq-loading-more {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 44px;
  color: var(--muted);
  font-size: 14px;
}}
.iq-loading-more .iq-spin {{
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--line);
  border-top-color: var(--accent);
  animation: iq-rot 0.8s linear infinite;
}}
@keyframes iq-rot {{ to {{ transform: rotate(360deg); }} }}
@media (prefers-reduced-motion: reduce) {{
  .iq-loading-more .iq-spin {{ animation: none; }}
}}
/* Hidden relay elements must have zero size so they don't push layout */
.st-key-home_relay_input,
.st-key-home_relay_submit,
.st-key-iq_pill_trigger {{
  height: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
  opacity: 0 !important;
  pointer-events: none !important;
}}

/* ═══════════════════════════════════════════════════════════════════
   20.  Scrollbar styling (fix item 10: dark coverage)
═══════════════════════════════════════════════════════════════════ */
::-webkit-scrollbar        {{ width: 4px; }}
::-webkit-scrollbar-track  {{ background: transparent; }}
::-webkit-scrollbar-thumb  {{ background: var(--line); border-radius: 2px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--muted); }}

/* ═══════════════════════════════════════════════════════════════════
   21.  Streamlit container border override (fix item 4)
        Remove the white "page" look of Streamlit's default border
═══════════════════════════════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {{
  border: 0 !important;
  background: transparent !important;
}}
"""
