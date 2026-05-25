"""Recovery decision and resume-action helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from awp_workstation.action_groups import annotate_recovery_actions, dedupe_action_entries, find_user_action_label
from awp_workstation.action_normalization import (
    choose_default_follow_up_action,
    normalized_confirmation_queue,
    normalized_follow_up_actions,
)
from awp_workstation.action_priority import prioritize_action_entries
from awp_workstation.action_text import review_action_command
from awp_workstation.commands import (
    review_epoch_command,
    run_worknet_command,
    workstation_background_command,
    workstation_confirmation_command,
    workstation_follow_up_command,
    workstation_pause_command,
)
from awp_workstation.worknets import resolve_worknet


def recovery_decision_actions_from_ui(
    user_actions: list[dict[str, Any]],
    action_map: dict[str, str],
    *,
    primary_label: Optional[str] = None,
    restart_label: Optional[str] = None,
    switch_label: Optional[str] = None,
) -> list[dict[str, Any]]:
    priority_labels = [
        label
        for label in [primary_label, restart_label, switch_label, "Pause background work"]
        if isinstance(label, str) and label.strip()
    ]
    items_by_label = {
        str(item.get("label")): item
        for item in user_actions
        if isinstance(item, dict) and isinstance(item.get("label"), str) and item.get("label").strip()
    }
    actions: list[dict[str, Any]] = []
    for label in priority_labels:
        item = items_by_label.get(label)
        command = action_map.get(label)
        if item is None or not isinstance(command, str) or not command.strip():
            continue
        actions.append(
            {
                "label": label,
                "description": str(item.get("description") or "Action details pending."),
                "command": command.strip(),
            }
        )
    return dedupe_action_entries(actions)


def recovery_decision_actions_from_recovery(
    recovery: Any,
    *,
    preferred_profile: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    recovery = recovery if isinstance(recovery, dict) else {}
    preferred_profile = preferred_profile if isinstance(preferred_profile, dict) else None
    worknet_key = str(recovery.get("lastWorknetKey") or "").strip()
    worknet_profile = resolve_worknet(worknet_key) if worknet_key else None
    worknet_name = (
        str(worknet_profile.get("name"))
        if isinstance(worknet_profile, dict) and worknet_profile.get("name")
        else worknet_key
    )
    preferred_key = str(preferred_profile.get("key")) if isinstance(preferred_profile, dict) and preferred_profile.get("key") else None
    actions: list[dict[str, Any]] = []
    active_background = recovery.get("activeBackgroundProcesses", []) if isinstance(recovery.get("activeBackgroundProcesses"), list) else []
    has_runtime_guidance = bool(recovery.get("hasRuntimeGuidance") and recovery.get("followUpActionCount"))

    if (
        recovery.get("hasLatestPlaybook")
        and worknet_key
        and not active_background
        and not has_runtime_guidance
        and (
            not recovery.get("preferFreshStartOverResume")
            or (preferred_key is not None and preferred_key == worknet_key)
        )
    ):
        actions.append(
            {
                "label": f"Start {worknet_name}",
                "description": "Run the latest WorkNet playbook.",
                "command": run_worknet_command(worknet_key, execute=True, auto_advance=True),
            }
        )

    default_confirmation_label = str(recovery.get("defaultConfirmationLabel") or "").strip()
    if default_confirmation_label:
            actions.append(
                {
                    "label": default_confirmation_label,
                    "description": "Review this pending confirmation before execution.",
                    "command": workstation_confirmation_command(default_confirmation_label, execute=False),
                }
            )

    source_follow_up_label = str(recovery.get("sourceFollowUpLabel") or "").strip()
    if source_follow_up_label and recovery.get("oldRunStopped"):
        restart_display = source_follow_up_label.removeprefix("Start ").strip() or source_follow_up_label
        actions.append(
            {
                "label": f"Restart {restart_display}",
                "description": "Restart the stopped runtime follow-up action.",
                "command": workstation_follow_up_command(source_follow_up_label, execute=True),
            }
        )

    default_follow_up_label = str(recovery.get("defaultFollowUpLabel") or "").strip()
    follow_up_actions = recovery.get("followUpActions", []) if isinstance(recovery.get("followUpActions"), list) else []
    if default_follow_up_label and follow_up_actions:
        matched = next(
            (
                item
                for item in follow_up_actions
                if isinstance(item, dict) and str(item.get("label") or "").strip() == default_follow_up_label
            ),
            None,
        )
        if isinstance(matched, dict):
            command = review_action_command(
                worknet_key,
                default_follow_up_label,
                command=str(matched.get("command")) if isinstance(matched.get("command"), str) else None,
                safe_to_auto_run=bool(matched.get("safeToAutoRun")),
                requires_confirmation=bool(matched.get("requiresConfirmation")),
            )
            if command:
                actions.append(
                    {
                        "label": default_follow_up_label,
                        "description": "Follow the runtime-provided next action.",
                        "command": command,
                    }
                )

    if active_background:
        if len(active_background) == 1:
            actions.append(
                {
                    "label": "Pause background work",
                    "description": "Pause the active background process.",
                    "command": workstation_pause_command(execute=True),
                }
            )
        for item in active_background[:3]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if label:
                actions.append(
                    {
                        "label": f"Inspect {label}",
                        "description": "Inspect this background process status and log tail.",
                        "command": workstation_background_command(label, tail_lines=80),
                    }
                )
                actions.append(
                    {
                        "label": f"Stop {label}",
                        "description": "Stop this background process after confirmation.",
                        "command": workstation_background_command(label, stop=True, execute=False),
                    }
                )

    if (
        recovery.get("preferFreshStartOverResume")
        and preferred_profile is not None
        and str(preferred_profile.get("key") or "").strip()
        and str(preferred_profile.get("key")) != worknet_key
    ):
        preferred_key = str(preferred_profile["key"])
        preferred_name = str(preferred_profile.get("name") or preferred_key)
        actions.append(
            {
                "label": f"Start {preferred_name}",
                "description": "Start the preferred WorkNet instead of resuming stale work.",
                "command": run_worknet_command(preferred_key, execute=True, auto_advance=True),
            }
        )

    if recovery.get("hasLatestRun"):
        actions.append(
            {
                "label": "Review latest epoch",
                "description": "Review the latest run and recovery state.",
                "command": review_epoch_command(),
            }
        )

    return dedupe_action_entries(actions)


def recovery_decision_actions_from_run_response(
    response: dict[str, Any],
    *,
    primary_label: Optional[str] = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: Optional[str], description: str, command: Optional[str]) -> None:
        text = str(label or "").strip()
        resolved = str(command or "").strip()
        if not text or not resolved or text in seen:
            return
        actions.append(
            {
                "label": text,
                "description": description,
                "command": resolved,
            }
        )
        seen.add(text)

    queue = normalized_confirmation_queue(response.get("confirmationQueue", []))
    if queue:
        label = str(queue[0].get("label") or "").strip()
        if label:
            add(
                label,
                "Review this pending confirmation before execution.",
                workstation_confirmation_command(label, execute=False),
            )

    follow_up_actions = normalized_follow_up_actions(response.get("followUpActions", []))
    if follow_up_actions:
        default_follow_up = choose_default_follow_up_action(follow_up_actions) or follow_up_actions[0]
        label = str(default_follow_up.get("label") or "").strip()
        if label:
            command = review_action_command(
                str(response.get("selectedWorknetKey") or ""),
                label,
                command=str(default_follow_up.get("command")) if isinstance(default_follow_up.get("command"), str) else None,
                safe_to_auto_run=bool(default_follow_up.get("safeToAutoRun")),
                requires_confirmation=bool(default_follow_up.get("requiresConfirmation")),
            )
            add(
                label,
                "Follow the runtime-provided next action.",
                command,
            )

    active = response.get("activeBackgroundProcesses", [])
    if isinstance(active, list) and active:
        if len(active) == 1 and isinstance(active[0], dict):
            add(
                "Pause background work",
                "Pause the active background process.",
                workstation_pause_command(execute=True),
            )
        for item in active[:3]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if label:
                add(
                    f"Inspect {label}",
                    "Inspect this background process status and log tail.",
                    workstation_background_command(label, tail_lines=80),
                )
                add(
                    f"Stop {label}",
                    "Stop this background process after confirmation.",
                    workstation_background_command(label, stop=True, execute=False),
                )

    selected = response.get("selectedBackground")
    if isinstance(selected, dict):
        label = str(selected.get("label") or "").strip()
        if label:
            add(
                f"Inspect {label}",
                "Inspect this background process status and log tail.",
                workstation_background_command(label, tail_lines=80),
            )
            add(
                f"Stop {label}",
                "Stop this background process after confirmation.",
                workstation_background_command(label, stop=True, execute=False),
            )

    if response.get("playbookSource") == "preferred-worknet-over-stale-run":
        worknet_key = str(response.get("selectedWorknetKey") or "").strip()
        worknet_name = str(response.get("selectedWorknetName") or worknet_key).strip()
        if worknet_key:
            add(
                f"Start {worknet_name}",
                "Run the preferred WorkNet playbook.",
                run_worknet_command(worknet_key, execute=True, auto_advance=True),
            )
    elif response.get("playbookSource") == "last-selected":
        worknet_key = str(response.get("selectedWorknetKey") or "").strip()
        worknet_name = str(response.get("selectedWorknetName") or worknet_key).strip()
        if worknet_key:
            add(
                f"Start {worknet_name}",
                "Run the last-selected WorkNet playbook.",
                run_worknet_command(worknet_key, execute=True, auto_advance=True),
            )

    return dedupe_action_entries(actions)


def humanize_runtime_guidance_message(recovery: dict[str, Any]) -> str:
    raw = str(recovery.get("runtimeGuidanceMessage") or "").strip()
    worknet_key = str(recovery.get("lastWorknetKey") or "")
    next_action = str(recovery.get("runtimeGuidanceNextAction") or "")
    default_label = str(recovery.get("defaultFollowUpLabel") or "").strip()
    if worknet_key == "mine":
        if raw.lower().startswith("please select a dataset"):
            if default_label:
                return f"Mine needs a dataset selection before continuing. Suggested action: {default_label}."
            return "Mine needs a dataset selection before continuing."
        if "mining environment is ready" in raw.lower():
            return "Mine environment is ready."
    if worknet_key == "gov" and next_action == "acquire_awp_power_or_observe_gov":
        return "Gov signed actions need AWP Power; acquire power or observe until eligible."
    if worknet_key == "predict" and next_action == "wait_for_predict_market":
        return "Predict is waiting for a suitable market."
    return raw or "No runtime guidance message is available yet."


def humanize_recovery_stale_reason(reason: Optional[str]) -> Optional[str]:
    text = str(reason or "").strip()
    if not text:
        return None
    mapping = {
        "latest run stopped and only restart guidance remains": "Latest run stopped and only restart guidance remains.",
        "latest review status is blocked": "Latest review is blocked.",
        "latest review status is partial": "Latest review is partial.",
        "latest review status is observe_only": "Latest review is observe-only.",
        "latest review status is awaiting_dataset": "Latest review is waiting for dataset selection.",
    }
    if text in mapping:
        return mapping[text]
    if text.startswith("latest run is ") and text.endswith(" hours old"):
        return text
    return text


def build_recovery_decision(
    recovery: Any,
    *,
    worknet_name: Optional[str] = None,
    preferred_profile: Optional[dict[str, Any]] = None,
    primary_label: Optional[str] = None,
    restart_label: Optional[str] = None,
    switch_label: Optional[str] = None,
    actions: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    recovery = recovery if isinstance(recovery, dict) else {}
    preferred_profile = preferred_profile if isinstance(preferred_profile, dict) else None
    resolved_actions = dedupe_action_entries(
        list(actions or []) + recovery_decision_actions_from_recovery(
            recovery,
            preferred_profile=preferred_profile,
        )
    )
    inferred_continue_label = next(
        (
            item["label"]
            for item in resolved_actions
            if str(item.get("label", "")).strip()
            and not str(item.get("label", "")).strip().lower().startswith(("restart ", "start ", "switch "))
        ),
        None,
    )
    inferred_restart_label = (
        str(restart_label).strip()
        if isinstance(restart_label, str) and restart_label.strip()
        else next((item["label"] for item in resolved_actions if str(item.get("label", "")).strip().lower().startswith("restart ")), None)
    )
    inferred_switch_label = (
        str(switch_label).strip()
        if isinstance(switch_label, str) and switch_label.strip()
        else next((item["label"] for item in resolved_actions if str(item.get("label", "")).strip().lower().startswith(("start ", "switch "))), None)
    )

    last_worknet_key = str(recovery.get("lastWorknetKey") or "").strip() or None

    def prioritize_actions(preferred_label: Optional[str], *, status_hint: str) -> list[dict[str, Any]]:
        prioritized = prioritize_action_entries(
            resolved_actions,
            execution_state=None,
            resume_status=status_hint,
            worknet_key=last_worknet_key,
        )
        label = str(preferred_label or "").strip()
        if not label:
            return prioritized
        first = [item for item in prioritized if str(item.get("label")) == label]
        rest = [item for item in prioritized if str(item.get("label")) != label]
        return annotate_recovery_actions(first + rest)

    last_profile = resolve_worknet(str(recovery.get("lastWorknetKey") or ""))
    last_name = (
        str(last_profile.get("name"))
        if isinstance(last_profile, dict) and last_profile.get("name")
        else str(worknet_name or recovery.get("lastWorknetKey") or "WorkNet")
    )
    preferred_name = (
        str(preferred_profile.get("name"))
        if preferred_profile is not None and preferred_profile.get("name")
        else str(preferred_profile.get("key") or "WorkNet")
        if preferred_profile is not None
        else None
    )
    stale_reason = humanize_recovery_stale_reason(recovery.get("staleLatestRunReason")) or "Previous run is stale."

    if (
        recovery.get("preferFreshStartOverResume")
        and preferred_profile is not None
        and last_profile is not None
        and str(preferred_profile.get("key")) != str(last_profile.get("key"))
    ):
        message = f"{last_name} should start fresh because {stale_reason}"
        if restart_label:
            message += f" Restart option: {restart_label}."
        if switch_label and preferred_name:
            message += f" Preferred switch option: {switch_label} for {preferred_name}."
        elif preferred_name:
            message += f" Preferred WorkNet: {preferred_name}."
        primary_action_label = inferred_switch_label or inferred_restart_label or inferred_continue_label or (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        resolved_actions = prioritize_actions(primary_action_label, status_hint="prefer_fresh_start")
        return {
            "decision": "prefer_fresh_start",
            "status": "prefer_fresh_start",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": stale_reason,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": f"Fresh start preferred for {last_name}",
            "message": message,
        }

    if recovery.get("pendingConfirmations"):
        confirmation_label = str(recovery.get("defaultConfirmationLabel") or "").strip()
        message = "Pending confirmations must be handled before continuing."
        if confirmation_label:
            message = f"Pending confirmation requires review: {confirmation_label}."
        primary_action_label = confirmation_label or (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        resolved_actions = prioritize_actions(primary_action_label, status_hint="needs_confirmation")
        return {
            "decision": "needs_confirmation",
            "status": "needs_confirmation",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": None,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": "Pending confirmation",
            "message": message,
        }

    if recovery.get("oldRunStopped"):
        primary_action_label = inferred_restart_label or inferred_continue_label or (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        message = f"{last_name} has a stopped previous run."
        if restart_label:
            message += f" Restart option: {restart_label}."
        elif primary_action_label:
            message += f" Suggested action: {primary_action_label}."
        resolved_actions = prioritize_actions(primary_action_label, status_hint="restart_available" if restart_label else "resume_available")
        return {
            "decision": "restart_available" if restart_label else "resume_available",
            "status": "restart_available" if restart_label else "resume_available",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": stale_reason if recovery.get("staleLatestRun") else None,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": f"{last_name} restart available",
            "message": message,
        }

    if recovery.get("activeBackgroundCount"):
        primary_action_label = (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        resolved_actions = prioritize_actions(primary_action_label, status_hint="background_running")
        return {
            "decision": "background_running",
            "status": "background_running",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": None,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": "Background work is running",
            "message": "A managed background process is active; monitor, pause, or stop it before starting conflicting work.",
        }

    if recovery.get("hasRuntimeGuidance") and recovery.get("followUpActionCount"):
        primary_action_label = (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        resolved_actions = prioritize_actions(primary_action_label, status_hint="follow_runtime_guidance")
        return {
            "decision": "follow_runtime_guidance",
            "status": "follow_runtime_guidance",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": None,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": "Runtime guidance available",
            "message": "Follow the runtime guidance before changing WorkNet route.",
        }

    primary_action_label = inferred_continue_label or (
        str(primary_label).strip()
        if isinstance(primary_label, str) and primary_label.strip()
        else (resolved_actions[0]["label"] if resolved_actions else None)
    )
    message = f"{last_name} can resume from the previous run."
    if primary_action_label:
        message += f" Suggested action: {primary_action_label}."
    resolved_actions = prioritize_actions(primary_action_label, status_hint="resume_available")
    return {
        "decision": "resume_available",
        "status": "resume_available",
        "lastWorknetName": last_name,
        "preferredWorknetName": preferred_name,
        "staleReason": None,
        "primaryActionLabel": primary_action_label,
        "restartActionLabel": inferred_restart_label,
        "switchActionLabel": inferred_switch_label,
        "actions": resolved_actions,
        "headline": f"{last_name} resume available",
        "message": message,
    }


def build_resume_recovery_briefing(
    recovery: Any,
    user_actions: list[dict[str, Any]],
    *,
    worknet_name: Optional[str] = None,
    preferred_profile: Optional[dict[str, Any]] = None,
    context_message: Optional[str] = None,
    action_map: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    recovery = recovery if isinstance(recovery, dict) else {}
    preferred_profile = preferred_profile if isinstance(preferred_profile, dict) else None
    restart_label = find_user_action_label(user_actions, prefix="Restart ")
    switch_label = find_user_action_label(user_actions, prefix="Switch ")
    primary_label = user_actions[0]["label"] if user_actions else None
    context = str(context_message or "").strip()
    decision = build_recovery_decision(
        recovery,
        worknet_name=worknet_name,
        preferred_profile=preferred_profile,
        primary_label=primary_label,
        restart_label=restart_label,
        switch_label=switch_label,
        actions=recovery_decision_actions_from_ui(
            user_actions,
            action_map if isinstance(action_map, dict) else {},
            primary_label=primary_label,
            restart_label=restart_label,
            switch_label=switch_label,
        ),
    )

    def combine(message: str) -> str:
        body = message.strip()
        if not context or context == body:
            return body
        return f"{context} {body}".strip()
    return {
        "headline": context or str(decision.get("headline") or ""),
        "message": combine(str(decision.get("message") or "")),
        "status": str(decision.get("status") or "resume_available"),
        "decision": decision,
    }


def build_recovery_state_payload(
    state: dict[str, Any],
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("recovery state dependencies are required")
    choose_default_confirmation = dependencies["choose_default_confirmation"]
    choose_default_follow_up_action = dependencies["choose_default_follow_up_action"]
    hours_since_iso = dependencies["hours_since_iso"]
    inspect_background_process = dependencies["inspect_background_process"]
    load_active_processes = dependencies["load_active_processes"]
    load_json = dependencies["load_json"]
    normalized_confirmation_queue = dependencies["normalized_confirmation_queue"]
    normalized_follow_up_actions = dependencies["normalized_follow_up_actions"]
    review_status_display = dependencies["review_status_display"]

    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    pending = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    latest_playbook = load_json(Path(state["playbooks"]) / "last-selected.json", {})
    latest_review = load_json(Path(state["reviews"]) / "latest-review.json", {})
    latest_run_playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
    active_processes = [
        inspect_background_process(state, str(item.get("label")), tail_lines=20)
        for item in load_active_processes(state)
        if isinstance(item, dict) and item.get("label")
    ]
    pending_count = len(pending) if isinstance(pending, list) else 0
    executed_count = len(latest_run.get("executedSteps", [])) if isinstance(latest_run, dict) else 0
    follow_up_actions = normalized_follow_up_actions(latest_run.get("followUpActions", [])) if isinstance(latest_run, dict) else []
    normalized_pending = normalized_confirmation_queue(pending)
    default_follow_up = choose_default_follow_up_action(follow_up_actions)
    default_confirmation = choose_default_confirmation(normalized_pending)
    runtime_guidance = latest_run.get("runtimeGuidance", {}) if isinstance(latest_run, dict) else {}
    runtime_guidance = runtime_guidance if isinstance(runtime_guidance, dict) else {}
    source_follow_up = latest_run.get("sourceFollowUpAction", {}) if isinstance(latest_run, dict) else {}
    last_worknet_key = (
        latest_run_playbook.get("worknetKey")
        if isinstance(latest_run_playbook, dict) and latest_run_playbook.get("worknetKey")
        else (latest_playbook.get("worknetKey") if isinstance(latest_playbook, dict) else None)
    )
    latest_run_generated_at = latest_run.get("generatedAt") if isinstance(latest_run, dict) else None
    latest_run_age_hours = hours_since_iso(latest_run_generated_at)
    latest_review_worknet_key = str(latest_review.get("worknetKey") or "") if isinstance(latest_review, dict) and latest_review.get("worknetKey") else None
    latest_review_matches_last_worknet = bool(
        latest_review_worknet_key
        and last_worknet_key
        and latest_review_worknet_key == str(last_worknet_key)
    )
    latest_review_status = (
        str(latest_review.get("status") or "")
        if isinstance(latest_review, dict) and (latest_review_matches_last_worknet or not last_worknet_key or not latest_review_worknet_key)
        else ""
    )
    latest_review_headline = (
        latest_review.get("headline")
        if isinstance(latest_review, dict) and (latest_review_matches_last_worknet or not last_worknet_key or not latest_review_worknet_key)
        else None
    )
    old_run_stopped = bool(latest_run) and not active_processes and str(runtime_guidance.get("nextAction") or "") == "monitor_background_run"
    stale_statuses = {"restart_available", "blocked", "partial", "observe_only", "awaiting_dataset"}
    stale_due_to_review = latest_review_status in stale_statuses
    stale_due_to_age = bool(latest_run) and not active_processes and pending_count == 0 and latest_run_age_hours is not None and latest_run_age_hours >= 2.0
    stale_latest_run = bool(latest_run) and (old_run_stopped or stale_due_to_review or stale_due_to_age)
    prefer_fresh_start = bool(latest_run) and not active_processes and pending_count == 0 and (
        latest_review_status in {"blocked", "partial", "observe_only", "awaiting_dataset"}
        or stale_due_to_age
        or (stale_latest_run and latest_review_status == "restart_available")
    )
    stale_reason = None
    if prefer_fresh_start and latest_review_status in {"blocked", "partial", "observe_only", "awaiting_dataset"}:
        stale_reason = f"latest review status is {latest_review_status}"
    elif stale_due_to_review and latest_review_status == "restart_available":
        stale_reason = "latest run stopped and only restart guidance remains"
    elif stale_due_to_age:
        stale_reason = f"latest run is {latest_run_age_hours:.1f} hours old"
    return {
        "resumeAvailable": bool(latest_playbook or latest_run or pending_count),
        "pendingConfirmations": pending_count,
        "pendingConfirmationLabels": [item.get("label") for item in normalized_pending],
        "defaultConfirmationLabel": default_confirmation.get("label") if isinstance(default_confirmation, dict) else None,
        "hasLatestRun": bool(latest_run),
        "hasLatestPlaybook": bool(latest_playbook),
        "lastWorknetId": (
            latest_run_playbook.get("worknetId")
            if isinstance(latest_run_playbook, dict) and latest_run_playbook.get("worknetId") is not None
            else (latest_playbook.get("worknetId") if isinstance(latest_playbook, dict) else None)
        ),
        "lastWorknetKey": last_worknet_key,
        "lastMode": latest_run.get("mode") if isinstance(latest_run, dict) else None,
        "executedStepCount": executed_count,
        "hasRuntimeGuidance": bool(runtime_guidance),
        "runtimeGuidanceMessage": runtime_guidance.get("message") if isinstance(runtime_guidance, dict) else None,
        "runtimeGuidanceNextAction": runtime_guidance.get("nextAction") if isinstance(runtime_guidance, dict) else None,
        "followUpActionCount": len(follow_up_actions),
        "autoRunnableFollowUpCount": sum(1 for item in follow_up_actions if item.get("safeToAutoRun") and not item.get("requiresConfirmation") and item.get("argv")),
        "defaultFollowUpLabel": default_follow_up.get("label") if isinstance(default_follow_up, dict) else None,
        "defaultFollowUpCommand": default_follow_up.get("command") if isinstance(default_follow_up, dict) else None,
        "followUpActions": follow_up_actions,
        "sourceFollowUpLabel": source_follow_up.get("label") if isinstance(source_follow_up, dict) else None,
        "activeBackgroundCount": len(active_processes),
        "activeBackgroundLabels": [item.get("label") for item in active_processes],
        "activeBackgroundProcesses": active_processes,
        "latestRunGeneratedAt": latest_run_generated_at,
        "latestRunAgeHours": round(latest_run_age_hours, 2) if latest_run_age_hours is not None else None,
        "latestReviewStatus": latest_review_status or None,
        "latestReviewStatusDisplay": review_status_display(latest_review_status) if latest_review_status else None,
        "latestReviewHeadline": latest_review_headline,
        "latestReviewWorknetKey": latest_review_worknet_key,
        "latestReviewMatchesLastWorknet": latest_review_matches_last_worknet,
        "oldRunStopped": old_run_stopped,
        "staleLatestRun": stale_latest_run,
        "staleLatestRunReason": stale_reason,
        "preferFreshStartOverResume": prefer_fresh_start,
    }
