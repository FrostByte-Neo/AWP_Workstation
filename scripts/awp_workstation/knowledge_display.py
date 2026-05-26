"""Knowledge display helpers."""

from __future__ import annotations

from typing import Any, Optional


def humanize_runtime_probe_check_label_payload(
    label: Any,
    *,
    command: Any = None,
    skill_key: Any = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    if dependencies is None:
        raise ValueError("humanize runtime probe check label dependencies are required")
    humanize_executed_step_label = dependencies["humanize_executed_step_label"]
    humanize_playbook_command_label = dependencies["humanize_playbook_command_label"]
    humanize_runtime_guidance_action_label = dependencies["humanize_runtime_guidance_action_label"]
    resolve_worknet = dependencies["resolve_worknet"]
    runtime_guidance_worknet_key = dependencies["runtime_guidance_worknet_key"]
    runtime_guidance_worknet_name = dependencies["runtime_guidance_worknet_name"]

    command_text = str(command or "").strip()
    lowered_command = command_text.lower()
    text = str(label or "").strip()
    mapped = humanize_playbook_command_label(text)
    if mapped != text:
        return mapped
    label_prefix = text.lower().split(" ", 1)[0] if text else ""
    explicit_label_skill = ""
    if label_prefix in {"awp-skill", "awp-wallet"}:
        explicit_label_skill = label_prefix
    elif label_prefix and isinstance(resolve_worknet(label_prefix), dict):
        explicit_label_skill = label_prefix
    if not explicit_label_skill:
        if "scripts/preflight.py" in lowered_command or "scripts/query-status.py" in lowered_command or "scripts/query-worknet.py" in lowered_command:
            explicit_label_skill = "awp-skill"
    resolved_skill_key = (
        str(skill_key or "").strip().lower()
        or explicit_label_skill
        or runtime_guidance_worknet_key(
            None,
            labels=[text] if text else None,
            action_map={"_": lowered_command} if lowered_command else None,
        )
    )
    worknet_name = runtime_guidance_worknet_name(resolved_skill_key) if resolved_skill_key else "Runtime"
    lowered_text = text.lower()
    if lowered_text:
        if "query worknet" in lowered_text:
            return "AWP RootNet WorkNet query" if resolved_skill_key == "awp-skill" else f"{worknet_name} WorkNet query"
        if lowered_text.endswith(" preflight"):
            return "AWP RootNet preflight" if resolved_skill_key == "awp-skill" else f"{worknet_name} preflight"
        if lowered_text.endswith(" readiness"):
            return f"{worknet_name} readiness"
        if lowered_text.endswith(" control status"):
            return f"{worknet_name} control status"
        if lowered_text.endswith(" agent status"):
            return f"{worknet_name} agent status"
        if lowered_text.endswith(" status"):
            return f"{worknet_name} status"
    resolved_skill_key = runtime_guidance_worknet_key(
        resolved_skill_key or None,
        labels=[text] if text else None,
        action_map={"_": lowered_command} if lowered_command else None,
    ) or resolved_skill_key
    if resolved_skill_key == "predict":
        if "predict-agent preflight" in lowered_command:
            return "Predict preflight"
        if "predict-agent status" in lowered_command:
            return "Predict status"
        if "predict-agent stake" in lowered_command:
            return "Predict stake check"
        if "predict-agent context" in lowered_command:
            return "Predict context"
    if resolved_skill_key == "ardi":
        if "ardi-agent preflight" in lowered_command:
            return "Ardi preflight"
        if "ardi-agent status" in lowered_command:
            return "Ardi status"
        if "ardi-agent gas" in lowered_command:
            return "Ardi gas check"
        if "ardi-agent stake" in lowered_command:
            return "Ardi stake check"
    if resolved_skill_key == "gov":
        if "scripts/public/markets.py" in lowered_command:
            return "Gov public markets"
        if "scripts/helpers/what-can-i-do.py" in lowered_command:
            return "Gov phase helper"
        if "scripts/private/state.py" in lowered_command:
            return "Gov private state"
    if text:
        return (
            humanize_runtime_guidance_action_label(resolved_skill_key or None, text, command=command_text)
            or humanize_executed_step_label(text, category="inspect", execution_policy="probe")
            or text
        )
    if "scripts/preflight.py" in lowered_command:
        return "AWP RootNet preflight"
    if "scripts/query-status.py" in lowered_command:
        return "AWP RootNet status query"
    if "scripts/query-worknet.py" in lowered_command:
        return "AWP RootNet WorkNet query"
    if "scripts/run_tool.py agent-control status" in lowered_command:
        return "Mine control status"
    if "scripts/run_tool.py agent-status" in lowered_command:
        return "Mine agent status"
    if "scripts/run_tool.py doctor" in lowered_command:
        return "Mine doctor check"
    if "scripts/run_tool.py agent-start" in lowered_command:
        return "Mine agent start"
    if "bootstrap.sh" in lowered_command:
        return "Mine bootstrap script"
    return None


def knowledge_runtime_probe_display_payload(
    inspection: Any,
    *,
    skill_key: Any,
    dependencies: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("knowledge runtime probe display dependencies are required")
    RUNTIME_PROBE_TOP_LEVEL_FIELDS = dependencies["RUNTIME_PROBE_TOP_LEVEL_FIELDS"]
    build_runtime_probe_contract_item = dependencies["build_runtime_probe_contract_item"]
    build_runtime_probe_highlight_entry = dependencies["build_runtime_probe_highlight_entry"]
    humanize_executed_step_label = dependencies["humanize_executed_step_label"]
    humanize_executed_step_status_display = dependencies["humanize_executed_step_status_display"]
    humanize_runtime_probe_check_label = dependencies["humanize_runtime_probe_check_label"]
    humanize_runtime_probe_locator_display = dependencies["humanize_runtime_probe_locator_display"]
    humanize_skill_inspection_status = dependencies["humanize_skill_inspection_status"]
    knowledge_runtime_probe_summary = dependencies["knowledge_runtime_probe_summary"]
    knowledge_runtime_probe_summary_raw = dependencies["knowledge_runtime_probe_summary_raw"]
    normalize_runtime_probe_payload = dependencies["normalize_runtime_probe_payload"]
    render_argv = dependencies["render_argv"]
    runtime_guidance_worknet_name = dependencies["runtime_guidance_worknet_name"]
    runtime_message = dependencies["runtime_message"]
    runtime_probe_effective_status = dependencies["runtime_probe_effective_status"]
    safe_slug = dependencies["safe_slug"]

    if not isinstance(inspection, dict):
        return None
    normalized_skill_key = str(skill_key or inspection.get("skillKey") or "").strip().lower()
    probe_results = inspection.get("probeResults", []) if isinstance(inspection.get("probeResults"), list) else []
    label = runtime_guidance_worknet_name(normalized_skill_key)
    summary = knowledge_runtime_probe_summary(probe_results, label=label)
    summary_raw = knowledge_runtime_probe_summary_raw(probe_results)
    items: list[dict[str, Any]] = []
    highlights: list[dict[str, Any]] = []
    for probe in probe_results:
        if not isinstance(probe, dict):
            continue
        raw_label = str(probe.get("label") or "").strip()
        command = render_argv([str(part) for part in probe.get("argv", [])]) if isinstance(probe.get("argv"), list) and probe.get("argv") else None
        display_label = humanize_runtime_probe_check_label(
            raw_label,
            command=command,
            skill_key=normalized_skill_key,
        ) or humanize_executed_step_label(raw_label, category="inspect", execution_policy="probe") or raw_label
        locator_display = humanize_runtime_probe_locator_display(
            display_label or raw_label,
            command=command,
            skill_key=normalized_skill_key,
        )
        status = runtime_probe_effective_status(probe)
        status_summary = humanize_executed_step_status_display(status)
        result_summary = str(probe.get("resultSummary") or probe.get("messageDisplay") or probe.get("textDisplay") or "").strip() or None
        if not result_summary and display_label and status_summary:
            result_summary = f"{display_label}: {status_summary}."
        result_display = probe.get("resultDisplay") if isinstance(probe.get("resultDisplay"), dict) else {}
        stdout_display = result_display.get("stdoutDisplay") if isinstance(result_display.get("stdoutDisplay"), dict) else {}
        runtime_guidance_display = probe.get("runtimeGuidanceDisplay") if isinstance(probe.get("runtimeGuidanceDisplay"), dict) else {}
        preview_display = str(probe.get("previewDisplay") or result_summary or "").strip() or None
        preview_raw = str(
            probe.get("previewRaw")
            or result_display.get("previewRaw")
            or stdout_display.get("previewRaw")
            or probe.get("textRaw")
            or probe.get("text")
            or ""
        ).strip() or None
        message_display = str(probe.get("messageDisplay") or result_summary or "").strip() or None
        message_raw = str(
            probe.get("messageRaw")
            or runtime_guidance_display.get("messageRaw")
            or stdout_display.get("messageRaw")
            or runtime_message(probe.get("result"))
            or ""
        ).strip() or None
        text_raw = str(probe.get("textRaw") or probe.get("text") or "").strip() or None
        summary_raw = str(
            probe.get("resultSummaryRaw")
            or result_display.get("summaryRaw")
            or text_raw
            or ""
        ).strip() or None
        payload = probe.get("result") if isinstance(probe.get("result"), dict) else {}
        state_raw = str(payload.get("state") or "").strip() if isinstance(payload, dict) else ""
        next_command_raw = None
        next_command = runtime_guidance_display.get("nextCommand")
        if isinstance(next_command, list) and next_command:
            next_command_raw = render_argv([str(part) for part in next_command])
        elif isinstance(next_command, str) and next_command.strip():
            next_command_raw = next_command.strip()
        user_actions_raw = [
            str(item).strip()
            for item in runtime_guidance_display.get("userActionsRaw", runtime_guidance_display.get("userActions", []))
            if isinstance(item, str) and str(item).strip()
        ] if isinstance(runtime_guidance_display.get("userActionsRaw", runtime_guidance_display.get("userActions", [])), list) else []
        item = build_runtime_probe_contract_item(
            key=f"{normalized_skill_key}:{safe_slug(raw_label) or 'probe'}" if normalized_skill_key else (safe_slug(raw_label) or raw_label),
            raw_label=raw_label or None,
            display_label=display_label or raw_label or None,
            command=command,
            locator_display=locator_display,
            status=status,
            status_display=status_summary,
            summary=result_summary,
            summary_raw=summary_raw,
            preview=preview_display,
            preview_raw=preview_raw,
            message=message_display,
            message_raw=message_raw,
            state=state_raw or None,
            state_display=probe.get("stateDisplay"),
            user_actions=runtime_guidance_display.get("userActionsDisplay") or probe.get("userActionsDisplay"),
            user_actions_display=runtime_guidance_display.get("userActionsDisplay") or probe.get("userActionsDisplay"),
            user_actions_raw=user_actions_raw or None,
            next_command=next_command_raw,
            next_command_display=runtime_guidance_display.get("nextCommandDisplay") or probe.get("nextCommandDisplay"),
            next_command_raw=runtime_guidance_display.get("nextCommandRaw") or next_command_raw,
            text_display=probe.get("textDisplay"),
            text_raw=text_raw,
            detail_display=stdout_display.get("detailDisplay"),
            detail_raw=stdout_display.get("detailRaw"),
            error_summary_display=stdout_display.get("errorSummaryDisplay"),
            error_summary_raw=stdout_display.get("errorSummaryRaw"),
            result_display=result_display or None,
            runtime_guidance_display=runtime_guidance_display or None,
        )
        items.append(item)
        highlights.append(
            build_runtime_probe_highlight_entry(
                item,
                probe_label=raw_label or None,
                skill_key=normalized_skill_key or None,
            )
        )
    payload = {
        "skillKey": normalized_skill_key or None,
        "status": inspection.get("status"),
        "statusDisplay": humanize_skill_inspection_status(str(inspection.get("status") or "").strip() or None),
        "summary": summary,
        "summaryDisplay": summary,
        "summaryRaw": summary_raw,
        "preview": summary,
        "previewDisplay": summary,
        "previewRaw": summary_raw,
        "itemCount": len(items),
        "items": items,
        "highlights": highlights,
    }
    return normalize_runtime_probe_payload(payload, RUNTIME_PROBE_TOP_LEVEL_FIELDS)

