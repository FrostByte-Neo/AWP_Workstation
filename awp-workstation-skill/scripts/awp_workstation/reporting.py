"""Reporter and daily-summary presentation helpers."""

from __future__ import annotations

import re
from typing import Any, Optional

from awp_workstation.narratives import canonical_worknet_plain_text
from awp_workstation.text import compact_preview_text, strip_sentence_end


def build_daily_summary(
    worknet_key: str,
    headline: Optional[str],
    estimated_rewards: list[str],
    user_actions: list[str],
    *,
    reporter_note: Optional[str] = None,
) -> Optional[str]:
    def normalize_part(text: Any) -> str:
        value = strip_sentence_end(text)
        return re.sub(r"[\s!?,:;]+", "", value).lower()

    parts: list[str] = []
    seen: set[str] = set()

    def add_part(text: Any, *, max_chars: int, max_sentences: int = 1) -> None:
        preview = compact_preview_text(text, max_chars=max_chars, max_sentences=max_sentences)
        if not preview:
            return
        rendered = strip_sentence_end(preview)
        normalized = normalize_part(rendered)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        parts.append(rendered)

    if isinstance(headline, str) and headline.strip():
        add_part(headline, max_chars=120, max_sentences=1)
    else:
        plain = canonical_worknet_plain_text(worknet_key)
        if plain:
            add_part(plain, max_chars=120, max_sentences=1)
    if isinstance(reporter_note, str) and reporter_note.strip():
        add_part(reporter_note, max_chars=90, max_sentences=1)
    if estimated_rewards:
        reward_summary = str(estimated_rewards[0] or "").strip()
        if reward_summary and reward_summary.lower() != "no reward estimate is available yet.":
            add_part(reward_summary, max_chars=120, max_sentences=1)
    if user_actions:
        first_action = str(user_actions[0]).strip()
        if first_action:
            add_part(f"Next action: {first_action}", max_chars=100, max_sentences=1)
    if not parts:
        return None
    rendered: list[str] = []
    for part in parts:
        text = strip_sentence_end(part)
        if not text:
            continue
        if rendered:
            rendered.append(" " if rendered[-1].endswith(".") else ". ")
        rendered.append(text)
    if not rendered:
        return None
    if rendered[-1].endswith("."):
        return "".join(rendered)
    return "".join(rendered) + "."


def reporter_reference_note(
    knowledge_context: Any,
    knowledge_reference_highlights: Any,
) -> Optional[str]:
    if not isinstance(knowledge_context, dict) or not isinstance(knowledge_reference_highlights, list):
        return None
    for item in knowledge_reference_highlights:
        if not isinstance(item, dict):
            continue
        ref_label = str(item.get("label") or item.get("key") or "").strip()
        if ref_label:
            return f"Reference: {ref_label}."
    return None


def knowledge_source_labels_text(
    knowledge_source_highlights: Any,
    *,
    affected_only: Optional[bool] = None,
    limit: int = 3,
) -> Optional[str]:
    if not isinstance(knowledge_source_highlights, list):
        return None
    labels: list[str] = []
    for item in knowledge_source_highlights:
        if not isinstance(item, dict):
            continue
        freshness = str(item.get("freshnessStatus") or "").strip().lower()
        if affected_only is True and freshness != "affected":
            continue
        if affected_only is False and freshness == "affected":
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label or label in labels:
            continue
        labels.append(label)
        if len(labels) >= limit:
            break
    if not labels:
        return None
    return "   ".join(labels)


def reporter_source_note(knowledge_source_highlights: Any) -> Optional[str]:
    affected_items = [
        item
        for item in knowledge_source_highlights
        if isinstance(item, dict) and str(item.get("freshnessStatus") or "").strip().lower() == "affected"
    ] if isinstance(knowledge_source_highlights, list) else []
    stable_items = [
        item
        for item in knowledge_source_highlights
        if isinstance(item, dict) and str(item.get("freshnessStatus") or "").strip().lower() != "affected"
    ] if isinstance(knowledge_source_highlights, list) else []
    affected_labels = knowledge_source_labels_text(affected_items, affected_only=None, limit=3)
    stable_labels = knowledge_source_labels_text(stable_items, affected_only=None, limit=3)
    if affected_labels:
        first_label = str((affected_items[0].get("label") or affected_items[0].get("key") or "") if affected_items else "").strip()
        if first_label:
            return f"Changed source: {first_label}."
        return f"Changed source: {affected_labels.split('   ')[0]}."
    if stable_labels:
        first_label = str((stable_items[0].get("label") or stable_items[0].get("key") or "") if stable_items else "").strip()
        if first_label:
            return f"Source: {first_label}."
        return f"Source: {stable_labels.split('   ')[0]}."
    return None


def build_reporter_note(
    knowledge_context: Any,
    knowledge_reference_highlights: Any,
    knowledge_source_highlights: Any = None,
) -> Optional[str]:
    if not isinstance(knowledge_context, dict):
        return None
    label = str(knowledge_context.get("label") or knowledge_context.get("key") or "WorkNet").strip()
    freshness = str(knowledge_context.get("freshnessStatus") or "").strip().lower()
    if freshness == "affected":
        note = f"{label} needs source review."
    else:
        note = f"{label} is ready."
    source_note = reporter_source_note(knowledge_source_highlights)
    if source_note:
        note += f" {source_note}"
    reference_note = reporter_reference_note(knowledge_context, knowledge_reference_highlights)
    if reference_note:
        note += f" {reference_note}"
    return note
