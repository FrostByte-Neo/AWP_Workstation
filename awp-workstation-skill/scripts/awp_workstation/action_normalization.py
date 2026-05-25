"""Follow-up action and confirmation queue normalization helpers."""

from __future__ import annotations

import shlex
from typing import Any, Optional

from awp_workstation.action_groups import annotate_execution_actions
from awp_workstation.action_text import humanize_public_action_label
from awp_workstation.commands import render_argv
from awp_workstation.contracts import CONFIRMATION_SECURITY_FIELDS


def annotate_raw_follow_up_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        updated = dict(item)
        label = str(updated.get("label") or "").strip()
        if label and not isinstance(updated.get("displayLabel"), str):
            updated["displayLabel"] = humanize_public_action_label(label)
        normalized.append(updated)
    return annotate_execution_actions(normalized)


def confirmation_item_incomplete_fields(item: dict[str, Any]) -> list[str]:
    checks = {
        "action": ("action", "label"),
        "chain": ("chain", "chainId", "chainName", "network", "offChain", "gasless", "chainNote"),
        "target": ("target", "targetAddress", "recipient", "recipientAddress", "contract", "to", "noTargetReason"),
        "estimatedCost": ("estimatedCost", "estimatedFee", "estimatedGas", "cost", "fee", "gasEstimate", "unknownCost"),
        "risk": ("risk", "riskLevel", "riskSummary", "riskDisplay"),
    }
    missing: list[str] = []
    for public_field, candidates in checks.items():
        if not any(item.get(candidate) not in (None, "", [], {}) for candidate in candidates):
            missing.append(public_field)
    return missing


def copy_confirmation_security_fields(target: dict[str, Any], source: dict[str, Any]) -> None:
    for field in CONFIRMATION_SECURITY_FIELDS:
        if field in source:
            target[field] = source.get(field)
        else:
            target.setdefault(field, None)


def annotate_raw_confirmation_queue(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        updated = dict(item)
        label = str(updated.get("label") or "").strip()
        if label and not isinstance(updated.get("displayLabel"), str):
            updated["displayLabel"] = humanize_public_action_label(label)
        copy_confirmation_security_fields(updated, item)
        incomplete = confirmation_item_incomplete_fields(updated)
        if incomplete:
            updated["incompleteFields"] = incomplete
        normalized.append(updated)
    return annotate_execution_actions(normalized)


def normalized_follow_up_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        command = item.get("command")
        argv = item.get("argv")
        parsed_argv = [str(part) for part in argv] if isinstance(argv, list) and argv else None
        if parsed_argv is None and isinstance(command, str) and command.strip() and not command.strip().startswith(("http://", "https://", "Send ")):
            try:
                parsed_argv = shlex.split(command)
            except ValueError:
                parsed_argv = None
        normalized.append(
            {
                "label": label.strip(),
                "command": str(command).strip() if isinstance(command, str) and command.strip() else None,
                "argv": parsed_argv,
                "cwd": str(item.get("cwd")) if item.get("cwd") else None,
                "safeToAutoRun": bool(item.get("safeToAutoRun", False)),
                "requiresConfirmation": bool(item.get("requiresConfirmation", False)),
                "selectedByDefault": bool(item.get("selectedByDefault", False)),
                "longRunning": bool(item.get("longRunning", False)),
                "parameterSchema": [
                    spec for spec in item.get("parameterSchema", []) if isinstance(spec, dict)
                ] if isinstance(item.get("parameterSchema"), list) else [],
            }
        )
    return annotate_raw_follow_up_actions(normalized)


def normalized_confirmation_queue(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        argv = item.get("argv")
        normalized_item = {
            "label": label.strip(),
            "displayLabel": humanize_public_action_label(label.strip()),
            "command": render_argv([str(part) for part in argv]) if isinstance(argv, list) and argv else None,
            "argv": [str(part) for part in argv] if isinstance(argv, list) and argv else None,
            "cwd": str(item.get("cwd")) if item.get("cwd") else None,
            "category": item.get("category"),
            "executionPolicy": item.get("executionPolicy"),
            "status": item.get("status", "queued_for_confirmation"),
            "longRunning": bool(item.get("longRunning", False)),
            "parameterSchema": [
                spec for spec in item.get("parameterSchema", []) if isinstance(spec, dict)
            ] if isinstance(item.get("parameterSchema"), list) else [],
        }
        copy_confirmation_security_fields(normalized_item, item)
        normalized.append(normalized_item)
    return annotate_raw_confirmation_queue(normalized)


def choose_default_confirmation(queue: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    return queue[0] if queue else None


def choose_default_background_process(active: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    return active[0] if active else None


def choose_default_follow_up_action(actions: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    candidates = [
        item
        for item in actions
        if item.get("safeToAutoRun") and not item.get("requiresConfirmation") and item.get("argv")
    ]
    if not candidates:
        return None
    for item in candidates:
        if item.get("selectedByDefault"):
            return item
    return candidates[0]
