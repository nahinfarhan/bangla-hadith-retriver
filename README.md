---
title: Hadith QA — Bangla Islamic Q&A
emoji: 🕌
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Bangla Hadith Retriever 🕌

A semantic search and conversational Q&A system over **20,505 hadiths** from Ṣaḥīḥ al-Bukhārī, Ṣaḥīḥ Muslim, and Jāmiʿ at-Tirmidhī — supporting both Bangla and English queries.

**Live demo:** [nahinfarhan/bangla-hadith-retriver on HF Spaces](https://huggingface.co/spaces/nahinfarhan/bangla-hadith-retriver)

---

## What I Built

The goal was to build a retrieval system that can answer Islamic questions in **Bangla** — a language that is severely underrepresented in NLP. Most existing hadith search tools work only in Arabic or English. This system lets a Bengali-speaking user ask a question like *"নামাজ কীভাবে পড়তে হয়?"* and get semantically relevant hadiths back, ranked by actual meaning — not just keyword overlap.

### The Problem

Keyword search (BM25 alone) breaks down with Bangla because:
- Bangla is morphologically rich — the same root word appears in dozens of inflected forms
- Transliteration inconsistency across hadith collections
- No strong pre-trained Bangla retrieval model existed for this domain

### The Solution

A **multi-stage hybrid retrieval pipeline** combining:

1. **Query reframing** via Gemini — expands a single user query into 3 semantically varied variants to improve recall
2. **Dense retrieval** — a fine-tuned `multilingual-e5-base` model encodes both query and hadith passages into 768-dimensional vectors stored in ChromaDB
3. **BM25 retrieval** — sparse keyword matching over the same corpus using `rank_bm25`
4. **RRF fusion** — Reciprocal Rank Fusion (k=60) merges the dense and BM25 ranked lists
5. **Cross-encoder re-ranking** — `cross-encoder/ms-marco-MiniLM-L-6-v2` re-scores the fused candidates to produce the final ranked output
6. **Gemini-powered answer synthesis** — the top retrieved hadiths are passed to Gemini as context to generate a grounded, cited answer

---

## Architecture

```
User Query (Bangla or English)
        │
        ▼
┌───────────────────┐
│  Query Reframer   │  Gemini → 3 query variants
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Dense  │ │  BM25  │  Per variant, top-N results each
│ Search │ │ Search │
│(ChromaDB│ │(rank_  │
│+ e5-bn)│ │ bm25)  │
└────┬───┘ └───┬────┘
     └────┬────┘
          ▼
┌──────────────────┐
│   RRF Fusion     │  score = Σ 1/(k + rank),  k=60
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Cross-Encoder    │  ms-marco-MiniLM-L-6-v2
│  Re-ranking      │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Gemini Synthesis│  (optional — requires API key)
│  grounded answer │
└──────────────────┘
         ▼
    Final Results
```

---

## The Fine-tuned Model

**Model:** [`nahinfarhan/hadith-retriever-bn-v2`](https://huggingface.co/nahinfarhan/hadith-retriever-bn-v2)

- **Base:** `intfloat/multilingual-e5-base` (XLM-RoBERTa backbone)
- **Output:** 768-dimensional dense vectors, cosine similarity
- **Max tokens:** 256
- **Training loss:** `MultipleNegativesRankingLoss` (scale=20, cosine similarity)
- **Epochs:** 7
- **Training samples:** 21,389 Bangla hadith QA pairs

### Training Data Format

Each training sample is an `(anchor, positive)` pair:

| anchor | positive |
|--------|----------|
| `query: রমজান মাসে রোজা অবস্থায় সহবাস করলে কাফফারা কী?` | `passage: বর্ণিত। এক ব্যক্তি রমজান মাসে তার স্ত্রীর সাথে সহবাস করে...` |
| `query: জানাজার নামাজ পড়লে কতটুকু সওয়াব পাওয়া যায়?` | `passage: নবী (ﷺ) বললেন, তা উহুদ পাহাড় সমতুল্য...` |

The `query:` and `passage:` prefixes follow the `multilingual-e5` instruction format. At inference time, queries are prefixed with `query:` and hadith texts with `passage:`.

### Training Pairs Generation

Training pairs were generated from the raw hadith JSON files using a semi-automated pipeline:
- Extract the hadith text from each entry
- Generate a plausible question for the hadith using Gemini (`gemini-3.1-flash`)
- Store as `(question, hadith_text)` pairs in JSONL format
- Files: `data/bukhari_training_pairs.jsonl`, `data/bukhari_enhanced_pairs.jsonl`, `data/muslim_enhanced_pairs.jsonl`

---

## Data

### Hadith Corpus

**Dataset:** [`nahinfarhan/hadith-vectors-db`](https://huggingface.co/datasets/nahinfarhan/hadith-vectors-db)

The dataset contains:
- Pre-built **ChromaDB vector store** (`data/hadith_vectors/`) — 284 MB, contains the embedded vectors for all 20,505 hadiths, ready to use without re-embedding
- Raw hadith JSON files:
  - `hadiths.json` — Ṣaḥīḥ al-Bukhārī (7,563 hadiths)
  - `muslim_hadiths.json` — Ṣaḥīḥ Muslim (7,470 hadiths)
  - `tirmidhi_hadiths.json` — Jāmiʿ at-Tirmidhī (3,956 hadiths)

Each JSON entry has the structure:
```json
{
  "hadith_id": 1,
  "book": "Sahih_Bukhari",
  "text": "বর্ণনাকারীঃ আবূ হুরাইরা (রাঃ)...",
  "narrator": "আবূ হুরাইরা (রাঃ)",
  "grade": "সহিহ",
  "word_count": 87
}
```

### Downloading the Data from Hugging Face

```bash
pip install huggingface_hub

python - <<'EOF'
from huggingface_hub import snapshot_download

# Download the full vector DB + raw JSON files
snapshot_download(
    repo_id="nahinfarhan/hadith-vectors-db",
    repo_type="dataset",
    local_dir="./data"
)
EOF
```

Or with the `huggingface-cli`:
```bash
huggingface-cli download nahinfarhan/hadith-vectors-db \
    --repo-type dataset \
    --local-dir ./data
```

### Downloading the Fine-tuned Model

```bash
huggingface-cli download nahinfarhan/hadith-retriever-bn-v2 \
    --local-dir ./models/hadith-retriever-bn-v2
```

---

## Running Locally

### Prerequisites

- Python 3.11+
- ~3 GB disk space (model + vector DB)
- A [Gemini API key](https://aistudio.google.com) (free) for AI-generated answers — optional, search works without it

### Step 1 — Clone the repo

```bash
git clone https://github.com/nahinfarhan/bangla-hadith-retriver.git
cd bangla-hadith-retriver
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Download data and model from Hugging Face

```bash
pip install huggingface_hub

# Download vector DB and raw hadith JSON
huggingface-cli download nahinfarhan/hadith-vectors-db \
    --repo-type dataset \
    --local-dir ./data

# Download fine-tuned embedding model
huggingface-cli download nahinfarhan/hadith-retriever-bn-v2 \
    --local-dir ./models/hadith-retriever-bn-v2
```

After this your directory should look like:
```
bangla-hadith-retriver/
├── app/
├── data/
│   ├── hadith_vectors/       ← ChromaDB (pre-built)
│   ├── hadiths.json
│   ├── muslim_hadiths.json
│   └── tirmidhi_hadiths.json
└── models/
    └── hadith-retriever-bn-v2/
```

### Step 4 — Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your Gemini key(s)
```

```env
GEMINI_API_KEY=your_key_here
# Or multiple keys (rotated automatically to avoid rate limits):
GEMINI_API_KEYS=key1,key2,key3
```

### Step 5 — Run the app

```bash
streamlit run app/main.py
```

The app will be available at `http://localhost:8501`.

> **Note:** On first run the app loads the ChromaDB and the embedding model into memory (~1-2 minutes). Subsequent loads use Streamlit's `@st.cache_resource` so it stays warm.

---

## Running with Docker

If you want an environment identical to the HF Spaces deployment:

```bash
# Build
docker build -t bangla-hadith-retriver .

# Run
docker run -p 7860:7860 \
  -e GEMINI_API_KEYS="your_key_here" \
  bangla-hadith-retriver
```

The app will be at `http://localhost:7860`.

> **Important:** The Dockerfile expects `data/hadith_vectors/`, `data/*.json`, and `models/hadith-retriever-bn-v2/` to be present locally before building. Download them first (Step 3 above).

---

## Rebuilding the Vector Database from Scratch

If you want to re-embed all hadiths yourself rather than using the pre-built ChromaDB:

```bash
python app/build_hadith_db.py
```

This will:
1. Load all hadiths from the three JSON files
2. Encode each hadith with the fine-tuned `hadith-retriever-bn-v2` model
3. Store embeddings in `data/hadith_vectors/` (ChromaDB format)

Runtime: ~10 minutes on CPU, ~2 minutes with a GPU.

---

## Key Source Files

| File | Purpose |
|------|---------|
| `app/main.py` | Streamlit UI — search tab, chat tab, direct lookup |
| `app/hybrid_search.py` | Full hybrid pipeline: BM25 + Dense + RRF + re-ranking |
| `app/hadith_search.py` | Dense-only search using the fine-tuned e5 model |
| `app/bm25_index.py` | BM25 index over the hadith corpus (`rank_bm25`) |
| `app/reranker.py` | Cross-encoder re-ranking (`ms-marco-MiniLM-L-6-v2`) |
| `app/query_reframer.py` | Query expansion via Gemini |
| `app/hadith_chat.py` | Grounded answer synthesis via Gemini |
| `app/gemini_client.py` | Gemini API client with multi-key rotation and rate-limit handling |
| `app/embed.py` | Wrapper around the fine-tuned sentence-transformers model |
| `app/vector_store.py` | ChromaDB wrapper for document ingestion and search |
| `app/ingest.py` | PDF/TXT document ingestor for the general doc search tab |
| `app/hadith_processor.py` | PDF processor for extracting clean Bangla text from hadithbd.com PDFs |
| `app/build_hadith_db.py` | Script to build the ChromaDB vector store from the raw JSON files |

---

## Live Deployment

The app is deployed on **Hugging Face Spaces** as a Docker Space:

🔗 **[nahinfarhan/bangla-hadith-retriver](https://huggingface.co/spaces/nahinfarhan/bangla-hadith-retriver)**

The Space bakes the pre-built ChromaDB and the fine-tuned model directly into the Docker image, so there is no cold-start embedding step. The image is ~3 GB.

To deploy your own copy to HF Spaces:
1. Create a new Space at huggingface.co/spaces — choose **Docker** as the SDK
2. Set the secret `GEMINI_API_KEYS` in the Space settings
3. Push this repo (with data and models included) to the Space's git remote:

```bash
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE
git push space main
```

---

## Tech Stack

| Component | Library / Service |
|-----------|------------------|
| UI | Streamlit |
| Vector store | ChromaDB 0.4.24 |
| Embedding model | sentence-transformers + fine-tuned multilingual-e5-base |
| Sparse retrieval | rank-bm25 |
| Re-ranking | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Answer generation | Google Gemini (gemini-1.5-flash) |
| PDF parsing | pdfplumber |
| Deployment | Docker + Hugging Face Spaces |

---

## Limitations

- The cross-encoder (`ms-marco-MiniLM-L-6-v2`) was trained on English MS MARCO data. It works reasonably well as a re-ranker but a Bangla-native cross-encoder would improve results further.
- Gemini-generated answers are only as good as the retrieved hadiths. If retrieval misses the relevant hadith, the answer will be wrong or incomplete.
- The BM25 index is rebuilt in memory on startup from the JSON files. For a production deployment, persisting the index to disk would reduce startup time.
- The system does not cover all hadith collections — only Bukhari, Muslim, and Tirmidhi.

---

## License

MIT
