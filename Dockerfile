# ─────────────────────────────────────────────────────────────────────────────
# Hadith QA — Docker image (dev/VPS)
#
# Data (hadith_vectors/, *.json) and models/ are NOT baked in —
# they are mounted at runtime via docker-compose volumes for fast builds.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── System deps ───────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN useradd -m -u 1000 appuser
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements-docker.txt .
RUN pip install --no-cache-dir --timeout 1000 -r requirements-docker.txt

# ── Application source only (data/models mounted at runtime) ──────────────────
COPY app/ ./app/
COPY .streamlit/ ./.streamlit/

# ── Runtime directories ───────────────────────────────────────────────────────
RUN mkdir -p data/hadith_vectors data/vectors data/uploaded_docs data/query_cache \
             data/feedback /secrets \
    && chown -R appuser:appuser /app /secrets

USER appuser

ENV GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json \
    GCP_REGION=us-central1 \
    PYTHONUNBUFFERED=1

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:7860/_stcore/health || exit 1

CMD ["streamlit", "run", "app/main.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
