from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


@dataclass(slots=True)
class PiiMatch:
    label: str
    value: str
    replacement: str


class PIISanitizer:
    def __init__(self) -> None:
        self.patterns: list[tuple[str, re.Pattern[str], str]] = [
            ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
            ("phone", re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b"), "[PHONE]"),
            ("card", re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[PAYMENT_ID]"),
            ("ip_address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_ADDRESS]"),
            ("order_id", re.compile(r"\b(?:order|ticket|case|invoice|account)[-_:#\s]?[A-Z0-9]{5,}\b", re.IGNORECASE), "[CASE_ID]"),
            ("person_name", re.compile(r"\b(?:Cust|Agent)[A-Z0-9]{3,}\b"), "[NAME]"),
            ("url", re.compile(r"https?://\S+|www\.\S+"), "[URL]"),
            ("postal_code", re.compile(r"\b\d{5}(?:-\d{4})?\b"), "[ZIP_CODE]"),
        ]

    def _stable_alias(self, label: str, value: str, template: str) -> str:
        digest = hashlib.sha1(f"{label}:{value}".encode("utf-8")).hexdigest()[:6].upper()
        return f"{template}_{digest}"

    def sanitize_text(self, text: str) -> tuple[str, list[PiiMatch]]:
        sanitized = " ".join(text.split())
        matches: list[PiiMatch] = []
        for label, pattern, template in self.patterns:
            current_matches = list(pattern.finditer(sanitized))
            for match in current_matches:
                value = match.group(0)
                replacement = self._stable_alias(label, value, template)
                matches.append(PiiMatch(label=label, value=value, replacement=replacement))
                sanitized = sanitized.replace(value, replacement)
        return sanitized, matches

