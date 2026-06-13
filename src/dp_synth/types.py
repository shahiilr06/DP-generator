from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class ConversationDocument:
    conversation_id: str
    dialogue: str
    metadata: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record.update(self.metadata)
        return record


@dataclass(slots=True)
class SyntheticDialogue:
    dialogue_id: str
    scenario: str
    channel: str
    issue_type: str
    outcome: str
    turns: list[dict[str, str]]

