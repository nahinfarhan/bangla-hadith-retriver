#!/usr/bin/env python3
"""
embed_server.py — Subprocess embeddinhttps://app.kiro.dev/signin?state=48db339e-89b3-4eb0-94d4-ea63688a088a&code_challenge=aQLx_3dIlYLWPiZOPUx7Gk_iLwMMj-bVYj_OcUTpSbs&code_challenge_method=S256&redirect_uri=http%3A%2F%2Flocalhost%3A3128&redirect_from=KiroIDE worker (Python 3.11)
============================================================
Designed to be called by embed.py via subprocess.  This file must be run
with the hadith_qa conda environment (Python 3.11) because the system Python
3.13 free-threading build causes segfaults in PyTorch BERT models.

Protocol (line-delimited JSON over stdin/stdout):
  stdin  →  JSON line: {"texts": ["text1", "text2", ...]}
  stdout →  JSON line: {"embeddings": [[...], [...], ...]}
  stderr →  log/warning output (ignored by caller)

Usage (called automatically by EmbeddingModel in embed.py):
  /opt/anaconda3/envs/hadith_qa/bin/python3.11 app/embed_server.py
"""

import sys
import json
import os
from pathlib import Path

# Silence tokenizers parallelism warning
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from pathlib import Path

# ── Model selection ───────────────────────────────────────────────────────────
# Priority (highest to lowest):
#   1. EMBED_MODEL_OVERRIDE env var  — explicit model name/path (for eval runs)
#   2. Fine-tuned model on disk      — models/hadith-retriever-bn-v2
#   3. Fallback                      — intfloat/multilingual-e5-base
_PROJECT_ROOT   = Path(__file__).parent.parent
_FINETUNED_PATH = _PROJECT_ROOT / "models" / "hadith-retriever-bn-v2"
_FALLBACK_MODEL = "intfloat/multilingual-e5-base"

_override = os.environ.get("EMBED_MODEL_OVERRIDE", "").strip()
if _override:
    # Resolve relative paths against the project root
    _override_path = Path(_override)
    if not _override_path.is_absolute():
        _override_path = _PROJECT_ROOT / _override_path
    MODEL_ID = str(_override_path) if _override_path.exists() else _override
    USE_ST   = True
    print(f"[embed_server] OVERRIDE model: {MODEL_ID}", file=sys.stderr, flush=True)
elif _FINETUNED_PATH.exists():
    MODEL_ID     = str(_FINETUNED_PATH)
    USE_ST       = True   # sentence-transformers API
    print(f"[embed_server] Using fine-tuned model: {MODEL_ID}", file=sys.stderr, flush=True)
else:
    MODEL_ID     = _FALLBACK_MODEL
    USE_ST       = False  # raw transformers API
    print(f"[embed_server] Fine-tuned model not found, using: {MODEL_ID}", file=sys.stderr, flush=True)

MAX_SEQ_LEN = 512

# For e5 models — queries need "query: " prefix, passages get "passage: "
# The fine-tuned model was trained with these prefixes.
QUERY_PREFIX   = "query: "   if USE_ST else ""
PASSAGE_PREFIX = "passage: " if USE_ST else ""


def load_model():
    if USE_ST:
        from sentence_transformers import SentenceTransformer
        print(f"[embed_server] Loading via sentence-transformers...", file=sys.stderr, flush=True)
        model = SentenceTransformer(MODEL_ID)
        print("[embed_server] Model ready.", file=sys.stderr, flush=True)
        return None, model  # tok=None, model=ST model
    else:
        import torch
        from transformers import AutoTokenizer, AutoModel
        print(f"[embed_server] Loading {MODEL_ID} ...", file=sys.stderr, flush=True)
        tok = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModel.from_pretrained(MODEL_ID)
        model.eval()
        print("[embed_server] Model ready.", file=sys.stderr, flush=True)
        return tok, model


def mean_pool(token_embeddings, attention_mask):
    """Mean pooling over non-padding tokens."""
    import torch
    mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (token_embeddings * mask).sum(1) / mask.sum(1).clamp(min=1e-9)


def embed_batch(tok, model, texts):
    if USE_ST:
        # sentence-transformers path
        # Texts prefixed with "passage:" are document passages; everything else is a query
        prefixed = [
            t if t.startswith("passage:") or t.startswith("query:")
            else f"{PASSAGE_PREFIX}{t}"
            for t in texts
        ]
        vecs = model.encode(prefixed, batch_size=32, normalize_embeddings=True)
        return vecs.tolist()
    else:
        import torch
        enc = tok(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=MAX_SEQ_LEN,
        )
        with torch.no_grad():
            out = model(**enc)
        vecs = mean_pool(out.last_hidden_state, enc["attention_mask"])
        return vecs.tolist()


def main():
    tok, model = load_model()

    # Read request lines from stdin until EOF
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            texts = req["texts"]
            embeddings = embed_batch(tok, model, texts)
            response = json.dumps({"embeddings": embeddings})
            print(response, flush=True)
        except Exception as e:
            error = json.dumps({"error": str(e)})
            print(error, flush=True)


if __name__ == "__main__":
    main()
