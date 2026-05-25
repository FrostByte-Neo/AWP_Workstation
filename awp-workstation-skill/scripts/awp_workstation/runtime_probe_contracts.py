"""Runtime probe response contract fields and projection helpers."""

from __future__ import annotations

from typing import Any

from awp_workstation.contracts import project_fields


RUNTIME_PROBE_SHARED_FIELDS = [
    "label",
    "labelRaw",
    "displayLabel",
    "command",
    "commandRaw",
    "commandDisplay",
    "summary",
    "summaryDisplay",
    "summaryRaw",
    "preview",
    "previewDisplay",
    "previewRaw",
    "message",
    "messageDisplay",
    "messageRaw",
    "textDisplay",
    "textRaw",
    "state",
    "stateDisplay",
    "userActions",
    "userActionsDisplay",
    "userActionsRaw",
    "nextCommand",
    "nextCommandDisplay",
    "nextCommandRaw",
    "detailDisplay",
    "detailRaw",
    "errorSummaryDisplay",
    "errorSummaryRaw",
    "status",
    "statusDisplay",
    "locatorDisplay",
    "resultDisplay",
    "runtimeGuidanceDisplay",
]

RUNTIME_PROBE_TOP_LEVEL_FIELDS = [
    "skillKey",
    "status",
    "statusDisplay",
    "summary",
    "summaryDisplay",
    "summaryRaw",
    "preview",
    "previewDisplay",
    "previewRaw",
    "itemCount",
    "items",
    "highlights",
]

RUNTIME_PROBE_ITEM_FIELDS = [
    "key",
    *RUNTIME_PROBE_SHARED_FIELDS,
]

RUNTIME_PROBE_HIGHLIGHT_FIELDS = [
    "recordKind",
    "recordKey",
    "fullRecordKey",
    "key",
    "label",
    "headline",
    "preview",
    "command",
    "queryCommand",
    "primaryCommand",
    "freshnessStatus",
    "freshnessStatusDisplay",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
    *RUNTIME_PROBE_SHARED_FIELDS,
    "summaryPreview",
    "summaryFull",
    "probeLabel",
    "skillKey",
]

RUNTIME_PROBE_EVIDENCE_FIELDS = [
    "key",
    "topicKey",
    *RUNTIME_PROBE_SHARED_FIELDS,
    "claim",
    "claimDisplay",
    "claimRaw",
    "sourceKey",
    "sourceName",
    "sourceNameDisplay",
    "locator",
    "evidenceType",
    "evidenceTypeDisplay",
    "stability",
    "stabilityDisplay",
    "rationale",
    "rationaleDisplay",
    "sourceUrl",
    "trustTier",
]


def normalize_runtime_probe_payload(record: Any, fields: list[str]) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, fields)


def runtime_probe_contract_fields(item: Any) -> dict[str, Any]:
    return normalize_runtime_probe_payload(item, RUNTIME_PROBE_SHARED_FIELDS)


def build_runtime_probe_contract_item(
    *,
    key: Any,
    raw_label: Any,
    display_label: Any,
    command: Any,
    locator_display: Any,
    status: Any,
    status_display: Any,
    summary: Any,
    summary_raw: Any,
    preview: Any,
    preview_raw: Any,
    message: Any,
    message_raw: Any,
    state: Any,
    state_display: Any,
    user_actions: Any,
    user_actions_display: Any,
    user_actions_raw: Any,
    next_command: Any,
    next_command_display: Any,
    next_command_raw: Any,
    text_display: Any,
    text_raw: Any,
    detail_display: Any,
    detail_raw: Any,
    error_summary_display: Any,
    error_summary_raw: Any,
    result_display: Any,
    runtime_guidance_display: Any,
) -> dict[str, Any]:
    payload = {
        "key": key,
        "label": raw_label,
        "labelRaw": raw_label,
        "displayLabel": display_label,
        "command": command,
        "commandRaw": command,
        "commandDisplay": display_label,
        "locatorDisplay": locator_display,
        "status": status,
        "statusDisplay": status_display,
        "summary": summary,
        "summaryDisplay": summary,
        "summaryRaw": summary_raw,
        "preview": preview,
        "previewDisplay": preview,
        "previewRaw": preview_raw,
        "message": message,
        "messageDisplay": message,
        "messageRaw": message_raw,
        "state": state,
        "stateDisplay": state_display,
        "userActions": user_actions,
        "userActionsDisplay": user_actions_display,
        "userActionsRaw": user_actions_raw,
        "nextCommand": next_command,
        "nextCommandDisplay": next_command_display,
        "nextCommandRaw": next_command_raw,
        "textDisplay": text_display,
        "textRaw": text_raw,
        "detailDisplay": detail_display,
        "detailRaw": detail_raw,
        "errorSummaryDisplay": error_summary_display,
        "errorSummaryRaw": error_summary_raw,
        "resultDisplay": result_display,
        "runtimeGuidanceDisplay": runtime_guidance_display,
    }
    return normalize_runtime_probe_payload(payload, RUNTIME_PROBE_ITEM_FIELDS)
