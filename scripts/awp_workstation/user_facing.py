"""Small stable user-facing fields for agent narration."""

from __future__ import annotations

from typing import Any, Optional


BOOTSTRAP_STATES = {
    "install_awp_skill_dependency",
    "install_or_setup_wallet",
    "prepare_registration_runtime",
    "setup_needed",
    "needs_runtime_setup",
    "installed-needs-bootstrap",
}

BLOCKED_STATES = {
    "awaiting_confirmation",
    "awaiting_dataset",
    "blocked",
    "manual_review",
    "needs_confirmation",
    "needs_review",
    "needs_runtime_input",
    "network_blocked",
    "partial",
    "partial_ready",
    "registration_blocked",
    "registration_needed",
    "registration_required",
    "review_required",
    "runtime_error",
    "stake_required",
}

FAILED_STATES = {
    "background_failed",
    "failed",
    "runtime_error",
    "state_invalid",
}

RUNNING_STATES = {
    "background_running",
    "running",
    "started_background",
}

PAUSED_STATES = {
    "background_stopped",
    "paused",
    "stopped",
}

COMPLETED_STATES = {
    "background_completed",
    "completed",
    "executed",
    "progressed",
}

READY_STATES = {
    "ready",
    "ready_to_execute",
    "ready_to_start",
}

ACTION_LABELS = {
    "await_confirmation": "review the pending confirmation",
    "execute_when_ready": "run again with --execute when you want to start execution",
    "follow_runtime_guidance": "follow the runtime guidance",
    "install_awp_skill_dependency": "install awp-skill",
    "install_or_setup_wallet": "install or set up the agent wallet",
    "monitor_background_run": "check background progress",
    "monitor_background_runs": "check background progress",
    "prepare_registration_runtime": "prepare the registration runtime",
    "register_agent": "register the agent",
    "registration_already_confirmed": "choose a WorkNet",
    "resume_pending_confirmations": "review pending confirmations",
    "resume_previous_run": "review or restart the previous run",
    "resume_runtime_guidance": "continue the runtime follow-up",
    "retry_registration_preflight": "retry registration preflight",
    "review_epoch": "review the latest epoch",
    "run_awp_skill_registration": "run awp-skill registration",
    "scan_worknets": "choose a WorkNet",
}

NOT_STARTED_STATES = {
    "available_manual",
    "idle",
    "not_started",
    "planned",
    "prepared",
    "ready_to_choose_worknet",
    "resume_available",
    "restart_available",
    "scan_worknets",
}


def _first_text(*values: Any) -> Optional[str]:
    for value in values:
        if isinstance(value, list):
            for item in value:
                text = str(item or "").strip()
                if text:
                    return text
            continue
        text = str(value or "").strip()
        if text:
            return text
    return None


def _nested_dict(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def _first_action(record: dict[str, Any]) -> Optional[str]:
    user_action_details = record.get("userActionDetails")
    if isinstance(user_action_details, list):
        for item in user_action_details:
            if not isinstance(item, dict):
                continue
            action = _first_text(item.get("displayLabel"), item.get("label"))
            if action:
                return action
    user_actions = record.get("userActions") or record.get("user_actions")
    if isinstance(user_actions, list):
        for item in user_actions:
            if isinstance(item, dict):
                action = _first_text(item.get("displayLabel"), item.get("label"))
            else:
                action = _first_text(item)
            if action:
                return action
    return _humanize_action(_first_text(
        record.get("primaryUserActionDisplay"),
        record.get("primaryUserAction"),
        record.get("nextRecommendedAction"),
        record.get("nextAction"),
        _nested_dict(record, "recoveryDecision").get("primaryActionLabel"),
    ))


def _humanize_action(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    return ACTION_LABELS.get(text, text)


def _run_next_action(record: dict[str, Any]) -> Optional[str]:
    next_action = str(record.get("nextAction") or "").strip()
    status = str(record.get("status") or "").strip()
    if next_action == "execute_when_ready" or status == "planned":
        return ACTION_LABELS["execute_when_ready"]
    if next_action in ACTION_LABELS:
        return ACTION_LABELS[next_action]
    return _first_action(record)


def _looks_misleading_for_phase(message: str, phase: str) -> bool:
    lowered = message.lower()
    if "prepared" in lowered:
        return True
    if phase in {"ready", "running"}:
        return False
    ready_claims = (
        " is ready",
        " ready.",
        " ready to",
        "can earn",
        "begin earning",
        "start earning",
        "can start earning",
    )
    return any(claim in lowered for claim in ready_claims)


def _blocking_reason(record: dict[str, Any], phase: str) -> Optional[str]:
    runtime_guidance = _nested_dict(record, "runtimeGuidance")
    recovery_decision = _nested_dict(record, "recoveryDecision")
    state_summary = _nested_dict(record, "stateSummary")
    if phase in {"blocked", "failed", "bootstrapping"}:
        return _first_text(
            record.get("blockingIssues"),
            record.get("failures"),
            record.get("latestFailure"),
            record.get("knowledgeCaveat"),
            recovery_decision.get("message"),
            runtime_guidance.get("message"),
            record.get("reason"),
            state_summary.get("latestFailure"),
            record.get("error"),
        )
    return None


def _raw_state_candidates(record: dict[str, Any]) -> list[str]:
    runtime_guidance = _nested_dict(record, "runtimeGuidance")
    selected_background = _nested_dict(record, "selectedBackground")
    selected_summary = _nested_dict(selected_background, "summary")
    state_summary = _nested_dict(record, "stateSummary")
    candidates: list[Any] = [
        record.get("executionState"),
        record.get("status"),
        record.get("nextAction"),
        record.get("reminderType"),
        runtime_guidance.get("state"),
        selected_summary.get("state"),
        state_summary.get("currentExecutionPhase"),
        state_summary.get("status"),
    ]
    return [str(item).strip().lower() for item in candidates if str(item or "").strip()]


def normalize_user_phase(record: dict[str, Any]) -> str:
    if record.get("shouldNotify") is True and str(record.get("status") or "").strip().lower() in FAILED_STATES:
        return "failed"
    if isinstance(record.get("confirmationQueue"), list) and record.get("confirmationQueue"):
        return "blocked"
    if isinstance(record.get("activeBackgroundProcesses"), list) and record.get("activeBackgroundProcesses"):
        return "running"
    for state in _raw_state_candidates(record):
        if state in FAILED_STATES:
            return "failed"
        if state in RUNNING_STATES:
            return "running"
        if state in PAUSED_STATES:
            return "paused"
        if state in BLOCKED_STATES:
            return "blocked"
        if state in BOOTSTRAP_STATES:
            return "bootstrapping"
        if state in READY_STATES:
            return "ready"
        if state in COMPLETED_STATES:
            return "completed"
        if state in NOT_STARTED_STATES:
            return "not_started"
    if record.get("runnable") is True and str(record.get("cliStatus") or "").strip().lower() == "ready":
        return "ready"
    return "not_started"


def _subject(record: dict[str, Any], *, intent: str) -> str:
    name = _first_text(
        record.get("worknetName"),
        record.get("selectedWorknetName"),
        record.get("requiredSkill"),
        record.get("name"),
        record.get("worknetKey"),
        record.get("selectedWorknetKey"),
        record.get("symbol"),
    )
    if name:
        return name
    if intent == "monitor":
        return "Monitor"
    if intent == "preflight":
        return "Workstation preflight"
    return "Workstation"


def build_user_status(record: dict[str, Any], *, intent: str) -> dict[str, Any]:
    phase = normalize_user_phase(record)
    next_action = _run_next_action(record) if intent == "run" else _first_action(record)
    blocking_reason = _blocking_reason(record, phase)
    return {
        "phase": phase,
        "canEarnNow": phase in {"ready", "running"},
        "nextAction": next_action,
        "blockingReason": blocking_reason,
        "confidence": "high",
    }


def build_user_message(record: dict[str, Any], *, intent: str, user_status: dict[str, Any]) -> str:
    phase = str(user_status.get("phase") or "not_started")
    subject = _subject(record, intent=intent)
    next_action = _first_text(user_status.get("nextAction"))
    blocking_reason = _first_text(user_status.get("blockingReason"))

    if intent == "monitor":
        if record.get("shouldNotify") is True:
            return _first_text(record.get("notificationText"), record.get("message"), record.get("headline")) or "A workstation notification is ready."
        return "No user notification is needed now."
    if intent in {"status", "continue", "earnings", "failures", "research", "review-queue", "switch-worknet", "pause"}:
        existing = _first_text(record.get("answer"), record.get("headline"))
        if existing and not _looks_misleading_for_phase(existing, phase):
            return existing
    if intent == "review":
        existing = _first_text(record.get("dailySummary"), record.get("headline"))
        if existing and not _looks_misleading_for_phase(existing, phase):
            return existing
    if intent == "preflight":
        existing = _first_text(record.get("plainLanguageSummary"))
        if existing and not _looks_misleading_for_phase(existing, phase):
            return existing
    if intent == "run" and phase == "not_started":
        action = f" Next action: {next_action}." if next_action else ""
        return f"{subject} did not start execution; this was a plan-only run.{action}"
    if phase == "running":
        return f"{subject} is running. Check progress before changing routes."
    if phase == "ready":
        action = f" Next action: {next_action}." if next_action else ""
        return f"{subject} is ready to execute.{action}"
    if phase == "bootstrapping":
        reason = f" Blocker: {blocking_reason}." if blocking_reason else ""
        action = f" Next action: {next_action}." if next_action else ""
        return f"{subject} cannot earn yet; setup is still required.{reason}{action}"
    if phase == "blocked":
        reason = f" Reason: {blocking_reason}." if blocking_reason else ""
        action = f" Next action: {next_action}." if next_action else ""
        return f"{subject} cannot continue yet.{reason}{action}"
    if phase == "failed":
        reason = f" Reason: {blocking_reason}." if blocking_reason else ""
        action = f" Next action: {next_action}." if next_action else ""
        return f"{subject} failed.{reason}{action}"
    if phase == "paused":
        action = f" Next action: {next_action}." if next_action else ""
        return f"{subject} is paused.{action}"
    if phase == "completed":
        action = f" Next action: {next_action}." if next_action else ""
        return f"{subject} completed the latest round.{action}"
    action = f" Next action: {next_action}." if next_action else ""
    return f"{subject} has not started earning yet.{action}"


def attach_user_fields(payload: Any, *, intent: str) -> Any:
    if not isinstance(payload, dict):
        return payload
    record = dict(payload)
    user_status = build_user_status(record, intent=intent)
    record["user_status"] = user_status
    record["user_message"] = build_user_message(record, intent=intent, user_status=user_status)
    return record
