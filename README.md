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

# Hadith QA — Bangla & English Islamic Q&A

A semantic search and question-answering system over **20,499 hadiths** from
Ṣaḥīḥ al-Bukhārī, Ṣaḥīḥ Muslim, and Jāmiʿ at-Tirmidhī — supporting both
Bangla and English queries.

## Features

- **Hybrid search** — BM25 + fine-tuned dense retrieval + RRF fusion + cross-encoder re-ranking
- **Hadith Companion** — conversational Q&A powered by Gemini, grounded in hadith sources
- **Direct lookup** — find any hadith by book and number
- **Bangla-first** — fine-tuned on 21,389 Bangla hadith QA pairs

## Model

Fine-tuned `intfloat/multilingual-e5-base` on a custom Bangla hadith retrieval
dataset using MultipleNegativesRankingLoss over 7 epochs.

## Setup (Gemini API key)

Add your Gemini API key(s) in the sidebar to enable AI-generated answers.
Free keys available at [aistudio.google.com](https://aistudio.google.com).

You can also set the `GEMINI_API_KEYS` secret in the Space settings
(comma-separated if you have multiple keys).
