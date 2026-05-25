"""Runtime payload extraction helpers."""

from __future__ import annotations

import shlex
from typing import Any, Optional

from awp_workstation.worknets import resolve_worknet


def runtime_message(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("user_message", "message", "detail", "summary", "title"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().splitlines()[0]
    return None


def runtime_payload_error_summary(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        suggestion = error.get("suggestion")
        if isinstance(suggestion, str) and suggestion.strip():
            return suggestion.strip()
        code = error.get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    if payload.get("ok") is False:
        if isinstance(error, dict):
            suggestion = error.get("suggestion")
            if isinstance(suggestion, str) and suggestion.strip():
                return suggestion.strip()
            code = error.get("code")
            if isinstance(code, str) and code.strip():
                return code.strip()
        message = runtime_message(payload)
        if message:
            return message
    status = str(payload.get("status") or "").lower()
    if status == "error":
        data = payload.get("data")
        if isinstance(data, dict):
            suggestion = data.get("suggestion")
            if isinstance(suggestion, str) and suggestion.strip():
                return suggestion.strip()
        message = runtime_message(payload)
        if message:
            return message
    if isinstance(error, str) and error.strip():
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        return error.strip()
    return None


def runtime_payload_has_blocker(payload: Any) -> bool:
    return runtime_payload_error_summary(payload) is not None


def runtime_action_map(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    internal = payload.get("_internal")
    if not isinstance(internal, dict):
        return {}
    action_map = internal.get("action_map")
    if not isinstance(action_map, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in action_map.items():
        if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
            normalized[key.strip()] = value.strip()
    return normalized

def runtime_guidance_worknet_key(
    worknet_key: Optional[str],
    *,
    labels: Any = None,
    action_map: Any = None,
    message: Any = None,
) -> str:
    candidate = str(worknet_key or "").strip().lower()
    if candidate:
        return candidate
    labels_list = [str(item).strip().lower() for item in labels if isinstance(item, str)] if isinstance(labels, list) else []
    commands = [str(value).strip().lower() for value in action_map.values()] if isinstance(action_map, dict) else []
    message_text = str(message or "").strip().lower()
    if (
        any(item in {"start mining", "check status", "re-initialize", "run diagnostics"} for item in labels_list)
        or any("agent-start" in command or "agent-control status" in command or "run_tool.py doctor" in command for command in commands)
        or "mining environment" in message_text
        or "mining session" in message_text
    ):
        return "mine"
    return ""


def runtime_guidance_worknet_name(worknet_key: Optional[str]) -> str:
    key = str(worknet_key or "").strip().lower()
    if not key:
        return "Current"
    explicit_names = {
        "awp-skill": "AWP RootNet Skill",
        "awp-wallet": "AWP Wallet",
    }
    if key in explicit_names:
        return explicit_names[key]
    profile = resolve_worknet(key)
    if isinstance(profile, dict):
        name = str(profile.get("name") or profile.get("key") or key).strip()
        if name.endswith(" WorkNet"):
            name = name[:-len(" WorkNet")].strip()
        if name:
            return name
    return key.replace("-", " ").strip().title() or "Current"


def runtime_payload_worknet_key(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    playbook = payload.get("playbook")
    if isinstance(playbook, dict):
        worknet_key = str(playbook.get("worknetKey") or "").strip().lower()
        if worknet_key:
            return worknet_key
    for field in ("selectedWorknetKey", "worknetKey"):
        worknet_key = str(payload.get(field) or "").strip().lower()
        if worknet_key:
            return worknet_key
    return ""


def executed_step_result_payload(step: Any) -> Any:
    if not isinstance(step, dict):
        return None
    result = step.get("result")
    if not isinstance(result, dict):
        return None
    return result.get("stdout")


def step_result_payload(step: Any) -> Any:
    if not isinstance(step, dict):
        return None
    result = step.get("result")
    if not isinstance(result, dict):
        return None
    if "stdout" in result:
        return result.get("stdout")
    return result


def runtime_next_command(payload: Any) -> Optional[list[str]]:
    if not isinstance(payload, dict):
        return None
    internal = payload.get("_internal")
    if not isinstance(internal, dict):
        return None
    value = internal.get("next_command")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return shlex.split(value)
    except ValueError:
        return None


def build_executed_step_stdout_display_payload(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
    dependencies: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("build executed step stdout display dependencies are required")
    compact_preview_text = dependencies["compact_preview_text"]
    executed_step_payload_summary_display = dependencies["executed_step_payload_summary_display"]
    extract_runtime_guidance_from_payload = dependencies["extract_runtime_guidance_from_payload"]
    humanize_runtime_guidance_message_display = dependencies["humanize_runtime_guidance_message_display"]
    humanize_runtime_next_command_display = dependencies["humanize_runtime_next_command_display"]
    humanize_runtime_payload_state = dependencies["humanize_runtime_payload_state"]
    normalize_executed_step_stdout_display_payload = dependencies["normalize_executed_step_stdout_display_payload"]
    normalize_runtime_guidance_contract_payload = dependencies["normalize_runtime_guidance_contract_payload"]
    render_argv = dependencies["render_argv"]
    runtime_guidance_preview_display = dependencies["runtime_guidance_preview_display"]
    runtime_message = dependencies["runtime_message"]
    runtime_payload_error_summary = dependencies["runtime_payload_error_summary"]
    should_replace_display_text = dependencies["should_replace_display_text"]
    structured_preview_text = dependencies["structured_preview_text"]

    if payload is None:
        return normalize_executed_step_stdout_display_payload({})
    summary = executed_step_payload_summary_display(worknet_key, step, payload)
    preview = structured_preview_text(payload)
    if isinstance(payload, dict):
        display: dict[str, Any] = {
            "kind": "structured",
            "summary": summary,
            "preview": preview,
        }
        if preview:
            display["previewRaw"] = preview
        state = str(payload.get("state") or "").strip()
        if state:
            display["state"] = state
            display["stateDisplay"] = humanize_runtime_payload_state(state)
        message = runtime_message(payload)
        if message:
            display["message"] = message
            display["messageRaw"] = message
            message_display = humanize_runtime_guidance_message_display(
                worknet_key or None,
                message,
                state=state or None,
            )
            if message_display:
                display["message"] = message_display
                display["messageDisplay"] = message_display
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            display["detail"] = detail.strip()
            display["detailRaw"] = detail.strip()
        error_summary = runtime_payload_error_summary(payload)
        if error_summary and error_summary != message:
            display["errorSummary"] = error_summary
        guidance = extract_runtime_guidance_from_payload(payload, worknet_key=worknet_key or None)
        if isinstance(guidance, dict):
            guidance = dict(guidance)
            if should_replace_display_text(guidance.get("messageDisplay"), summary):
                raw_guidance_message = str(guidance.get("message") or "").strip()
                if raw_guidance_message and raw_guidance_message != summary and "messageRaw" not in guidance:
                    guidance["messageRaw"] = raw_guidance_message
                guidance["message"] = summary
                guidance["messageDisplay"] = summary
            humanized_next_command = humanize_runtime_next_command_display(
                worknet_key or None,
                guidance.get("nextCommand"),
            )
            if humanized_next_command:
                guidance["nextCommandDisplay"] = humanized_next_command
            guidance_preview = runtime_guidance_preview_display(guidance)
            if guidance_preview:
                guidance["previewDisplay"] = guidance_preview
            display["guidance"] = normalize_runtime_guidance_contract_payload(guidance)
            next_command = guidance.get("nextCommand")
            if isinstance(next_command, list) and next_command:
                display["nextCommandDisplay"] = humanize_runtime_next_command_display(
                    worknet_key or None,
                    next_command,
                ) or render_argv([str(part) for part in next_command])
            preview_display = str(guidance.get("previewDisplay") or "").strip()
            if preview_display:
                display["previewDisplay"] = preview_display
        if should_replace_display_text(display.get("messageDisplay"), summary):
            if isinstance(display.get("message"), str) and display.get("message") != summary and "messageRaw" not in display:
                display["messageRaw"] = display.get("message")
            display["message"] = summary
            display["messageDisplay"] = summary
        detail_display = str(display.get("messageDisplay") or display.get("summary") or "").strip()
        if detail_display:
            if isinstance(display.get("detail"), str) and display.get("detail") != detail_display and "detailRaw" not in display:
                display["detailRaw"] = display.get("detail")
            display["detail"] = detail_display
            display["detailDisplay"] = detail_display
        error_display = str(display.get("summary") or display.get("messageDisplay") or "").strip()
        if error_display:
            if isinstance(display.get("errorSummary"), str) and display.get("errorSummary") != error_display and "errorSummaryRaw" not in display:
                display["errorSummaryRaw"] = display.get("errorSummary")
            display["errorSummary"] = error_display
            display["errorSummaryDisplay"] = error_display
        if not isinstance(display.get("previewDisplay"), str):
            preview_display = str(display.get("messageDisplay") or display.get("summary") or "").strip()
            if preview_display:
                display["previewDisplay"] = compact_preview_text(
                    preview_display,
                    max_chars=180,
                    max_sentences=2,
                )
        if isinstance(display.get("previewDisplay"), str):
            display["preview"] = display["previewDisplay"]
            display["structuredPreviewDisplay"] = display["previewDisplay"]
        return normalize_executed_step_stdout_display_payload(display)
    return normalize_executed_step_stdout_display_payload({
        "kind": type(payload).__name__,
        "summary": summary or preview,
        "preview": summary or preview,
        "previewRaw": preview,
        "previewDisplay": summary or preview,
        "structuredPreviewDisplay": summary or preview,
    })


def build_executed_step_result_display_payload(
    worknet_key: str,
    step: dict[str, Any],
    dependencies: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("build executed step result display dependencies are required")
    build_executed_step_stdout_display = dependencies["build_executed_step_stdout_display"]
    compact_preview_text = dependencies["compact_preview_text"]
    executed_step_result_payload = dependencies["executed_step_result_payload"]
    normalize_executed_step_result_display_payload = dependencies["normalize_executed_step_result_display_payload"]

    result = step.get("result")
    if not isinstance(result, dict):
        return None
    payload = executed_step_result_payload(step)
    stdout_display = build_executed_step_stdout_display(worknet_key, step, payload)
    stderr = result.get("stderr")
    stderr_display = compact_preview_text(stderr, max_chars=180, max_sentences=2) if isinstance(stderr, str) and stderr.strip() else None
    code = result.get("code")
    summary = None
    if isinstance(stdout_display, dict):
        summary = str(stdout_display.get("summary") or "").strip() or None
    summary = summary or stderr_display
    if not summary and code is not None:
        summary = f"Process exited with code {code}."
    raw_summary = None
    if isinstance(stdout_display, dict):
        raw_summary = str(
            stdout_display.get("summaryRaw")
            or stdout_display.get("previewRaw")
            or stdout_display.get("messageRaw")
            or ""
        ).strip() or None
    raw_summary = raw_summary or stderr_display
    preview_display = None
    if isinstance(stdout_display, dict):
        preview_display = str(stdout_display.get("previewDisplay") or stdout_display.get("summary") or "").strip() or None
    preview_display = preview_display or summary
    preview_raw = None
    if isinstance(stdout_display, dict):
        preview_raw = str(stdout_display.get("previewRaw") or "").strip() or None
    preview_raw = preview_raw or stderr_display or raw_summary
    payload = {
        "code": code,
        "codeDisplay": f"Exit code {code}" if code is not None else None,
        "summary": summary,
        "summaryDisplay": summary,
        "summaryRaw": raw_summary,
        "preview": preview_display,
        "previewDisplay": preview_display,
        "previewRaw": preview_raw,
        "structuredPreviewDisplay": preview_display,
        "stdoutDisplay": stdout_display,
        "stderrDisplay": stderr_display,
        "stderrDisplayRaw": stderr_display,
    }
    if not isinstance(payload.get("previewDisplay"), str):
        preview_text = str(summary or "").strip()
        if preview_text:
            payload["preview"] = preview_text
            payload["previewDisplay"] = preview_text
            payload["structuredPreviewDisplay"] = preview_text
    return normalize_executed_step_result_display_payload(payload)


def annotate_executed_step_payload(
    step: Any,
    *,
    worknet_key: Optional[str] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> Any:
    if dependencies is None:
        raise ValueError("annotate executed step dependencies are required")
    RESEARCH_HIGHLIGHT_GROUP_RANKS = dependencies["RESEARCH_HIGHLIGHT_GROUP_RANKS"]
    RESEARCH_HIGHLIGHT_TIER_LABELS = dependencies["RESEARCH_HIGHLIGHT_TIER_LABELS"]
    RESEARCH_HIGHLIGHT_TIER_RANKS = dependencies["RESEARCH_HIGHLIGHT_TIER_RANKS"]
    STEP_GROUP_LABELS = dependencies["STEP_GROUP_LABELS"]
    annotate_background_record = dependencies["annotate_background_record"]
    annotate_execution_actions = dependencies["annotate_execution_actions"]
    annotate_parameter_schema_items = dependencies["annotate_parameter_schema_items"]
    annotate_runtime_guidance_payload = dependencies["annotate_runtime_guidance_payload"]
    build_executed_step_result_display = dependencies["build_executed_step_result_display"]
    executed_step_result_payload = dependencies["executed_step_result_payload"]
    humanize_executed_step_detail_display = dependencies["humanize_executed_step_detail_display"]
    humanize_executed_step_label = dependencies["humanize_executed_step_label"]
    humanize_executed_step_reason_display = dependencies["humanize_executed_step_reason_display"]
    humanize_executed_step_status_display = dependencies["humanize_executed_step_status_display"]
    humanize_parameter_error_message = dependencies["humanize_parameter_error_message"]
    render_argv = dependencies["render_argv"]

    if not isinstance(step, dict):
        return step
    normalized = dict(step)
    label = str(normalized.get("label") or "").strip()
    command = render_argv(normalized.get("argv", [])) if isinstance(normalized.get("argv"), list) else None
    policy = str(normalized.get("executionPolicy") or "").strip().lower()
    status = str(normalized.get("status") or "").strip().lower()
    display_label = humanize_executed_step_label(
        label,
        category=normalized.get("category"),
        execution_policy=normalized.get("executionPolicy"),
    ) if label else None
    if display_label:
        normalized["displayLabel"] = display_label
    if status in {"queued_for_confirmation", "awaiting_confirmation"} or policy == "confirmation":
        group_key = "confirmations"
        tier = "current"
    elif status == "started_background":
        group_key = "background"
        tier = "current"
    elif policy in {"probe", "manual-review"} or str(normalized.get("category") or "").strip().lower() == "inspect":
        group_key = "inspect"
        tier = "related"
    elif policy in {"setup", "manual-setup"}:
        group_key = "setup"
        tier = "overview"
    else:
        action_meta = annotate_execution_actions([
            {
                "label": label,
                "command": command,
                "executionPolicy": normalized.get("executionPolicy"),
                "status": normalized.get("status"),
            }
        ])
        action_group_key = str(action_meta[0].get("actionGroupKey") or "").strip() if action_meta else ""
        action_tier = str(action_meta[0].get("actionTier") or "").strip() if action_meta else ""
        group_key = action_group_key or "current"
        tier = action_tier or "current"
    normalized["stepGroupKey"] = group_key
    normalized["stepGroupLabel"] = STEP_GROUP_LABELS.get(group_key, group_key)
    normalized["stepGroupRank"] = RESEARCH_HIGHLIGHT_GROUP_RANKS.get(group_key)
    normalized["stepTier"] = tier
    normalized["stepTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get(tier, tier)
    normalized["stepTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
    normalized["actionGroupKey"] = group_key
    normalized["actionGroupLabel"] = STEP_GROUP_LABELS.get(group_key, group_key)
    normalized["actionGroupRank"] = RESEARCH_HIGHLIGHT_GROUP_RANKS.get(group_key)
    normalized["actionTier"] = tier
    normalized["actionTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get(tier, tier)
    normalized["actionTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
    resolved_worknet_key = str(worknet_key or normalized.get("worknetKey") or "").strip().lower()
    payload = executed_step_result_payload(normalized)
    normalized["statusDisplay"] = humanize_executed_step_status_display(status)
    detail_display = humanize_executed_step_detail_display(resolved_worknet_key, normalized, payload)
    if detail_display:
        normalized["detailDisplay"] = detail_display
    reason_display = humanize_executed_step_reason_display(resolved_worknet_key, normalized, payload)
    if reason_display:
        normalized["reasonDisplay"] = reason_display
    result_display = build_executed_step_result_display(resolved_worknet_key, normalized)
    if isinstance(result_display, dict):
        normalized["resultDisplay"] = result_display
        if result_display.get("summary"):
            normalized["resultSummary"] = result_display.get("summary")
        if result_display.get("previewDisplay"):
            normalized["previewDisplay"] = result_display.get("previewDisplay")
        if result_display.get("stdoutDisplay") is not None:
            normalized["stdoutDisplay"] = result_display.get("stdoutDisplay")
        if result_display.get("stderrDisplay"):
            normalized["stderrDisplay"] = result_display.get("stderrDisplay")
    elif detail_display or reason_display or normalized.get("statusDisplay"):
        normalized["resultSummary"] = detail_display or reason_display or normalized.get("statusDisplay")
    if isinstance(normalized.get("parameterErrors"), list):
        normalized["parameterErrorsDisplay"] = [
            humanize_parameter_error_message(normalized, item) or str(item)
            for item in normalized.get("parameterErrors", [])
        ]
    if isinstance(normalized.get("parameterSchema"), list):
        normalized["parameterSchemaDisplay"] = annotate_parameter_schema_items(normalized.get("parameterSchema"))
    if isinstance(normalized.get("runtimeGuidance"), dict):
        normalized["runtimeGuidance"] = annotate_runtime_guidance_payload(
            normalized.get("runtimeGuidance"),
            worknet_key=resolved_worknet_key or None,
        )
    if isinstance(normalized.get("backgroundProcess"), dict):
        normalized["backgroundProcess"] = annotate_background_record(normalized.get("backgroundProcess"))
    return normalized


def annotate_probe_result_display_payload(
    probe: dict[str, Any],
    *,
    skill_key: str,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("annotate probe result display dependencies are required")
    build_executed_step_result_display = dependencies["build_executed_step_result_display"]
    compact_preview_text = dependencies["compact_preview_text"]
    extract_runtime_guidance_from_payload = dependencies["extract_runtime_guidance_from_payload"]
    humanize_runtime_guidance_message_display = dependencies["humanize_runtime_guidance_message_display"]
    humanize_runtime_next_command_display = dependencies["humanize_runtime_next_command_display"]
    humanize_runtime_payload_state = dependencies["humanize_runtime_payload_state"]
    humanize_runtime_probe_summary_display = dependencies["humanize_runtime_probe_summary_display"]
    probe_result_worknet_key = dependencies["probe_result_worknet_key"]
    runtime_probe_effective_status = dependencies["runtime_probe_effective_status"]
    should_replace_display_text = dependencies["should_replace_display_text"]

    normalized = dict(probe)
    payload = normalized.get("result")
    worknet_key = probe_result_worknet_key(skill_key, normalized)
    effective_status = runtime_probe_effective_status(normalized)
    step_like = {
        "label": normalized.get("label"),
        "status": effective_status,
        "result": {
            "code": normalized.get("code"),
            "stdout": payload,
            "stderr": None if isinstance(payload, (dict, list)) else normalized.get("text"),
        },
    }
    result_display = build_executed_step_result_display(worknet_key, step_like)
    text_display = compact_preview_text(normalized.get("text"), max_chars=220, max_sentences=2)
    if text_display:
        normalized["textDisplay"] = text_display
    if isinstance(result_display, dict):
        normalized["resultDisplay"] = result_display
        if result_display.get("summary"):
            normalized["resultSummary"] = result_display.get("summary")
        if result_display.get("stdoutDisplay") is not None:
            normalized["stdoutDisplay"] = result_display.get("stdoutDisplay")
        if result_display.get("stderrDisplay"):
            normalized["stderrDisplay"] = result_display.get("stderrDisplay")
        if result_display.get("previewDisplay"):
            normalized["previewDisplay"] = result_display.get("previewDisplay")
    if isinstance(payload, dict):
        state = str(payload.get("state") or "").strip()
        if state:
            normalized["stateDisplay"] = humanize_runtime_payload_state(state)
        message_display = humanize_runtime_guidance_message_display(
            worknet_key or None,
            payload.get("user_message") or payload.get("message"),
            state=payload.get("state"),
        )
        if message_display:
            normalized["messageDisplay"] = message_display
        guidance = extract_runtime_guidance_from_payload(payload, worknet_key=worknet_key or None)
        if isinstance(guidance, dict):
            normalized["runtimeGuidanceDisplay"] = guidance
            user_actions_display = guidance.get("userActionsDisplay")
            if isinstance(user_actions_display, list) and user_actions_display:
                normalized["userActionsDisplay"] = user_actions_display
            next_command_display = guidance.get("nextCommandDisplay")
            if isinstance(next_command_display, str) and next_command_display.strip():
                normalized["nextCommandDisplay"] = next_command_display.strip()
            preview_display = guidance.get("previewDisplay")
            if isinstance(preview_display, str) and preview_display.strip():
                normalized["previewDisplay"] = preview_display.strip()
    humanized_summary = humanize_runtime_probe_summary_display(
        worknet_key,
        str(normalized.get("label") or "").strip(),
        status=effective_status,
        payload=payload,
        text=normalized.get("text"),
    )
    if isinstance(humanized_summary, str) and humanized_summary.strip():
        normalized["resultSummary"] = humanized_summary.strip()
        if should_replace_display_text(normalized.get("messageDisplay"), humanized_summary):
            normalized["messageDisplay"] = humanized_summary.strip()
        if should_replace_display_text(normalized.get("previewDisplay"), humanized_summary):
            normalized["previewDisplay"] = humanized_summary.strip()
        if should_replace_display_text(normalized.get("textDisplay"), humanized_summary):
            normalized["textDisplay"] = humanized_summary.strip()
        if isinstance(normalized.get("resultDisplay"), dict):
            result_display = dict(normalized["resultDisplay"])
            current_summary = str(result_display.get("summary") or "").strip()
            if current_summary and current_summary != humanized_summary and not str(result_display.get("summaryRaw") or "").strip():
                result_display["summaryRaw"] = current_summary
            result_display["summary"] = humanized_summary.strip()
            result_display["summaryDisplay"] = humanized_summary.strip()
            current_preview = str(result_display.get("preview") or result_display.get("previewDisplay") or "").strip()
            if current_preview and current_preview != humanized_summary and not str(result_display.get("previewRaw") or "").strip():
                result_display["previewRaw"] = current_preview
            result_display["preview"] = humanized_summary.strip()
            result_display["previewDisplay"] = humanized_summary.strip()
            result_display["structuredPreviewDisplay"] = humanized_summary.strip()
            current_stderr = str(result_display.get("stderrDisplay") or "").strip()
            if current_stderr:
                if current_stderr != humanized_summary and not str(result_display.get("stderrDisplayRaw") or "").strip():
                    result_display["stderrDisplayRaw"] = current_stderr
                result_display["stderrDisplay"] = humanized_summary.strip()
                result_display["stderrDisplayDisplay"] = humanized_summary.strip()
            normalized["resultDisplay"] = result_display
        if isinstance(normalized.get("runtimeGuidanceDisplay"), dict):
            guidance_display = dict(normalized["runtimeGuidanceDisplay"])
            if should_replace_display_text(guidance_display.get("messageDisplay"), humanized_summary):
                raw_guidance_message = str(guidance_display.get("message") or "").strip()
                if raw_guidance_message and raw_guidance_message != humanized_summary and "messageRaw" not in guidance_display:
                    guidance_display["messageRaw"] = raw_guidance_message
                guidance_display["message"] = humanized_summary.strip()
                guidance_display["messageDisplay"] = humanized_summary.strip()
            if should_replace_display_text(guidance_display.get("previewDisplay"), humanized_summary):
                guidance_display["previewDisplay"] = humanized_summary.strip()
            next_command_display = humanize_runtime_next_command_display(
                worknet_key or None,
                guidance_display.get("nextCommand"),
            )
            if next_command_display:
                guidance_display["nextCommandDisplay"] = next_command_display
            normalized["runtimeGuidanceDisplay"] = guidance_display
    if not isinstance(normalized.get("previewDisplay"), str):
        fallback_preview = str(
            normalized.get("messageDisplay")
            or normalized.get("resultSummary")
            or normalized.get("textDisplay")
            or ""
        ).strip()
        if fallback_preview:
            normalized["previewDisplay"] = fallback_preview
    return normalized
