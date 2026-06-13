from __future__ import annotations

from difflib import SequenceMatcher


def is_too_similar(candidate: str, references: list[str], threshold: float) -> bool:
    normalized_candidate = " ".join(candidate.lower().split())
    for reference in references:
        ratio = SequenceMatcher(None, normalized_candidate, " ".join(reference.lower().split())).ratio()
        if ratio >= threshold:
            return True
    return False

