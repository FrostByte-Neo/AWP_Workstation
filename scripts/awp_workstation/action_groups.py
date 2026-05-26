"""User-action grouping, ordering, and recovery-action helpers."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.contracts import (
    EXECUTION_ACTION_GROUP_LABEL_OVERRIDES,
    RESEARCH_HIGHLIGHT_GROUP_LABELS,
    RESEARCH_HIGHLIGHT_GROUP_RANKS,
    RESEARCH_HIGHLIGHT_TIER_LABELS,
    RESEARCH_HIGHLIGHT_TIER_RANKS,
)


def append_user_action(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    *,
    label: Optional[str],
    description: str,
    command: Optional[str],
) -> None:
    text = str(label or "").strip()
    resolved_command = str(command or "").strip()
    if not text or not resolved_command:
        return
    if any(isinstance(item, dict) and item.get("label") == text for item in actions):
        return
    actions.append({"label": text, "description": description})
    action_map[text] = resolved_command


def merge_recovery_decision_actions(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    decision: Any,
    *,
    prefer_front: bool = False,
) -> None:
    if not isinstance(decision, dict):
        return
    items = decision.get("actions")
    if not isinstance(items, list):
        return
    desired_order: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        command = item.get("command") if isinstance(item.get("command"), str) else None
        if not label or not isinstance(command, str) or not command.strip():
            continue
        action_map[label] = command.strip()
        desired_order.append(
            {
                "label": label,
                "description": str(item.get("description") or "Review this recovery action."),
            }
        )

    if prefer_front and desired_order:
        existing_by_label = {
            str(item.get("label")): item
            for item in actions
            if isinstance(item, dict) and isinstance(item.get("label"), str) and item.get("label").strip()
        }
        ordered: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in desired_order:
            label = item["label"]
            ordered.append(
                existing_by_label.get(
                    label,
                    {
                        "label": label,
                        "description": item["description"],
                    },
                )
            )
            seen.add(label)
        for item in actions:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label or label in seen:
                continue
            ordered.append(item)
        actions[:] = ordered
    else:
        for item in desired_order:
            if any(isinstance(existing, dict) and existing.get("label") == item["label"] for existing in actions):
                continue
            actions.append(item)


def maybe_promote_recovery_decision(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    decision: Any,
) -> None:
    if not isinstance(decision, dict):
        return
    status = str(decision.get("status") or "").strip()
    if status not in {"resume_available", "restart_available", "prefer_fresh_start", "needs_confirmation", "follow_runtime_guidance", "background_running"}:
        return
    merge_recovery_decision_actions(actions, action_map, decision, prefer_front=True)


def merge_payload_user_actions(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    payload: Any,
) -> None:
    if not isinstance(payload, dict):
        return
    items = payload.get("user_actions")
    source_map = payload.get("_internal", {}).get("action_map", {})
    if not isinstance(items, list) or not isinstance(source_map, dict):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        description = str(item.get("description") or "Review this runtime action.")
        command = source_map.get(label)
        append_user_action(
            actions,
            action_map,
            label=label,
            description=description,
            command=command if isinstance(command, str) else None,
        )


def merge_payload_user_action_details(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    payload: Any,
    *,
    limit: Optional[int] = None,
) -> None:
    if not isinstance(payload, dict):
        return
    items = payload.get("userActionDetails")
    if not isinstance(items, list):
        return
    for item in items[:limit] if isinstance(limit, int) and limit >= 0 else items:
        if not isinstance(item, dict):
            continue
        label = item.get("displayLabel") or item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        append_user_action(
            actions,
            action_map,
            label=label,
            description=str(item.get("description") or "Review this runtime action.").strip(),
            command=str(item.get("command") or "").strip() or None,
        )


def find_user_action_label(
    actions: list[dict[str, Any]],
    *,
    exact: Optional[str] = None,
    prefix: Optional[str] = None,
    contains: Optional[str] = None,
) -> Optional[str]:
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        if exact and label == exact:
            return label
        if prefix and label.startswith(prefix):
            return label
        if contains and contains in label:
            return label
    return None


def frontload_user_action_labels(
    actions: list[dict[str, Any]],
    labels: list[Any],
) -> list[dict[str, Any]]:
    if not isinstance(actions, list) or not actions:
        return actions
    wanted = [str(label or "").strip() for label in labels if str(label or "").strip()]
    if not wanted:
        return actions
    existing_by_label = {
        str(item.get("label") or "").strip(): item
        for item in actions
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    }
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for label in wanted:
        item = existing_by_label.get(label)
        if not isinstance(item, dict):
            continue
        ordered.append(item)
        seen.add(label)
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label or label in seen:
            continue
        ordered.append(item)
    return ordered


def annotate_research_action_details(
    user_action_details: list[dict[str, Any]],
    *,
    current_labels: list[Any],
    control_labels: list[Any],
    source_labels: list[Any],
    topic_labels: list[Any],
    worknet_labels: list[Any],
    reference_labels: list[Any],
    background_labels: Optional[list[Any]] = None,
    review_labels: Optional[list[Any]] = None,
    confirmation_labels: Optional[list[Any]] = None,
    current_tier: str = "current",
    control_tier: str = "overview",
    source_tier: str = "overview",
    topic_tier: str = "overview",
    worknet_tier: str = "overview",
    reference_tier: str = "overview",
    background_tier: str = "current",
    review_tier: str = "related",
    confirmation_tier: str = "current",
    group_label_overrides: Optional[dict[str, str]] = None,
    group_rank_overrides: Optional[dict[str, int]] = None,
    tier_label_overrides: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    normalized_buckets = [
        ("current", current_tier, {str(item or "").strip() for item in current_labels if str(item or "").strip()}),
        ("confirmations", confirmation_tier, {str(item or "").strip() for item in (confirmation_labels or []) if str(item or "").strip()}),
        ("background", background_tier, {str(item or "").strip() for item in (background_labels or []) if str(item or "").strip()}),
        ("control", control_tier, {str(item or "").strip() for item in control_labels if str(item or "").strip()}),
        ("sources", source_tier, {str(item or "").strip() for item in source_labels if str(item or "").strip()}),
        ("topics", topic_tier, {str(item or "").strip() for item in topic_labels if str(item or "").strip()}),
        ("worknets", worknet_tier, {str(item or "").strip() for item in worknet_labels if str(item or "").strip()}),
        ("review", review_tier, {str(item or "").strip() for item in (review_labels or []) if str(item or "").strip()}),
        ("references", reference_tier, {str(item or "").strip() for item in reference_labels if str(item or "").strip()}),
    ]
    group_labels = dict(RESEARCH_HIGHLIGHT_GROUP_LABELS)
    if isinstance(group_label_overrides, dict):
        group_labels.update(
            {
                str(key).strip(): str(value).strip()
                for key, value in group_label_overrides.items()
                if str(key).strip() and str(value).strip()
            }
        )
    group_ranks = dict(RESEARCH_HIGHLIGHT_GROUP_RANKS)
    if isinstance(group_rank_overrides, dict):
        group_ranks.update(
            {
                str(key).strip(): int(value)
                for key, value in group_rank_overrides.items()
                if str(key).strip() and isinstance(value, int)
            }
        )
    tier_labels = dict(RESEARCH_HIGHLIGHT_TIER_LABELS)
    if isinstance(tier_label_overrides, dict):
        tier_labels.update(
            {
                str(key).strip(): str(value).strip()
                for key, value in tier_label_overrides.items()
                if str(key).strip() and str(value).strip()
            }
        )
    annotated: list[dict[str, Any]] = []
    for item in user_action_details if isinstance(user_action_details, list) else []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            annotated.append(dict(item))
            continue
        normalized = dict(item)
        for group_key, tier, labels in normalized_buckets:
            if label not in labels:
                continue
            normalized["researchGroupKey"] = group_key
            normalized["researchGroupLabel"] = group_labels.get(group_key, group_key)
            normalized["researchGroupRank"] = group_ranks.get(group_key)
            normalized["researchTier"] = tier
            normalized["researchTierLabel"] = tier_labels.get(tier, tier)
            normalized["researchTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
            normalized["actionGroupKey"] = group_key
            normalized["actionGroupLabel"] = group_labels.get(group_key, group_key)
            normalized["actionGroupRank"] = group_ranks.get(group_key)
            normalized["actionTier"] = tier
            normalized["actionTierLabel"] = tier_labels.get(tier, tier)
            normalized["actionTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
            break
        annotated.append(normalized)
    return annotated


def research_action_group_payload(
    user_action_details: list[dict[str, Any]],
    *,
    key: str,
    label: str,
    summary: str,
    labels: list[Any],
) -> Optional[dict[str, Any]]:
    wanted = {str(item or "").strip() for item in labels if str(item or "").strip()}
    if not wanted:
        return None
    items = [
        dict(item)
        for item in user_action_details
        if isinstance(item, dict) and str(item.get("label") or "").strip() in wanted
    ]
    if not items:
        return None
    return {
        "key": key,
        "label": label,
        "summary": summary,
        "count": len(items),
        "actions": items,
    }


def build_research_action_groups(
    user_action_details: list[dict[str, Any]],
    *,
    current_labels: list[Any],
    control_labels: list[Any],
    source_labels: list[Any],
    topic_labels: list[Any],
    worknet_labels: list[Any],
    reference_labels: list[Any],
    control_first: bool = True,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    ordered_group_specs = (
        research_action_group_payload(
            user_action_details,
            key="current",
            label="Current",
            summary="Primary actions for the current context.",
            labels=current_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="control",
            label="Controls",
            summary="Refresh, review, and control actions.",
            labels=control_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="sources",
            label="Sources",
            summary="Source review and refresh actions.",
            labels=source_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="topics",
            label="Topics",
            summary="Protocol, RootNet, and WorkNet knowledge topics.",
            labels=topic_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="worknets",
            label="WorkNets",
            summary="WorkNet selection, playbook, and capability actions.",
            labels=worknet_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="references",
            label="References",
            summary="Reference highlights and evidence links.",
            labels=reference_labels,
        ),
    )
    if control_first:
        ordered_payloads = ordered_group_specs
    else:
        ordered_payloads = (
            ordered_group_specs[0],
            ordered_group_specs[2],
            ordered_group_specs[3],
            ordered_group_specs[4],
            ordered_group_specs[1],
            ordered_group_specs[5],
        )
    for payload in ordered_payloads:
        if isinstance(payload, dict):
            groups.append(payload)
    return groups


def execution_action_label_buckets(
    actions: list[dict[str, Any]],
) -> dict[str, list[str]]:
    buckets = {
        "current": [],
        "control": [],
        "sources": [],
        "topics": [],
        "worknets": [],
        "background": [],
        "review": [],
        "confirmations": [],
        "references": [],
    }
    for item in actions if isinstance(actions, list) else []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        command = str(item.get("command") or "").strip()
        execution_policy = str(item.get("executionPolicy") or "").strip().lower()
        status = str(item.get("status") or "").strip().lower()
        requires_confirmation = bool(item.get("requiresConfirmation"))
        if not label:
            continue
        lowered_label = label.lower()
        if (
            lowered_label.startswith("confirm ")
            or requires_confirmation
            or execution_policy == "confirmation"
            or status in {"queued_for_confirmation", "awaiting_confirmation"}
        ):
            buckets["confirmations"].append(label)
        elif execution_policy == "manual-control" or lowered_label.startswith(("pause ", "stop ", "force ", "retry ")):
            buckets["control"].append(label)
        elif lowered_label.startswith(("inspect ", "stop ", "restart ")) and ("background" in lowered_label or "--background-label" in command or "--stop-background-label" in command):
            buckets["background"].append(label)
        elif "review-epoch.py" in command or lowered_label.startswith(("review latest epoch", "review pending confirmation")):
            buckets["review"].append(label)
        elif lowered_label.startswith(("review source", "refresh source")):
            buckets["sources"].append(label)
        elif lowered_label.startswith(("review reference", "open reference")):
            buckets["references"].append(label)
        elif lowered_label.startswith(("review topic", "refresh topic", "research topic")):
            buckets["topics"].append(label)
        elif (
            lowered_label.startswith(("review worknet", "start ", "build "))
            or "playbook" in label.lower()
        ):
            buckets["worknets"].append(label)
        else:
            buckets["current"].append(label)
    return buckets


def annotate_execution_actions(
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    buckets = execution_action_label_buckets(actions)
    return annotate_research_action_details(
        actions,
        current_labels=buckets["current"],
        control_labels=buckets["control"],
        source_labels=buckets["sources"],
        topic_labels=buckets["topics"],
        worknet_labels=buckets["worknets"],
        reference_labels=buckets["references"],
        background_labels=buckets["background"],
        review_labels=buckets["review"],
        confirmation_labels=buckets["confirmations"],
        group_label_overrides=EXECUTION_ACTION_GROUP_LABEL_OVERRIDES,
        control_tier="overview",
        source_tier="related",
        topic_tier="related",
        worknet_tier="related",
        reference_tier="related",
        background_tier="current",
        review_tier="related",
        confirmation_tier="current",
    )


def annotate_recovery_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets = execution_action_label_buckets(actions)
    return annotate_research_action_details(
        actions,
        current_labels=[*buckets["current"], *buckets["confirmations"]],
        control_labels=buckets["control"],
        source_labels=buckets["sources"],
        topic_labels=buckets["topics"],
        worknet_labels=buckets["worknets"],
        reference_labels=buckets["references"],
        background_labels=buckets["background"],
        review_labels=buckets["review"],
        confirmation_labels=[],
        group_label_overrides={
            **EXECUTION_ACTION_GROUP_LABEL_OVERRIDES,
            "current": "Current actions",
            "worknets": "WorkNet actions",
            "review": "Review actions",
        },
        group_rank_overrides={
            "current": 0,
            "worknets": 1,
            "review": 2,
        },
        control_tier="overview",
        source_tier="related",
        topic_tier="related",
        worknet_tier="related",
        reference_tier="related",
        background_tier="current",
        review_tier="related",
    )


def dedupe_action_entries(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        command = str(item.get("command") or "").strip()
        if not label or not command:
            continue
        key = (label, command)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "label": label,
                "description": str(item.get("description") or "Action details pending."),
                "command": command,
            }
        )
    return deduped
