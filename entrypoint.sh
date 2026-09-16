#!/bin/sh
# entrypoint.sh
# Builds the hadith vector database on the very first container start,
# then launches Streamlit. On subsequent starts the sentinel file exists
# so the build step is skipped entirely — no wasted time.

set -e

echo "=== Hadith QA App ==="

# Build DB only if not already done
if [ ! -f "data/hadith_vectors/.build_complete" ]; then
    echo "⏳ First run: building hadith vector database from JSON …"
    python3 app/build_hadith_db.py
else
    echo "✅ Hadith database already built — skipping rebuild."
fi

echo "🚀 Starting Streamlit …"
exec streamlit run app/main.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
