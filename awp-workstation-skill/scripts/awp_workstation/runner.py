"""Workstation run loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def run_workstation_payload(
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
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("runner dependencies are required")
    annotate_runtime_action_payloads = dependencies["annotate_runtime_action_payloads"]
    build_recovery_state = dependencies["build_recovery_state"]
    choose_default_background_process = dependencies["choose_default_background_process"]
    choose_default_follow_up_action = dependencies["choose_default_follow_up_action"]
    command_status_without_execution = dependencies["command_status_without_execution"]
    continue_background_runs = dependencies["continue_background_runs"]
    continue_pending_confirmations = dependencies["continue_pending_confirmations"]
    continue_runtime_guidance_without_default = dependencies["continue_runtime_guidance_without_default"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    execute_confirmation_action = dependencies["execute_confirmation_action"]
    execute_follow_up_action = dependencies["execute_follow_up_action"]
    extract_runtime_guidance_from_payload = dependencies["extract_runtime_guidance_from_payload"]
    finalize_run_response_payload = dependencies["finalize_run_response_payload"]
    humanize_recovery_stale_reason = dependencies["humanize_recovery_stale_reason"]
    inspect_background_process = dependencies["inspect_background_process"]
    load_active_processes = dependencies["load_active_processes"]
    load_json = dependencies["load_json"]
    load_playbook = dependencies["load_playbook"]
    normalized_confirmation_queue = dependencies["normalized_confirmation_queue"]
    normalized_follow_up_actions = dependencies["normalized_follow_up_actions"]
    now_iso = dependencies["now_iso"]
    parse_input_assignments = dependencies["parse_input_assignments"]
    parse_json_loose = dependencies["parse_json_loose"]
    persist_final_run_record = dependencies["persist_final_run_record"]
    resolve_worknet = dependencies["resolve_worknet"]
    run_command = dependencies["run_command"]
    state_context = dependencies["state_context"]
    stop_background_process = dependencies["stop_background_process"]
    sync_managed_external_processes_from_run = dependencies["sync_managed_external_processes_from_run"]
    synthesize_run_guidance = dependencies["synthesize_run_guidance"]
    trim_output = dependencies["trim_output"]

    state = state_context()
    preferences = ensure_user_preferences(state)
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    pending_queue = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    parsed_inputs = parse_input_assignments(provided_inputs)
    recovery_snapshot: Optional[dict[str, Any]] = None

    if not worknet_identifier and not playbook_path and isinstance(latest_run, dict):
        active = load_active_processes(state)
        if pause:
            selected = choose_default_background_process(active)
            if selected is None:
                raise ValueError("no active background task to pause")
            stopped = stop_background_process(state, str(selected.get("label")), execute=execute, prefer_pause=True)
            return finalize_run_response_payload(annotate_runtime_action_payloads({
                "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
                "status": stopped.get("status"),
                "executedSteps": [],
                "confirmationQueue": [],
                "runtimeGuidance": None,
                "followUpActions": [],
                "activeBackgroundProcesses": stopped.get("activeBackgroundProcesses", []),
                "selectedBackground": stopped.get("selectedBackground"),
                "resumedFromState": True,
                "nextAction": "monitor_background_run" if stopped.get("activeBackgroundProcesses") else "review_epoch",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }), preferences=preferences, recovery=recovery_snapshot)
        if background_label:
            inspected = inspect_background_process(state, background_label, tail_lines=tail_lines)
            return finalize_run_response_payload(annotate_runtime_action_payloads({
                "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
                "status": "background_running" if inspected.get("alive") else "planned",
                "executedSteps": [],
                "confirmationQueue": [],
                "runtimeGuidance": {
                    "message": (
                        f"{background_label} is running."
                        if inspected.get("alive")
                        else f"{background_label} is not running."
                    ),
                    "userActions": [],
                    "actionMap": {},
                    "nextCommand": None,
                    "nextAction": "monitor_background_run" if inspected.get("alive") else "execute_when_ready",
                    "state": None,
                    "detail": inspected.get("logPath"),
                },
                "followUpActions": [],
                "activeBackgroundProcesses": [inspected],
                "resumedFromState": True,
                "nextAction": "monitor_background_run" if inspected.get("alive") else "execute_when_ready",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }), preferences=preferences, recovery=recovery_snapshot)
        if stop_background_label:
            stopped = stop_background_process(state, stop_background_label, execute=execute)
            return finalize_run_response_payload(annotate_runtime_action_payloads({
                "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
                "status": stopped.get("status"),
                "executedSteps": [],
                "confirmationQueue": [],
                "runtimeGuidance": None,
                "followUpActions": [],
                "activeBackgroundProcesses": stopped.get("activeBackgroundProcesses", []),
                "selectedBackground": stopped.get("selectedBackground"),
                "resumedFromState": True,
                "nextAction": "monitor_background_run" if stopped.get("activeBackgroundProcesses") else "review_epoch",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }), preferences=preferences, recovery=recovery_snapshot)
        queue = normalized_confirmation_queue(pending_queue)
        if confirm_label:
            for item in queue:
                if str(item.get("label")) == confirm_label:
                    return finalize_run_response_payload(execute_confirmation_action(
                        latest_run,
                        queue,
                        item,
                        execute=execute,
                        provided_inputs=parsed_inputs,
                        state=state,
                    ), preferences=preferences, recovery=recovery_snapshot)
            raise ValueError(f"unknown confirmation label: {confirm_label}")
        if queue:
            return finalize_run_response_payload(continue_pending_confirmations(latest_run, queue, state=state), preferences=preferences, recovery=recovery_snapshot)
        follow_up_actions = normalized_follow_up_actions(latest_run.get("followUpActions", []))
        if follow_up_label:
            for item in follow_up_actions:
                if str(item.get("label")) == follow_up_label:
                    return finalize_run_response_payload(execute_follow_up_action(
                        latest_run,
                        item,
                        execute=execute,
                        explicit_selection=True,
                        state=state,
                    ), preferences=preferences, recovery=recovery_snapshot)
            source_follow_up = latest_run.get("sourceFollowUpAction")
            if isinstance(source_follow_up, dict) and str(source_follow_up.get("label")) == follow_up_label:
                fallback_actions = normalized_follow_up_actions([source_follow_up])
                if fallback_actions:
                    return finalize_run_response_payload(execute_follow_up_action(
                        latest_run,
                        fallback_actions[0],
                        execute=execute,
                        explicit_selection=True,
                        state=state,
                    ), preferences=preferences, recovery=recovery_snapshot)
            raise ValueError(f"unknown follow-up label: {follow_up_label}")
        if follow_up_actions:
            default_follow_up = choose_default_follow_up_action(follow_up_actions)
            if default_follow_up is not None:
                return finalize_run_response_payload(execute_follow_up_action(
                    latest_run,
                    default_follow_up,
                    execute=execute,
                    explicit_selection=False,
                    state=state,
                ), preferences=preferences, recovery=recovery_snapshot)
            return finalize_run_response_payload(continue_runtime_guidance_without_default(latest_run, state=state), preferences=preferences, recovery=recovery_snapshot)
        if load_active_processes(state):
            return finalize_run_response_payload(continue_background_runs(latest_run, state=state, tail_lines=tail_lines), preferences=preferences, recovery=recovery_snapshot)
    selected_worknet_identifier = worknet_identifier
    selection_warnings: list[str] = []
    redirected_to_preferred_worknet = False
    if not selected_worknet_identifier and not playbook_path:
        recovery = build_recovery_state(state)
        recovery_snapshot = recovery
        preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))
        if (
            isinstance(latest_run, dict)
            and latest_run
            and recovery.get("preferFreshStartOverResume")
            and preferred_profile is not None
            and str(preferred_profile.get("key")) != str(recovery.get("lastWorknetKey") or "")
        ):
            selected_worknet_identifier = str(preferred_profile["key"])
            redirected_to_preferred_worknet = True
            reason = humanize_recovery_stale_reason(recovery.get("staleLatestRunReason")) or "    run                         "
            selection_warnings.append(
                f"latest run was stale, so workstation switched to preferredWorknet={preferred_profile['key']}: {reason}"
            )
    playbook, warnings, playbook_source = load_playbook(playbook_path, selected_worknet_identifier)
    if redirected_to_preferred_worknet and playbook_source == "worknet":
        playbook_source = "preferred-worknet-over-stale-run"
    commands = playbook.get("commands", [])
    executed_steps: list[dict[str, Any]] = []
    confirmation_queue: list[dict[str, Any]] = []
    stop_execution_reason: Optional[str] = None
    primary_work_executed = False
    for command in commands:
        step = {
            "label": command.get("label"),
            "cwd": command.get("cwd"),
            "argv": command.get("argv"),
            "category": command.get("category"),
            "executionPolicy": command.get("executionPolicy"),
            "status": command_status_without_execution(command, execute=execute),
        }
        policy = str(command.get("executionPolicy", "manual"))
        if command.get("requires_confirmation"):
            confirmation_queue.append(step)
        elif not command.get("argv"):
            pass
        elif execute and policy not in {"probe", "setup", "primary-work"}:
            step["status"] = "available_manual"
            executed_steps.append(step)
            continue
        elif stop_execution_reason:
            step["status"] = "blocked_after_previous_step"
            step["reason"] = stop_execution_reason
        elif execute:
            if policy == "primary-work" and primary_work_executed:
                step["status"] = "skipped_after_primary_work"
                executed_steps.append(step)
                continue
            result = run_command(command["argv"], cwd=command.get("cwd"))
            step["status"] = "ok" if result["ok"] else "failed"
            step["result"] = {
                "code": result["code"],
                "stdout": trim_output(parse_json_loose(result["stdout"])),
                "stderr": trim_output(result["stderr"]),
            }
            worknet_key = str(playbook.get("worknetKey") or "").strip().lower()
            guidance = extract_runtime_guidance_from_payload(
                step["result"]["stdout"],
                worknet_key=worknet_key or None,
            )
            if guidance:
                step["runtimeGuidance"] = guidance
            if policy == "primary-work":
                primary_work_executed = True
                stop_execution_reason = "primary work step already executed; remaining control commands stay manual"
            elif policy == "setup" and result["ok"] is False:
                stop_execution_reason = f"{command.get('label')} failed"
        executed_steps.append(step)
    runtime_guidance, follow_up_actions = synthesize_run_guidance(playbook, executed_steps)
    run_record = annotate_runtime_action_payloads({
        "generatedAt": now_iso(),
        "mode": mode,
        "execute": execute,
        "playbook": playbook,
        "executedSteps": executed_steps,
        "confirmationQueue": confirmation_queue,
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "warnings": selection_warnings + warnings + state["warnings"],
    })
    active_processes = sync_managed_external_processes_from_run(state, run_record)
    has_managed_external = bool(run_record.get("managedExternalProcess"))
    response_payload = annotate_runtime_action_payloads({
        "mode": mode,
        "status": (
            "needs_confirmation"
            if confirmation_queue
            else (
                "background_running"
                if has_managed_external
                else ("needs_runtime_input" if runtime_guidance and follow_up_actions else ("executed" if execute else "planned"))
            )
        ),
        "executedSteps": executed_steps,
        "confirmationQueue": confirmation_queue,
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "resumedFromState": playbook_source == "last-selected",
        "playbookSource": playbook_source,
        "selectedWorknetKey": playbook.get("worknetKey"),
        "selectedWorknetName": playbook.get("requiredSkill"),
        "warnings": selection_warnings + warnings + state["warnings"],
        "nextAction": (
            "await_confirmation"
            if confirmation_queue
            else (
                "monitor_background_run"
                if has_managed_external
                else (
                    "follow_runtime_guidance"
                    if runtime_guidance and follow_up_actions
                    else ("review_epoch" if execute else "execute_when_ready")
                )
            )
        ),
        **({"activeBackgroundProcesses": active_processes} if has_managed_external else {}),
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })
    final_payload = finalize_run_response_payload(
        response_payload,
        preferences=preferences,
        recovery=recovery_snapshot,
    )
    persist_final_run_record(state, run_record, final_payload, confirmation_queue)
    if execute and auto_advance and not confirmation_queue and follow_up_actions:
        default_follow_up = choose_default_follow_up_action(normalized_follow_up_actions(follow_up_actions))
        if default_follow_up is not None:
            return finalize_run_response_payload(execute_follow_up_action(
                run_record,
                default_follow_up,
                execute=True,
                explicit_selection=False,
                state=state,
            ), preferences=preferences, recovery=recovery_snapshot)
    return final_payload


def build_run_response_briefing_payload(
    response: dict[str, Any],
    *,
    preferences: Optional[dict[str, Any]] = None,
    recovery: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("run response briefing dependencies are required")
    action_details_from_decision = dependencies["action_details_from_decision"]
    align_run_execution_user_message = dependencies["align_run_execution_user_message"]
    annotate_execution_actions = dependencies["annotate_execution_actions"]
    append_runtime_maturity_note = dependencies["append_runtime_maturity_note"]
    append_unique_action_detail = dependencies["append_unique_action_detail"]
    build_recovery_decision = dependencies["build_recovery_decision"]
    canonical_worknet_caution_text = dependencies["canonical_worknet_caution_text"]
    canonical_worknet_loop_text = dependencies["canonical_worknet_loop_text"]
    compact_knowledge_context = dependencies["compact_knowledge_context"]
    derive_runtime_execution_state = dependencies["derive_runtime_execution_state"]
    knowledge_action_description = dependencies["knowledge_action_description"]
    knowledge_context_for_worknet = dependencies["knowledge_context_for_worknet"]
    knowledge_refresh_action_description = dependencies["knowledge_refresh_action_description"]
    knowledge_related_reference_highlights = dependencies["knowledge_related_reference_highlights"]
    knowledge_related_source_highlights = dependencies["knowledge_related_source_highlights"]
    knowledge_source_action_description = dependencies["knowledge_source_action_description"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    normalized_confirmation_queue = dependencies["normalized_confirmation_queue"]
    prepend_canonical_worknet_plain = dependencies["prepend_canonical_worknet_plain"]
    prioritize_action_entries = dependencies["prioritize_action_entries"]
    recovery_decision_actions_from_run_response = dependencies["recovery_decision_actions_from_run_response"]
    recovery_status_display = dependencies["recovery_status_display"]
    reporter_source_note = dependencies["reporter_source_note"]
    resolve_worknet = dependencies["resolve_worknet"]
    run_response_primary_action = dependencies["run_response_primary_action"]
    worknet_runtime_maturity_note = dependencies["worknet_runtime_maturity_note"]

    playbook_source = str(response.get("playbookSource") or "").strip()
    selected_key = str(response.get("selectedWorknetKey") or "").strip().lower()
    selected_name = str(response.get("selectedWorknetName") or response.get("selectedWorknetKey") or "WorkNet").strip()
    next_action = str(response.get("nextAction") or "").strip()
    status = str(response.get("status") or "").strip()
    runtime_guidance = response.get("runtimeGuidance", {})
    runtime_guidance = runtime_guidance if isinstance(runtime_guidance, dict) else {}
    active_background = response.get("activeBackgroundProcesses", [])
    selected_background = response.get("selectedBackground")
    recovery = recovery if isinstance(recovery, dict) else {}
    primary_action = run_response_primary_action(response)
    preferred_profile = resolve_worknet(str((preferences or {}).get("preferredWorknet") or ""))
    decision = build_recovery_decision(
        recovery,
        worknet_name=selected_name,
        preferred_profile=preferred_profile,
        primary_label=primary_action,
        actions=recovery_decision_actions_from_run_response(
            response,
            primary_label=primary_action,
        ),
    )
    queue = normalized_confirmation_queue(response.get("confirmationQueue", []))
    worknet_context_key = selected_key or str(recovery.get("lastWorknetKey") or "").strip().lower()
    knowledge_catalog = load_or_build_knowledge_catalog()
    knowledge_context = compact_knowledge_context(
        knowledge_context_for_worknet(knowledge_catalog, worknet_context_key)
    )
    knowledge_reference_highlights = knowledge_related_reference_highlights(
        knowledge_catalog,
        knowledge_context,
    ) if isinstance(knowledge_context, dict) else []
    knowledge_source_highlights = knowledge_related_source_highlights(
        knowledge_catalog,
        knowledge_context,
    ) if isinstance(knowledge_context, dict) else []

    headline = None
    user_message = None
    if playbook_source == "preferred-worknet-over-stale-run":
        stale_reason = str(decision.get("staleReason") or "Previous run is stale.")
        headline = f"Fresh start preferred: {decision.get('lastWorknetName') or selected_name} to {selected_name}"
        user_message = f"{stale_reason} Use the {selected_name} playbook for the preferred fresh route."
    elif playbook_source == "preferred-worknet":
        headline = f"Preferred playbook selected: {selected_name}"
        user_message = f"Workstation selected the preferred {selected_name} playbook."
    elif status == "background_running":
        if isinstance(active_background, list) and len(active_background) == 1 and isinstance(active_background[0], dict):
            summary = active_background[0].get("summary", {})
            background_headline = summary.get("headline") if isinstance(summary, dict) else None
            headline = str(background_headline).strip() if isinstance(background_headline, str) and background_headline.strip() else "Background process is running"
            user_message = "A background process is running; monitor, pause, or stop it before starting conflicting work."
        else:
            headline = str(runtime_guidance.get("message") or "Background processes are running.").strip()
            user_message = "Multiple background processes are running; inspect active process state before changing routes."
        user_message = prepend_canonical_worknet_plain(user_message, worknet_context_key)
    elif isinstance(selected_background, dict):
        label = str(selected_background.get("label") or "background process").strip()
        if status == "stopped":
            headline = f"{label} stopped"
            user_message = "The selected background process has stopped."
        elif status == "failed":
            headline = f"{label} failed"
            user_message = "The selected background process failed; inspect logs before restarting."
        elif status == "needs_confirmation":
            headline = f"{label} needs confirmation"
            user_message = "The selected background action needs confirmation before continuing."
    elif response.get("confirmationQueue"):
        first_label = queue[0].get("label") if queue else None
        headline = "Pending confirmation"
        if isinstance(first_label, str) and first_label.strip():
            user_message = f"Review pending confirmation before execution: {first_label.strip()}."
        else:
            user_message = "Review pending confirmations before execution."
        caution = canonical_worknet_caution_text(worknet_context_key)
        if caution and caution not in user_message:
            user_message = f"{user_message} {caution}".strip()
        user_message = prepend_canonical_worknet_plain(user_message, worknet_context_key)
        decision = {
            **decision,
            "decision": "needs_confirmation",
            "status": "needs_confirmation",
            "headline": headline,
            "message": user_message,
            "primaryActionLabel": str(first_label).strip() if isinstance(first_label, str) and first_label.strip() else decision.get("primaryActionLabel"),
        }
    elif next_action == "follow_runtime_guidance":
        headline = str(runtime_guidance.get("message") or f"{selected_name} runtime guidance is ready.").strip()
        user_message = "The official runtime has already provided the next step, so follow that guidance instead of reselecting a WorkNet."
        loop = canonical_worknet_loop_text(worknet_context_key)
        if loop:
            user_message = f"{user_message} {loop}".strip()
        user_message = prepend_canonical_worknet_plain(user_message, worknet_context_key)
        decision = {
            **decision,
            "decision": "follow_runtime_guidance",
            "status": "follow_runtime_guidance",
            "headline": headline,
            "message": user_message,
        }
    elif playbook_source == "last-selected" and selected_name:
        headline = str(decision.get("headline") or f"Ready to resume {selected_name}.")
        if next_action == "execute_when_ready":
            user_message = str(decision.get("message") or f"Use the existing {selected_name} playbook when prerequisites are ready.")
        elif next_action == "review_epoch":
            user_message = f"Review the latest {selected_name} epoch before starting another run."
        else:
            user_message = str(decision.get("message") or f"Continue from the previously selected {selected_name} route.")
    elif playbook_source == "worknet" and selected_name:
        headline = f"{selected_name} is selected."
        if next_action == "execute_when_ready":
            user_message = f"{selected_name} has a playbook ready."
            if primary_action:
                user_message += f" Use `{primary_action}` when you want to continue."
        else:
            user_message = f"{selected_name} is selected; inspect the recommended actions before execution."
    elif next_action == "review_epoch":
        headline = f"{selected_name or 'The selected WorkNet'} needs epoch review."
        user_message = "Review the previous epoch before starting a new run."
    elif next_action == "execute_when_ready" and selected_name:
        headline = f"{selected_name} is ready."
        user_message = "The playbook can execute when prerequisites and confirmations are satisfied."
        if primary_action:
            user_message += f" Use `{primary_action}` when ready."
    if headline is None:
        headline = str(runtime_guidance.get("message") or "Work loop status has been updated.").strip()
    if user_message is None:
        user_message = headline
    if selected_key and playbook_source in {"preferred-worknet-over-stale-run", "preferred-worknet", "last-selected", "worknet"}:
        user_message = prepend_canonical_worknet_plain(user_message, selected_key)
    maturity_note = worknet_runtime_maturity_note(worknet_key=selected_key or worknet_context_key)
    if maturity_note:
        user_message = append_runtime_maturity_note(user_message, maturity_note)
    if isinstance(knowledge_context, dict) and str(knowledge_context.get("freshnessStatus") or "") == "affected":
        label = str(knowledge_context.get("label") or selected_name or worknet_context_key or "current WorkNet").strip()
        source_note = reporter_source_note(knowledge_source_highlights)
        reminder = f"{label} has upstream source changes; review official sources before continuing automation."
        if source_note:
            reminder = f"{reminder} {source_note}".strip()
        if reminder not in str(user_message):
            user_message = f"{str(user_message).strip()} {reminder}".strip()
    user_action_details = action_details_from_decision(decision)
    if isinstance(knowledge_context, dict):
        label = str(knowledge_context.get("label") or selected_name or worknet_context_key or "current WorkNet").strip()
        append_unique_action_detail(
            user_action_details,
            label=f"View {label} dossier",
            description=knowledge_action_description(knowledge_context),
            command=knowledge_context.get("queryCommand"),
        )
        primary_knowledge_command = str(knowledge_context.get("primaryCommand") or "").strip()
        query_command = str(knowledge_context.get("queryCommand") or "").strip()
        if primary_knowledge_command and primary_knowledge_command != query_command:
            append_unique_action_detail(
                user_action_details,
                label=f"Refresh {label} dossier",
                description=knowledge_refresh_action_description(knowledge_context),
                command=primary_knowledge_command,
            )
    for item in knowledge_source_highlights[:2]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        append_unique_action_detail(
            user_action_details,
            label=f"Review source {label}",
            description=knowledge_source_action_description(item),
            command=item.get("queryCommand"),
        )
        primary_command = str(item.get("primaryCommand") or "").strip()
        query_command = str(item.get("queryCommand") or "").strip()
        if primary_command and primary_command != query_command:
            append_unique_action_detail(
                user_action_details,
                label=f"Refresh source {label}",
                description=f"Refresh {label} before continuing automation.",
                command=primary_command,
            )
    resume_status = str(decision.get("status") or "").strip() or None
    execution_state = derive_runtime_execution_state(
        response,
        headline=headline,
        recovery=recovery,
    )
    user_action_details = prioritize_action_entries(
        user_action_details,
        execution_state=execution_state.get("executionState"),
        resume_status=resume_status,
        worknet_key=worknet_context_key,
    )
    user_action_details = annotate_execution_actions(user_action_details)
    if primary_action is None and isinstance(decision.get("primaryActionLabel"), str) and decision.get("primaryActionLabel"):
        primary_action = str(decision.get("primaryActionLabel"))
    primary_user_action_display = None
    primary_user_action_command = None
    if primary_action:
        matched = next(
            (item for item in user_action_details if str(item.get("label") or "").strip() == str(primary_action).strip()),
            None,
        )
        if isinstance(matched, dict):
            if isinstance(matched.get("displayLabel"), str) and matched.get("displayLabel"):
                primary_user_action_display = str(matched["displayLabel"])
            if isinstance(matched.get("command"), str) and matched.get("command"):
                primary_user_action_command = str(matched["command"])
    if primary_action is None and user_action_details:
        primary_action = str(user_action_details[0].get("label") or "").strip() or None
    if primary_user_action_display is None and user_action_details:
        primary_user_action_display = str(user_action_details[0].get("displayLabel") or "") or None
    if primary_user_action_command is None and user_action_details:
        primary_user_action_command = str(user_action_details[0].get("command") or "") or None
    user_message = align_run_execution_user_message(
        user_message,
        execution_state=execution_state.get("executionState"),
        execution_headline=execution_state.get("executionHeadline"),
        primary_action=primary_action,
        worknet_context_key=worknet_context_key,
        extra_parts=[maturity_note] if maturity_note else None,
    )
    return {
        "headline": headline,
        "userMessage": user_message,
        "resumeStatus": resume_status,
        "resumeStatusDisplay": recovery_status_display(resume_status) if resume_status else None,
        "executionState": execution_state.get("executionState"),
        "executionStateDisplay": execution_state.get("executionStateDisplay"),
        "executionHeadline": execution_state.get("executionHeadline"),
        "primaryUserAction": primary_action,
        "primaryUserActionDisplay": primary_user_action_display,
        "primaryUserActionCommand": primary_user_action_command,
        "userActionDetails": user_action_details,
        "knowledgeContext": knowledge_context,
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "recoveryDecision": decision if decision.get("decision") else None,
    }


def execute_follow_up_action_payload(
    latest_run: dict[str, Any],
    action: dict[str, Any],
    *,
    execute: bool,
    explicit_selection: bool = False,
    state: dict[str, Any],
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("execute follow up action dependencies are required")
    annotate_runtime_action_payloads = dependencies["annotate_runtime_action_payloads"]
    derive_runtime_execution_state = dependencies["derive_runtime_execution_state"]
    extract_runtime_guidance_from_payload = dependencies["extract_runtime_guidance_from_payload"]
    launch_background_command = dependencies["launch_background_command"]
    now_iso = dependencies["now_iso"]
    parse_json_loose = dependencies["parse_json_loose"]
    persist_final_run_record = dependencies["persist_final_run_record"]
    run_command = dependencies["run_command"]
    sync_managed_external_processes_from_run = dependencies["sync_managed_external_processes_from_run"]
    synthesize_run_guidance = dependencies["synthesize_run_guidance"]
    trim_output = dependencies["trim_output"]

    step = {
        "label": action.get("label"),
        "cwd": action.get("cwd"),
        "argv": action.get("argv"),
        "category": "follow-up",
        "executionPolicy": "follow-up",
        "status": "planned" if execute else "available_manual",
        "parameterSchema": action.get("parameterSchema", []),
        "longRunning": bool(action.get("longRunning", False)),
    }
    runtime_guidance: Optional[dict[str, Any]] = None
    follow_up_actions: list[dict[str, Any]] = []
    if action.get("requiresConfirmation"):
        step["status"] = "queued_for_confirmation"
    elif not execute:
        return annotate_runtime_action_payloads({
            "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
            "status": "planned",
            "executedSteps": [step | {"status": "available_manual"}],
            "confirmationQueue": [],
            "runtimeGuidance": None,
            "followUpActions": [],
            "resumedFromState": True,
            "nextAction": "execute_when_ready",
            "progress": "[4/5] Work loop",
            "stateRoot": state["root"],
        })
    elif execute and (action.get("safeToAutoRun") or explicit_selection) and action.get("argv"):
        if action.get("longRunning"):
            launched = launch_background_command(
                [str(part) for part in action["argv"]],
                cwd=action.get("cwd"),
                state=state,
                label=str(action.get("label")),
            )
            step["status"] = "started_background"
            step["backgroundProcess"] = launched
            runtime_guidance = {
                "message": f"{action.get('label')} started in the background.",
                "userActions": [],
                "actionMap": {},
                "nextCommand": None,
                "nextAction": "monitor_background_run",
                "state": None,
                "detail": launched.get("logPath"),
            }
            step["runtimeGuidance"] = runtime_guidance
        else:
            result = run_command([str(part) for part in action["argv"]], cwd=action.get("cwd"))
            step["status"] = "ok" if result.get("ok", False) else "failed"
            step["result"] = {
                "code": result.get("code"),
                "stdout": trim_output(parse_json_loose(result.get("stdout", ""))),
                "stderr": trim_output(result.get("stderr", "")),
            }
            playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
            worknet_key = str(playbook.get("worknetKey") or "").strip().lower()
            guidance = extract_runtime_guidance_from_payload(
                step["result"]["stdout"],
                worknet_key=worknet_key or None,
            )
            if guidance:
                step["runtimeGuidance"] = guidance
    executed_steps = [step]
    playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
    if runtime_guidance is None:
        runtime_guidance, follow_up_actions = synthesize_run_guidance(playbook, executed_steps)
    else:
        follow_up_actions = []
    run_record = annotate_runtime_action_payloads({
        "generatedAt": now_iso(),
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "execute": execute,
        "playbook": playbook,
        "executedSteps": executed_steps,
        "confirmationQueue": [step] if step.get("status") == "queued_for_confirmation" else [],
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "warnings": state["warnings"],
        "resumedFollowUp": True,
        "sourceFollowUpAction": action,
    })
    active_processes = sync_managed_external_processes_from_run(state, run_record)
    has_managed_external = bool(run_record.get("managedExternalProcess"))
    has_background_process = has_managed_external or step.get("status") == "started_background"
    response_payload = annotate_runtime_action_payloads({
        "mode": run_record["mode"],
        "status": (
            "needs_confirmation"
            if run_record["confirmationQueue"]
            else (
                "background_running"
                if has_background_process or (isinstance(runtime_guidance, dict) and runtime_guidance.get("nextAction") == "monitor_background_run")
                else ("needs_runtime_input" if runtime_guidance and follow_up_actions else ("executed" if execute else "planned"))
            )
        ),
        "executedSteps": executed_steps,
        "confirmationQueue": run_record["confirmationQueue"],
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "resumedFromState": True,
        "nextAction": (
            "await_confirmation"
            if run_record["confirmationQueue"]
            else (
                "monitor_background_run"
                if has_background_process
                else (
                    runtime_guidance.get("nextAction")
                    if isinstance(runtime_guidance, dict) and runtime_guidance.get("nextAction") == "monitor_background_run"
                    else (
                        "follow_runtime_guidance"
                        if runtime_guidance and follow_up_actions
                        else ("review_epoch" if execute else "execute_when_ready")
                    )
                )
            )
        ),
        **({"activeBackgroundProcesses": active_processes} if has_background_process else {}),
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })
    final_like_payload = {
        **response_payload,
        **derive_runtime_execution_state(response_payload),
    }
    persist_final_run_record(
        state,
        run_record,
        final_like_payload,
        run_record["confirmationQueue"],
    )
    return final_like_payload


def execute_confirmation_action_payload(
    latest_run: dict[str, Any],
    pending_queue: list[dict[str, Any]],
    action: dict[str, Any],
    *,
    execute: bool,
    provided_inputs: dict[str, str],
    state: dict[str, Any],
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("execute confirmation action dependencies are required")
    annotate_runtime_action_payloads = dependencies["annotate_runtime_action_payloads"]
    build_confirmation_execute_command = dependencies["build_confirmation_execute_command"]
    derive_runtime_execution_state = dependencies["derive_runtime_execution_state"]
    extract_runtime_guidance_from_payload = dependencies["extract_runtime_guidance_from_payload"]
    normalized_confirmation_queue = dependencies["normalized_confirmation_queue"]
    now_iso = dependencies["now_iso"]
    parse_json_loose = dependencies["parse_json_loose"]
    persist_final_run_record = dependencies["persist_final_run_record"]
    render_argv = dependencies["render_argv"]
    resolve_parameterized_argv = dependencies["resolve_parameterized_argv"]
    run_command = dependencies["run_command"]
    trim_output = dependencies["trim_output"]
    workstation_confirmation_command = dependencies["workstation_confirmation_command"]

    queue = normalized_confirmation_queue(pending_queue)
    selected_label = str(action.get("label"))
    remaining_queue = [item for item in queue if str(item.get("label")) != selected_label] if execute else queue
    step = {
        "label": action.get("label"),
        "cwd": action.get("cwd"),
        "argv": action.get("argv"),
        "category": action.get("category", "confirmation"),
        "executionPolicy": "confirmation",
        "status": "awaiting_confirmation" if not execute else "queued_for_confirmation",
        "parameterSchema": action.get("parameterSchema", []),
    }
    runtime_guidance: Optional[dict[str, Any]] = None
    follow_up_actions: list[dict[str, Any]] = []
    parameter_schema = [
        spec for spec in action.get("parameterSchema", []) if isinstance(spec, dict)
    ] if isinstance(action.get("parameterSchema"), list) else []
    if not execute:
        return annotate_runtime_action_payloads({
            "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
            "status": "needs_confirmation",
            "executedSteps": [step],
            "confirmationQueue": queue,
            "selectedConfirmation": {
                "label": action.get("label"),
                "command": render_argv(action.get("argv", [])) if isinstance(action.get("argv"), list) else None,
                "requiredInputs": parameter_schema,
                "executeCommand": (
                    build_confirmation_execute_command(selected_label, parameter_schema)
                    if parameter_schema
                    else workstation_confirmation_command(selected_label, execute=True)
                ),
            },
            "runtimeGuidance": None,
            "followUpActions": [],
            "resumedFromState": True,
            "nextAction": "await_confirmation",
            "progress": "[4/5] Work loop",
            "stateRoot": state["root"],
        })
    if execute:
        argv = action.get("argv")
        if isinstance(argv, list) and argv:
            resolved_argv = [str(part) for part in argv]
            parameter_errors: list[str] = []
            if parameter_schema:
                maybe_resolved, parameter_errors = resolve_parameterized_argv(
                    resolved_argv,
                    parameter_schema,
                    provided_inputs,
                )
                if maybe_resolved is not None:
                    resolved_argv = maybe_resolved
            if parameter_errors:
                return annotate_runtime_action_payloads({
                    "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
                    "status": "needs_confirmation",
                    "executedSteps": [
                        {
                            **step,
                            "status": "missing_parameters",
                            "parameterErrors": parameter_errors,
                        }
                    ],
                    "confirmationQueue": queue,
                    "selectedConfirmation": {
                        "label": action.get("label"),
                        "command": render_argv(action.get("argv", [])) if isinstance(action.get("argv"), list) else None,
                        "requiredInputs": parameter_schema,
                        "executeCommand": build_confirmation_execute_command(selected_label, parameter_schema),
                    },
                    "runtimeGuidance": None,
                    "followUpActions": [],
                    "resumedFromState": True,
                    "nextAction": "await_confirmation",
                    "progress": "[4/5] Work loop",
                    "stateRoot": state["root"],
                })
            step["argv"] = resolved_argv
            result = run_command(resolved_argv, cwd=action.get("cwd"))
            step["status"] = "ok" if result.get("ok", False) else "failed"
            step["result"] = {
                "code": result.get("code"),
                "stdout": trim_output(parse_json_loose(result.get("stdout", ""))),
                "stderr": trim_output(result.get("stderr", "")),
            }
            playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
            worknet_key = str(playbook.get("worknetKey") or "").strip().lower()
            guidance = extract_runtime_guidance_from_payload(
                step["result"]["stdout"],
                worknet_key=worknet_key or None,
            )
            if guidance:
                step["runtimeGuidance"] = guidance
                runtime_guidance = guidance
        else:
            step["status"] = "missing_runtime_command"
    run_record = annotate_runtime_action_payloads({
        "generatedAt": now_iso(),
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "execute": execute,
        "playbook": latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {},
        "executedSteps": [step],
        "confirmationQueue": remaining_queue,
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "warnings": state["warnings"],
        "confirmedAction": action,
    })
    response_payload = annotate_runtime_action_payloads({
        "mode": run_record["mode"],
        "status": (
            "needs_confirmation"
            if remaining_queue
            else ("executed" if execute else "needs_confirmation")
        ),
        "executedSteps": [step],
        "confirmationQueue": remaining_queue,
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "resumedFromState": True,
        "nextAction": (
            "await_confirmation"
            if remaining_queue
            else ("review_epoch" if execute else "await_confirmation")
        ),
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })
    final_like_payload = {
        **response_payload,
        **derive_runtime_execution_state(response_payload),
    }
    persist_final_run_record(state, run_record, final_like_payload, remaining_queue)
    return final_like_payload

