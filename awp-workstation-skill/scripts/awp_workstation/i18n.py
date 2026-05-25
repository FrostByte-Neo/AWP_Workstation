"""Public text normalization for workstation JSON output."""

from __future__ import annotations

import re
from typing import Any, Optional


NON_ASCII_TEXT_RE = re.compile(r"[^\x00-\x7f]")
EXCESSIVE_SPACE_RE = re.compile(r"[ \t]{2,}")

CONTEXTUAL_EMPTY_TEXT_DEFAULTS = {
    "answer": "No workstation answer is available yet.",
    "dailySummary": "No epoch summary is available yet.",
    "description": "Action details pending.",
    "estimatedRewards": "No reward estimate is available yet.",
    "headline": "No pending knowledge reviews.",
    "intro": "AWP agent Workstation.",
    "label": "Action pending.",
    "message": "No status message is available yet.",
    "primaryActionLabel": "Review pending knowledge updates",
    "refreshActionLabel": "Refresh knowledge review queue",
    "reporterNote": "No reporter note is available yet.",
    "summary": "No summary is available yet.",
    "user_message": "No workstation message is available yet.",
}

def normalize_public_text(text: str, *, context_key: Optional[str] = None) -> str:
    normalized = EXCESSIVE_SPACE_RE.sub(" ", text)
    normalized = normalized.strip()
    if normalized:
        return normalized
    key = str(context_key or "").strip()
    return CONTEXTUAL_EMPTY_TEXT_DEFAULTS.get(key, "Details pending.")


def public_text_to_english(text: str, *, context_key: Optional[str] = None) -> str:
    if not NON_ASCII_TEXT_RE.search(text):
        if EXCESSIVE_SPACE_RE.search(text) or text != text.strip():
            return normalize_public_text(text, context_key=context_key)
        return text
    ascii_only = NON_ASCII_TEXT_RE.sub("", text)
    ascii_only = re.sub(r"\s+", " ", ascii_only)
    ascii_only = ascii_only.strip(" \t\r\n,. ;:()[]")
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_./:#@+-]*", ascii_only)
    if tokens:
        return " ".join(tokens)
    return normalize_public_text(ascii_only, context_key=context_key)


def sanitize_public_payload(payload: Any, *, context_key: Optional[str] = None) -> Any:
    if isinstance(payload, dict):
        return {
            public_text_to_english(key) if isinstance(key, str) else key: sanitize_public_payload(
                value,
                context_key=key if isinstance(key, str) else context_key,
            )
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [sanitize_public_payload(item, context_key=context_key) for item in payload]
    if isinstance(payload, str):
        return public_text_to_english(payload, context_key=context_key)
    return payload
