#!/usr/bin/env python3
"""Emit a proactive workstation monitor notification contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from awp_workstation_lib import (
    build_workstation_status,
    load_active_processes,
    load_json,
    now_iso,
    print_json,
    public_workstation_status_view,
    state_context,
    summarize_background_record,
)
from awp_workstation.storage import atomic_write_json


def monitor_state_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "workstation-monitor.json"


def notification_severity(status: dict[str, Any], active: list[dict[str, Any]]) -> str:
    code = str(status.get("status") or "").strip()
    if status.get("error") or code in {"cache_missing", "blocked", "failed", "runtime-error"}:
        return "alert"
    recovery = status.get("recoveryDecision") if isinstance(status.get("recoveryDecision"), dict) else {}
    if recovery.get("pendingConfirmations") or code in {"awaiting_confirmation", "resume_pending_confirmations"}:
        return "action_required"
    if active or code in {"background_running", "monitor_background_runs"}:
        return "running"
    if status.get("resumeStatus") or code in {"resume_available", "resume_runtime_guidance"}:
        return "action_required"
    queue = status.get("knowledgeReviewQueueSummary")
    if isinstance(queue, dict) and queue.get("hasPendingReviews"):
        return "attention"
    return "info"


def next_check_seconds(severity: str, active: list[dict[str, Any]]) -> int:
    if severity in {"alert", "action_required"}:
        return 300
    if active or severity == "running":
        return 900
    if severity == "attention":
        return 1800
    return 3600


def repeat_notify_seconds(severity: str) -> int | None:
    if severity == "alert":
        return 900
    if severity == "action_required":
        return 3600
    if severity == "attention":
        return 7200
    return None


def seconds_since_iso(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()


def repeat_notification_due(previous: dict[str, Any], severity: str) -> bool:
    interval = repeat_notify_seconds(severity)
    if interval is None:
        return False
    age = seconds_since_iso(previous.get("lastNotifiedAt"))
    return age is None or age >= interval


def notification_title(status: dict[str, Any], severity: str) -> str:
    headline = str(status.get("headline") or "").strip()
    if severity == "alert":
        return "AWP needs attention"
    if severity == "action_required":
        return "AWP is waiting for you"
    if severity == "running":
        return "AWP work is running"
    return headline or "AWP workstation status"


def notification_body(status: dict[str, Any], active: list[dict[str, Any]]) -> str:
    if active:
        first = active[0]
        summary = first.get("summary") if isinstance(first.get("summary"), dict) else {}
        headline = str(summary.get("headline") or "").strip()
        detail = str(summary.get("detail") or "").strip()
        if headline and detail:
            return f"{headline} {detail}"
        if headline:
            return headline
    answer = str(status.get("answer") or status.get("executionHeadline") or status.get("headline") or "").strip()
    return answer or "No workstation status summary is available yet."


def digest_notification(payload: dict[str, Any]) -> str:
    stable = {
        "severity": payload.get("severity"),
        "title": payload.get("title"),
        "body": payload.get("body"),
        "primaryAction": payload.get("primaryAction"),
        "status": payload.get("status"),
    }
    raw = json.dumps(stable, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_monitor_report(*, read_only: bool, force: bool, full: bool) -> dict[str, Any]:
    state = state_context()
    status_full = build_workstation_status(
        query="现在任务进展如何",
        intent="status",
        read_only=read_only,
    )
    status = public_workstation_status_view(status_full)
    active = [
        summarize_background_record(item, tail_lines=40)
        for item in load_active_processes(state)
        if isinstance(item, dict)
    ]
    severity = notification_severity(status, active)
    notification = {
        "severity": severity,
        "title": notification_title(status, severity),
        "body": notification_body(status, active),
        "status": status.get("status"),
        "primaryAction": status.get("primaryUserAction"),
        "primaryActionCommand": status.get("primaryUserActionCommand"),
    }
    digest = digest_notification(notification)
    previous = load_json(monitor_state_path(state), {})
    previous_digest = previous.get("lastDigest") if isinstance(previous, dict) else None
    previous_state = previous if isinstance(previous, dict) else {}
    changed = digest != previous_digest
    should_notify = force or changed or repeat_notification_due(previous_state, severity)
    generated_at = now_iso()
    report = {
        "generatedAt": generated_at,
        "stateRoot": state["root"],
        "shouldNotify": should_notify,
        "digest": digest,
        "previousDigest": previous_digest,
        "nextCheckSeconds": next_check_seconds(severity, active),
        "notification": notification,
        "activeBackgroundProcesses": active,
        "statusSnapshot": {
            "headline": status.get("headline"),
            "answer": status.get("answer"),
            "status": status.get("status"),
            "resumeStatus": status.get("resumeStatus"),
            "executionState": status.get("executionState"),
            "worknetKey": status.get("worknetKey"),
            "worknetName": status.get("worknetName"),
            "primaryUserAction": status.get("primaryUserAction"),
            "primaryUserActionCommand": status.get("primaryUserActionCommand"),
        },
        "commands": {
            "status": "python3 scripts/workstation-status.py --intent status",
            "monitor": "python3 scripts/workstation-monitor.py",
            "forceNotify": "python3 scripts/workstation-monitor.py --force",
        },
    }
    if full:
        report["status"] = status
    atomic_write_json(
        monitor_state_path(state),
        {
            "lastCheckedAt": generated_at,
            "lastNotifiedAt": generated_at if should_notify else previous.get("lastNotifiedAt") if isinstance(previous, dict) else None,
            "lastDigest": digest,
            "lastSeverity": severity,
            "lastTitle": notification["title"],
            "nextCheckSeconds": report["nextCheckSeconds"],
        },
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--read-only", action="store_true", help="Use cached workstation status where possible.")
    parser.add_argument("--force", action="store_true", help="Mark the current notification as worth sending.")
    parser.add_argument("--full", action="store_true", help="Include the full public workstation status payload.")
    args = parser.parse_args()
    print_json(build_monitor_report(read_only=args.read_only, force=args.force, full=args.full))


if __name__ == "__main__":
    main()
