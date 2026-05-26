"""Start response builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def build_start_response_from_preflight_payload(
    preflight: Any,
    *,
    state: Optional[dict[str, Any]] = None,
    knowledge_catalog: Optional[dict[str, Any]] = None,
    cached_bundle: Optional[dict[str, Any]] = None,
    persist: bool = False,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("start response dependencies are required")
    action_details_from_ui_actions = dependencies["action_details_from_ui_actions"]
    align_run_execution_user_message = dependencies["align_run_execution_user_message"]
    annotate_execution_actions = dependencies["annotate_execution_actions"]
    append_user_action = dependencies["append_user_action"]
    atomic_write_json = dependencies["atomic_write_json"]
    background_observations_from_run = dependencies["background_observations_from_run"]
    build_capability_bundle = dependencies["build_capability_bundle"]
    build_preflight_plain_language_summary = dependencies["build_preflight_plain_language_summary"]
    build_preflight_report = dependencies["build_preflight_report"]
    build_resume_recovery_briefing = dependencies["build_resume_recovery_briefing"]
    derive_execution_state = dependencies["derive_execution_state"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    humanize_public_action_entries = dependencies["humanize_public_action_entries"]
    humanize_public_recovery_decision = dependencies["humanize_public_recovery_decision"]
    humanize_recovery_stale_reason = dependencies["humanize_recovery_stale_reason"]
    humanize_runtime_guidance_message = dependencies["humanize_runtime_guidance_message"]
    humanize_worknet_switch_summary = dependencies["humanize_worknet_switch_summary"]
    knowledge_focus_topics_payload = dependencies["knowledge_focus_topics_payload"]
    knowledge_reference_highlights_payload = dependencies["knowledge_reference_highlights_payload"]
    knowledge_source_highlights_payload = dependencies["knowledge_source_highlights_payload"]
    load_cached_capability_bundle = dependencies["load_cached_capability_bundle"]
    load_json = dependencies["load_json"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    maybe_promote_recovery_decision = dependencies["maybe_promote_recovery_decision"]
    merge_recovery_decision_actions = dependencies["merge_recovery_decision_actions"]
    prioritize_ui_actions = dependencies["prioritize_ui_actions"]
    progress_message = dependencies["progress_message"]
    recommend_worknet_actions = dependencies["recommend_worknet_actions"]
    recovery_status_display = dependencies["recovery_status_display"]
    resolve_worknet = dependencies["resolve_worknet"]
    review_background_action_label = dependencies["review_background_action_label"]
    run_worknet_command = dependencies["run_worknet_command"]
    runtime_follow_up_description = dependencies["runtime_follow_up_description"]
    state_context = dependencies["state_context"]
    workstation_background_command = dependencies["workstation_background_command"]
    workstation_confirmation_command = dependencies["workstation_confirmation_command"]
    workstation_follow_up_command = dependencies["workstation_follow_up_command"]
    workstation_pause_command = dependencies["workstation_pause_command"]
    workstation_status_command = dependencies["workstation_status_command"]

    state = state or state_context()
    preflight = preflight if isinstance(preflight, dict) else build_preflight_report()
    knowledge_catalog = knowledge_catalog or load_or_build_knowledge_catalog(state)
    knowledge_overview = (
        knowledge_catalog.get("knowledgeOverview", {})
        if isinstance(knowledge_catalog.get("knowledgeOverview"), dict)
        else {}
    )
    knowledge_focus_topics = knowledge_focus_topics_payload(knowledge_catalog)
    knowledge_reference_highlights = knowledge_reference_highlights_payload(knowledge_catalog)
    knowledge_source_highlights = knowledge_source_highlights_payload(knowledge_catalog)
    registration_plan = preflight.get("registrationPlan", {})
    preferences = (
        preflight.get("userPreferences", {})
        if isinstance(preflight.get("userPreferences"), dict)
        else ensure_user_preferences(state)
    )
    knowledge_review_queue_summary = (
        preflight.get("knowledgeReviewQueueSummary", {})
        if isinstance(preflight.get("knowledgeReviewQueueSummary"), dict)
        else {}
    )
    queue_headline_for_message: Optional[str] = None
    recovery_decision = (
        preflight.get("recoveryDecision")
        if isinstance(preflight.get("recoveryDecision"), dict)
        else None
    )
    recommendation: Optional[dict[str, Any]] = None
    cached_bundle = cached_bundle if isinstance(cached_bundle, dict) else load_cached_capability_bundle(state)
    preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))

    user_actions: list[dict[str, Any]] = []
    action_map: dict[str, str] = {}
    progress = progress_message(1, 5, "AWP setup", "Checking workstation readiness")

    intro = (
        "AWP Agent Workstation prepares the wallet, skill runtime, WorkNet catalog, and safe next action before execution."
    )
    preflight_intro = build_preflight_plain_language_summary(
        str(preflight.get("nextAction") or ""),
        knowledge_review_queue_summary=knowledge_review_queue_summary,
        include_queue_note=False,
    )

    if preflight.get("nextAction") == "install_awp_skill_dependency":
        progress = progress_message(1, 5, "Setup", "Install awp-skill for RootNet operations")
        user_message = (
            "The agent work wallet is ready, but the official awp-skill runtime is not installed. "
            "Install awp-skill before registration or RootNet actions."
        )
        command = registration_plan.get("commands", [{}])[0] if registration_plan.get("commands") else None
        if isinstance(command, dict):
            label = "Install awp-skill"
            user_actions.append(
                {
                    "label": label,
                    "description": "Install the official RootNet skill dependency.",
                }
            )
            action_map[label] = " ".join(command.get("argv", []))
        user_actions.append(
            {
                "label": "Review WorkNets",
                "description": "Inspect available WorkNets before selecting a route.",
            }
        )
        action_map["Review WorkNets"] = "python3 scripts/scan-worknets.py"
    elif preflight.get("nextAction") in {"run_awp_skill_registration", "register_agent"}:
        progress = progress_message(2, 5, "Registration", "Prepare gasless onboarding")
        user_message = "Run official awp-skill registration to complete gasless onboarding."
        command = registration_plan.get("commands", [{}])[0] if registration_plan.get("commands") else None
        if isinstance(command, dict):
            label = "Register agent"
            user_actions.append({"label": label, "description": "Register this agent through the official awp-skill flow."})
            action_map[label] = " ".join(command.get("argv", []))
        official_message = registration_plan.get("officialMessage")
        if official_message:
            user_message += " " + str(official_message)
    elif preflight.get("nextAction") == "retry_registration_preflight":
        progress = progress_message(2, 5, "Registration", "Retry when AWP API is reachable")
        user_message = "awp-skill registration preflight could not reach the AWP API. Retry registration after connectivity recovers."
        official_message = registration_plan.get("officialMessage")
        if official_message:
            user_message += " " + str(official_message)
        user_actions.append(
            {
                "label": "Retry registration",
                "description": "Run agent registration again after the API is reachable.",
            }
        )
        action_map["Retry registration"] = "python3 scripts/register-agent.py"
        user_actions.append(
            {
                "label": "Review WorkNets",
                "description": "Inspect WorkNet options while registration is unavailable.",
            }
        )
        action_map["Review WorkNets"] = "python3 scripts/scan-worknets.py"
    elif preflight.get("nextAction") == "resume_runtime_guidance":
        recovery = preflight.get("recovery", {})
        worknet_key = str(recovery.get("lastWorknetKey") or "")
        progress = progress_message(4, 5, "Resume", "Continue from runtime guidance")
        user_message = humanize_runtime_guidance_message(recovery)
        default_label = recovery.get("defaultFollowUpLabel")
        default_command = recovery.get("defaultFollowUpCommand")
        if default_label and default_command:
            user_actions.append(
                {
                    "label": "Continue runtime action",
                    "description": (
                        f"Continue with {default_label}."
                        if not worknet_key
                        else runtime_follow_up_description(worknet_key, str(default_label))
                    ),
                }
            )
            action_map["Continue runtime action"] = "python3 scripts/run-workstation.py --mode autopilot --execute"
        for item in recovery.get("followUpActions", []):
            if not isinstance(item, dict) or not item.get("label"):
                continue
            label = str(item["label"])
            command = item.get("command")
            user_actions.append(
                {
                    "label": label,
                    "description": runtime_follow_up_description(worknet_key, label),
                }
            )
            if item.get("requiresConfirmation"):
                action_map[label] = workstation_follow_up_command(label, execute=False)
            elif item.get("safeToAutoRun") and item.get("argv"):
                action_map[label] = workstation_follow_up_command(label, execute=True)
            elif isinstance(command, str) and command.strip():
                action_map[label] = command.strip()
        if isinstance(recovery_decision, dict):
            maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
    elif preflight.get("nextAction") == "monitor_background_runs":
        recovery = preflight.get("recovery", {})
        active = recovery.get("activeBackgroundProcesses", [])
        progress = progress_message(4, 5, "Background", f"{recovery.get('activeBackgroundCount', 0)} active process(es)")
        user_message = "Background work is running. Monitor or pause before starting another route."
        if len(active) == 1 and isinstance(active[0], dict):
            summary = active[0].get("summary", {})
            headline = summary.get("headline") if isinstance(summary, dict) else None
            if isinstance(headline, str) and headline.strip():
                user_message = headline.strip()
        if isinstance(recovery_decision, dict) and str(recovery_decision.get("status") or "").strip() == "background_running":
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
        if not user_actions:
            if recovery.get("activeBackgroundCount") == 1:
                user_actions.append(
                    {
                        "label": "Pause background work",
                        "description": "Pause the active background process.",
                    }
                )
                action_map["Pause background work"] = workstation_pause_command(execute=True)
            for item in active:
                if not isinstance(item, dict) or not item.get("label"):
                    continue
                label = str(item["label"])
                user_actions.append(
                    {
                        "label": f"Inspect {label}",
                        "description": (
                            str(item.get("summary", {}).get("headline"))
                            if isinstance(item.get("summary"), dict) and item.get("summary", {}).get("headline")
                            else "Inspect the background process status and recent log tail."
                        ),
                    }
                )
                action_map[f"Inspect {label}"] = workstation_background_command(label, tail_lines=40)
                user_actions.append(
                    {
                        "label": f"Stop {label}",
                        "description": "Stop this background process after confirmation.",
                    }
                )
                action_map[f"Stop {label}"] = workstation_background_command(label, stop=True, execute=False)
            if isinstance(recovery_decision, dict):
                maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
    elif preflight.get("nextAction") == "resume_previous_run":
        latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
        recovery = preflight.get("recovery", {}) if isinstance(preflight.get("recovery"), dict) else {}
        source_follow_up = latest_run.get("sourceFollowUpAction", {}) if isinstance(latest_run, dict) else {}
        restart_label = str(source_follow_up.get("label") or "")
        observations = background_observations_from_run(latest_run, state=state)
        last_background = observations[0] if observations else None
        worknet_name = (
            latest_run.get("playbook", {}).get("requiredSkill")
            if isinstance(latest_run.get("playbook"), dict)
            else None
        )
        progress = progress_message(4, 5, "Resume", "Review previous run state")
        if isinstance(last_background, dict):
            summary = last_background.get("summary", {})
            headline = summary.get("headline") if isinstance(summary, dict) else None
            if isinstance(headline, str) and headline.strip():
                if last_background.get("alive"):
                    user_message = headline.strip()
                else:
                    user_message = f"Previous background process ended: {headline.strip()}"
            else:
                user_message = f"Previous {worknet_name or 'AWP'} run is available for review or restart."
        else:
            user_message = f"Previous {worknet_name or 'AWP'} run is available for review or restart."
        if restart_label:
            resume_label = review_background_action_label(restart_label, restart=True)
            user_actions.append(
                {
                    "label": resume_label,
                    "description": "Restart the previous runtime follow-up action.",
                }
            )
            action_map[resume_label] = workstation_follow_up_command(restart_label, execute=True)
        if recovery.get("preferFreshStartOverResume") and preferred_profile and str(preferred_profile.get("key")) != str(recovery.get("lastWorknetKey") or ""):
            bundle_for_resume = cached_bundle or build_capability_bundle()
            preferred_report = next(
                (
                    item
                    for item in bundle_for_resume.get("reports", [])
                    if isinstance(item, dict)
                    and str(item.get("worknetId")) == str(preferred_profile.get("worknet_id"))
                ),
                None,
            )
            preferred_runnable = bool(
                preferred_report
                and preferred_report.get("runnable")
                and preferred_report.get("recommendedRole") not in {"identity", "observer"}
                and preferred_report.get("automationLevel") != "manual-only"
            )
            if preferred_runnable:
                preferred_name = str(preferred_report.get("name") or preferred_profile.get("name") or preferred_profile["key"])
                stale_reason = humanize_recovery_stale_reason(recovery.get("staleLatestRunReason"))
                user_message += (
                    f" Previous {worknet_name or 'WorkNet'} run looks stale; preferred route {preferred_name} is runnable."
                )
                if stale_reason:
                    user_message += f" {stale_reason}."
                user_actions.append(
                    {
                        "label": f"Start {preferred_name}",
                        "description": "Start the preferred WorkNet route instead of resuming stale work.",
                    }
                )
                action_map[f"Start {preferred_name}"] = run_worknet_command(
                    str(preferred_profile["key"]),
                    execute=True,
                    auto_advance=True,
                )
        user_actions.append(
            {
                "label": "Review latest epoch",
                "description": "Review the latest run and recovery state before choosing the next action.",
            }
        )
        action_map["Review latest epoch"] = "python3 scripts/review-epoch.py"
        resume_briefing = build_resume_recovery_briefing(
            recovery,
            user_actions,
            worknet_name=worknet_name,
            preferred_profile=preferred_profile,
            context_message=user_message,
            action_map=action_map,
        )
        if isinstance(resume_briefing.get("message"), str) and resume_briefing.get("message"):
            user_message = str(resume_briefing["message"])
        if isinstance(resume_briefing.get("decision"), dict):
            recovery_decision = resume_briefing.get("decision")
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
        if not restart_label:
            if recommendation is None:
                recommendation = recommend_worknet_actions(
                    cached_bundle or build_capability_bundle(),
                    preferences=preferences,
                )
            user_actions.extend(recommendation["actions"])
            action_map.update(recommendation["actionMap"])
    elif preflight.get("nextAction") in {"scan_worknets", "resume_pending_confirmations"}:
        bundle_for_recommendation = cached_bundle or build_capability_bundle()
        if recommendation is None:
            recommendation = recommend_worknet_actions(
                bundle_for_recommendation,
                preferences=preferences,
            )
        earning_runnable_count = recommendation.get("earningRunnableCount", 0)
        support_runnable_count = recommendation.get("supportRunnableCount", 0)
        detail = f"{earning_runnable_count} earning route(s) runnable"
        if support_runnable_count:
            detail += f"; {support_runnable_count} support route(s) available"
        progress = progress_message(3, 5, "WorkNet selection", detail)
        user_message = recommendation["recommendation"]
        preferred_report = next(
            (
                item
                for item in bundle_for_recommendation.get("reports", [])
                if isinstance(item, dict)
                and preferred_profile
                and str(item.get("worknetId")) == str(preferred_profile.get("worknet_id"))
            ),
            None,
        )
        preferred_runnable = bool(
            preferred_report
            and preferred_report.get("runnable")
            and preferred_report.get("recommendedRole") not in {"identity", "observer"}
            and preferred_report.get("automationLevel") != "manual-only"
        )
        if preflight.get("nextAction") == "scan_worknets" and preferred_profile and preferred_runnable:
            preferred_name = str(preferred_report.get("name") or preferred_profile.get("name") or preferred_profile["key"])
            user_message += f" Preferred WorkNet {preferred_name} is runnable."
            user_actions.append(
                {
                    "label": f"Start {preferred_name}",
                    "description": (
                        humanize_worknet_switch_summary(preferred_profile, preferred_report)
                        or "Build and run the preferred WorkNet playbook."
                    ),
                }
            )
            action_map[f"Start {preferred_name}"] = run_worknet_command(
                str(preferred_profile["key"]),
                execute=True,
                auto_advance=True,
            )
        user_actions.extend(recommendation["actions"])
        action_map.update(recommendation["actionMap"])
        if preflight.get("nextAction") == "resume_pending_confirmations":
            recovery = preflight.get("recovery", {})
            user_actions.insert(
                0,
                {
                    "label": "Resume pending confirmations",
                    "description": "Open the current run so pending confirmations can be handled.",
                },
            )
            action_map["Resume pending confirmations"] = "python3 scripts/run-workstation.py --mode autopilot"
            for label in recovery.get("pendingConfirmationLabels", []):
                if not isinstance(label, str) or not label.strip():
                    continue
                user_actions.append(
                    {
                        "label": label,
                        "description": "Review this pending confirmation before execution.",
                    }
                )
                action_map[label] = workstation_confirmation_command(label, execute=False)
            if isinstance(recovery_decision, dict):
                maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
    else:
        user_message = "Workstation                                                             "

    if str(preflight.get("nextAction") or "") in {
        "install_awp_skill_dependency",
        "run_awp_skill_registration",
        "register_agent",
        "retry_registration_preflight",
        "scan_worknets",
    }:
        if preflight_intro and preflight_intro not in user_message:
            user_message = f"{preflight_intro} {user_message}".strip()

    if knowledge_review_queue_summary.get("hasPendingReviews"):
        queue_headline = str(knowledge_review_queue_summary.get("headline") or "").strip()
        queue_headline_for_message = queue_headline or None
        if queue_headline:
            if user_message.endswith(("   ", "   ", "   ", ".", "!", "?")):
                user_message += queue_headline
            else:
                user_message += "   " + queue_headline
        queue_label = str(knowledge_review_queue_summary.get("primaryActionLabel") or "").strip()
        queue_command = str(knowledge_review_queue_summary.get("primaryActionCommand") or "").strip()
        if queue_label and queue_command and not any(item.get("label") == queue_label for item in user_actions):
            user_actions.append(
                {
                    "label": queue_label,
                    "description": "Review changed source material before trusting generated guidance.",
                }
            )
            action_map[queue_label] = queue_command

    if preflight.get("registered") is not True and registration_plan.get("officialNextAction") == "retry_preflight":
        user_message += " Retry the awp-skill preflight after the AWP API is reachable."

    append_user_action(
        user_actions,
        action_map,
        label="Research AWP",
        description="Open the workstation research view for AWP protocol and WorkNet context.",
        command=workstation_status_command(intent="research"),
    )

    execution_state = derive_execution_state(
        recovery=preflight.get("recovery"),
        next_action=preflight.get("nextAction"),
    )
    resume_status = str(recovery_decision.get("status") or "").strip() if isinstance(recovery_decision, dict) else None
    user_actions = prioritize_ui_actions(
        user_actions,
        action_map,
        execution_state=execution_state.get("executionState"),
        resume_status=resume_status,
        worknet_key=str(preflight.get("recovery", {}).get("lastWorknetKey") or "").strip() or None,
    )
    user_action_details = action_details_from_ui_actions(user_actions, action_map)
    user_action_details = annotate_execution_actions(user_action_details)
    user_actions = annotate_execution_actions(user_actions)
    public_user_actions = humanize_public_action_entries(user_actions)
    public_preflight = dict(preflight)
    public_preflight["recoveryDecision"] = humanize_public_recovery_decision(preflight.get("recoveryDecision"))
    user_message = align_run_execution_user_message(
        user_message,
        execution_state=execution_state.get("executionState"),
        execution_headline=execution_state.get("executionHeadline"),
        primary_action=user_actions[0]["label"] if user_actions else None,
        worknet_context_key=str(preflight.get("recovery", {}).get("lastWorknetKey") or ""),
        include_canonical_plain=False,
        extra_parts=[queue_headline_for_message] if queue_headline_for_message else None,
    )
    payload = {
        "progress": progress,
        "intro": intro,
        "user_message": user_message,
        "user_actions": public_user_actions,
        "resumeStatus": resume_status or None,
        "resumeStatusDisplay": recovery_status_display(resume_status) if resume_status else None,
        "executionState": execution_state.get("executionState"),
        "executionStateDisplay": execution_state.get("executionStateDisplay"),
        "executionHeadline": execution_state.get("executionHeadline"),
        "primaryUserAction": user_actions[0]["label"] if user_actions else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "userActionDetails": user_action_details,
        "recoveryDecision": humanize_public_recovery_decision(recovery_decision),
        "knowledgeReviewQueueSummary": knowledge_review_queue_summary,
        "knowledgeOverview": knowledge_overview,
        "knowledgeFocusTopics": knowledge_focus_topics,
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "_internal": {
            "action_map": action_map,
            "preflight": public_preflight,
            "capability_bundle_path": str(Path(state["cache"]) / "capability-scan.json"),
        },
    }
    if persist:
        atomic_write_json(Path(state["cache"]) / "start-response.json", payload)
    return payload
