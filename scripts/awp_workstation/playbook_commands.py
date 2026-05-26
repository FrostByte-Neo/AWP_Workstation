"""Playbook command policy and display annotation helpers."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.contracts import (
    PLAYBOOK_COMMAND_GROUP_LABELS,
    RESEARCH_HIGHLIGHT_TIER_LABELS,
    RESEARCH_HIGHLIGHT_TIER_RANKS,
)


def infer_command_execution_policy(
    command: dict[str, Any],
    *,
    inspection_status: Optional[str] = None,
) -> str:
    if command.get("requires_confirmation"):
        return "confirm"
    label = str(command.get("label", "")).lower()
    category = str(command.get("category", "")).lower()
    if label.startswith("inspect ") and label.endswith(" skill"):
        return "manual-review"
    if category in {"inspect", "read"} or command.get("autoRunOnInspect"):
        return "probe"
    if category in {"install", "repair", "registration"}:
        return "setup" if inspection_status != "ready" else "manual-setup"
    if any(token in label for token in ("pause", "stop", "cancel", "resume")):
        return "manual-control"
    if category == "work":
        if label.startswith("start ") or label.startswith("run ") or command.get("long_running"):
            return "primary-work"
        return "manual-control"
    return "manual"


def annotate_playbook_commands(
    commands: list[dict[str, Any]],
    *,
    inspection_status: Optional[str] = None,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for command in commands:
        updated = dict(command)
        policy = infer_command_execution_policy(updated, inspection_status=inspection_status)
        updated["executionPolicy"] = policy
        updated["selectedByDefault"] = policy in {"probe", "setup", "primary-work", "confirm"}
        if policy == "confirm":
            group_key = "confirmations"
            tier = "current"
        elif policy in {"setup", "manual-setup"}:
            group_key = "setup"
            tier = "overview"
        elif policy in {"probe", "manual-review"}:
            group_key = "inspect"
            tier = "related"
        elif policy in {"manual-control"}:
            group_key = "control"
            tier = "related"
        else:
            group_key = "current"
            tier = "current"
        updated["commandGroupKey"] = group_key
        updated["commandGroupLabel"] = PLAYBOOK_COMMAND_GROUP_LABELS.get(group_key, group_key)
        updated["commandTier"] = tier
        updated["commandTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get(tier, tier)
        updated["commandTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
        annotated.append(updated)
    return annotated


def dedupe_playbook_commands(commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for command in commands:
        argv = tuple(str(item) for item in command.get("argv", []))
        cwd = str(command.get("cwd") or "")
        key = (cwd, argv)
        if argv and key in seen:
            continue
        if argv:
            seen.add(key)
        deduped.append(command)
    return deduped
