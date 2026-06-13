# History of Errors and Challenges

This document tracks the technical "face" of errors encountered during the development of DP-generator.

## ❗ Critical Error: Index Not Built
- **Symptom:** API calls to `/api/chat` or `/api/autogen` fail with `400` or `500`.
- **Root Cause:** The vector store is empty or the CSV dataset was not found.
- **Resolution:** Implemented a status check in the UI and a "Build Index" button that triggers the `/api/build-index` endpoint.

## ❗ Challenge: PII Leakage in RAG Context
- **Symptom:** LLM sometimes outputs snippets of real names.
- **Root Cause:** Some names (e.g., "John") are common words and missed by simple regex.
- **Resolution:** Improved regex patterns and added [[Stable Aliases]] to ensure consistent masking.

## ❗ Performance: Embedding Generation Timeouts
- **Symptom:** Large datasets (3000+ dialogues) cause the Docker container to time out during indexing.
- **Resolution:** Added `healthcheck` with a long `start_period` in `docker-compose.yml` and implemented chunked processing.

## ❗ Logic: Gibberish in Synthetic Output
- **Symptom:** The model occasionally generates long strings of repetitive tokens.
- **Resolution:** Implemented `strip_gibberish` in `src/dp_synth/llm/rag_chat_engine.py` to post-process LLM outputs.

---
Back to [[Index]]
