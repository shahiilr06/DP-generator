from __future__ import annotations

import random
import re
from typing import Generator, Any, Callable

import pandas as pd

from dp_synth.config import AppConfig
from dp_synth.llm.openrouter_client import OpenRouterClient
from dp_synth.privacy.pii import PIISanitizer


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a helpful customer-support assistant.
You have been given relevant, privacy-sanitized conversation examples retrieved \
from a support knowledge base. Use them as context to craft accurate, helpful, \
and empathetic replies.

Rules:
- Never reproduce real customer identifiers, names, phone numbers, emails, \
addresses, payment details, or URLs from the examples.
- Keep answers concise and actionable.
- If the user's issue is not covered by the examples, use your general knowledge.
- Do NOT reveal that you are using example dialogues internally.
"""

AUTO_SYSTEM_PROMPT = """You are a customer-support agent in a simulated training conversation.
You are given privacy-sanitized example dialogues as reference.

Rules:
- Respond naturally and helpfully as a support agent.
- Never reproduce real PII from examples.
- Keep replies concise (2-4 sentences).
- Do NOT reveal that this is simulated.
"""

# ---------------------------------------------------------------------------
# Noise / gibberish filter
# ---------------------------------------------------------------------------
_GIBBERISH_RE = re.compile(
    r"\b(?:[a-z]{3,20}\s){6,}\b",  # 6+ consecutive short random lowercase words
    re.IGNORECASE,
)

def strip_gibberish(text: str) -> str:
    """Remove long runs of random-looking words appended to messages."""
    # Find where the gibberish block starts (after real content)
    match = _GIBBERISH_RE.search(text)
    if match and match.start() > 10:
        return text[: match.start()].strip()
    return text.strip()


# ---------------------------------------------------------------------------
# RAG context builder
# ---------------------------------------------------------------------------
def build_rag_context_block(examples: list[dict[str, Any]]) -> str:
    """Format retrieved examples into a compact context string."""
    if not examples:
        return ""
    lines = ["<retrieved_context>"]
    for idx, ex in enumerate(examples, start=1):
        meta = ex.get("metadata", {})
        issue = meta.get("issue_type", "")
        channel = meta.get("channel", "")
        lines.append(
            f"\n[Example {idx}]"
            + (f" | issue: {issue}" if issue else "")
            + (f" | channel: {channel}" if channel else "")
        )
        lines.append(ex.get("document", "")[:1200])
    lines.append("</retrieved_context>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pick related customer turn from retrieved dialogues
# ---------------------------------------------------------------------------
def _extract_customer_turns(document: str) -> list[str]:
    """Parse 'Customer: ...' lines from a sanitized dialogue string."""
    turns = []
    for line in document.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("customer:"):
            text = stripped[len("customer:"):].strip()
            if len(text) > 15:  # skip very short fragments
                turns.append(text)
    return turns


def pick_related_customer_turn(
    retrieved_examples: list[dict[str, Any]],
    used: set[str],
) -> str | None:
    """
    Extract customer turns from retrieved dialogue examples and pick a random
    one that has not been used yet.
    Returns None if nothing usable was found.
    """
    candidates: list[str] = []
    for ex in retrieved_examples:
        doc = ex.get("document", "")
        candidates.extend(_extract_customer_turns(doc))

    # Filter used
    unused = [c for c in candidates if c not in used]
    pool = unused if unused else candidates
    if not pool:
        return None
    return random.choice(pool)


# ---------------------------------------------------------------------------
# Random question picker (from turns_df)
# ---------------------------------------------------------------------------
def pick_random_question(turns_df: pd.DataFrame, used: set[str] | None = None) -> str:
    """
    Pick a random customer opening message from the dataset that has not
    been used yet. Falls back to any message if all have been used.
    """
    customer_rows = turns_df[turns_df["role"].str.lower() == "customer"]
    first_turns = (
        customer_rows.sort_values("turn_index")
        .groupby("conv_id", sort=False)
        .first()
        .reset_index()
    )
    texts = first_turns["text"].dropna().astype(str).tolist()
    if not texts:
        return "I need help with my account."

    if used:
        unused = [t for t in texts if t not in used]
        texts = unused if unused else texts

    return random.choice(texts)


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------
class RAGChatEngine:
    """
    Conversational RAG chat engine — supports:
      • Interactive chat with streaming replies and live PII masking
      • Fully automated multi-turn synthetic dialogue generation
    """

    def __init__(self, client: OpenRouterClient, config: AppConfig) -> None:
        self.client = client
        self.config = config
        self.sanitizer = PIISanitizer()
        self._history: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    # Public API — interactive chat
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear conversation history."""
        self._history = []

    @property
    def history(self) -> list[dict[str, str]]:
        return list(self._history)

    def sanitize_for_display(self, text: str) -> str:
        """Sanitize PII and strip gibberish — used before showing user text in UI."""
        cleaned = strip_gibberish(text)
        sanitized, _ = self.sanitizer.sanitize_text(cleaned)
        return sanitized

    def stream_reply(
        self,
        user_message: str,
        retrieved_examples: list[dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """
        Yield text chunks for the assistant reply.
        • user_message is sanitized (PII removed) before being sent to the LLM.
        • The full reply is appended to history after streaming finishes.
        """
        clean_message, _ = self.sanitizer.sanitize_text(strip_gibberish(user_message))
        messages = self._build_messages(clean_message, retrieved_examples, SYSTEM_PROMPT)

        full_reply: list[str] = []
        for chunk in self.client.stream_chat(messages, max_tokens=max_tokens, temperature=temperature):
            full_reply.append(chunk)
            yield chunk

        self._history.append({"role": "user", "content": clean_message})
        self._history.append({"role": "assistant", "content": "".join(full_reply)})

    # ------------------------------------------------------------------
    # Public API — automated dialogue generation
    # ------------------------------------------------------------------

    def auto_generate_dialogue(
        self,
        turns_df: pd.DataFrame,
        vector_store,
        embedder,
        config: AppConfig,
        n_turns: int = 4,
        on_turn: Callable[[str, str, int], None] | None = None,
    ) -> list[dict[str, str]]:
        """
        Fully automated multi-turn synthetic dialogue generation.

        Flow per turn:
          1.  Customer question (Q) pulled from dataset / RAG-related turns
          2.  Q is sanitized (PII removed, gibberish stripped)
          3.  RAG retrieves relevant examples for Q
          4.  LLM streams agent reply (R)
          5.  Context = Q + R is used to retrieve related Q for the next turn

        Parameters
        ----------
        turns_df   : raw customer-support dataframe (for picking Q1)
        vector_store : built DialogueVectorStore
        embedder   : EmbeddingModel
        config     : AppConfig
        n_turns    : number of customer→agent turn pairs
        on_turn    : callback(event, text, turn_idx)
                     event ∈ {"customer", "agent_chunk", "agent_done"}

        Returns
        -------
        list of {"role": "customer"|"agent", "text": str}
        """
        self.reset()
        dialogue: list[dict[str, str]] = []
        used_questions: set[str] = set()

        # — Pick Q1 from dataset —
        raw_q = pick_random_question(turns_df, used_questions)

        for turn_idx in range(n_turns):
            # Sanitize customer turn
            clean_q = self.sanitize_for_display(raw_q)
            used_questions.add(raw_q)
            used_questions.add(clean_q)

            dialogue.append({"role": "customer", "text": clean_q})
            if on_turn:
                on_turn("customer", clean_q, turn_idx)

            # Retrieve RAG context for this customer turn
            qvec = embedder.encode([clean_q])[0]
            retrieved = vector_store.retrieve(
                query_embedding=qvec,
                n_results=config.privacy.max_reference_examples,
                privacy=config.privacy,
            )

            # Build messages for this turn (isolated from chat history to keep
            # each turn RAG-context fresh)
            messages = self._build_messages(clean_q, retrieved, AUTO_SYSTEM_PROMPT)

            # Stream agent reply
            full_reply_parts: list[str] = []
            for chunk in self.client.stream_chat(
                messages, max_tokens=512, temperature=0.75
            ):
                full_reply_parts.append(chunk)
                if on_turn:
                    on_turn("agent_chunk", chunk, turn_idx)

            agent_reply = "".join(full_reply_parts).strip()
            dialogue.append({"role": "agent", "text": agent_reply})
            if on_turn:
                on_turn("agent_done", agent_reply, turn_idx)

            # Commit to history so context accumulates
            self._history.append({"role": "user", "content": clean_q})
            self._history.append({"role": "assistant", "content": agent_reply})

            # — Pick related Q for next turn (skip on last iteration) —
            if turn_idx < n_turns - 1:
                context_for_next = f"{clean_q}\n{agent_reply}"
                context_vec = embedder.encode([context_for_next])[0]
                related = vector_store.retrieve(
                    query_embedding=context_vec,
                    n_results=8,
                    privacy=config.privacy,
                )
                next_q = pick_related_customer_turn(related, used_questions)
                if next_q:
                    raw_q = next_q
                else:
                    # fallback: pick a fresh random question from dataset
                    raw_q = pick_random_question(turns_df, used_questions)

        return dialogue

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        user_message: str,
        retrieved_examples: list[dict[str, Any]],
        system_prompt: str,
    ) -> list[dict[str, str]]:
        context_block = build_rag_context_block(retrieved_examples)
        system_content = system_prompt
        if context_block:
            system_content = system_prompt + "\n\n" + context_block

        messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_message})
        return messages
