"""Workstation monitor and reminder evaluation helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from awp_workstation.background_supervisor import background_supervisor_snapshot


SUPPORTED_ADAPTERS = [
    {"key": "codex-heartbeat", "description": "Emit a heartbeat payload for Codex polling or orchestration."},
    {"key": "cron", "description": "Run the monitor from cron or a systemd timer."},
    {"key": "desktop", "description": "Send a local desktop notification."},
    {"key": "telegram-webhook", "description": "Forward the monitor payload to a Telegram webhook adapter."},
    {"key": "discord-webhook", "description": "Forward the monitor payload to a Discord webhook adapter."},
    {"key": "email", "description": "Send the monitor payload through an email adapter."},
]

FAILURE_NOTIFICATION_STATUSES = {
    "background_failed",
    "blocked",
    "partial",
}

CRITICAL_ALWAYS_NOTIFY_STATUSES = {
    "state_invalid",
    "awaiting_confirmation",
    "auth_required",
    "registration_required",
    "stake_required",
    "awaiting_dataset",
}

INFO_NOTIFICATION_STATUSES = {
    "background_completed",
    "ready_to_start",
}

SEVERITY_BY_REMINDER_TYPE = {
    "alert": "error",
    "action_required": "warning",
    "attention": "warning",
    "running": "info",
    "info": "info",
}


def _monitor_cache_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "workstation-monitor.json"


def _parse_clock_minutes(value: Any) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        hours_text, minutes_text = text.split(":", 1)
        hours = int(hours_text)
        minutes = int(minutes_text)
    except (ValueError, TypeError):
        return None
    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        return None
    return hours * 60 + minutes


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _future_iso(minutes: int) -> str:
    return (_local_now() + timedelta(minutes=max(1, int(minutes)))).astimezone().isoformat(timespec="seconds")


def _inside_quiet_hours(preferences: dict[str, Any]) -> bool:
    start_minutes = _parse_clock_minutes(preferences.get("quietHoursStart"))
    end_minutes = _parse_clock_minutes(preferences.get("quietHoursEnd"))
    if start_minutes is None or end_minutes is None or start_minutes == end_minutes:
        return False
    now = _local_now()
    current_minutes = now.hour * 60 + now.minute
    if start_minutes < end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def _json_file_is_invalid(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return True
    if not text.strip():
        return False
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return True
    return False


def _first_text(*items: Any) -> Optional[str]:
    if len(items) == 1 and isinstance(items[0], list):
        candidates = items[0]
    else:
        candidates = items
    for item in candidates:
        text = str(item or "").strip()
        if text:
            return text
    return None


def _report_digest(payload: dict[str, Any]) -> str:
    material = {
        "reminderType": payload.get("reminderType"),
        "status": payload.get("status"),
        "currentTask": payload.get("currentTask"),
        "worknetKey": payload.get("worknetKey"),
        "executionState": payload.get("executionState"),
        "activeBackgroundCount": payload.get("activeBackgroundCount"),
        "waitingForConfirmation": payload.get("waitingForConfirmation"),
        "latestSuccess": payload.get("latestSuccess"),
        "latestFailure": payload.get("latestFailure"),
        "nextRecommendedAction": payload.get("nextRecommendedAction"),
    }
    raw = json.dumps(material, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _cooldown_elapsed(last_delivered_at: Any, *, parse_iso_datetime: Any, cooldown_minutes: int) -> bool:
    parsed = parse_iso_datetime(last_delivered_at)
    if parsed is None:
        return True
    return parsed <= datetime.now(parsed.tzinfo) - timedelta(minutes=max(1, cooldown_minutes))


def _hours_since(timestamp: Any, *, parse_iso_datetime: Any) -> Optional[float]:
    parsed = parse_iso_datetime(timestamp)
    if parsed is None:
        return None
    return max(0.0, (datetime.now(parsed.tzinfo) - parsed).total_seconds() / 3600.0)


def _derive_monitor_state(
    *,
    latest_run: dict[str, Any],
    latest_review: dict[str, Any],
    status_report: dict[str, Any],
    active_background: list[dict[str, Any]],
    pending_confirmations: list[dict[str, Any]],
    source_drift: dict[str, Any],
    invalid_files: list[str],
    parse_iso_datetime: Any,
) -> dict[str, Any]:
    failures = [str(item).strip() for item in latest_review.get("failures", []) if str(item).strip()]
    latest_failure = _first_text(failures)
    latest_success = _first_text(latest_review.get("workDone")) or _first_text(status_report.get("userActions"))
    first_background = active_background[0] if len(active_background) == 1 and isinstance(active_background[0], dict) else None
    background_summary = (
        first_background.get("summary", {})
        if isinstance(first_background, dict) and isinstance(first_background.get("summary"), dict)
        else {}
    )
    background_state = str(background_summary.get("state") or "").strip()
    background_alive = any(bool(item.get("alive")) for item in active_background if isinstance(item, dict))
    active_background_count = len(active_background)
    if not latest_success:
        latest_success = _first_text(background_summary.get("detail"), background_summary.get("headline"))
    if not latest_failure and background_state in {"error", "llm_error", "stopped"}:
        latest_failure = _first_text(background_summary.get("detail"), background_summary.get("headline"))
    worknet_key = (
        str(status_report.get("worknetKey") or "").strip()
        or str(latest_run.get("selectedWorknetKey") or "").strip()
        or str(latest_review.get("worknetKey") or "").strip()
        or None
    )
    worknet_name = (
        str(status_report.get("worknetName") or "").strip()
        or str(latest_run.get("selectedWorknetName") or "").strip()
        or str(latest_review.get("worknetName") or "").strip()
        or None
    )
    current_task = (
        str(latest_run.get("executionHeadline") or "").strip()
        or str(latest_run.get("headline") or "").strip()
        or str(status_report.get("executionHeadline") or "").strip()
        or str(status_report.get("headline") or "").strip()
        or str(latest_review.get("executionHeadline") or "").strip()
        or str(latest_review.get("headline") or "").strip()
        or "Workstation idle"
    )
    execution_state = (
        str(status_report.get("executionState") or "").strip()
        or str(latest_run.get("executionState") or "").strip()
        or str(latest_review.get("executionState") or "").strip()
        or None
    )
    next_recommended_action = (
        str(status_report.get("primaryUserAction") or "").strip()
        or str(latest_review.get("primaryUserAction") or "").strip()
        or str(latest_run.get("primaryUserAction") or "").strip()
        or None
    )
    latest_progress_candidates = [latest_review.get("generatedAt"), latest_run.get("generatedAt")]
    if isinstance(first_background, dict):
        latest_progress_candidates.append(first_background.get("startedAt"))
    progress_hours = min(
        [
            hours
            for hours in (
                _hours_since(value, parse_iso_datetime=parse_iso_datetime)
                for value in latest_progress_candidates
            )
            if hours is not None
        ],
        default=None,
    )

    reminder_type = "info"
    headline = "Workstation is idle."
    message = "No urgent workstation action is pending."
    reason = "no urgent action is pending"
    status = "ok"
    supervisor = background_supervisor_snapshot(first_background, parse_iso_datetime=parse_iso_datetime) if isinstance(first_background, dict) else None

    if invalid_files:
        reminder_type = "alert"
        headline = "State file repair is required."
        message = "One or more workstation state files could not be parsed."
        reason = "invalid state files: " + ", ".join(invalid_files)
        status = "state_invalid"
    elif pending_confirmations:
        selected = pending_confirmations[0] if isinstance(pending_confirmations[0], dict) else {}
        label = str(selected.get("displayLabel") or selected.get("label") or "Pending confirmation").strip()
        reminder_type = "action_required"
        headline = f"Confirmation required: {label}"
        message = "A queued confirmation is waiting for user approval before work can continue."
        reason = "pending confirmation is blocking continuation"
        status = "awaiting_confirmation"
    elif background_state in {"failed", "llm_error"}:
        reminder_type = "alert"
        headline = str(background_summary.get("headline") or "Background runtime failed.").strip()
        message = str(background_summary.get("detail") or "Inspect the background logs and recover the runtime.").strip()
        reason = "background runtime reported a failure state"
        status = "background_failed"
    elif latest_failure:
        reminder_type = "action_required"
        headline = str(latest_review.get("headline") or "Review latest failure").strip()
        message = latest_failure
        reason = "latest review contains a failure that needs action"
        status = str(latest_review.get("status") or "blocked").strip() or "blocked"
    elif supervisor is not None:
        reminder_type = str(supervisor.get("reminderType") or "running")
        headline = str(supervisor.get("headline") or headline).strip()
        message = str(supervisor.get("message") or message).strip()
        reason = str(supervisor.get("reason") or reason).strip()
        status = str(supervisor.get("status") or status).strip()
        progress_hours = supervisor.get("progressHours")
        next_recommended_action = str(supervisor.get("nextActionLabel") or next_recommended_action or "").strip() or next_recommended_action
    elif active_background_count:
        reminder_type = "running"
        background_headline = str(background_summary.get("headline") or "").strip()
        headline = background_headline or "Background work is running."
        message = (
            str(background_summary.get("detail") or "").strip()
            or "The workstation has active background work and should be monitored periodically."
        )
        reason = "background task is still active"
        status = "background_running"
    else:
        review_queue = source_drift.get("reviewQueueSummary", {}) if isinstance(source_drift.get("reviewQueueSummary"), dict) else {}
        pending_reviews = int(review_queue.get("pendingCount") or 0) if str(review_queue.get("pendingCount") or "").strip() else 0
        if pending_reviews > 0:
            reminder_type = "attention"
            headline = str(review_queue.get("headline") or "Knowledge review is pending.").strip()
            message = "Official sources or generated knowledge need review before trusting stale automation."
            reason = "knowledge review queue still has pending entries"
            status = "knowledge_attention"
        elif next_recommended_action:
            reminder_type = "info"
            headline = str(status_report.get("headline") or latest_review.get("headline") or "Workstation status updated.").strip()
            message = str(status_report.get("answer") or latest_review.get("dailySummary") or "A next action is available.").strip()
            reason = "a stable next action is available"
            status = str(status_report.get("status") or latest_review.get("status") or "ready").strip() or "ready"

    return {
        "reminderType": reminder_type,
        "headline": headline,
        "message": message,
        "reason": reason,
        "status": status,
        "currentTask": current_task,
        "worknetKey": worknet_key,
        "worknetName": worknet_name,
        "executionState": execution_state,
        "activeBackgroundCount": active_background_count,
        "waitingForConfirmation": bool(pending_confirmations),
        "latestSuccess": latest_success,
        "latestFailure": latest_failure,
        "nextRecommendedAction": next_recommended_action,
        "primaryUserAction": next_recommended_action,
        "primaryUserActionCommand": (
            supervisor.get("nextActionCommand") if isinstance(supervisor, dict) else None
        ) or status_report.get("primaryUserActionCommand") or latest_review.get("primaryUserActionCommand"),
        "progressHours": progress_hours,
        "activeBackgroundSupervisorState": supervisor.get("state") if isinstance(supervisor, dict) else None,
        "activeBackgroundSupervisorDisplay": supervisor.get("display") if isinstance(supervisor, dict) else None,
        "activeBackgroundSupervisorHeadline": supervisor.get("headline") if isinstance(supervisor, dict) else None,
    }


def _snapshot_monitor_fallback(state_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "reminderType": state_summary.get("reminderType") or ("action_required" if state_summary.get("waitingForConfirmation") else "info"),
        "headline": str(state_summary.get("currentTask") or "Cached workstation snapshot").strip(),
        "message": (
            f"Using cached workstation-state snapshot. Suggested action: {state_summary.get('nextRecommendedAction')}."
            if state_summary.get("nextRecommendedAction")
            else "Using cached workstation-state snapshot."
        ),
        "reason": "rich status caches are missing, so monitor fell back to workstation-state.json",
        "status": state_summary.get("status") or "snapshot_available",
        "currentTask": state_summary.get("currentTask"),
        "worknetKey": state_summary.get("currentWorknetKey"),
        "worknetName": state_summary.get("currentWorknetName"),
        "executionState": state_summary.get("currentExecutionPhase"),
        "activeBackgroundCount": state_summary.get("activeBackgroundCount") or 0,
        "waitingForConfirmation": bool(state_summary.get("waitingForConfirmation")),
        "latestSuccess": state_summary.get("latestSuccess"),
        "latestFailure": state_summary.get("latestFailure"),
        "nextRecommendedAction": state_summary.get("nextRecommendedAction"),
        "primaryUserAction": state_summary.get("nextRecommendedAction"),
        "primaryUserActionCommand": state_summary.get("nextRecommendedActionCommand"),
        "progressHours": None,
        "activeBackgroundSupervisorState": state_summary.get("activeBackgroundState"),
        "activeBackgroundSupervisorDisplay": None,
        "activeBackgroundSupervisorHeadline": state_summary.get("activeBackgroundHeadline"),
    }


def build_workstation_monitor_payload(
    *,
    read_only: bool = False,
    timeline_limit: int = 12,
    persist: bool = True,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("workstation monitor dependencies are required")
    aggregate_background_supervisor_view = dependencies["aggregate_background_supervisor_view"]
    atomic_write_json = dependencies["atomic_write_json"]
    build_epoch_review = dependencies["build_epoch_review"]
    build_timeline_view = dependencies["build_timeline_view"]
    build_workstation_state_summary = dependencies["build_workstation_state_summary"]
    build_workstation_status = dependencies["build_workstation_status"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    load_active_processes = dependencies["load_active_processes"]
    load_cached_workstation_state_summary = dependencies["load_cached_workstation_state_summary"]
    load_json = dependencies["load_json"]
    load_user_preferences = dependencies["load_user_preferences"]
    now_iso = dependencies["now_iso"]
    parse_iso_datetime = dependencies["parse_iso_datetime"]
    persist_background_observation = dependencies["persist_background_observation"]
    state_context = dependencies["state_context"]
    summarize_background_record = dependencies["summarize_background_record"]

    state = state_context()
    preferences = load_user_preferences(state) if read_only else ensure_user_preferences(state)
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    pending_confirmations = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    latest_review = load_json(Path(state["reviews"]) / "latest-review.json", {})
    status_report = load_json(Path(state["cache"]) / "workstation-status.json", {})
    source_drift = load_json(Path(state["cache"]) / "source-drift.json", {})
    cached_state_summary = load_cached_workstation_state_summary(state=state) if read_only else {}
    previous = load_json(_monitor_cache_path(state), {})

    if (not isinstance(latest_review, dict) or not latest_review) and not read_only:
        latest_review = build_epoch_review()
    if (not isinstance(status_report, dict) or not status_report) and not read_only:
        status_report = build_workstation_status(query="What is running?", intent="status", read_only=False)

    active_background = [
        persist_background_observation(
            state,
            summarize_background_record(item, tail_lines=40),
        )
        for item in load_active_processes(state)
        if isinstance(item, dict)
    ]
    aggregate_background = aggregate_background_supervisor_view(active_background) if len(active_background) > 1 else {}
    invalid_files = [
        rel
        for rel in (
            "runs/latest-run.json",
            "runs/active-processes.json",
            "runs/pending-confirmations.json",
            "reviews/latest-review.json",
            "cache/workstation-status.json",
        )
        if _json_file_is_invalid(Path(state["root"]) / rel)
    ]
    if read_only and (not isinstance(status_report, dict) or not status_report) and (not isinstance(latest_review, dict) or not latest_review) and isinstance(cached_state_summary, dict) and cached_state_summary:
        derived = _snapshot_monitor_fallback(cached_state_summary)
    else:
        derived = _derive_monitor_state(
            latest_run=latest_run if isinstance(latest_run, dict) else {},
            latest_review=latest_review if isinstance(latest_review, dict) else {},
            status_report=status_report if isinstance(status_report, dict) else {},
            active_background=active_background,
            pending_confirmations=pending_confirmations if isinstance(pending_confirmations, list) else [],
            source_drift=source_drift if isinstance(source_drift, dict) else {},
            invalid_files=invalid_files,
            parse_iso_datetime=parse_iso_datetime,
        )
        if isinstance(aggregate_background, dict) and aggregate_background.get("count"):
            derived["headline"] = aggregate_background.get("headline") or derived.get("headline")
            derived["message"] = aggregate_background.get("message") or derived.get("message")
            derived["reason"] = aggregate_background.get("reason") or derived.get("reason")
            derived["status"] = aggregate_background.get("status") or derived.get("status")
            derived["reminderType"] = aggregate_background.get("reminderType") or derived.get("reminderType")
            derived["nextRecommendedAction"] = aggregate_background.get("nextActionLabel") or derived.get("nextRecommendedAction")
            derived["primaryUserAction"] = aggregate_background.get("nextActionLabel") or derived.get("primaryUserAction")
            derived["primaryUserActionCommand"] = aggregate_background.get("nextActionCommand") or derived.get("primaryUserActionCommand")
            derived["latestSuccess"] = aggregate_background.get("latestSuccess") or derived.get("latestSuccess")
            derived["latestFailure"] = aggregate_background.get("latestFailure") or derived.get("latestFailure")
            derived["activeBackgroundSupervisorState"] = aggregate_background.get("state")
            derived["activeBackgroundSupervisorDisplay"] = aggregate_background.get("display")
            derived["activeBackgroundSupervisorHeadline"] = aggregate_background.get("headline")

    cooldown_minutes = int(preferences.get("notificationCooldownMinutes") or 60)
    quiet_hours_suppressed = _inside_quiet_hours(preferences) and derived["reminderType"] not in {"alert", "action_required"}
    last_delivered_digest = str(previous.get("lastDeliveredDigest") or "").strip() or None
    last_delivered_at = previous.get("lastDeliveredAt")
    payload = {
        "generatedAt": now_iso(),
        **derived,
        "supportedAdapters": SUPPORTED_ADAPTERS,
        "statusCacheAvailable": bool(status_report),
        "reviewCacheAvailable": bool(latest_review),
        "timeline": build_timeline_view(limit=timeline_limit, state=state),
        "cooldownMinutes": cooldown_minutes,
        "lastDeliveredDigest": last_delivered_digest,
        "lastDeliveredAt": last_delivered_at,
        "quietHoursStart": preferences.get("quietHoursStart"),
        "quietHoursEnd": preferences.get("quietHoursEnd"),
        "quietHoursSuppressed": quiet_hours_suppressed,
        "stateRoot": state["root"],
        "userPreferences": preferences,
    }
    payload["stateSummary"] = build_workstation_state_summary(
        latest_run=latest_run if isinstance(latest_run, dict) else {},
        latest_review=latest_review if isinstance(latest_review, dict) else {},
        status_report=status_report if isinstance(status_report, dict) else {},
        active_background=active_background,
        pending_confirmations=pending_confirmations if isinstance(pending_confirmations, list) else [],
        monitor_report={
            "shouldNotify": None,
            "reminderType": payload.get("reminderType"),
            "nextCheckAt": None,
            "nextRecommendedAction": payload.get("nextRecommendedAction"),
            "primaryUserActionCommand": payload.get("primaryUserActionCommand"),
            "latestSuccess": payload.get("latestSuccess"),
            "latestFailure": payload.get("latestFailure"),
            "activeBackgroundSupervisorState": payload.get("activeBackgroundSupervisorState"),
            "activeBackgroundSupervisorHeadline": payload.get("activeBackgroundSupervisorHeadline"),
        },
    )
    payload["digest"] = _report_digest(payload)
    payload["nextCheckAt"] = _future_iso(
        15 if payload["reminderType"] in {"alert", "action_required"} else
        20 if payload["reminderType"] == "running" else
        120 if payload["reminderType"] == "attention" else
        360
    )
    payload["cooldownUntil"] = (
        _future_iso(cooldown_minutes)
        if last_delivered_digest == payload["digest"] and last_delivered_at
        else None
    )

    should_notify = False
    if not quiet_hours_suppressed:
        failure_controlled = (
            str(payload.get("status") or "").strip() in FAILURE_NOTIFICATION_STATUSES
            or (
                bool(payload.get("latestFailure"))
                and str(payload.get("status") or "").strip() not in CRITICAL_ALWAYS_NOTIFY_STATUSES
            )
        )
        if payload["reminderType"] in {"alert", "action_required"}:
            if failure_controlled and not bool(preferences.get("remindOnFailure", True)):
                should_notify = False
            else:
                should_notify = (
                    payload["digest"] != last_delivered_digest
                    or _cooldown_elapsed(last_delivered_at, parse_iso_datetime=parse_iso_datetime, cooldown_minutes=cooldown_minutes)
                )
        elif payload["reminderType"] == "attention":
            if bool(preferences.get("remindOnStall", True)):
                should_notify = (
                    payload["digest"] != last_delivered_digest
                    or _cooldown_elapsed(last_delivered_at, parse_iso_datetime=parse_iso_datetime, cooldown_minutes=cooldown_minutes)
                )
        elif payload["reminderType"] == "info":
            if (
                str(payload.get("status") or "").strip() in INFO_NOTIFICATION_STATUSES
                and bool(preferences.get("remindOnEarningsChange", True))
            ):
                should_notify = payload["digest"] != last_delivered_digest
    payload["shouldNotify"] = should_notify
    payload["severity"] = SEVERITY_BY_REMINDER_TYPE.get(str(payload.get("reminderType") or ""), "info")
    payload["notificationText"] = (
        str(payload.get("message") or payload.get("headline") or "Workstation status changed.").strip()
        if should_notify
        else None
    )
    if isinstance(payload.get("stateSummary"), dict):
        payload["stateSummary"]["needsReminder"] = should_notify
        payload["stateSummary"]["reminderType"] = payload.get("reminderType")
        payload["stateSummary"]["nextCheckAt"] = payload.get("nextCheckAt")

    previous_delivery_count = int(previous.get("deliveryCount") or 0) if str(previous.get("deliveryCount") or "").strip() else 0
    payload["deliveryCount"] = previous_delivery_count
    if persist and not read_only:
        atomic_write_json(_monitor_cache_path(state), payload)
    return payload


def record_workstation_monitor_delivery_payload(
    report: Any,
    *,
    state: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("monitor delivery dependencies are required")
    atomic_write_json = dependencies["atomic_write_json"]
    now_iso = dependencies["now_iso"]
    state_context = dependencies["state_context"]
    load_json = dependencies["load_json"]

    state = state or state_context()
    payload = report if isinstance(report, dict) else load_json(_monitor_cache_path(state), {})
    updated = dict(payload)
    updated["lastDeliveredDigest"] = updated.get("digest")
    updated["lastDeliveredAt"] = now_iso()
    updated["deliveryCount"] = int(updated.get("deliveryCount") or 0) + 1
    updated["shouldNotify"] = False
    updated["notificationText"] = None
    atomic_write_json(_monitor_cache_path(state), updated)
    return updated
