from __future__ import annotations

from dataclasses import asdict
import json
import re
from typing import Any

from dp_synth.config import AppConfig
from dp_synth.privacy.pii import PIISanitizer
from dp_synth.types import SyntheticDialogue
from dp_synth.utils.similarity import is_too_similar


PROMPT_TEMPLATE = """You are generating privacy-safe synthetic customer support dialogues.

Rules:
- Never reproduce real customer identifiers, names, phone numbers, emails, addresses, payment details, or URLs.
- Invent realistic but fake details when needed.
- Keep the dialogues useful for training a support chatbot.
- Use the retrieved examples only as style and issue references, never copy wording.
- Return strict JSON only.

User request:
{user_request}

Target count: {target_count}

Retrieved sanitized examples:
{retrieved_examples}

Return JSON with this schema:
{{
  "dialogues": [
    {{
      "dialogue_id": "SYN-001",
      "scenario": "short description",
      "channel": "chat/email/voice/social",
      "issue_type": "billing/login/shipping/etc",
      "outcome": "Resolved/Pending/Escalated",
      "turns": [
        {{"role": "customer", "text": "..." }},
        {{"role": "agent", "text": "..." }}
      ]
    }}
  ]
}}
"""


class SyntheticDialogueGenerator:
    def __init__(self, model_client, config: AppConfig) -> None:
        self.model_client = model_client
        self.config = config
        self.sanitizer = PIISanitizer()

    def generate(
        self,
        user_request: str,
        retrieved_examples: list[dict[str, Any]],
        target_count: int,
    ) -> list[SyntheticDialogue]:
        prompt = PROMPT_TEMPLATE.format(
            user_request=user_request.strip(),
            target_count=target_count,
            retrieved_examples=self._format_examples(retrieved_examples),
        )
        raw_output = self.model_client.generate(prompt)
        parsed = self._parse_output(raw_output)

        synthetic_dialogues: list[SyntheticDialogue] = []
        reference_texts = [item["document"] for item in retrieved_examples]
        for item in parsed.get("dialogues", []):
            dialogue = SyntheticDialogue(
                dialogue_id=str(item.get("dialogue_id", f"SYN-{len(synthetic_dialogues) + 1:03d}")),
                scenario=str(item.get("scenario", "Synthetic support conversation")),
                channel=str(item.get("channel", "chat")),
                issue_type=str(item.get("issue_type", "general_support")),
                outcome=str(item.get("outcome", "Resolved")),
                turns=self._sanitize_turns(item.get("turns", [])),
            )
            joined = "\n".join(f"{turn['role']}: {turn['text']}" for turn in dialogue.turns)
            if joined and not is_too_similar(joined, reference_texts, self.config.privacy.similarity_threshold):
                synthetic_dialogues.append(dialogue)
        return synthetic_dialogues

    def _format_examples(self, retrieved_examples: list[dict[str, Any]]) -> str:
        blocks = []
        for index, item in enumerate(retrieved_examples[: self.config.privacy.max_reference_examples], start=1):
            metadata = item.get("metadata", {})
            summary = {
                "industry": metadata.get("industry", ""),
                "product": metadata.get("product", ""),
                "issue_type": metadata.get("issue_type", ""),
                "channel": metadata.get("channel", ""),
                "outcome": metadata.get("outcome", ""),
            }
            blocks.append(
                f"Example {index}\nMetadata: {json.dumps(summary)}\nDialogue:\n{item['document'][:1800]}"
            )
        return "\n\n".join(blocks) if blocks else "No examples retrieved."

    def _sanitize_turns(self, turns: list[dict[str, Any]]) -> list[dict[str, str]]:
        sanitized_turns: list[dict[str, str]] = []
        for turn in turns:
            role = str(turn.get("role", "customer")).lower()
            if role not in {"customer", "agent"}:
                role = "customer" if "user" in role else "agent"
            text, _ = self.sanitizer.sanitize_text(str(turn.get("text", "")))
            sanitized_turns.append({"role": role, "text": text})
        return sanitized_turns

    @staticmethod
    def _parse_output(raw_output: str) -> dict[str, Any]:
        candidate = raw_output.strip()
        match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if match:
            candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return {"dialogues": []}

    @staticmethod
    def as_json(dialogues: list[SyntheticDialogue]) -> str:
        return json.dumps([asdict(item) for item in dialogues], indent=2)

