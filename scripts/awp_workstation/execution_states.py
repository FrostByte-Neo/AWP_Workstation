"""Execution and recovery status display helpers."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.narratives import canonical_worknet_plain_text
from awp_workstation.text import join_product_sentences


def review_status_display(status: Any) -> Optional[str]:
    mapping = {
        "idle": "Idle",
        "not_started": "Not started",
        "prepared": "Not started",
        "ready": "Ready",
        "running": "Running",
        "paused": "Paused",
        "failed": "Failed",
        "completed": "Completed",
        "bootstrapping": "Bootstrapping",
        "progressed": "Progressed",
        "awaiting_dataset": "Awaiting dataset selection",
        "observe_only": "Observe only",
        "restart_available": "Restart available",
        "partial": "Partially completed",
        "blocked": "Blocked",
    }
    code = str(status or "").strip()
    if not code:
        return None
    return mapping.get(code, code)


def recovery_status_display(status: Any) -> Optional[str]:
    mapping = {
        "resume_available": "Resume available",
        "restart_available": "Restart available",
        "prefer_fresh_start": "Fresh start preferred",
        "needs_confirmation": "Needs confirmation",
        "follow_runtime_guidance": "Follow runtime guidance",
        "background_running": "Background running",
    }
    code = str(status or "").strip()
    if not code:
        return None
    return mapping.get(code, code)


def execution_state_display(status: Any) -> Optional[str]:
    code = str(status or "").strip()
    if not code:
        return None
    review_display = review_status_display(code)
    if review_display and review_display != code:
        return review_display
    mapping = {
        "setup_needed": "Setup needed",
        "registration_needed": "Registration needed",
        "registration_blocked": "Registration blocked",
        "ready_to_choose_worknet": "Choose WorkNet",
        "awaiting_confirmation": "Awaiting confirmation",
        "ready_for_follow_up": "Ready for follow-up",
        "background_running": "Background running",
        "resume_available": "Resume available",
        "knowledge_ready": "Knowledge ready",
        "knowledge_review_needed": "Knowledge review needed",
        "knowledge_fresh": "Knowledge fresh",
        "stale_knowledge_pending": "Stale knowledge pending",
        "source_ready": "Source ready",
        "source_review_needed": "Source review needed",
        "source_missing": "Source missing",
        "review_required": "Review required",
        "ready_to_execute": "Ready to execute",
        "observe_only": "Observe only",
        "needs_runtime_setup": "Runtime setup needed",
        "partial_ready": "Partially ready",
        "runtime_error": "Runtime error",
        "network_blocked": "Network blocked",
        "manual_review": "Manual review needed",
        "executed": "Executed",
    }
    return mapping.get(code, code)


def execution_state_payload(
    status: Any,
    *,
    headline: Optional[str] = None,
) -> dict[str, Optional[str]]:
    code = str(status or "").strip()
    if not code:
        return {
            "executionState": None,
            "executionStateDisplay": None,
            "executionHeadline": None,
        }
    default_headline_map = {
        "knowledge_ready": "Knowledge is ready.",
        "knowledge_review_needed": "Knowledge review is needed.",
        "knowledge_fresh": "Knowledge is fresh.",
        "stale_knowledge_pending": "Stale knowledge review is pending.",
        "source_ready": "Source is ready.",
        "source_review_needed": "Source review is needed.",
        "source_missing": "Source is missing.",
    }
    return {
        "executionState": code,
        "executionStateDisplay": execution_state_display(code),
        "executionHeadline": str(headline or default_headline_map.get(code) or "").strip() or None,
    }


def derive_execution_state(
    *,
    review: Any = None,
    recovery: Any = None,
    next_action: Any = None,
) -> dict[str, Any]:
    status = None
    headline = None
    if isinstance(review, dict):
        review_status = str(review.get("status") or "").strip()
        if review_status:
            status = review_status
            headline = str(review.get("headline") or "").strip() or None
    if status is None and isinstance(recovery, dict):
        latest_review_status = str(recovery.get("latestReviewStatus") or "").strip()
        if latest_review_status:
            status = latest_review_status
            headline = str(recovery.get("latestReviewHeadline") or "").strip() or None
    if status is None:
        action = str(next_action or "").strip()
        mapping = {
            "install_awp_skill_dependency": "setup_needed",
            "run_awp_skill_registration": "registration_needed",
            "register_agent": "registration_needed",
            "retry_registration_preflight": "registration_blocked",
            "scan_worknets": "ready_to_choose_worknet",
            "resume_pending_confirmations": "awaiting_confirmation",
            "resume_runtime_guidance": "ready_for_follow_up",
            "monitor_background_runs": "background_running",
            "resume_previous_run": "resume_available",
        }
        status = mapping.get(action)
    return {
        "executionState": status or None,
        "executionStateDisplay": execution_state_display(status) if status else None,
        "executionHeadline": headline,
    }


def derive_playbook_execution_state(
    profile: dict[str, Any],
    *,
    inspection_status: Any,
    knowledge_caveat: Optional[str],
) -> dict[str, Any]:
    name = str(profile.get("name") or profile.get("key") or "WorkNet").strip()
    status = str(inspection_status or "").strip()
    if knowledge_caveat:
        execution_state = "review_required"
        headline = knowledge_caveat
    elif status == "ready":
        execution_state = "ready_to_execute"
        headline = f"{name} playbook is ready to execute."
    elif status == "installed-needs-bootstrap":
        execution_state = "needs_runtime_setup"
        headline = f"{name} needs runtime bootstrap."
    elif status == "partial":
        execution_state = "partial_ready"
        headline = f"{name} is partially ready and needs review."
    elif status == "runtime-error":
        execution_state = "runtime_error"
        headline = f"{name} runtime reported an error."
    elif status == "network-blocked":
        execution_state = "network_blocked"
        headline = f"{name} runtime probes are blocked by the network."
    elif status in {"remote-profile-only", "empty-official-repo"}:
        execution_state = "manual_review"
        headline = f"{name} needs manual review before execution."
    else:
        execution_state = "needs_runtime_setup"
        headline = f"{name} needs runtime setup."
    return {
        "executionState": execution_state,
        "executionStateDisplay": execution_state_display(execution_state),
        "executionHeadline": headline,
    }


def runtime_confirmation_queue_preview(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    return [
        {"label": str(item.get("label") or "").strip()}
        for item in items
        if isinstance(item, dict) and isinstance(item.get("label"), str) and item.get("label").strip()
    ]


def derive_runtime_execution_state(
    response: Any,
    *,
    headline: Optional[str] = None,
    recovery: Any = None,
) -> dict[str, Any]:
    response = response if isinstance(response, dict) else {}
    recovery = recovery if isinstance(recovery, dict) else {}
    status = str(response.get("status") or "").strip()
    next_action = str(response.get("nextAction") or "").strip()
    queue = runtime_confirmation_queue_preview(response.get("confirmationQueue", []))
    runtime_guidance = response.get("runtimeGuidance", {}) if isinstance(response.get("runtimeGuidance"), dict) else {}
    executed_steps = response.get("executedSteps", []) if isinstance(response.get("executedSteps"), list) else []
    step_statuses = {
        str(item.get("status") or "").strip()
        for item in executed_steps
        if isinstance(item, dict) and str(item.get("status") or "").strip()
    }
    execution_state = None
    if queue or status == "needs_confirmation" or next_action == "await_confirmation":
        execution_state = "awaiting_confirmation"
    elif status == "background_running" or next_action == "monitor_background_run":
        execution_state = "background_running"
    elif status == "needs_runtime_input" or next_action == "follow_runtime_guidance":
        execution_state = "ready_for_follow_up"
    elif status == "executed" or next_action == "review_epoch":
        execution_state = "executed"
    elif step_statuses and step_statuses.issubset({"planned", "available_manual"}):
        execution_state = "not_started"
    elif status == "planned" and (
        response.get("selectedWorknetKey")
        or response.get("selectedBackground")
        or response.get("playbookSource")
    ):
        execution_state = "not_started"
    elif status:
        execution_state = status
    selected_name = str(response.get("selectedWorknetName") or response.get("selectedWorknetKey") or "selected WorkNet").strip()
    chosen_headline = str(headline or response.get("headline") or "").strip() or None
    if execution_state == "not_started":
        latest_review_headline = str(recovery.get("latestReviewHeadline") or "").strip()
        if latest_review_headline:
            chosen_headline = latest_review_headline
        elif selected_name:
            chosen_headline = f"{selected_name} is selected but has not started."
    elif execution_state == "awaiting_confirmation":
        first_label = queue[0].get("label") if queue else None
        if isinstance(first_label, str) and first_label.strip():
            chosen_headline = f"Pending confirmation: {first_label.strip()}."
        elif not chosen_headline:
            chosen_headline = "Pending confirmation."
    elif execution_state == "ready_for_follow_up":
        guidance_message = str(runtime_guidance.get("message") or "").strip()
        if guidance_message:
            chosen_headline = guidance_message
        elif selected_name:
            chosen_headline = f"{selected_name} has runtime guidance ready."
    elif execution_state == "executed":
        if next_action == "review_epoch" and selected_name:
            chosen_headline = f"{selected_name} execution finished; review the epoch."
        elif not chosen_headline:
            chosen_headline = "Execution finished; review the epoch."
    elif execution_state == "background_running":
        guidance_message = str(runtime_guidance.get("message") or "").strip()
        if guidance_message:
            chosen_headline = guidance_message
        elif not chosen_headline:
            chosen_headline = "Background work is running."
    return {
        "executionState": execution_state or None,
        "executionStateDisplay": execution_state_display(execution_state) if execution_state else None,
        "executionHeadline": chosen_headline,
    }


def align_run_execution_user_message(
    user_message: Optional[str],
    *,
    execution_state: Any,
    execution_headline: Optional[str],
    primary_action: Optional[str],
    worknet_context_key: Optional[str],
    include_canonical_plain: bool = True,
    extra_parts: Optional[list[str]] = None,
) -> Optional[str]:
    state = str(execution_state or "").strip()
    base_message = str(user_message or "").strip()
    if state != "not_started":
        return base_message or None
    detail = str(execution_headline or "").strip()
    if not detail:
        return base_message or None
    parts: list[str] = []
    plain = canonical_worknet_plain_text(worknet_context_key) if include_canonical_plain else None
    if plain:
        parts.append(plain)
    parts.append(detail)
    action_label = str(primary_action or "").strip()
    if action_label:
        parts.append(f"Suggested action: {action_label}.")
    for item in extra_parts or []:
        text = str(item or "").strip()
        if text:
            parts.append(text)
    return join_product_sentences(parts) or base_message or None
