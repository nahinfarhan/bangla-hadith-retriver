"""
app/ui — UI package for the Bangla Islamic Q&A Streamlit app.

Exposes a helper to load logo PNGs as base64 data URIs so they can
be embedded directly in CSS / HTML without extra HTTP requests.
"""
import base64
from pathlib import Path

_ASSETS = Path(__file__).parent / "assets"


def _load_b64(filename: str) -> str:
    """Return the base64-encoded content of an asset file, or '' on error."""
    path = _ASSETS / filename
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""


# Pre-load at import time so main.py can reference them cheaply.
LOGO_LIGHT_B64: str = _load_b64("logo-light.png")
LOGO_DARK_B64: str  = _load_b64("logo-dark.png")
LOGO_MASK_B64: str  = _load_b64("logo-mask.png")
