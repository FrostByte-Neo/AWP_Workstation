"""Public response projection and display helpers."""

from __future__ import annotations

from typing import Any

from awp_workstation.commands import render_argv
from awp_workstation.contracts import (
    CAPABILITY_PUBLIC_FIELDS,
    PLAYBOOK_PUBLIC_FIELDS,
    PREFLIGHT_PUBLIC_FIELDS,
    REVIEW_PUBLIC_FIELDS,
    WORKSTATION_STATE_SUMMARY_FIELDS,
    WORKSTATION_PREFERENCES_PUBLIC_FIELDS,
    WORKSTATION_STATUS_PUBLIC_FIELDS,
    normalize_workstation_state_summary_payload,
    project_fields,
)
from awp_workstation.knowledge_contracts import (
    KNOWLEDGE_AUTOMATION_LABELS,
    KNOWLEDGE_RISK_LABELS,
    KNOWLEDGE_ROLE_LABELS,
    KNOWLEDGE_WORKNET_STATUS_LABELS,
)


def public_preflight_view(report: dict[str, Any]) -> dict[str, Any]:
    return project_fields(report, PREFLIGHT_PUBLIC_FIELDS)


def humanize_public_capability_report(report: dict[str, Any]) -> dict[str, Any]:
    normalized = project_fields(report, CAPABILITY_PUBLIC_FIELDS)
    normalized["status"] = KNOWLEDGE_WORKNET_STATUS_LABELS.get(
        str(normalized.get("status") or "").strip().lower(),
        normalized.get("status"),
    )
    normalized["automationLevel"] = KNOWLEDGE_AUTOMATION_LABELS.get(
        str(normalized.get("automationLevel") or "").strip(),
        normalized.get("automationLevel"),
    )
    normalized["riskLevel"] = KNOWLEDGE_RISK_LABELS.get(
        str(normalized.get("riskLevel") or "").strip(),
        normalized.get("riskLevel"),
    )
    normalized["recommendedRole"] = KNOWLEDGE_ROLE_LABELS.get(
        str(normalized.get("recommendedRole") or "").strip(),
        normalized.get("recommendedRole"),
    )
    return normalized


def public_capability_view(report: dict[str, Any]) -> dict[str, Any]:
    return humanize_public_capability_report(report)


def humanize_playbook_command_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return text
    mapping = {
        "inspect mine skill": "Inspect Mine skill",
        "mine agent status": "Check Mine agent status",
        "mine control status": "Check Mine control status",
        "start mine worker": "Start Mine worker",
        "pause mine worker": "Pause Mine worker",
        "inspect predict skill": "Inspect Predict skill",
        "predict wallet safety": "Check Predict wallet safety",
        "predict status": "Check Predict status",
        "predict preflight": "Run Predict preflight",
        "predict stake eligibility": "Check Predict stake eligibility",
        "inspect gov skill": "Inspect Gov skill",
        "gov public markets": "Check Gov public markets",
        "gov phase-aware helper": "Check Gov phase-aware helper",
        "gov private state": "Check Gov private state",
        "inspect ardi skill": "Inspect Ardi skill",
        "ardi status": "Check Ardi status",
        "ardi gas check": "Check Ardi gas",
        "ardi preflight": "Run Ardi preflight",
        "ardi stake guidance": "Check Ardi stake guidance",
        "inspect community skill": "Inspect Community skill",
        "inspect tmr skill": "Inspect TMR skill",
        "inspect kya skill": "Inspect KYA skill",
        "awp-skill preflight": "Run AWP RootNet preflight",
        "kya relay recipient help": "Review KYA relay recipient help",
        "kya sign claim help": "Review KYA sign claim help",
        "create gov skill venv": "Create Gov skill virtualenv",
        "install gov skill deps": "Install Gov skill dependencies",
    }
    if text in mapping:
        return mapping[text]
    if text.startswith("inspect ") and text.endswith(" skill"):
        return "Inspect " + text[len("inspect "):]
    return text


def humanize_playbook_command_description(command: dict[str, Any]) -> str:
    label = str(command.get("label") or "").strip()
    if label in {"inspect mine skill", "inspect predict skill", "inspect gov skill", "inspect ardi skill", "inspect community skill", "inspect tmr skill", "inspect kya skill"}:
        return "Inspect the local WorkNet skill checkout and runtime files."
    if label in {"mine agent status", "predict status", "ardi status"}:
        return "Check the runtime status without starting a new value-moving action."
    if label == "mine control status":
        return "Check Mine worker controls and active session state."
    if label in {"predict preflight", "ardi preflight"}:
        return "Run the skill preflight before live execution."
    if label in {"predict stake eligibility", "ardi stake guidance"}:
        return "Check stake requirements before committing capital."
    if label == "ardi gas check":
        return "Check Base gas readiness before sending Ardi operations."
    if label == "gov public markets":
        return "Load Gov public market and proposal context."
    if label == "gov phase-aware helper":
        return "Check Gov phase timing before signing actions."
    if label == "gov private state":
        return "Inspect private Gov state locally before any signed transaction."
    if label == "start mine worker":
        return "Start the Mine background worker."
    if label == "pause mine worker":
        return "Pause the active Mine background worker."
    if label == "create gov skill venv":
        return "Create the Gov skill Python virtual environment."
    if label == "install gov skill deps":
        return "Install the Gov skill Python dependencies."
    return "Run the playbook command."


def humanize_public_playbook_commands(playbook: dict[str, Any]) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    commands = playbook.get("commands", [])
    for item in commands if isinstance(commands, list) else []:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        raw_label = str(item.get("label") or "").strip()
        human_label = humanize_playbook_command_label(raw_label)
        normalized["rawLabel"] = raw_label or None
        normalized["label"] = human_label or raw_label
        normalized["description"] = humanize_playbook_command_description(item)
        argv = item.get("argv")
        normalized["command"] = render_argv([str(part) for part in argv]) if isinstance(argv, list) and argv else item.get("command")
        rendered.append(normalized)
    return rendered


def public_playbook_view(playbook: dict[str, Any]) -> dict[str, Any]:
    normalized = project_fields(playbook, PLAYBOOK_PUBLIC_FIELDS)
    normalized["commands"] = humanize_public_playbook_commands(playbook)
    return normalized


def public_review_view(review: dict[str, Any]) -> dict[str, Any]:
    return project_fields(review, REVIEW_PUBLIC_FIELDS)


def public_workstation_status_view(report: dict[str, Any]) -> dict[str, Any]:
    normalized = project_fields(report, WORKSTATION_STATUS_PUBLIC_FIELDS)
    normalized["stateSummary"] = normalize_workstation_state_summary_payload(report.get("stateSummary"))
    return normalized


def public_workstation_preferences_view(report: dict[str, Any]) -> dict[str, Any]:
    return project_fields(report, WORKSTATION_PREFERENCES_PUBLIC_FIELDS)
