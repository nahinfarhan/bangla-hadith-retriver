"""
app/ui/scripts.py — Injected JavaScript strings.

Each function returns a self-contained HTML/JS snippet to be injected once
via st.components.v1.html(script, height=0).

All scripts use window.parent.document to reach the Streamlit page DOM
(the component renders inside an iframe).

Fix item 2: copy handler now reads from a hidden <div> via data-copy-id
instead of from a data-copy-text attribute (which broke on quotes/newlines).
"""
import json


def theme_toggle_script() -> str:
    """Theme toggle with SVG moon/sun icons (matching Appendix A).

    - Reads localStorage['theme'] (falls back to prefers-color-scheme).
    - Sets data-theme on the parent <html> element.
    - Renders the 48px round theme button fixed at right edge
      (top-right corner at <=900px).

    The button and its click handler are installed by a <script> element
    created in the *parent* document, so they run in the main page's JS
    context. Before, the handler lived inside this component iframe; when
    Streamlit re-created the iframe on a rerun / view switch the handler
    died and the button stopped responding.
    """
    sun_svg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
    moon_svg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
    css = (
        "#iq-theme-btn{position:fixed;z-index:9999;top:50%;"
        "right:max(16px,env(safe-area-inset-right,0px));transform:translateY(-50%);"
        "width:48px;height:48px;border-radius:50%;border:1px solid var(--line);"
        "background:var(--surface);color:var(--ink);cursor:pointer;display:flex;"
        "align-items:center;justify-content:center;box-shadow:var(--shadow);"
        "transition:border-color .2s,color .2s,background-color .2s;padding:0}"
        "#iq-theme-btn svg{width:20px;height:20px;display:block;pointer-events:none}"
        "#iq-theme-btn:hover{border-color:var(--accent);color:var(--accent)}"
        "@media (max-width:899px){#iq-theme-btn{top:calc(4px + env(safe-area-inset-top,0px));"
        "right:max(8px,env(safe-area-inset-right,0px));transform:none;width:44px;height:44px;box-shadow:none}}"
    )
    # Code that runs inside the parent page (installed once per page load).
    parent_code = """
(function(){
  if (window.__iqTheme) { window.__iqTheme.sync(); return; }
  var SUN = %(sun)s, MOON = %(moon)s;
  var html = document.documentElement;
  function stored(){ try { return localStorage.getItem('theme'); } catch(e) { return null; } }
  function systemDark(){ return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches; }
  function current(){ return html.getAttribute('data-theme') || stored() || (systemDark() ? 'dark' : 'light'); }
  function paintBtn(t){
    var b = document.getElementById('iq-theme-btn'); if (!b) return;
    b.innerHTML = t === 'dark' ? SUN : MOON;
    b.setAttribute('aria-label', t === 'dark' ? 'লাইট থিম' : 'ডার্ক থিম');
    b.setAttribute('aria-pressed', t === 'dark' ? 'true' : 'false');
  }
  function apply(t){ html.setAttribute('data-theme', t); paintBtn(t); }
  function ensureBtn(){
    if (!document.getElementById('iq-theme-style')) {
      var st = document.createElement('style'); st.id = 'iq-theme-style';
      st.textContent = %(css)s; document.head.appendChild(st);
    }
    var old = document.getElementById('iq-theme-btn');
    // Replace a button left by the previous script version (it carries its
    // own click listener, which would toggle twice together with ours).
    if (old && old.getAttribute('data-iq') !== '2') { old.remove(); old = null; }
    if (!old) {
      var b = document.createElement('button');
      b.id = 'iq-theme-btn'; b.type = 'button'; b.setAttribute('data-iq', '2');
      document.body.appendChild(b);
    }
    paintBtn(current());
  }
  // One delegated listener on the document: works even if the button
  // element is ever replaced.
  document.addEventListener('click', function(e){
    if (!e.target.closest || !e.target.closest('#iq-theme-btn')) return;
    var next = current() === 'dark' ? 'light' : 'dark';
    apply(next);
    try { localStorage.setItem('theme', next); } catch(ex) {}
  });
  try {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e){
      if (!stored()) apply(e.matches ? 'dark' : 'light');
    });
  } catch(e) {}
  // Keep the icon right if anything else changes data-theme.
  new MutationObserver(function(){ paintBtn(html.getAttribute('data-theme') || 'light'); })
    .observe(html, {attributes: true, attributeFilter: ['data-theme']});
  window.__iqTheme = { sync: function(){ ensureBtn(); apply(stored() || current()); } };
  window.__iqTheme.sync();
})();
""" % {"sun": json.dumps(sun_svg), "moon": json.dumps(moon_svg), "css": json.dumps(css)}
    return f"""
<script>
(function() {{
  var pd = window.parent.document;
  var s = pd.createElement('script');
  s.textContent = {json.dumps(parent_code)};
  pd.body.appendChild(s);
  pd.body.removeChild(s);
}})();
</script>
"""


def copy_handler_script() -> str:
    """Delegated copy handler injected once into the parent document.

    Fix item 2: reads text from a hidden <div> identified by data-copy-id
    (not from a data-copy-text attribute). This avoids breakage when the
    hadith text contains quotes, newlines, or HTML special characters.

    The handler:
      1. Finds the closest element with data-copy-id on click.
      2. Reads document.getElementById(copyId).textContent.
      3. Calls navigator.clipboard.writeText with execCommand('copy') fallback.
      4. Shows a toast "কপি হয়েছে" (or "কপি করা যায়নি" on failure).
    """
    return """
<script>
(function() {
  var pd = window.parent.document;
  if (pd.__iqCopyHandlerInstalled) return;
  pd.__iqCopyHandlerInstalled = true;

  function showToast(msg) {
    var t = pd.getElementById('iq-copy-toast');
    if (!t) {
      t = pd.createElement('div');
      t.id = 'iq-copy-toast';
      t.setAttribute('role', 'status');
      t.style.cssText = [
        'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);',
        'background:var(--ink);color:var(--bg);',
        'padding:9px 20px;border-radius:999px;font-size:14px;',
        'z-index:99999;pointer-events:none;',
        'font-family:Hind Siliguri,sans-serif;',
        'transition:opacity 0.3s;opacity:0;'
      ].join('');
      pd.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = '1';
    clearTimeout(t.__hideTimer);
    t.__hideTimer = setTimeout(function() { t.style.opacity = '0'; }, 2200);
  }

  pd.addEventListener('click', function(e) {
    // Fix item 2: read from hidden div via data-copy-id
    var el = e.target.closest('[data-copy-id]');
    if (!el) return;
    var copyId = el.getAttribute('data-copy-id');
    if (!copyId) return;
    var textEl = pd.getElementById(copyId);
    if (!textEl) return;
    var text = textEl.textContent || '';
    if (!text) return;

    function doCopy() {
      if (window.parent.navigator.clipboard && window.parent.navigator.clipboard.writeText) {
        window.parent.navigator.clipboard.writeText(text)
          .then(function() { showToast('কপি হয়েছে'); })
          .catch(function() { fallbackCopy(text); });
      } else {
        fallbackCopy(text);
      }
    }

    function fallbackCopy(text) {
      try {
        var ta = pd.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0;';
        pd.body.appendChild(ta);
        ta.focus();
        ta.select();
        var ok = pd.execCommand('copy');
        pd.body.removeChild(ta);
        showToast(ok ? 'কপি হয়েছে' : 'কপি করা যায়নি');
      } catch(e) {
        showToast('কপি করা যায়নি');
      }
    }

    doCopy();
  });
})();
</script>
"""


def infinite_scroll_script(sentinel_id: str = "sentinel_load_more") -> str:
    """Scroll-based load-more, rendered with st.components.v1.html.

    st.html() strips <script> (DOMPurify), so this must be an iframe
    component.  To survive iframe re-creation on reruns, the iframe injects
    the real listener as a <script> into the PARENT document, guarded by a
    flag on the parent window so it is installed exactly once per page load.
    The listener measures the parent scroll container and clicks whichever
    'আরও দেখুন' button (load_more / load_more_search) is present, only when
    the user is within 300px of the bottom, at most once per 1.5s.
    """
    parent_code = r"""
(function () {
  if (window.__iqScrollInstalled) return;
  window.__iqScrollInstalled = true;
  var busy = false, timer = null;
  function scrollers() {
    return [
      document.querySelector('[data-testid="stMain"]'),
      document.querySelector('[data-testid="stAppViewContainer"]'),
      document.scrollingElement || document.documentElement
    ].filter(Boolean);
  }
  function nearBottom() {
    var list = scrollers();
    for (var i = 0; i < list.length; i++) {
      var el = list[i];
      if (el.scrollHeight > el.clientHeight + 10 &&
          el.scrollTop > 0 &&
          el.scrollHeight - el.scrollTop - el.clientHeight < 300) return true;
    }
    return false;
  }
  function findBtn() {
    return document.querySelector(
      '.st-key-load_more button, .st-key-load_more_search button');
  }
  var pending = false;
  function cardCount() {
    return document.querySelectorAll('[class*="st-key-hcard_"]').length;
  }
  function check() {
    if (busy) { pending = true; return; }   // user scrolled while loading
    if (!nearBottom()) return;
    var b = findBtn();
    if (!b) return;                          // end of list
    busy = true; pending = false;
    var before = cardCount(), started = Date.now();
    b.click();
    // Stay busy until the new cards are rendered (or 8s), so one scroll
    // gesture never loads two batches.  If the user kept scrolling while
    // the batch loaded, check again once it is in.
    (function wait() {
      if (cardCount() > before || Date.now() - started > 8000) {
        busy = false;
        if (pending) { pending = false; setTimeout(check, 150); }
        return;
      }
      setTimeout(wait, 150);
    })();
  }
  // Throttle (not debounce): check at most every 200ms DURING continuous
  // scrolling, plus one trailing check after the user stops.  A debounce
  // never fires while the user keeps scrolling, which stalled loading.
  var lastRun = 0;
  function onScroll() {
    var now = Date.now();
    clearTimeout(timer);
    if (now - lastRun >= 200) { lastRun = now; check(); }
    timer = setTimeout(function () { lastRun = Date.now(); check(); }, 200);
  }
  // 'scroll' does not fire once the page is already at the very bottom, so
  // also listen to the user's scroll intent (wheel / touch / keys).
  document.addEventListener('scroll', onScroll, { passive: true, capture: true });
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('wheel', function (e) { if (e.deltaY > 0) onScroll(); }, { passive: true });
  window.addEventListener('touchmove', onScroll, { passive: true });
  window.addEventListener('keydown', function (e) {
    if (['ArrowDown', 'PageDown', 'End', ' '].indexOf(e.key) >= 0) onScroll();
  });
})();
"""
    import json as _json
    return f"""
<script>
(function () {{
  var pd = window.parent.document;
  if (window.parent.__iqScrollInstalled) return;
  var s = pd.createElement('script');
  s.textContent = {_json.dumps(parent_code)};
  pd.body.appendChild(s);
}})();
</script>
"""


def scroll_to_summary_script() -> str:
    """Scroll the AI summary panel into view after it is opened."""
    return """
<script>
(function () {
  var pd = window.parent.document;
  function go() {
    var el = pd.querySelector('.st-key-ai_summary_panel');
    if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  [60, 300, 800].forEach(function (t) { setTimeout(go, t); });
})();
</script>
"""


def scroll_to_last_question_script() -> str:
    """Scroll the newest user question bubble to the top of the viewport.

    Rendered with st.components.v1.html(height=0).  Runs right after a new
    question is shown (and again after the final rerun re-renders the thread),
    so focus stays on the new question and its answer instead of the old
    conversation.  The user can still scroll up freely afterwards.
    Retries briefly because Streamlit lays the page out asynchronously.
    """
    return """
<script>
(function () {
  var pd = window.parent.document;
  function go() {
    var bubbles = pd.querySelectorAll('.iq-msg-user');
    if (!bubbles.length) return;
    var el = bubbles[bubbles.length - 1];
    el.style.scrollMarginTop = '72px';
    el.scrollIntoView({ block: 'start', behavior: 'auto' });
  }
  go();
  [100, 300, 700].forEach(function (t) { setTimeout(go, t); });
})();
</script>
"""


def aria_patch_script() -> str:
    """Patches aria-label onto icon-only Streamlit buttons and adds
    role='status' to toast containers. Uses a MutationObserver for rerenders.
    """
    return """
<script>
(function() {
  var pd = window.parent.document;
  if (pd.__iqAriaPatchInstalled) return;
  pd.__iqAriaPatchInstalled = true;

  var PATCHES = [
    ['st-key-retry',           'আবার চেষ্টা করুন'],
    ['st-key-load_more',       'আরও হাদীস লোড করুন'],
    ['st-key-load_more_search', 'আরও হাদীস লোড করুন'],
    ['st-key-clear_search',    'সার্চ মুছুন'],
    ['st-key-h_go',            'নম্বরে যান'],
    ['st-key-pill_hadith',      'হাদীস গ্রন্থ খুলুন'],
    ['st-key-new_chat',         'নতুন চ্যাট শুরু করুন'],
    ['st-key-back_to_chat',     'চ্যাটে ফিরুন'],
  ];

  function applyPatches() {
    PATCHES.forEach(function(p) {
      var container = pd.querySelector('.' + p[0]);
      if (!container) {
        // also try partial match (st-key-xxx_yyy → class*="st-key-xxx")
        container = pd.querySelector('[class*="' + p[0] + '"]');
      }
      if (!container) return;
      var btn = container.querySelector('button');
      if (btn && !btn.getAttribute('aria-label')) {
        btn.setAttribute('aria-label', p[1]);
      }
    });

    pd.querySelectorAll('[data-testid="stToast"], .stToast').forEach(function(t) {
      if (!t.getAttribute('role')) t.setAttribute('role', 'status');
    });
  }

  applyPatches();

  var observer = new MutationObserver(applyPatches);
  observer.observe(pd.body, { childList: true, subtree: true });
})();
</script>
"""
