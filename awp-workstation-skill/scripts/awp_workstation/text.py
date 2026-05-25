"""Text cleanup and preview helpers."""

from __future__ import annotations

import re
from typing import Any, Optional


def strip_sentence_end(text: Any) -> str:
    return str(text or "").strip().rstrip(".!?")


def compact_preview_text(
    value: Any,
    *,
    max_chars: int = 180,
    max_sentences: int = 2,
) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    sentence_endings = set(".!?;")
    if len(text) <= max_chars and sum(1 for char in text if char in sentence_endings) <= max_sentences:
        return text
    preview_chars: list[str] = []
    sentence_count = 0
    for char in text:
        preview_chars.append(char)
        if char in sentence_endings:
            sentence_count += 1
            if sentence_count >= max_sentences:
                break
        if len(preview_chars) >= max_chars:
            break
    preview = "".join(preview_chars).strip()
    if len(preview) < len(text):
        cut_index = len(preview)
        if (
            cut_index < len(text)
            and preview
            and re.match(r"[A-Za-z0-9_-]", preview[-1])
            and re.match(r"[A-Za-z0-9_-]", text[cut_index])
        ):
            boundary = max(
                preview.rfind(" "),
                preview.rfind(","),
                preview.rfind(":"),
                preview.rfind("/"),
                preview.rfind("-"),
                preview.rfind("_"),
            )
            if boundary >= max(0, len(preview) - 24):
                preview = preview[:boundary].strip()
            else:
                while preview and re.match(r"[A-Za-z0-9_-]", preview[-1]):
                    preview = preview[:-1]
                preview = preview.strip()
        preview = preview.rstrip(".!?;, ") + "..."
    return preview


def preview_candidate_fragments(value: Any) -> list[str]:
    text = re.sub(r"\s+", " ", str(value or "").strip()).strip()
    if not text:
        return []
    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: Any) -> None:
        fragment = strip_sentence_end(str(candidate or "").strip()).strip(" ,;:")
        if not fragment:
            return
        normalized = fragment.lower()
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append(fragment)

    for delimiter in (",", ":", ";", "(", "\n"):
        prefix, _, _ = text.partition(delimiter)
        if len(prefix.strip()) >= 8:
            add(prefix)
    for delimiter in (".", "!", "?"):
        prefix, _, _ = text.partition(delimiter)
        if prefix.strip():
            add(prefix)
    add(text)
    return candidates


def join_sentences(parts: list[str]) -> str:
    cleaned = []
    for part in parts:
        text = (part or "").strip()
        if not text:
            continue
        cleaned.append(text.rstrip("."))
    return ". ".join(cleaned)


def join_product_sentences(parts: list[str]) -> str:
    cleaned = []
    for part in parts:
        text = str(part or "").strip()
        if not text:
            continue
        cleaned.append(strip_sentence_end(text))
    return ". ".join(cleaned)
