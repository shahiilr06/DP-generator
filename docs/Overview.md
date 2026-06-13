# Overview

DP‑generator is a **differential‑privacy chatbot** that combines Retrieval‑Augmented Generation (RAG) with the NVIDIA **Nemotron‑3‑nano‑omni‑30b‑a3b‑reasoning** model via OpenRouter. It provides privacy‑preserving answers while keeping the conversation context relevant.

- **Backend** – FastAPI, vector store, index‑gate UI, and SSE streaming.
- **Frontend** – Vite + React with a premium dark glassmorphism design.
- **Containerisation** – Docker Compose orchestrates backend, frontend (served by Nginx), and data volumes.

For a deeper look, see the following linked notes:

- [[Architecture]]
- [[Setup]]
- [[Usage]]
- [[Errors]]
- [[UI Design]]
- [[Docker Compose]]
- [[Contributing]]
