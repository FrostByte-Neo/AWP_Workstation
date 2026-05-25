"""Playbook display text helpers."""

from __future__ import annotations

from awp_workstation.knowledge_contracts import KNOWLEDGE_ROLE_LABELS
from awp_workstation.narratives import canonical_worknet_loop_text, canonical_worknet_plain_text


def humanize_playbook_goal(worknet_key: str, raw_goal: str) -> str:
    plain = canonical_worknet_plain_text(worknet_key)
    if plain:
        return plain
    return raw_goal


def humanize_playbook_role(role: str) -> str:
    text = str(role or "").strip()
    return KNOWLEDGE_ROLE_LABELS.get(text, text)


def humanize_playbook_loop(worknet_key: str, raw_loop: str) -> str:
    loop = canonical_worknet_loop_text(worknet_key)
    if loop:
        return loop
    return raw_loop


def humanize_playbook_success_metric(metric: str) -> str:
    mapping = {
        "valid commits": "Valid commits",
        "successful reveal timing": "Successful reveal timing",
        "mint cap respected": "Mint cap respected",
        "low reasoning repetition": "Low reasoning repetition",
        "rate-limit discipline": "Rate-limit discipline",
        "positive settlement quality": "Positive settlement quality",
        "correct phase timing": "Correct phase timing",
        "clear rationale": "Clear rationale",
        "tracked settlement delta": "Tracked settlement delta",
    }
    text = str(metric or "").strip()
    return mapping.get(text, text)


def humanize_playbook_failure_mode(mode: str) -> str:
    mapping = {
        "insufficient Base gas": "Insufficient Base gas",
        "stake ineligible": "Stake ineligible",
        "missed reveal window": "Missed reveal window",
        "duplicate reasoning": "Duplicate reasoning",
        "overtrading": "Overtrading",
        "thin context": "Thin context",
        "missing verified local runtime": "Missing verified local runtime",
        "stake gate still blocks submissions until 1000 AWP or KYA delegated eligibility is satisfied": "Stake gate blocks submissions until 1000 AWP or KYA delegated eligibility is satisfied.",
        "voting or trading outside phase windows": "Voting or trading outside phase windows",
        "unreviewed capital movement": "Unreviewed capital movement",
        "missing market context": "Missing market context",
        "public operator docs remain thin": "Public operator docs remain thin",
        "official skill has not been inspected locally yet": "Official skill has not been inspected locally yet.",
    }
    text = str(mode or "").strip()
    return mapping.get(text, text)


def humanize_playbook_confirmation_item(text: str) -> str:
    mapping = {
        "Confirm funding the Base wallet before Ardi execution.": "Confirm funding the Base wallet before Ardi execution.",
        "Confirm the stake path before any buy, swap, or stake action.": "Confirm the stake path before any buy, swap, or stake action.",
        "Confirm every capital-bearing order or ticket action.": "Confirm every capital-bearing order or ticket action.",
        "Confirm the stake or KYA-sponsored eligibility path before enabling the autonomous Predict loop.": "Confirm the stake or KYA-sponsored eligibility path before enabling the autonomous Predict loop.",
        "Confirm every stake, allocation, vote, and trade action.": "Confirm every stake, allocation, vote, and trade action.",
        "Confirm before auto-installing or executing the official Community skill.": "Confirm before auto-installing or executing the official Community skill.",
        "Confirm before auto-installing or executing the official TMR skill.": "Confirm before auto-installing or executing the official TMR skill.",
    }
    normalized = str(text or "").strip()
    return mapping.get(normalized, normalized)
