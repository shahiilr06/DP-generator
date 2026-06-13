from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
import csv

import pandas as pd

from dp_synth.types import ConversationDocument


REQUIRED_COLUMNS = {"conv_id", "turn_index", "role", "text"}
METADATA_COLUMNS = [
    "industry",
    "product",
    "issue_type",
    "language",
    "channel",
    "overall_sentiment",
    "overall_urgency",
    "outcome",
    "primary_intent",
]


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9_]+", "_", regex=True)
    )
    return df


def load_turns(source: str | Path | BinaryIO) -> pd.DataFrame:
    if hasattr(source, "seek"):
        source.seek(0)
    try:
        df = pd.read_csv(
            source,
            engine="python",
            encoding="utf-8",
            quoting=csv.QUOTE_MINIMAL,
            on_bad_lines="skip",
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            source,
            engine="python",
            encoding="latin1",
            quoting=csv.QUOTE_MINIMAL,
            on_bad_lines="skip",
        )

    df = _clean_columns(df)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    df["conv_id"] = df["conv_id"].fillna("").astype(str)
    df["turn_index"] = pd.to_numeric(df["turn_index"], errors="coerce").fillna(0).astype(int)
    df["text"] = df["text"].fillna("").astype(str)
    df["role"] = df["role"].fillna("unknown").astype(str).str.lower()
    return df


def build_conversation_documents(
    turns_df: pd.DataFrame,
    sanitizer,
    max_dialogues: int | None = None,
) -> list[ConversationDocument]:
    df = turns_df.sort_values(["conv_id", "turn_index"]).copy()
    if max_dialogues:
        selected_ids = df["conv_id"].drop_duplicates().head(max_dialogues)
        df = df[df["conv_id"].isin(selected_ids)]

    documents: list[ConversationDocument] = []
    for conv_id, group in df.groupby("conv_id", sort=False):
        dialogue_lines: list[str] = []
        pii_hits = 0
        first = group.iloc[0]
        for row in group.itertuples(index=False):
            sanitized_text, matches = sanitizer.sanitize_text(str(row.text))
            pii_hits += len(matches)
            role = str(row.role).strip().capitalize() or "Unknown"
            dialogue_lines.append(f"{role}: {sanitized_text}")

        metadata = {
            "source_conv_id": str(conv_id),
            "turn_count": int(len(group)),
            "pii_replacements": pii_hits,
        }
        for column in METADATA_COLUMNS:
            if column in group.columns:
                metadata[column] = str(first[column]) if pd.notna(first[column]) else ""

        documents.append(
            ConversationDocument(
                conversation_id=str(conv_id),
                dialogue="\n".join(dialogue_lines),
                metadata=metadata,
            )
        )

    return documents

