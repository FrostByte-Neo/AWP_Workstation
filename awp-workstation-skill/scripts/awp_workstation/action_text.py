"""User-action labels, descriptions, and public action detail helpers."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.action_groups import annotate_recovery_actions
from awp_workstation.action_priority import prioritize_action_entries
from awp_workstation.commands import workstation_confirmation_command, workstation_follow_up_command
from awp_workstation.execution_states import recovery_status_display


def runtime_follow_up_description(worknet_key: str, label: str) -> str:
    if worknet_key == "mine":
        if label == "Basic Amazon Products Dataset":
            return "Choose the basic Amazon product dataset and start the first Mine collection round."
        if label == "Basic Amazon Products Pending Dataset":
            return "Continue with the pending Amazon product dataset if you want a smaller follow-up batch."
        if label == "Amazon Reviews Dataset":
            return "Choose the Amazon reviews dataset and start the first Mine collection round."
        return "Choose a Mine dataset and continue the data collection loop."
    if worknet_key == "gov":
        if label in {"Check Gov current phase", "       Gov             "}:
            return "Check the current Gov phase and only use public actions first."
        if label in {"View Gov markets", "       Gov markets"}:
            return "Read current public Gov markets before considering votes or orders."
        if label in {"Check staking status", "       staking       "}:
            return "Check whether principal staking or AWP Power is available."
        return "Continue with Gov observation while keeping signed actions behind confirmation."
    if worknet_key == "predict":
        if "loop" in label.lower():
            return "Let Predict continue its quiet observation loop."
        if "context" in label.lower() or "predict" in label.lower():
            return "Refresh Predict market context before making another decision."
    return "Continue with the recommended next runtime action."


def review_action_command(
    worknet_key: str,
    label: str,
    *,
    command: Optional[str],
    safe_to_auto_run: bool,
    requires_confirmation: bool,
) -> Optional[str]:
    if requires_confirmation:
        return workstation_follow_up_command(label, execute=False)
    if safe_to_auto_run:
        return workstation_follow_up_command(label, execute=True)
    if isinstance(command, str) and command.strip():
        return command.strip()
    return None


def humanize_review_action_entry(
    worknet_key: str,
    label: str,
    *,
    command: Optional[str],
    safe_to_auto_run: bool,
    requires_confirmation: bool,
) -> str:
    resolved_command = review_action_command(
        worknet_key,
        label,
        command=command,
        safe_to_auto_run=safe_to_auto_run,
        requires_confirmation=requires_confirmation,
    )
    prefix = label
    if worknet_key == "mine":
        prefix = label
    elif worknet_key == "gov":
        prefix = label
    if resolved_command:
        return f"{prefix}: {resolved_command}"
    return prefix


def humanize_review_action_label(worknet_key: str, label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return text
    mapping = {
        "       Gov markets": "View Gov markets",
        "       Gov             ": "Check Gov phase",
        "       staking       ": "Check staking status",
        "       Predict context": "View Predict context",
        "predict context": "View Predict context",
        "       Predict stake       ": "Check Predict eligibility",
        "       Predict loop            ": "Start Predict loop",
        "       Predict loop                  ": "Start Predict quiet loop",
        "       Predict             ": "Start Predict loop",
        "       Predict                         ": "Start Predict quiet loop",
        "    Base Gas": "Check Base gas",
        "       Ardi preflight": "Run Ardi preflight",
        "       Ardi stake       ": "Check Ardi stake",
        "submit gov order": "Submit Gov order",
        "Basic Amazon Products Dataset": "Use Amazon products dataset",
        "Basic Amazon Products Pending Dataset": "Use pending Amazon products dataset",
        "Amazon Reviews Dataset": "Use Amazon reviews dataset",
    }
    return mapping.get(text, text)


def humanize_public_action_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return text
    return humanize_review_action_label("", text)


def humanize_review_confirmation_label(worknet_key: str, label: str) -> str:
    display = humanize_review_action_label(worknet_key, label)
    prefix = f"Confirm {display}"
    if worknet_key == "gov":
        prefix = f"Confirm Gov action: {display}"
    elif worknet_key == "predict":
        prefix = f"Confirm Predict action: {display}"
    elif worknet_key == "ardi":
        prefix = f"Confirm Ardi action: {display}"
    return prefix


def humanize_review_confirmation_entry(worknet_key: str, label: str) -> str:
    prefix = humanize_review_confirmation_label(worknet_key, label)
    return f"{prefix}: {workstation_confirmation_command(label, execute=False)}"


def append_unique_action_detail(
    items: list[dict[str, Any]],
    *,
    label: Optional[str],
    display_label: Optional[str] = None,
    description: Optional[str],
    command: Optional[str],
) -> None:
    text = str(label or "").strip()
    resolved_command = str(command or "").strip()
    if not text or not resolved_command:
        return
    if any(isinstance(item, dict) and item.get("label") == text for item in items):
        return
    items.append(
        {
            "label": text,
            "displayLabel": str(display_label or humanize_public_action_label(text)).strip() or humanize_public_action_label(text),
            "description": str(description or "Action pending.").strip(),
            "command": resolved_command,
        }
    )


def humanize_public_action_description(label: str, description: str) -> str:
    text = str(description or "").strip()
    label_text = str(label or "").strip()
    if not text:
        return text
    replacements = {
        "       WorkNet     playbook": "WorkNet playbook",
        "       runtime": "runtime",
        "runtime             ": "runtime",
        " dataset ": " dataset ",
    }
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    direct_map = {
        "Review WorkNet playbook": "Open the generated WorkNet playbook.",
        "Inspect runtime": "Inspect the local runtime before execution.",
        "Open WorkNet playbook": "Open the WorkNet playbook before execution.",
    }
    if text in direct_map:
        normalized = direct_map[text]
    if not normalized:
        normalized = "Action pending."
    if label_text == "Review":
        normalized = "Review this action before continuing."
    return normalized


def humanize_public_action_entries(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    entries: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        normalized = dict(item)
        normalized["label"] = label
        normalized["description"] = humanize_public_action_description(
            label,
            str(item.get("description") or "Action pending.").strip(),
        )
        entries.append(normalized)
    return entries


def humanize_public_recovery_decision(decision: Any) -> Any:
    if not isinstance(decision, dict):
        return decision
    normalized = dict(decision)
    normalized["statusDisplay"] = recovery_status_display(decision.get("status"))
    raw_actions = decision.get("actions") if isinstance(decision.get("actions"), list) else []
    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in raw_actions
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    normalized_actions = humanize_public_action_entries(raw_actions)
    normalized["actions"] = annotate_recovery_actions(prioritize_ui_actions(
        normalized_actions,
        action_map,
        execution_state=None,
        resume_status=str(decision.get("status") or "").strip() or None,
        worknet_key=None,
    ))
    if normalized["actions"]:
        normalized["primaryActionLabel"] = str(normalized["actions"][0].get("label") or "").strip() or normalized.get("primaryActionLabel")
    return normalized


def action_details_from_ui_actions(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        description = humanize_public_action_description(
            label,
            str(item.get("description") or "Action pending.").strip(),
        )
        command = action_map.get(label)
        append_unique_action_detail(
            details,
            label=label,
            description=description,
            command=command if isinstance(command, str) else None,
        )
    return details


def prioritize_ui_actions(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    *,
    execution_state: Optional[str],
    resume_status: Optional[str] = None,
    worknet_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        entries.append(
            {
                "label": label,
                "description": str(item.get("description") or "Review this action.").strip(),
                "command": str(action_map.get(label) or "").strip() or None,
            }
        )
    prioritized = prioritize_action_entries(
        entries,
        execution_state=execution_state,
        resume_status=resume_status,
        worknet_key=worknet_key,
    )
    return [
        {
            "label": str(item.get("label") or "").strip(),
            "description": str(item.get("description") or "Review this action.").strip(),
        }
        for item in prioritized
        if str(item.get("label") or "").strip()
    ]


def action_details_from_decision(decision: Any) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    if not isinstance(decision, dict):
        return details
    actions = decision.get("actions")
    if not isinstance(actions, list):
        return details
    for item in actions:
        if not isinstance(item, dict):
            continue
        append_unique_action_detail(
            details,
            label=str(item.get("label") or "").strip(),
            description=humanize_public_action_description(
                str(item.get("label") or "").strip(),
                str(item.get("description") or "Review this action.").strip(),
            ),
            command=str(item.get("command") or "").strip(),
        )
    return details


def humanize_review_action_description(
    worknet_key: str,
    label: str,
    *,
    requires_confirmation: bool = False,
) -> str:
    text = str(label or "").strip()
    if requires_confirmation:
        if worknet_key == "gov":
            return "Confirm the Gov signed action before execution."
        if worknet_key == "predict":
            return "Confirm the Predict capital-bearing action before execution."
        if worknet_key == "ardi":
            return "Confirm the Ardi value-moving action before execution."
        return "Confirm this action before execution."
    mapping = {
        "       Gov markets": "Review live Gov market context.",
        "       Gov             ": "Review Gov helper output.",
        "       staking       ": "Check AWP Power and staking readiness.",
        "       Predict context": "Refresh Predict market context.",
        "predict context": "Refresh Predict market context.",
        "       Predict stake       ": "Check Predict stake eligibility.",
        "       Predict loop            ": "Start the Predict loop.",
        "       Predict loop                  ": "Start the Predict loop with notifications.",
        "       Predict             ": "Start the Predict loop.",
        "       Predict                         ": "Start the Predict loop with notifications.",
        "       Ardi preflight": "Run Ardi preflight checks.",
        "       Ardi stake       ": "Check Ardi stake eligibility.",
        "    Base Gas": "Check Base gas before running Ardi.",
        "Buy and stake Ardi": "Buy and stake before running Ardi commits.",
        "    KYA             ": "Open KYA eligibility guidance.",
        "Basic Amazon Products Dataset": "Select the Basic Amazon Products dataset.",
        "Basic Amazon Products Pending Dataset": "Select the pending Basic Amazon Products dataset.",
        "Amazon Reviews Dataset": "Select the Amazon Reviews dataset.",
    }
    if text in mapping:
        return mapping[text]
    return runtime_follow_up_description(worknet_key, text)


def prioritize_review_actions(
    worknet_key: str,
    status: str,
    user_actions: list[str],
    user_action_details: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    detail_by_label = {
        str(item.get("label") or "").strip(): dict(item)
        for item in user_action_details
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    }
    seed_entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for label in user_actions:
        text = str(label or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        entry = detail_by_label.get(text, {"label": text, "command": None})
        seed_entries.append(entry)
    for item in user_action_details:
        text = str(item.get("label") or "").strip() if isinstance(item, dict) else ""
        if not text or text in seen:
            continue
        seen.add(text)
        seed_entries.append(dict(item))
    prioritized = prioritize_action_entries(
        seed_entries,
        execution_state=status,
        resume_status=None,
        worknet_key=worknet_key,
    )
    reordered_actions = [str(item.get("label") or "").strip() for item in prioritized if str(item.get("label") or "").strip()]
    reordered_details = [item for item in prioritized if str(item.get("label") or "").strip() in detail_by_label]
    return reordered_actions, reordered_details
