"""Workstation status builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def _snapshot_answer(state_summary: dict[str, Any]) -> str:
    task = str(state_summary.get("currentTask") or "Workstation state").strip()
    phase = str(state_summary.get("currentExecutionPhaseDisplay") or state_summary.get("currentExecutionPhase") or "").strip()
    worknet = str(state_summary.get("currentWorknetName") or state_summary.get("currentWorknetKey") or "").strip()
    next_action = str(state_summary.get("nextRecommendedAction") or "").strip()
    parts = [task]
    if worknet:
        parts.append(f"Current WorkNet: {worknet}.")
    if phase:
        parts.append(f"Phase: {phase}.")
    if next_action:
        parts.append(f"Suggested action: {next_action}.")
    return " ".join(part for part in parts if part).strip()


def _snapshot_action_bundle(state_summary: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    label = str(state_summary.get("nextRecommendedAction") or "").strip()
    command = str(state_summary.get("nextRecommendedActionCommand") or "").strip()
    if not label:
        return [], []
    user_actions = [{"label": label, "description": "Continue from the cached workstation snapshot."}]
    user_action_details = [
        {
            "label": label,
            "displayLabel": label,
            "description": "Continue from the cached workstation snapshot.",
            "command": command or None,
        }
    ]
    return user_actions, user_action_details


def _snapshot_fallback_report(
    *,
    state_summary: dict[str, Any],
    query: Optional[str],
    intent: str,
    now_iso: Any,
    recovery_status_display: Any,
) -> dict[str, Any]:
    user_actions, user_action_details = _snapshot_action_bundle(state_summary)
    resume_status = state_summary.get("resumeStatus")
    return {
        "generatedAt": now_iso(),
        "query": query,
        "intent": intent,
        "progress": "[5/5] Workstation Status",
        "headline": str(state_summary.get("currentTask") or "Cached workstation snapshot").strip(),
        "answer": _snapshot_answer(state_summary),
        "status": state_summary.get("status") or "snapshot_available",
        "error": None,
        "missingCaches": [],
        "resumeStatus": resume_status,
        "resumeStatusDisplay": recovery_status_display(resume_status) if resume_status else None,
        "executionState": state_summary.get("currentExecutionPhase"),
        "executionStateDisplay": state_summary.get("currentExecutionPhaseDisplay"),
        "executionHeadline": state_summary.get("currentTask"),
        "worknetKey": state_summary.get("currentWorknetKey"),
        "worknetName": state_summary.get("currentWorknetName"),
        "sourceKey": None,
        "sourceName": None,
        "readOnly": True,
        "knowledgeCaveat": "Using the cached workstation-state snapshot because richer status caches are missing.",
        "recoveryDecision": None,
        "knowledgeReviewQueueSummary": {},
        "knowledgeOverview": {},
        "knowledgeFocusTopics": [],
        "knowledgeReferenceHighlights": [],
        "knowledgeSourceHighlights": [],
        "sourceTopicHighlights": [],
        "sourceFactHighlights": [],
        "sourceWorknetHighlights": [],
        "sourceEvidenceHighlights": [],
        "knowledgeRecord": None,
        "sourceRecord": None,
        "targetWorknetDisplay": None,
        "stateSummary": state_summary,
        "primaryUserAction": label if (label := state_summary.get("nextRecommendedAction")) else None,
        "primaryUserActionDisplay": label if label else None,
        "primaryUserActionCommand": state_summary.get("nextRecommendedActionCommand"),
        "userActions": user_actions,
        "userActionDetails": user_action_details,
        "latestReview": {},
        "_internal": {
            "action_map": {
                detail["label"]: detail.get("command")
                for detail in user_action_details
                if isinstance(detail, dict) and detail.get("command")
            },
            "stateRoot": None,
            "snapshotFallback": True,
        },
        "researchActionGroups": [],
    }


def _predict_live_earnings_hint(record: dict[str, Any]) -> Optional[str]:
    payload = record.get("statusPayload") if isinstance(record.get("statusPayload"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    recent_results = [item for item in data.get("recent_results", []) if isinstance(item, dict)] if isinstance(data.get("recent_results"), list) else []
    open_orders = [item for item in data.get("open_orders", []) if isinstance(item, dict)] if isinstance(data.get("open_orders"), list) else []
    balance = str(data.get("balance") or "").strip()
    total_predictions = data.get("total_predictions")
    parts: list[str] = []

    if recent_results:
        wins = sum(1 for item in recent_results if item.get("won") is True)
        payout_total = 0
        for item in recent_results:
            try:
                payout_total += int(item.get("payout_chips") or 0)
            except (TypeError, ValueError):
                continue
        result_text = f"Recent Predict results: {len(recent_results)} result(s), {wins} win(s), payout {payout_total} chips"
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
        if latest_market:
            result_text += f"; latest {latest_market}"
        parts.append(result_text + ".")

    if balance:
        balance_text = f"Current Predict balance: {balance} chips"
        if total_predictions not in (None, ""):
            balance_text += f" after {total_predictions} total prediction(s)"
        parts.append(balance_text + ".")

    if open_orders:
        total_tickets = 0
        total_filled = 0
        for item in open_orders:
            try:
                total_tickets += int(item.get("tickets") or 0)
            except (TypeError, ValueError):
                continue
            try:
                total_filled += int(item.get("tickets_filled") or 0)
            except (TypeError, ValueError):
                continue
        parts.append(f"Open orders: {len(open_orders)} active, {total_filled}/{total_tickets} tickets filled.".strip())

    return " ".join(part for part in parts if part).strip() or None


def _mine_live_earnings_hint(record: dict[str, Any]) -> Optional[str]:
    payload = record.get("statusPayload") if isinstance(record.get("statusPayload"), dict) else {}
    internal = payload.get("_internal") if isinstance(payload.get("_internal"), dict) else {}
    runtime_status = internal.get("status") if isinstance(internal.get("status"), dict) else {}
    earnings_summary = runtime_status.get("earnings_summary") if isinstance(runtime_status.get("earnings_summary"), dict) else {}
    progress = runtime_status.get("progress") if isinstance(runtime_status.get("progress"), dict) else {}

    parts: list[str] = []
    submitted = earnings_summary.get("submitted")
    target = earnings_summary.get("target")
    percent = earnings_summary.get("progress_percent") or progress.get("epoch_completion_percent")
    remaining = earnings_summary.get("remaining") or progress.get("epoch_remaining")
    eta = earnings_summary.get("estimated_completion") or progress.get("estimated_completion")
    if submitted not in (None, "") or target not in (None, ""):
        progress_text = f"Mine epoch progress: {submitted or 0}/{target or '?'}"
        if percent not in (None, ""):
            progress_text += f" ({percent}% complete)"
        if remaining not in (None, ""):
            progress_text += f", {remaining} remaining"
        if eta not in (None, ""):
            progress_text += f", ETA {eta}"
        parts.append(progress_text + ".")

    credit_score = runtime_status.get("credit_score")
    credit_tier = str(runtime_status.get("credit_tier") or "").strip()
    if credit_score not in (None, "") or credit_tier:
        credit_text = "Mine credit"
        if credit_score not in (None, ""):
            credit_text += f" score {credit_score}"
        if credit_tier:
            credit_text += f", tier {credit_tier}"
        parts.append(credit_text + ".")

    summary = record.get("summary", {}) if isinstance(record.get("summary"), dict) else {}
    detail = str(summary.get("detail") or "").strip()
    if detail and not parts:
        parts.append(detail if detail.endswith(".") else detail + ".")
    return " ".join(part for part in parts if part).strip() or None


def _background_earnings_hints(active_background_records: list[dict[str, Any]]) -> list[str]:
    hints: list[str] = []
    for item in active_background_records:
        if not isinstance(item, dict):
            continue
        worknet_key = str(item.get("worknetKey") or "").strip().lower()
        hint = None
        if worknet_key == "predict":
            hint = _predict_live_earnings_hint(item)
        elif worknet_key == "mine":
            hint = _mine_live_earnings_hint(item)
        if hint and hint not in hints:
            hints.append(hint)
    return hints


def build_workstation_status_payload(
    *,
    query: Optional[str] = None,
    intent: Optional[str] = None,
    worknet_identifier: Optional[str] = None,
    source_identifier: Optional[str] = None,
    read_only: bool = False,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("workstation status dependencies are required")
    action_details_from_ui_actions = dependencies["action_details_from_ui_actions"]
    aggregate_background_supervisor_view = dependencies["aggregate_background_supervisor_view"]
    align_run_execution_user_message = dependencies["align_run_execution_user_message"]
    annotate_execution_actions = dependencies["annotate_execution_actions"]
    annotate_research_action_details = dependencies["annotate_research_action_details"]
    append_user_action = dependencies["append_user_action"]
    atomic_write_json = dependencies["atomic_write_json"]
    background_supervisor_view = dependencies["background_supervisor_view"]
    build_capability_bundle = dependencies["build_capability_bundle"]
    build_epoch_review = dependencies["build_epoch_review"]
    build_knowledge_query_result = dependencies["build_knowledge_query_result"]
    build_knowledge_review_queue = dependencies["build_knowledge_review_queue"]
    build_playbook_command = dependencies["build_playbook_command"]
    build_research_action_groups = dependencies["build_research_action_groups"]
    build_resume_recovery_briefing = dependencies["build_resume_recovery_briefing"]
    build_source_query_result = dependencies["build_source_query_result"]
    build_start_response = dependencies["build_start_response"]
    build_workstation_state_summary = dependencies["build_workstation_state_summary"]
    derive_execution_state = dependencies["derive_execution_state"]
    detect_source_from_text = dependencies["detect_source_from_text"]
    detect_worknet_from_text = dependencies["detect_worknet_from_text"]
    direct_knowledge_topic_from_research_text = dependencies["direct_knowledge_topic_from_research_text"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    execution_state_payload = dependencies["execution_state_payload"]
    find_topic_directory_entry = dependencies["find_topic_directory_entry"]
    frontload_user_action_labels = dependencies["frontload_user_action_labels"]
    humanize_knowledge_source_label = dependencies["humanize_knowledge_source_label"]
    humanize_public_action_entries = dependencies["humanize_public_action_entries"]
    humanize_public_recovery_decision = dependencies["humanize_public_recovery_decision"]
    humanize_worknet_switch_summary = dependencies["humanize_worknet_switch_summary"]
    knowledge_action_description = dependencies["knowledge_action_description"]
    knowledge_focus_topics_payload = dependencies["knowledge_focus_topics_payload"]
    knowledge_reference_highlights_payload = dependencies["knowledge_reference_highlights_payload"]
    knowledge_related_source_highlights = dependencies["knowledge_related_source_highlights"]
    knowledge_review_queue_note_for_target = dependencies["knowledge_review_queue_note_for_target"]
    knowledge_source_action_description = dependencies["knowledge_source_action_description"]
    knowledge_source_highlights_payload = dependencies["knowledge_source_highlights_payload"]
    load_active_processes = dependencies["load_active_processes"]
    load_cached_capability_bundle = dependencies["load_cached_capability_bundle"]
    load_cached_knowledge_catalog = dependencies["load_cached_knowledge_catalog"]
    load_cached_knowledge_review_queue = dependencies["load_cached_knowledge_review_queue"]
    load_cached_workstation_state_summary = dependencies["load_cached_workstation_state_summary"]
    load_json = dependencies["load_json"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    load_user_preferences = dependencies["load_user_preferences"]
    maybe_promote_recovery_decision = dependencies["maybe_promote_recovery_decision"]
    merge_payload_user_action_details = dependencies["merge_payload_user_action_details"]
    merge_payload_user_actions = dependencies["merge_payload_user_actions"]
    merge_recovery_decision_actions = dependencies["merge_recovery_decision_actions"]
    now_iso = dependencies["now_iso"]
    persist_background_observation = dependencies["persist_background_observation"]
    prioritize_ui_actions = dependencies["prioritize_ui_actions"]
    public_earnings_hint_for_worknet = dependencies["public_earnings_hint_for_worknet"]
    query_knowledge_command = dependencies["query_knowledge_command"]
    recommend_worknet_actions = dependencies["recommend_worknet_actions"]
    recovery_status_display = dependencies["recovery_status_display"]
    resolve_worknet = dependencies["resolve_worknet"]
    resolve_workstation_status_intent = dependencies["resolve_workstation_status_intent"]
    review_epoch_command = dependencies["review_epoch_command"]
    run_worknet_command = dependencies["run_worknet_command"]
    safe_slug = dependencies["safe_slug"]
    scan_worknets_command = dependencies["scan_worknets_command"]
    state_context = dependencies["state_context"]
    summarize_background_record = dependencies["summarize_background_record"]
    summarize_knowledge_review_queue = dependencies["summarize_knowledge_review_queue"]
    worknet_runtime_maturity_note = dependencies["worknet_runtime_maturity_note"]
    workstation_background_command = dependencies["workstation_background_command"]
    workstation_pause_command = dependencies["workstation_pause_command"]
    workstation_preferences_command = dependencies["workstation_preferences_command"]
    workstation_preflight_command = dependencies["workstation_preflight_command"]

    state = state_context()
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    pending_confirmations = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    cached_monitor = load_json(Path(state["cache"]) / "workstation-monitor.json", {})
    cached_state_summary = load_cached_workstation_state_summary(state=state) if read_only else {}
    active_background_records = [
        persist_background_observation(
            state,
            summarize_background_record(item, tail_lines=30),
        )
        for item in load_active_processes(state)
        if isinstance(item, dict)
    ]
    aggregate_background = aggregate_background_supervisor_view(active_background_records) if len(active_background_records) > 1 else {}
    preferences = load_user_preferences(state) if read_only else ensure_user_preferences(state)
    knowledge_catalog = load_cached_knowledge_catalog(state) if read_only else load_or_build_knowledge_catalog(state)
    start_response = (
        load_json(Path(state["cache"]) / "start-response.json", {})
        if read_only
        else build_start_response()
    )
    review = (
        load_json(Path(state["reviews"]) / "latest-review.json", {})
        if read_only
        else build_epoch_review()
    )
    knowledge_review_queue = (
        load_cached_knowledge_review_queue(state)
        if read_only
        else (load_cached_knowledge_review_queue(state) or build_knowledge_review_queue(state=state))
    )
    if read_only:
        missing_caches: list[str] = []
        if not isinstance(knowledge_catalog, dict) or not knowledge_catalog:
            missing_caches.append("knowledge-catalog.json")
        if not isinstance(start_response, dict) or not start_response:
            missing_caches.append("start-response.json")
        if not isinstance(review, dict) or not review:
            missing_caches.append("latest-review.json")
        if not isinstance(knowledge_review_queue, dict) or not knowledge_review_queue:
            missing_caches.append("knowledge-review-queue.json")
        if missing_caches:
            resolved_intent = resolve_workstation_status_intent(query, explicit_intent=intent)
            if isinstance(cached_state_summary, dict) and cached_state_summary:
                report = _snapshot_fallback_report(
                    state_summary=cached_state_summary,
                    query=query,
                    intent=resolved_intent,
                    now_iso=now_iso,
                    recovery_status_display=recovery_status_display,
                )
                report["missingCaches"] = missing_caches
                report["_internal"]["stateRoot"] = state["root"]
                return report
            return {
                "generatedAt": now_iso(),
                "query": query,
                "intent": resolved_intent,
                "progress": "[5/5] Workstation Status",
                "headline": "Cached workstation status is not available.",
                "answer": "Read-only status cannot rebuild missing caches: " + ", ".join(missing_caches) + ".",
                "status": "cache_missing",
                "readOnly": True,
                "missingCaches": missing_caches,
                "error": "cache_missing",
                "stateRoot": state["root"],
            }
    knowledge_overview = (
        knowledge_catalog.get("knowledgeOverview", {})
        if isinstance(knowledge_catalog.get("knowledgeOverview"), dict)
        else {}
    )
    knowledge_focus_topics = knowledge_focus_topics_payload(knowledge_catalog)
    knowledge_reference_highlights = knowledge_reference_highlights_payload(knowledge_catalog)
    knowledge_source_highlights = knowledge_source_highlights_payload(knowledge_catalog)
    topic_directory = knowledge_catalog.get("topicDirectory", []) if isinstance(knowledge_catalog.get("topicDirectory"), list) else []
    preflight = (
        start_response.get("_internal", {}).get("preflight", {})
        if isinstance(start_response.get("_internal"), dict)
        else {}
    )
    knowledge_review_queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
    resolved_intent = resolve_workstation_status_intent(query, explicit_intent=intent)
    target_profile = detect_worknet_from_text(query, explicit_identifier=worknet_identifier)
    target_source = detect_source_from_text(
        query,
        explicit_identifier=source_identifier,
        catalog=knowledge_catalog,
    )
    explicit_worknet_requested = isinstance(worknet_identifier, str) and worknet_identifier.strip()
    target_knowledge_topic = None
    if resolved_intent == "research" and target_source is None and not explicit_worknet_requested:
        target_knowledge_topic = direct_knowledge_topic_from_research_text(knowledge_catalog, query)
        if target_knowledge_topic:
            target_profile = None
    if (
        target_source is not None
        and resolved_intent == "status"
        and not (isinstance(intent, str) and intent.strip())
        and isinstance(source_identifier, str)
        and source_identifier.strip()
    ):
        resolved_intent = "research"
    recovery_decision = (
        preflight.get("recoveryDecision")
        if isinstance(preflight.get("recoveryDecision"), dict)
        else None
    )
    bundle = load_cached_capability_bundle(state)
    if (target_profile or resolved_intent == "switch-worknet") and not read_only:
        bundle = bundle or build_capability_bundle()

    reports_by_key: dict[str, dict[str, Any]] = {}
    if isinstance(bundle, dict):
        for item in bundle.get("reports", []):
            if not isinstance(item, dict):
                continue
            profile = (
                resolve_worknet(str(item.get("worknetId") or ""))
                or resolve_worknet(str(item.get("name") or ""))
                or resolve_worknet(str(item.get("symbol") or ""))
            )
            if profile is not None:
                reports_by_key[profile["key"]] = item

    review_generated_at = str(review.get("generatedAt") or now_iso())
    current_worknet_key = str(review.get("worknetKey") or "").strip() or None
    current_worknet_name = str(review.get("worknetName") or "").strip() or None
    current_status = str(review.get("status") or preflight.get("nextAction") or "idle")
    current_headline = str(review.get("headline") or start_response.get("user_message") or "Workstation                ")
    current_answer = str(review.get("dailySummary") or start_response.get("user_message") or current_headline)

    knowledge_caveat = None
    if resolved_intent == "review-queue":
        knowledge_caveat = str(knowledge_review_queue_summary.get("headline") or "").strip() or None
    elif target_source is not None:
        knowledge_caveat = knowledge_review_queue_note_for_target(
            knowledge_review_queue,
            target_source.get("key"),
            target_label=humanize_knowledge_source_label(target_source.get("name") or target_source.get("key")),
        )
    elif target_profile is not None:
        knowledge_caveat = knowledge_review_queue_note_for_target(
            knowledge_review_queue,
            target_profile.get("key"),
            target_label=target_profile.get("name"),
        )
    elif current_worknet_key:
        knowledge_caveat = knowledge_review_queue_note_for_target(
            knowledge_review_queue,
            current_worknet_key,
            target_label=current_worknet_name,
        )

    user_actions: list[dict[str, Any]] = []
    action_map: dict[str, str] = {}

    headline = current_headline
    answer = current_answer
    status = current_status
    worknet_key = target_profile.get("key") if isinstance(target_profile, dict) else current_worknet_key
    worknet_name = target_profile.get("name") if isinstance(target_profile, dict) else current_worknet_name
    source_key = str(target_source.get("key") or "").strip() if isinstance(target_source, dict) else None
    source_name = (
        humanize_knowledge_source_label(target_source.get("name") or target_source.get("key"))
        if isinstance(target_source, dict)
        else None
    )
    source_record: Optional[dict[str, Any]] = None
    topic_knowledge_record: Optional[dict[str, Any]] = None
    target_worknet_display: Optional[dict[str, Any]] = None
    related_source_highlights: list[dict[str, Any]] = []
    source_topic_highlights: list[dict[str, Any]] = []
    source_fact_highlights: list[dict[str, Any]] = []
    source_worknet_highlights: list[dict[str, Any]] = []
    source_evidence_highlights: list[dict[str, Any]] = []
    research_action_groups: list[dict[str, Any]] = []
    research_current_labels: list[str] = []
    research_control_labels: list[str] = []
    research_source_labels: list[str] = []
    research_topic_labels: list[str] = []
    research_worknet_labels: list[str] = []
    research_reference_labels: list[str] = []
    pause_priority_labels: list[str] = []
    status_priority_labels: list[str] = []

    if resolved_intent == "status":
        merge_payload_user_actions(user_actions, action_map, start_response)
        if isinstance(recovery_decision, dict):
            maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
        recovery_mode = str(preflight.get("nextAction") or "") in {
            "resume_previous_run",
            "resume_runtime_guidance",
            "resume_pending_confirmations",
            "monitor_background_runs",
        }
        if recovery_mode and isinstance(recovery_decision, dict):
            headline = str(recovery_decision.get("headline") or start_response.get("user_message") or current_headline)
            answer = str(recovery_decision.get("message") or start_response.get("user_message") or current_answer)
            status = str(recovery_decision.get("status") or preflight.get("nextAction") or current_status)
        else:
            headline = str(start_response.get("user_message") or current_headline)
            answer = str(review.get("dailySummary") or start_response.get("user_message") or current_answer)
            status = str(review.get("status") or preflight.get("nextAction") or current_status)
    elif resolved_intent == "continue":
        merge_payload_user_actions(user_actions, action_map, start_response)
        recovery = (
            preflight.get("recovery", {})
            if isinstance(preflight.get("recovery"), dict)
            else {}
        )
        preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))
        resume_briefing = build_resume_recovery_briefing(
            recovery,
            user_actions,
            worknet_name=worknet_name,
            preferred_profile=preferred_profile,
            context_message=None,
            action_map=action_map,
        )
        headline = str(resume_briefing.get("headline") or start_response.get("user_message") or current_headline)
        answer = str(resume_briefing.get("message") or start_response.get("user_message") or review.get("dailySummary") or current_answer)
        status = str(resume_briefing.get("status") or review.get("status") or preflight.get("nextAction") or current_status)
        if isinstance(resume_briefing.get("decision"), dict):
            recovery_decision = resume_briefing.get("decision")
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
    elif resolved_intent == "earnings":
        rewards = [str(item).strip() for item in review.get("estimatedRewards", []) if str(item).strip()]
        live_hints = _background_earnings_hints(active_background_records)
        public_hint = public_earnings_hint_for_worknet(state, worknet_key or current_worknet_key or "")
        headline = "Earnings"
        answer_parts: list[str] = []
        if live_hints:
            answer_parts.append(live_hints[0])
            if len(live_hints) > 1:
                answer_parts.append(f"{len(live_hints) - 1} additional live earnings context item(s) are available from other background tasks.")
            status = "estimated"
        if rewards:
            review_text = f"Latest review {review_generated_at}: {rewards[0]}"
            if len(rewards) > 1:
                review_text += " " + rewards[1]
            answer_parts.append(review_text)
            status = "estimated"
        if public_hint:
            answer_parts.append(public_hint)
            status = "estimated"
        if answer_parts:
            answer = " ".join(part for part in answer_parts if part).strip()
        else:
            answer = f"Latest review {review_generated_at}: no reward estimate is available yet."
            status = "unavailable"
        if len(active_background_records) == 1 and isinstance(active_background_records[0], dict):
            label = str(active_background_records[0].get("label") or "").strip()
            if label:
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"Inspect {label}",
                    description="Inspect the active background task for the latest live earnings context.",
                    command=workstation_background_command(label, tail_lines=80),
                )
        append_user_action(
            user_actions,
            action_map,
            label="Review latest epoch",
            description="Review the latest epoch summary and reward evidence.",
            command=review_epoch_command(),
        )
        merge_payload_user_actions(user_actions, action_map, start_response)
        if isinstance(recovery_decision, dict):
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision)
    elif resolved_intent == "failures":
        failures = [str(item).strip() for item in review.get("failures", []) if str(item).strip()]
        strategy_changes = [str(item).strip() for item in review.get("strategyChanges", []) if str(item).strip()]
        headline = "Failures"
        if failures:
            answer = f"Latest review {review_generated_at}: {failures[0]}"
            if len(failures) > 1:
                answer += f" {len(failures) - 1} additional failure(s) recorded."
            status = "blocked" if str(review.get("status") or "") == "blocked" else "partial"
        else:
            answer = f"Latest review {review_generated_at}: no failures are recorded."
            status = "clear"
        if strategy_changes:
            answer += f" Strategy change: {strategy_changes[0]}"
        append_user_action(
            user_actions,
            action_map,
            label="Review latest epoch",
            description="Inspect failures, recovery guidance, and strategy changes.",
            command=review_epoch_command(),
        )
        merge_payload_user_actions(user_actions, action_map, start_response)
        if isinstance(recovery_decision, dict):
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision)
    elif resolved_intent == "pause":
        active = [
            persist_background_observation(
                state,
                summarize_background_record(item, tail_lines=30),
            )
            for item in load_active_processes(state)
        ]
        if not active:
            headline = "Idle"
            answer = "No active background process is registered."
            status = "idle"
            merge_payload_user_actions(user_actions, action_map, start_response)
            if isinstance(recovery_decision, dict):
                maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
        elif len(active) == 1:
            item = active[0]
            supervisor = background_supervisor_view(item)
            background_headline = str(
                supervisor.get("headline")
                or (item.get("summary", {}) if isinstance(item.get("summary"), dict) else {}).get("headline")
                or "Background process is running."
            ).strip()
            headline = str(supervisor.get("display") or "Background running")
            answer = str(supervisor.get("message") or f"One background process is running: {background_headline}")
            status = str(supervisor.get("status") or "background_running")
            if isinstance(recovery_decision, dict) and str(recovery_decision.get("status") or "").strip() == "background_running":
                merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
            if not user_actions:
                next_action_label = str(supervisor.get("nextActionLabel") or "").strip()
                next_action_command = str(supervisor.get("nextActionCommand") or "").strip()
                if next_action_label and next_action_command:
                    append_user_action(
                        user_actions,
                        action_map,
                        label=next_action_label,
                        description="Continue from the background runtime's next required step.",
                        command=next_action_command,
                    )
                    pause_priority_labels.append(next_action_label)
                if status == "awaiting_dataset":
                    append_user_action(
                        user_actions,
                        action_map,
                        label=f"Inspect {item.get('label')}",
                        description="Inspect Mine dataset selection guidance and recent log tail.",
                        command=workstation_background_command(str(item.get("label")), tail_lines=80),
                    )
                append_user_action(
                    user_actions,
                    action_map,
                    label="Pause background work",
                    description="Pause the active background process.",
                    command=workstation_pause_command(execute=True),
                )
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"Inspect {item.get('label')}",
                    description="Inspect the active background process status and log tail.",
                    command=workstation_background_command(str(item.get("label")), tail_lines=80),
                )
                if isinstance(recovery_decision, dict):
                    maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
        else:
            headline = "Background running"
            answer = f"{len(active)} background processes are registered."
            status = "background_running"
            if isinstance(recovery_decision, dict) and str(recovery_decision.get("status") or "").strip() == "background_running":
                merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
            if not user_actions:
                for item in active[:3]:
                    label = str(item.get("label") or "").strip()
                    if not label:
                        continue
                    append_user_action(
                        user_actions,
                        action_map,
                        label=f"Stop {label}",
                        description="Stop this background process after confirmation.",
                        command=workstation_background_command(label, stop=True, execute=False),
                    )
                    append_user_action(
                        user_actions,
                        action_map,
                        label=f"Inspect {label}",
                        description="Inspect this background process status and log tail.",
                        command=workstation_background_command(label, tail_lines=80),
                    )
                if isinstance(recovery_decision, dict):
                    maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
    elif resolved_intent == "switch-worknet":
        bundle = bundle or build_capability_bundle()
        recommendation = recommend_worknet_actions(bundle, preferences=preferences)
        if target_profile is not None:
            target_key = str(target_profile.get("key"))
            target_name = str(target_profile.get("name"))
            target_report = reports_by_key.get(target_key, {})
            runnable = bool(target_report.get("runnable"))
            summary = humanize_worknet_switch_summary(target_profile, target_report)
            headline = f"WorkNet: {target_name}"
            if runnable:
                answer = summary
                status = "runnable"
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"Start {target_name}",
                    description=(
                        humanize_worknet_switch_summary(target_profile, target_report)
                        or "Build and run this WorkNet playbook."
                    ),
                    command=run_worknet_command(target_key, execute=True, auto_advance=True),
                )
            else:
                answer = summary
                status = "discover_only"
            append_user_action(
                user_actions,
                action_map,
                label=f"Set preferred WorkNet: {target_name}",
                description="Save this WorkNet as the preferred default route.",
                command=workstation_preferences_command(preferred_worknet=target_key),
            )
            append_user_action(
                user_actions,
                action_map,
                label=f"Research {target_name}",
                description="Open WorkNet knowledge context and source evidence.",
                command=query_knowledge_command(target_key),
            )
            append_user_action(
                user_actions,
                action_map,
                label=f"Build {target_name} playbook",
                description="Build the WorkNet playbook without running it.",
                command=build_playbook_command(target_key),
            )
        else:
            headline = "          WorkNet"
            answer = str(recommendation.get("recommendation") or "Review WorkNet options before choosing a route.")
            status = "switch_suggested"
            for item in recommendation.get("actions", []):
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                description = str(item.get("description") or "Review this WorkNet option.")
                command = recommendation.get("actionMap", {}).get(label)
                append_user_action(
                    user_actions,
                    action_map,
                    label=label,
                    description=description,
                    command=command if isinstance(command, str) else None,
                )
            preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))
            if preferred_profile is not None:
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"Research {preferred_profile.get('name')}",
                    description="Open knowledge context for the preferred WorkNet.",
                    command=query_knowledge_command(str(preferred_profile.get("key"))),
                )
            append_user_action(
                user_actions,
                action_map,
                label="       WorkNet       ",
                description="Scan available WorkNets and capability reports.",
                command=scan_worknets_command(),
            )
    elif resolved_intent == "safety":
        active = load_active_processes(state)
        headline = "Safety"
        answer = "Workstation safety policy requires confirmation before value-moving actions."
        answer += (
            f" Autopilot mode: {preferences.get('autopilotMode')}; "
            f"allowAssetActions={str(bool(preferences.get('allowAssetActions'))).lower()}   "
        )
        status = "non_financial_only" if str(preferences.get("autopilotMode")) == "non-financial-only" else "custom"
        append_user_action(
            user_actions,
            action_map,
            label="Force non-financial autopilot",
            description="Disable asset-moving actions and keep autopilot in non-financial-only mode.",
            command=workstation_preferences_command(
                allow_asset_actions=False,
                autopilot_mode="non-financial-only",
            ),
        )
        if active:
            append_user_action(
                user_actions,
                action_map,
                label="Pause background work",
                description="Pause active background work before changing safety settings.",
                command=workstation_pause_command(execute=True),
            )
        append_user_action(
            user_actions,
            action_map,
            label="Run full preflight",
            description="Re-check wallet, skill, source, and WorkNet readiness.",
            command=workstation_preflight_command(full=True),
        )
        append_user_action(
            user_actions,
            action_map,
            label="Review latest epoch",
            description="Inspect recent execution, confirmations, and recovery notes.",
            command=review_epoch_command(),
        )
    elif resolved_intent == "review-queue":
        review_queue_payload = build_knowledge_query_result("review-queue", catalog=knowledge_catalog)
        headline = str(review_queue_payload.get("headline") or "Knowledge review queue")
        answer = str(review_queue_payload.get("summary") or knowledge_review_queue_summary.get("headline") or "No pending knowledge review summary is available.")
        status = str(review_queue_payload.get("status") or ("stale_knowledge_pending" if knowledge_review_queue_summary.get("hasPendingReviews") else "knowledge_fresh"))
        worknet_key = None
        worknet_name = None
        merge_payload_user_action_details(user_actions, action_map, review_queue_payload, limit=8)
        if isinstance(review_queue_payload.get("researchActionGroups"), list):
            research_action_groups = review_queue_payload.get("researchActionGroups", [])
        queue_primary_label = str(review_queue_payload.get("primaryUserAction") or knowledge_review_queue_summary.get("primaryActionLabel") or "").strip()
        if queue_primary_label:
            research_current_labels.append(queue_primary_label)
        queue_topic_actions = review_queue_payload.get("userActionDetails", []) if isinstance(review_queue_payload, dict) else []
        for item in queue_topic_actions:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label or label == queue_primary_label:
                continue
            if label.startswith(("Review source", "Refresh source", "Research source")):
                research_source_labels.append(label)
            elif label.startswith(("Review topic", "Refresh topic", "Research topic")):
                research_topic_labels.append(label)
            elif label in {"Refresh knowledge review queue", "Review pending knowledge updates"}:
                research_control_labels.append(label)
        queue_refresh_label = str(knowledge_review_queue_summary.get("refreshActionLabel") or "").strip()
        if queue_refresh_label:
            research_control_labels.append(queue_refresh_label)

    if (
        resolved_intent in {"status", "continue"}
        and len(active_background_records) == 1
        and not pending_confirmations
        and target_source is None
        and not target_knowledge_topic
        and (target_profile is None or str(target_profile.get("key") or "").strip() == str(active_background_records[0].get("worknetKey") or "").strip())
    ):
        background_record = active_background_records[0]
        supervisor = background_supervisor_view(background_record)
        if isinstance(supervisor, dict):
            headline = str(
                supervisor.get("display")
                or supervisor.get("headline")
                or headline
            ).strip() or headline
            answer = str(
                supervisor.get("message")
                or supervisor.get("headline")
                or answer
            ).strip() or answer
            status = str(supervisor.get("status") or status).strip() or status
            if background_record.get("worknetKey"):
                worknet_key = str(background_record.get("worknetKey") or "").strip() or worknet_key
            if background_record.get("worknetName"):
                worknet_name = str(background_record.get("worknetName") or "").strip() or worknet_name

            next_action_label = str(supervisor.get("nextActionLabel") or "").strip()
            next_action_command = str(supervisor.get("nextActionCommand") or "").strip()
            if next_action_label and next_action_command:
                append_user_action(
                    user_actions,
                    action_map,
                    label=next_action_label,
                    description="Continue from the active background runtime's next required step.",
                    command=next_action_command,
                )
                status_priority_labels.append(next_action_label)

            inspect_label = f"Inspect {background_record.get('label')}"
            append_user_action(
                user_actions,
                action_map,
                label=inspect_label,
                description="Inspect the active background process status and log tail.",
                command=workstation_background_command(str(background_record.get("label")), tail_lines=80),
            )
            status_priority_labels.append(inspect_label)

            if background_record.get("alive"):
                append_user_action(
                    user_actions,
                    action_map,
                    label="Pause background work",
                    description="Pause the active background process.",
                    command=workstation_pause_command(execute=True),
                )
                status_priority_labels.append("Pause background work")
    elif (
        resolved_intent in {"status", "continue"}
        and len(active_background_records) > 1
        and not pending_confirmations
        and target_source is None
        and not target_knowledge_topic
        and isinstance(aggregate_background, dict)
        and aggregate_background.get("count")
    ):
        headline = str(aggregate_background.get("headline") or headline).strip() or headline
        answer = str(aggregate_background.get("message") or answer).strip() or answer
        status = str(aggregate_background.get("status") or status).strip() or status
        if target_profile is None:
            worknet_key = None
            worknet_name = "Multiple WorkNets"

        next_action_label = str(aggregate_background.get("nextActionLabel") or "").strip()
        next_action_command = str(aggregate_background.get("nextActionCommand") or "").strip()
        if next_action_label and next_action_command:
            append_user_action(
                user_actions,
                action_map,
                label=next_action_label,
                description="Continue from the most urgent background runtime step.",
                command=next_action_command,
            )
            status_priority_labels.append(next_action_label)

        ordered_items = aggregate_background.get("items", []) if isinstance(aggregate_background.get("items"), list) else []
        for item in ordered_items[:3]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            inspect_label = f"Inspect {label}"
            append_user_action(
                user_actions,
                action_map,
                label=inspect_label,
                description="Inspect this background process status and log tail.",
                command=workstation_background_command(label, tail_lines=80),
            )
            status_priority_labels.append(inspect_label)
    elif resolved_intent == "research":
        status = "stale_knowledge_pending" if knowledge_review_queue_summary.get("hasPendingReviews") else "knowledge_ready"
        if target_source is not None:
            source_key = str(target_source.get("key") or "").strip() or None
            source_name = humanize_knowledge_source_label(target_source.get("name") or target_source.get("key")) or source_key
            if source_key:
                source_record = build_source_query_result(source_key, catalog=knowledge_catalog)
            if isinstance(source_record, dict):
                source_topic_highlights = source_record.get("topicHighlights", []) if isinstance(source_record.get("topicHighlights"), list) else []
                source_fact_highlights = source_record.get("factHighlights", []) if isinstance(source_record.get("factHighlights"), list) else []
                source_worknet_highlights = source_record.get("worknetHighlights", []) if isinstance(source_record.get("worknetHighlights"), list) else []
                source_evidence_highlights = source_record.get("evidenceHighlights", []) if isinstance(source_record.get("evidenceHighlights"), list) else []
            source_display = (
                source_record.get("sourceDisplay", {})
                if isinstance(source_record, dict) and isinstance(source_record.get("sourceDisplay"), dict)
                else {}
            )
            if isinstance(source_display, dict):
                source_name = str(source_display.get("nameDisplay") or source_name or source_key).strip() or source_name
            headline = str(source_record.get("headline") or (f"Source: {source_name}" if source_name else "Source research"))
            answer = str(
                (
                    source_display.get("summaryPreview")
                    if isinstance(source_display, dict)
                    else None
                )
                or source_record.get("summaryPreview")
                or source_record.get("summary")
                or headline
            )
            drift = (
                source_record.get("drift", {})
                if isinstance(source_record, dict) and isinstance(source_record.get("drift"), dict)
                else {}
            )
            drift_status = str(drift.get("status") or "").strip()
            status = "source_review_needed" if drift_status and drift_status not in {"unchanged", "no-baseline"} else "source_ready"
            worknet_key = None
            worknet_name = None
            merge_payload_user_action_details(user_actions, action_map, source_record, limit=5)
            if isinstance(source_record, dict) and isinstance(source_record.get("researchActionGroups"), list):
                research_action_groups = source_record.get("researchActionGroups", [])
            if isinstance(source_record, dict):
                for index, item in enumerate(source_record.get("userActionDetails", [])):
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get("label") or "").strip()
                    if not label:
                        continue
                    if index == 0:
                        research_current_labels.append(label)
                    elif label in {"Refresh knowledge review queue", "Review pending knowledge updates"}:
                        research_control_labels.append(label)
                    elif label.startswith(("Review source", "Refresh source")):
                        research_topic_labels.append(label)
                    elif label.startswith(("Review WorkNet", "Research WorkNet")) or label.endswith(" WorkNet"):
                        research_worknet_labels.append(label)
        elif target_knowledge_topic:
            topic_knowledge_record = build_knowledge_query_result(
                target_knowledge_topic,
                catalog=knowledge_catalog,
            )
            glossary_record = (
                topic_knowledge_record.get("glossary")
                if isinstance(topic_knowledge_record.get("glossary"), dict)
                else None
            )
            primary_glossary_record = (
                isinstance(glossary_record, dict)
                and safe_slug(str(topic_knowledge_record.get("resolvedTopicKey") or ""))
                == safe_slug(str(glossary_record.get("term") or ""))
            )
            target_worknet_display = (
                topic_knowledge_record.get("worknetDisplay")
                if not primary_glossary_record and isinstance(topic_knowledge_record.get("worknetDisplay"), dict)
                else None
            )
            if isinstance(target_worknet_display, dict):
                worknet_key = str(target_worknet_display.get("key") or "").strip() or None
                worknet_name = str(target_worknet_display.get("name") or target_worknet_display.get("label") or "").strip() or None
            else:
                worknet_key = None
                worknet_name = None
            source_key = None
            source_name = None
            headline = str(
                topic_knowledge_record.get("headline")
                or topic_knowledge_record.get("resolvedTopicLabel")
                or "AWP knowledge"
            )
            answer = str(
                topic_knowledge_record.get("summary")
                or topic_knowledge_record.get("plainLanguage")
                or headline
            )
            status = str(topic_knowledge_record.get("status") or status)
            related_source_highlights = (
                topic_knowledge_record.get("relatedSourceHighlights", [])
                if isinstance(topic_knowledge_record.get("relatedSourceHighlights"), list)
                else []
            )
            merge_payload_user_action_details(user_actions, action_map, topic_knowledge_record, limit=8)
            if isinstance(topic_knowledge_record.get("researchActionGroups"), list):
                research_action_groups = topic_knowledge_record.get("researchActionGroups", [])
            for index, item in enumerate(topic_knowledge_record.get("userActionDetails", [])):
                if not isinstance(item, dict):
                    continue
                label = str(item.get("displayLabel") or item.get("label") or "").strip()
                if not label:
                    continue
                if index == 0 or label.startswith(("Review topic", "Research topic", "Open topic")):
                    research_current_labels.append(label)
                elif label.startswith(("Review source", "Refresh source", "Research source")):
                    research_source_labels.append(label)
                elif label.startswith(("Review reference", "Open reference")):
                    research_reference_labels.append(label)
                elif label.startswith(("Review WorkNet", "Research WorkNet")) or label.endswith(" WorkNet"):
                    research_worknet_labels.append(label)
                else:
                    research_topic_labels.append(label)
        elif target_profile is not None:
            topic_entry = find_topic_directory_entry(
                topic_directory,
                key=str(target_profile.get("key") or ""),
                worknet_key=str(target_profile.get("key") or ""),
            )
            if isinstance(topic_entry, dict):
                label = str(topic_entry.get("label") or target_profile.get("name") or target_profile.get("key") or "WorkNet").strip()
                headline = f"WorkNet: {label}"
                status = "knowledge_review_needed" if str(topic_entry.get("freshnessStatus") or "") == "affected" else "knowledge_ready"
                worknet_key = target_profile.get("key")
                worknet_name = target_profile.get("name")
                topic_key_for_record = str(topic_entry.get("key") or target_profile.get("key") or "").strip()
                if topic_key_for_record:
                    topic_knowledge_record = build_knowledge_query_result(
                        topic_key_for_record,
                        catalog=knowledge_catalog,
                    )
                    if isinstance(topic_knowledge_record.get("worknetDisplay"), dict):
                        target_worknet_display = topic_knowledge_record.get("worknetDisplay")
                    answer = str(
                        topic_knowledge_record.get("summary")
                        or topic_entry.get("summary")
                        or topic_entry.get("headline")
                        or knowledge_overview.get("summary")
                        or headline
                    )
                    status = str(topic_knowledge_record.get("status") or status)
                    merge_payload_user_action_details(user_actions, action_map, topic_knowledge_record, limit=5)
                    if isinstance(topic_knowledge_record.get("researchActionGroups"), list):
                        research_action_groups = topic_knowledge_record.get("researchActionGroups", [])
                    if isinstance(topic_knowledge_record, dict):
                        for index, item in enumerate(topic_knowledge_record.get("userActionDetails", [])):
                            if not isinstance(item, dict):
                                continue
                            label = str(item.get("label") or "").strip()
                            if not label:
                                continue
                            if index == 0 or label.startswith(("Review topic", "Research topic", "Open topic")):
                                research_current_labels.append(label)
                            elif label.startswith(("Review source", "Refresh source", "Research source")):
                                research_source_labels.append(label)
                            else:
                                research_worknet_labels.append(label)
                else:
                    answer = str(topic_entry.get("summary") or topic_entry.get("headline") or knowledge_overview.get("summary") or headline)
                related_source_highlights = knowledge_related_source_highlights(
                    knowledge_catalog,
                    topic_entry,
                    limit=3,
                )
                for item in related_source_highlights[:2]:
                    if not isinstance(item, dict):
                        continue
                    source_label = str(item.get("label") or item.get("key") or "").strip()
                    append_user_action(
                        user_actions,
                        action_map,
                        label=f"Review source {source_label}",
                        description=knowledge_source_action_description(item),
                        command=item.get("queryCommand"),
                    )
                    research_source_labels.append(f"Review source {source_label}")
            else:
                headline = str(knowledge_overview.get("headline") or "AWP knowledge")
                answer = str(knowledge_overview.get("summary") or "No knowledge overview summary is available.")
        else:
            headline = str(knowledge_overview.get("headline") or "AWP knowledge")
            answer = str(knowledge_overview.get("summary") or "No knowledge overview summary is available.")
            worknet_key = None
            worknet_name = None
            if knowledge_review_queue_summary.get("hasPendingReviews"):
                append_user_action(
                    user_actions,
                    action_map,
                    label=knowledge_review_queue_summary.get("refreshActionLabel"),
                    description="Refresh the knowledge review queue from current source drift state.",
                    command=knowledge_review_queue_summary.get("refreshActionCommand"),
                )
                refresh_label = str(knowledge_review_queue_summary.get("refreshActionLabel") or "").strip()
                if refresh_label:
                    research_control_labels.append(refresh_label)
            for item in knowledge_focus_topics[:5]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or item.get("key") or "").strip()
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"Review topic {label}",
                    description=knowledge_action_description(item),
                    command=item.get("queryCommand"),
                )
                research_topic_labels.append(f"Review topic {label}")
            for item in knowledge_source_highlights[:3]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or item.get("key") or "").strip()
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"Review source {label}",
                    description=knowledge_source_action_description(item),
                    command=item.get("queryCommand"),
                )
                research_source_labels.append(f"Review source {label}")
            for item in knowledge_reference_highlights[:2]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or item.get("key") or "").strip()
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"Review reference {label}",
                    description="Open the related reference highlight for source-backed context.",
                    command=item.get("queryCommand"),
                )
                research_reference_labels.append(f"Review reference {label}")
            append_user_action(
                user_actions,
                action_map,
                label="Review WorkNet options",
                description="Scan WorkNet options and capability reports.",
                command=scan_worknets_command(),
            )
            research_worknet_labels.append("Review WorkNet options")

    if knowledge_review_queue_summary.get("hasPendingReviews"):
        append_user_action(
            user_actions,
            action_map,
            label=knowledge_review_queue_summary.get("primaryActionLabel"),
            description="Review pending knowledge updates before trusting generated guidance.",
            command=knowledge_review_queue_summary.get("primaryActionCommand"),
        )
        queue_label = str(knowledge_review_queue_summary.get("primaryActionLabel") or "").strip()
        if queue_label:
            if resolved_intent == "research" and target_source is None and target_profile is None and not target_knowledge_topic:
                if queue_label not in research_control_labels:
                    research_control_labels.insert(0, queue_label)
            elif resolved_intent in {"research", "review-queue"} and queue_label not in research_control_labels and queue_label not in research_current_labels:
                research_control_labels.append(queue_label)

    resume_status = str(
        (recovery_decision.get("status") if isinstance(recovery_decision, dict) else None)
        or start_response.get("resumeStatus")
        or ""
    ).strip() or None
    runtime_execution_state = derive_execution_state(
        review=review,
        recovery=preflight.get("recovery"),
        next_action=preflight.get("nextAction"),
    )
    report_resume_status = resume_status
    report_execution_state = runtime_execution_state
    if resolved_intent == "research":
        report_resume_status = None
        if isinstance(source_record, dict):
            report_execution_state = {
                "executionState": source_record.get("executionState"),
                "executionStateDisplay": source_record.get("executionStateDisplay"),
                "executionHeadline": source_record.get("executionHeadline"),
            }
        elif isinstance(topic_knowledge_record, dict):
            report_execution_state = {
                "executionState": topic_knowledge_record.get("executionState"),
                "executionStateDisplay": topic_knowledge_record.get("executionStateDisplay"),
                "executionHeadline": topic_knowledge_record.get("executionHeadline"),
            }
        else:
            report_execution_state = execution_state_payload(status, headline=headline)
    elif resolved_intent == "review-queue":
        report_resume_status = None
        report_execution_state = execution_state_payload(status, headline=headline)
    action_priority_state = report_execution_state.get("executionState") or runtime_execution_state.get("executionState")
    action_priority_resume = report_resume_status
    if resolved_intent in {"switch-worknet", "pause"}:
        action_priority_state = status
        action_priority_resume = None
    if resolved_intent in {"status", "continue", "earnings", "failures", "research", "switch-worknet", "pause", "review-queue"}:
        user_actions = prioritize_ui_actions(
            user_actions,
            action_map,
            execution_state=action_priority_state,
            resume_status=action_priority_resume,
            worknet_key=worknet_key or current_worknet_key,
        )
    if resolved_intent in {"status", "continue"} and status_priority_labels:
        user_actions = frontload_user_action_labels(user_actions, status_priority_labels)
    if resolved_intent == "pause" and pause_priority_labels:
        user_actions = frontload_user_action_labels(user_actions, pause_priority_labels)
    if resolved_intent == "research":
        if target_source is None and target_profile is None and not target_knowledge_topic:
            ordered_research_labels = [
                *research_current_labels,
                *research_control_labels,
                *research_source_labels,
                *research_topic_labels,
                *research_worknet_labels,
                *research_reference_labels,
            ]
        else:
            ordered_research_labels = [
                *research_current_labels,
                *research_source_labels,
                *research_topic_labels,
                *research_worknet_labels,
                *research_control_labels,
                *research_reference_labels,
            ]
        user_actions = frontload_user_action_labels(user_actions, ordered_research_labels)
    elif resolved_intent == "review-queue":
        ordered_review_queue_labels = [
            *research_current_labels,
            *research_source_labels,
            *research_topic_labels,
            *research_worknet_labels,
            *research_control_labels,
        ]
        user_actions = frontload_user_action_labels(user_actions, ordered_review_queue_labels)
    if resolved_intent in {"status", "continue"}:
        status_maturity_note = worknet_runtime_maturity_note(worknet_key=worknet_key or current_worknet_key)
        answer = align_run_execution_user_message(
            answer,
            execution_state=runtime_execution_state.get("executionState"),
            execution_headline=runtime_execution_state.get("executionHeadline"),
            primary_action=user_actions[0]["label"] if user_actions else None,
            worknet_context_key=worknet_key or current_worknet_key,
            include_canonical_plain=False,
            extra_parts=[status_maturity_note] if status_maturity_note else None,
        ) or answer
    if resolved_intent == "research" and target_source is None and target_profile is None and not target_knowledge_topic:
        user_actions = annotate_research_action_details(
            user_actions,
            current_labels=[],
            control_labels=[
                knowledge_review_queue_summary.get("primaryActionLabel"),
                knowledge_review_queue_summary.get("refreshActionLabel"),
            ],
            source_labels=[
                f"Review source {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_source_highlights[:3]
                if isinstance(item, dict)
            ],
            topic_labels=[
                f"Review topic {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_focus_topics[:5]
                if isinstance(item, dict)
            ],
            worknet_labels=["Review WorkNet options"],
            reference_labels=[
                f"Review reference {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_reference_highlights[:2]
                if isinstance(item, dict)
            ],
            control_tier="overview",
            source_tier="overview",
            topic_tier="overview",
            worknet_tier="overview",
            reference_tier="overview",
        )
    elif resolved_intent == "research":
        user_actions = annotate_research_action_details(
            user_actions,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            current_tier="current",
            control_tier="queued",
            source_tier="related",
            topic_tier="related",
            worknet_tier="related",
            reference_tier="related",
        )
    elif resolved_intent == "review-queue":
        user_actions = annotate_research_action_details(
            user_actions,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="queued",
            worknet_tier="queued",
        )
    else:
        user_actions = annotate_execution_actions(user_actions)
    public_user_actions = humanize_public_action_entries(user_actions)
    public_preflight = dict(preflight)
    public_preflight["recoveryDecision"] = humanize_public_recovery_decision(preflight.get("recoveryDecision"))
    report = {
        "generatedAt": now_iso(),
        "query": query,
        "intent": resolved_intent,
        "progress": "[5/5] Workstation Status",
        "headline": headline,
        "answer": answer,
        "status": status,
        "error": None,
        "missingCaches": [],
        "resumeStatus": report_resume_status,
        "resumeStatusDisplay": recovery_status_display(report_resume_status) if report_resume_status else None,
        "executionState": report_execution_state.get("executionState"),
        "executionStateDisplay": report_execution_state.get("executionStateDisplay"),
        "executionHeadline": report_execution_state.get("executionHeadline"),
        "worknetKey": worknet_key,
        "worknetName": worknet_name,
        "sourceKey": source_key,
        "sourceName": source_name,
        "readOnly": bool(read_only),
        "knowledgeCaveat": knowledge_caveat,
        "recoveryDecision": humanize_public_recovery_decision(recovery_decision),
        "knowledgeReviewQueueSummary": knowledge_review_queue_summary,
        "knowledgeOverview": knowledge_overview,
        "knowledgeFocusTopics": knowledge_focus_topics,
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "sourceTopicHighlights": source_topic_highlights,
        "sourceFactHighlights": source_fact_highlights,
        "sourceWorknetHighlights": source_worknet_highlights,
        "sourceEvidenceHighlights": source_evidence_highlights,
        "knowledgeRecord": topic_knowledge_record,
        "sourceRecord": source_record,
        "targetWorknetDisplay": target_worknet_display,
        "primaryUserAction": user_actions[0]["label"] if user_actions else None,
        "primaryUserActionDisplay": None,
        "primaryUserActionCommand": None,
        "userActions": public_user_actions,
        "userActionDetails": [],
        "latestReview": {
            "generatedAt": review.get("generatedAt"),
            "status": review.get("status"),
            "statusDisplay": review.get("statusDisplay"),
            "executionState": review.get("executionState"),
            "executionStateDisplay": review.get("executionStateDisplay"),
            "executionHeadline": review.get("executionHeadline"),
            "headline": review.get("headline"),
            "dailySummary": review.get("dailySummary"),
            "reporterNote": review.get("reporterNote"),
            "estimatedRewards": review.get("estimatedRewards"),
            "failures": review.get("failures"),
            "strategyChanges": review.get("strategyChanges"),
            "primaryUserAction": review.get("primaryUserAction"),
        },
        "_internal": {
            "action_map": action_map,
            "preflight": public_preflight,
            "start_response": start_response,
            "review": review,
            "targetWorknet": target_profile,
            "targetSource": target_source,
            "targetSourceRecord": source_record,
            "targetKnowledgeRecord": topic_knowledge_record,
            "relatedSourceHighlights": related_source_highlights,
            "stateRoot": state["root"],
        },
    }
    user_action_details = action_details_from_ui_actions(user_actions, action_map)
    if resolved_intent == "research" and target_source is None and target_profile is None and not target_knowledge_topic:
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=[],
            control_labels=[
                knowledge_review_queue_summary.get("primaryActionLabel"),
                knowledge_review_queue_summary.get("refreshActionLabel"),
            ],
            source_labels=[
                f"Review source {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_source_highlights[:3]
                if isinstance(item, dict)
            ],
            topic_labels=[
                f"Review topic {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_focus_topics[:5]
                if isinstance(item, dict)
            ],
            worknet_labels=["Review WorkNet options"],
            reference_labels=[
                f"Review reference {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_reference_highlights[:2]
                if isinstance(item, dict)
            ],
            control_tier="overview",
            source_tier="overview",
            topic_tier="overview",
            worknet_tier="overview",
            reference_tier="overview",
        )
    elif resolved_intent == "research":
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            current_tier="current",
            control_tier="queued",
            source_tier="related",
            topic_tier="related",
            worknet_tier="related",
            reference_tier="related",
        )
    elif resolved_intent == "review-queue":
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="queued",
            worknet_tier="queued",
        )
    else:
        user_action_details = annotate_execution_actions(user_action_details)
    if not research_action_groups and resolved_intent == "research" and target_source is None and target_profile is None and not target_knowledge_topic:
        research_action_groups = build_research_action_groups(
            user_action_details,
            current_labels=[],
            control_labels=[
                knowledge_review_queue_summary.get("primaryActionLabel"),
                knowledge_review_queue_summary.get("refreshActionLabel"),
            ],
            source_labels=[
                f"Review source {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_source_highlights[:3]
                if isinstance(item, dict)
            ],
            topic_labels=[
                f"Review topic {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_focus_topics[:5]
                if isinstance(item, dict)
            ],
            worknet_labels=["Review WorkNet options"],
            reference_labels=[
                f"Review reference {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_reference_highlights[:2]
                if isinstance(item, dict)
            ],
            control_first=True,
        )
    elif not research_action_groups and resolved_intent in {"research", "review-queue"}:
        research_action_groups = build_research_action_groups(
            user_action_details,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            control_first=False,
        )
    report["userActionDetails"] = user_action_details
    report["researchActionGroups"] = research_action_groups
    report["primaryUserActionDisplay"] = user_action_details[0]["displayLabel"] if user_action_details else None
    report["primaryUserActionCommand"] = user_action_details[0]["command"] if user_action_details else None
    monitor_context = dict(cached_monitor) if isinstance(cached_monitor, dict) else {}
    if len(active_background_records) == 1:
        supervisor = background_supervisor_view(active_background_records[0])
        if isinstance(supervisor, dict):
            monitor_context.setdefault("activeBackgroundSupervisorState", supervisor.get("state"))
            monitor_context.setdefault("activeBackgroundSupervisorHeadline", supervisor.get("headline"))
    elif isinstance(aggregate_background, dict) and aggregate_background.get("count"):
        monitor_context.setdefault("activeBackgroundSupervisorState", aggregate_background.get("state"))
        monitor_context.setdefault("activeBackgroundSupervisorHeadline", aggregate_background.get("headline"))
        monitor_context.setdefault("latestSuccess", aggregate_background.get("latestSuccess"))
        monitor_context.setdefault("latestFailure", aggregate_background.get("latestFailure"))
    report["stateSummary"] = build_workstation_state_summary(
        latest_run=latest_run if isinstance(latest_run, dict) else {},
        latest_review=review if isinstance(review, dict) else {},
        status_report={
            "headline": headline,
            "status": status,
            "resumeStatus": report_resume_status,
            "executionState": report_execution_state.get("executionState"),
            "executionStateDisplay": report_execution_state.get("executionStateDisplay"),
            "executionHeadline": report_execution_state.get("executionHeadline"),
            "worknetKey": worknet_key,
            "worknetName": worknet_name,
            "primaryUserAction": report.get("primaryUserAction"),
            "primaryUserActionCommand": report.get("primaryUserActionCommand"),
            "userActions": [item.get("label") for item in user_actions if isinstance(item, dict)],
        },
        active_background=active_background_records,
        pending_confirmations=pending_confirmations if isinstance(pending_confirmations, list) else [],
        monitor_report=monitor_context,
    )
    if not read_only:
        atomic_write_json(Path(state["cache"]) / "workstation-status.json", report)
    return report
