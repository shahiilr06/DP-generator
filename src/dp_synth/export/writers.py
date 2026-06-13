from __future__ import annotations

from dataclasses import asdict
import json

import pandas as pd

from dp_synth.types import SyntheticDialogue


def dialogues_to_json(dialogues: list[SyntheticDialogue]) -> str:
    return json.dumps([asdict(item) for item in dialogues], indent=2)


def dialogues_to_csv(dialogues: list[SyntheticDialogue]) -> str:
    rows = []
    for dialogue in dialogues:
        for turn_index, turn in enumerate(dialogue.turns):
            rows.append(
                {
                    "dialogue_id": dialogue.dialogue_id,
                    "scenario": dialogue.scenario,
                    "channel": dialogue.channel,
                    "issue_type": dialogue.issue_type,
                    "outcome": dialogue.outcome,
                    "turn_index": turn_index,
                    "role": turn["role"],
                    "text": turn["text"],
                }
            )
    return pd.DataFrame(rows).to_csv(index=False)

