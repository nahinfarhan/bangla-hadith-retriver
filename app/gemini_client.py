"""
gemini_client.py — Shared Gemini client via Vertex AI SDK
==========================================================
Single source of truth for all Gemini calls across the app.

Authentication:
  Uses Application Default Credentials (ADC) — the SDK automatically picks up
  the service-account key from GOOGLE_APPLICATION_CREDENTIALS.  No API key
  strings anywhere in this file.

Environment variables (set in .env / Docker --env-file):
  GOOGLE_APPLICATION_CREDENTIALS  path to service-account JSON key file
  GCP_PROJECT_ID                  Google Cloud project ID
  GCP_REGION                      Vertex AI region (default: us-central1)

Usage:
    from gemini_client import call_gemini, get_gemini_status

    answer, _ = call_gemini("Your prompt here")
    print(get_gemini_status())
"""

import os
from pathlib import Path
from typing import Tuple, Iterator

import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold,
)

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"   # Vertex AI model ID

# Safety settings — mirror the old behaviour (BLOCK_NONE across all categories)
_SAFETY_SETTINGS = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.OFF,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.OFF,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.OFF,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.OFF,
    ),
]


# ── .env loader ───────────────────────────────────────────────────────────────

def _load_dotenv() -> None:
    """Load .env file into os.environ if present (does not overwrite existing vars)."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


# ── Vertex AI initialisation (lazy, once) ─────────────────────────────────────

_vertexai_initialised = False


def _ensure_vertexai() -> None:
    """Initialise the Vertex AI SDK once, using env vars for project/region."""
    global _vertexai_initialised
    if _vertexai_initialised:
        return

    project = os.environ.get("GCP_PROJECT_ID", "")
    region  = os.environ.get("GCP_REGION", "us-central1")

    if not project:
        raise RuntimeError(
            "GCP_PROJECT_ID is not set. "
            "Add it to .env or pass it as an environment variable."
        )

    # GOOGLE_APPLICATION_CREDENTIALS is read automatically by the SDK — no
    # explicit credentials argument needed here.
    vertexai.init(project=project, location=region)
    _vertexai_initialised = True


# ── Public API ────────────────────────────────────────────────────────────────

def call_gemini(
    prompt: str,
    # Legacy keyword arguments kept for call-site compatibility; ignored now
    # that auth is handled by ADC rather than per-request API keys.
    extra_keys_raw: str = "",   # no-op — retained so call sites don't break
    max_tokens: int = 8192,
    temperature: float = 0.3,
) -> Tuple[str, str]:
    """
    Send a prompt to Gemini via Vertex AI and return the full response.

    Args:
        prompt:         The prompt to send.
        extra_keys_raw: Ignored (kept for backward compatibility).
        max_tokens:     Maximum output tokens (default 8192 — Gemini 2.5 Flash
                        uses an internal thinking budget that consumes tokens
                        before producing visible text, so 1024 is too small).
        temperature:    Sampling temperature.

    Returns:
        (answer_text, model_id)  — model_id is the GEMINI_MODEL string.

    Raises:
        RuntimeError: If Vertex AI is not configured or the call fails.
    """
    _ensure_vertexai()

    model = GenerativeModel(GEMINI_MODEL)
    generation_config = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        top_p=0.9,
    )

    response = model.generate_content(
        prompt,
        generation_config=generation_config,
        safety_settings=_SAFETY_SETTINGS,
    )

    text = response.text.strip() if response.text else ""
    if not text:
        raise RuntimeError("Vertex AI Gemini returned an empty response.")

    return text, GEMINI_MODEL


def stream_gemini(
    prompt: str,
    extra_keys_raw: str = "",   # no-op — retained for call-site compatibility
    max_tokens: int = 8192,
    temperature: float = 0.3,
) -> Iterator[str]:
    """
    Stream a Gemini response token-by-token via Vertex AI.

    Yields text chunks as they arrive so the UI can render progressively
    instead of waiting for the full response.

    Args:
        prompt:         The prompt to send.
        extra_keys_raw: Ignored (kept for backward compatibility).
        max_tokens:     Maximum output tokens.
        temperature:    Sampling temperature.

    Yields:
        str — successive text chunks from the model.

    Raises:
        RuntimeError: If Vertex AI is not configured or the stream fails.
    """
    _ensure_vertexai()

    model = GenerativeModel(GEMINI_MODEL)
    generation_config = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        top_p=0.9,
    )

    responses = model.generate_content(
        prompt,
        generation_config=generation_config,
        safety_settings=_SAFETY_SETTINGS,
        stream=True,
    )

    for chunk in responses:
        try:
            text = chunk.text
            if text:
                yield text
        except Exception:
            # Some chunks (e.g. final usage metadata) have no .text — skip them
            continue
    """
    Send a prompt to Gemini via Vertex AI and return the response.

    Args:
        prompt:         The prompt to send.
        extra_keys_raw: Ignored (kept for backward compatibility).
        max_tokens:     Maximum output tokens (default 8192 — Gemini 2.5 Flash
                        uses an internal thinking budget that consumes tokens
                        before producing visible text, so 1024 is too small).
        temperature:    Sampling temperature.

    Returns:
        (answer_text, model_id)  — model_id is the GEMINI_MODEL string.

    Raises:
        RuntimeError: If Vertex AI is not configured or the call fails.
    """
    _ensure_vertexai()

    model = GenerativeModel(GEMINI_MODEL)
    generation_config = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        top_p=0.9,
    )

    response = model.generate_content(
        prompt,
        generation_config=generation_config,
        safety_settings=_SAFETY_SETTINGS,
    )

    text = response.text.strip() if response.text else ""
    if not text:
        raise RuntimeError("Vertex AI Gemini returned an empty response.")

    return text, GEMINI_MODEL


def get_gemini_status() -> str:
    """Return a human-readable Vertex AI configuration status string."""
    project = os.environ.get("GCP_PROJECT_ID", "")
    region  = os.environ.get("GCP_REGION", "us-central1")
    creds   = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")

    if not project:
        return "⚠️ GCP_PROJECT_ID not set — Vertex AI unavailable"
    if not creds:
        return f"⚠️ GOOGLE_APPLICATION_CREDENTIALS not set (project: {project})"
    return (
        f"✅ Vertex AI ready · project={project} · "
        f"region={region} · model={GEMINI_MODEL}"
    )


# ── Legacy shims (used by main.py sidebar) ───────────────────────────────────

def get_key_status(extra_keys_raw: str = "") -> str:
    """Deprecated shim — returns Vertex AI status instead of key list."""
    return get_gemini_status()


def get_active_key_count(extra_keys_raw: str = "") -> int:
    """Deprecated shim — returns 1 if Vertex AI is configured, else 0."""
    project = os.environ.get("GCP_PROJECT_ID", "")
    creds   = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    return 1 if (project and creds) else 0
