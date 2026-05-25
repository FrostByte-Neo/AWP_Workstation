"""Alternate user-facing projections for workstation status and timeline data."""

from __future__ import annotations

from typing import Any


def workstation_status_brief_view(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "generatedAt": report.get("generatedAt"),
        "headline": report.get("headline"),
        "answer": report.get("answer"),
        "status": report.get("status"),
        "executionState": report.get("executionState"),
        "executionStateDisplay": report.get("executionStateDisplay"),
        "executionHeadline": report.get("executionHeadline"),
        "worknetKey": report.get("worknetKey"),
        "worknetName": report.get("worknetName"),
        "stateSummary": report.get("stateSummary"),
        "primaryUserAction": report.get("primaryUserAction"),
        "primaryUserActionDisplay": report.get("primaryUserActionDisplay"),
        "primaryUserActionCommand": report.get("primaryUserActionCommand"),
    }


def workstation_actions_only_view(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "generatedAt": report.get("generatedAt"),
        "headline": report.get("headline"),
        "status": report.get("status"),
        "stateSummary": report.get("stateSummary"),
        "primaryUserAction": report.get("primaryUserAction"),
        "primaryUserActionDisplay": report.get("primaryUserActionDisplay"),
        "primaryUserActionCommand": report.get("primaryUserActionCommand"),
        "userActions": report.get("userActions"),
        "userActionDetails": report.get("userActionDetails"),
    }


def workstation_timeline_view(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "generatedAt": report.get("generatedAt"),
        "headline": report.get("headline"),
        "status": report.get("status"),
        "count": report.get("count"),
        "events": report.get("events"),
        "latestEvent": report.get("latestEvent"),
    }


def workstation_monitor_view(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "generatedAt": report.get("generatedAt"),
        "headline": report.get("headline"),
        "message": report.get("message"),
        "status": report.get("status"),
        "reason": report.get("reason"),
        "digest": report.get("digest"),
        "shouldNotify": report.get("shouldNotify"),
        "quietHoursSuppressed": report.get("quietHoursSuppressed"),
        "nextCheckAt": report.get("nextCheckAt"),
        "reminderType": report.get("reminderType"),
        "currentTask": report.get("currentTask"),
        "worknetKey": report.get("worknetKey"),
        "worknetName": report.get("worknetName"),
        "executionState": report.get("executionState"),
        "primaryUserAction": report.get("primaryUserAction"),
        "primaryUserActionCommand": report.get("primaryUserActionCommand"),
        "activeBackgroundCount": report.get("activeBackgroundCount"),
        "waitingForConfirmation": report.get("waitingForConfirmation"),
        "latestSuccess": report.get("latestSuccess"),
        "latestFailure": report.get("latestFailure"),
        "stateSummary": report.get("stateSummary"),
        "supportedAdapters": report.get("supportedAdapters"),
    }
