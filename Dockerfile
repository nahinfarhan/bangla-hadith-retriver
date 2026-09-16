# ─────────────────────────────────────────────────────────────────────────────
# Hadith QA — Hugging Face Spaces Docker image
#
# What gets baked in:
#   • Python deps (CPU-only torch, sentence-transformers, chromadb …)
#   • app/           — Streamlit source
#   • data/hadith_vectors/  — pre-built ChromaDB (273 MB, 20 499 hadiths)
#   • data/*.json    — raw hadith JSON (Bukhari / Muslim / Tirmidhi)
#   • models/hadith-retriever-bn-v2/  — fine-tuned embed model (~1 GB)
#     ↳ checkpoint-3745/ is excluded (.dockerignore) — training artefact only
#   • .streamlit/    — theme + server config
#
# HF Spaces requirements:
#   • Non-root user with UID/GID 1000
#   • App must listen on port 7860
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── System deps ───────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (UID 1000 required by HF Spaces) ───────────────────────────
RUN useradd -m -u 1000 appuser

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements-docker.txt .
RUN pip install --no-cache-dir --timeout 1000 -r requirements-docker.txt

# ── Application source ────────────────────────────────────────────────────────
COPY app/                          ./app/
COPY .streamlit/                   ./.streamlit/

# ── Hadith data (JSON sources + pre-built vector DB) ─────────────────────────
# Copy only the three hadith JSON files needed at runtime
COPY data/hadiths.json             ./data/hadiths.json
COPY data/muslim_hadiths.json      ./data/muslim_hadiths.json
COPY data/tirmidhi_hadiths.json    ./data/tirmidhi_hadiths.json

# Pre-built ChromaDB — skips the 10-minute first-run build on HF Spaces
COPY data/hadith_vectors/          ./data/hadith_vectors/

# ── Fine-tuned embedding model (~1 GB, checkpoint-3745 excluded) ──────────────
COPY models/hadith-retriever-bn-v2/ ./models/hadith-retriever-bn-v2/

# ── Runtime directories ───────────────────────────────────────────────────────
RUN mkdir -p data/vectors data/uploaded_docs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:7860/_stcore/health || exit 1

# DB is already built — go straight to Streamlit on port 7860
CMD ["streamlit", "run", "app/main.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
