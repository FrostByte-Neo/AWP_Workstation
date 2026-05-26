#!/usr/bin/env python3
"""Shared helpers for the AWP workstation skill."""

from __future__ import annotations

import json
import os
import py_compile
import re
import shutil
import shlex
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any, Optional

from awp_workstation.commands import (
    build_playbook_command,
    knowledge_review_queue_command,
    query_knowledge_command,
    query_source_command,
    render_argv,
    review_epoch_command,
    run_worknet_command,
    scan_worknets_command,
    start_workstation_command,
    workstation_background_command,
    workstation_confirmation_command,
    workstation_follow_up_command,
    workstation_pause_command,
    workstation_preferences_command,
    workstation_preflight_command,
    workstation_status_command,
)
from awp_workstation.action_priority import prioritize_action_entries
from awp_workstation.action_text import (
    action_details_from_decision,
    action_details_from_ui_actions,
    append_unique_action_detail,
    humanize_public_action_description,
    humanize_public_action_entries,
    humanize_public_action_label,
    humanize_public_recovery_decision,
    humanize_review_action_description,
    humanize_review_action_label,
    humanize_review_confirmation_label,
    prioritize_review_actions,
    prioritize_ui_actions,
    review_action_command,
    runtime_follow_up_description,
)
from awp_workstation.audit import (
    build_branch_contract_audit_payload,
    build_display_contract_audit_payload,
    build_coverage_audit_payload,
    build_public_contract_audit_payload,
    build_query_contract_audit_payload,
    contract_audit_item,
    contract_audit_result,
    first_dict_item,
    first_non_runtime_evidence_item,
)
from awp_workstation.background_supervisor import background_supervisor_snapshot
from awp_workstation.background_supervisor import aggregate_background_supervisors
from awp_workstation.action_groups import (
    annotate_execution_actions,
    annotate_recovery_actions,
    annotate_research_action_details,
    append_user_action,
    build_research_action_groups,
    dedupe_action_entries,
    find_user_action_label,
    frontload_user_action_labels,
    maybe_promote_recovery_decision,
    merge_payload_user_action_details,
    merge_payload_user_actions,
    merge_recovery_decision_actions,
)
from awp_workstation.action_normalization import (
    annotate_raw_confirmation_queue,
    annotate_raw_follow_up_actions,
    choose_default_background_process,
    choose_default_confirmation,
    choose_default_follow_up_action,
    confirmation_item_incomplete_fields,
    copy_confirmation_security_fields,
    normalized_confirmation_queue,
    normalized_follow_up_actions,
)
from awp_workstation.capability_scan import (
    build_capability_bundle_payload,
    capability_reports_by_worknet_key_payload,
    enrich_reports_with_cached_live_worknets_payload,
    enrich_reports_with_rpc_payload,
    fallback_capability_reports_payload,
    load_cached_capability_bundle_payload,
    load_cached_live_worknets_payload,
    resolve_live_worknet_id_payload,
    sync_live_worknets_payload,
)
from awp_workstation.capability_helpers import (
    awp_wallet_snapshot,
    capability_knowledge_caveat,
    derive_capability_execution_state,
    humanize_skill_inspection_status,
    infer_runnable,
    inspection_status_blocks_runtime,
    inspection_status_enables_runtime,
    knowledge_topic_execution_state,
)
from awp_workstation.contracts import (
    BACKGROUND_RECORD_FIELDS,
    BACKGROUND_SUMMARY_FIELDS,
    CAPABILITY_PUBLIC_FIELDS,
    CONFIRMED_ACTION_FIELDS,
    CONFIRMATION_QUEUE_ITEM_FIELDS,
    CONFIRMATION_SECURITY_FIELDS,
    EXECUTED_STEP_FIELDS,
    EXECUTED_STEP_RESULT_DISPLAY_FIELDS,
    EXECUTED_STEP_STDOUT_DISPLAY_FIELDS,
    EXECUTION_ACTION_GROUP_LABEL_OVERRIDES,
    FOLLOW_UP_ACTION_FIELDS,
    PARAMETER_SCHEMA_ITEM_FIELDS,
    PLAYBOOK_COMMAND_PUBLIC_FIELDS,
    PLAYBOOK_PUBLIC_FIELDS,
    PREFLIGHT_PUBLIC_FIELDS,
    PUBLIC_ACTION_FIELDS,
    RECOVERY_DECISION_FIELDS,
    RESEARCH_HIGHLIGHT_GROUP_LABELS,
    RESEARCH_HIGHLIGHT_GROUP_RANKS,
    RESEARCH_HIGHLIGHT_TIER_LABELS,
    RESEARCH_HIGHLIGHT_TIER_RANKS,
    RESUME_RECOVERY_BRIEFING_FIELDS,
    REVIEW_PUBLIC_FIELDS,
    RUN_RESPONSE_BRIEFING_FIELDS,
    RUN_RESPONSE_FIELDS,
    RUNTIME_GUIDANCE_FIELDS,
    RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS,
    RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
    SELECTED_BACKGROUND_ERROR_FIELDS,
    SELECTED_BACKGROUND_PREVIEW_FIELDS,
    SELECTED_CONFIRMATION_FIELDS,
    START_RESPONSE_FIELDS,
    STEP_GROUP_LABELS,
    USER_ACTION_DETAIL_FIELDS,
    WORKSTATION_PREFERENCES_PUBLIC_FIELDS,
    WORKSTATION_STATUS_INTERNAL_FIELDS,
    WORKSTATION_STATUS_PUBLIC_FIELDS,
    normalize_background_summary_payload,
    normalize_executed_step_result_display_payload,
    normalize_executed_step_stdout_display_payload,
    normalize_parameter_schema_item_payload,
    normalize_runtime_guidance_contract_payload,
    normalize_runtime_guidance_user_action_detail_payload,
    project_fields,
)
from awp_workstation.execution_states import (
    align_run_execution_user_message,
    derive_playbook_execution_state,
    derive_execution_state,
    derive_runtime_execution_state,
    execution_state_display,
    execution_state_payload,
    recovery_status_display,
    review_status_display,
)
from awp_workstation.i18n import sanitize_public_payload
from awp_workstation.knowledge_catalog import (
    build_knowledge_catalog_payload,
    build_knowledge_overview_payload,
    build_knowledge_source_directory_payload,
    build_knowledge_topic_index_payload,
    knowledge_topic_recommendations_payload,
)
from awp_workstation.knowledge_contracts import *  # Response-contract constants and projection helpers.
from awp_workstation.knowledge_queries import (
    build_changed_sources_query_result_payload,
    build_concept_query_result_payload,
    build_glossary_query_result_payload,
    build_knowledge_query_result_payload,
    build_source_query_result_payload,
)
from awp_workstation.knowledge_display import (
    humanize_runtime_probe_check_label_payload,
    knowledge_runtime_probe_display_payload,
)
from awp_workstation.knowledge_data import (
    load_derived_evidence_records,
    load_derived_topic_dossiers,
    load_knowledge_coverage_requirements,
    load_knowledge_display_overrides,
    load_knowledge_source_labels,
    load_official_web_sources,
    load_safety_rules,
)
from awp_workstation.manifest_commands import (
    build_manifest_commands,
    official_remote_manifest,
    planned_skill_root,
    rewrite_command_for_skill_root,
)
from awp_workstation.monitor import (
    build_workstation_monitor_payload,
    record_workstation_monitor_delivery_payload,
)
from awp_workstation.messaging import (
    append_runtime_maturity_note,
    build_preflight_plain_language_summary,
    prepend_canonical_worknet_plain,
)
from awp_workstation.narratives import (
    canonical_topic_narrative,
    canonical_worknet_caution_text,
    canonical_worknet_loop_text,
    canonical_worknet_plain_text,
    canonical_worknet_scan_reason,
    canonical_worknet_switch_summary_text,
)
from awp_workstation.notification_adapters import (
    build_notification_delivery_payload,
    dispatch_monitor_notification_payload,
)
from awp_workstation.parameters import (
    build_confirmation_execute_command,
    extract_command_parameter_schema,
    parse_input_assignments,
    resolve_parameterized_argv,
)
from awp_workstation.playbook import build_work_playbook_payload
from awp_workstation.playbook_commands import annotate_playbook_commands, dedupe_playbook_commands
from awp_workstation.playbook_text import (
    humanize_playbook_confirmation_item,
    humanize_playbook_failure_mode,
    humanize_playbook_goal,
    humanize_playbook_loop,
    humanize_playbook_role,
    humanize_playbook_success_metric,
)
from awp_workstation.preflight import (
    build_preflight_report_payload,
    build_registration_plan_payload,
    runtime_probe_payload,
)
from awp_workstation.preferences import ensure_user_preferences, load_user_preferences, update_user_preferences
from awp_workstation.processes import (
    active_processes_path,
    find_active_process,
    launch_background_command,
    load_active_processes,
    process_is_alive,
    persist_background_observation,
    record_command_argv,
    register_active_process,
    remove_active_process,
    stop_background_process,
    summarize_background_log,
    tail_text,
)
from awp_workstation.public_views import (
    humanize_playbook_command_description,
    humanize_playbook_command_label,
    humanize_public_capability_report,
    humanize_public_playbook_commands,
    public_capability_view,
    public_playbook_view,
    public_preflight_view,
    public_review_view,
    public_workstation_preferences_view,
    public_workstation_status_view,
)
from awp_workstation.runner import (
    build_run_response_briefing_payload,
    execute_confirmation_action_payload,
    execute_follow_up_action_payload,
    run_workstation_payload,
)
from awp_workstation.runtime import (
    command_exists,
    command_help_probe,
    parse_json_loose,
    run_command,
    trim_output,
)
from awp_workstation.runtime_actions import (
    find_executed_step,
)
from awp_workstation.runtime_guidance import synthesize_run_guidance as synthesize_runtime_guidance
from awp_workstation.runtime_probe_contracts import *  # Runtime probe response-contract helpers.
from awp_workstation.runtime_probe_helpers import (
    command_probe_available,
    contains_non_ascii_text,
    humanize_capability_reason_part,
    probe_failures_are_expected_state,
    probe_failures_are_network_only,
    run_inspection_probe,
    runtime_probe_blockers,
    should_replace_display_text,
)
from awp_workstation.rpc import DEFAULT_RPC_URL, rpc_call, rpc_result_body, rpc_try_many
from awp_workstation.runtime_payloads import (
    annotate_executed_step_payload,
    annotate_probe_result_display_payload,
    build_executed_step_result_display_payload,
    build_executed_step_stdout_display_payload,
    executed_step_result_payload,
    runtime_action_map,
    runtime_guidance_worknet_key,
    runtime_guidance_worknet_name,
    runtime_message,
    runtime_next_command,
    runtime_payload_error_summary,
    runtime_payload_has_blocker,
    runtime_payload_worknet_key,
    step_result_payload,
)
from awp_workstation.reference_exports import write_reference_export
from awp_workstation.recovery import (
    build_recovery_decision,
    build_recovery_state_payload,
    build_resume_recovery_briefing,
    humanize_recovery_stale_reason,
    humanize_runtime_guidance_message,
    recovery_decision_actions_from_run_response,
    recovery_decision_actions_from_recovery,
    recovery_decision_actions_from_ui,
)
from awp_workstation.reporting import (
    build_daily_summary,
    build_reporter_note,
    knowledge_source_labels_text,
    reporter_reference_note,
    reporter_source_note,
)
from awp_workstation.review import (
    background_strategy_change_from_summary,
    build_epoch_review_from_run_payload,
    build_review_headline,
    humanize_phase_value,
    humanize_review_failure,
    humanize_review_status_token,
    humanize_review_step,
    humanize_review_step_label,
    review_all_steps_prepared,
    review_background_action_label,
    review_line_detail,
    review_runtime_safety_hint,
    review_status_code,
    strategy_changes_from_guidance,
    summarize_worknet_review,
)
from awp_workstation.skill_inventory import (
    OFFICIAL_SKILL_ALLOWLIST_PREFIXES,
    build_skill_inspect_command_payload,
    build_skill_inspection_catalog_payload,
    build_skill_sync_command_payload,
    inspect_skill_runtime_payload,
    load_cached_skill_inspection_catalog_payload,
    looks_official_skill_uri,
    resolve_skill_root,
    skill_registry_from_inventory,
)
from awp_workstation.source_drift import build_source_drift_report, load_cached_source_drift
from awp_workstation.source_inventory import build_source_inventory
from awp_workstation.source_review import (
    build_concept_catalog,
    build_glossary_catalog,
    build_knowledge_review_queue,
    build_source_drift_impact_report,
    build_source_evidence_catalog,
    build_source_fact_catalog,
    build_topic_dossier_catalog,
    build_topic_freshness_catalog,
    load_cached_knowledge_review_queue,
    load_cached_source_impact,
    load_cached_topic_freshness,
    refresh_official_sources,
)
from awp_workstation.state import (
    REFERENCE_EXPORT_ROOT,
    SKILL_ROOT,
    seed_verification_state_from_reference_exports,
    state_context,
)
from awp_workstation.start_response import build_start_response_from_preflight_payload
from awp_workstation.storage import append_jsonl, atomic_write_json, load_json
from awp_workstation.status_views import (
    workstation_actions_only_view,
    workstation_monitor_view,
    workstation_status_brief_view,
    workstation_timeline_view,
)
from awp_workstation.text import (
    compact_preview_text,
    join_product_sentences,
    join_sentences,
    preview_candidate_fragments,
    strip_sentence_end,
)
from awp_workstation.utils import (
    hours_since_iso,
    normalize_knowledge_source_token,
    normalize_worknet_id,
    normalize_worknet_token,
    now_iso,
    parse_iso_datetime,
    print_json,
    repository_file_is_metadata,
    repository_files,
    repository_is_effectively_empty,
    safe_slug,
)
from awp_workstation.timeline import (
    append_timeline_event_payload,
    build_timeline_view_payload,
    timeline_event_from_monitor_payload,
    timeline_event_from_review_payload,
    timeline_event_from_run_payload,
)
from awp_workstation.workstation_status import build_workstation_status_payload
from awp_workstation.workstation_state import (
    build_workstation_state_summary_payload,
    load_cached_workstation_state_summary_payload,
    persist_workstation_state_summary_payload,
)
from awp_workstation.worknets import (
    detect_worknet_from_text,
    load_worknet_profiles,
    recommend_worknet_actions_payload,
    resolve_worknet,
)


KNOWLEDGE_CATALOG_SCHEMA_VERSION = 19
COMMAND_HINT_RE = re.compile(
    r"(python3\s+scripts/[A-Za-z0-9._/\-]+(?:\s+--?[A-Za-z0-9._/\-<>$]+(?:\s+[A-Za-z0-9._/\-<>:$]+)?)*)"
)
MINE_SESSION_RE = re.compile(r"\bsession:\s*([A-Za-z0-9_.:-]+)")

SAFETY_RULES: list[dict[str, Any]] = load_safety_rules()

OFFICIAL_WEB_SOURCES: list[dict[str, Any]] = load_official_web_sources()

DERIVED_TOPIC_DOSSIERS: list[dict[str, Any]] = load_derived_topic_dossiers()

KNOWLEDGE_COVERAGE_REQUIREMENTS: list[dict[str, Any]] = load_knowledge_coverage_requirements()

KNOWN_WORKNETS: list[dict[str, Any]] = load_worknet_profiles()

HUMANIZED_KNOWLEDGE_SOURCE_LABELS: dict[str, str] = load_knowledge_source_labels()

def worknet_runtime_maturity_note(
    *,
    worknet_key: Optional[str],
    capability_report: Optional[dict[str, Any]] = None,
    worknet_id: Any = None,
    source_keys: Any = None,
    install_uri: Any = None,
) -> Optional[str]:
    metadata = knowledge_worknet_metadata(
        worknet_key=worknet_key,
        worknet_id=worknet_id,
        source_keys=source_keys,
        install_uri=install_uri,
        capability_report=capability_report,
    )
    if not isinstance(metadata, dict):
        return None
    runtime_spec_state_display = str(metadata.get("runtimeSpecStateDisplay") or "").strip()
    canonical_worknet_id = str(metadata.get("canonicalWorknetId") or "").strip()
    min_stake_hint_display = str(metadata.get("minStakeHintDisplay") or "").strip()
    parts: list[str] = []
    if runtime_spec_state_display:
        parts.append(f"runtime spec maturity is {runtime_spec_state_display}")
    if canonical_worknet_id:
        parts.append(f"canonical ID is {canonical_worknet_id}")
    if min_stake_hint_display:
        parts.append(f"live minStake hint is {min_stake_hint_display}")
    if not parts:
        return None
    return "Note: " + ", ".join(parts) + "."


def humanize_runtime_guidance_message_display(
    worknet_key: Optional[str],
    message: Any,
    *,
    state: Any = None,
) -> Optional[str]:
    text = str(message or "").strip()
    resolved_worknet = runtime_guidance_worknet_name(worknet_key)
    state_text = str(state or "").strip().lower()
    lowered = text.lower()
    if lowered.startswith("wallet ready:"):
        address = text.split(":", 1)[1].strip() if ":" in text else ""
        if address:
            return f"{resolved_worknet} wallet is ready: {address}."
        return f"{resolved_worknet} wallet is ready."
    if worknet_key == "predict" and lowered.startswith("agent status:"):
        match = re.search(
            r"agent status:\s*(\d+)\s+total predictions,\s*([0-9.]+)\s+chips balance,\s*persona:\s*([a-z0-9_-]+)",
            lowered,
        )
        if match:
            total_predictions, balance, persona = match.groups()
            return f"Predict runtime status synced: {total_predictions} total predictions, {balance} chips balance, persona {persona}."
        return "Predict runtime status synced."
    if worknet_key == "predict" and "failed to fetch status" in lowered and "coordinator" in lowered:
        return "Predict cannot reach the coordinator right now; check coordinator connectivity."
    if worknet_key == "predict" and "failed to fetch stake status" in lowered:
        return "Predict is blocked on eligibility because the stake result is not stable yet."
    if worknet_key == "gov" and "name or service not known" in lowered:
        return "Gov cannot reach the upstream service right now; check network or DNS."
    if worknet_key == "gov" and ("principal has no awp power this epoch" in lowered or "state_principal_not_in_epoch" in lowered):
        return "This principal has no AWP Power for the current period, so Gov signed reads and writes cannot continue."
    if worknet_key == "ardi" and "all base rpcs failed" in lowered:
        return "Ardi cannot reach the Base RPC right now; check the network or RPC endpoint."
    if worknet_key == "mine":
        if state_text == "ready" or "mining environment is ready" in lowered:
            return "Mine runtime is ready and can start collection."
        if state_text == "idle" or "no active mining session" in lowered:
            return "Mine has no active collection session; start a new round to produce work."
        if state_text == "auth_required" or "wallet session expired" in lowered:
            return "Mine wallet session expired; reinitialize the runtime first."
    if state_text == "auth_required" and resolved_worknet != "Current":
        return f"{resolved_worknet} wallet session expired; reinitialize the runtime first."
    if state_text == "selection_required" and resolved_worknet != "Current":
        return f"{resolved_worknet} is waiting for the next operator selection."
    if state_text == "waiting_for_market" and resolved_worknet != "Current":
        return f"{resolved_worknet} has no suitable target right now; wait for the next round."
    return compact_preview_text(text, max_chars=160, max_sentences=2) if text else None


def humanize_runtime_next_command_display(
    worknet_key: Optional[str],
    next_command: Any,
) -> Optional[str]:
    rendered = None
    if isinstance(next_command, list) and next_command:
        rendered = render_argv([str(part) for part in next_command])
    else:
        rendered = str(next_command or "").strip() or None
    if not rendered:
        return None
    humanized = humanize_runtime_probe_check_label(
        "",
        command=rendered,
        skill_key=worknet_key,
    )
    return humanized or rendered


def humanize_runtime_guidance_action_label(
    worknet_key: Optional[str],
    label: Any,
    *,
    command: Any = None,
) -> str:
    text = str(label or "").strip()
    if not text:
        return text
    mapped = humanize_playbook_command_label(text)
    if mapped != text:
        return mapped
    command_text = str(command or "").strip().lower()
    resolved_worknet = runtime_guidance_worknet_key(
        worknet_key,
        labels=[text],
        action_map={"_": command_text} if command_text else None,
    )
    worknet_name = runtime_guidance_worknet_name(resolved_worknet)
    lowered = text.lower()
    if resolved_worknet == "mine":
        if lowered == "start mining" or "agent-start" in command_text:
            return "Start Mine collection"
        if lowered == "check status":
            if "agent-control status" in command_text:
                return "View Mine control status"
            return "View Mine runtime status"
        if lowered == "re-initialize" or "bootstrap.sh" in command_text:
            return "Reinitialize Mine runtime"
        if lowered == "run diagnostics" or "run_tool.py doctor" in command_text:
            return "Run Mine diagnostics"
    if lowered in {"re-initialize", "reinitialize"}:
        return f"Reinitialize {worknet_name} runtime" if worknet_name != "Current" else "Reinitialize runtime"
    if lowered == "run diagnostics":
        return f"Run {worknet_name} diagnostics" if worknet_name != "Current" else "Run diagnostics"
    if lowered in {"check status", "status"}:
        return f"View {worknet_name} status" if worknet_name != "Current" else "View status"
    return humanize_public_action_label(text)


def humanize_runtime_guidance_action_description(
    worknet_key: Optional[str],
    label: Any,
    *,
    command: Any = None,
    message: Any = None,
    state: Any = None,
) -> str:
    text = str(label or "").strip()
    if not text:
        return "Continue the recommended action."
    command_text = str(command or "").strip().lower()
    lowered = text.lower()
    resolved_worknet = runtime_guidance_worknet_key(
        worknet_key,
        labels=[text],
        action_map={"_": command_text} if command_text else None,
        message=message,
    )
    if resolved_worknet == "mine":
        if lowered == "start mining" or "agent-start" in command_text:
            return "Start a new Mine collection round so the worker enters the earning loop."
        if lowered == "check status":
            return "Check Mine status again to confirm whether it can continue."
        if lowered == "re-initialize" or "bootstrap.sh" in command_text:
            return "Reinitialize the local Mine runtime and wallet session, then continue."
        if lowered == "run diagnostics" or "run_tool.py doctor" in command_text:
            return "Run Mine diagnostics to identify wallet-session, dependency, or path issues."
    if lowered in {"re-initialize", "reinitialize"}:
        return "Reinitialize the current runtime and session."
    if lowered == "run diagnostics":
        return "Run diagnostics to identify whether the blocker is environment, dependency, or permission related."
    if lowered in {"check status", "status"}:
        return "Check the current status again to confirm whether execution can continue."
    display_message = humanize_runtime_guidance_message_display(resolved_worknet, message, state=state)
    if display_message:
        return display_message
    return humanize_public_action_description(text, str(message or "Continue this recommended action.").strip() or "Continue this recommended action.")


def runtime_guidance_preview_display(guidance: Any) -> Optional[str]:
    if not isinstance(guidance, dict):
        return None
    message = str(guidance.get("messageDisplay") or guidance.get("message") or "").strip()
    actions = [
        str(item).strip()
        for item in guidance.get("userActionsDisplay", [])
        if isinstance(item, str) and str(item).strip()
    ] if isinstance(guidance.get("userActionsDisplay"), list) else []
    if not actions:
        actions = [
            str(item.get("displayLabel") or item.get("label") or "").strip()
            for item in guidance.get("userActionDetails", [])
            if isinstance(item, dict) and str(item.get("displayLabel") or item.get("label") or "").strip()
        ] if isinstance(guidance.get("userActionDetails"), list) else []
    if message and actions:
        action_text = f"Next suggested action: {actions[0]}."
        return compact_preview_text(
            join_product_sentences([message, action_text]),
            max_chars=180,
            max_sentences=2,
        )
    if message:
        return compact_preview_text(message, max_chars=180, max_sentences=2)
    if actions:
        return compact_preview_text(
            f"Next suggested action: {actions[0]}.",
            max_chars=180,
            max_sentences=2,
        )
    next_command_display = str(guidance.get("nextCommandDisplay") or "").strip()
    if next_command_display:
        return compact_preview_text(
            f"Next command: {next_command_display}",
            max_chars=180,
            max_sentences=2,
        )
    return None


def build_raw_user_action_details(
    labels: Any,
    action_map: Any,
    *,
    worknet_key: Optional[str] = None,
    guidance_state: Any = None,
    default_description: Optional[str] = None,
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    if not isinstance(labels, list):
        return details
    resolved_worknet = runtime_guidance_worknet_key(
        worknet_key,
        labels=labels,
        action_map=action_map,
        message=default_description,
    )
    for label in labels:
        if not isinstance(label, str) or not label.strip():
            continue
        text = label.strip()
        command = str(action_map.get(label) or "").strip() if isinstance(action_map, dict) else ""
        append_unique_action_detail(
            details,
            label=text,
            display_label=humanize_runtime_guidance_action_label(
                resolved_worknet,
                text,
                command=command,
            ),
            description=humanize_runtime_guidance_action_description(
                resolved_worknet,
                text,
                command=command,
                message=default_description,
                state=guidance_state,
            ),
            command=command or None,
        )
    return details


def annotate_runtime_user_action_details(
    details: Any,
    *,
    worknet_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    if not isinstance(details, list):
        return []
    annotated: list[dict[str, Any]] = []
    for item in details:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        raw_label = str(normalized.get("label") or "").strip()
        raw_command = str(normalized.get("command") or "").strip()
        display_label = str(normalized.get("displayLabel") or raw_label).strip() or raw_label
        description_display = str(normalized.get("description") or "").strip()
        if raw_label:
            normalized["labelRaw"] = raw_label
        if display_label:
            normalized["displayLabel"] = display_label
        if description_display:
            normalized["descriptionDisplay"] = description_display
        if raw_command:
            normalized["commandRaw"] = raw_command
            normalized["commandDisplay"] = humanize_runtime_probe_check_label(
                "",
                command=raw_command,
                skill_key=worknet_key,
            ) or display_label or raw_command
        annotated.append(normalize_runtime_guidance_user_action_detail_payload(normalized))
    return annotated


def annotate_runtime_guidance_payload(
    guidance: Any,
    *,
    worknet_key: Optional[str] = None,
) -> Any:
    if not isinstance(guidance, dict):
        return guidance
    normalized = dict(guidance)
    resolved_worknet = runtime_guidance_worknet_key(
        worknet_key,
        labels=normalized.get("userActions"),
        action_map=normalized.get("actionMap"),
        message=normalized.get("message"),
    )
    message_display = humanize_runtime_guidance_message_display(
        resolved_worknet,
        normalized.get("message"),
        state=normalized.get("state"),
    )
    raw_message = str(normalized.get("message") or "").strip()
    if message_display:
        if raw_message and raw_message != message_display:
            normalized["messageRaw"] = raw_message
        normalized["message"] = message_display
        normalized["messageDisplay"] = message_display
    next_command = normalized.get("nextCommand")
    next_command_raw = None
    if isinstance(next_command, list) and next_command:
        next_command_raw = render_argv([str(part) for part in next_command])
        normalized["nextCommandRaw"] = next_command_raw
        normalized["nextCommandDisplay"] = humanize_runtime_next_command_display(
            resolved_worknet or None,
            next_command,
        ) or next_command_raw
    elif isinstance(next_command, str) and next_command.strip():
        next_command_raw = next_command.strip()
        normalized["nextCommandRaw"] = next_command_raw
        normalized["nextCommandDisplay"] = humanize_runtime_next_command_display(
            resolved_worknet or None,
            next_command,
        ) or next_command_raw
    raw_user_actions = [
        str(item).strip()
        for item in normalized.get("userActions", [])
        if isinstance(item, str) and str(item).strip()
    ] if isinstance(normalized.get("userActions"), list) else []
    if raw_user_actions:
        normalized["userActionsRaw"] = raw_user_actions
    user_action_details = build_raw_user_action_details(
        normalized.get("userActions"),
        normalized.get("actionMap"),
        worknet_key=resolved_worknet or None,
        guidance_state=normalized.get("state"),
        default_description=message_display or str(normalized.get("message") or "Review this runtime action.").strip() or None,
    )
    if user_action_details:
        user_action_details = annotate_execution_actions(user_action_details)
        user_action_details = annotate_runtime_user_action_details(
            user_action_details,
            worknet_key=resolved_worknet or None,
        )
    normalized["userActionDetails"] = user_action_details
    if isinstance(normalized.get("userActions"), list):
        normalized["userActionsDisplay"] = [
            humanize_runtime_guidance_action_label(
                resolved_worknet,
                item,
                command=normalized.get("actionMap", {}).get(item) if isinstance(normalized.get("actionMap"), dict) and isinstance(item, str) else None,
            )
            for item in normalized.get("userActions", [])
            if isinstance(item, str) and item.strip()
        ]
    display_preview = runtime_guidance_preview_display(normalized)
    if display_preview:
        normalized["preview"] = display_preview
        normalized["previewDisplay"] = display_preview
    raw_preview = None
    if raw_message or raw_user_actions or next_command_raw:
        raw_preview = runtime_guidance_preview_display(
            {
                "message": raw_message or None,
                "userActionsDisplay": raw_user_actions,
                "nextCommandDisplay": next_command_raw,
                "userActionDetails": [
                    {"label": item}
                    for item in raw_user_actions
                ],
            }
        )
    if raw_preview:
        normalized["previewRaw"] = raw_preview
    return normalize_runtime_guidance_contract_payload(normalized)


def annotate_runtime_action_payloads(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    worknet_key = runtime_payload_worknet_key(normalized)
    normalized["runtimeGuidance"] = annotate_runtime_guidance_payload(
        normalized.get("runtimeGuidance"),
        worknet_key=worknet_key or None,
    )
    normalized["followUpActions"] = annotate_raw_follow_up_actions(normalized.get("followUpActions"))
    normalized["confirmationQueue"] = annotate_raw_confirmation_queue(normalized.get("confirmationQueue"))
    normalized["executedSteps"] = annotate_executed_steps(
        normalized.get("executedSteps"),
        worknet_key=worknet_key or None,
    )
    if isinstance(normalized.get("activeBackgroundProcesses"), list):
        normalized["activeBackgroundProcesses"] = [
            annotate_background_record(item)
            for item in normalized.get("activeBackgroundProcesses", [])
            if isinstance(item, dict)
        ]
    if isinstance(normalized.get("selectedBackground"), dict):
        normalized["selectedBackground"] = annotate_background_record(normalized.get("selectedBackground"))
    if isinstance(normalized.get("selectedConfirmation"), dict):
        normalized["selectedConfirmation"] = annotate_selected_confirmation(normalized.get("selectedConfirmation"))
    if isinstance(normalized.get("sourceFollowUpAction"), dict):
        follow_up = annotate_raw_follow_up_actions([normalized.get("sourceFollowUpAction")])
        normalized["sourceFollowUpAction"] = follow_up[0] if follow_up else normalized.get("sourceFollowUpAction")
    if isinstance(normalized.get("confirmedAction"), dict):
        confirmed = annotate_raw_confirmation_queue([normalized.get("confirmedAction")])
        normalized["confirmedAction"] = confirmed[0] if confirmed else normalized.get("confirmedAction")
    return normalized


def annotate_parameter_schema_items(items: Any) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        prompt = str(item.get("prompt") or "").strip()
        placeholder = str(item.get("placeholder") or "").strip()
        display_name = name.replace("_", " ").strip() if name else None
        rendered.append(
            normalize_parameter_schema_item_payload({
                **item,
                "displayName": display_name,
                "promptDisplay": prompt or display_name,
                "placeholderDisplay": placeholder or None,
            })
        )
    return rendered


def annotate_background_record(record: Any) -> Any:
    if not isinstance(record, dict):
        return record
    normalized = dict(record)
    label = str(normalized.get("label") or "").strip()
    if label:
        normalized["displayLabel"] = humanize_public_action_label(label)
    normalized["actionGroupKey"] = "background"
    normalized["actionGroupLabel"] = EXECUTION_ACTION_GROUP_LABEL_OVERRIDES.get("background")
    normalized["actionGroupRank"] = RESEARCH_HIGHLIGHT_GROUP_RANKS.get("background")
    normalized["actionTier"] = "current"
    normalized["actionTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get("current")
    normalized["actionTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get("current")
    summary = normalized.get("summary")
    if isinstance(summary, dict):
        normalized["summaryDisplay"] = normalize_background_summary_payload(summary)
    return normalized


def annotate_selected_confirmation(selection: Any) -> Any:
    if not isinstance(selection, dict):
        return selection
    normalized = dict(selection)
    copy_confirmation_security_fields(normalized, selection)
    label = str(normalized.get("label") or "").strip()
    if label:
        normalized["displayLabel"] = humanize_public_action_label(label)
    normalized["actionGroupKey"] = "confirmations"
    normalized["actionGroupLabel"] = EXECUTION_ACTION_GROUP_LABEL_OVERRIDES.get("confirmations")
    normalized["actionGroupRank"] = RESEARCH_HIGHLIGHT_GROUP_RANKS.get("confirmations")
    normalized["actionTier"] = "current"
    normalized["actionTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get("current")
    normalized["actionTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get("current")
    if isinstance(normalized.get("requiredInputs"), list):
        normalized["requiredInputsDisplay"] = annotate_parameter_schema_items(normalized.get("requiredInputs"))
    incomplete_fields = confirmation_item_incomplete_fields(normalized)
    if incomplete_fields:
        normalized["incompleteFields"] = incomplete_fields
    return normalized


def executed_step_parameter_display_name(step: dict[str, Any], name: str) -> str:
    target = str(name or "").strip()
    if not target:
        return "parameter"
    for spec in step.get("parameterSchema", []) if isinstance(step.get("parameterSchema"), list) else []:
        if not isinstance(spec, dict):
            continue
        spec_name = str(spec.get("name") or "").strip()
        if spec_name != target:
            continue
        prompt = str(spec.get("prompt") or "").strip()
        placeholder = str(spec.get("placeholder") or "").strip()
        if prompt:
            return prompt
        if placeholder:
            return placeholder
        break
    return target.replace("_", " ").strip() or target


def humanize_parameter_error_message(step: dict[str, Any], error: Any) -> Optional[str]:
    text = str(error or "").strip()
    if not text:
        return None
    if text.startswith("missing input: "):
        name = text[len("missing input: "):].strip()
        return f"Missing required input: {executed_step_parameter_display_name(step, name)}."
    if text.startswith("invalid value for "):
        remainder = text[len("invalid value for "):].strip()
        name, _, value = remainder.partition(":")
        label = executed_step_parameter_display_name(step, name.strip())
        if value.strip():
            return f"Invalid value for {label}: {value.strip()}."
        return f"Invalid value for {label}."
    return text


def humanize_executed_step_reason_text(reason: Any) -> Optional[str]:
    text = str(reason or "").strip()
    if not text:
        return None
    if text == "primary work step already executed; remaining control commands stay manual":
        return "Primary work already ran; remaining control commands stay manual."
    if text.lower().endswith(" failed"):
        failed_label = text[:-len(" failed")].strip()
        display = humanize_executed_step_label(failed_label) or failed_label or "step"
        return f"{display} failed."
    return text


def join_display_sentences(items: list[str]) -> Optional[str]:
    cleaned: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        cleaned.append(text.rstrip(".; "))
    if not cleaned:
        return None
    return ". ".join(cleaned) + "."


def humanize_executed_step_status_display(status: Any) -> Optional[str]:
    code = str(status or "").strip().lower()
    if not code:
        return None
    mapping = {
        "available_manual": "manual action available",
        "planned": "planned",
        "ok": "completed",
        "failed": "failed",
        "queued_for_confirmation": "queued for confirmation",
        "awaiting_confirmation": "awaiting confirmation",
        "missing_runtime_command": "missing runtime command",
        "missing_parameters": "missing parameters",
        "started_background": "started in background",
        "background_running": "running in background",
        "blocked_after_previous_step": "blocked after previous step",
        "skipped_after_primary_work": "skipped after primary work",
    }
    return mapping.get(code, code)


def humanize_runtime_payload_state(state: Any) -> Optional[str]:
    code = str(state or "").strip().lower()
    if not code:
        return None
    mapping = {
        "ready": "ready",
        "idle": "idle",
        "selection_required": "selection required",
        "auth_required": "authentication required",
        "waiting_for_market": "waiting for market",
        "llm_running": "LLM running",
        "llm_error": "LLM error",
        "challenge_ready": "challenge ready",
        "iteration_started": "iteration started",
        "starting": "starting",
        "running": "running",
        "error": "error",
    }
    return mapping.get(code, code.replace("_", " ").strip())


def structured_preview_text(value: Any, *, max_chars: int = 220) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return compact_preview_text(value, max_chars=max_chars, max_sentences=2)
    trimmed = trim_output(value, limit=180, max_items=4, max_keys=12, max_depth=4)
    try:
        text = json.dumps(trimmed, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(trimmed)
    return compact_preview_text(text, max_chars=max_chars, max_sentences=2)


def executed_step_payload_summary_display(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
) -> Optional[str]:
    if not isinstance(payload, dict):
        return structured_preview_text(payload)
    label = str(step.get("label") or "").strip()
    status = str(step.get("status") or "").strip().lower()
    state = str(payload.get("state") or "").strip().lower()
    state_display = humanize_runtime_payload_state(state)
    message = runtime_message(payload)
    message_display = humanize_runtime_guidance_message_display(
        worknet_key or None,
        message,
        state=state,
    )
    if status in {"planned", "ok", "failed"} and runtime_payload_has_blocker(payload):
        return (
            humanize_review_failure(worknet_key, step, payload)
            or runtime_payload_error_summary(payload)
            or message_display
            or state_display
            or message
            or structured_preview_text(payload)
        )
    if state not in {"auth_required", "waiting_for_market", "llm_error", "error"}:
        review_detail = humanize_review_step(worknet_key, step, payload)
        if review_detail:
            return review_detail
    if message_display:
        return message_display
    if state_display and message:
        preview = compact_preview_text(message, max_chars=160, max_sentences=2) or message
        if state_display in preview:
            return preview
        return f"{state_display}: {preview}"
    return state_display or message or structured_preview_text(payload) or humanize_review_status_token(worknet_key, label, status)


def humanize_started_background_detail(step: dict[str, Any]) -> Optional[str]:
    guidance = step.get("runtimeGuidance")
    message = runtime_message(guidance) if isinstance(guidance, dict) else None
    log_path = None
    background = step.get("backgroundProcess")
    if isinstance(background, dict):
        value = background.get("logPath")
        if isinstance(value, str) and value.strip():
            log_path = value.strip()
    detail = message or "Background process started."
    if log_path and log_path not in detail:
        detail = f"{detail} Log: {log_path}."
    return detail


def humanize_executed_step_reason_display(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
) -> Optional[str]:
    status = str(step.get("status") or "").strip().lower()
    reason_display = humanize_executed_step_reason_text(step.get("reason"))
    if reason_display:
        return reason_display
    if status == "missing_parameters" and isinstance(step.get("parameterErrors"), list):
        rendered = [
            item
            for item in (
                humanize_parameter_error_message(step, item)
                for item in step.get("parameterErrors", [])
            )
            if isinstance(item, str) and item.strip()
        ]
        if rendered:
            return join_display_sentences(rendered)
    if status in {"planned", "ok", "failed"} and runtime_payload_has_blocker(payload):
        return (
            humanize_review_failure(worknet_key, step, payload)
            or runtime_payload_error_summary(payload)
            or runtime_message(payload)
        )
    if status == "failed":
        stderr = step.get("result", {}).get("stderr") if isinstance(step.get("result"), dict) else None
        if isinstance(stderr, str) and stderr.strip():
            return stderr.strip().splitlines()[0]
    if status in {"queued_for_confirmation", "awaiting_confirmation", "missing_runtime_command"}:
        label = str(step.get("label") or "").strip()
        return humanize_review_status_token(worknet_key, label, status)
    return None


def humanize_executed_step_detail_display(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
) -> Optional[str]:
    status = str(step.get("status") or "").strip().lower()
    label = str(step.get("label") or "").strip()
    message = runtime_message(payload)
    reason_display = humanize_executed_step_reason_display(worknet_key, step, payload)
    if status == "started_background":
        return humanize_started_background_detail(step)
    if status == "background_running":
        return "Background process is still running."
    if status in {"planned", "ok"} and runtime_payload_has_blocker(payload):
        return reason_display or humanize_review_status_token(worknet_key, label, status)
    if status in {"planned", "ok"}:
        return executed_step_payload_summary_display(worknet_key, step, payload) or humanize_review_status_token(worknet_key, label, status)
    if status in {"available_manual", "skipped_after_primary_work", "blocked_after_previous_step"}:
        return reason_display or humanize_review_status_token(worknet_key, label, status)
    if status in {"queued_for_confirmation", "awaiting_confirmation", "missing_runtime_command", "failed", "missing_parameters"}:
        return reason_display or executed_step_payload_summary_display(worknet_key, step, payload) or humanize_review_status_token(worknet_key, label, status)
    return reason_display or humanize_review_status_token(worknet_key, label, status) or message


def build_executed_step_stdout_display(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
) -> Optional[dict[str, Any]]:
    return build_executed_step_stdout_display_payload(
        worknet_key,
        step,
        payload,
        dependencies={
            "compact_preview_text": compact_preview_text,
            "executed_step_payload_summary_display": executed_step_payload_summary_display,
            "extract_runtime_guidance_from_payload": extract_runtime_guidance_from_payload,
            "humanize_runtime_guidance_message_display": humanize_runtime_guidance_message_display,
            "humanize_runtime_next_command_display": humanize_runtime_next_command_display,
            "humanize_runtime_payload_state": humanize_runtime_payload_state,
            "normalize_executed_step_stdout_display_payload": normalize_executed_step_stdout_display_payload,
            "normalize_runtime_guidance_contract_payload": normalize_runtime_guidance_contract_payload,
            "render_argv": render_argv,
            "runtime_guidance_preview_display": runtime_guidance_preview_display,
            "runtime_message": runtime_message,
            "runtime_payload_error_summary": runtime_payload_error_summary,
            "should_replace_display_text": should_replace_display_text,
            "structured_preview_text": structured_preview_text,
        },
    )


def build_executed_step_result_display(
    worknet_key: str,
    step: dict[str, Any],
) -> Optional[dict[str, Any]]:
    return build_executed_step_result_display_payload(
        worknet_key,
        step,
        dependencies={
            "build_executed_step_stdout_display": build_executed_step_stdout_display,
            "compact_preview_text": compact_preview_text,
            "executed_step_result_payload": executed_step_result_payload,
            "normalize_executed_step_result_display_payload": normalize_executed_step_result_display_payload,
        },
    )


def annotate_executed_step(step: Any, *, worknet_key: Optional[str] = None) -> Any:
    return annotate_executed_step_payload(
        step,
        worknet_key=worknet_key,
        dependencies={
            "RESEARCH_HIGHLIGHT_GROUP_RANKS": RESEARCH_HIGHLIGHT_GROUP_RANKS,
            "RESEARCH_HIGHLIGHT_TIER_LABELS": RESEARCH_HIGHLIGHT_TIER_LABELS,
            "RESEARCH_HIGHLIGHT_TIER_RANKS": RESEARCH_HIGHLIGHT_TIER_RANKS,
            "STEP_GROUP_LABELS": STEP_GROUP_LABELS,
            "annotate_background_record": annotate_background_record,
            "annotate_execution_actions": annotate_execution_actions,
            "annotate_parameter_schema_items": annotate_parameter_schema_items,
            "annotate_runtime_guidance_payload": annotate_runtime_guidance_payload,
            "build_executed_step_result_display": build_executed_step_result_display,
            "executed_step_result_payload": executed_step_result_payload,
            "humanize_executed_step_detail_display": humanize_executed_step_detail_display,
            "humanize_executed_step_label": humanize_executed_step_label,
            "humanize_executed_step_reason_display": humanize_executed_step_reason_display,
            "humanize_executed_step_status_display": humanize_executed_step_status_display,
            "humanize_parameter_error_message": humanize_parameter_error_message,
            "render_argv": render_argv,
        },
    )


def annotate_executed_steps(
    steps: Any,
    *,
    worknet_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    if not isinstance(steps, list):
        return []
    return [
        annotated
        for annotated in (
            annotate_executed_step(step, worknet_key=worknet_key)
            for step in steps
        )
        if isinstance(annotated, dict)
    ]


def extract_runtime_guidance_from_payload(
    payload: Any,
    *,
    worknet_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    message = runtime_message(payload)
    actions = payload.get("user_actions")
    user_actions = [str(item) for item in actions if isinstance(item, str) and str(item).strip()] if isinstance(actions, list) else []
    action_map = runtime_action_map(payload)
    next_command = runtime_next_command(payload)
    next_action = None
    internal = payload.get("_internal")
    if isinstance(internal, dict) and isinstance(internal.get("next_action"), str):
        next_action = str(internal.get("next_action"))
    state = payload.get("state") if isinstance(payload.get("state"), str) else None
    if not any([message, user_actions, action_map, next_command, next_action, state]):
        return None
    return annotate_runtime_guidance_payload({
        "message": message,
        "userActions": user_actions,
        "actionMap": action_map,
        "nextCommand": next_command,
        "nextAction": next_action,
        "state": state,
    }, worknet_key=worknet_key)


def summarize_knowledge_review_queue(queue: Any) -> dict[str, Any]:
    if not isinstance(queue, dict):
        return normalize_knowledge_review_queue_summary({
            "available": False,
            "hasPendingReviews": False,
            "pendingReviewCount": 0,
            "changedSourceCount": 0,
            "topicCount": 0,
            "factCount": 0,
            "evidenceCount": 0,
            "worknetCount": 0,
            "highestPriority": None,
            "focusSources": [],
            "focusTopics": [],
            "headline": "Knowledge review queue is unavailable.",
            "primaryActionLabel": None,
            "primaryActionCommand": None,
            "refreshActionLabel": "Refresh knowledge review queue",
            "refreshActionCommand": knowledge_review_queue_command(refresh=True),
            "generatedAt": None,
            "sourceImpactGeneratedAt": None,
        })

    priority_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    summary = queue.get("summary", {}) if isinstance(queue.get("summary"), dict) else {}
    entries = queue.get("entries", []) if isinstance(queue.get("entries"), list) else []
    source_labels: list[str] = []
    topic_labels: list[str] = []
    highest_priority: Optional[str] = None

    for item in entries:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        priority = str(item.get("priority") or "low")
        if priority_rank.get(priority, 0) > priority_rank.get(str(highest_priority or "low"), 0):
            highest_priority = priority
        if item.get("kind") == "source" and label not in source_labels:
            source_labels.append(label)
        if item.get("kind") == "topic" and label not in topic_labels:
            topic_labels.append(label)

    pending_review_count = int(summary.get("entries", len(entries)) or 0)
    changed_source_count = int(summary.get("sources", len(source_labels)) or 0)
    topic_count = int(summary.get("topics", len(topic_labels)) or 0)
    fact_count = int(summary.get("facts", 0) or 0)
    evidence_count = int(summary.get("evidence", 0) or 0)
    worknet_count = int(summary.get("worknets", 0) or 0)
    focus_sources = source_labels[:3]
    focus_topics = topic_labels[:3]
    focus_sources_display = [humanize_knowledge_source_label(item) for item in focus_sources]
    has_pending_reviews = pending_review_count > 0

    if has_pending_reviews:
        headline = f"{changed_source_count} changed sources require {pending_review_count} knowledge reviews."
        if topic_count:
            headline += f" {topic_count} topics are affected."
        if focus_topics:
            headline += f" Focus topics: {', '.join(focus_topics)}."
    else:
        headline = "No pending knowledge reviews."

    return normalize_knowledge_review_queue_summary({
        "available": True,
        "hasPendingReviews": has_pending_reviews,
        "pendingReviewCount": pending_review_count,
        "changedSourceCount": changed_source_count,
        "topicCount": topic_count,
        "factCount": fact_count,
        "evidenceCount": evidence_count,
        "worknetCount": worknet_count,
        "highestPriority": highest_priority,
        "highestPriorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(str(highest_priority or "").strip()),
        "focusSources": focus_sources,
        "focusSourcesDisplay": focus_sources_display,
        "focusTopics": focus_topics,
        "headline": headline,
        "primaryActionLabel": "Review pending knowledge updates" if has_pending_reviews else None,
        "primaryActionCommand": query_knowledge_command("review-queue") if has_pending_reviews else None,
        "refreshActionLabel": "Refresh knowledge review queue",
        "refreshActionCommand": knowledge_review_queue_command(refresh=True),
        "generatedAt": queue.get("generatedAt"),
        "sourceImpactGeneratedAt": queue.get("sourceImpactGeneratedAt"),
    })


def resolve_workstation_status_intent(query: Optional[str], explicit_intent: Optional[str] = None) -> str:
    if isinstance(explicit_intent, str) and explicit_intent.strip():
        return explicit_intent.strip().lower()
    text = str(query or "").strip().lower()
    if not text:
        return "status"
    if any(token in text for token in ("earn", "earning", "reward", "rewards", "payout", "income", "profit")):
        return "earnings"
    if any(token in text for token in ("why failed", "why fail", "failure", "failed", "error", "blocked", "issue")):
        return "failures"
    if any(token in text for token in ("safety", "safe", "don't move funds", "dont move funds", "non-financial", "risk", "funds")):
        return "safety"
    if any(token in text for token in ("stale", "review queue", "upstream", "source drift", "changed source", "knowledge review")):
        return "review-queue"
    if any(token in text for token in ("what is running", "running now", "status", "what's running")):
        return "status"
    if any(token in text for token in ("guide", "research", "learn", "what is", "source", "docs", "repo", "repository", "explain")):
        return "research"
    if any(token in text for token in ("pause", "stop current", "stop running", "hold", "halt")):
        return "pause"
    if any(token in text for token in ("continue", "resume", "restart", "go on", "keep running")):
        return "continue"
    if any(token in text for token in ("switch", "only run", "select worknet", "change worknet", "run mine", "run predict", "run gov", "run ardi", "run tmr", "run community")):
        return "switch-worknet"
    return "status"


def knowledge_source_records_from_catalog(catalog: Any) -> dict[str, dict[str, Any]]:
    source_records: dict[str, dict[str, Any]] = {}
    sources = catalog.get("sources", {}) if isinstance(catalog, dict) and isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
    if not source_records:
        for item in OFFICIAL_WEB_SOURCES:
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
    return source_records


def source_record_match_candidates(source_record: Any) -> list[str]:
    if not isinstance(source_record, dict):
        return []
    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: Any) -> None:
        text = str(candidate or "").strip()
        if not text:
            return
        normalized = text.lower()
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append(text)

    add(source_record.get("key"))
    add(source_record.get("name"))
    add(humanize_knowledge_source_label(source_record.get("key")))
    add(humanize_knowledge_source_label(source_record.get("name")))
    url = str(source_record.get("url") or "").strip()
    add(url)
    if url:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.strip()
        path = parsed.path.rstrip("/")
        add(host)
        if host and path:
            add(f"{host}{path}")
        add(path)
        segments = [segment for segment in path.split("/") if segment]
        if segments:
            add(segments[-1])
        if len(segments) >= 2:
            add("/".join(segments[-2:]))
    return candidates


def detect_source_from_text(
    query: Optional[str],
    explicit_identifier: Optional[str] = None,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    source_text = explicit_identifier if isinstance(explicit_identifier, str) and explicit_identifier.strip() else query
    raw_text = str(source_text or "").strip()
    if not raw_text:
        return None
    text = raw_text.lower()
    normalized_query = normalize_knowledge_source_token(raw_text)
    if not normalized_query:
        return None
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    best_match: Optional[dict[str, Any]] = None
    best_score = 0
    explicit = isinstance(explicit_identifier, str) and explicit_identifier.strip()

    for source_record in knowledge_source_records_from_catalog(catalog).values():
        score = 0
        for candidate in source_record_match_candidates(source_record):
            candidate_text = str(candidate or "").strip().lower()
            normalized_candidate = normalize_knowledge_source_token(candidate)
            if not candidate_text or not normalized_candidate:
                continue
            if candidate_text == text or normalized_candidate == normalized_query:
                score = max(score, 1000 + len(normalized_candidate))
                continue
            if explicit and len(normalized_query) >= 6 and normalized_query in normalized_candidate:
                score = max(score, 700 + len(normalized_candidate))
            if len(candidate_text) >= 6 and candidate_text in text:
                score = max(score, 600 + len(normalized_candidate))
            if len(normalized_candidate) >= 6 and normalized_candidate in normalized_query:
                score = max(score, 500 + len(normalized_candidate))
        if score > best_score:
            best_score = score
            best_match = source_record
    return best_match


def priority_label(priority: Optional[str]) -> str:
    mapping = {
        "critical": "Critical",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }
    text = str(priority or "").strip().lower()
    return mapping.get(text, text or "Unspecified")


def knowledge_review_queue_note_for_target(
    queue: Any,
    target_key: Optional[str],
    *,
    target_label: Optional[str] = None,
) -> Optional[str]:
    if not isinstance(queue, dict):
        return None
    key = str(target_key or "").strip()
    if not key:
        return None
    matches = [
        item
        for item in queue.get("entries", [])
        if isinstance(item, dict) and str(item.get("key") or "").strip() == key
    ]
    if not matches:
        return None
    rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    highest = "low"
    for item in matches:
        priority = str(item.get("priority") or "low")
        if rank.get(priority, 0) > rank.get(highest, 0):
            highest = priority
    label = str(target_label or key)
    return f"{label}: {len(matches)} pending review item(s), highest priority {priority_label(highest)}."


def probe_result_worknet_key(skill_key: str, probe: dict[str, Any]) -> str:
    normalized_skill = str(skill_key or "").strip().lower()
    if normalized_skill in {item["key"] for item in KNOWN_WORKNETS}:
        return normalized_skill
    payload = probe.get("result")
    labels = payload.get("user_actions") if isinstance(payload, dict) else None
    action_map = payload.get("_internal", {}).get("action_map") if isinstance(payload, dict) and isinstance(payload.get("_internal"), dict) else None
    message = payload.get("user_message") if isinstance(payload, dict) else None
    return runtime_guidance_worknet_key(
        None,
        labels=labels,
        action_map=action_map,
        message=message,
    )


def runtime_probe_effective_status(probe: dict[str, Any]) -> str:
    payload = probe.get("result")
    if isinstance(payload, dict):
        if payload.get("ok") is False:
            return "failed"
        if str(payload.get("status") or "").strip().lower() == "error":
            return "failed"
        if runtime_payload_has_blocker(payload):
            return "failed"
    return "ok" if probe.get("ok") else "failed"


def humanize_runtime_probe_plain_text_summary(
    worknet_key: str,
    label: str,
    text: Any,
) -> Optional[str]:
    raw = str(text or "").strip()
    if not raw:
        return None
    lowered = raw.lower()
    if worknet_key == "kya":
        if label == "kya sign claim help":
            return "KYA can sign the claim after eligibility and wallet checks pass."
        if label == "kya relay recipient help":
            return "KYA relay recipient guidance is available for the delegated eligibility flow."
        if label == "kya kyc help":
            return "KYA identity guidance is available."
    if worknet_key == "gov" and "name or service not known" in lowered:
        return "Gov network lookup failed; retry after connectivity is available."
    if worknet_key == "gov" and label == "gov private state":
        if "state_principal_not_in_epoch" in lowered or "no awp power" in lowered:
            return "This principal has no AWP Power for the current Gov epoch."
        if "traceback" in lowered or "state.py" in lowered:
            return "Gov private-state inspection failed before AWP Power could be confirmed."
    if worknet_key == "ardi" and "all base rpcs failed" in lowered:
        return "Ardi could not reach a Base RPC endpoint."
    if lowered.startswith("wallet ready:"):
        address = raw.split(":", 1)[1].strip() if ":" in raw else ""
        worknet_name = runtime_guidance_worknet_name(worknet_key)
        if address:
            return f"{worknet_name} wallet ready: {address}."
        return f"{worknet_name} wallet ready."
    return None


def humanize_runtime_probe_summary_display(
    worknet_key: str,
    label: str,
    *,
    status: str,
    payload: Any,
    text: Any,
) -> Optional[str]:
    step_like = {
        "label": label,
        "status": status,
    }
    if isinstance(payload, dict):
        if status == "failed":
            failure = humanize_review_failure(worknet_key, step_like, payload)
            if failure:
                return failure
        review = humanize_review_step(worknet_key, step_like, payload)
        if review:
            return review
        message_display = humanize_runtime_guidance_message_display(
            worknet_key or None,
            payload.get("user_message") or payload.get("message"),
            state=payload.get("state"),
        )
        if message_display:
            return message_display
        error_summary = runtime_payload_error_summary(payload)
        if error_summary:
            return humanize_runtime_probe_plain_text_summary(worknet_key, label, error_summary) or error_summary
    return humanize_runtime_probe_plain_text_summary(worknet_key, label, text)


def annotate_probe_result_display(
    probe: dict[str, Any],
    *,
    skill_key: str,
) -> dict[str, Any]:
    return annotate_probe_result_display_payload(
        probe,
        skill_key=skill_key,
        dependencies={
            "build_executed_step_result_display": build_executed_step_result_display,
            "compact_preview_text": compact_preview_text,
            "extract_runtime_guidance_from_payload": extract_runtime_guidance_from_payload,
            "humanize_runtime_guidance_message_display": humanize_runtime_guidance_message_display,
            "humanize_runtime_next_command_display": humanize_runtime_next_command_display,
            "humanize_runtime_payload_state": humanize_runtime_payload_state,
            "humanize_runtime_probe_summary_display": humanize_runtime_probe_summary_display,
            "probe_result_worknet_key": probe_result_worknet_key,
            "runtime_probe_effective_status": runtime_probe_effective_status,
            "should_replace_display_text": should_replace_display_text,
        },
    )


def annotate_probe_results_display(
    probe_results: Any,
    *,
    skill_key: str,
) -> list[dict[str, Any]]:
    if not isinstance(probe_results, list):
        return []
    return [
        annotate_probe_result_display(item, skill_key=skill_key)
        for item in probe_results
        if isinstance(item, dict)
    ]


def annotate_skill_inspection_record(record: Any) -> Any:
    if not isinstance(record, dict):
        return record
    normalized = dict(record)
    skill_key = str(normalized.get("skillKey") or "").strip().lower()
    normalized["probeResults"] = annotate_probe_results_display(
        normalized.get("probeResults"),
        skill_key=skill_key,
    )
    return normalized


def annotate_skill_inspection_catalog_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    inspections = normalized.get("inspections")
    if isinstance(inspections, list):
        normalized["inspections"] = [
            annotate_skill_inspection_record(item)
            for item in inspections
            if isinstance(item, dict)
        ]
    return normalized


def annotate_capability_bundle_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    skill_inspections = normalized.get("skillInspections")
    if isinstance(skill_inspections, list):
        normalized["skillInspections"] = [
            annotate_skill_inspection_record(item)
            for item in skill_inspections
            if isinstance(item, dict)
        ]
    reports = normalized.get("reports")
    if isinstance(reports, list):
        annotated_reports: list[dict[str, Any]] = []
        for item in reports:
            if not isinstance(item, dict):
                continue
            report = dict(item)
            if isinstance(report.get("skillInspection"), dict):
                report["skillInspection"] = annotate_skill_inspection_record(report.get("skillInspection"))
            annotated_reports.append(report)
        normalized["reports"] = annotated_reports
    return normalized


def find_probe_result(inspection: dict[str, Any], label: str) -> Optional[dict[str, Any]]:
    probe_results = inspection.get("probeResults", []) if isinstance(inspection, dict) else []
    for item in probe_results:
        if isinstance(item, dict) and item.get("label") == label:
            return item
    return None


def predict_persona_value(inspection: dict[str, Any]) -> Optional[str]:
    step = find_probe_result(inspection, "predict status")
    payload = step_result_payload(step) if step else None
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("persona"), str):
        value = str(data.get("persona")).strip()
        return value or None
    return None


def persona_from_log_lines(lines: list[str]) -> Optional[str]:
    for line in reversed(lines):
        match = re.search(r"persona=([A-Za-z0-9_-]+)", line)
        if match:
            value = match.group(1).strip()
            return value or None
    return None


def predict_persona_hint(state: dict[str, Any], inspection: dict[str, Any]) -> Optional[str]:
    current = predict_persona_value(inspection)
    if current and current.strip().lower() not in {"none", "null"}:
        return current
    cached = load_json(Path(state["cache"]) / "skill-inspections.json", {})
    if isinstance(cached, dict):
        for item in cached.get("inspections", []):
            if not isinstance(item, dict) or item.get("skillKey") != "predict":
                continue
            cached_persona = predict_persona_value(item)
            if cached_persona and cached_persona.strip().lower() not in {"none", "null"}:
                return cached_persona
    for item in load_active_processes(state):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "")
        argv = [str(part) for part in item.get("argv", [])] if isinstance(item.get("argv"), list) else []
        legacy_predict_prefix = (" " * 7) + "Predict "
        if (
            label.startswith("Start Predict loop")
            or (label.startswith(legacy_predict_prefix) and ("loop" in label or (" " * 6) in label))
            or argv[:2] == ["predict-agent", "loop"]
        ):
            persona = persona_from_log_lines(tail_text(item.get("logPath"), lines=80))
            if persona and persona.lower() not in {"none", "null"}:
                return persona
    log_root = Path(state["runs"]) / "logs"
    if log_root.exists():
        candidates = sorted(log_root.glob("*predict-loop*.log"))
        for path in reversed(candidates[-5:]):
            persona = persona_from_log_lines(tail_text(str(path), lines=80))
            if persona and persona.lower() not in {"none", "null"}:
                return persona
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    if isinstance(latest_run, dict):
        for step in latest_run.get("executedSteps", []):
            if not isinstance(step, dict):
                continue
            label = str(step.get("label") or "")
            if label.startswith("Select ") or label.startswith(" " * 7):
                argv = step.get("argv")
                if isinstance(argv, list) and argv:
                    value = str(argv[-1]).strip()
                    if value and value.lower() not in {"none", "null"}:
                        return value
    return None


def predict_loop_ready(state: dict[str, Any], inspection: dict[str, Any]) -> bool:
    persona = (predict_persona_hint(state, inspection) or "").strip().lower()
    return persona not in {"", "none", "null"}


def derive_runtime_remediation(
    skill_key: str,
    *,
    state: dict[str, Any],
    skill_root: Optional[Path],
    probe_results: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    notes: list[str] = []
    commands: list[dict[str, Any]] = []
    combined_text = "\n".join(str(item.get("text", "")) for item in probe_results if isinstance(item, dict))

    if skill_root is not None and repository_is_effectively_empty(skill_root):
        notes.append(
            "The official checkout currently only contains license or metadata files, so there is no upstream runtime to bootstrap yet."
        )
        return notes, commands

    if skill_key == "mine" and "dataclass() got an unexpected keyword argument 'slots'" in combined_text:
        notes.append("Mine runtime needs Python 3.11+; the current default python3 is too old for dataclass(slots=True).")
        python311 = shutil.which("python3.11")
        if python311 and skill_root is not None:
            commands.append(
                {
                    "label": "bootstrap mine with python3.11",
                    "cwd": str(skill_root),
                    "argv": ["env", f"PYTHON_BIN={python311}", "bash", "./scripts/bootstrap.sh"],
                    "category": "repair",
                    "requires_confirmation": False,
                }
            )
        elif skill_root is not None:
            commands.append(
                {
                    "label": "bootstrap mine with Python 3.11+",
                    "cwd": str(skill_root),
                    "argv": ["bash", "./scripts/bootstrap.sh"],
                    "category": "repair",
                    "requires_confirmation": False,
                }
            )
    if skill_key == "awp-skill" and "Could not reach AWP API" in combined_text:
        notes.append("awp-skill runtime is installed, but its own preflight could not reach the AWP API from this environment.")
    if skill_key == "gov" and "No module named 'eth_hash'" in combined_text and skill_root is not None:
        notes.append("gov-skill checkout is present, but its Python dependencies are not installed yet.")
        commands.extend(
            [
                {
                    "label": "create gov skill venv",
                    "cwd": str(skill_root),
                    "argv": ["python3", "-m", "venv", ".venv"],
                    "category": "repair",
                    "requires_confirmation": False,
                },
                {
                    "label": "install gov skill deps",
                    "cwd": str(skill_root),
                    "argv": [str(skill_root / ".venv" / "bin" / "pip"), "install", "eth-hash", "eth-account", "websockets", "pytest"],
                    "category": "repair",
                    "requires_confirmation": False,
                },
            ]
        )
    if skill_key == "predict" and skill_root is not None:
        install_script = skill_root / "install.sh"
        cargo_toml = skill_root / "Cargo.toml"
        if install_script.exists() and cargo_toml.exists() and not command_exists("predict-agent"):
            notes.append("predict-skill checkout is present, but predict-agent is not installed yet. The official install script pulls a GitHub release binary.")
            commands.append(
                {
                    "label": "install predict-agent binary",
                    "cwd": str(skill_root),
                    "argv": ["bash", "install.sh"],
                    "category": "repair",
                    "requires_confirmation": False,
                }
            )
            if shutil.which("cargo"):
                notes.append("Rust toolchain is present, so building predict-agent from source is also possible if release downloads stay blocked.")
                commands.append(
                    {
                        "label": "build predict-agent from source",
                        "cwd": str(skill_root),
                        "argv": ["cargo", "build", "--release"],
                        "category": "repair",
                        "requires_confirmation": False,
                    }
                )
            else:
                notes.append("Rust toolchain is not installed here, so source-build fallback is not currently available.")

    return notes, commands


def humanize_executed_step_label(
    label: Any,
    *,
    category: Any = None,
    execution_policy: Any = None,
) -> Optional[str]:
    text = str(label or "").strip()
    if not text:
        return None
    playbook_label = humanize_playbook_command_label(text)
    if playbook_label != text:
        return playbook_label
    review_label = humanize_review_step_label("", text)
    if review_label != text:
        return review_label
    action_label = humanize_public_action_label(text)
    if action_label != text:
        return action_label
    category_text = str(category or "").strip().lower()
    policy_text = str(execution_policy or "").strip().lower()
    lowered = text.lower()
    if category_text == "inspect" or policy_text in {"probe", "manual-review"}:
        if lowered.startswith("inspect "):
            return "Inspect " + text[len("inspect "):]
        return f"Inspect {text}"
    if policy_text in {"manual-control"}:
        if lowered.startswith("pause "):
            return "Pause " + text[len("pause "):]
        if lowered.startswith("stop "):
            return "Stop " + text[len("stop "):]
    if policy_text == "confirmation":
        return f"Confirm {text}"
    return text


def build_playbook_user_action_details(playbook: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    knowledge_actions = [
        item for item in playbook.get("knowledgeActions", [])
        if isinstance(item, dict)
    ] if isinstance(playbook.get("knowledgeActions"), list) else []
    command_actions = humanize_public_playbook_commands(playbook)
    combined = []
    if str(playbook.get("executionState") or "") == "review_required":
        combined.extend(knowledge_actions)
        combined.extend(command_actions)
    else:
        combined.extend(command_actions)
        combined.extend(knowledge_actions)
    for item in combined:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        command = str(item.get("command") or "").strip()
        if not label or not command:
            continue
        entries.append(
            {
                "label": label,
                "description": str(item.get("description") or "Action details pending.").strip(),
                "command": command,
            }
        )
    prioritized = prioritize_action_entries(
        entries,
        execution_state=str(playbook.get("executionState") or "").strip() or None,
        resume_status=str(playbook.get("resumeStatus") or "").strip() or None,
        worknet_key=str(playbook.get("worknetKey") or "").strip() or None,
    )
    details: list[dict[str, Any]] = []
    for item in prioritized:
        append_unique_action_detail(
            details,
            label=str(item.get("label") or "").strip(),
            description=str(item.get("description") or "Action details pending.").strip(),
            command=str(item.get("command") or "").strip() or None,
        )
    return details


def progress_message(step: int, total: int, title: str, detail: str) -> str:
    return f"[{step}/{total}] {title}: {detail}"


def official_preflight_cache_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "official-awp-skill-preflight.json"


def official_live_worknets_cache_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "official-live-worknets.json"


def inspect_background_process(
    state: dict[str, Any],
    label: str,
    *,
    tail_lines: int = 40,
) -> dict[str, Any]:
    record = find_active_process(state, label)
    if record is None:
        raise ValueError(f"unknown background label: {label}")
    return persist_background_observation(
        state,
        summarize_background_record(record, tail_lines=tail_lines),
    )


def _managed_payload_internal(payload: Any) -> dict[str, Any]:
    internal = payload.get("_internal") if isinstance(payload, dict) else None
    return internal if isinstance(internal, dict) else {}


def _managed_runtime_status(payload: Any) -> dict[str, Any]:
    status = _managed_payload_internal(payload).get("status")
    return status if isinstance(status, dict) else {}


def _append_unique_detail(details: list[str], value: Optional[str]) -> None:
    text = str(value or "").strip()
    if not text or text in details:
        return
    details.append(text)


_MINE_PROGRESS_PHASE_RE = re.compile(r"\bphase ([a-z_]+)\b", re.IGNORECASE)


def _mine_runtime_phase_state(runtime_status: dict[str, Any]) -> Optional[str]:
    queues = runtime_status.get("queues") if isinstance(runtime_status.get("queues"), dict) else {}
    current_batch = runtime_status.get("current_batch") if isinstance(runtime_status.get("current_batch"), dict) else {}
    last_summary = runtime_status.get("last_summary") if isinstance(runtime_status.get("last_summary"), dict) else {}
    messages = last_summary.get("messages") if isinstance(last_summary.get("messages"), list) else []

    for message in reversed(messages):
        text = str(message or "").strip()
        if not text:
            continue
        match = _MINE_PROGRESS_PHASE_RE.search(text)
        if not match:
            continue
        phase = match.group(1).strip().lower()
        mapping = {
            "discovery": "discovering",
            "dedup": "deduplicating",
            "pow": "preparing_proof",
            "crawling": "collecting",
            "structuring": "structuring",
            "submitting": "submitting",
        }
        mapped = mapping.get(phase)
        if mapped:
            return mapped

    if int(queues.get("submit_pending") or 0) > 0:
        return "submitting"
    if int(last_summary.get("submitted_items") or 0) > 0:
        return "submitting"
    if int(last_summary.get("processed_items") or 0) > 0:
        return "structuring"
    if int(last_summary.get("discovery_items") or 0) > 0 or int(last_summary.get("discovered_followups") or 0) > 0:
        return "discovering"
    if str(current_batch.get("state") or "").strip().lower() == "running" and int(current_batch.get("size") or 0) > 0:
        return "collecting"
    return None


def _mine_phase_headline(phase_state: Optional[str], *, dataset_text: str, fallback_message: str, recent_errors: list[Any]) -> str:
    if recent_errors:
        return "Mine worker is running with recent errors."
    mapping = {
        "discovering": "Mine is discovering new URLs.",
        "deduplicating": "Mine is deduplicating the active batch.",
        "preparing_proof": "Mine is preparing proof for the active batch.",
        "collecting": "Mine is collecting pages from the active dataset.",
        "structuring": "Mine is structuring collected records.",
        "submitting": "Mine is submitting processed records.",
    }
    if phase_state in mapping:
        return mapping[phase_state]
    if dataset_text:
        return f"Mine worker is running on {dataset_text}."
    return fallback_message or "Mine worker is running."


def _mine_managed_summary_from_payload(
    payload: dict[str, Any],
    *,
    fallback_state: str,
    fallback_message: str,
) -> dict[str, Any]:
    internal = _managed_payload_internal(payload)
    runtime_status = _managed_runtime_status(payload)
    if not runtime_status:
        return {
            "state": fallback_state,
            "headline": fallback_message,
            "detail": None,
            "alive": fallback_state.lower() not in {"stopped", "failed", "complete", "completed", "idle"},
        }

    mining_state = str(runtime_status.get("mining_state") or fallback_state or "running").strip().lower() or "running"
    progress = runtime_status.get("progress") if isinstance(runtime_status.get("progress"), dict) else {}
    earnings_summary = runtime_status.get("earnings_summary") if isinstance(runtime_status.get("earnings_summary"), dict) else {}
    queues = runtime_status.get("queues") if isinstance(runtime_status.get("queues"), dict) else {}
    handoff = queues.get("agent_handoff") if isinstance(queues.get("agent_handoff"), dict) else {}
    recent_errors = internal.get("recent_errors") if isinstance(internal.get("recent_errors"), list) else []

    selected_dataset_ids = [str(item).strip() for item in runtime_status.get("selected_dataset_ids", []) if str(item).strip()]
    dataset_text = ", ".join(selected_dataset_ids[:2]) if selected_dataset_ids else ""
    if len(selected_dataset_ids) > 2:
        dataset_text += f" (+{len(selected_dataset_ids) - 2} more)"
    phase_state = _mine_runtime_phase_state(runtime_status) if mining_state == "running" else None

    if mining_state == "running":
        headline = _mine_phase_headline(
            phase_state,
            dataset_text=dataset_text,
            fallback_message="Mine worker is running.",
            recent_errors=recent_errors,
        )
    elif mining_state == "paused":
        headline = "Mine worker is paused."
    elif mining_state == "stopped":
        headline = "Mine worker has stopped."
    elif mining_state == "idle":
        headline = "Mine worker is idle."
    else:
        headline = fallback_message or f"Mine worker is {mining_state}."

    details: list[str] = []
    _append_unique_detail(details, f"Datasets: {dataset_text}" if dataset_text else None)

    epoch_submitted = earnings_summary.get("submitted")
    epoch_target = earnings_summary.get("target")
    epoch_percent = earnings_summary.get("progress_percent")
    epoch_remaining = earnings_summary.get("remaining")
    epoch_eta = earnings_summary.get("estimated_completion") or progress.get("estimated_completion")
    epoch_parts: list[str] = []
    if epoch_submitted not in (None, "") or epoch_target not in (None, ""):
        epoch_parts.append(f"Epoch progress {epoch_submitted or 0}/{epoch_target or '?'}")
    if epoch_percent not in (None, ""):
        try:
            epoch_value = float(epoch_percent)
            epoch_parts.append(f"{epoch_value:.0f}% complete" if epoch_value.is_integer() else f"{epoch_value:.1f}% complete")
        except (TypeError, ValueError):
            epoch_parts.append(f"{epoch_percent}% complete")
    if epoch_remaining not in (None, ""):
        epoch_parts.append(f"{epoch_remaining} remaining")
    if epoch_eta not in (None, ""):
        epoch_parts.append(f"ETA {epoch_eta}")
    _append_unique_detail(details, ", ".join(epoch_parts) if epoch_parts else None)

    processed = progress.get("session_processed_items")
    submitted = progress.get("session_submitted_items")
    failed = progress.get("session_failed_items")
    progress_bits: list[str] = []
    if processed not in (None, ""):
        progress_bits.append(f"{processed} processed")
    if submitted not in (None, ""):
        progress_bits.append(f"{submitted} submitted")
    if failed not in (None, ""):
        progress_bits.append(f"{failed} failed")
    _append_unique_detail(details, f"Session {', '.join(progress_bits)}" if progress_bits else None)

    queue_bits: list[str] = []
    for key, label in (("backlog", "backlog"), ("auth_pending", "auth"), ("submit_pending", "submit")):
        value = queues.get(key)
        if value not in (None, "", 0):
            queue_bits.append(f"{label}={value}")
    if isinstance(handoff, dict):
        handoff_total = sum(int(value or 0) for value in handoff.values())
        if handoff_total > 0:
            queue_bits.append(f"handoff={handoff_total}")
    _append_unique_detail(details, f"Queues {', '.join(queue_bits)}" if queue_bits else None)

    if phase_state:
        _append_unique_detail(details, f"Work phase: {phase_state.replace('_', ' ')}")
    phase = str(runtime_status.get("phase") or "").strip()
    _append_unique_detail(details, f"Phase: {phase}" if phase else None)

    current_batch = runtime_status.get("current_batch") if isinstance(runtime_status.get("current_batch"), dict) else {}
    if current_batch:
        batch_state = str(current_batch.get("state") or "").strip()
        batch_size = current_batch.get("size")
        batch_datasets = current_batch.get("dataset_ids") if isinstance(current_batch.get("dataset_ids"), list) else []
        batch_bits: list[str] = []
        if batch_state:
            batch_bits.append(batch_state)
        if batch_size not in (None, ""):
            batch_bits.append(f"{batch_size} item(s)")
        if batch_datasets:
            batch_bits.append("datasets " + ", ".join(str(item).strip() for item in batch_datasets[:2] if str(item).strip()))
        _append_unique_detail(details, f"Current batch: {', '.join(batch_bits)}" if batch_bits else None)

    last_summary = runtime_status.get("last_summary") if isinstance(runtime_status.get("last_summary"), dict) else {}
    summary_bits: list[str] = []
    for key, label in (
        ("discovery_items", "discovery"),
        ("discovered_followups", "follow-ups"),
        ("retry_pending", "retry pending"),
    ):
        value = last_summary.get(key)
        if value not in (None, "", 0):
            summary_bits.append(f"{label}={value}")
    _append_unique_detail(details, f"Last iteration summary: {', '.join(summary_bits)}" if summary_bits else None)

    last_iteration = runtime_status.get("last_iteration")
    _append_unique_detail(details, f"Last iteration {last_iteration}" if last_iteration not in (None, "", 0) else None)

    if recent_errors:
        _append_unique_detail(details, f"Last error: {str(recent_errors[-1])[:180].strip()}")

    detail = ". ".join(details) + "." if details else None
    return {
        "state": phase_state or mining_state,
        "headline": headline,
        "detail": detail,
        "alive": mining_state not in {"stopped", "failed", "complete", "completed", "idle"},
    }


def _predict_local_summary_from_probe(
    payload: dict[str, Any],
    *,
    fallback_state: str,
    fallback_headline: str,
    fallback_detail: Optional[str],
) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    internal = payload.get("_internal") if isinstance(payload.get("_internal"), dict) else {}
    timeslot = data.get("timeslot") if isinstance(data.get("timeslot"), dict) else {}
    open_orders = [item for item in data.get("open_orders", []) if isinstance(item, dict)] if isinstance(data.get("open_orders"), list) else []
    recent_results = [item for item in data.get("recent_results", []) if isinstance(item, dict)] if isinstance(data.get("recent_results"), list) else []
    state = str(fallback_state or "").strip().lower()
    error_code = str(error.get("code") or "").strip().lower()
    retryable = bool(error.get("retryable"))

    submissions_remaining = timeslot.get("submissions_remaining")
    submissions_used = timeslot.get("submissions_used")
    slot_limit = timeslot.get("slot_limit")
    slot_resets_in = timeslot.get("slot_resets_in") or timeslot.get("resets_in_seconds")

    if not state or state == "running":
        try:
            if submissions_remaining is not None and int(submissions_remaining) <= 0:
                state = "waiting_for_timeslot_reset"
        except (TypeError, ValueError):
            pass
    if error_code == "status_failed" and retryable:
        state = "waiting_for_service"
    elif error_code == "status_failed" and not state:
        state = "error"
    elif state in {"running", ""} and open_orders:
        state = "orders_open"
    elif state in {"running", ""} and recent_results:
        state = "recent_result_recorded"
    if not state:
        state = "running"

    if state == "waiting_for_timeslot_reset":
        headline = "Predict loop is waiting for the next timeslot."
    elif state == "waiting_for_service":
        headline = "Predict status probe is waiting for coordinator connectivity."
    elif state == "orders_open":
        headline = f"Predict has {len(open_orders)} open order(s) working."
    elif state == "recent_result_recorded":
        headline = "Predict recorded a recent market result."
    elif fallback_headline and fallback_headline != "Background process is running.":
        headline = fallback_headline
    else:
        headline = "Predict loop is running."

    detail_bits: list[str] = []
    persona = str(data.get("persona") or "").strip()
    total_predictions = data.get("total_predictions")
    balance = str(data.get("balance") or "").strip()
    if persona or total_predictions not in (None, "") or balance:
        persona_bits: list[str] = []
        if persona:
            persona_bits.append(f"Persona {persona}")
        if total_predictions not in (None, ""):
            persona_bits.append(f"{total_predictions} total predictions")
        if balance:
            persona_bits.append(f"{balance} chips")
        _append_unique_detail(detail_bits, ", ".join(persona_bits))

    timeslot_bits: list[str] = []
    if submissions_used not in (None, "") and slot_limit not in (None, ""):
        timeslot_bits.append(f"Timeslot {submissions_used}/{slot_limit} used")
    elif submissions_remaining not in (None, ""):
        timeslot_bits.append(f"{submissions_remaining} submissions remaining")
    if submissions_remaining not in (None, "") and submissions_used not in (None, "") and slot_limit in (None, ""):
        timeslot_bits.append(f"{submissions_remaining} submissions remaining")
    if slot_resets_in not in (None, ""):
        timeslot_bits.append(f"reset in {slot_resets_in}s")
    _append_unique_detail(detail_bits, ", ".join(timeslot_bits) if timeslot_bits else None)

    if open_orders:
        total_tickets = 0
        total_filled = 0
        for order in open_orders:
            try:
                total_tickets += int(order.get("tickets") or 0)
            except (TypeError, ValueError):
                pass
            try:
                total_filled += int(order.get("tickets_filled") or 0)
            except (TypeError, ValueError):
                pass
        first = open_orders[0]
        fill_phrase = f"{total_filled}/{total_tickets} filled" if total_tickets > 0 else None
        first_market = " ".join(
            part
            for part in (
                str(first.get("asset") or "").strip(),
                str(first.get("window") or "").strip(),
                str(first.get("direction") or "").strip().upper(),
            )
            if part
        ).strip()
        first_bits = []
        if first_market:
            first_bits.append(first_market)
        if first.get("tickets") not in (None, ""):
            first_bits.append(
                f"{first.get('tickets_filled') or 0}/{first.get('tickets')} filled"
            )
        if first.get("close_at") not in (None, ""):
            first_bits.append(f"closes {first.get('close_at')}")
        orders_phrase = f"Open orders {len(open_orders)}"
        if fill_phrase:
            orders_phrase += f", {fill_phrase}"
        if first_bits:
            orders_phrase += f"; first: {', '.join(str(item) for item in first_bits)}"
        _append_unique_detail(detail_bits, orders_phrase)

    if recent_results:
        wins = sum(1 for item in recent_results if item.get("won") is True)
        payout_total = 0
        for item in recent_results:
            try:
                payout_total += int(item.get("payout_chips") or 0)
            except (TypeError, ValueError):
                pass
        latest = recent_results[0]
        latest_market = " ".join(
            part
            for part in (
                str(latest.get("asset") or "").strip(),
                str(latest.get("window") or "").strip(),
                str(latest.get("direction") or "").strip().upper(),
            )
            if part
        ).strip()
        result_phrase = f"Recent results {len(recent_results)}, {wins} win(s), payout {payout_total} chips"
        latest_bits = []
        if latest_market:
            latest_bits.append(latest_market)
        latest_bits.append("WON" if latest.get("won") is True else "LOST")
        if latest.get("payout_chips") not in (None, ""):
            latest_bits.append(f"payout {latest.get('payout_chips')}")
        if latest_bits:
            result_phrase += f"; latest: {', '.join(str(item) for item in latest_bits)}"
        _append_unique_detail(detail_bits, result_phrase)

    next_action = str(internal.get("next_action") or "").strip()
    next_command = str(internal.get("next_command") or "").strip()
    if next_action or next_command:
        guidance_bits = []
        if next_action:
            guidance_bits.append(f"next action {next_action}")
        if next_command:
            guidance_bits.append(next_command)
        _append_unique_detail(detail_bits, "Guidance: " + " | ".join(guidance_bits))

    message = runtime_message(payload)
    if error_code == "status_failed":
        _append_unique_detail(detail_bits, message or str(error.get("suggestion") or "").strip())
    elif fallback_detail:
        _append_unique_detail(detail_bits, fallback_detail)
    elif message and message != headline:
        _append_unique_detail(detail_bits, message)

    detail = ". ".join(detail_bits) + "." if detail_bits else fallback_detail
    return {
        "state": state,
        "headline": headline,
        "detail": detail,
    }


def summarize_managed_external_record(
    record: dict[str, Any],
    *,
    tail_lines: int = 40,
) -> dict[str, Any]:
    status_argv = record_command_argv(record, "statusArgv")
    status_result: Optional[dict[str, Any]] = None
    status_payload: Any = (
        record.get("statusPayload")
        if isinstance(record.get("statusPayload"), (dict, list))
        else None
    )
    message = str(record.get("lastMessage") or "Managed external process is controlled outside Workstation.").strip()
    state = str(record.get("runtimeState") or "running").strip() or "running"
    alive = state not in {"stopped", "failed", "complete", "completed"}
    if isinstance(status_payload, dict):
        payload_state = str(status_payload.get("state") or status_payload.get("status") or "").strip()
        if payload_state:
            state = payload_state
            alive = payload_state.lower() not in {"stopped", "failed", "complete", "completed", "idle"}
        guidance = extract_runtime_guidance_from_payload(
            status_payload,
            worknet_key=str(record.get("worknetKey") or "") or None,
        )
        guidance_message = guidance.get("message") if isinstance(guidance, dict) else None
        payload_message = runtime_message(status_payload)
        message = str(guidance_message or payload_message or message).strip()
        if str(record.get("worknetKey") or "").strip().lower() == "mine":
            mine_summary = _mine_managed_summary_from_payload(
                status_payload,
                fallback_state=state,
                fallback_message=message,
            )
            state = str(mine_summary.get("state") or state).strip() or state
            alive = bool(mine_summary.get("alive")) if mine_summary.get("alive") is not None else alive
            message = str(mine_summary.get("headline") or message).strip()
    if status_argv:
        result = run_command(
            status_argv,
            cwd=str(record.get("cwd")) if record.get("cwd") else None,
            timeout=30,
        )
        status_result = {
            "ok": result.get("ok"),
            "code": result.get("code"),
            "stderr": trim_output(result.get("stderr", "")),
        }
        status_payload = parse_json_loose(result.get("stdout", ""))
        if isinstance(status_payload, dict):
            payload_state = str(status_payload.get("state") or status_payload.get("status") or "").strip()
            if payload_state:
                state = payload_state
                alive = payload_state.lower() not in {"stopped", "failed", "complete", "completed", "idle"}
            guidance = extract_runtime_guidance_from_payload(
                status_payload,
                worknet_key=str(record.get("worknetKey") or "") or None,
            )
            guidance_message = guidance.get("message") if isinstance(guidance, dict) else None
            payload_message = runtime_message(status_payload)
            message = str(guidance_message or payload_message or message).strip()
            if str(record.get("worknetKey") or "").strip().lower() == "mine":
                mine_summary = _mine_managed_summary_from_payload(
                    status_payload,
                    fallback_state=state,
                    fallback_message=message,
                )
                state = str(mine_summary.get("state") or state).strip() or state
                alive = bool(mine_summary.get("alive")) if mine_summary.get("alive") is not None else alive
                message = str(mine_summary.get("headline") or message).strip()
        elif result.get("ok") is False:
            alive = False
            error = trim_output(result.get("stderr", "")) or "status command failed"
            message = f"Status command failed: {error}"
    detail = status_result.get("stderr") if isinstance(status_result, dict) and status_result.get("stderr") else None
    if isinstance(status_payload, dict) and str(record.get("worknetKey") or "").strip().lower() == "mine":
        mine_summary = _mine_managed_summary_from_payload(
            status_payload,
            fallback_state=state,
            fallback_message=message,
        )
        state = str(mine_summary.get("state") or state).strip() or state
        alive = bool(mine_summary.get("alive")) if mine_summary.get("alive") is not None else alive
        message = str(mine_summary.get("headline") or message).strip()
        detail = str(mine_summary.get("detail") or detail or "").strip() or detail
    summary = {
        "state": state,
        "headline": message,
        "detail": detail,
    }
    return {
        "label": str(record.get("label") or ""),
        "kind": "managed-external",
        "worknetKey": record.get("worknetKey"),
        "worknetName": record.get("worknetName"),
        "externalSessionId": record.get("externalSessionId"),
        "pid": None,
        "cwd": record.get("cwd"),
        "argv": record.get("argv"),
        "statusCommand": record.get("statusCommand"),
        "pauseCommand": record.get("pauseCommand"),
        "stopCommand": record.get("stopCommand"),
        "logPath": record.get("logPath"),
        "startedAt": record.get("startedAt"),
        "alive": alive,
        "logTail": tail_text(record.get("logPath"), lines=tail_lines),
        "summary": summary,
        "statusResult": status_result,
        "statusPayload": status_payload if isinstance(status_payload, (dict, list)) else None,
    }


def summarize_background_record(
    record: dict[str, Any],
    *,
    tail_lines: int = 40,
) -> dict[str, Any]:
    if str(record.get("kind") or "") == "managed-external":
        return summarize_managed_external_record(record, tail_lines=tail_lines)
    log_tail = tail_text(record.get("logPath"), lines=tail_lines)
    summary = summarize_background_log(record, log_tail)
    status_argv = record_command_argv(record, "statusArgv")
    status_result: Optional[dict[str, Any]] = None
    status_payload: Any = None
    if status_argv:
        result = run_command(
            status_argv,
            cwd=str(record.get("cwd")) if record.get("cwd") else None,
            timeout=30,
        )
        status_result = {
            "ok": result.get("ok"),
            "code": result.get("code"),
            "stderr": trim_output(result.get("stderr", "")),
        }
        status_payload = parse_json_loose(result.get("stdout", ""))
        if isinstance(status_payload, dict) and str(record.get("worknetKey") or "").strip().lower() == "predict":
            summary = _predict_local_summary_from_probe(
                status_payload,
                fallback_state=str(summary.get("state") or ""),
                fallback_headline=str(summary.get("headline") or ""),
                fallback_detail=str(summary.get("detail") or "").strip() or None,
            )
    return {
        "label": str(record.get("label") or ""),
        "worknetKey": record.get("worknetKey"),
        "worknetName": record.get("worknetName"),
        "pid": record.get("pid"),
        "cwd": record.get("cwd"),
        "argv": record.get("argv"),
        "statusCommand": render_argv(status_argv) if status_argv else None,
        "logPath": record.get("logPath"),
        "startedAt": record.get("startedAt"),
        "alive": process_is_alive(int(record["pid"])) if isinstance(record.get("pid"), int) else False,
        "logTail": log_tail,
        "summary": summary,
        "statusResult": status_result,
        "statusPayload": status_payload if isinstance(status_payload, (dict, list)) else None,
    }


def mine_session_id_from_guidance(guidance: Any) -> Optional[str]:
    if not isinstance(guidance, dict):
        return None
    internal = guidance.get("_internal")
    if isinstance(internal, dict):
        for key in ("session_id", "sessionId", "background_session", "worker_session"):
            value = internal.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    message = str(guidance.get("message") or guidance.get("messageDisplay") or "").strip()
    match = MINE_SESSION_RE.search(message)
    return match.group(1) if match else None


def follow_up_action_by_token(actions: list[dict[str, Any]], token: str) -> Optional[dict[str, Any]]:
    token = token.lower()
    for item in actions:
        label = str(item.get("label") or "").lower()
        command = str(item.get("command") or "").lower()
        argv_text = " ".join(str(part) for part in item.get("argv", [])).lower() if isinstance(item.get("argv"), list) else ""
        if token in label or token in command or token in argv_text:
            return item
    return None


def action_argv(action: Optional[dict[str, Any]]) -> Optional[list[str]]:
    if not isinstance(action, dict):
        return None
    argv = action.get("argv")
    if isinstance(argv, list) and argv:
        return [str(part) for part in argv]
    command = action.get("command")
    if isinstance(command, str) and command.strip():
        try:
            return shlex.split(command)
        except ValueError:
            return None
    return None


def build_mine_managed_external_record(
    run_record: dict[str, Any],
    *,
    state: dict[str, Any],
) -> Optional[dict[str, Any]]:
    playbook = run_record.get("playbook", {}) if isinstance(run_record.get("playbook"), dict) else {}
    if str(playbook.get("worknetKey") or "").strip().lower() != "mine":
        return None
    guidance = run_record.get("runtimeGuidance", {})
    session_id = mine_session_id_from_guidance(guidance)
    if not session_id:
        return None
    executed_steps = run_record.get("executedSteps", []) if isinstance(run_record.get("executedSteps"), list) else []
    source_step = next(
        (
            step for step in reversed(executed_steps)
            if isinstance(step, dict)
            and step.get("status") == "ok"
            and isinstance(step.get("argv"), list)
            and "scripts/run_tool.py" in " ".join(str(part) for part in step.get("argv", []))
            and "agent-start" in " ".join(str(part) for part in step.get("argv", []))
        ),
        None,
    )
    if source_step is None:
        return None
    follow_up_actions = normalized_follow_up_actions(run_record.get("followUpActions", []))
    status_action = follow_up_action_by_token(follow_up_actions, "status")
    pause_action = follow_up_action_by_token(follow_up_actions, "pause")
    stop_action = follow_up_action_by_token(follow_up_actions, "stop")
    cwd = (
        str(source_step.get("cwd"))
        if source_step.get("cwd")
        else str(status_action.get("cwd")) if isinstance(status_action, dict) and status_action.get("cwd") else None
    )
    status_argv = action_argv(status_action)
    pause_argv = action_argv(pause_action)
    stop_argv = action_argv(stop_action) or pause_argv
    message = str(guidance.get("message") or "").strip()
    return {
        "kind": "managed-external",
        "type": "managed-external",
        "label": f"Mine session {session_id}",
        "worknetKey": "mine",
        "worknetName": playbook.get("requiredSkill") or "Mine WorkNet",
        "externalSessionId": session_id,
        "cwd": cwd,
        "argv": [str(part) for part in source_step.get("argv", [])],
        "statusArgv": status_argv,
        "pauseArgv": pause_argv,
        "stopArgv": stop_argv,
        "statusCommand": render_argv(status_argv) if status_argv else None,
        "pauseCommand": render_argv(pause_argv) if pause_argv else None,
        "stopCommand": render_argv(stop_argv) if stop_argv else None,
        "startedAt": run_record.get("generatedAt") or now_iso(),
        "source": "runtime-guidance",
        "sourceStepLabel": source_step.get("label"),
        "lastMessage": message or f"Mine background worker launched (session: {session_id}).",
        "runtimeState": str(guidance.get("state") or "running"),
        "stateRoot": state["root"],
    }


def sync_managed_external_processes_from_run(
    state: dict[str, Any],
    run_record: dict[str, Any],
) -> list[dict[str, Any]]:
    record = build_mine_managed_external_record(run_record, state=state)
    if record is None:
        return load_active_processes(state)
    active = register_active_process(state, record)
    run_record["managedExternalProcess"] = record
    run_record["activeBackgroundProcesses"] = active
    return active


def first_present(record: Any, keys: list[str], default: Any = None) -> Any:
    if not isinstance(record, dict):
        return default
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return default


def normalize_worknet_entries(payload: Any) -> list[dict[str, Any]]:
    body = rpc_result_body(payload)
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    if isinstance(body, dict):
        for key in ("items", "worknets", "data", "rows", "results"):
            value = body.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def normalize_search_entries(payload: Any) -> list[dict[str, Any]]:
    body = rpc_result_body(payload)
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    if isinstance(body, dict):
        for key in ("items", "worknets", "data", "rows", "results"):
            value = body.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def extract_command_hints_from_skill_md(path: Path, limit: int = 20) -> list[str]:
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    hints: list[str] = []
    for match in COMMAND_HINT_RE.finditer(text):
        cmd = " ".join(match.group(1).split())
        if cmd not in hints:
            hints.append(cmd)
        if len(hints) >= limit:
            break
    return hints


def inspect_skill_runtime(
    skill_key: str,
    *,
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return inspect_skill_runtime_payload(
        skill_key,
        state=state,
        inventory=inventory,
        dependencies={
            "annotate_probe_results_display": annotate_probe_results_display,
            "build_manifest_commands": build_manifest_commands,
            "build_source_inventory": build_source_inventory,
            "command_exists": command_exists,
            "command_probe_available": command_probe_available,
            "derive_runtime_remediation": derive_runtime_remediation,
            "extract_command_hints_from_skill_md": extract_command_hints_from_skill_md,
            "official_remote_manifest": official_remote_manifest,
            "planned_skill_root": planned_skill_root,
            "probe_failures_are_expected_state": probe_failures_are_expected_state,
            "probe_failures_are_network_only": probe_failures_are_network_only,
            "repository_file_is_metadata": repository_file_is_metadata,
            "repository_files": repository_files,
            "repository_is_effectively_empty": repository_is_effectively_empty,
            "resolve_skill_root": resolve_skill_root,
            "run_inspection_probe": run_inspection_probe,
            "state_context": state_context,
        },
    )


def build_skill_inspection_catalog(
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_skill_inspection_catalog_payload(
        state=state,
        inventory=inventory,
        dependencies={
            "KNOWN_WORKNETS": KNOWN_WORKNETS,
            "annotate_skill_inspection_catalog_payload": annotate_skill_inspection_catalog_payload,
            "atomic_write_json": atomic_write_json,
            "build_source_inventory": build_source_inventory,
            "inspect_skill_runtime": inspect_skill_runtime,
            "now_iso": now_iso,
            "state_context": state_context,
            "write_reference_export": write_reference_export,
        },
    )


def load_cached_skill_inspection_catalog(
    state: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    return load_cached_skill_inspection_catalog_payload(
        state=state,
        dependencies={
            "annotate_skill_inspection_catalog_payload": annotate_skill_inspection_catalog_payload,
            "load_json": load_json,
            "state_context": state_context,
        },
    )


def build_recovery_state(state: dict[str, Any]) -> dict[str, Any]:
    return build_recovery_state_payload(
        state,
        dependencies={
            "choose_default_confirmation": choose_default_confirmation,
            "choose_default_follow_up_action": choose_default_follow_up_action,
            "hours_since_iso": hours_since_iso,
            "inspect_background_process": inspect_background_process,
            "load_active_processes": load_active_processes,
            "load_json": load_json,
            "normalized_confirmation_queue": normalized_confirmation_queue,
            "normalized_follow_up_actions": normalized_follow_up_actions,
            "review_status_display": review_status_display,
        },
    )


def build_skill_sync_command(skill_record: dict[str, Any]) -> Optional[dict[str, Any]]:
    return build_skill_sync_command_payload(
        skill_record,
        dependencies={
            "SKILL_ROOT": SKILL_ROOT,
            "looks_official_skill_uri": looks_official_skill_uri,
        },
    )


def build_skill_inspect_command(skill_key: str) -> dict[str, Any]:
    return build_skill_inspect_command_payload(
        skill_key,
        dependencies={
            "SKILL_ROOT": SKILL_ROOT,
        },
    )


def runtime_probe(state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return runtime_probe_payload(
        state=state,
        dependencies={
            "command_exists": command_exists,
            "command_help_probe": command_help_probe,
            "now_iso": now_iso,
            "shutil": shutil,
            "state_context": state_context,
        },
    )


def awp_skill_checkout_root(state: Optional[dict[str, Any]] = None) -> Path:
    state = state or state_context()
    return Path(state["skills"]) / "checkouts" / "awp-skill"


def run_awp_skill_preflight(
    state: Optional[dict[str, Any]] = None,
    *,
    address: Optional[str] = None,
) -> dict[str, Any]:
    state = state or state_context()
    root = awp_skill_checkout_root(state)
    script = root / "scripts" / "preflight.py"
    if not script.exists():
        return {
            "available": False,
            "path": str(script),
            "ok": False,
            "result": None,
            "command": None,
            "error": "awp-skill preflight.py not found",
        }
    argv = ["python3", str(script)]
    if address:
        argv.extend(["--address", address])
    result = run_command(argv, cwd=str(root), timeout=60)
    payload = parse_json_loose(result.get("stdout", ""))
    record = {
        "available": True,
        "path": str(script),
        "ok": result.get("ok", False),
        "result": payload if isinstance(payload, dict) else None,
        "command": {
            "argv": argv,
            "cwd": str(root),
            "code": result.get("code"),
            "stderr": trim_output(result.get("stderr", "")),
        },
        "error": None if result.get("ok", False) else trim_output(result.get("stderr", "") or result.get("stdout", "")),
    }
    cache_path = official_preflight_cache_path(state)
    existing = load_json(cache_path, {})
    candidate_result = record.get("result") if isinstance(record.get("result"), dict) else {}
    existing_result = existing.get("result") if isinstance(existing, dict) else {}
    candidate_registered = None
    if isinstance(candidate_result, dict):
        candidate_registered = candidate_result.get("state", {}).get("registered")
    existing_registered = None
    if isinstance(existing_result, dict):
        existing_registered = existing_result.get("state", {}).get("registered")

    should_write = True
    if existing and existing_registered in {True, False} and candidate_registered is None:
        should_write = False
    if should_write:
        atomic_write_json(cache_path, record)
    return record


def build_dependency_command(
    dependency_key: str,
    install_uri: str,
    *,
    category: str = "install",
    requires_confirmation: bool = False,
) -> dict[str, Any]:
    return {
        "label": f"ensure {dependency_key} dependency",
        "cwd": str(SKILL_ROOT / "scripts"),
        "argv": [
            "python3",
            str(SKILL_ROOT / "scripts" / "manage-dependency.py"),
            "--dependency-key",
            dependency_key,
            "--uri",
            install_uri,
            "--mode",
            "ensure",
        ],
        "category": category,
        "requires_confirmation": requires_confirmation,
    }


def build_registration_plan(
    state: Optional[dict[str, Any]] = None,
    wallet: Optional[dict[str, Any]] = None,
    *,
    include_probe: bool = True,
) -> dict[str, Any]:
    return build_registration_plan_payload(
        state=state,
        wallet=wallet,
        include_probe=include_probe,
        dependencies={
            "awp_wallet_snapshot": awp_wallet_snapshot,
            "build_dependency_command": build_dependency_command,
            "now_iso": now_iso,
            "run_awp_skill_preflight": run_awp_skill_preflight,
            "runtime_probe": runtime_probe,
            "state_context": state_context,
        },
    )


def recommend_worknet_actions(
    bundle: dict[str, Any],
    *,
    preferences: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return recommend_worknet_actions_payload(
        bundle,
        preferences=preferences,
        dependencies={
            "build_playbook_command": build_playbook_command,
            "humanize_worknet_switch_summary": humanize_worknet_switch_summary,
            "query_knowledge_command": query_knowledge_command,
            "resolve_worknet": resolve_worknet,
            "run_worknet_command": run_worknet_command,
        },
    )


def fallback_capability_reports(
    inventory: dict[str, Any], state: Optional[dict[str, Any]] = None
) -> list[dict[str, Any]]:
    return fallback_capability_reports_payload(
        inventory,
        state=state,
        dependencies={
            "KNOWN_WORKNETS": KNOWN_WORKNETS,
            "build_skill_inspection_catalog": build_skill_inspection_catalog,
            "canonical_worknet_scan_reason": canonical_worknet_scan_reason,
            "ensure_user_preferences": ensure_user_preferences,
            "humanize_capability_reason_part": humanize_capability_reason_part,
            "infer_runnable": infer_runnable,
            "inspection_status_blocks_runtime": inspection_status_blocks_runtime,
            "inspection_status_enables_runtime": inspection_status_enables_runtime,
            "join_product_sentences": join_product_sentences,
            "knowledge_worknet_metadata": knowledge_worknet_metadata,
            "looks_official_skill_uri": looks_official_skill_uri,
            "official_remote_manifest": official_remote_manifest,
            "predict_loop_ready": predict_loop_ready,
            "runtime_probe_blockers": runtime_probe_blockers,
            "runtime_spec_reason_parts": runtime_spec_reason_parts,
            "skill_registry_from_inventory": skill_registry_from_inventory,
            "state_context": state_context,
            "strip_sentence_end": strip_sentence_end,
        },
    )


def match_profile_from_rpc(entry: dict[str, Any]) -> Optional[dict[str, Any]]:
    candidate_values = [
        str(first_present(entry, ["worknetId", "id", "worknet_id", "subnetId"], "")).lower(),
        str(first_present(entry, ["name"], "")).lower(),
        str(first_present(entry, ["symbol", "tokenSymbol"], "")).lower(),
    ]
    normalized_candidates = {normalize_worknet_token(value) for value in candidate_values if value}
    for profile in KNOWN_WORKNETS:
        aliases = {profile["key"], str(profile["worknet_id"]).lower(), profile["name"].lower()}
        aliases.update(alias.lower() for alias in profile.get("aliases", []))
        normalized_aliases = {normalize_worknet_token(value) for value in aliases if value}
        if any(value and value in aliases for value in candidate_values):
            return profile
        if normalized_candidates.intersection(normalized_aliases):
            return profile
    return None


def resolve_live_worknet_id(
    entry: dict[str, Any],
    profile: Optional[dict[str, Any]],
    auxiliary_candidates: Optional[list[dict[str, Any]]] = None,
) -> tuple[Any, str, list[dict[str, Any]]]:
    return resolve_live_worknet_id_payload(
        entry,
        profile,
        auxiliary_candidates=auxiliary_candidates,
        dependencies={
            "first_present": first_present,
            "normalize_search_entries": normalize_search_entries,
            "normalize_worknet_id": normalize_worknet_id,
            "normalize_worknet_token": normalize_worknet_token,
            "rpc_call": rpc_call,
        },
    )


def resolution_confidence(resolved_via: str) -> str:
    if resolved_via == "entry":
        return "high"
    if resolved_via == "profile-successor":
        return "medium"
    if resolved_via == "profile":
        return "medium"
    if resolved_via.startswith("ranked"):
        return "medium"
    if resolved_via.startswith("search:"):
        return "medium"
    return "low"


def enrich_reports_with_rpc(
    reports: list[dict[str, Any]], inventory: dict[str, Any], agent_address: Optional[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return enrich_reports_with_rpc_payload(
        reports,
        inventory,
        agent_address,
        dependencies={
            "first_present": first_present,
            "looks_official_skill_uri": looks_official_skill_uri,
            "match_profile_from_rpc": match_profile_from_rpc,
            "normalize_worknet_entries": normalize_worknet_entries,
            "rpc_call": rpc_call,
            "rpc_result_body": rpc_result_body,
            "rpc_try_many": rpc_try_many,
            "trim_output": trim_output,
        },
    )


def enrich_reports_with_cached_live_worknets(
    reports: list[dict[str, Any]], live_worknets: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return enrich_reports_with_cached_live_worknets_payload(
        reports,
        live_worknets,
        dependencies={
            "looks_official_skill_uri": looks_official_skill_uri,
            "match_profile_from_rpc": match_profile_from_rpc,
            "normalize_worknet_id": normalize_worknet_id,
            "safe_slug": safe_slug,
        },
    )


def build_capability_bundle() -> dict[str, Any]:
    return build_capability_bundle_payload(
        dependencies={
            "annotate_capability_bundle_payload": annotate_capability_bundle_payload,
            "atomic_write_json": atomic_write_json,
            "attach_knowledge_to_capability_reports": attach_knowledge_to_capability_reports,
            "awp_wallet_snapshot": awp_wallet_snapshot,
            "build_skill_inspection_catalog": build_skill_inspection_catalog,
            "build_source_inventory": build_source_inventory,
            "derive_capability_execution_state": derive_capability_execution_state,
            "enrich_reports_with_cached_live_worknets": enrich_reports_with_cached_live_worknets,
            "enrich_reports_with_rpc": enrich_reports_with_rpc,
            "ensure_user_preferences": ensure_user_preferences,
            "fallback_capability_reports": fallback_capability_reports,
            "load_cached_live_worknets": load_cached_live_worknets,
            "load_cached_skill_inspection_catalog": load_cached_skill_inspection_catalog,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "now_iso": now_iso,
            "skill_registry_from_inventory": skill_registry_from_inventory,
            "state_context": state_context,
            "write_reference_export": write_reference_export,
        },
    )


def load_cached_capability_bundle(state: dict[str, Any]) -> Optional[dict[str, Any]]:
    return load_cached_capability_bundle_payload(
        state,
        dependencies={
            "annotate_capability_bundle_payload": annotate_capability_bundle_payload,
            "load_json": load_json,
        },
    )


def probe_registration(bundle: dict[str, Any], agent_address: Optional[str]) -> tuple[Optional[bool], Optional[str], list[str]]:
    if not agent_address:
        return None, None, ["agent address missing"]
    issues: list[str] = []
    for report in bundle.get("reports", []):
        diagnostics = report.get("rpcDiagnostics")
        if not isinstance(diagnostics, dict):
            continue
        agent_info = diagnostics.get("agentInfo")
        if not isinstance(agent_info, dict):
            continue
        recipient = first_present(agent_info, ["recipient", "rewardRecipient", "resolvedRecipient"])
        stake = first_present(agent_info, ["stake", "allocatedStake", "allocation"])
        if recipient or stake:
            return True, recipient, issues
    if bundle.get("rpc", {}).get("used"):
        return False, None, issues
    issues.append("live RPC unavailable; registration status is unknown")
    return None, None, issues


def probe_cached_official_registration(state: dict[str, Any]) -> tuple[Optional[bool], Optional[str], Optional[dict[str, Any]]]:
    payload = load_json(official_preflight_cache_path(state), {})
    if not isinstance(payload, dict):
        return None, None, None
    result = payload.get("result")
    if not isinstance(result, dict):
        return None, None, payload
    state_obj = result.get("state", {})
    if not isinstance(state_obj, dict):
        return None, None, payload
    registered = state_obj.get("registered")
    recipient = state_obj.get("recipient")
    if registered not in {True, False, None}:
        registered = None
    return registered, recipient, payload


def sync_live_worknets(
    state: Optional[dict[str, Any]] = None,
    *,
    agent_address: Optional[str] = None,
    limit: int = 100,
    max_pages: int = 5,
) -> dict[str, Any]:
    return sync_live_worknets_payload(
        state=state,
        agent_address=agent_address,
        limit=limit,
        max_pages=max_pages,
        dependencies={
            "atomic_write_json": atomic_write_json,
            "awp_wallet_snapshot": awp_wallet_snapshot,
            "first_present": first_present,
            "looks_official_skill_uri": looks_official_skill_uri,
            "match_profile_from_rpc": match_profile_from_rpc,
            "normalize_worknet_entries": normalize_worknet_entries,
            "normalize_worknet_id": normalize_worknet_id,
            "now_iso": now_iso,
            "official_live_worknets_cache_path": official_live_worknets_cache_path,
            "resolution_confidence": resolution_confidence,
            "resolve_live_worknet_id": resolve_live_worknet_id,
            "rpc_call": rpc_call,
            "rpc_result_body": rpc_result_body,
            "rpc_try_many": rpc_try_many,
            "state_context": state_context,
            "trim_output": trim_output,
            "write_reference_export": write_reference_export,
        },
    )


def load_cached_live_worknets(state: dict[str, Any]) -> Optional[dict[str, Any]]:
    return load_cached_live_worknets_payload(
        state,
        dependencies={
            "load_json": load_json,
            "official_live_worknets_cache_path": official_live_worknets_cache_path,
        },
    )


def build_preflight_report() -> dict[str, Any]:
    return build_preflight_report_payload(
        dependencies={
            "atomic_write_json": atomic_write_json,
            "awp_wallet_snapshot": awp_wallet_snapshot,
            "build_capability_bundle": build_capability_bundle,
            "build_knowledge_review_queue": build_knowledge_review_queue,
            "build_preflight_plain_language_summary": build_preflight_plain_language_summary,
            "build_recovery_decision": build_recovery_decision,
            "build_recovery_state": build_recovery_state,
            "build_registration_plan": build_registration_plan,
            "ensure_user_preferences": ensure_user_preferences,
            "load_cached_capability_bundle": load_cached_capability_bundle,
            "load_cached_knowledge_review_queue": load_cached_knowledge_review_queue,
            "load_json": load_json,
            "probe_cached_official_registration": probe_cached_official_registration,
            "probe_registration": probe_registration,
            "resolve_worknet": resolve_worknet,
            "state_context": state_context,
            "summarize_knowledge_review_queue": summarize_knowledge_review_queue,
        },
    )


def build_start_response_from_preflight(
    preflight: Any,
    *,
    state: Optional[dict[str, Any]] = None,
    knowledge_catalog: Optional[dict[str, Any]] = None,
    cached_bundle: Optional[dict[str, Any]] = None,
    persist: bool = False,
) -> dict[str, Any]:
    return build_start_response_from_preflight_payload(
        preflight,
        state=state,
        knowledge_catalog=knowledge_catalog,
        cached_bundle=cached_bundle,
        persist=persist,
        dependencies={
            "action_details_from_ui_actions": action_details_from_ui_actions,
            "align_run_execution_user_message": align_run_execution_user_message,
            "aggregate_background_supervisor_view": aggregate_background_supervisor_view,
            "annotate_execution_actions": annotate_execution_actions,
            "append_user_action": append_user_action,
            "atomic_write_json": atomic_write_json,
            "background_observations_from_run": background_observations_from_run,
            "build_capability_bundle": build_capability_bundle,
            "build_preflight_plain_language_summary": build_preflight_plain_language_summary,
            "build_preflight_report": build_preflight_report,
            "build_resume_recovery_briefing": build_resume_recovery_briefing,
            "derive_execution_state": derive_execution_state,
            "ensure_user_preferences": ensure_user_preferences,
            "humanize_public_action_entries": humanize_public_action_entries,
            "humanize_public_recovery_decision": humanize_public_recovery_decision,
            "humanize_recovery_stale_reason": humanize_recovery_stale_reason,
            "humanize_runtime_guidance_message": humanize_runtime_guidance_message,
            "humanize_worknet_switch_summary": humanize_worknet_switch_summary,
            "knowledge_focus_topics_payload": knowledge_focus_topics_payload,
            "knowledge_reference_highlights_payload": knowledge_reference_highlights_payload,
            "knowledge_source_highlights_payload": knowledge_source_highlights_payload,
            "load_cached_capability_bundle": load_cached_capability_bundle,
            "load_json": load_json,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "maybe_promote_recovery_decision": maybe_promote_recovery_decision,
            "merge_recovery_decision_actions": merge_recovery_decision_actions,
            "prioritize_ui_actions": prioritize_ui_actions,
            "progress_message": progress_message,
            "recommend_worknet_actions": recommend_worknet_actions,
            "recovery_status_display": recovery_status_display,
            "resolve_worknet": resolve_worknet,
            "review_background_action_label": review_background_action_label,
            "run_worknet_command": run_worknet_command,
            "runtime_follow_up_description": runtime_follow_up_description,
            "state_context": state_context,
            "workstation_background_command": workstation_background_command,
            "workstation_confirmation_command": workstation_confirmation_command,
            "workstation_follow_up_command": workstation_follow_up_command,
            "workstation_pause_command": workstation_pause_command,
            "workstation_status_command": workstation_status_command,
        },
    )


def build_start_response() -> dict[str, Any]:
    state = state_context()
    preflight = build_preflight_report()
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    cached_bundle = load_cached_capability_bundle(state)
    payload = build_start_response_from_preflight(
        preflight,
        state=state,
        knowledge_catalog=knowledge_catalog,
        cached_bundle=cached_bundle,
        persist=True,
    )
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    latest_review = load_json(Path(state["reviews"]) / "latest-review.json", {})
    pending_queue = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    persist_workstation_state_summary(
        build_workstation_state_summary(
            latest_run=latest_run,
            latest_review=latest_review,
            status_report={
                "headline": payload.get("user_message"),
                "status": preflight.get("nextAction"),
                "resumeStatus": payload.get("resumeStatus"),
                "executionState": payload.get("executionState"),
                "executionStateDisplay": payload.get("executionStateDisplay"),
                "executionHeadline": payload.get("executionHeadline"),
                "worknetKey": preflight.get("recovery", {}).get("lastWorknetKey") if isinstance(preflight.get("recovery"), dict) else None,
                "worknetName": preflight.get("recovery", {}).get("lastWorknetName") if isinstance(preflight.get("recovery"), dict) else None,
                "primaryUserAction": payload.get("primaryUserAction"),
                "primaryUserActionCommand": payload.get("primaryUserActionCommand"),
                "userActions": [item.get("label") for item in payload.get("user_actions", []) if isinstance(item, dict)],
            },
            active_background=[
                summarize_background_record(item, tail_lines=30)
                for item in load_active_processes(state)
                if isinstance(item, dict)
            ],
            pending_confirmations=pending_queue,
            monitor_report=load_json(Path(state["cache"]) / "workstation-monitor.json", {}),
        ),
        state=state,
    )
    return payload


def build_work_playbook(worknet_identifier: str) -> dict[str, Any]:
    return build_work_playbook_payload(
        worknet_identifier,
        dependencies={
            "annotate_execution_actions": annotate_execution_actions,
            "annotate_playbook_commands": annotate_playbook_commands,
            "append_unique_text": append_unique_text,
            "atomic_write_json": atomic_write_json,
            "build_manifest_commands": build_manifest_commands,
            "build_playbook_user_action_details": build_playbook_user_action_details,
            "build_skill_inspect_command": build_skill_inspect_command,
            "build_skill_sync_command": build_skill_sync_command,
            "build_source_inventory": build_source_inventory,
            "canonical_worknet_caution_text": canonical_worknet_caution_text,
            "canonical_worknet_loop_text": canonical_worknet_loop_text,
            "capability_knowledge_caveat": capability_knowledge_caveat,
            "compact_knowledge_context": compact_knowledge_context,
            "dedupe_action_entries": dedupe_action_entries,
            "dedupe_playbook_commands": dedupe_playbook_commands,
            "derive_playbook_execution_state": derive_playbook_execution_state,
            "ensure_user_preferences": ensure_user_preferences,
            "humanize_playbook_confirmation_item": humanize_playbook_confirmation_item,
            "humanize_playbook_failure_mode": humanize_playbook_failure_mode,
            "humanize_playbook_goal": humanize_playbook_goal,
            "humanize_playbook_loop": humanize_playbook_loop,
            "humanize_playbook_role": humanize_playbook_role,
            "humanize_playbook_success_metric": humanize_playbook_success_metric,
            "inspect_skill_runtime": inspect_skill_runtime,
            "knowledge_action_description": knowledge_action_description,
            "knowledge_context_for_worknet": knowledge_context_for_worknet,
            "knowledge_refresh_action_description": knowledge_refresh_action_description,
            "knowledge_related_reference_highlights": knowledge_related_reference_highlights,
            "knowledge_related_source_highlights": knowledge_related_source_highlights,
            "knowledge_source_action_description": knowledge_source_action_description,
            "knowledge_source_labels_text": knowledge_source_labels_text,
            "knowledge_worknet_metadata": knowledge_worknet_metadata,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "now_iso": now_iso,
            "official_remote_manifest": official_remote_manifest,
            "resolve_skill_root": resolve_skill_root,
            "resolve_worknet": resolve_worknet,
            "rewrite_command_for_skill_root": rewrite_command_for_skill_root,
            "skill_registry_from_inventory": skill_registry_from_inventory,
            "state_context": state_context,
        },
    )


def load_playbook(
    path: Optional[str],
    worknet_identifier: Optional[str],
) -> tuple[dict[str, Any], list[str], str]:
    warnings: list[str] = []
    state = state_context()
    if path:
        payload = load_json(Path(path), None)
        if isinstance(payload, dict):
            return payload, warnings, "path"
        raise ValueError(f"playbook not found or invalid: {path}")
    if worknet_identifier:
        return build_work_playbook(worknet_identifier), warnings, "worknet"
    latest_path = Path(state["playbooks"]) / "last-selected.json"
    payload = load_json(latest_path, None)
    if isinstance(payload, dict):
        return payload, warnings, "last-selected"
    preferences = ensure_user_preferences(state)
    preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))
    if preferred_profile is not None:
        warnings.append(
            f"no last-selected playbook was found, so workstation fell back to preferredWorknet={preferred_profile['key']}"
        )
        return build_work_playbook(str(preferred_profile["key"])), warnings, "preferred-worknet"
    raise ValueError("no playbook path or worknet provided")


def runtime_guidance_from_step(
    step: dict[str, Any],
    *,
    worknet_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    resolved_worknet = str(worknet_key or step.get("worknetKey") or "").strip().lower()
    return extract_runtime_guidance_from_payload(
        step_result_payload(step),
        worknet_key=resolved_worknet or None,
    )


def synthesize_run_guidance(playbook: dict[str, Any], executed_steps: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    return synthesize_runtime_guidance(
        playbook,
        executed_steps,
        runtime_guidance_from_step=runtime_guidance_from_step,
        state_root=str(state_context()["root"]),
    )


def command_status_without_execution(command: dict[str, Any], *, execute: bool) -> str:
    policy = str(command.get("executionPolicy", "manual"))
    if command.get("requires_confirmation"):
        return "queued_for_confirmation"
    if not command.get("argv"):
        return "missing_runtime_command"
    if execute:
        return "available_manual"
    if policy in {"probe", "setup", "primary-work"}:
        return "planned"
    return "available_manual"


def mine_reward_hint_from_guidance(guidance: Optional[dict[str, Any]]) -> Optional[str]:
    if not isinstance(guidance, dict):
        return None
    state = str(guidance.get("state") or "")
    if state == "selection_required":
        return "Mine needs a dataset selection before the worker can earn."
    message = str(guidance.get("message") or "")
    if "begin earning" in message.lower():
        return "Mine worker is ready to begin earning when idle work is available."
    return None


def reward_hints_from_run(latest_run: dict[str, Any]) -> list[str]:
    playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
    worknet_key = str(playbook.get("worknetKey") or "")
    steps = latest_run.get("executedSteps", []) if isinstance(latest_run, dict) else []
    hints: list[str] = []
    if worknet_key == "mine":
        for step in reversed(steps):
            guidance = runtime_guidance_from_step(step) if isinstance(step, dict) else None
            hint = mine_reward_hint_from_guidance(guidance)
            if hint:
                hints.append(hint)
                break
    elif worknet_key == "predict":
        for step in steps:
            payload = step_result_payload(step) if isinstance(step, dict) else None
            if not isinstance(payload, dict):
                continue
            data = payload.get("data")
            if isinstance(data, dict) and data.get("balance") not in (None, ""):
                hints.append(
                    f"Predict virtual chip balance: {data.get('balance')}."
                )
                break
    elif worknet_key == "gov":
        hints.append("Gov rewards depend on current epoch AWP Power and eligible signed participation.")
    elif worknet_key == "ardi":
        hints.append("Ardi rewards require gas-ready commit and reveal execution.")
    return hints


def format_awp_amount(value: Any, *, decimals: int = 18, places: int = 3) -> Optional[str]:
    try:
        raw = int(str(value))
    except (TypeError, ValueError):
        return None
    sign = "-" if raw < 0 else ""
    raw = abs(raw)
    base = 10 ** decimals
    whole, fraction = divmod(raw, base)
    text = f"{sign}{whole:,}"
    if places > 0:
        fraction_text = f"{fraction:0{decimals}d}"[:places].rstrip("0")
        if fraction_text:
            text += f".{fraction_text}"
    return f"{text} AWP"


def append_unique_text(items: list[str], value: Optional[str]) -> None:
    if not isinstance(value, str):
        return
    text = value.strip()
    if not text or text in items:
        return
    items.append(text)


def recent_public_earnings_samples(
    state: dict[str, Any],
    worknet_key: str,
) -> tuple[Optional[str], list[dict[str, Any]]]:
    profile = resolve_worknet(worknet_key)
    if profile is None:
        return None, []
    worknet_id = str(profile.get("worknet_id"))
    name = str(profile.get("name") or worknet_key)
    samples: list[dict[str, Any]] = []
    bundle = load_cached_capability_bundle(state)
    if isinstance(bundle, dict):
        for item in bundle.get("reports", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("worknetId")) != worknet_id:
                continue
            diagnostics = item.get("rpcDiagnostics", {})
            if isinstance(diagnostics, dict) and isinstance(diagnostics.get("earnings"), list):
                samples = [entry for entry in diagnostics.get("earnings", []) if isinstance(entry, dict)]
                break
    if not samples:
        live = load_cached_live_worknets(state)
        if isinstance(live, dict):
            for item in live.get("entries", []):
                if not isinstance(item, dict):
                    continue
                if str(item.get("worknetId")) != worknet_id:
                    continue
                if isinstance(item.get("earnings"), list):
                    samples = [entry for entry in item.get("earnings", []) if isinstance(entry, dict)]
                    break
    return name, samples


def public_earnings_hint_for_worknet(state: dict[str, Any], worknet_key: str) -> Optional[str]:
    name, samples = recent_public_earnings_samples(state, worknet_key)
    if not name or not samples:
        return None
    formatted: list[str] = []
    for sample in samples[:3]:
        text = format_awp_amount(sample.get("awp_amount"))
        if text:
            formatted.append(text)
    if not formatted:
        return None
    epochs = [sample.get("epoch_id") for sample in samples[:3] if sample.get("epoch_id") not in (None, "")]
    epoch_suffix = ""
    if epochs:
        epoch_suffix = f" Epochs: {', '.join(str(item) for item in epochs)}."
    if len(formatted) == 1:
        return f"{name} recent public earning sample: {formatted[0]}.{epoch_suffix}"
    return (
        f"{name} recent public earnings samples: {len(formatted)} entries, latest {formatted[-1]}, first {formatted[0]}."
        f"{epoch_suffix}"
    )


def background_observations_from_run(
    latest_run: dict[str, Any],
    *,
    state: dict[str, Any],
    tail_lines: int = 60,
) -> list[dict[str, Any]]:
    active_records = {
        str(item.get("label")): persist_background_observation(
            state,
            summarize_background_record(item, tail_lines=tail_lines),
        )
        for item in load_active_processes(state)
        if isinstance(item, dict) and item.get("label")
    }
    observations: list[dict[str, Any]] = []
    seen: set[str] = set()
    steps = latest_run.get("executedSteps", []) if isinstance(latest_run, dict) else []
    for step in reversed(steps):
        if not isinstance(step, dict) or step.get("status") != "started_background":
            continue
        record = step.get("backgroundProcess")
        if not isinstance(record, dict):
            continue
        label = str(record.get("label") or "")
        if not label or label in seen:
            continue
        observation = active_records.get(label) or summarize_background_record(record, tail_lines=tail_lines)
        observations.append(observation)
        seen.add(label)
    for label, observation in active_records.items():
        if label in seen:
            continue
        observations.append(observation)
    return observations


def run_response_primary_action(response: dict[str, Any]) -> Optional[str]:
    queue = normalized_confirmation_queue(response.get("confirmationQueue", []))
    if queue:
        label = queue[0].get("label")
        if isinstance(label, str) and label.strip():
            return label.strip()
    follow_up_actions = normalized_follow_up_actions(response.get("followUpActions", []))
    if follow_up_actions:
        default_follow_up = choose_default_follow_up_action(follow_up_actions) or follow_up_actions[0]
        label = default_follow_up.get("label")
        if isinstance(label, str) and label.strip():
            return label.strip()
    runtime_guidance = response.get("runtimeGuidance", {})
    if isinstance(runtime_guidance, dict):
        actions = runtime_guidance.get("userActions", [])
        if isinstance(actions, list):
            for item in actions:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    active = response.get("activeBackgroundProcesses", [])
    if isinstance(active, list) and len(active) == 1 and isinstance(active[0], dict):
        label = active[0].get("label")
        if isinstance(label, str) and label.strip():
            return f"Manage {label.strip()}"
    selected = response.get("selectedBackground")
    if isinstance(selected, dict):
        label = selected.get("label")
        if isinstance(label, str) and label.strip():
            return f"Manage {label.strip()}"
    return None


def build_run_response_briefing(
    response: dict[str, Any],
    *,
    preferences: Optional[dict[str, Any]] = None,
    recovery: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_run_response_briefing_payload(
        response,
        preferences=preferences,
        recovery=recovery,
        dependencies={
            "action_details_from_decision": action_details_from_decision,
            "align_run_execution_user_message": align_run_execution_user_message,
            "annotate_execution_actions": annotate_execution_actions,
            "append_runtime_maturity_note": append_runtime_maturity_note,
            "append_unique_action_detail": append_unique_action_detail,
            "build_recovery_decision": build_recovery_decision,
            "canonical_worknet_caution_text": canonical_worknet_caution_text,
            "canonical_worknet_loop_text": canonical_worknet_loop_text,
            "compact_knowledge_context": compact_knowledge_context,
            "derive_runtime_execution_state": derive_runtime_execution_state,
            "knowledge_action_description": knowledge_action_description,
            "knowledge_context_for_worknet": knowledge_context_for_worknet,
            "knowledge_refresh_action_description": knowledge_refresh_action_description,
            "knowledge_related_reference_highlights": knowledge_related_reference_highlights,
            "knowledge_related_source_highlights": knowledge_related_source_highlights,
            "knowledge_source_action_description": knowledge_source_action_description,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "normalized_confirmation_queue": normalized_confirmation_queue,
            "prepend_canonical_worknet_plain": prepend_canonical_worknet_plain,
            "prioritize_action_entries": prioritize_action_entries,
            "recovery_decision_actions_from_run_response": recovery_decision_actions_from_run_response,
            "recovery_status_display": recovery_status_display,
            "reporter_source_note": reporter_source_note,
            "resolve_worknet": resolve_worknet,
            "run_response_primary_action": run_response_primary_action,
            "worknet_runtime_maturity_note": worknet_runtime_maturity_note,
        },
    )


def humanize_worknet_switch_summary(profile: dict[str, Any], report: Optional[dict[str, Any]]) -> str:
    key = str(profile.get("key") or "")
    name = str(profile.get("name") or key)
    report = report or {}
    runnable = bool(report.get("runnable"))
    can_start_without_stake = report.get("canStartWithoutStake") is True
    maturity_note = worknet_runtime_maturity_note(
        worknet_key=key,
        capability_report=report,
        worknet_id=report.get("worknetId") or profile.get("worknet_id"),
        source_keys=profile.get("source_keys", []),
        install_uri=profile.get("install_uri") or profile.get("skills_uri"),
    )

    canonical = canonical_worknet_switch_summary_text(
        profile,
        runnable=runnable,
        can_start_without_stake=can_start_without_stake,
    )
    if canonical:
        return append_runtime_maturity_note(canonical, maturity_note) or canonical

    if key == "mine":
        if runnable:
            text = f"{name} can start a managed Mine worker route."
            return append_runtime_maturity_note(text, maturity_note) or text
        text = f"{name} needs runtime and dataset readiness before starting."
        return append_runtime_maturity_note(text, maturity_note) or text
    if key == "predict":
        if runnable:
            text = f"{name} can start after Predict runtime checks."
            return append_runtime_maturity_note(text, maturity_note) or text
        text = f"{name} needs context and runtime readiness before starting."
        return append_runtime_maturity_note(text, maturity_note) or text
    if key == "gov":
        if runnable:
            text = f"{name} can start after Gov public and signed-action checks."
            return append_runtime_maturity_note(text, maturity_note) or text
        text = f"{name} needs market and phase readiness before starting."
        return append_runtime_maturity_note(text, maturity_note) or text
    if key == "ardi":
        if runnable:
            text = f"{name} can proceed through preflight, commit, reveal, and inscribe checks."
            return append_runtime_maturity_note(text, maturity_note) or text
        text = f"{name} needs gas and stake readiness before starting."
        return append_runtime_maturity_note(text, maturity_note) or text
    if key == "kya":
        text = f"{name} requires identity or delegated eligibility review."
        return append_runtime_maturity_note(text, maturity_note) or text
    if key in {"tmr", "community"}:
        text = f"{name} needs skill review before execution."
        return append_runtime_maturity_note(text, maturity_note) or text
    if runnable and can_start_without_stake:
        text = f"{name} is runnable without an immediate stake gate."
        return append_runtime_maturity_note(text, maturity_note) or text
    if runnable:
        text = f"{name} is runnable."
        return append_runtime_maturity_note(text, maturity_note) or text
    reason = str(report.get("reason") or "").strip()
    if reason:
        text = f"{name}: {reason}"
        return append_runtime_maturity_note(text, maturity_note) or text
    text = f"{name} needs review before execution."
    return append_runtime_maturity_note(text, maturity_note) or text


def execute_follow_up_action(
    latest_run: dict[str, Any],
    action: dict[str, Any],
    *,
    execute: bool,
    explicit_selection: bool = False,
    state: dict[str, Any],
) -> dict[str, Any]:
    return execute_follow_up_action_payload(
        latest_run,
        action,
        execute=execute,
        explicit_selection=explicit_selection,
        state=state,
        dependencies={
            "annotate_runtime_action_payloads": annotate_runtime_action_payloads,
            "derive_runtime_execution_state": derive_runtime_execution_state,
            "extract_runtime_guidance_from_payload": extract_runtime_guidance_from_payload,
            "launch_background_command": launch_background_command,
            "now_iso": now_iso,
            "parse_json_loose": parse_json_loose,
            "persist_final_run_record": persist_final_run_record,
            "run_command": run_command,
            "sync_managed_external_processes_from_run": sync_managed_external_processes_from_run,
            "synthesize_run_guidance": synthesize_run_guidance,
            "trim_output": trim_output,
        },
    )


def continue_runtime_guidance_without_default(latest_run: dict[str, Any], *, state: dict[str, Any]) -> dict[str, Any]:
    follow_up_actions = normalized_follow_up_actions(latest_run.get("followUpActions", []))
    runtime_guidance = latest_run.get("runtimeGuidance", {}) if isinstance(latest_run, dict) else {}
    return annotate_runtime_action_payloads({
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "status": "needs_runtime_input" if follow_up_actions else "planned",
        "executedSteps": [],
        "confirmationQueue": [],
        "runtimeGuidance": runtime_guidance if isinstance(runtime_guidance, dict) else None,
        "followUpActions": follow_up_actions,
        "resumedFromState": True,
        "nextAction": "follow_runtime_guidance" if follow_up_actions else "execute_when_ready",
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })


def continue_pending_confirmations(
    latest_run: dict[str, Any],
    pending_queue: list[dict[str, Any]],
    *,
    state: dict[str, Any],
) -> dict[str, Any]:
    queue = normalized_confirmation_queue(pending_queue)
    return annotate_runtime_action_payloads({
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "status": "needs_confirmation",
        "executedSteps": [],
        "confirmationQueue": queue,
        "runtimeGuidance": None,
        "followUpActions": [],
        "resumedFromState": True,
        "nextAction": "await_confirmation",
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })


def continue_background_runs(
    latest_run: dict[str, Any],
    *,
    state: dict[str, Any],
    tail_lines: int = 40,
) -> dict[str, Any]:
    active = load_active_processes(state)
    inspected_all = [
        inspect_background_process(state, str(item.get("label")), tail_lines=tail_lines)
        for item in active
        if isinstance(item, dict)
    ]
    inspected = [item for item in inspected_all if item.get("alive") is not False]
    inactive_labels = {
        str(item.get("label"))
        for item in inspected_all
        if item.get("alive") is False and item.get("label")
    }
    if inactive_labels:
        remaining = [
            item for item in load_active_processes(state)
            if not (isinstance(item, dict) and str(item.get("label")) in inactive_labels)
        ]
        atomic_write_json(active_processes_path(state), remaining)
    summary_message = f"{len(inspected)} background process(es) inspected."
    response_status = "background_running" if inspected else "planned"
    follow_up_actions: list[dict[str, Any]] = []
    runtime_guidance_state = None
    runtime_guidance_actions: list[str] = []
    runtime_guidance_action_map: dict[str, str] = {}
    next_action = "monitor_background_run" if inspected else "execute_when_ready"
    selected_background: Optional[dict[str, Any]] = None
    if len(inspected) == 1:
        info = inspected[0].get("summary", {})
        headline = info.get("headline") if isinstance(info, dict) else None
        if isinstance(headline, str) and headline.strip():
            summary_message = headline.strip()
        supervisor = background_supervisor_view(inspected[0])
        if isinstance(supervisor, dict):
            response_status = str(supervisor.get("status") or response_status).strip() or response_status
            runtime_guidance_state = supervisor.get("state")
            supervisor_message = str(supervisor.get("message") or supervisor.get("headline") or "").strip()
            if supervisor_message:
                summary_message = supervisor_message
            next_label = str(supervisor.get("nextActionLabel") or "").strip()
            next_command = str(supervisor.get("nextActionCommand") or "").strip()
            if next_label and next_command:
                runtime_guidance_actions = [next_label]
                runtime_guidance_action_map = {next_label: next_command}
                follow_up_actions = [
                    {
                        "label": next_label,
                        "command": next_command,
                        "safeToAutoRun": False,
                        "requiresConfirmation": False,
                    }
                ]
                next_action = "follow_runtime_guidance"
        selected_background = inspected[0]
    elif len(inspected) > 1:
        aggregate = aggregate_background_supervisor_view(inspected)
        if isinstance(aggregate, dict):
            response_status = str(aggregate.get("status") or response_status).strip() or response_status
            runtime_guidance_state = aggregate.get("state")
            aggregate_message = str(aggregate.get("message") or aggregate.get("headline") or "").strip()
            if aggregate_message:
                summary_message = aggregate_message
            next_label = str(aggregate.get("nextActionLabel") or "").strip()
            next_command = str(aggregate.get("nextActionCommand") or "").strip()
            selected_label = str(aggregate.get("selectedLabel") or "").strip()
            if selected_label and not next_command:
                next_label = next_label or f"Inspect {selected_label}"
                next_command = workstation_background_command(selected_label, tail_lines=80)
            if next_label and next_command:
                runtime_guidance_actions = [next_label]
                runtime_guidance_action_map = {next_label: next_command}
                follow_up_actions = [
                    {
                        "label": next_label,
                        "command": next_command,
                        "safeToAutoRun": False,
                        "requiresConfirmation": False,
                    }
                ]
                next_action = "follow_runtime_guidance"
            if selected_label:
                selected_background = next(
                    (
                        item for item in inspected
                        if isinstance(item, dict) and str(item.get("label") or "").strip() == selected_label
                    ),
                    None,
                )
    return annotate_runtime_action_payloads({
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "status": response_status,
        "executedSteps": [],
        "confirmationQueue": [],
        "runtimeGuidance": {
            "message": summary_message if inspected else "No background process is running.",
            "userActions": runtime_guidance_actions,
            "actionMap": runtime_guidance_action_map,
            "nextCommand": None,
            "nextAction": next_action,
            "state": runtime_guidance_state,
        },
        "followUpActions": follow_up_actions,
        "activeBackgroundProcesses": inspected,
        **({"selectedBackground": selected_background} if isinstance(selected_background, dict) else {}),
        "resumedFromState": True,
        "nextAction": next_action,
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })


def execute_confirmation_action(
    latest_run: dict[str, Any],
    pending_queue: list[dict[str, Any]],
    action: dict[str, Any],
    *,
    execute: bool,
    provided_inputs: dict[str, str],
    state: dict[str, Any],
) -> dict[str, Any]:
    return execute_confirmation_action_payload(
        latest_run,
        pending_queue,
        action,
        execute=execute,
        provided_inputs=provided_inputs,
        state=state,
        dependencies={
            "annotate_runtime_action_payloads": annotate_runtime_action_payloads,
            "build_confirmation_execute_command": build_confirmation_execute_command,
            "derive_runtime_execution_state": derive_runtime_execution_state,
            "extract_runtime_guidance_from_payload": extract_runtime_guidance_from_payload,
            "normalized_confirmation_queue": normalized_confirmation_queue,
            "now_iso": now_iso,
            "parse_json_loose": parse_json_loose,
            "persist_final_run_record": persist_final_run_record,
            "render_argv": render_argv,
            "resolve_parameterized_argv": resolve_parameterized_argv,
            "run_command": run_command,
            "trim_output": trim_output,
            "workstation_confirmation_command": workstation_confirmation_command,
        },
    )


def finalize_run_response_payload(
    response: dict[str, Any],
    *,
    preferences: Optional[dict[str, Any]] = None,
    recovery: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    briefing = build_run_response_briefing(
        response,
        preferences=preferences,
        recovery=recovery,
    )
    return {
        **response,
        "headline": briefing.get("headline"),
        "userMessage": briefing.get("userMessage"),
        "resumeStatus": briefing.get("resumeStatus"),
        "resumeStatusDisplay": briefing.get("resumeStatusDisplay"),
        "executionState": briefing.get("executionState"),
        "executionStateDisplay": briefing.get("executionStateDisplay"),
        "executionHeadline": briefing.get("executionHeadline"),
        "knowledgeContext": briefing.get("knowledgeContext"),
        "knowledgeReferenceHighlights": briefing.get("knowledgeReferenceHighlights"),
        "knowledgeSourceHighlights": briefing.get("knowledgeSourceHighlights"),
        "primaryUserAction": briefing.get("primaryUserAction"),
        "primaryUserActionDisplay": briefing.get("primaryUserActionDisplay"),
        "primaryUserActionCommand": briefing.get("primaryUserActionCommand"),
        "userActionDetails": briefing.get("userActionDetails"),
        "recoveryDecision": humanize_public_recovery_decision(briefing.get("recoveryDecision")),
    }


def enrich_run_record_for_persistence(run_record: dict[str, Any], final_payload: dict[str, Any]) -> dict[str, Any]:
    persisted = dict(run_record)
    for field in [*RUN_RESPONSE_FIELDS, "activeBackgroundProcesses"]:
        if field in final_payload:
            persisted[field] = final_payload.get(field)
    return persisted


def persist_final_run_record(
    state: dict[str, Any],
    run_record: dict[str, Any],
    final_payload: dict[str, Any],
    confirmation_queue: list[dict[str, Any]],
) -> dict[str, Any]:
    persisted = enrich_run_record_for_persistence(run_record, final_payload)
    atomic_write_json(Path(state["runs"]) / "latest-run.json", persisted)
    atomic_write_json(Path(state["runs"]) / "pending-confirmations.json", confirmation_queue)
    append_jsonl(Path(state["runs"]) / "history.jsonl", persisted)
    append_timeline_event_payload(
        state,
        timeline_event_from_run_payload(
            run_record,
            final_payload,
            confirmation_queue,
            dependencies={"now_iso": now_iso},
        ),
        dependencies={
            "append_jsonl": append_jsonl,
            "now_iso": now_iso,
        },
    )
    latest_review = load_json(Path(state["reviews"]) / "latest-review.json", {})
    persist_workstation_state_summary(
        build_workstation_state_summary(
            latest_run=persisted,
            latest_review=latest_review if isinstance(latest_review, dict) else {},
            status_report={
                "headline": final_payload.get("headline"),
                "status": final_payload.get("status"),
                "resumeStatus": final_payload.get("resumeStatus"),
                "executionState": final_payload.get("executionState"),
                "executionStateDisplay": final_payload.get("executionStateDisplay"),
                "executionHeadline": final_payload.get("executionHeadline"),
                "worknetKey": final_payload.get("selectedWorknetKey"),
                "worknetName": final_payload.get("selectedWorknetName"),
                "primaryUserAction": final_payload.get("primaryUserAction"),
                "primaryUserActionCommand": final_payload.get("primaryUserActionCommand"),
                "userActions": [item.get("label") for item in final_payload.get("userActions", []) if isinstance(item, dict)],
            },
            active_background=final_payload.get("activeBackgroundProcesses", []),
            pending_confirmations=confirmation_queue,
            monitor_report=load_json(Path(state["cache"]) / "workstation-monitor.json", {}),
        ),
        state=state,
    )
    return persisted


def run_workstation(
    mode: str,
    worknet_identifier: Optional[str] = None,
    playbook_path: Optional[str] = None,
    follow_up_label: Optional[str] = None,
    confirm_label: Optional[str] = None,
    background_label: Optional[str] = None,
    stop_background_label: Optional[str] = None,
    pause: bool = False,
    tail_lines: int = 40,
    auto_advance: bool = False,
    provided_inputs: Optional[list[str]] = None,
    execute: bool = False,
) -> dict[str, Any]:
    return run_workstation_payload(
        mode,
        worknet_identifier=worknet_identifier,
        playbook_path=playbook_path,
        follow_up_label=follow_up_label,
        confirm_label=confirm_label,
        background_label=background_label,
        stop_background_label=stop_background_label,
        pause=pause,
        tail_lines=tail_lines,
        auto_advance=auto_advance,
        provided_inputs=provided_inputs,
        execute=execute,
        dependencies={
            "annotate_runtime_action_payloads": annotate_runtime_action_payloads,
            "background_supervisor_view": background_supervisor_view,
            "build_recovery_state": build_recovery_state,
            "choose_default_background_process": choose_default_background_process,
            "choose_default_follow_up_action": choose_default_follow_up_action,
            "command_status_without_execution": command_status_without_execution,
            "continue_background_runs": continue_background_runs,
            "continue_pending_confirmations": continue_pending_confirmations,
            "continue_runtime_guidance_without_default": continue_runtime_guidance_without_default,
            "ensure_user_preferences": ensure_user_preferences,
            "execute_confirmation_action": execute_confirmation_action,
            "execute_follow_up_action": execute_follow_up_action,
            "extract_runtime_guidance_from_payload": extract_runtime_guidance_from_payload,
            "finalize_run_response_payload": finalize_run_response_payload,
            "humanize_recovery_stale_reason": humanize_recovery_stale_reason,
            "inspect_background_process": inspect_background_process,
            "load_active_processes": load_active_processes,
            "load_json": load_json,
            "load_playbook": load_playbook,
            "normalized_confirmation_queue": normalized_confirmation_queue,
            "normalized_follow_up_actions": normalized_follow_up_actions,
            "now_iso": now_iso,
            "parse_input_assignments": parse_input_assignments,
            "parse_json_loose": parse_json_loose,
            "persist_final_run_record": persist_final_run_record,
            "resolve_worknet": resolve_worknet,
            "run_command": run_command,
            "state_context": state_context,
            "stop_background_process": stop_background_process,
            "sync_managed_external_processes_from_run": sync_managed_external_processes_from_run,
            "synthesize_run_guidance": synthesize_run_guidance,
            "trim_output": trim_output,
        },
    )


def build_epoch_review_from_run(
    latest_run: Any,
    pending_queue: Any,
    *,
    state: Optional[dict[str, Any]] = None,
    knowledge_catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_epoch_review_from_run_payload(
        latest_run,
        pending_queue,
        state=state,
        knowledge_catalog=knowledge_catalog,
        dependencies={
            "annotate_execution_actions": annotate_execution_actions,
            "append_unique_action_detail": append_unique_action_detail,
            "append_unique_text": append_unique_text,
            "background_observations_from_run": background_observations_from_run,
            "background_strategy_change_from_summary": background_strategy_change_from_summary,
            "build_daily_summary": build_daily_summary,
            "build_reporter_note": build_reporter_note,
            "build_review_headline": build_review_headline,
            "compact_knowledge_context": compact_knowledge_context,
            "humanize_review_action_description": humanize_review_action_description,
            "humanize_review_action_label": humanize_review_action_label,
            "humanize_review_confirmation_label": humanize_review_confirmation_label,
            "humanize_review_failure": humanize_review_failure,
            "humanize_review_status_token": humanize_review_status_token,
            "humanize_review_step": humanize_review_step,
            "humanize_review_step_label": humanize_review_step_label,
            "knowledge_action_description": knowledge_action_description,
            "knowledge_context_for_worknet": knowledge_context_for_worknet,
            "knowledge_refresh_action_description": knowledge_refresh_action_description,
            "knowledge_related_reference_highlights": knowledge_related_reference_highlights,
            "knowledge_related_source_highlights": knowledge_related_source_highlights,
            "knowledge_source_action_description": knowledge_source_action_description,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "now_iso": now_iso,
            "prioritize_review_actions": prioritize_review_actions,
            "public_earnings_hint_for_worknet": public_earnings_hint_for_worknet,
            "review_action_command": review_action_command,
            "review_all_steps_prepared": review_all_steps_prepared,
            "review_background_action_label": review_background_action_label,
            "review_runtime_safety_hint": review_runtime_safety_hint,
            "review_status_code": review_status_code,
            "review_status_display": review_status_display,
            "reward_hints_from_run": reward_hints_from_run,
            "run_worknet_command": run_worknet_command,
            "runtime_message": runtime_message,
            "runtime_payload_error_summary": runtime_payload_error_summary,
            "runtime_payload_has_blocker": runtime_payload_has_blocker,
            "state_context": state_context,
            "step_result_payload": step_result_payload,
            "strategy_changes_from_guidance": strategy_changes_from_guidance,
            "summarize_worknet_review": summarize_worknet_review,
            "workstation_background_command": workstation_background_command,
            "workstation_confirmation_command": workstation_confirmation_command,
            "workstation_follow_up_command": workstation_follow_up_command,
            "workstation_pause_command": workstation_pause_command,
        },
    )


def build_epoch_review() -> dict[str, Any]:
    state = state_context()
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    pending_queue = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    previous_review = load_json(Path(state["reviews"]) / "latest-review.json", {})
    review = build_epoch_review_from_run(
        latest_run,
        pending_queue,
        state=state,
        knowledge_catalog=knowledge_catalog,
    )
    atomic_write_json(Path(state["reviews"]) / "latest-review.json", review)
    if {
        key: review.get(key)
        for key in ("status", "headline", "dailySummary", "primaryUserAction", "workDone", "failures", "strategyChanges")
    } != {
        key: previous_review.get(key)
        for key in ("status", "headline", "dailySummary", "primaryUserAction", "workDone", "failures", "strategyChanges")
    }:
        append_timeline_event_payload(
            state,
            timeline_event_from_review_payload(
                review,
                dependencies={"now_iso": now_iso},
            ),
            dependencies={
                "append_jsonl": append_jsonl,
                "now_iso": now_iso,
            },
        )
    persist_workstation_state_summary(
        build_workstation_state_summary(
            latest_run=latest_run,
            latest_review=review,
            status_report={
                "headline": review.get("headline"),
                "status": review.get("status"),
                "resumeStatus": review.get("resumeStatus"),
                "executionState": review.get("executionState"),
                "executionStateDisplay": review.get("executionStateDisplay"),
                "executionHeadline": review.get("executionHeadline"),
                "worknetKey": review.get("worknetKey"),
                "worknetName": review.get("worknetName"),
                "primaryUserAction": review.get("primaryUserAction"),
                "primaryUserActionCommand": review.get("primaryUserActionCommand"),
                "userActions": review.get("userActions"),
            },
            active_background=background_observations_from_run(latest_run, state=state),
            pending_confirmations=pending_queue,
            monitor_report=load_json(Path(state["cache"]) / "workstation-monitor.json", {}),
        ),
        state=state,
    )
    return review


def build_timeline_view(*, limit: int = 20, state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    state = state or state_context()
    return build_timeline_view_payload(
        state=state,
        limit=limit,
        dependencies={"now_iso": now_iso},
    )


def build_workstation_monitor(
    *,
    read_only: bool = False,
    timeline_limit: int = 12,
) -> dict[str, Any]:
    report = build_workstation_monitor_payload(
        read_only=read_only,
        timeline_limit=timeline_limit,
        dependencies={
            "atomic_write_json": atomic_write_json,
            "aggregate_background_supervisor_view": aggregate_background_supervisor_view,
            "background_supervisor_view": background_supervisor_view,
            "build_epoch_review": build_epoch_review,
            "build_timeline_view": build_timeline_view,
            "build_workstation_state_summary": build_workstation_state_summary,
            "build_workstation_status": build_workstation_status,
            "ensure_user_preferences": ensure_user_preferences,
            "load_active_processes": load_active_processes,
            "load_cached_workstation_state_summary": load_cached_workstation_state_summary,
            "load_json": load_json,
            "load_user_preferences": load_user_preferences,
            "now_iso": now_iso,
            "parse_iso_datetime": parse_iso_datetime,
            "persist_background_observation": persist_background_observation,
            "state_context": state_context,
            "summarize_background_record": summarize_background_record,
        },
    )
    if not read_only and isinstance(report.get("stateSummary"), dict):
        persist_workstation_state_summary(report["stateSummary"])
    return report


def record_workstation_monitor_delivery(
    report: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state_context()
    updated = record_workstation_monitor_delivery_payload(
        report,
        state=state,
        dependencies={
            "atomic_write_json": atomic_write_json,
            "load_json": load_json,
            "now_iso": now_iso,
            "state_context": state_context,
        },
    )
    append_timeline_event_payload(
        state,
        timeline_event_from_monitor_payload(
            updated,
            dependencies={"now_iso": now_iso},
        ),
        dependencies={
            "append_jsonl": append_jsonl,
            "now_iso": now_iso,
        },
    )
    return updated


def build_workstation_notification_delivery(
    report: dict[str, Any],
    *,
    adapter_key: str,
    webhook_url: Optional[str] = None,
    email_to: Optional[str] = None,
) -> dict[str, Any]:
    return build_notification_delivery_payload(
        report,
        adapter_key=adapter_key,
        webhook_url=webhook_url,
        email_to=email_to,
    )


def dispatch_workstation_notification(
    report: dict[str, Any],
    *,
    adapter_key: str,
    webhook_url: Optional[str] = None,
    email_to: Optional[str] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    return dispatch_monitor_notification_payload(
        report,
        adapter_key=adapter_key,
        webhook_url=webhook_url,
        email_to=email_to,
        dry_run=dry_run,
    )


def build_workstation_state_summary(
    *,
    latest_run: Any,
    latest_review: Any,
    status_report: Any,
    active_background: Any,
    pending_confirmations: Any,
    monitor_report: Any = None,
) -> dict[str, Any]:
    return build_workstation_state_summary_payload(
        latest_run=latest_run,
        latest_review=latest_review,
        status_report=status_report,
        active_background=active_background,
        pending_confirmations=pending_confirmations,
        monitor_report=monitor_report,
        dependencies={"now_iso": now_iso},
    )


def background_supervisor_view(record: Any) -> dict[str, Any]:
    return background_supervisor_snapshot(
        record,
        parse_iso_datetime=parse_iso_datetime,
    )


def aggregate_background_supervisor_view(records: Any) -> dict[str, Any]:
    return aggregate_background_supervisors(
        records,
        parse_iso_datetime=parse_iso_datetime,
    )


def load_cached_workstation_state_summary(
    *,
    state: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state or state_context()
    return load_cached_workstation_state_summary_payload(
        state,
        dependencies={"load_json": load_json},
    )


def persist_workstation_state_summary(
    summary: dict[str, Any],
    *,
    state: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state or state_context()
    return persist_workstation_state_summary_payload(
        state,
        summary,
        dependencies={"atomic_write_json": atomic_write_json},
    )


def build_workstation_status(
    *,
    query: Optional[str] = None,
    intent: Optional[str] = None,
    worknet_identifier: Optional[str] = None,
    source_identifier: Optional[str] = None,
    read_only: bool = False,
) -> dict[str, Any]:
    report = build_workstation_status_payload(
        query=query,
        intent=intent,
        worknet_identifier=worknet_identifier,
        source_identifier=source_identifier,
        read_only=read_only,
        dependencies={
            "action_details_from_ui_actions": action_details_from_ui_actions,
            "aggregate_background_supervisor_view": aggregate_background_supervisor_view,
            "align_run_execution_user_message": align_run_execution_user_message,
            "annotate_execution_actions": annotate_execution_actions,
            "annotate_research_action_details": annotate_research_action_details,
            "append_user_action": append_user_action,
            "atomic_write_json": atomic_write_json,
            "background_supervisor_view": background_supervisor_view,
            "build_capability_bundle": build_capability_bundle,
            "build_epoch_review": build_epoch_review,
            "build_knowledge_query_result": build_knowledge_query_result,
            "build_knowledge_review_queue": build_knowledge_review_queue,
            "build_playbook_command": build_playbook_command,
            "build_research_action_groups": build_research_action_groups,
            "build_resume_recovery_briefing": build_resume_recovery_briefing,
            "build_source_query_result": build_source_query_result,
            "build_start_response": build_start_response,
            "build_workstation_state_summary": build_workstation_state_summary,
            "derive_execution_state": derive_execution_state,
            "detect_source_from_text": detect_source_from_text,
            "detect_worknet_from_text": detect_worknet_from_text,
            "direct_knowledge_topic_from_research_text": direct_knowledge_topic_from_research_text,
            "ensure_user_preferences": ensure_user_preferences,
            "execution_state_payload": execution_state_payload,
            "find_topic_directory_entry": find_topic_directory_entry,
            "frontload_user_action_labels": frontload_user_action_labels,
            "humanize_knowledge_source_label": humanize_knowledge_source_label,
            "humanize_public_action_entries": humanize_public_action_entries,
            "humanize_public_recovery_decision": humanize_public_recovery_decision,
            "humanize_worknet_switch_summary": humanize_worknet_switch_summary,
            "knowledge_action_description": knowledge_action_description,
            "knowledge_focus_topics_payload": knowledge_focus_topics_payload,
            "knowledge_reference_highlights_payload": knowledge_reference_highlights_payload,
            "knowledge_related_source_highlights": knowledge_related_source_highlights,
            "knowledge_review_queue_note_for_target": knowledge_review_queue_note_for_target,
            "knowledge_source_action_description": knowledge_source_action_description,
            "knowledge_source_highlights_payload": knowledge_source_highlights_payload,
            "load_active_processes": load_active_processes,
            "load_cached_capability_bundle": load_cached_capability_bundle,
            "load_cached_knowledge_catalog": load_cached_knowledge_catalog,
            "load_cached_knowledge_review_queue": load_cached_knowledge_review_queue,
            "load_cached_workstation_state_summary": load_cached_workstation_state_summary,
            "load_json": load_json,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "load_user_preferences": load_user_preferences,
            "maybe_promote_recovery_decision": maybe_promote_recovery_decision,
            "merge_payload_user_action_details": merge_payload_user_action_details,
            "merge_payload_user_actions": merge_payload_user_actions,
            "merge_recovery_decision_actions": merge_recovery_decision_actions,
            "now_iso": now_iso,
            "persist_background_observation": persist_background_observation,
            "prioritize_ui_actions": prioritize_ui_actions,
            "public_earnings_hint_for_worknet": public_earnings_hint_for_worknet,
            "query_knowledge_command": query_knowledge_command,
            "recommend_worknet_actions": recommend_worknet_actions,
            "recovery_status_display": recovery_status_display,
            "resolve_worknet": resolve_worknet,
            "resolve_workstation_status_intent": resolve_workstation_status_intent,
            "review_epoch_command": review_epoch_command,
            "run_worknet_command": run_worknet_command,
            "safe_slug": safe_slug,
            "scan_worknets_command": scan_worknets_command,
            "state_context": state_context,
            "summarize_background_record": summarize_background_record,
            "summarize_knowledge_review_queue": summarize_knowledge_review_queue,
            "worknet_runtime_maturity_note": worknet_runtime_maturity_note,
            "workstation_background_command": workstation_background_command,
            "workstation_pause_command": workstation_pause_command,
            "workstation_preferences_command": workstation_preferences_command,
            "workstation_preflight_command": workstation_preflight_command,
        },
    )
    if not read_only and isinstance(report.get("stateSummary"), dict):
        persist_workstation_state_summary(report["stateSummary"])
    return report


def build_coverage_audit(
    *,
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
    source_facts: Optional[dict[str, Any]] = None,
    source_evidence: Optional[dict[str, Any]] = None,
    topic_dossiers: Optional[dict[str, Any]] = None,
    glossary: Optional[dict[str, Any]] = None,
    concept_catalog: Optional[dict[str, Any]] = None,
    skill_inspections: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_coverage_audit_payload(
        state=state,
        inventory=inventory,
        source_facts=source_facts,
        source_evidence=source_evidence,
        topic_dossiers=topic_dossiers,
        glossary=glossary,
        concept_catalog=concept_catalog,
        skill_inspections=skill_inspections,
        coverage_requirements=KNOWLEDGE_COVERAGE_REQUIREMENTS,
        generated_root=REFERENCE_EXPORT_ROOT,
        dependencies={
            "state_context": state_context,
            "build_source_inventory": build_source_inventory,
            "build_source_fact_catalog": build_source_fact_catalog,
            "build_source_evidence_catalog": build_source_evidence_catalog,
            "build_topic_dossier_catalog": build_topic_dossier_catalog,
            "build_glossary_catalog": build_glossary_catalog,
            "build_concept_catalog": build_concept_catalog,
            "load_cached_live_worknets": load_cached_live_worknets,
            "load_cached_source_drift": load_cached_source_drift,
            "load_cached_source_impact": load_cached_source_impact,
            "load_cached_knowledge_review_queue": load_cached_knowledge_review_queue,
            "load_cached_skill_inspection_catalog": load_cached_skill_inspection_catalog,
            "skill_registry_from_inventory": skill_registry_from_inventory,
            "build_registration_plan": build_registration_plan,
            "load_json": load_json,
            "build_skill_inspection_catalog": build_skill_inspection_catalog,
            "atomic_write_json": atomic_write_json,
            "write_reference_export": write_reference_export,
            "now_iso": now_iso,
        },
    )


def build_display_contract_audit(
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_display_contract_audit_payload(
        catalog=catalog,
        dependencies={
            "CITATION_DISPLAY_FIELDS": CITATION_DISPLAY_FIELDS,
            "CONCEPT_DIRECTORY_ITEM_FIELDS": CONCEPT_DIRECTORY_ITEM_FIELDS,
            "DOSSIER_DISPLAY_FIELDS": DOSSIER_DISPLAY_FIELDS,
            "DRIFT_DISPLAY_FIELDS": DRIFT_DISPLAY_FIELDS,
            "FRESHNESS_DISPLAY_FIELDS": FRESHNESS_DISPLAY_FIELDS,
            "FRESHNESS_ITEM_FIELDS": FRESHNESS_ITEM_FIELDS,
            "RUNTIME_PROBE_EVIDENCE_FIELDS": RUNTIME_PROBE_EVIDENCE_FIELDS,
            "SOURCE_FACT_DISPLAY_FIELDS": SOURCE_FACT_DISPLAY_FIELDS,
            "SOURCE_IMPACT_DISPLAY_FIELDS": SOURCE_IMPACT_DISPLAY_FIELDS,
            "SOURCE_IMPACT_ITEM_FIELDS": SOURCE_IMPACT_ITEM_FIELDS,
            "SOURCE_RECORD_DISPLAY_FIELDS": SOURCE_RECORD_DISPLAY_FIELDS,
            "WORKNET_DISPLAY_FIELDS": WORKNET_DISPLAY_FIELDS,
            "build_changed_sources_query_result": build_changed_sources_query_result,
            "build_knowledge_query_result": build_knowledge_query_result,
            "build_source_query_result": build_source_query_result,
            "knowledge_display_changed_sources": knowledge_display_changed_sources,
            "knowledge_display_drift_item": knowledge_display_drift_item,
            "knowledge_display_source_impact": knowledge_display_source_impact,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "now_iso": now_iso,
            "query_knowledge_command": query_knowledge_command,
            "query_source_command": query_source_command,
            "seed_verification_state_from_reference_exports": seed_verification_state_from_reference_exports,
            "state_context": state_context,
        },
    )


def build_glossary_query_result(
    term: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_glossary_query_result_payload(
        term,
        catalog=catalog,
        dependencies={
            "GLOSSARY_QUERY_FIELDS": GLOSSARY_QUERY_FIELDS,
            "build_glossary_catalog": build_glossary_catalog,
            "normalize_glossary_item_payload": normalize_glossary_item_payload,
            "normalize_glossary_query_match_payload": normalize_glossary_query_match_payload,
            "normalize_query_payload": normalize_query_payload,
        },
    )


def build_query_contract_audit(
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_query_contract_audit_payload(
        catalog=catalog,
        dependencies={
            "CHANGED_SOURCES_QUERY_FIELDS": CHANGED_SOURCES_QUERY_FIELDS,
            "CONCEPT_DIRECTORY_ITEM_FIELDS": CONCEPT_DIRECTORY_ITEM_FIELDS,
            "GLOSSARY_ITEM_FIELDS": GLOSSARY_ITEM_FIELDS,
            "GLOSSARY_QUERY_FIELDS": GLOSSARY_QUERY_FIELDS,
            "GLOSSARY_QUERY_MATCH_FIELDS": GLOSSARY_QUERY_MATCH_FIELDS,
            "KNOWLEDGE_ATLAS_GAP_FIELDS": KNOWLEDGE_ATLAS_GAP_FIELDS,
            "KNOWLEDGE_ATLAS_QUERY_FIELDS": KNOWLEDGE_ATLAS_QUERY_FIELDS,
            "KNOWLEDGE_DIRECTORY_ENTRY_FIELDS": KNOWLEDGE_DIRECTORY_ENTRY_FIELDS,
            "KNOWLEDGE_OVERVIEW_FIELDS": KNOWLEDGE_OVERVIEW_FIELDS,
            "KNOWLEDGE_QUERY_FIELDS": KNOWLEDGE_QUERY_FIELDS,
            "KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS": KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS,
            "REVIEW_SCOPE_FIELDS": REVIEW_SCOPE_FIELDS,
            "SOURCE_DIRECTORY_ENTRY_FIELDS": SOURCE_DIRECTORY_ENTRY_FIELDS,
            "SOURCE_QUERY_FIELDS": SOURCE_QUERY_FIELDS,
            "build_changed_sources_query_result": build_changed_sources_query_result,
            "build_glossary_query_result": build_glossary_query_result,
            "build_knowledge_query_result": build_knowledge_query_result,
            "build_source_query_result": build_source_query_result,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "now_iso": now_iso,
            "seed_verification_state_from_reference_exports": seed_verification_state_from_reference_exports,
            "state_context": state_context,
        },
    )


def build_public_contract_audit() -> dict[str, Any]:
    return build_public_contract_audit_payload(
        dependencies={
            "CAPABILITY_PUBLIC_FIELDS": CAPABILITY_PUBLIC_FIELDS,
            "PLAYBOOK_COMMAND_PUBLIC_FIELDS": PLAYBOOK_COMMAND_PUBLIC_FIELDS,
            "PLAYBOOK_PUBLIC_FIELDS": PLAYBOOK_PUBLIC_FIELDS,
            "PREFLIGHT_PUBLIC_FIELDS": PREFLIGHT_PUBLIC_FIELDS,
            "PUBLIC_ACTION_FIELDS": PUBLIC_ACTION_FIELDS,
            "REVIEW_PUBLIC_FIELDS": REVIEW_PUBLIC_FIELDS,
            "RUN_RESPONSE_FIELDS": RUN_RESPONSE_FIELDS,
            "START_RESPONSE_FIELDS": START_RESPONSE_FIELDS,
            "USER_ACTION_DETAIL_FIELDS": USER_ACTION_DETAIL_FIELDS,
            "WORKSTATION_STATUS_INTERNAL_FIELDS": WORKSTATION_STATUS_INTERNAL_FIELDS,
            "WORKSTATION_STATUS_PUBLIC_FIELDS": WORKSTATION_STATUS_PUBLIC_FIELDS,
            "annotate_runtime_action_payloads": annotate_runtime_action_payloads,
            "build_capability_bundle": build_capability_bundle,
            "build_epoch_review": build_epoch_review,
            "build_epoch_review_from_run": build_epoch_review_from_run,
            "build_preflight_report": build_preflight_report,
            "build_start_response": build_start_response,
            "build_start_response_from_preflight": build_start_response_from_preflight,
            "build_work_playbook": build_work_playbook,
            "build_workstation_status": build_workstation_status,
            "finalize_run_response_payload": finalize_run_response_payload,
            "load_or_build_knowledge_catalog": load_or_build_knowledge_catalog,
            "now_iso": now_iso,
            "public_capability_view": public_capability_view,
            "public_playbook_view": public_playbook_view,
            "public_preflight_view": public_preflight_view,
            "public_review_view": public_review_view,
            "public_workstation_status_view": public_workstation_status_view,
            "resolve_worknet": resolve_worknet,
            "run_workstation": run_workstation,
            "seed_verification_state_from_reference_exports": seed_verification_state_from_reference_exports,
            "state_context": state_context,
        },
    )


def build_branch_contract_audit() -> dict[str, Any]:
    return build_branch_contract_audit_payload(
        dependencies={
            "BACKGROUND_RECORD_FIELDS": BACKGROUND_RECORD_FIELDS,
            "BACKGROUND_SUMMARY_FIELDS": BACKGROUND_SUMMARY_FIELDS,
            "CONFIRMATION_QUEUE_ITEM_FIELDS": CONFIRMATION_QUEUE_ITEM_FIELDS,
            "CONFIRMED_ACTION_FIELDS": CONFIRMED_ACTION_FIELDS,
            "EXECUTED_STEP_FIELDS": EXECUTED_STEP_FIELDS,
            "EXECUTED_STEP_RESULT_DISPLAY_FIELDS": EXECUTED_STEP_RESULT_DISPLAY_FIELDS,
            "EXECUTED_STEP_STDOUT_DISPLAY_FIELDS": EXECUTED_STEP_STDOUT_DISPLAY_FIELDS,
            "FOLLOW_UP_ACTION_FIELDS": FOLLOW_UP_ACTION_FIELDS,
            "PARAMETER_SCHEMA_ITEM_FIELDS": PARAMETER_SCHEMA_ITEM_FIELDS,
            "RECOVERY_DECISION_FIELDS": RECOVERY_DECISION_FIELDS,
            "RESUME_RECOVERY_BRIEFING_FIELDS": RESUME_RECOVERY_BRIEFING_FIELDS,
            "REVIEW_PUBLIC_FIELDS": REVIEW_PUBLIC_FIELDS,
            "RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS": RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS,
            "RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS": RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            "RUN_RESPONSE_BRIEFING_FIELDS": RUN_RESPONSE_BRIEFING_FIELDS,
            "SELECTED_BACKGROUND_ERROR_FIELDS": SELECTED_BACKGROUND_ERROR_FIELDS,
            "SELECTED_BACKGROUND_PREVIEW_FIELDS": SELECTED_BACKGROUND_PREVIEW_FIELDS,
            "SELECTED_CONFIRMATION_FIELDS": SELECTED_CONFIRMATION_FIELDS,
            "USER_ACTION_DETAIL_FIELDS": USER_ACTION_DETAIL_FIELDS,
            "annotate_background_record": annotate_background_record,
            "annotate_parameter_schema_items": annotate_parameter_schema_items,
            "annotate_probe_result_display": annotate_probe_result_display,
            "annotate_raw_confirmation_queue": annotate_raw_confirmation_queue,
            "annotate_raw_follow_up_actions": annotate_raw_follow_up_actions,
            "annotate_runtime_action_payloads": annotate_runtime_action_payloads,
            "annotate_runtime_guidance_payload": annotate_runtime_guidance_payload,
            "annotate_selected_confirmation": annotate_selected_confirmation,
            "build_epoch_review_from_run": build_epoch_review_from_run,
            "build_executed_step_result_display": build_executed_step_result_display,
            "build_knowledge_query_result": build_knowledge_query_result,
            "build_resume_recovery_briefing": build_resume_recovery_briefing,
            "build_run_response_briefing": build_run_response_briefing,
            "build_start_response": build_start_response,
            "build_workstation_status": build_workstation_status,
            "humanize_public_recovery_decision": humanize_public_recovery_decision,
            "now_iso": now_iso,
            "public_review_view": public_review_view,
            "run_workstation": run_workstation,
            "state_context": state_context,
            "summarize_background_log": summarize_background_log,
        },
    )


def build_meta_contract_audit() -> dict[str, Any]:
    state = state_context()
    seed_verification_state_from_reference_exports(state)
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    suites = [
        {
            "key": "public-contract-audit",
            "title": "Public contract audit",
            "audit": build_public_contract_audit(),
        },
        {
            "key": "branch-contract-audit",
            "title": "Branch contract audit",
            "audit": build_branch_contract_audit(),
        },
        {
            "key": "query-contract-audit",
            "title": "Query contract audit",
            "audit": build_query_contract_audit(catalog=knowledge_catalog),
        },
        {
            "key": "display-contract-audit",
            "title": "Display contract audit",
            "audit": build_display_contract_audit(catalog=knowledge_catalog),
        },
    ]

    suite_items: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    all_green = True
    for suite in suites:
        audit = suite["audit"] if isinstance(suite, dict) else {}
        summary = audit.get("summary", {}) if isinstance(audit, dict) else {}
        partial = int(summary.get("partial", 0) or 0)
        missing = int(summary.get("missing", 0) or 0)
        covered = int(summary.get("covered", 0) or 0)
        status = "covered" if partial == 0 and missing == 0 else ("missing" if missing else "partial")
        if status != "covered":
            all_green = False
        suite_items.append(
            {
                "key": suite["key"],
                "title": suite["title"],
                "status": status,
                "summary": {
                    "covered": covered,
                    "partial": partial,
                    "missing": missing,
                },
                "generatedAt": audit.get("generatedAt") if isinstance(audit, dict) else None,
            }
        )
        for item in audit.get("items", []) if isinstance(audit, dict) and isinstance(audit.get("items"), list) else []:
            if not isinstance(item, dict) or item.get("status") == "covered":
                continue
            unresolved.append(
                {
                    "suiteKey": suite["key"],
                    "suiteTitle": suite["title"],
                    "key": item.get("key"),
                    "title": item.get("title"),
                    "status": item.get("status"),
                    "sampleRef": item.get("sampleRef"),
                    "missingFields": item.get("missingFields", [])[:10],
                    "extraFields": item.get("extraFields", [])[:10],
                    "reasons": item.get("reasons", [])[:3],
                    "evidenceFiles": item.get("evidenceFiles", [])[:5],
                }
            )

    payload = {
        "generatedAt": now_iso(),
        "status": "covered" if all_green else "needs_attention",
        "summary": {
            "suiteCount": len(suite_items),
            "coveredSuites": sum(1 for item in suite_items if item["status"] == "covered"),
            "partialSuites": sum(1 for item in suite_items if item["status"] == "partial"),
            "missingSuites": sum(1 for item in suite_items if item["status"] == "missing"),
            "unresolvedCount": len(unresolved),
        },
        "suites": suite_items,
        "unresolved": unresolved,
    }
    atomic_write_json(Path(state["cache"]) / "contract-audit.json", payload)
    write_reference_export("contract-audit.json", payload)
    return payload


def build_python_compile_audit() -> dict[str, Any]:
    scripts_root = SKILL_ROOT / "scripts"
    records: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="awp-workstation-pyc-") as temp_dir:
        temp_root = Path(temp_dir)
        for path in sorted(scripts_root.glob("*.py")):
            rel = path.relative_to(SKILL_ROOT)
            target = temp_root / rel.with_suffix(".pyc")
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                py_compile.compile(str(path), cfile=str(target), doraise=True)
                records.append(
                    {
                        "path": str(rel),
                        "status": "covered",
                        "error": None,
                    }
                )
            except py_compile.PyCompileError as exc:
                message = str(exc).strip()
                item = {
                    "path": str(rel),
                    "status": "missing",
                    "error": message,
                }
                records.append(item)
                failed.append(item)
    payload = {
        "generatedAt": now_iso(),
        "status": "covered" if not failed else "missing",
        "summary": {
            "covered": len(records) - len(failed),
            "missing": len(failed),
            "total": len(records),
        },
        "items": records,
    }
    return payload


def build_verification_audit() -> dict[str, Any]:
    state = state_context()
    seed_verification_state_from_reference_exports(state)
    compile_audit = build_python_compile_audit()
    contract_audit = build_meta_contract_audit()
    contract_suite_status = "covered" if contract_audit.get("status") == "covered" else "partial"
    suites = [
        {
            "key": "python-compile",
            "title": "Python compile audit",
            "status": compile_audit.get("status"),
            "summary": compile_audit.get("summary"),
            "generatedAt": compile_audit.get("generatedAt"),
        },
        {
            "key": "contract-audit",
            "title": "Unified contract audit",
            "status": contract_suite_status,
            "summary": contract_audit.get("summary"),
            "generatedAt": contract_audit.get("generatedAt"),
        },
    ]
    unresolved: list[dict[str, Any]] = []
    for item in compile_audit.get("items", []) if isinstance(compile_audit, dict) and isinstance(compile_audit.get("items"), list) else []:
        if not isinstance(item, dict) or item.get("status") == "covered":
            continue
        unresolved.append(
            {
                "suiteKey": "python-compile",
                "suiteTitle": "Python compile audit",
                "key": item.get("path"),
                "title": item.get("path"),
                "status": item.get("status"),
                "error": item.get("error"),
            }
        )
    for item in contract_audit.get("unresolved", []) if isinstance(contract_audit, dict) and isinstance(contract_audit.get("unresolved"), list) else []:
        if isinstance(item, dict):
            unresolved.append(item)
    status = "covered" if compile_audit.get("status") == "covered" and contract_audit.get("status") == "covered" else "needs_attention"
    payload = {
        "generatedAt": now_iso(),
        "status": status,
        "summary": {
            "suiteCount": len(suites),
            "coveredSuites": sum(1 for item in suites if item.get("status") == "covered"),
            "partialSuites": sum(1 for item in suites if item.get("status") == "partial"),
            "missingSuites": sum(1 for item in suites if item.get("status") == "missing"),
            "unresolvedCount": len(unresolved),
        },
        "suites": suites,
        "compileAudit": compile_audit,
        "contractAudit": contract_audit,
        "unresolved": unresolved,
    }
    atomic_write_json(Path(state["cache"]) / "verification-audit.json", payload)
    write_reference_export("verification-audit.json", payload)
    return payload


def build_knowledge_catalog(*, rebuild_derived: bool = False) -> dict[str, Any]:
    return build_knowledge_catalog_payload(
        rebuild_derived=rebuild_derived,
        dependencies={
            "CONCEPT_DIRECTORY_ITEM_FIELDS": CONCEPT_DIRECTORY_ITEM_FIELDS,
            "DEFAULT_RPC_URL": DEFAULT_RPC_URL,
            "KNOWLEDGE_CATALOG_SCHEMA_VERSION": KNOWLEDGE_CATALOG_SCHEMA_VERSION,
            "KNOWN_WORKNETS": KNOWN_WORKNETS,
            "OFFICIAL_SKILL_ALLOWLIST_PREFIXES": OFFICIAL_SKILL_ALLOWLIST_PREFIXES,
            "SAFETY_RULES": SAFETY_RULES,
            "annotate_knowledge_catalog_runtime_summaries": annotate_knowledge_catalog_runtime_summaries,
            "atomic_write_json": atomic_write_json,
            "build_concept_catalog": build_concept_catalog,
            "build_coverage_audit": build_coverage_audit,
            "build_glossary_catalog": build_glossary_catalog,
            "build_knowledge_overview": build_knowledge_overview,
            "build_knowledge_reference_index": build_knowledge_reference_index,
            "build_knowledge_review_queue": build_knowledge_review_queue,
            "build_knowledge_source_directory": build_knowledge_source_directory,
            "build_knowledge_topic_directory": build_knowledge_topic_directory,
            "build_knowledge_topic_index": build_knowledge_topic_index,
            "build_skill_inspection_catalog": build_skill_inspection_catalog,
            "build_source_drift_impact_report": build_source_drift_impact_report,
            "build_source_drift_report": build_source_drift_report,
            "build_source_evidence_catalog": build_source_evidence_catalog,
            "build_source_fact_catalog": build_source_fact_catalog,
            "build_source_inventory": build_source_inventory,
            "build_topic_dossier_catalog": build_topic_dossier_catalog,
            "build_topic_freshness_catalog": build_topic_freshness_catalog,
            "ensure_user_preferences": ensure_user_preferences,
            "load_cached_knowledge_review_queue": load_cached_knowledge_review_queue,
            "load_cached_source_drift": load_cached_source_drift,
            "load_cached_source_impact": load_cached_source_impact,
            "load_cached_topic_freshness": load_cached_topic_freshness,
            "now_iso": now_iso,
            "project_fields": project_fields,
            "skill_registry_from_inventory": skill_registry_from_inventory,
            "state_context": state_context,
            "write_reference_export": write_reference_export,
        },
    )


def load_cached_knowledge_catalog(state: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    state = state or state_context()
    payload = load_json(Path(state["cache"]) / "knowledge-catalog.json", None)
    if not isinstance(payload, dict):
        return None
    if payload.get("schemaVersion") != KNOWLEDGE_CATALOG_SCHEMA_VERSION:
        return None
    required_sections = (
        "sourceDrift",
        "sourceImpact",
        "topicFreshness",
        "sourceFacts",
        "sourceEvidence",
        "concepts",
        "topicDossiers",
        "knowledgeOverview",
        "topicIndex",
        "topicDirectory",
        "referenceIndex",
        "sourceDirectory",
        "conceptDirectory",
    )
    if any(section not in payload for section in required_sections):
        return None
    return annotate_knowledge_catalog_runtime_summaries(payload)


def humanize_knowledge_source_label(text: Any) -> str:
    raw = str(text or "").strip()
    if not raw:
        return raw
    return HUMANIZED_KNOWLEDGE_SOURCE_LABELS.get(raw, HUMANIZED_KNOWLEDGE_SOURCE_LABELS.get(raw.lower(), raw))


def humanize_knowledge_source_kind(kind: Any) -> Optional[str]:
    raw = str(kind or "").strip()
    if not raw:
        return None
    return KNOWLEDGE_SOURCE_KIND_LABELS.get(raw, raw)


def humanize_knowledge_trust_tier(tier: Any) -> Optional[str]:
    try:
        value = int(tier)
    except (TypeError, ValueError):
        return None
    return KNOWLEDGE_TRUST_TIER_LABELS.get(value, str(value))


def humanize_source_changed_field(field: Any) -> str:
    raw = str(field or "").strip()
    if not raw:
        return raw
    return KNOWLEDGE_CHANGED_FIELD_LABELS.get(raw, raw)


def normalized_knowledge_display_key(text: Any) -> str:
    normalized = str(text or "").strip().lower()
    if normalized.startswith("awp "):
        normalized = normalized[4:]
    if normalized.endswith(" worknet"):
        normalized = normalized[:-8]
    return " ".join(normalized.split())


def ranked_knowledge_review_queue_entries(queue: Any, limit: int = 5) -> list[dict[str, Any]]:
    entries = queue.get("entries", []) if isinstance(queue, dict) else []
    ranked: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        ranked.append((index, item))
    ranked.sort(
        key=lambda pair: (
            -KNOWLEDGE_QUEUE_PRIORITY_RANK.get(str(pair[1].get("priority") or "low"), 0),
            KNOWLEDGE_QUEUE_KIND_ORDER.get(str(pair[1].get("kind") or ""), 99),
            pair[0],
        )
    )
    return [item for _, item in ranked[:limit]]


def knowledge_review_queue_recommendation(
    entry: Any,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    entry = entry if isinstance(entry, dict) else {}
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    display_entries = knowledge_display_review_queue_entries([entry], catalog=catalog)
    rendered = display_entries[0] if display_entries else {}
    kind = str(rendered.get("recordKind") or rendered.get("kind") or entry.get("kind") or "").strip()
    label = str(rendered.get("labelDisplay") or rendered.get("label") or entry.get("label") or entry.get("key") or "").strip()
    action_prefix = {
        "source": "Review source",
        "topic": "Review topic",
        "fact": "Review fact",
        "worknet": "Review WorkNet",
        "evidence": "Review evidence",
    }.get(kind, "Review item")
    reason = (
        knowledge_highlight_action_description(rendered, action="refresh")
        if isinstance(rendered, dict) and rendered
        else (humanize_knowledge_review_reason(str(entry.get("reason") or "").strip()) or "Review the affected knowledge entry.")
    )
    return {
        "label": f"{action_prefix}: {label}" if label else action_prefix,
        "kind": kind,
        "key": entry.get("key"),
        "priority": entry.get("priority"),
        "description": reason,
        "command": rendered.get("primaryCommand") if isinstance(rendered, dict) and rendered.get("primaryCommand") else entry.get("command"),
        "preview": rendered.get("preview") if isinstance(rendered, dict) else None,
        "recordKind": kind,
    }


def knowledge_review_queue_summary_text(summary: Any) -> str:
    summary = summary if isinstance(summary, dict) else {}
    if not summary.get("hasPendingReviews"):
        return "No pending knowledge reviews."
    text = str(summary.get("headline") or "").strip()
    highest_priority = str(summary.get("highestPriority") or "").strip()
    if highest_priority:
        text += f" Highest priority: {KNOWLEDGE_PRIORITY_LABELS.get(highest_priority, highest_priority)}."
    focus_sources = [
        humanize_knowledge_source_label(item)
        for item in summary.get("focusSources", [])
        if str(item).strip()
    ]
    focus_topics = [str(item).strip() for item in summary.get("focusTopics", []) if str(item).strip()]
    if focus_sources:
        text += f" Focus sources: {', '.join(focus_sources[:3])}."
    if focus_topics:
        text += f" Focus topics: {', '.join(focus_topics[:3])}."
    return text.strip()


def knowledge_first_non_empty(*values: object) -> Optional[str]:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def knowledge_freshness_status_display(status: Any) -> Optional[str]:
    return KNOWLEDGE_FRESHNESS_STATUS_LABELS.get(str(status or "").strip())


def knowledge_highlight_group_key(kind: Any) -> str:
    normalized = str(kind or "").strip().lower()
    return {
        "source": "sources",
        "topic": "topics",
        "worknet": "worknets",
        "reference": "references",
        "fact": "facts",
        "evidence": "evidence",
    }.get(normalized, "topics")


def build_knowledge_highlight_entry(
    *,
    kind: str,
    key: Any,
    label: Any,
    headline: Any = None,
    preview: Any = None,
    query_command: Any = None,
    primary_command: Any = None,
    freshness_status: Any = None,
    full_record_key: Any = None,
    research_group: Any = None,
    research_tier: Any = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    normalized_key = str(key or "").strip() or None
    normalized_label = str(label or normalized_key or "").strip() or None
    normalized_preview = compact_preview_text(preview, max_chars=140, max_sentences=2) if preview else None
    normalized_query_command = str(query_command or "").strip() or None
    normalized_primary_command = str(primary_command or "").strip() or None
    normalized_freshness_status = str(freshness_status or "").strip() or None
    record_key = str(full_record_key or normalized_key or "").strip() or None
    normalized_kind = str(kind or "").strip() or None
    normalized_research_group = str(research_group or knowledge_highlight_group_key(kind)).strip() or None
    normalized_research_tier = str(research_tier or "").strip() or None
    payload = {
        "recordKind": normalized_kind,
        "recordKey": record_key,
        "fullRecordKey": record_key,
        "key": normalized_key,
        "label": normalized_label,
        "headline": str(headline or "").strip() or None,
        "preview": normalized_preview,
        "command": normalized_query_command or normalized_primary_command,
        "queryCommand": normalized_query_command,
        "primaryCommand": normalized_primary_command,
        "freshnessStatus": normalized_freshness_status,
        "freshnessStatusDisplay": knowledge_freshness_status_display(normalized_freshness_status),
        "researchGroupKey": normalized_research_group,
        "researchGroupLabel": RESEARCH_HIGHLIGHT_GROUP_LABELS.get(normalized_research_group, normalized_research_group),
        "researchGroupRank": RESEARCH_HIGHLIGHT_GROUP_RANKS.get(normalized_research_group),
        "researchTier": normalized_research_tier,
        "researchTierLabel": RESEARCH_HIGHLIGHT_TIER_LABELS.get(normalized_research_tier, normalized_research_tier),
        "researchTierRank": RESEARCH_HIGHLIGHT_TIER_RANKS.get(normalized_research_tier),
    }
    if isinstance(extra, dict):
        payload.update(extra)
    return payload


def find_concept_match(concepts: Any, query: str) -> Optional[dict[str, Any]]:
    normalized_query = safe_slug(str(query or "").strip())
    if not normalized_query or not isinstance(concepts, list):
        return None
    for item in concepts:
        if not isinstance(item, dict):
            continue
        candidates = {
            safe_slug(str(item.get("key") or "").strip()),
            safe_slug(str(item.get("title") or "").strip()),
        }
        candidates.update(
            safe_slug(str(alias).strip())
            for alias in item.get("aliases", [])
            if str(alias).strip()
        )
        if normalized_query in candidates:
            return item
    return None


def find_glossary_match(terms: Any, query: str) -> Optional[dict[str, Any]]:
    normalized_query = safe_slug(str(query or "").strip())
    if not normalized_query or not isinstance(terms, list):
        return None
    for item in terms:
        if not isinstance(item, dict):
            continue
        candidates = {
            safe_slug(str(item.get("term") or "").strip()),
        }
        candidates.update(
            safe_slug(str(alias).strip())
            for alias in item.get("aliases", [])
            if str(alias).strip()
        )
        if normalized_query in candidates:
            return item
    return None


def research_query_match_candidates(query: Optional[str]) -> list[str]:
    raw = str(query or "").strip()
    if not raw:
        return []
    candidates: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        text = str(value or "").strip(" \t\r\n:-?")
        if not text:
            return
        key = safe_slug(text)
        if key in seen:
            return
        seen.add(key)
        candidates.append(text)

    add(raw)
    lowered = raw.lower()
    prefixes = [
        "research",
        "learn",
        "what is",
        "what's",
        "tell me about",
        "guide",
        "docs",
        "documentation",
        "source",
    ]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            add(raw[len(prefix):])
    return candidates


def direct_knowledge_topic_from_research_text(
    catalog: Any,
    query: Optional[str],
) -> Optional[str]:
    if not isinstance(catalog, dict):
        return None
    concepts = catalog.get("conceptDirectory", catalog.get("concepts", []))
    if not isinstance(concepts, list):
        concepts = []
    glossary_terms = catalog.get("glossary", [])
    if not isinstance(glossary_terms, list):
        glossary_terms = []
    for candidate in research_query_match_candidates(query):
        if find_concept_match(concepts, candidate):
            return candidate
    for candidate in research_query_match_candidates(query):
        if find_glossary_match(glossary_terms, candidate):
            return candidate
    return None


def build_normalized_knowledge_highlight(
    *,
    kind: str,
    fields: Optional[list[str]] = None,
    key: Any,
    label: Any,
    headline: Any = None,
    preview: Any = None,
    query_command: Any = None,
    primary_command: Any = None,
    freshness_status: Any = None,
    full_record_key: Any = None,
    research_group: Any = None,
    research_tier: Any = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload = build_knowledge_highlight_entry(
        kind=kind,
        key=key,
        label=label,
        headline=headline,
        preview=preview,
        query_command=query_command,
        primary_command=primary_command,
        freshness_status=freshness_status,
        full_record_key=full_record_key,
        research_group=research_group,
        research_tier=research_tier,
        extra=extra,
    )
    normalized_fields = knowledge_highlight_fields(kind, fields)
    return normalize_knowledge_highlight_payload(payload, normalized_fields)


def humanize_knowledge_review_reason(reason: str) -> str:
    text = str(reason or "").strip()
    if not text:
        return text
    if text == "Re-read the affected upstream source and re-check the linked topic dossiers, facts, and runtime guidance.":
        return "Review the affected source, linked dossiers, facts, and runtime guidance."
    return text


def knowledge_display_topic_label(
    topic: str,
    *,
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
) -> str:
    return knowledge_first_non_empty(
        dossier.get("title") if isinstance(dossier, dict) else None,
        worknet.get("name") if isinstance(worknet, dict) else None,
        glossary_match.get("term") if isinstance(glossary_match, dict) else None,
        source_fact.get("topic") if isinstance(source_fact, dict) else None,
        topic,
    ) or topic


def knowledge_topic_worknet_context(
    topic: str,
    *,
    dossier: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    if not isinstance(worknet, dict) or not worknet.get("key"):
        return None
    worknet_key = str(worknet.get("key") or "").strip().lower()
    dossier_key = str(dossier.get("key") or "").strip().lower() if isinstance(dossier, dict) else ""
    if worknet_key == topic or (dossier_key and dossier_key == worknet_key):
        return worknet
    return None


def knowledge_resolved_topic_key(
    topic: str,
    *,
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
) -> str:
    return knowledge_first_non_empty(
        worknet.get("key") if isinstance(worknet, dict) else None,
        dossier.get("key") if isinstance(dossier, dict) else None,
        glossary_match.get("term") if isinstance(glossary_match, dict) else None,
        topic,
    ) or topic


def knowledge_topic_plain_language(
    *,
    narrative: Optional[dict[str, str]],
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
) -> Optional[str]:
    source_facts = source_fact.get("facts", []) if isinstance(source_fact, dict) else []
    return knowledge_first_non_empty(
        narrative.get("plain") if isinstance(narrative, dict) else None,
        glossary_match.get("plainLanguage") if isinstance(glossary_match, dict) else None,
        dossier.get("summary") if isinstance(dossier, dict) else None,
        source_facts[0] if isinstance(source_facts, list) and source_facts else None,
        glossary_match.get("definition") if isinstance(glossary_match, dict) else None,
        worknet.get("goal") if isinstance(worknet, dict) else None,
    )


def knowledge_freshness_affected_items(freshness: Any) -> list[dict[str, Any]]:
    if not isinstance(freshness, dict):
        return []
    items = freshness.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict) and item.get("status") == "affected"]


def knowledge_topic_headline(label: str, freshness: Any) -> str:
    if knowledge_freshness_affected_items(freshness):
        return f"{label} review required"
    return f"{label} ready"


def knowledge_topic_summary(
    label: str,
    *,
    narrative: Optional[dict[str, str]],
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
    freshness: Any,
) -> str:
    parts: list[str] = []
    plain = knowledge_topic_plain_language(
        narrative=narrative,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet,
    )
    if plain:
        parts.append(plain)
    why_it_matters = knowledge_first_non_empty(
        narrative.get("why") if isinstance(narrative, dict) else None,
        glossary_match.get("whyItMatters") if isinstance(glossary_match, dict) else None,
        dossier.get("whyItExists") if isinstance(dossier, dict) else None,
    )
    if why_it_matters:
        parts.append(why_it_matters)
    if isinstance(worknet, dict) and worknet:
        automation = KNOWLEDGE_AUTOMATION_LABELS.get(str(worknet.get("automationLevel") or "").strip())
        risk = KNOWLEDGE_RISK_LABELS.get(str(worknet.get("riskLevel") or "").strip())
        loop_text = knowledge_first_non_empty(
            narrative.get("loop") if isinstance(narrative, dict) else None,
            (f"Loop: {worknet.get('loop')}" if knowledge_first_non_empty(worknet.get("loop")) else None),
        )
        posture = None
        if automation and risk:
            posture = f"WorkNet posture: {automation}; risk: {risk}."
        elif automation:
            posture = f"WorkNet posture: {automation}."
        elif risk:
            posture = f"WorkNet risk: {risk}."
        parts.extend([item for item in (loop_text, posture) if item])
    affected = knowledge_freshness_affected_items(freshness)
    if affected:
        affected_labels: list[str] = []
        seen_labels: set[str] = set()
        source_names: list[str] = []
        seen_sources: set[str] = set()
        for item in affected:
            label_text = str(item.get("label") or item.get("key") or "").strip()
            normalized_label = normalized_knowledge_display_key(label_text)
            if label_text and normalized_label and normalized_label not in seen_labels:
                seen_labels.add(normalized_label)
                affected_labels.append(label_text)
            for impact in item.get("impactItems", []):
                if not isinstance(impact, dict):
                    continue
                source_name = humanize_knowledge_source_label(impact.get("sourceName") or impact.get("sourceKey"))
                normalized_source = normalized_knowledge_display_key(source_name)
                if source_name and normalized_source and normalized_source not in seen_sources:
                    seen_sources.add(normalized_source)
                    source_names.append(source_name)
        detail = f"Affected entries: {', '.join(affected_labels[:3])}."
        if source_names:
            detail += f" Changed sources: {', '.join(source_names[:3])}."
        parts.append(detail)
    else:
        parts.append("No source drift currently affects this topic.")
    caution = knowledge_first_non_empty(narrative.get("caution") if isinstance(narrative, dict) else None)
    if caution:
        parts.append(caution)
    return humanize_knowledge_display_text(" ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())) or ""


def knowledge_topic_citations(
    evidence_matches: list[dict[str, Any]],
    *,
    source_records: dict[str, dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in evidence_matches[:limit]:
        if not isinstance(item, dict):
            continue
        source_key = str(item.get("sourceKey") or "").strip()
        claim = str(item.get("claim") or "").strip()
        key = (source_key, claim)
        if not source_key or not claim or key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "sourceKey": source_key,
                "sourceName": item.get("sourceName"),
                "url": item.get("sourceUrl"),
                "locator": item.get("locator"),
                "claim": claim,
                "evidenceType": item.get("evidenceType"),
                "stability": item.get("stability"),
            }
        )
    if citations:
        return citations
    if isinstance(dossier, dict):
        for source_key in dossier.get("sourceKeys", [])[:limit]:
            source_record = source_records.get(str(source_key), {})
            citations.append(
                {
                    "sourceKey": source_key,
                    "sourceName": source_record.get("name"),
                    "url": source_record.get("url"),
                    "locator": None,
                    "claim": None,
                    "evidenceType": source_record.get("kind"),
                    "stability": None,
                }
            )
    return citations


KNOWLEDGE_DISPLAY_OVERRIDES: dict[str, Any] = load_knowledge_display_overrides()
KNOWLEDGE_DOSSIER_DISPLAY_OVERRIDES: dict[str, dict[str, Any]] = KNOWLEDGE_DISPLAY_OVERRIDES.get("dossiers", {})
KNOWLEDGE_SOURCE_FACT_DISPLAY_OVERRIDES: dict[str, list[str]] = KNOWLEDGE_DISPLAY_OVERRIDES.get("sourceFacts", {})
KNOWLEDGE_EVIDENCE_DISPLAY_OVERRIDES: dict[str, dict[str, str]] = KNOWLEDGE_DISPLAY_OVERRIDES.get("evidence", {})


def humanize_knowledge_locator(text: Any) -> Optional[str]:
    raw = str(text or "").strip()
    if not raw:
        return None
    lowered = raw.lower()
    if "scripts/preflight.py" in lowered:
        return "AWP RootNet preflight"
    if "scripts/query-status.py" in lowered:
        return "AWP RootNet status query"
    if "scripts/query-worknet.py" in lowered:
        return "AWP RootNet WorkNet query"
    if "scripts/run_tool.py agent-control status" in lowered:
        return "Mine control status"
    if "scripts/run_tool.py agent-status" in lowered:
        return "Mine agent status"
    if "scripts/run_tool.py doctor" in lowered:
        return "Mine doctor check"
    if "scripts/run_tool.py agent-start" in lowered:
        return "Mine agent start"
    if "bootstrap.sh" in lowered:
        return "Mine bootstrap script"
    mapping = {
        "whitepaper abstract and definitions": "Whitepaper abstract and definitions",
        "README endpoint section": "README endpoint section",
        "README installation and quickstart": "README installation and quickstart",
        "README gasless support table": "README gasless support table",
        "AIP-001 abstract and motivation": "AIP-001 abstract and motivation",
        "AIP-001 terminology, token, and role sections": "AIP-001 terminology, token, and role sections",
        "AIP-002 abstract and worknet page summary": "AIP-002 abstract and WorkNet page summary",
        "AIP-002 chip economy and participation design": "AIP-002 chip economy and participation design",
        "SKILL.md quick start, stake requirement, and install sections": "SKILL.md quick start, stake requirement, and install sections",
        "worknets.get + worknets.getSkills live snapshots captured by workstation on 2026-05-20": "2026-05-20 live `worknets.get` and `worknets.getSkills` snapshots",
        "SKILL.md read vs signed section": "SKILL.md read vs signed section",
        "SKILL.md error handling discipline": "SKILL.md error handling discipline",
        "SKILL.md agent-only and auto-mine guidance": "SKILL.md agent-only and auto-mine guidance",
        "SKILL.md limits and constraints": "SKILL.md limits and constraints",
        "SKILL.md prerequisites and handoff text": "SKILL.md prerequisites and handoff text",
        "SKILL.md messaging and non-TTY guidance": "SKILL.md messaging and non-TTY guidance",
        "staking page main description": "Staking page main description",
        "DAO page governance summary line": "DAO page governance summary line",
        "testnet join section": "Testnet join section",
        "official live skill URI returned by AWP plus repository landing page": "Official live skill URI and repository landing page",
        "blog index visible article list": "Blog index visible article list",
    }
    return mapping.get(raw, raw)


def humanize_runtime_probe_check_label(
    label: Any,
    *,
    command: Any = None,
    skill_key: Any = None,
) -> Optional[str]:
    return humanize_runtime_probe_check_label_payload(
        label,
        command=command,
        skill_key=skill_key,
        dependencies={
            "humanize_executed_step_label": humanize_executed_step_label,
            "humanize_playbook_command_label": humanize_playbook_command_label,
            "humanize_runtime_guidance_action_label": humanize_runtime_guidance_action_label,
            "resolve_worknet": resolve_worknet,
            "runtime_guidance_worknet_key": runtime_guidance_worknet_key,
            "runtime_guidance_worknet_name": runtime_guidance_worknet_name,
        },
    )


def humanize_runtime_probe_locator_display(
    label: Any,
    *,
    command: Any = None,
    skill_key: Any = None,
) -> Optional[str]:
    check_label = humanize_runtime_probe_check_label(
        label,
        command=command,
        skill_key=skill_key,
    )
    if check_label:
        return f"Runtime probe: {check_label}"
    command_text = str(command or "").strip()
    if command_text:
        generic = humanize_knowledge_locator(command_text)
        if generic and generic != command_text:
            return generic
    return "Runtime probe command" if command_text else None


KNOWLEDGE_DISPLAY_TEXT_REPLACEMENTS: list[tuple[str, str]] = [
    tuple(item)
    for item in KNOWLEDGE_DISPLAY_OVERRIDES.get("textReplacements", [])
    if isinstance(item, list) and len(item) == 2
]


def humanize_knowledge_display_text(text: Any) -> Optional[str]:
    raw = str(text or "").strip()
    if not raw:
        return None
    rendered = raw
    for old, new in KNOWLEDGE_DISPLAY_TEXT_REPLACEMENTS:
        rendered = rendered.replace(old, new)
    rendered = re.sub(r"[^\x00-\x7f]", "", rendered)
    rendered = re.sub(r" {3,}", " ", rendered)
    rendered = rendered.replace("  ", " ")
    return rendered


def humanize_knowledge_display_list(items: Any) -> list[str]:
    rendered: list[str] = []
    for item in items if isinstance(items, list) else []:
        text = humanize_knowledge_display_text(item)
        if text:
            rendered.append(text)
    return rendered


def knowledge_display_dossier(
    dossier: Any,
    *,
    summary: Optional[str] = None,
    why: Optional[str] = None,
    worknet_metadata: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(dossier, dict):
        return None
    key = str(dossier.get("key") or "").strip().lower()
    override = KNOWLEDGE_DOSSIER_DISPLAY_OVERRIDES.get(key, {})
    worknet_metadata = worknet_metadata if isinstance(worknet_metadata, dict) else {}
    return normalize_dossier_payload({
        "key": dossier.get("key"),
        "kind": dossier.get("kind"),
        "title": dossier.get("title"),
        "summary": humanize_knowledge_display_text(override.get("summary") or summary or dossier.get("summary")),
        "defaultEntrypoint": dossier.get("defaultEntrypoint"),
        "whyItExists": humanize_knowledge_display_text(override.get("whyItExists") or why or dossier.get("whyItExists")),
        "operatorLoop": humanize_knowledge_display_list(override.get("operatorLoop") or []),
        "economics": humanize_knowledge_display_list(override.get("economics") or []),
        "risks": humanize_knowledge_display_list(override.get("risks") or []),
        "sourceKeys": dossier.get("sourceKeys", []),
        "officialUrls": dossier.get("officialUrls", []),
        **worknet_metadata,
    })


def knowledge_runtime_probe_summary_sentence(runtime_probe_display: Any) -> Optional[str]:
    if not isinstance(runtime_probe_display, dict):
        return None
    summary = str(runtime_probe_display.get("summary") or "").strip()
    if not summary:
        return None
    return humanize_knowledge_display_text(summary)


def knowledge_runtime_probe_count(runtime_probe_display: Any) -> int:
    try:
        return int(runtime_probe_display.get("itemCount", 0) or 0) if isinstance(runtime_probe_display, dict) else 0
    except (TypeError, ValueError):
        return 0


def knowledge_display_source_fact(
    source_fact: Any,
    *,
    summary: Optional[str] = None,
    runtime_probe_display: Any = None,
    worknet_metadata: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(source_fact, dict):
        return None
    key = str(source_fact.get("key") or "").strip().lower()
    override_facts = KNOWLEDGE_SOURCE_FACT_DISPLAY_OVERRIDES.get(key, [])
    runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
    summary_display = humanize_knowledge_display_text(summary)
    if runtime_summary:
        summary_display = join_product_sentences([summary_display, runtime_summary]) or runtime_summary
    worknet_metadata = worknet_metadata if isinstance(worknet_metadata, dict) else {}
    return normalize_source_fact_payload({
        "key": source_fact.get("key"),
        "topic": source_fact.get("topic"),
        "summary": summary_display,
        "facts": humanize_knowledge_display_list(override_facts),
        "sourceKeys": source_fact.get("sourceKeys", []),
        **worknet_metadata,
        "runtimeSummary": runtime_summary,
        "runtimeProbeCount": knowledge_runtime_probe_count(runtime_probe_display) or None,
    })


def knowledge_display_evidence(evidence_matches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    rendered: list[dict[str, Any]] = []
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for item in evidence_matches:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        claim = str(item.get("claim") or "").strip()
        source_key = str(item.get("sourceKey") or "").strip()
        override = KNOWLEDGE_EVIDENCE_DISPLAY_OVERRIDES.get(key, {})
        claim_display = humanize_knowledge_display_text(override.get("claim") or claim)
        preview_display = str(item.get("previewDisplay") or claim_display or "").strip() or None
        display_item = normalize_runtime_probe_payload({
            "key": key or None,
            "topicKey": item.get("topicKey"),
            "label": key or claim or None,
            "labelRaw": key or claim or None,
            "displayLabel": claim_display or key or None,
            "command": None,
            "commandRaw": None,
            "commandDisplay": None,
            "summary": preview_display,
            "summaryDisplay": preview_display,
            "summaryRaw": claim or None,
            "preview": preview_display,
            "claim": claim or None,
            "claimDisplay": claim_display,
            "claimRaw": claim or None,
            "previewDisplay": preview_display,
            "previewRaw": claim or None,
            "message": claim_display,
            "messageDisplay": claim_display,
            "messageRaw": claim or None,
            "textDisplay": claim_display,
            "textRaw": claim or None,
            "state": None,
            "stateDisplay": None,
            "userActions": None,
            "userActionsDisplay": None,
            "userActionsRaw": None,
            "nextCommand": None,
            "nextCommandDisplay": None,
            "nextCommandRaw": None,
            "detailDisplay": None,
            "detailRaw": None,
            "errorSummaryDisplay": None,
            "errorSummaryRaw": None,
            "status": None,
            "statusDisplay": None,
            "sourceKey": source_key or None,
            "sourceName": item.get("sourceName"),
            "sourceNameDisplay": humanize_knowledge_source_label(item.get("sourceName") or source_key) or None,
            "locator": item.get("locator"),
            "locatorDisplay": humanize_knowledge_locator(item.get("locator")),
            "resultDisplay": None,
            "runtimeGuidanceDisplay": None,
            "evidenceType": item.get("evidenceType"),
            "evidenceTypeDisplay": KNOWLEDGE_EVIDENCE_TYPE_LABELS.get(str(item.get("evidenceType") or "").strip()),
            "stability": item.get("stability"),
            "stabilityDisplay": KNOWLEDGE_STABILITY_LABELS.get(str(item.get("stability") or "").strip()),
            "rationale": item.get("rationale"),
            "rationaleDisplay": humanize_knowledge_display_text(override.get("rationale") or item.get("rationale")),
            "sourceUrl": item.get("sourceUrl"),
            "trustTier": item.get("trustTier"),
        }, RUNTIME_PROBE_EVIDENCE_FIELDS)
        rendered.append(display_item)
        if source_key and claim:
            index[(source_key, claim)] = display_item
    return rendered, index


def knowledge_display_citations(
    citations: list[dict[str, Any]],
    *,
    evidence_display_index: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for item in citations:
        if not isinstance(item, dict):
            continue
        source_key = str(item.get("sourceKey") or "").strip()
        claim = str(item.get("claim") or "").strip()
        match = evidence_display_index.get((source_key, claim), {})
        rendered.append(
            normalize_citation_payload({
                "sourceKey": source_key or None,
                "sourceName": item.get("sourceName"),
                "sourceNameDisplay": humanize_knowledge_source_label(item.get("sourceName") or source_key) or None,
                "url": item.get("url"),
                "locator": item.get("locator"),
                "locatorDisplay": humanize_knowledge_locator(item.get("locator")),
                "claim": item.get("claim"),
                "claimDisplay": match.get("claimDisplay") if isinstance(match, dict) else None,
                "evidenceType": item.get("evidenceType"),
                "evidenceTypeDisplay": KNOWLEDGE_EVIDENCE_TYPE_LABELS.get(str(item.get("evidenceType") or "").strip()),
                "stability": item.get("stability"),
                "stabilityDisplay": KNOWLEDGE_STABILITY_LABELS.get(str(item.get("stability") or "").strip()),
            })
        )
    return rendered


def knowledge_source_summary_display(source_record: Any) -> Optional[str]:
    if not isinstance(source_record, dict):
        return None
    key = str(source_record.get("key") or "").strip().lower()
    kind = str(source_record.get("kind") or "").strip()
    worknet_key = str(source_record.get("worknetKey") or "").strip().lower()
    worknet_name = None
    if worknet_key:
        profile = resolve_worknet(worknet_key)
        if isinstance(profile, dict):
            worknet_name = str(profile.get("name") or "").strip() or None
    if key == "tmr-skill":
        return "TMR skill repository snapshot from 2026-05-22 exposes LICENSE, README, and SKILL.md."
    if key == "community-skill":
        return "Community skill repository snapshot from 2026-05-22 exposes LICENSE, README, SKILL.md, and contract context."
    if key == "awp-community":
        return "AWP community source provides WorkNet community context."
    if key == "awp-agents":
        return "AWP agents source explains agent work wallets and runtime expectations."
    if key == "awp-whitepaper-page":
        return "AWP whitepaper page links protocol PDF material and public surface context."
    if key == "awp-blog-01-launch-worknet":
        return "Official blog launch guidance explains WorkNet onboarding, gasless setup, Guardian expectations, and manager handoff context."
    if key == "awp-blog-02-what-is-awp":
        return "Official blog material explains AWP, agent work, fair launch, proof of useful work, and permissionless WorkNets."
    if key == "awp-blog-03-start-earning":
        return "Official blog material explains how an operator can start earning with awp-skill, gas checks, and WorkNet selection."
    if key == "awp-blog-04-fair-launch":
        return "Official blog material explains the AWP fair launch, 10B emission context, WorkNet wages, and DAO Treasury framing."
    if key == "awp-blog-05-worknet":
        return "Official blog material explains what a WorkNet is and how WorkNet payroll, equity, and agent participation fit together."
    if kind == "protocol":
        return "AWP protocol source."
    if kind == "directory":
        return "Directory source used for source discovery."
    if kind == "paper":
        return "Paper source covering RootNet and WorkNet concepts."
    if kind == "skill":
        if worknet_name:
            return f"{worknet_name} skill source."
        return "Skill source."
    if kind == "skill-doc":
        if worknet_name:
            return f"{worknet_name} skill documentation."
        return "Skill documentation source."
    if kind == "aip":
        if worknet_name:
            return f"{worknet_name} AIP source for WorkNet behavior."
        return "AIP source for WorkNet behavior."
    if kind == "live-api":
        return "Live API source for WorkNet ID and runtime metadata."
    if kind == "worknet":
        if worknet_name:
            return f"{worknet_name} WorkNet source."
        return "WorkNet source."
    if kind == "protocol-surface":
        return "Protocol surface source."
    if kind == "worknet-surface":
        return "WorkNet surface source."
    if kind == "docs":
        return "Documentation source."
    if kind == "service":
        return "Service source."
    summary = str(source_record.get("summary") or "").strip()
    return summary or None


def knowledge_worknet_metadata(
    *,
    worknet_key: Any = None,
    worknet_id: Any = None,
    source_keys: Any = None,
    install_uri: Any = None,
    capability_report: Any = None,
) -> dict[str, Any]:
    resolved_key = str(worknet_key or "").strip().lower()
    profile = resolve_worknet(resolved_key or str(worknet_id or ""))
    if not resolved_key and isinstance(profile, dict):
        resolved_key = str(profile.get("key") or "").strip().lower()
    source_key_items = source_keys if isinstance(source_keys, list) else []
    source_key_set = {
        str(item).strip()
        for item in source_key_items
        if str(item).strip()
    }
    if isinstance(profile, dict):
        source_key_set.update(
            str(item).strip()
            for item in profile.get("source_keys", [])
            if str(item).strip()
        )
    canonical_worknet_id = knowledge_first_non_empty(
        worknet_id,
        profile.get("worknet_id") if isinstance(profile, dict) else None,
    )
    predecessor_worknet_ids = [
        str(item).strip()
        for item in (profile.get("predecessor_worknet_ids", []) if isinstance(profile, dict) else [])
        if str(item).strip()
    ]
    official_skill_uri = knowledge_first_non_empty(
        install_uri,
        profile.get("skills_uri") if isinstance(profile, dict) else None,
        profile.get("install_uri") if isinstance(profile, dict) else None,
    )
    min_stake_hint = None
    if isinstance(capability_report, dict) and capability_report.get("minStake") not in {None, ""}:
        min_stake_hint = capability_report.get("minStake")
    elif isinstance(profile, dict) and profile.get("min_stake") not in {None, ""}:
        min_stake_hint = profile.get("min_stake")

    inspection_state = str(capability_report.get("cliStatus") or "").strip() if isinstance(capability_report, dict) else ""
    runtime_spec_state = "unknown"
    if inspection_state in {"ready", "installed-needs-bootstrap", "network-blocked", "runtime-error"}:
        runtime_spec_state = "local-runtime-evidence"
    elif any(key.endswith("-skill-raw") for key in source_key_set):
        runtime_spec_state = "runtime-doc-available"
    elif resolved_key == "community" and "awp-community" in source_key_set:
        runtime_spec_state = "thin-repo-plus-hub"
    elif official_skill_uri:
        runtime_spec_state = "thin-repo-only"

    min_stake_hint_display = None
    if min_stake_hint not in {None, ""}:
        min_stake_hint_display = str(min_stake_hint)
        if resolved_key in {"tmr", "community"} and str(min_stake_hint) == "0":
            min_stake_hint_display = "0 AWP required"

    return {
        "canonicalWorknetId": str(canonical_worknet_id).strip() if str(canonical_worknet_id or "").strip() else None,
        "predecessorWorknetIds": predecessor_worknet_ids,
        "officialSkillUri": str(official_skill_uri).strip() if str(official_skill_uri or "").strip() else None,
        "minStakeHint": min_stake_hint,
        "minStakeHintDisplay": min_stake_hint_display,
        "runtimeSpecState": runtime_spec_state if runtime_spec_state != "unknown" or resolved_key in {"tmr", "community"} else None,
        "runtimeSpecStateDisplay": KNOWLEDGE_RUNTIME_SPEC_STATE_LABELS.get(runtime_spec_state) if runtime_spec_state != "unknown" or resolved_key in {"tmr", "community"} else None,
    }


def preferred_worknet_source_keys_for_runtime_state(
    source_keys: list[str],
    *,
    runtime_spec_state: Optional[str],
    source_records: Optional[dict[str, dict[str, Any]]] = None,
) -> list[str]:
    source_records = source_records or {}
    deduped: list[str] = []
    for item in source_keys:
        text = str(item or "").strip()
        if text and text not in deduped and text != "awp-live-query":
            deduped.append(text)
    if not deduped:
        return deduped

    state = str(runtime_spec_state or "").strip()
    def source_kind(key: str) -> str:
        record = source_records.get(key, {})
        return str(record.get("kind") or "").strip()

    if state == "thin-repo-plus-hub":
        preferred_order = {"docs": 0, "service": 1, "worknet": 2, "skill-doc": 3, "skill": 4}
        return sorted(deduped, key=lambda key: (preferred_order.get(source_kind(key), 9), deduped.index(key)))
    if state == "thin-repo-only":
        preferred_order = {"skill": 0, "skill-doc": 1, "docs": 2, "service": 3, "worknet": 4}
        return sorted(deduped, key=lambda key: (preferred_order.get(source_kind(key), 9), deduped.index(key)))
    if state == "runtime-doc-available":
        preferred_order = {"skill-doc": 0, "worknet": 1, "skill": 2, "docs": 3, "service": 4, "aip": 5}
        return sorted(deduped, key=lambda key: (preferred_order.get(source_kind(key), 9), deduped.index(key)))
    return deduped


def runtime_spec_reason_parts(
    *,
    runtime_spec_state: Optional[str],
    runtime_spec_state_display: Optional[str],
    canonical_worknet_id: Optional[str],
    min_stake_hint_display: Optional[str],
) -> list[str]:
    state = str(runtime_spec_state or "").strip()
    display = str(runtime_spec_state_display or "").strip()
    parts: list[str] = []
    if state == "runtime-doc-available":
        parts.append("official runtime docs and operator surfaces are already captured locally")
    elif state == "thin-repo-only":
        parts.append("only a thin official repo surface is available so far")
    elif state == "thin-repo-plus-hub":
        parts.append("only a thin official repo surface plus a community hub are available so far")
    if canonical_worknet_id:
        parts.append(f"canonical worknet id: {canonical_worknet_id}")
    if min_stake_hint_display:
        parts.append(f"live minStake hint: {min_stake_hint_display}")
    if display and display not in parts:
        parts.append(f"runtime maturity: {display}")
    return parts


def knowledge_display_source_record(
    source_record: Any,
    *,
    drift_item: Any = None,
    impact_item: Any = None,
    runtime_probe_display: Any = None,
    capability_report: Any = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(source_record, dict):
        return None
    key = str(source_record.get("key") or "").strip()
    name_display = humanize_knowledge_source_label(source_record.get("name") or key) or None
    kind = str(source_record.get("kind") or "").strip()
    trust_tier = source_record.get("trustTier")
    drift_status = str(drift_item.get("status") or drift_item.get("driftStatus") or "").strip() if isinstance(drift_item, dict) else ""
    headline = (
        f"{name_display} source review required"
        if drift_status and drift_status not in {"unchanged", "no-baseline"}
        else f"{name_display} source ready"
    ) if name_display else None
    impacted_topics = len(impact_item.get("impactedTopics", [])) if isinstance(impact_item, dict) and isinstance(impact_item.get("impactedTopics"), list) else 0
    impacted_facts = len(impact_item.get("impactedFacts", [])) if isinstance(impact_item, dict) and isinstance(impact_item.get("impactedFacts"), list) else 0
    impacted_worknets = len(impact_item.get("impactedWorknets", [])) if isinstance(impact_item, dict) and isinstance(impact_item.get("impactedWorknets"), list) else 0
    summary_display = knowledge_source_summary_display(source_record)
    if isinstance(impact_item, dict) and (impacted_topics or impacted_facts or impacted_worknets):
        summary_display = (
            f"{summary_display} Affects {impacted_topics} topic(s), "
            f"{impacted_facts} fact(s), and {impacted_worknets} WorkNet(s)."
        ).strip()
    runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
    if runtime_summary:
        summary_display = join_product_sentences([summary_display, runtime_summary]) or runtime_summary
    summary_preview = knowledge_runtime_augmented_preview(
        summary_display or source_record.get("summary"),
        runtime_summary,
        headline=headline,
        max_chars=140,
        max_sentences=2,
    ) or compact_preview_text(
        summary_display or source_record.get("summary"),
        max_chars=140,
        max_sentences=2,
    )
    worknet_metadata = knowledge_worknet_metadata(
        worknet_key=source_record.get("worknetKey"),
        source_keys=[source_record.get("key")] if source_record.get("key") else None,
        install_uri=source_record.get("url") if kind == "skill" else None,
        capability_report=capability_report,
    )
    return normalize_source_record_payload({
        "key": source_record.get("key"),
        "name": source_record.get("name"),
        "nameDisplay": name_display,
        "url": source_record.get("url"),
        "kind": source_record.get("kind"),
        "kindDisplay": humanize_knowledge_source_kind(kind),
        "trustTier": trust_tier,
        "trustTierDisplay": humanize_knowledge_trust_tier(trust_tier),
        "worknetKey": source_record.get("worknetKey"),
        **worknet_metadata,
        "headline": headline,
        "summary": source_record.get("summary"),
        "summaryDisplay": summary_display,
        "summaryPreview": summary_preview,
        "runtimeSummary": runtime_summary,
        "runtimeProbeCount": knowledge_runtime_probe_count(runtime_probe_display) or None,
    })


def knowledge_display_drift_item(
    drift_item: Any,
    *,
    source_record: Any = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(drift_item, dict):
        return None
    source_name = (
        (source_record.get("name") if isinstance(source_record, dict) else None)
        or drift_item.get("name")
        or drift_item.get("key")
    )
    changed_fields = [str(item).strip() for item in drift_item.get("changedFields", []) if str(item).strip()]
    return normalize_drift_payload({
        "key": drift_item.get("key"),
        "name": drift_item.get("name"),
        "nameDisplay": humanize_knowledge_source_label(source_name) or None,
        "status": drift_item.get("status"),
        "statusDisplay": KNOWLEDGE_DRIFT_STATUS_LABELS.get(str(drift_item.get("status") or "").strip()),
        "changedFields": changed_fields,
        "changedFieldsDisplay": [humanize_source_changed_field(item) for item in changed_fields],
        "note": drift_item.get("note"),
        "previous": drift_item.get("previous"),
        "current": drift_item.get("current"),
    })


def knowledge_display_changed_sources(
    changed_items: Any,
    *,
    source_records: Optional[dict[str, dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    source_records = source_records or {}
    for item in changed_items if isinstance(changed_items, list) else []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        rendered.append(
            knowledge_display_drift_item(
                item,
                source_record=source_records.get(key),
            )
            or {}
        )
    return [item for item in rendered if item]


def changed_source_highlight_entry(item: Any) -> Optional[dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    key = str(item.get("key") or "").strip()
    label = str(item.get("nameDisplay") or item.get("name") or key).strip()
    changed_fields = item.get("changedFieldsDisplay", []) if isinstance(item.get("changedFieldsDisplay"), list) else []
    preview = str(item.get("note") or "").strip()
    if not preview and changed_fields:
        preview = f"Changed fields: {', '.join(str(field).strip() for field in changed_fields if str(field).strip())}."
    payload = build_normalized_knowledge_highlight(
        kind="source",
        fields=CHANGED_SOURCE_HIGHLIGHT_FIELDS,
        key=key,
        label=label,
        headline=item.get("headline") or (f"{label} source review required" if label else None),
        preview=preview,
        query_command=query_source_command(key) if key else None,
        primary_command=query_source_command(key, rebuild=True) if key else None,
        freshness_status="affected",
        research_tier="queued",
        extra={
            "nameDisplay": item.get("nameDisplay"),
            "statusDisplay": item.get("statusDisplay"),
            "changedFieldsDisplay": changed_fields,
            "summary": compact_preview_text(preview, max_chars=140, max_sentences=2) if preview else None,
            "summaryPreview": compact_preview_text(preview, max_chars=140, max_sentences=2) if preview else None,
            "summaryFull": preview or None,
        },
    )
    return payload


def knowledge_skill_inspections_by_key(catalog: Any) -> dict[str, dict[str, Any]]:
    inspections = catalog.get("skillInspections", []) if isinstance(catalog, dict) else []
    return {
        str(item.get("skillKey") or "").strip().lower(): item
        for item in inspections
        if isinstance(item, dict) and str(item.get("skillKey") or "").strip()
    }


def knowledge_runtime_probe_display_from_catalog(
    catalog: Any,
    *,
    source_keys: Any = None,
    worknet_key: Optional[str] = None,
    capability_report: Any = None,
) -> Optional[dict[str, Any]]:
    if isinstance(capability_report, dict) and isinstance(capability_report.get("skillInspection"), dict):
        return knowledge_runtime_probe_display(
            capability_report.get("skillInspection"),
            skill_key=worknet_key,
        )
    inspections = knowledge_skill_inspections_by_key(catalog)
    normalized_worknet_key = str(worknet_key or "").strip().lower()
    if normalized_worknet_key and normalized_worknet_key in inspections:
        return knowledge_runtime_probe_display(
            inspections[normalized_worknet_key],
            skill_key=normalized_worknet_key,
        )
    source_records = knowledge_source_records_from_catalog(catalog)
    for source_key in source_keys if isinstance(source_keys, list) else []:
        normalized_source_key = str(source_key or "").strip().lower()
        if not normalized_source_key:
            continue
        if normalized_source_key in inspections:
            return knowledge_runtime_probe_display(
                inspections[normalized_source_key],
                skill_key=normalized_source_key,
            )
        source_record = source_records.get(normalized_source_key) or source_records.get(str(source_key or "").strip())
        source_worknet_key = str(source_record.get("worknetKey") or "").strip().lower() if isinstance(source_record, dict) else ""
        if source_worknet_key and source_worknet_key in inspections:
            return knowledge_runtime_probe_display(
                inspections[source_worknet_key],
                skill_key=source_worknet_key,
            )
    return None


def knowledge_runtime_probe_summary(
    probe_results: Any,
    *,
    label: str,
) -> Optional[str]:
    items = [item for item in probe_results if isinstance(item, dict)] if isinstance(probe_results, list) else []
    if not items:
        return None
    failed = [item for item in items if runtime_probe_effective_status(item) != "ok"]
    if failed:
        first = failed[0]
        detail = str(
            first.get("summaryDisplay")
            or first.get("resultSummary")
            or first.get("messageDisplay")
            or first.get("textDisplay")
            or ""
        ).strip()
        if detail:
            return f"{label}: {len(failed)} runtime probe(s) failed. {detail}"
        return f"{label}: {len(failed)} runtime probe(s) failed."
    first = items[0]
    detail = str(
        first.get("summaryDisplay")
        or first.get("resultSummary")
        or first.get("messageDisplay")
        or first.get("textDisplay")
        or ""
    ).strip()
    if detail:
        return f"{label}: {len(items)} runtime probe(s) checked. {detail}"
    return f"{label}: {len(items)} runtime probe(s) checked."


def knowledge_runtime_probe_summary_raw(
    probe_results: Any,
) -> Optional[str]:
    items = [item for item in probe_results if isinstance(item, dict)] if isinstance(probe_results, list) else []
    if not items:
        return None
    failed = [item for item in items if runtime_probe_effective_status(item) != "ok"]
    first = failed[0] if failed else items[0]
    return str(
        first.get("summaryRaw")
        or first.get("previewRaw")
        or first.get("messageRaw")
        or first.get("textRaw")
        or first.get("resultSummary")
        or first.get("text")
        or ""
    ).strip() or None


def runtime_probe_highlight_extra(
    item: Any,
    *,
    summary_full: Any,
    probe_label: Any,
    skill_key: Any,
) -> dict[str, Any]:
    payload = runtime_probe_contract_fields(item)
    payload.update(
        {
            "label": item.get("displayLabel") or item.get("label"),
            "command": item.get("command"),
            "summary": compact_preview_text(summary_full, max_chars=140, max_sentences=2) if summary_full else None,
            "summaryPreview": compact_preview_text(summary_full, max_chars=140, max_sentences=2) if summary_full else None,
            "summaryFull": summary_full,
            "probeLabel": probe_label,
            "skillKey": skill_key,
        }
    )
    return payload


def runtime_probe_claim_display(item: Any) -> Optional[str]:
    item = item if isinstance(item, dict) else {}
    label = str(item.get("displayLabel") or item.get("label") or "").strip()
    summary = str(item.get("summary") or item.get("messageDisplay") or item.get("textDisplay") or "").strip()
    preview_display = str(item.get("previewDisplay") or "").strip()
    if preview_display:
        return preview_display
    if summary:
        normalized_summary = strip_sentence_end(summary)
        normalized_label = strip_sentence_end(label)
        return summary if normalized_label and normalized_summary.startswith(normalized_label) else f"{label}: {summary}"
    if label:
        return f"{label}: {str(item.get('statusDisplay') or '').strip() or 'status unavailable'}."
    return None


def build_runtime_probe_highlight_entry(
    item: Any,
    *,
    probe_label: Any,
    skill_key: Any,
) -> dict[str, Any]:
    item = item if isinstance(item, dict) else {}
    label = str(item.get("displayLabel") or item.get("label") or "").strip()
    status = str(item.get("status") or "").strip()
    summary = str(item.get("summary") or "").strip() or None
    payload = build_knowledge_highlight_entry(
        kind="evidence",
        key=item.get("key"),
        label=label,
        headline=f"{label}: {humanize_executed_step_status_display(status) or status}." if label else None,
        preview=summary,
        query_command=item.get("command"),
        primary_command=item.get("command"),
        freshness_status="affected" if status != "ok" else "stable",
        research_tier="related",
        extra=runtime_probe_highlight_extra(
            item,
            summary_full=summary,
            probe_label=probe_label,
            skill_key=skill_key,
        ),
    )
    return normalize_runtime_probe_payload(payload, RUNTIME_PROBE_HIGHLIGHT_FIELDS)


def build_runtime_probe_evidence_entry(
    item: Any,
    *,
    skill_key: str,
    source_name_display: str,
    topic_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    item = item if isinstance(item, dict) else {}
    label = str(item.get("displayLabel") or item.get("label") or "").strip()
    if not label:
        return None
    command = str(item.get("command") or "").strip() or None
    locator_display = humanize_runtime_probe_locator_display(
        label,
        command=command,
        skill_key=skill_key,
    ) or "Runtime probe command"
    claim_display = runtime_probe_claim_display(item)
    if not claim_display:
        return None
    payload = {
        "key": item.get("key"),
        "topicKey": topic_key or None,
        **runtime_probe_contract_fields(item),
        "label": label,
        "command": command,
        "labelRaw": item.get("labelRaw") or item.get("label"),
        "claim": claim_display,
        "claimDisplay": humanize_knowledge_display_text(claim_display),
        "claimRaw": item.get("previewRaw") or item.get("summaryRaw") or item.get("messageRaw") or item.get("textRaw"),
        "sourceKey": skill_key or None,
        "sourceName": source_name_display,
        "sourceNameDisplay": source_name_display,
        "locator": command,
        "locatorDisplay": locator_display,
        "evidenceType": "runtime-inspection",
        "evidenceTypeDisplay": KNOWLEDGE_EVIDENCE_TYPE_LABELS.get("runtime-inspection"),
        "stability": "medium" if item.get("status") == "ok" else "low",
        "stabilityDisplay": KNOWLEDGE_STABILITY_LABELS.get("medium" if item.get("status") == "ok" else "low"),
        "rationale": "Runtime inspection output provides local evidence for capability readiness.",
        "rationaleDisplay": "Runtime inspection output provides local evidence for capability readiness.",
        "sourceUrl": None,
        "trustTier": None,
        "summaryDisplay": item.get("summaryDisplay") or item.get("summary"),
        "previewDisplay": str(item.get("previewDisplay") or "").strip() or humanize_knowledge_display_text(claim_display),
    }
    return normalize_runtime_probe_payload(payload, RUNTIME_PROBE_EVIDENCE_FIELDS)


def knowledge_runtime_probe_display(
    inspection: Any,
    *,
    skill_key: Any,
) -> Optional[dict[str, Any]]:
    return knowledge_runtime_probe_display_payload(
        inspection,
        skill_key=skill_key,
        dependencies={
            "RUNTIME_PROBE_TOP_LEVEL_FIELDS": RUNTIME_PROBE_TOP_LEVEL_FIELDS,
            "build_runtime_probe_contract_item": build_runtime_probe_contract_item,
            "build_runtime_probe_highlight_entry": build_runtime_probe_highlight_entry,
            "humanize_executed_step_label": humanize_executed_step_label,
            "humanize_executed_step_status_display": humanize_executed_step_status_display,
            "humanize_runtime_probe_check_label": humanize_runtime_probe_check_label,
            "humanize_runtime_probe_locator_display": humanize_runtime_probe_locator_display,
            "humanize_skill_inspection_status": humanize_skill_inspection_status,
            "knowledge_runtime_probe_summary": knowledge_runtime_probe_summary,
            "knowledge_runtime_probe_summary_raw": knowledge_runtime_probe_summary_raw,
            "normalize_runtime_probe_payload": normalize_runtime_probe_payload,
            "render_argv": render_argv,
            "runtime_guidance_worknet_name": runtime_guidance_worknet_name,
            "runtime_message": runtime_message,
            "runtime_probe_effective_status": runtime_probe_effective_status,
            "safe_slug": safe_slug,
        },
    )


def knowledge_runtime_probe_evidence_entries(
    runtime_probe_display: Any,
    *,
    topic_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    if not isinstance(runtime_probe_display, dict):
        return []
    skill_key = str(runtime_probe_display.get("skillKey") or "").strip().lower()
    source_name = runtime_guidance_worknet_name(skill_key)
    source_name_display = (
        f"{source_name} runtime" if source_name and source_name != "runtime" else "Runtime probe"
    )
    rendered: list[dict[str, Any]] = []
    for item in runtime_probe_display.get("items", [])[:3]:
        payload = build_runtime_probe_evidence_entry(
            item,
            skill_key=skill_key,
            source_name_display=source_name_display,
            topic_key=topic_key,
        )
        if payload:
            rendered.append(payload)
    return rendered


def knowledge_runtime_probe_display_for_topic(
    *,
    topic: str,
    catalog: Any,
    worknet_context: Any,
    capability_report: Any,
) -> Optional[dict[str, Any]]:
    inspections = knowledge_skill_inspections_by_key(catalog)
    worknet_key = str(worknet_context.get("key") or "").strip().lower() if isinstance(worknet_context, dict) else ""
    if isinstance(capability_report, dict) and isinstance(capability_report.get("skillInspection"), dict):
        return knowledge_runtime_probe_display(
            capability_report.get("skillInspection"),
            skill_key=worknet_key,
        )
    topic_key = str(topic or "").strip().lower()
    if topic_key and topic_key in inspections:
        return knowledge_runtime_probe_display(inspections[topic_key], skill_key=topic_key)
    if worknet_key and worknet_key in inspections:
        return knowledge_runtime_probe_display(inspections[worknet_key], skill_key=worknet_key)
    return None


def knowledge_runtime_probe_display_for_source(
    *,
    source_key: str,
    source_record: Any,
    catalog: Any,
    capability_report: Any = None,
) -> Optional[dict[str, Any]]:
    inspections = knowledge_skill_inspections_by_key(catalog)
    normalized_source_key = str(source_key or "").strip().lower()
    worknet_key = str(source_record.get("worknetKey") or "").strip().lower() if isinstance(source_record, dict) else ""
    if isinstance(capability_report, dict) and isinstance(capability_report.get("skillInspection"), dict):
        return knowledge_runtime_probe_display(
            capability_report.get("skillInspection"),
            skill_key=worknet_key or normalized_source_key,
        )
    if normalized_source_key and normalized_source_key in inspections:
        return knowledge_runtime_probe_display(inspections[normalized_source_key], skill_key=normalized_source_key)
    if worknet_key and worknet_key in inspections:
        return knowledge_runtime_probe_display(inspections[worknet_key], skill_key=worknet_key)
    return None


def knowledge_display_worknet(
    worknet: Any,
    *,
    capability_report: Any = None,
    runtime_probe_display: Any = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(worknet, dict):
        return None
    key = str(worknet.get("key") or "").strip().lower()
    narrative = canonical_topic_narrative(key, dossier_key=key, worknet_key=key)
    runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
    caution_display = humanize_knowledge_display_text((narrative or {}).get("caution"))
    if runtime_summary:
        caution_display = join_product_sentences([caution_display, runtime_summary]) or runtime_summary
    profile = resolve_worknet(str(worknet.get("key") or worknet.get("worknetId") or ""))
    merged_source_keys: list[str] = []
    for source_key in worknet.get("sourceKeys", []) if isinstance(worknet.get("sourceKeys"), list) else []:
        text = str(source_key).strip()
        if text and text not in merged_source_keys:
            merged_source_keys.append(text)
    if isinstance(profile, dict):
        for source_key in profile.get("source_keys", []):
            text = str(source_key).strip()
            if text and text not in merged_source_keys:
                merged_source_keys.append(text)
    worknet_metadata = knowledge_worknet_metadata(
        worknet_key=worknet.get("key"),
        worknet_id=worknet.get("worknetId"),
        source_keys=merged_source_keys,
        install_uri=worknet.get("installUri"),
        capability_report=capability_report,
    )
    rendered = {
        "key": worknet.get("key"),
        "worknetId": worknet.get("worknetId"),
        "name": worknet.get("name"),
        "status": worknet.get("status"),
        "statusDisplay": KNOWLEDGE_WORKNET_STATUS_LABELS.get(str(worknet.get("status") or "").strip()),
        "symbol": worknet.get("symbol"),
        "installUri": worknet.get("installUri"),
        "sourceKeys": merged_source_keys,
        "sourceKeysDisplay": [
            humanize_knowledge_source_label(item)
            for item in merged_source_keys
            if str(item).strip()
        ],
        **worknet_metadata,
        "goal": worknet.get("goal"),
        "goalDisplay": humanize_knowledge_display_text((narrative or {}).get("plain") or worknet.get("goal")),
        "loop": worknet.get("loop"),
        "loopDisplay": humanize_knowledge_display_text((narrative or {}).get("loop") or worknet.get("loop")),
        "automationLevel": worknet.get("automationLevel"),
        "automationLevelDisplay": KNOWLEDGE_AUTOMATION_LABELS.get(str(worknet.get("automationLevel") or "").strip()),
        "riskLevel": worknet.get("riskLevel"),
        "riskLevelDisplay": KNOWLEDGE_RISK_LABELS.get(str(worknet.get("riskLevel") or "").strip()),
        "recommendedRole": worknet.get("recommendedRole"),
        "recommendedRoleDisplay": KNOWLEDGE_ROLE_LABELS.get(str(worknet.get("recommendedRole") or "").strip()),
        "cautionDisplay": caution_display,
        "runtimeSummary": runtime_summary,
        "runtimeProbeCount": knowledge_runtime_probe_count(runtime_probe_display) or None,
    }
    if isinstance(capability_report, dict):
        rendered["runnable"] = capability_report.get("runnable")
        rendered["canStartWithoutStake"] = capability_report.get("canStartWithoutStake")
        rendered["safeLongRun"] = capability_report.get("safeLongRun")
        rendered["cliStatus"] = capability_report.get("cliStatus")
        rendered["executionState"] = capability_report.get("executionState")
        rendered["executionStateDisplay"] = capability_report.get("executionStateDisplay")
        rendered["executionHeadline"] = capability_report.get("executionHeadline")
    return normalize_worknet_payload(rendered)


def knowledge_display_source_impact(
    source_impact: Any,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(source_impact, dict):
        return None
    items = source_impact.get("items", [])
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    topic_result_cache: dict[str, dict[str, Any]] = {}

    def topic_label(topic_key: Any) -> str:
        normalized = str(topic_key or "").strip()
        if not normalized:
            return normalized
        if normalized not in topic_result_cache:
            topic_result_cache[normalized] = build_knowledge_query_result(normalized, catalog=catalog)
        result = topic_result_cache[normalized]
        return str(result.get("resolvedTopicLabel") or normalized).strip()

    rendered_items: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        impacted_topics_display: list[str] = []
        for target in item.get("impactedTopics", []) if isinstance(item.get("impactedTopics"), list) else []:
            if isinstance(target, dict):
                label = str(target.get("title") or target.get("label") or target.get("key") or "").strip()
            else:
                label = ""
            if not label and target:
                label = topic_label(target)
            if label and label not in impacted_topics_display:
                impacted_topics_display.append(label)
        impacted_facts_display: list[str] = []
        for target in item.get("impactedFacts", []) if isinstance(item.get("impactedFacts"), list) else []:
            if isinstance(target, dict):
                label = str(target.get("topic") or target.get("title") or target.get("label") or target.get("key") or "").strip()
            else:
                label = ""
            if not label and target:
                label = topic_label(target)
            if label and label not in impacted_facts_display:
                impacted_facts_display.append(label)
        impacted_worknets_display: list[str] = []
        for target in item.get("impactedWorknets", []) if isinstance(item.get("impactedWorknets"), list) else []:
            profile = resolve_worknet(str(target or ""))
            label = str(profile.get("name") or target or "").strip() if isinstance(profile, dict) else str(target or "").strip()
            if label and label not in impacted_worknets_display:
                impacted_worknets_display.append(label)
        changed_fields = [str(field).strip() for field in item.get("changedFields", []) if str(field).strip()]
        review_commands = [
            str(command).strip()
            for command in item.get("reviewCommands", [])
            if str(command).strip()
        ] if isinstance(item.get("reviewCommands"), list) else []
        rendered_items.append(
            normalize_source_impact_item_payload({
                "sourceKey": item.get("sourceKey"),
                "sourceName": item.get("sourceName"),
                "sourceNameDisplay": humanize_knowledge_source_label(item.get("sourceName") or item.get("sourceKey")) or None,
                "priority": item.get("priority"),
                "priorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(str(item.get("priority") or "").strip()),
                "driftStatus": item.get("driftStatus"),
                "driftStatusDisplay": KNOWLEDGE_DRIFT_STATUS_LABELS.get(str(item.get("driftStatus") or "").strip()),
                "changedFields": changed_fields,
                "changedFieldsDisplay": [humanize_source_changed_field(field) for field in changed_fields],
                "note": item.get("note"),
                "impactedTopicsDisplay": impacted_topics_display,
                "impactedFactsDisplay": impacted_facts_display,
                "impactedWorknetsDisplay": impacted_worknets_display,
                "reviewHint": item.get("reviewHint"),
                "reviewCommands": review_commands,
            })
        )
    affected = bool(source_impact.get("affected"))
    if affected and rendered_items:
        summary = f"{len(rendered_items)} upstream source change(s) may affect this topic."
    else:
        summary = "No upstream source changes affect this topic."
    return normalize_source_impact_payload({
        "affected": affected,
        "summary": summary,
        "items": rendered_items,
    })


def knowledge_display_freshness(freshness: Any) -> Optional[dict[str, Any]]:
    if not isinstance(freshness, dict):
        return None
    items = freshness.get("items", [])
    rendered_items: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        impact_items = item.get("impactItems", [])
        changed_sources_display: list[str] = []
        for impact in impact_items if isinstance(impact_items, list) else []:
            if not isinstance(impact, dict):
                continue
            source_label = humanize_knowledge_source_label(impact.get("sourceName") or impact.get("sourceKey"))
            if source_label and source_label not in changed_sources_display:
                changed_sources_display.append(source_label)
        rendered_items.append(
            normalize_freshness_payload({
                "key": item.get("key"),
                "label": item.get("label"),
                "bucket": item.get("bucket"),
                "bucketDisplay": KNOWLEDGE_FRESHNESS_BUCKET_LABELS.get(str(item.get("bucket") or "").strip()),
                "status": item.get("status"),
                "statusDisplay": KNOWLEDGE_FRESHNESS_STATUS_LABELS.get(str(item.get("status") or "").strip()),
                "highestPriority": item.get("highestPriority"),
                "highestPriorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(str(item.get("highestPriority") or "").strip()),
                "changedSourceKeys": item.get("changedSourceKeys", []),
                "changedSourcesDisplay": changed_sources_display,
                "reviewHints": item.get("reviewHints", []),
            }, FRESHNESS_ITEM_FIELDS)
        )
    status = str(freshness.get("status") or "").strip()
    highest_priority = str(freshness.get("highestPriority") or "").strip()
    if status == "affected":
        summary = "Source freshness review is required before relying on this topic."
    else:
        summary = "No source freshness issues are currently attached to this topic."
    return normalize_freshness_payload({
        "status": freshness.get("status"),
        "statusDisplay": KNOWLEDGE_FRESHNESS_STATUS_LABELS.get(status),
        "highestPriority": freshness.get("highestPriority"),
        "highestPriorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(highest_priority),
        "summary": summary,
        "items": rendered_items,
    }, FRESHNESS_DISPLAY_FIELDS)


def knowledge_display_review_queue_entries(
    entries: Any,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    evidence_records = {
        str(item.get("key")): item
        for item in catalog.get("sourceEvidence", [])
        if isinstance(item, dict) and item.get("key")
    }
    topic_result_cache: dict[str, dict[str, Any]] = {}
    rendered: list[dict[str, Any]] = []
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        key = str(item.get("key") or "").strip()
        label = str(item.get("label") or key).strip()
        label_display = label
        headline = None
        if kind == "source":
            label_display = humanize_knowledge_source_label(label)
        elif kind == "evidence":
            evidence_record = evidence_records.get(key)
            if isinstance(evidence_record, dict):
                evidence_display, _ = knowledge_display_evidence([evidence_record])
                if evidence_display:
                    label_display = str(evidence_display[0].get("claimDisplay") or evidence_display[0].get("claim") or label).strip()
        else:
            topic_lookup_key = key
            if topic_lookup_key:
                if topic_lookup_key not in topic_result_cache:
                    topic_result_cache[topic_lookup_key] = build_knowledge_query_result(topic_lookup_key, catalog=catalog)
                topic_result = topic_result_cache[topic_lookup_key]
                label_display = str(topic_result.get("resolvedTopicLabel") or label).strip()
                headline = str(topic_result.get("headline") or "").strip() or None
        preview = humanize_knowledge_review_reason(item.get("reason") or "")
        query_command = None
        primary_command = None
        if kind == "source" and key:
            query_command = query_source_command(key)
            primary_command = query_source_command(key, rebuild=True)
        elif kind in {"topic", "fact", "worknet"} and key:
            query_command = query_knowledge_command(key)
            primary_command = query_knowledge_command(key, rebuild=True)
        elif kind == "evidence":
            evidence_record = evidence_records.get(key)
            topic_key = str(evidence_record.get("topicKey") or "").strip() if isinstance(evidence_record, dict) else ""
            if topic_key:
                query_command = query_knowledge_command(topic_key)
                primary_command = query_knowledge_command(topic_key, rebuild=True)
        payload = build_normalized_knowledge_highlight(
            kind=kind or "entry",
            fields=REVIEW_QUEUE_HIGHLIGHT_FIELDS,
            key=key,
            label=label_display or label,
            headline=headline,
            preview=preview,
            query_command=query_command or item.get("command"),
            primary_command=primary_command or item.get("command"),
            freshness_status="affected",
            research_tier="queued",
            extra={
                "kind": kind,
                "kindDisplay": KNOWLEDGE_QUEUE_KIND_LABELS.get(kind, kind),
                "label": label,
                "labelDisplay": label_display,
                "priority": item.get("priority"),
                "priorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(str(item.get("priority") or "").strip()),
                "description": preview,
            },
        )
        rendered.append(
            payload
        )
    return rendered


def knowledge_topic_recommendations(
    topic: str,
    label: str,
    *,
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
    capability_report: Optional[dict[str, Any]],
    freshness: Any,
    impact_matches: list[dict[str, Any]],
    source_records: Optional[dict[str, dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    return knowledge_topic_recommendations_payload(
        topic,
        label,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet,
        capability_report=capability_report,
        freshness=freshness,
        impact_matches=impact_matches,
        source_records=source_records,
        dependencies={
            "build_playbook_command": build_playbook_command,
            "build_skill_inspect_command": build_skill_inspect_command,
            "frontload_user_action_labels": frontload_user_action_labels,
            "humanize_knowledge_source_label": humanize_knowledge_source_label,
            "knowledge_freshness_affected_items": knowledge_freshness_affected_items,
            "knowledge_resolved_topic_key": knowledge_resolved_topic_key,
            "knowledge_topic_execution_state": knowledge_topic_execution_state,
            "knowledge_worknet_metadata": knowledge_worknet_metadata,
            "preferred_worknet_source_keys_for_runtime_state": preferred_worknet_source_keys_for_runtime_state,
            "prioritize_action_entries": prioritize_action_entries,
            "query_knowledge_command": query_knowledge_command,
            "query_source_command": query_source_command,
            "render_argv": render_argv,
            "run_worknet_command": run_worknet_command,
            "scan_worknets_command": scan_worknets_command,
        },
    )


def build_knowledge_query_result(
    topic: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_knowledge_query_result_payload(
        topic,
        catalog=catalog,
        dependencies={
            "KNOWLEDGE_ATLAS_QUERY_FIELDS": KNOWLEDGE_ATLAS_QUERY_FIELDS,
            "KNOWLEDGE_QUERY_FIELDS": KNOWLEDGE_QUERY_FIELDS,
            "KNOWLEDGE_QUEUE_PRIORITY_RANK": KNOWLEDGE_QUEUE_PRIORITY_RANK,
            "KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS": KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS,
            "action_details_from_ui_actions": action_details_from_ui_actions,
            "annotate_research_action_details": annotate_research_action_details,
            "append_unique_action_detail": append_unique_action_detail,
            "build_concept_query_result": build_concept_query_result,
            "build_knowledge_catalog": build_knowledge_catalog,
            "build_knowledge_review_queue": build_knowledge_review_queue,
            "build_research_action_groups": build_research_action_groups,
            "build_skill_inspect_command": build_skill_inspect_command,
            "canonical_topic_narrative": canonical_topic_narrative,
            "capability_reports_by_worknet_key": capability_reports_by_worknet_key,
            "compact_preview_text": compact_preview_text,
            "execution_state_payload": execution_state_payload,
            "find_concept_match": find_concept_match,
            "find_topic_directory_entry": find_topic_directory_entry,
            "frontload_user_action_labels": frontload_user_action_labels,
            "humanize_knowledge_source_label": humanize_knowledge_source_label,
            "join_product_sentences": join_product_sentences,
            "knowledge_display_changed_sources": knowledge_display_changed_sources,
            "knowledge_display_citations": knowledge_display_citations,
            "knowledge_display_dossier": knowledge_display_dossier,
            "knowledge_display_evidence": knowledge_display_evidence,
            "knowledge_display_freshness": knowledge_display_freshness,
            "knowledge_display_review_queue_entries": knowledge_display_review_queue_entries,
            "knowledge_display_source_fact": knowledge_display_source_fact,
            "knowledge_display_source_impact": knowledge_display_source_impact,
            "knowledge_display_topic_label": knowledge_display_topic_label,
            "knowledge_display_worknet": knowledge_display_worknet,
            "knowledge_focus_topics_payload": knowledge_focus_topics_payload,
            "knowledge_related_reference_highlights": knowledge_related_reference_highlights,
            "knowledge_related_source_highlights": knowledge_related_source_highlights,
            "knowledge_resolved_topic_key": knowledge_resolved_topic_key,
            "knowledge_review_queue_recommendation": knowledge_review_queue_recommendation,
            "knowledge_review_queue_summary_text": knowledge_review_queue_summary_text,
            "knowledge_runtime_probe_display_for_topic": knowledge_runtime_probe_display_for_topic,
            "knowledge_runtime_probe_evidence_entries": knowledge_runtime_probe_evidence_entries,
            "knowledge_source_action_description": knowledge_source_action_description,
            "knowledge_source_records_from_catalog": knowledge_source_records_from_catalog,
            "knowledge_topic_citations": knowledge_topic_citations,
            "knowledge_topic_execution_state": knowledge_topic_execution_state,
            "knowledge_topic_headline": knowledge_topic_headline,
            "knowledge_topic_plain_language": knowledge_topic_plain_language,
            "knowledge_topic_recommendations": knowledge_topic_recommendations,
            "knowledge_topic_summary": knowledge_topic_summary,
            "knowledge_topic_worknet_context": knowledge_topic_worknet_context,
            "knowledge_worknet_metadata": knowledge_worknet_metadata,
            "load_cached_capability_bundle": load_cached_capability_bundle,
            "load_cached_knowledge_catalog": load_cached_knowledge_catalog,
            "load_cached_knowledge_review_queue": load_cached_knowledge_review_queue,
            "normalize_concept_payload": normalize_concept_payload,
            "normalize_glossary_item_payload": normalize_glossary_item_payload,
            "normalize_knowledge_atlas_gap_payload": normalize_knowledge_atlas_gap_payload,
            "normalize_knowledge_directory_entry_payload": normalize_knowledge_directory_entry_payload,
            "normalize_knowledge_overview_payload": normalize_knowledge_overview_payload,
            "normalize_knowledge_review_queue_summary": normalize_knowledge_review_queue_summary,
            "normalize_query_payload": normalize_query_payload,
            "normalize_source_directory_entry_payload": normalize_source_directory_entry_payload,
            "preferred_worknet_source_keys_for_runtime_state": preferred_worknet_source_keys_for_runtime_state,
            "prioritize_action_entries": prioritize_action_entries,
            "query_knowledge_command": query_knowledge_command,
            "query_source_command": query_source_command,
            "ranked_knowledge_review_queue_entries": ranked_knowledge_review_queue_entries,
            "render_argv": render_argv,
            "scan_worknets_command": scan_worknets_command,
            "state_context": state_context,
            "summarize_knowledge_review_queue": summarize_knowledge_review_queue,
        },
    )


def build_concept_query_result(
    topic: str,
    concept_match: dict[str, Any],
    *,
    catalog: Optional[dict[str, Any]] = None,
    source_impact: Optional[dict[str, Any]] = None,
    topic_freshness_catalog: Optional[dict[str, Any]] = None,
    knowledge_review_queue: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_concept_query_result_payload(
        topic,
        concept_match,
        catalog=catalog,
        source_impact=source_impact,
        topic_freshness_catalog=topic_freshness_catalog,
        knowledge_review_queue=knowledge_review_queue,
        dependencies={
            "KNOWLEDGE_QUERY_FIELDS": KNOWLEDGE_QUERY_FIELDS,
            "KNOWLEDGE_QUEUE_PRIORITY_RANK": KNOWLEDGE_QUEUE_PRIORITY_RANK,
            "action_details_from_ui_actions": action_details_from_ui_actions,
            "annotate_research_action_details": annotate_research_action_details,
            "build_knowledge_catalog": build_knowledge_catalog,
            "build_knowledge_review_queue": build_knowledge_review_queue,
            "build_research_action_groups": build_research_action_groups,
            "compact_preview_text": compact_preview_text,
            "execution_state_payload": execution_state_payload,
            "find_topic_directory_entry": find_topic_directory_entry,
            "frontload_user_action_labels": frontload_user_action_labels,
            "knowledge_action_description": knowledge_action_description,
            "knowledge_display_citations": knowledge_display_citations,
            "knowledge_display_evidence": knowledge_display_evidence,
            "knowledge_display_freshness": knowledge_display_freshness,
            "knowledge_display_source_impact": knowledge_display_source_impact,
            "knowledge_related_reference_highlights": knowledge_related_reference_highlights,
            "knowledge_related_source_highlights": knowledge_related_source_highlights,
            "knowledge_source_action_description": knowledge_source_action_description,
            "knowledge_source_records_from_catalog": knowledge_source_records_from_catalog,
            "knowledge_topic_citations": knowledge_topic_citations,
            "load_cached_knowledge_catalog": load_cached_knowledge_catalog,
            "load_cached_knowledge_review_queue": load_cached_knowledge_review_queue,
            "normalize_concept_payload": normalize_concept_payload,
            "normalize_query_payload": normalize_query_payload,
            "query_knowledge_command": query_knowledge_command,
            "summarize_knowledge_review_queue": summarize_knowledge_review_queue,
        },
    )


def knowledge_display_glossary_items(items: Any) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        rendered.append(
            normalize_glossary_item_payload({
                "term": item.get("term"),
                "aliases": item.get("aliases", []),
                "plainLanguage": item.get("plainLanguage"),
                "definition": item.get("definition"),
                "whyItMatters": item.get("whyItMatters"),
                "relatedTopics": item.get("relatedTopics", []),
            })
        )
    return rendered


def build_source_query_result(
    source_key: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_source_query_result_payload(
        source_key,
        catalog=catalog,
        dependencies={
            "SOURCE_QUERY_FIELDS": SOURCE_QUERY_FIELDS,
            "action_details_from_ui_actions": action_details_from_ui_actions,
            "annotate_research_action_details": annotate_research_action_details,
            "append_unique_action_detail": append_unique_action_detail,
            "build_knowledge_catalog": build_knowledge_catalog,
            "build_knowledge_query_result": build_knowledge_query_result,
            "build_normalized_knowledge_highlight": build_normalized_knowledge_highlight,
            "build_research_action_groups": build_research_action_groups,
            "capability_reports_by_worknet_key": capability_reports_by_worknet_key,
            "compact_preview_text": compact_preview_text,
            "execution_state_payload": execution_state_payload,
            "frontload_user_action_labels": frontload_user_action_labels,
            "humanize_knowledge_source_label": humanize_knowledge_source_label,
            "join_product_sentences": join_product_sentences,
            "knowledge_action_description": knowledge_action_description,
            "knowledge_display_citations": knowledge_display_citations,
            "knowledge_display_drift_item": knowledge_display_drift_item,
            "knowledge_display_evidence": knowledge_display_evidence,
            "knowledge_display_glossary_items": knowledge_display_glossary_items,
            "knowledge_display_source_impact": knowledge_display_source_impact,
            "knowledge_display_source_record": knowledge_display_source_record,
            "knowledge_display_worknet": knowledge_display_worknet,
            "knowledge_runtime_probe_count": knowledge_runtime_probe_count,
            "knowledge_runtime_probe_display": knowledge_runtime_probe_display,
            "knowledge_runtime_probe_display_for_source": knowledge_runtime_probe_display_for_source,
            "knowledge_runtime_probe_evidence_entries": knowledge_runtime_probe_evidence_entries,
            "knowledge_runtime_probe_summary_sentence": knowledge_runtime_probe_summary_sentence,
            "load_cached_knowledge_catalog": load_cached_knowledge_catalog,
            "normalize_query_payload": normalize_query_payload,
            "normalize_review_scope_payload": normalize_review_scope_payload,
            "prioritize_action_entries": prioritize_action_entries,
            "query_knowledge_command": query_knowledge_command,
            "query_source_command": query_source_command,
        },
    )


def build_changed_sources_query_result(
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return build_changed_sources_query_result_payload(
        catalog=catalog,
        dependencies={
            "CHANGED_SOURCES_QUERY_FIELDS": CHANGED_SOURCES_QUERY_FIELDS,
            "action_details_from_ui_actions": action_details_from_ui_actions,
            "annotate_research_action_details": annotate_research_action_details,
            "build_knowledge_catalog": build_knowledge_catalog,
            "build_knowledge_review_queue": build_knowledge_review_queue,
            "build_research_action_groups": build_research_action_groups,
            "changed_source_highlight_entry": changed_source_highlight_entry,
            "execution_state_payload": execution_state_payload,
            "frontload_user_action_labels": frontload_user_action_labels,
            "humanize_knowledge_source_label": humanize_knowledge_source_label,
            "knowledge_display_changed_sources": knowledge_display_changed_sources,
            "knowledge_display_review_queue_entries": knowledge_display_review_queue_entries,
            "knowledge_display_source_impact": knowledge_display_source_impact,
            "knowledge_review_queue_summary_text": knowledge_review_queue_summary_text,
            "load_cached_knowledge_catalog": load_cached_knowledge_catalog,
            "load_cached_knowledge_review_queue": load_cached_knowledge_review_queue,
            "normalize_query_payload": normalize_query_payload,
            "query_source_command": query_source_command,
            "ranked_knowledge_review_queue_entries": ranked_knowledge_review_queue_entries,
            "summarize_knowledge_review_queue": summarize_knowledge_review_queue,
        },
    )


def knowledge_catalog_topic_keys(catalog: Any) -> list[str]:
    if not isinstance(catalog, dict):
        return []
    ordered_keys: list[str] = []
    seen: set[str] = set()
    for bucket in ("topicDossiers", "sourceFacts", "worknets"):
        items = catalog.get(bucket, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            ordered_keys.append(key)
    return ordered_keys


def knowledge_index_surface_level(item: Any) -> str:
    if not isinstance(item, dict):
        return "reference"
    if str(item.get("kind") or "").strip() != "fact":
        return "topic"
    raw_key = str(item.get("rawKey") or item.get("key") or "").strip().lower()
    return "topic" if raw_key in KNOWLEDGE_DIRECTORY_FACT_KEYS else "reference"


def knowledge_directory_key_for_item(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    raw_key = str(item.get("rawKey") or item.get("key") or "").strip().lower()
    mapped = KNOWLEDGE_DIRECTORY_FACT_KEYS.get(raw_key)
    if mapped:
        return mapped
    canonical = str(item.get("canonicalTopicKey") or item.get("key") or "").strip().lower()
    return canonical


def build_knowledge_topic_index(catalog: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    return build_knowledge_topic_index_payload(
        catalog,
        dependencies={
            "KNOWLEDGE_DIRECTORY_FACT_KEYS": KNOWLEDGE_DIRECTORY_FACT_KEYS,
            "build_knowledge_catalog": build_knowledge_catalog,
            "build_knowledge_query_result": build_knowledge_query_result,
            "capability_reports_by_worknet_key": capability_reports_by_worknet_key,
            "join_product_sentences": join_product_sentences,
            "knowledge_catalog_topic_keys": knowledge_catalog_topic_keys,
            "knowledge_first_non_empty": knowledge_first_non_empty,
            "knowledge_runtime_augmented_preview": knowledge_runtime_augmented_preview,
            "knowledge_runtime_probe_count": knowledge_runtime_probe_count,
            "knowledge_runtime_probe_display_from_catalog": knowledge_runtime_probe_display_from_catalog,
            "knowledge_runtime_probe_summary_sentence": knowledge_runtime_probe_summary_sentence,
            "load_cached_capability_bundle": load_cached_capability_bundle,
            "load_cached_knowledge_catalog": load_cached_knowledge_catalog,
            "query_knowledge_command": query_knowledge_command,
            "state_context": state_context,
        },
    )


def build_knowledge_topic_directory(topic_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    directory: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in topic_index:
        if not isinstance(item, dict):
            continue
        if knowledge_index_surface_level(item) != "topic":
            continue
        directory_key = knowledge_directory_key_for_item(item)
        if not directory_key or directory_key in seen:
            continue
        seen.add(directory_key)
        normalized = dict(item)
        normalized["key"] = directory_key
        normalized["surfaceLevel"] = "topic"
        directory.append(normalized)
    return directory


def build_knowledge_reference_index(topic_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for item in topic_index:
        if not isinstance(item, dict):
            continue
        if knowledge_index_surface_level(item) != "reference":
            continue
        normalized = dict(item)
        normalized["surfaceLevel"] = "reference"
        references.append(normalized)
    return references


def knowledge_source_directory_sort_key(item: Any) -> tuple[int, int, int, int, str]:
    item = item if isinstance(item, dict) else {}
    freshness = str(item.get("freshnessStatus") or "").strip().lower()
    freshness_rank = {"affected": 0, "stable": 1, "unknown": 2}
    priority_rank = KNOWLEDGE_QUEUE_PRIORITY_RANK.get(str(item.get("highestPriority") or "low").strip().lower(), 0)
    core_source_rank = {
        "awp-skill": 0,
        "awp-live-query": 1,
        "awp-whitepaper": 2,
        "awp-home": 3,
        "awp-worknets": 4,
        "awp-aip": 5,
        "awp-blog": 6,
    }
    key = str(item.get("key") or "").strip()
    label = str(item.get("label") or key).strip().lower()
    return (
        freshness_rank.get(freshness, 3),
        -priority_rank,
        core_source_rank.get(key, 99),
        0 if str(item.get("worknetKey") or "").strip() else 1,
        label,
    )


def build_knowledge_source_directory(catalog: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    return build_knowledge_source_directory_payload(
        catalog,
        dependencies={
            "build_knowledge_catalog": build_knowledge_catalog,
            "capability_reports_by_worknet_key": capability_reports_by_worknet_key,
            "compact_preview_text": compact_preview_text,
            "humanize_knowledge_source_label": humanize_knowledge_source_label,
            "knowledge_display_drift_item": knowledge_display_drift_item,
            "knowledge_display_source_impact": knowledge_display_source_impact,
            "knowledge_display_source_record": knowledge_display_source_record,
            "knowledge_runtime_augmented_preview": knowledge_runtime_augmented_preview,
            "knowledge_runtime_probe_display_from_catalog": knowledge_runtime_probe_display_from_catalog,
            "knowledge_source_directory_sort_key": knowledge_source_directory_sort_key,
            "knowledge_source_records_from_catalog": knowledge_source_records_from_catalog,
            "load_cached_capability_bundle": load_cached_capability_bundle,
            "load_cached_knowledge_catalog": load_cached_knowledge_catalog,
            "query_source_command": query_source_command,
            "state_context": state_context,
        },
    )


def apply_runtime_summary_to_knowledge_entry(
    entry: dict[str, Any],
    *,
    runtime_probe_display: Any,
) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return entry
    runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
    if not runtime_summary:
        return entry
    normalized = dict(entry)
    normalized["runtimeSummary"] = runtime_summary
    normalized["runtimeProbeCount"] = knowledge_runtime_probe_count(runtime_probe_display) or None
    summary_text = str(normalized.get("summary") or "").strip()
    if runtime_summary not in summary_text:
        summary_text = join_product_sentences([summary_text, runtime_summary]) or runtime_summary
    normalized["summary"] = summary_text or normalized.get("summary")
    normalized["summaryPreview"] = knowledge_runtime_augmented_preview(
        normalized.get("summaryPreview") or normalized.get("plainLanguage") or summary_text,
        runtime_summary,
        headline=normalized.get("headline"),
        max_chars=140,
        max_sentences=2,
    ) if summary_text else normalized.get("summaryPreview")
    return normalized


def annotate_knowledge_catalog_runtime_summaries(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    capability_reports = capability_reports_by_worknet_key(
        bundle=load_cached_capability_bundle(state_context()),
    )
    source_directory = normalized.get("sourceDirectory")
    if isinstance(source_directory, list):
        updated_sources: list[dict[str, Any]] = []
        for item in source_directory:
            if not isinstance(item, dict):
                continue
            runtime_probe_display = knowledge_runtime_probe_display_from_catalog(
                normalized,
                source_keys=[item.get("key")],
                worknet_key=str(item.get("worknetKey") or "").strip() or None,
                capability_report=capability_reports.get(str(item.get("worknetKey") or "").strip()) if str(item.get("worknetKey") or "").strip() else None,
            )
            updated_sources.append(
                apply_runtime_summary_to_knowledge_entry(
                    item,
                    runtime_probe_display=runtime_probe_display,
                )
            )
        normalized["sourceDirectory"] = updated_sources
    reference_index = normalized.get("referenceIndex")
    if isinstance(reference_index, list):
        updated_references: list[dict[str, Any]] = []
        for item in reference_index:
            if not isinstance(item, dict):
                continue
            runtime_probe_display = knowledge_runtime_probe_display_from_catalog(
                normalized,
                source_keys=item.get("sourceKeys"),
                worknet_key=str(item.get("worknetKey") or "").strip() or None,
                capability_report=capability_reports.get(str(item.get("worknetKey") or "").strip()) if str(item.get("worknetKey") or "").strip() else None,
            )
            updated_references.append(
                apply_runtime_summary_to_knowledge_entry(
                    item,
                    runtime_probe_display=runtime_probe_display,
                )
            )
        normalized["referenceIndex"] = updated_references
    return normalized


def build_knowledge_overview(
    catalog: Optional[dict[str, Any]] = None,
    *,
    topic_index: Optional[list[dict[str, Any]]] = None,
    topic_directory: Optional[list[dict[str, Any]]] = None,
    reference_index: Optional[list[dict[str, Any]]] = None,
    source_directory: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    return build_knowledge_overview_payload(
        catalog,
        topic_index=topic_index,
        topic_directory=topic_directory,
        reference_index=reference_index,
        source_directory=source_directory,
        dependencies={
            "build_knowledge_catalog": build_knowledge_catalog,
            "build_knowledge_reference_index": build_knowledge_reference_index,
            "build_knowledge_source_directory": build_knowledge_source_directory,
            "build_knowledge_topic_directory": build_knowledge_topic_directory,
            "build_knowledge_topic_index": build_knowledge_topic_index,
            "build_normalized_knowledge_highlight": build_normalized_knowledge_highlight,
            "knowledge_freshness_status_display": knowledge_freshness_status_display,
            "knowledge_review_queue_summary_text": knowledge_review_queue_summary_text,
            "knowledge_runtime_augmented_preview": knowledge_runtime_augmented_preview,
            "knowledge_runtime_augmented_summary": knowledge_runtime_augmented_summary,
            "load_cached_knowledge_catalog": load_cached_knowledge_catalog,
            "normalize_affected_topic_payload": normalize_affected_topic_payload,
            "now_iso": now_iso,
            "summarize_knowledge_review_queue": summarize_knowledge_review_queue,
        },
    )


def capability_reports_by_worknet_key(
    *,
    state: Optional[dict[str, Any]] = None,
    bundle: Optional[dict[str, Any]] = None,
) -> dict[str, dict[str, Any]]:
    return capability_reports_by_worknet_key_payload(
        state=state,
        bundle=bundle,
        dependencies={
            "load_cached_capability_bundle": load_cached_capability_bundle,
            "resolve_worknet": resolve_worknet,
            "state_context": state_context,
        },
    )


def load_or_build_knowledge_catalog(state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    state = state or state_context()
    return load_cached_knowledge_catalog(state) or build_knowledge_catalog()


def knowledge_focus_topics_payload(catalog: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    topic_directory = catalog.get("topicDirectory", []) if isinstance(catalog, dict) else []
    topics: list[dict[str, Any]] = []
    for item in topic_directory:
        if not isinstance(item, dict):
            continue
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        payload = build_normalized_knowledge_highlight(
            kind="topic",
            key=item.get("key"),
            label=item.get("label"),
            headline=item.get("headline"),
            preview=preview_text,
            query_command=item.get("queryCommand"),
            primary_command=item.get("primaryCommand"),
            freshness_status=item.get("freshnessStatus"),
            research_tier="overview",
            extra={
                "summary": preview_text,
                "summaryPreview": preview_text,
                "summaryFull": summary_text or item.get("summary"),
                "worknetKey": item.get("worknetKey"),
                "worknetName": item.get("worknetName"),
                "automationLevel": item.get("automationLevel"),
                "riskLevel": item.get("riskLevel"),
                "runtimeSummary": item.get("runtimeSummary"),
                "runtimeProbeCount": item.get("runtimeProbeCount"),
                "status": item.get("freshnessStatus"),
                "statusDisplay": knowledge_freshness_status_display(item.get("freshnessStatus")),
            },
        )
        topics.append(payload)
        if len(topics) >= limit:
            break
    return topics


def knowledge_reference_highlights_payload(catalog: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    reference_index = catalog.get("referenceIndex", []) if isinstance(catalog, dict) else []
    references: list[dict[str, Any]] = []
    for item in reference_index:
        if not isinstance(item, dict):
            continue
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        payload = build_normalized_knowledge_highlight(
            kind="reference",
            key=item.get("key"),
            label=item.get("label"),
            headline=item.get("headline"),
            preview=preview_text,
            query_command=item.get("queryCommand"),
            primary_command=item.get("primaryCommand"),
            freshness_status=item.get("freshnessStatus"),
            research_tier="overview",
            extra={
                "summary": preview_text,
                "summaryPreview": preview_text,
                "summaryFull": summary_text or item.get("summary"),
                "runtimeSummary": item.get("runtimeSummary"),
                "runtimeProbeCount": item.get("runtimeProbeCount"),
            },
        )
        references.append(payload)
        if len(references) >= limit:
            break
    return references


def knowledge_source_highlights_payload(catalog: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    source_directory = catalog.get("sourceDirectory", []) if isinstance(catalog, dict) else []
    highlights: list[dict[str, Any]] = []
    for item in source_directory:
        if not isinstance(item, dict):
            continue
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        payload = build_normalized_knowledge_highlight(
            kind="source",
            key=item.get("key"),
            label=item.get("label"),
            headline=item.get("headline"),
            preview=preview_text,
            query_command=item.get("queryCommand"),
            primary_command=item.get("primaryCommand"),
            freshness_status=item.get("freshnessStatus"),
            research_tier="overview",
            extra={
                "summary": preview_text,
                "summaryPreview": preview_text,
                "summaryFull": summary_text or item.get("summary"),
                "highestPriority": item.get("highestPriority"),
                "worknetKey": item.get("worknetKey"),
                "kindDisplay": item.get("kindDisplay"),
                "runtimeSummary": item.get("runtimeSummary"),
                "runtimeProbeCount": item.get("runtimeProbeCount"),
            },
        )
        highlights.append(payload)
        if len(highlights) >= limit:
            break
    return highlights


def find_topic_directory_entry(
    topic_directory: Any,
    *,
    key: Optional[str] = None,
    worknet_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(topic_directory, list):
        return None
    normalized_key = str(key or "").strip().lower()
    normalized_worknet_key = str(worknet_key or "").strip().lower()
    for item in topic_directory:
        if not isinstance(item, dict):
            continue
        item_key = str(item.get("key") or "").strip().lower()
        item_worknet_key = str(item.get("worknetKey") or "").strip().lower()
        if normalized_key and item_key == normalized_key:
            return item
        if normalized_worknet_key and item_worknet_key == normalized_worknet_key:
            return item
    return None


def knowledge_action_description(item: Any) -> str:
    return knowledge_highlight_action_description(item, action="view")


def knowledge_source_action_description(item: Any) -> str:
    return knowledge_highlight_action_description(item, action="source-view")


def knowledge_refresh_action_description(item: Any) -> str:
    return knowledge_highlight_action_description(item, action="refresh")


def knowledge_highlight_preview_text(item: Any) -> str:
    item = item if isinstance(item, dict) else {}
    return strip_sentence_end(
        item.get("preview")
        or item.get("summaryPreview")
        or item.get("summary")
        or item.get("headline")
        or item.get("label")
    )


def knowledge_runtime_augmented_summary(
    summary: Any,
    runtime_summary: Any,
) -> Optional[str]:
    summary_text = str(summary or "").strip()
    runtime_text = str(runtime_summary or "").strip()
    if runtime_text:
        runtime_core = strip_sentence_end(runtime_text)
        duplicate_pattern = re.compile(
            rf"(?:{re.escape(runtime_core)}(?:[.!?]?\s*)){{2,}}"
        )
        summary_text = duplicate_pattern.sub(runtime_core, summary_text).strip()
    if runtime_text:
        normalized_summary = strip_sentence_end(summary_text)
        normalized_runtime = strip_sentence_end(runtime_text)
        if normalized_runtime and normalized_runtime in normalized_summary:
            return summary_text
    if runtime_text and runtime_text in summary_text:
        return summary_text
    text = join_product_sentences(
        [
            summary_text,
            runtime_text,
        ]
    )
    return text or summary_text or None


def knowledge_runtime_augmented_preview(
    summary: Any,
    runtime_summary: Any,
    *,
    headline: Any = None,
    max_chars: int = 140,
    max_sentences: int = 2,
) -> Optional[str]:
    summary_text = str(summary or "").strip()
    runtime_text = str(runtime_summary or "").strip()
    headline_text = str(headline or "").strip()
    if not runtime_text:
        return compact_preview_text(summary_text or headline_text, max_chars=max_chars, max_sentences=max_sentences) if (summary_text or headline_text) else None
    summary_text = knowledge_runtime_augmented_summary(summary_text, runtime_text) or summary_text
    normalized_summary = strip_sentence_end(summary_text)
    normalized_runtime = strip_sentence_end(runtime_text)
    base_text = summary_text
    if normalized_runtime and normalized_runtime in normalized_summary:
        base_text = re.sub(
            rf"(?:[.!?]?\s*)?{re.escape(normalized_runtime)}(?:[.!?]?\s*)?",
            " ",
            summary_text,
            count=1,
        )
        base_text = re.sub(r"\s+", " ", base_text).strip()
    if not base_text and headline_text and strip_sentence_end(headline_text) != normalized_runtime:
        base_text = headline_text
    if len(runtime_text) >= max_chars - 12:
        return compact_preview_text(runtime_text, max_chars=max_chars, max_sentences=1)
    reserve = min(max(len(normalized_runtime) + 4, 48), max_chars - 18) if normalized_runtime else 48
    base_max_chars = max(18, min(72, max_chars - reserve))
    base_preview = None
    for candidate in preview_candidate_fragments(base_text):
        candidate_preview = compact_preview_text(candidate, max_chars=base_max_chars, max_sentences=1)
        if not isinstance(candidate_preview, str):
            continue
        candidate_preview = candidate_preview.rstrip()
        if candidate_preview.endswith((";", ":", ",")):
            boundary = max(
                candidate_preview.rfind("   "),
                candidate_preview.rfind("   "),
                candidate_preview.rfind("   "),
                candidate_preview.rfind(" "),
            )
            if boundary > 0:
                candidate_preview = candidate_preview[:boundary].rstrip()
        combined_candidate = join_product_sentences([candidate_preview, runtime_text])
        if len(combined_candidate) <= max_chars:
            base_preview = candidate_preview
            if "   " not in candidate_preview:
                break
    if not base_preview and headline_text and strip_sentence_end(headline_text) != normalized_runtime:
        base_preview = compact_preview_text(headline_text, max_chars=base_max_chars, max_sentences=1)
        if isinstance(base_preview, str):
            base_preview = base_preview.rstrip()
    combined = join_product_sentences([base_preview or base_text, runtime_text]) if (base_preview or base_text) else runtime_text
    preview = compact_preview_text(combined, max_chars=max_chars, max_sentences=max_sentences) if combined else None
    if normalized_runtime and isinstance(preview, str) and normalized_runtime not in strip_sentence_end(preview):
        runtime_only = compact_preview_text(runtime_text, max_chars=max_chars, max_sentences=1)
        if runtime_only:
            return runtime_only
    return preview


def knowledge_highlight_action_description(item: Any, *, action: str = "view") -> str:
    item = item if isinstance(item, dict) else {}
    record_kind = str(item.get("recordKind") or item.get("kind") or "").strip().lower()
    label = str(item.get("labelDisplay") or item.get("label") or item.get("key") or "item").strip()
    preview = knowledge_highlight_preview_text(item) or label
    freshness = str(item.get("freshnessStatus") or "").strip().lower()

    if action == "refresh":
        if freshness == "affected":
            return f"Refresh {label} because an upstream source changed."
        return f"Refresh {label} and rebuild its knowledge snapshot."

    if record_kind == "source" or action == "source-view":
        if freshness == "affected":
            return f"Open {label} because it has pending source changes."
        return f"{preview} Open the source record for details."

    if record_kind == "reference":
        return f"{preview} Open the related reference."
    if record_kind == "fact":
        return f"{preview} Review the supporting fact."
    if record_kind == "worknet":
        return f"{preview} Review the WorkNet context."
    if record_kind == "evidence":
        return f"{preview} Review the supporting evidence claim."
    return f"{preview} Review the knowledge item."


def knowledge_context_for_worknet(catalog: Any, worknet_key: Optional[str]) -> Optional[dict[str, Any]]:
    key = str(worknet_key or "").strip().lower()
    if not key or not isinstance(catalog, dict):
        return None
    topic_directory = catalog.get("topicDirectory", [])
    return find_topic_directory_entry(topic_directory, key=key, worknet_key=key)


def knowledge_related_reference_highlights(
    catalog: Any,
    knowledge_context: Any,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not isinstance(catalog, dict) or not isinstance(knowledge_context, dict):
        return []
    topic_source_keys = {
        str(item).strip()
        for item in knowledge_context.get("sourceKeys", [])
        if str(item).strip()
    }
    topic_label = str(knowledge_context.get("label") or "").strip().lower()
    topic_key = str(knowledge_context.get("key") or "").strip().lower()
    worknet_key = str(knowledge_context.get("worknetKey") or "").strip().lower()
    references = catalog.get("referenceIndex", [])
    ranked: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    for item in references:
        if not isinstance(item, dict):
            continue
        item_label = str(item.get("label") or "").strip().lower()
        item_key = str(item.get("key") or "").strip().lower()
        item_source_keys = {
            str(source_key).strip()
            for source_key in item.get("sourceKeys", [])
            if str(source_key).strip()
        }
        overlap = len(topic_source_keys.intersection(item_source_keys))
        same_label = 1 if topic_label and item_label == topic_label else 0
        key_hint = 1 if topic_key and topic_key in item_key else 0
        special_canonical = 1 if worknet_key and item_key == "live-worknet-canonical" and "awp-live-query" in topic_source_keys else 0
        score = same_label + key_hint + overlap + special_canonical
        strong_match = bool(same_label or key_hint or overlap >= 2 or special_canonical)
        if score <= 0 or not strong_match:
            continue
        ranked.append(((-score, -overlap, item_key), item))
    ranked.sort(key=lambda pair: pair[0])
    highlights: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, item in ranked:
        key = str(item.get("key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        highlights.append(
            build_normalized_knowledge_highlight(
                kind="reference",
                key=key,
                label=item.get("label"),
                headline=item.get("headline"),
                preview=preview_text,
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="related",
                extra={
                    "summary": preview_text,
                    "summaryPreview": preview_text,
                    "summaryFull": summary_text or item.get("summary"),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
        )
        if len(highlights) >= limit:
            break
    return highlights


def knowledge_related_source_highlights(
    catalog: Any,
    knowledge_context: Any,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not isinstance(catalog, dict) or not isinstance(knowledge_context, dict):
        return []
    topic_source_keys = {
        str(item).strip()
        for item in knowledge_context.get("sourceKeys", [])
        if str(item).strip()
    }
    worknet_key = str(knowledge_context.get("worknetKey") or "").strip().lower()
    source_directory = catalog.get("sourceDirectory", [])
    ranked: list[dict[str, Any]] = []
    for item in source_directory:
        if not isinstance(item, dict):
            continue
        item_key = str(item.get("key") or "").strip()
        item_worknet_key = str(item.get("worknetKey") or "").strip().lower()
        if item_key not in topic_source_keys and (not worknet_key or item_worknet_key != worknet_key):
            continue
        ranked.append(item)
    ranked.sort(key=knowledge_source_directory_sort_key)
    highlights: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in ranked:
        key = str(item.get("key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        highlights.append(
            build_normalized_knowledge_highlight(
                kind="source",
                key=key,
                label=item.get("label"),
                headline=item.get("headline"),
                preview=preview_text,
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="related",
                extra={
                    "summary": preview_text,
                    "summaryPreview": preview_text,
                    "summaryFull": summary_text or item.get("summary"),
                    "highestPriority": item.get("highestPriority"),
                    "worknetKey": item.get("worknetKey"),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
        )
        if len(highlights) >= limit:
            break
    return highlights


def compact_knowledge_context(item: Any) -> Optional[dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    payload = build_normalized_knowledge_highlight(
        kind="topic",
        key=item.get("key"),
        label=item.get("label"),
        headline=item.get("headline"),
        preview=item.get("summaryPreview") or item.get("summary"),
        query_command=item.get("queryCommand"),
        primary_command=item.get("primaryCommand"),
        freshness_status=item.get("freshnessStatus"),
        research_tier="current",
        extra={
            "summary": item.get("summaryPreview") or item.get("summary"),
            "summaryPreview": item.get("summaryPreview"),
            "summaryFull": item.get("summary"),
            "affectedSourceKeys": item.get("affectedSourceKeys", []),
            "worknetKey": item.get("worknetKey"),
            "worknetName": item.get("worknetName"),
            "automationLevel": item.get("automationLevel"),
            "riskLevel": item.get("riskLevel"),
            "runtimeSummary": item.get("runtimeSummary"),
            "runtimeProbeCount": item.get("runtimeProbeCount"),
            "status": item.get("freshnessStatus"),
            "statusDisplay": knowledge_freshness_status_display(item.get("freshnessStatus")),
        },
    )
    return payload


def attach_knowledge_to_capability_reports(
    reports: list[dict[str, Any]],
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    catalog = catalog if isinstance(catalog, dict) else load_or_build_knowledge_catalog()
    enriched: list[dict[str, Any]] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        normalized = dict(report)
        profile = (
            resolve_worknet(str(report.get("worknetId") or ""))
            or resolve_worknet(str(report.get("name") or ""))
            or resolve_worknet(str(report.get("symbol") or ""))
        )
        worknet_key = str(profile.get("key") or "") if isinstance(profile, dict) else ""
        knowledge_context = compact_knowledge_context(
            knowledge_context_for_worknet(catalog, worknet_key)
        )
        reference_highlights = knowledge_related_reference_highlights(
            catalog,
            knowledge_context,
        ) if isinstance(knowledge_context, dict) else []
        source_highlights = knowledge_related_source_highlights(
            catalog,
            knowledge_context,
        ) if isinstance(knowledge_context, dict) else []
        normalized["knowledgeContext"] = knowledge_context
        normalized["knowledgeReferenceHighlights"] = reference_highlights
        normalized["knowledgeSourceHighlights"] = source_highlights
        caveat = capability_knowledge_caveat(knowledge_context, source_highlights)
        reason = str(normalized.get("reason") or "").strip()
        if caveat and caveat not in reason:
            normalized["reason"] = f"{strip_sentence_end(reason)}. {caveat}".strip() if reason else caveat
        enriched.append(normalized)
    return enriched
