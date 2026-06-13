from __future__ import annotations

import json
import logging
from typing import Generator, Any

import urllib.request
import urllib.error

LOGGER = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"


class OpenRouterClient:
    """Streaming chat client backed by OpenRouter API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key
        self.model = model

    # ------------------------------------------------------------------
    # Non-streaming (full response)
    # ------------------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            OPENROUTER_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost",
                "X-Title": "DP Synthetic Dialogue Generator",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            LOGGER.error("OpenRouter HTTP %s: %s", exc.code, error_body)
            raise RuntimeError(f"OpenRouter API error {exc.code}: {error_body}") from exc

    # ------------------------------------------------------------------
    # Streaming (yields text chunks)
    # ------------------------------------------------------------------
    def stream_chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            OPENROUTER_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost",
                "X-Title": "DP Synthetic Dialogue Generator",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    try:
                        chunk = json.loads(line)
                        delta = chunk["choices"][0].get("delta", {})
                        text = delta.get("content", "")
                        if text:
                            yield text
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            LOGGER.error("OpenRouter HTTP %s: %s", exc.code, error_body)
            raise RuntimeError(f"OpenRouter API error {exc.code}: {error_body}") from exc
