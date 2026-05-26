"""Source drift report construction and cache helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from awp_workstation.reference_exports import write_reference_export
from awp_workstation.state import state_context
from awp_workstation.storage import atomic_write_json, load_json
from awp_workstation.utils import now_iso


def source_drift_report_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "source-drift.json"


def snapshot_results_map(snapshot: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return {}
    results = snapshot.get("results")
    if not isinstance(results, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in results:
        if isinstance(item, dict) and isinstance(item.get("key"), str):
            mapped[str(item["key"])] = item
    return mapped


def build_source_drift_report(
    *,
    state: Optional[dict[str, Any]] = None,
    current_snapshot: Optional[dict[str, Any]] = None,
    previous_snapshot: Any = None,
) -> dict[str, Any]:
    state = state or state_context()
    current_snapshot = current_snapshot or load_json(Path(state["cache"]) / "source-snapshot.json", {})
    if previous_snapshot is None:
        previous_snapshot = load_json(Path(state["cache"]) / "source-snapshot.previous.json", None)
    current_map = snapshot_results_map(current_snapshot)
    previous_map = snapshot_results_map(previous_snapshot)
    items: list[dict[str, Any]] = []
    all_keys = sorted(set(current_map.keys()) | set(previous_map.keys()))
    changed = 0
    content_changed = 0
    availability_changed = 0
    unreachable = 0
    for key in all_keys:
        current = current_map.get(key)
        previous = previous_map.get(key)
        name = (
            current.get("name")
            if isinstance(current, dict) and current.get("name")
            else (previous.get("name") if isinstance(previous, dict) else key)
        )
        status = "unchanged"
        changed_fields: list[str] = []
        note = None
        if previous is None:
            status = "no-baseline"
            note = "No previous snapshot exists, so this source becomes the baseline."
        elif current is None:
            status = "missing-current"
            changed_fields.append("results")
            note = "The source was present in the previous snapshot but is missing from the current snapshot."
        else:
            if bool(previous.get("ok")) != bool(current.get("ok")):
                changed_fields.append("availability")
            if previous.get("status") != current.get("status"):
                changed_fields.append("http_status")
            if previous.get("contentType") != current.get("contentType"):
                changed_fields.append("content_type")
            if previous.get("sha256") != current.get("sha256"):
                changed_fields.append("sha256")
            if previous.get("bytes") != current.get("bytes"):
                changed_fields.append("bytes")
            if previous.get("error") != current.get("error"):
                changed_fields.append("error")
            if "availability" in changed_fields:
                status = "availability_changed"
            elif any(field in changed_fields for field in ("sha256", "bytes", "content_type")):
                status = "content_changed"
            elif changed_fields:
                status = "metadata_changed"
            if status == "availability_changed":
                note = "The source availability changed and should be reviewed before trusting cached knowledge."
            elif status == "content_changed":
                note = "The source content changed and downstream knowledge may need review."
            elif status == "metadata_changed":
                note = "Only source metadata such as HTTP status, content type, size, or error text changed."
        if status != "unchanged":
            changed += 1
        if status == "content_changed":
            content_changed += 1
        if status == "availability_changed":
            availability_changed += 1
        if isinstance(current, dict) and not current.get("ok"):
            unreachable += 1
        items.append(
            {
                "key": key,
                "name": name,
                "status": status,
                "changedFields": changed_fields,
                "note": note,
                "previous": {
                    "ok": previous.get("ok") if isinstance(previous, dict) else None,
                    "status": previous.get("status") if isinstance(previous, dict) else None,
                    "sha256": previous.get("sha256") if isinstance(previous, dict) else None,
                    "bytes": previous.get("bytes") if isinstance(previous, dict) else None,
                    "fetchedAt": previous.get("fetchedAt") if isinstance(previous, dict) else None,
                },
                "current": {
                    "ok": current.get("ok") if isinstance(current, dict) else None,
                    "status": current.get("status") if isinstance(current, dict) else None,
                    "sha256": current.get("sha256") if isinstance(current, dict) else None,
                    "bytes": current.get("bytes") if isinstance(current, dict) else None,
                    "fetchedAt": current.get("fetchedAt") if isinstance(current, dict) else None,
                },
            }
        )
    report = {
        "generatedAt": now_iso(),
        "baselineGeneratedAt": previous_snapshot.get("generatedAt") if isinstance(previous_snapshot, dict) else None,
        "currentGeneratedAt": current_snapshot.get("generatedAt") if isinstance(current_snapshot, dict) else None,
        "baselineAvailable": bool(previous_map),
        "summary": {
            "trackedSources": len(items),
            "changedSources": changed,
            "contentChanged": content_changed,
            "availabilityChanged": availability_changed,
            "currentlyUnreachable": unreachable,
        },
        "items": items,
    }
    if isinstance(previous_snapshot, dict):
        atomic_write_json(Path(state["cache"]) / "source-snapshot.previous.json", previous_snapshot)
    atomic_write_json(source_drift_report_path(state), report)
    write_reference_export("source-drift.json", report)
    return report


def load_cached_source_drift(state: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    state = state or state_context()
    payload = load_json(source_drift_report_path(state), None)
    return payload if isinstance(payload, dict) else None
