"""
FastAPI backend for the Differentially Private RAG Chatbot.

Endpoints
---------
GET  /api/status
POST /api/build-index
POST /api/chat          (SSE streaming)
POST /api/chat/clear
GET  /api/random-question
POST /api/autogen       (SSE streaming)
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any, AsyncGenerator, Generator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dp_synth.config import DEFAULT_CONFIG, AppConfig, PrivacyConfig
from dp_synth.data.loader import build_conversation_documents, load_turns
from dp_synth.llm.openrouter_client import OpenRouterClient
from dp_synth.llm.rag_chat_engine import (
    AUTO_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_rag_context_block,
    pick_random_question,
    pick_related_customer_turn,
    strip_gibberish,
)
from dp_synth.privacy.pii import PIISanitizer
from dp_synth.rag.embeddings import EmbeddingModel
from dp_synth.rag.vector_store import DialogueVectorStore

# ── global mutable state (single-user) ──────────────────────────────────────
_lock = threading.Lock()
_turns_df = None
_vector_store: DialogueVectorStore | None = None
_embedder: EmbeddingModel | None = None
_indexed_count: int = 0
_chat_history: list[dict] = []
_chat_used_questions: set[str] = set()

# ── app ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="DP RAG Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── helpers ─────────────────────────────────────────────────────────────────

def _get_embedder() -> EmbeddingModel:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingModel(DEFAULT_CONFIG.embedding_model)
    return _embedder


def _make_privacy_cfg(epsilon: float, max_examples: int) -> PrivacyConfig:
    cfg = PrivacyConfig()
    cfg.epsilon = epsilon
    cfg.max_reference_examples = max_examples
    return cfg


def _retrieve(query: str, privacy: PrivacyConfig) -> list[dict]:
    if _vector_store is None:
        return []
    embedder = _get_embedder()
    qvec = embedder.encode([query])[0]
    return _vector_store.retrieve(
        query_embedding=qvec,
        n_results=max(privacy.max_reference_examples, 4),
        privacy=privacy,
    )


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


# ── request/response models ─────────────────────────────────────────────────

class BuildIndexRequest(BaseModel):
    max_dialogues: int = 3000


class ChatRequest(BaseModel):
    message: str
    epsilon: float = 1.5
    max_examples: int = 4
    api_key: str = ""
    model: str = ""


class AutogenRequest(BaseModel):
    n_turns: int = 4
    temperature: float = 0.85
    epsilon: float = 1.5
    max_examples: int = 4
    api_key: str = ""
    model: str = ""


# ── routes ──────────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    return {"indexed": _vector_store is not None, "indexed_count": _indexed_count}


@app.post("/api/build-index")
def build_index(req: BuildIndexRequest):
    global _turns_df, _vector_store, _indexed_count, _chat_history, _chat_used_questions
    sanitizer = PIISanitizer()
    turns_df = load_turns(DEFAULT_CONFIG.default_dataset)
    docs = build_conversation_documents(
        turns_df, sanitizer=sanitizer, max_dialogues=req.max_dialogues
    )
    embedder = _get_embedder()
    embeddings = embedder.encode([d.dialogue for d in docs])
    vs = DialogueVectorStore(
        DEFAULT_CONFIG.chroma_dir,
        DEFAULT_CONFIG.collection_name,
        DEFAULT_CONFIG.vector_backend,
    )
    vs.reset()
    vs.upsert_documents(docs, embeddings)

    with _lock:
        _turns_df = turns_df
        _vector_store = vs
        _indexed_count = len(docs)
        _chat_history = []
        _chat_used_questions = set()

    return {"indexed_count": _indexed_count, "status": "ok"}


@app.post("/api/chat/clear")
def clear_chat():
    global _chat_history, _chat_used_questions
    with _lock:
        _chat_history = []
        _chat_used_questions = set()
    return {"ok": True}


@app.get("/api/random-question")
def random_question():
    if _turns_df is None:
        return {"question": "I need help with my account."}
    q = pick_random_question(_turns_df, _chat_used_questions)
    return {"question": q}


@app.post("/api/chat")
def chat_stream(req: ChatRequest):
    def generate() -> Generator[str, None, None]:
        global _chat_history, _chat_used_questions

        sanitizer = PIISanitizer()
        privacy = _make_privacy_cfg(req.epsilon, req.max_examples)

        # Sanitize user message
        clean_msg, pii_matches = sanitizer.sanitize_text(strip_gibberish(req.message))
        pii_info = [{"label": m.label, "replacement": m.replacement} for m in pii_matches]

        # Retrieve RAG context
        retrieved = _retrieve(clean_msg, privacy)
        examples_meta = [
            {
                "issue_type": ex.get("metadata", {}).get("issue_type", "—"),
                "channel": ex.get("metadata", {}).get("channel", "—"),
                "score": round(ex.get("score", 0), 3),
                "snippet": ex.get("document", "")[:400],
            }
            for ex in retrieved
        ]
        yield _sse({"type": "retrieved", "count": len(retrieved), "examples": examples_meta})

        # Build messages
        ctx = build_rag_context_block(retrieved)
        system = SYSTEM_PROMPT + ("\n\n" + ctx if ctx else "")
        messages = [{"role": "system", "content": system}]
        messages.extend(_chat_history)
        messages.append({"role": "user", "content": clean_msg})

        # Resolve API key + model
        api_key = req.api_key.strip() or DEFAULT_CONFIG.openrouter_api_key
        model = req.model.strip() or DEFAULT_CONFIG.openrouter_model
        client = OpenRouterClient(api_key=api_key, model=model)

        # Stream reply
        full_reply = ""
        try:
            for chunk in client.stream_chat(messages, max_tokens=1024, temperature=0.7):
                full_reply += chunk
                yield _sse({"type": "chunk", "text": chunk})
        except RuntimeError as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        # Commit history
        with _lock:
            _chat_history.append({"role": "user", "content": clean_msg})
            _chat_history.append({"role": "assistant", "content": full_reply})
            _chat_used_questions.add(req.message)

        yield _sse({
            "type": "done",
            "pii": pii_info,
            "sanitized_message": clean_msg,
        })

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/autogen")
def autogen_stream(req: AutogenRequest):
    def generate() -> Generator[str, None, None]:
        if _turns_df is None or _vector_store is None:
            yield _sse({"type": "error", "message": "Index not built. Please build the index first."})
            return

        sanitizer = PIISanitizer()
        privacy = _make_privacy_cfg(req.epsilon, req.max_examples)
        api_key = req.api_key.strip() or DEFAULT_CONFIG.openrouter_api_key
        model = req.model.strip() or DEFAULT_CONFIG.openrouter_model
        client = OpenRouterClient(api_key=api_key, model=model)
        embedder = _get_embedder()

        used_q: set[str] = set()
        conv_history: list[dict] = []
        dialogue_record: list[dict] = []

        # Pick Q1
        raw_q = pick_random_question(_turns_df, used_q)

        for turn_idx in range(req.n_turns):
            # ── Customer turn ──────────────────────────────────────────────
            clean_q, _ = sanitizer.sanitize_text(strip_gibberish(raw_q))
            if not clean_q.strip():
                clean_q = "I need help with my account."
            used_q.add(raw_q)
            used_q.add(clean_q)

            yield _sse({"type": "customer", "text": clean_q, "turn": turn_idx})
            dialogue_record.append({"role": "customer", "text": clean_q})

            # Retrieve RAG context
            qvec = embedder.encode([clean_q])[0]
            retrieved = _vector_store.retrieve(qvec, req.max_examples, privacy)

            # Build messages
            ctx = build_rag_context_block(retrieved)
            system = AUTO_SYSTEM_PROMPT + ("\n\n" + ctx if ctx else "")
            messages: list[dict] = [{"role": "system", "content": system}]
            messages.extend(conv_history)
            messages.append({"role": "user", "content": clean_q})

            # ── Agent turn (streaming) ─────────────────────────────────────
            reply = ""
            try:
                for chunk in client.stream_chat(
                    messages, max_tokens=350, temperature=req.temperature
                ):
                    reply += chunk
                    yield _sse({"type": "agent_chunk", "text": chunk, "turn": turn_idx})
            except RuntimeError as exc:
                yield _sse({"type": "error", "message": str(exc)})
                return

            if not reply.strip():
                reply = "I understand your concern. Let me look into that for you right away."

            yield _sse({"type": "agent_done", "text": reply, "turn": turn_idx})
            dialogue_record.append({"role": "agent", "text": reply})

            # Update conversation history
            conv_history.append({"role": "user", "content": clean_q})
            conv_history.append({"role": "assistant", "content": reply})

            # ── Pick next Q ────────────────────────────────────────────────
            if turn_idx < req.n_turns - 1:
                ctx_vec = embedder.encode([f"{clean_q}\n{reply}"])[0]
                related = _vector_store.retrieve(ctx_vec, 8, privacy)
                next_q = pick_related_customer_turn(related, used_q)
                raw_q = next_q if next_q else pick_random_question(_turns_df, used_q)

        yield _sse({"type": "complete", "dialogue": dialogue_record})

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
