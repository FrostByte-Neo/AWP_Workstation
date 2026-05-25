"""Unified workstation state snapshot helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def _first_text(items: Any) -> Optional[str]:
    if isinstance(items, list):
        for item in items:
            text = str(item or "").strip()
            if text:
                return text
        return None
    text = str(items or "").strip()
    return text or None


def _first_value(*candidates: Any) -> Any:
    for value in candidates:
        if value not in (None, "", [], {}):
            return value
    return None


def build_workstation_state_summary_payload(
    *,
    latest_run: Any,
    latest_review: Any,
    status_report: Any,
    active_background: Any,
    pending_confirmations: Any,
    monitor_report: Any = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("workstation state dependencies are required")
    now_iso = dependencies["now_iso"]

    run_record = latest_run if isinstance(latest_run, dict) else {}
    review_record = latest_review if isinstance(latest_review, dict) else {}
    status_record = status_report if isinstance(status_report, dict) else {}
    monitor_record = monitor_report if isinstance(monitor_report, dict) else {}
    active = active_background if isinstance(active_background, list) else []
    pending = pending_confirmations if isinstance(pending_confirmations, list) else []
    first_background = active[0] if active and isinstance(active[0], dict) else {}
    background_summary = first_background.get("summary", {}) if isinstance(first_background.get("summary"), dict) else {}
    background_headline = _first_value(
        monitor_record.get("activeBackgroundSupervisorHeadline"),
        background_summary.get("headline") if isinstance(background_summary, dict) else None,
    )
    background_detail = _first_value(
        background_summary.get("detail") if isinstance(background_summary, dict) else None,
        background_headline,
    )

    current_task = _first_value(
        status_record.get("executionHeadline"),
        run_record.get("executionHeadline"),
        review_record.get("executionHeadline"),
        status_record.get("headline"),
        run_record.get("headline"),
        review_record.get("headline"),
    )
    current_worknet_key = _first_value(
        status_record.get("worknetKey"),
        run_record.get("selectedWorknetKey"),
        review_record.get("worknetKey"),
    )
    current_worknet_name = _first_value(
        status_record.get("worknetName"),
        run_record.get("selectedWorknetName"),
        review_record.get("worknetName"),
    )
    current_execution_phase = _first_value(
        status_record.get("executionState"),
        run_record.get("executionState"),
        review_record.get("executionState"),
        status_record.get("status"),
        run_record.get("status"),
        review_record.get("status"),
    )
    current_execution_phase_display = _first_value(
        status_record.get("executionStateDisplay"),
        run_record.get("executionStateDisplay"),
        review_record.get("executionStateDisplay"),
    )
    latest_success = _first_value(
        monitor_record.get("latestSuccess"),
        _first_text(review_record.get("workDone")),
        background_detail,
        _first_text(status_record.get("userActions")),
    )
    latest_failure = _first_value(
        monitor_record.get("latestFailure"),
        _first_text(review_record.get("failures")),
    )
    next_action = _first_value(
        monitor_record.get("nextRecommendedAction"),
        status_record.get("primaryUserAction"),
        review_record.get("primaryUserAction"),
        run_record.get("primaryUserAction"),
    )
    next_action_command = _first_value(
        monitor_record.get("primaryUserActionCommand"),
        status_record.get("primaryUserActionCommand"),
        review_record.get("primaryUserActionCommand"),
        run_record.get("primaryUserActionCommand"),
    )
    background_state = _first_value(
        monitor_record.get("activeBackgroundSupervisorState"),
        background_summary.get("state") if isinstance(background_summary, dict) else None,
    )

    return {
        "generatedAt": now_iso(),
        "currentTask": current_task,
        "currentWorknetKey": current_worknet_key,
        "currentWorknetName": current_worknet_name,
        "currentExecutionPhase": current_execution_phase,
        "currentExecutionPhaseDisplay": current_execution_phase_display,
        "status": _first_value(status_record.get("status"), run_record.get("status"), review_record.get("status")),
        "resumeStatus": _first_value(status_record.get("resumeStatus"), run_record.get("resumeStatus"), review_record.get("resumeStatus")),
        "hasActiveBackgroundProcesses": bool(active),
        "activeBackgroundCount": len(active),
        "activeBackgroundLabel": first_background.get("label") if isinstance(first_background, dict) else None,
        "activeBackgroundState": background_state,
        "activeBackgroundHeadline": background_headline,
        "waitingForConfirmation": bool(pending),
        "pendingConfirmationCount": len(pending),
        "latestSuccess": latest_success,
        "latestFailure": latest_failure,
        "nextRecommendedAction": next_action,
        "nextRecommendedActionCommand": next_action_command,
        "needsReminder": bool(monitor_record.get("shouldNotify")) if isinstance(monitor_record, dict) else None,
        "reminderType": monitor_record.get("reminderType") if isinstance(monitor_record, dict) else None,
        "nextCheckAt": monitor_record.get("nextCheckAt") if isinstance(monitor_record, dict) else None,
    }


def workstation_state_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "workstation-state.json"


def persist_workstation_state_summary_payload(
    state: dict[str, Any],
    summary: Any,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("workstation state persistence dependencies are required")
    atomic_write_json = dependencies["atomic_write_json"]
    normalized = summary if isinstance(summary, dict) else {}
    atomic_write_json(workstation_state_path(state), normalized)
    return normalized


def load_cached_workstation_state_summary_payload(
    state: dict[str, Any],
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("workstation state cache dependencies are required")
    load_json = dependencies["load_json"]
    payload = load_json(workstation_state_path(state), {})
    return payload if isinstance(payload, dict) else {}
