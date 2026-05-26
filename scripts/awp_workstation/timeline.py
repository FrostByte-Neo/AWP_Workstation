"""Timeline event persistence and view helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def timeline_path(state: dict[str, Any]) -> Path:
    return Path(state["runs"]) / "timeline.jsonl"


def normalize_timeline_event_payload(event: Any) -> dict[str, Any]:
    source = event if isinstance(event, dict) else {}
    normalized = {
        "generatedAt": source.get("generatedAt"),
        "eventType": source.get("eventType"),
        "source": source.get("source"),
        "headline": source.get("headline"),
        "message": source.get("message"),
        "status": source.get("status"),
        "executionState": source.get("executionState"),
        "nextAction": source.get("nextAction"),
        "currentTask": source.get("currentTask"),
        "worknetKey": source.get("worknetKey"),
        "worknetName": source.get("worknetName"),
        "primaryUserAction": source.get("primaryUserAction"),
        "activeBackgroundCount": source.get("activeBackgroundCount"),
        "waitingForConfirmation": bool(source.get("waitingForConfirmation")),
        "requiresAttention": bool(source.get("requiresAttention")),
        "latestSuccess": source.get("latestSuccess"),
        "latestFailure": source.get("latestFailure"),
        "nextCheckAt": source.get("nextCheckAt"),
    }
    return normalized


def _timeline_signature(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        event.get("eventType"),
        event.get("source"),
        event.get("headline"),
        event.get("message"),
        event.get("status"),
        event.get("executionState"),
        event.get("nextAction"),
        event.get("currentTask"),
        event.get("worknetKey"),
        event.get("worknetName"),
        event.get("primaryUserAction"),
        event.get("activeBackgroundCount"),
        event.get("waitingForConfirmation"),
        event.get("requiresAttention"),
        event.get("latestSuccess"),
        event.get("latestFailure"),
    )


def append_timeline_event_payload(
    state: dict[str, Any],
    event: Any,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("timeline event dependencies are required")
    append_jsonl = dependencies["append_jsonl"]
    now_iso = dependencies["now_iso"]

    normalized = normalize_timeline_event_payload(event)
    if not normalized.get("generatedAt"):
        normalized["generatedAt"] = now_iso()
    existing = load_timeline_events_payload(state, limit=1)
    if existing and _timeline_signature(existing[0]) == _timeline_signature(normalized):
        return existing[0]
    append_jsonl(timeline_path(state), normalized)
    return normalized


def load_timeline_events_payload(
    state: dict[str, Any],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    path = timeline_path(state)
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in reversed(lines):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        events.append(normalize_timeline_event_payload(payload))
        if len(events) >= max(1, int(limit)):
            break
    return events


def build_timeline_view_payload(
    *,
    state: dict[str, Any],
    limit: int = 20,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("timeline view dependencies are required")
    now_iso = dependencies["now_iso"]

    events = load_timeline_events_payload(state, limit=limit)
    latest = events[0] if events else None
    return {
        "generatedAt": now_iso(),
        "headline": (
            str(latest.get("headline") or "No timeline event is recorded yet.").strip()
            if isinstance(latest, dict)
            else "No timeline event is recorded yet."
        ),
        "status": "available" if events else "empty",
        "count": len(events),
        "events": events,
        "latestEvent": latest,
        "stateRoot": state["root"],
    }


def timeline_event_from_run_payload(
    run_record: Any,
    final_payload: Any,
    confirmation_queue: Any,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("run timeline dependencies are required")
    now_iso = dependencies["now_iso"]

    record = run_record if isinstance(run_record, dict) else {}
    payload = final_payload if isinstance(final_payload, dict) else {}
    playbook = record.get("playbook", {}) if isinstance(record.get("playbook"), dict) else {}
    active = payload.get("activeBackgroundProcesses", [])
    confirmations = confirmation_queue if isinstance(confirmation_queue, list) else []
    return normalize_timeline_event_payload(
        {
            "generatedAt": now_iso(),
            "eventType": "run",
            "source": "run-workstation",
            "headline": payload.get("headline") or payload.get("executionHeadline") or "Workstation run updated.",
            "message": payload.get("userMessage") or payload.get("progress"),
            "status": payload.get("status"),
            "executionState": payload.get("executionState"),
            "nextAction": payload.get("nextAction"),
            "currentTask": playbook.get("goal") or playbook.get("role") or record.get("mode"),
            "worknetKey": payload.get("selectedWorknetKey") or playbook.get("worknetKey"),
            "worknetName": payload.get("selectedWorknetName") or playbook.get("requiredSkill"),
            "primaryUserAction": payload.get("primaryUserAction"),
            "activeBackgroundCount": len(active) if isinstance(active, list) else 0,
            "waitingForConfirmation": bool(confirmations),
            "requiresAttention": bool(confirmations) or str(payload.get("status") or "") in {"failed", "needs_confirmation"},
        }
    )


def timeline_event_from_review_payload(
    review: Any,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("review timeline dependencies are required")
    now_iso = dependencies["now_iso"]

    payload = review if isinstance(review, dict) else {}
    work_done = [str(item).strip() for item in payload.get("workDone", []) if str(item).strip()]
    failures = [str(item).strip() for item in payload.get("failures", []) if str(item).strip()]
    return normalize_timeline_event_payload(
        {
            "generatedAt": now_iso(),
            "eventType": "review",
            "source": "review-epoch",
            "headline": payload.get("headline") or "Review updated.",
            "message": payload.get("dailySummary") or payload.get("reporterNote"),
            "status": payload.get("status"),
            "executionState": payload.get("executionState"),
            "nextAction": payload.get("primaryUserAction"),
            "currentTask": payload.get("executionHeadline") or payload.get("headline"),
            "worknetKey": payload.get("worknetKey"),
            "worknetName": payload.get("worknetName"),
            "primaryUserAction": payload.get("primaryUserAction"),
            "requiresAttention": bool(failures) or str(payload.get("status") or "") in {"blocked", "partial"},
            "latestSuccess": work_done[0] if work_done else None,
            "latestFailure": failures[0] if failures else None,
        }
    )


def timeline_event_from_monitor_payload(
    monitor: Any,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("monitor timeline dependencies are required")
    now_iso = dependencies["now_iso"]

    payload = monitor if isinstance(monitor, dict) else {}
    return normalize_timeline_event_payload(
        {
            "generatedAt": now_iso(),
            "eventType": "monitor",
            "source": "workstation-monitor",
            "headline": payload.get("headline") or "Monitor evaluation updated.",
            "message": payload.get("message") or payload.get("reason"),
            "status": payload.get("status"),
            "executionState": payload.get("executionState"),
            "nextAction": payload.get("nextRecommendedAction"),
            "currentTask": payload.get("currentTask"),
            "worknetKey": payload.get("worknetKey"),
            "worknetName": payload.get("worknetName"),
            "primaryUserAction": payload.get("primaryUserAction"),
            "activeBackgroundCount": payload.get("activeBackgroundCount"),
            "waitingForConfirmation": payload.get("waitingForConfirmation"),
            "requiresAttention": bool(payload.get("shouldNotify")),
            "latestSuccess": payload.get("latestSuccess"),
            "latestFailure": payload.get("latestFailure"),
            "nextCheckAt": payload.get("nextCheckAt"),
        }
    )


def timeline_event_from_background_observation_payload(
    observation: Any,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("background timeline dependencies are required")
    now_iso = dependencies["now_iso"]

    payload = observation if isinstance(observation, dict) else {}
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    status = str(payload.get("supervisorStatus") or "").strip() or ("background_running" if payload.get("alive") else "background_stopped")
    headline = (
        str(payload.get("supervisorHeadline") or "").strip()
        or str(summary.get("headline") or "").strip()
        or "Background observation updated."
    )
    message = (
        str(payload.get("supervisorMessage") or "").strip()
        or str(summary.get("detail") or "").strip()
        or headline
    )
    reminder_type = str(payload.get("supervisorReminderType") or "").strip().lower()
    requires_attention = reminder_type in {"alert", "action_required", "attention"} or status in {
        "background_failed",
        "background_stopped",
        "background_stalled",
        "auth_required",
        "registration_required",
        "stake_required",
        "awaiting_dataset",
    }
    latest_success = None
    latest_failure = None
    if status in {"background_running", "background_waiting", "ready_to_start"}:
        latest_success = str(summary.get("detail") or summary.get("headline") or "").strip() or None
    if requires_attention:
        latest_failure = str(summary.get("detail") or summary.get("headline") or "").strip() or None

    return normalize_timeline_event_payload(
        {
            "generatedAt": now_iso(),
            "eventType": "background",
            "source": "background-supervisor",
            "headline": headline,
            "message": message,
            "status": status,
            "executionState": payload.get("supervisorState") or summary.get("state"),
            "nextAction": payload.get("supervisorNextActionLabel"),
            "currentTask": summary.get("headline") or payload.get("label"),
            "worknetKey": payload.get("worknetKey"),
            "worknetName": payload.get("worknetName"),
            "primaryUserAction": payload.get("supervisorNextActionLabel"),
            "activeBackgroundCount": 1,
            "requiresAttention": requires_attention,
            "latestSuccess": latest_success,
            "latestFailure": latest_failure,
        }
    )
