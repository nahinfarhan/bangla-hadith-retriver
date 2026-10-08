"""
sentry_init.py — Sentry error tracking initialisation
======================================================
Call init_sentry() once at app startup.  If SENTRY_DSN is not set in the
environment the call is a no-op, so local development is unaffected.

Environment variables (add to /opt/hadith-app/.env on the VPS):
    SENTRY_DSN    — DSN string from your Sentry project settings
                    e.g. https://abc123@o123.ingest.sentry.io/456
    ENVIRONMENT   — "production" / "staging" / "development"  (default: production)
"""

import os


def init_sentry() -> None:
    """Initialise Sentry SDK.  Silent no-op if SENTRY_DSN is not set."""
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get("ENVIRONMENT", "production"),
            # Capture 10 % of transactions for performance tracing.
            # Set to 1.0 for full tracing (higher Sentry quota usage).
            traces_sample_rate=0.1,
            # Attach the user's query to the event so you can see exactly
            # what triggered the error — very useful for debugging.
            send_default_pii=False,
        )
        print("[Sentry] Error tracking active.", flush=True)
    except ImportError:
        print("[Sentry] sentry-sdk not installed — skipping.", flush=True)
    except Exception as e:
        # Never let monitoring setup crash the app
        print(f"[Sentry] Init failed (non-fatal): {e}", flush=True)
