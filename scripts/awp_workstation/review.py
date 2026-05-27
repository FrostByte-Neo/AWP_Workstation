"""Review and strategy presentation helpers."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.narratives import canonical_worknet_caution_text, canonical_worknet_loop_text
from awp_workstation.runtime_actions import find_executed_step
from awp_workstation.runtime_payloads import runtime_message, runtime_payload_error_summary, step_result_payload


def background_strategy_change_from_summary(summary: dict[str, Any], *, alive: bool) -> Optional[str]:
    state = str(summary.get("state") or "")
    if state == "selection_required":
        return "Mine is waiting for dataset selection before the worker can continue."
    if state == "auth_required":
        return "Mine needs a refreshed wallet session before the worker can continue."
    if state == "llm_error":
        return "Predict loop paused because the LLM call failed; inspect logs before restarting."
    if not alive:
        return "Background process is no longer alive; restart when the environment is ready."
    if state == "waiting_for_market":
        return "Predict loop is waiting for an eligible market."
    if state == "llm_running":
        return "Predict loop is running model reasoning in the background."
    if state in {"challenge_ready", "iteration_started", "starting"}:
        return "Background loop is active; monitor status before changing strategy."
    return None


def review_background_action_label(label: str, *, restart: bool = False, inspect: bool = False, stop: bool = False) -> str:
    legacy_prefix = " " * 7
    display = label[len(legacy_prefix):] if label.startswith(legacy_prefix) else label
    if restart:
        return f"Restart {display}"
    if inspect:
        return f"Inspect {display}"
    if stop:
        return f"Stop {display}"
    return display


def review_runtime_safety_hint(worknet_key: str) -> Optional[str]:
    caution = canonical_worknet_caution_text(worknet_key)
    if caution:
        return caution
    return None


def humanize_phase_value(value: Optional[str]) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    mapping = {
        "Voting": "Voting",
        "Trading": "Trading",
        "Settlement": "Settlement",
        "Observe": "Observe",
    }
    return mapping.get(text, text)


def humanize_review_step(worknet_key: str, step: dict[str, Any], payload: Any) -> Optional[str]:
    label = str(step.get("label") or "")
    status = str(step.get("status") or "").strip().lower()
    message = runtime_message(payload)
    state = str(payload.get("state") or "") if isinstance(payload, dict) else ""
    if worknet_key == "mine":
        if label == "mine agent status" and status == "ok":
            loop = canonical_worknet_loop_text("mine")
            if loop:
                return f"Mine agent status is ready. {loop}"
            return "Mine agent status is ready."
        if label == "mine control status" and status == "ok":
            loop = canonical_worknet_loop_text("mine")
            if loop:
                return f"Mine control status is healthy; continue discovery, scraping, cleaning, extraction, and submission. {loop}"
            return "Mine control status is healthy; continue discovery, scraping, cleaning, extraction, and submission."
        if label == "start mine worker" and state == "selection_required":
            return "Mine has reached dataset selection; choose a dataset before starting the first collection round."
        if label == "start mine worker" and message:
            return f"Mine collection loop returned next guidance: {message}"
    if worknet_key == "gov":
        if label == "gov public markets" and status == "ok":
            items = payload.get("items") if isinstance(payload, dict) else None
            if isinstance(items, list) and items:
                first = items[0] if isinstance(items[0], dict) else {}
                market_name = str(first.get("name") or "").strip()
                if market_name:
                    return f"Gov read {len(items)} public markets for this period; the first visible market is {market_name}."
                return f"Gov read {len(items)} public markets and the current time window."
            return "Gov read the current public markets and time window."
        if label == "gov phase-aware helper" and (status == "ok" or payload):
            phase = humanize_phase_value(payload.get("phase") if isinstance(payload, dict) else None)
            caution = canonical_worknet_caution_text("gov")
            if isinstance(phase, str) and phase.strip():
                if caution:
                    return f"Gov confirmed the current phase is {phase}; observe public actions for this phase first. {caution}"
                return f"Gov confirmed the current phase is {phase}; observe public actions for this phase first."
            if caution:
                return f"Gov confirmed the public actions available for this period. {caution}"
            return "Gov confirmed the public actions available for this period."
    if worknet_key == "predict":
        if label == "predict wallet safety" and status == "ok":
            data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
            address = str(data.get("address") or "").strip()
            if address:
                return f"Predict wallet is ready: {address}."
            return "Predict wallet is ready."
        lowered = str(message or "").strip().lower()
        if label in {"predict context", "View Predict context", "       Predict context"}:
            if "no candidate market found" in lowered or "no suitable market" in lowered:
                return "Predict has no suitable market right now; wait for the next round and refresh context later."
            if message:
                return f"Predict context updated: {message}"
        if label == "predict status":
            data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
            balance = str(data.get("balance") or "").strip()
            total_predictions = str(data.get("total_predictions") or "").strip()
            timeslot = data.get("timeslot") if isinstance(data.get("timeslot"), dict) else {}
            remaining = str(timeslot.get("submissions_remaining") or "").strip()
            if total_predictions or balance or remaining:
                details: list[str] = []
                if total_predictions:
                    details.append(f"{total_predictions} total predictions")
                if balance:
                    details.append(f"{balance} chips balance")
                if remaining:
                    details.append(f"{remaining} submissions remaining in this timeslot")
                return f"Predict runtime status synced: {', '.join(details)}."
            if message:
                return f"Predict runtime status updated: {message}"
            if status == "ok":
                return "Predict runtime status has been updated."
        if label == "predict stake eligibility":
            if message:
                return f"Predict eligibility check completed: {message}"
            if status == "ok":
                return "Predict eligibility check completed for this round."
    if worknet_key == "ardi":
        if label == "ardi status":
            data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
            balance_eth = data.get("balance_eth")
            coord_reachable = data.get("coord_reachable")
            agent_state = data.get("agent_state") if isinstance(data.get("agent_state"), dict) else {}
            remaining_mint_cap = agent_state.get("remainingMintCap")
            details: list[str] = []
            if balance_eth is not None:
                details.append(f"Base ETH balance {balance_eth:.6f} ETH" if isinstance(balance_eth, (int, float)) else f"Base ETH balance {balance_eth} ETH")
            if coord_reachable is True:
                details.append("coordinator reachable")
            elif coord_reachable is False:
                details.append("coordinator currently unreachable")
            if remaining_mint_cap is not None:
                details.append(f"{remaining_mint_cap} mints remaining")
            if details:
                return f"Ardi status updated: {', '.join(details)}."
            if message:
                return f"Ardi status updated: {message}"
            if status == "ok":
                return "Ardi status has been updated."
        if label == "ardi preflight":
            if message:
                return f"Ardi preflight returned the latest result: {message}"
            if status == "ok":
                return "Ardi preflight completed."
    return None


def humanize_review_failure(worknet_key: str, step: dict[str, Any], payload: Any) -> Optional[str]:
    label = str(step.get("label") or "")
    detail = runtime_payload_error_summary(payload) or runtime_message(payload)
    lowered_detail = str(detail or "").lower()
    if worknet_key == "gov" and label == "gov private state":
        return "This principal does not have AWP Power for the current period, so signed voting and trading cannot continue."
    if worknet_key == "gov" and label in {"gov public markets", "gov phase-aware helper"}:
        if "name or service not known" in lowered_detail:
            return "Gov cannot reach the upstream service right now; check network or DNS."
        if detail:
            return f"Gov could not fetch the latest public data: {detail}"
    if worknet_key == "predict":
        error = payload.get("error") if isinstance(payload, dict) else None
        error_code = str(error.get("code") or "") if isinstance(error, dict) else ""
        suggestion = str(error.get("suggestion") or "").strip() if isinstance(error, dict) else ""
        if label == "predict stake eligibility":
            if error_code == "NOT_STAKED":
                return "Predict cannot submit this round because the 1000 AWP requirement or KYA delegation path is not ready."
            if error_code == "STAKE_FETCH_FAILED":
                return "Predict is blocked on eligibility because the stake result is not stable yet."
            if suggestion:
                return f"Predict eligibility check returned guidance: {suggestion}"
        if label in {"View Predict context", "       Predict context", "predict context"}:
            if detail:
                return f"Predict could not refresh market context: {detail}"
            return "Predict has no suitable market context right now; wait and retry later."
        if label == "predict status" and detail:
            if "check coordinator connectivity" in lowered_detail:
                return "Predict status cannot reach the coordinator; check connectivity before retrying."
            return f"Predict status update failed: {detail}"
        if label == "predict wallet safety" and detail:
            return f"Predict wallet check failed: {detail}"
    if worknet_key == "ardi":
        data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
        suggestion = str(data.get("suggestion") or "").strip() if isinstance(data, dict) else ""
        if label == "ardi status":
            if "all base rpcs failed" in lowered_detail:
                return "Ardi could not reach any Base RPC; configure a working RPC endpoint before continuing."
            if detail:
                return f"Ardi status check failed: {detail}"
        if label == "ardi gas check":
            if suggestion:
                return f"Ardi needs Base gas before execution can continue: {suggestion}"
            return "Ardi needs Base gas before execution can continue."
        if label == "ardi stake guidance":
            if suggestion.startswith("Reach the 10000 AWP threshold on EITHER Ardi"):
                return "Ardi needs the 10000 AWP threshold through either the direct Ardi path or the KYA delegation path."
            if suggestion:
                return f"Ardi qualification guidance: {suggestion}"
            return "Ardi qualification is not ready yet."
        if label == "ardi preflight" and detail:
            return f"Ardi preflight failed: {detail}"
    if worknet_key == "mine" and label == "start mine worker":
        if detail:
            return f"Mine worker start failed: {detail}"
        return "Mine worker did not start."
    return None


def humanize_review_step_label(worknet_key: str, label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return "Review step"
    mapping = {
        "mine agent status": "Mine agent status",
        "mine control status": "Mine control status",
        "start mine worker": "Start Mine worker",
        "predict status": "Predict status",
        "predict stake eligibility": "Predict eligibility",
        "predict context": "Predict context",
        "View Predict context": "Predict context",
        "       Predict context": "Predict context",
        "gov public markets": "Gov public markets",
        "gov phase-aware helper": "Gov phase helper",
        "gov private state": "Gov private state",
        "ardi status": "Ardi status",
        "ardi gas check": "Ardi gas check",
        "ardi stake guidance": "Ardi stake guidance",
        "ardi preflight": "Ardi preflight",
    }
    return mapping.get(text, text)


def humanize_review_status_token(
    worknet_key: str,
    label: str,
    status: Any,
) -> Optional[str]:
    code = str(status or "").strip().lower()
    if not code:
        return None
    if code == "planned":
        if worknet_key == "mine" and label == "start mine worker":
            return "Mine is waiting for dataset selection or worker start."
        if worknet_key == "predict":
            return "Predict is planned and waiting for context or eligibility."
        if worknet_key == "gov":
            return "Gov is planned and waiting for the current phase or confirmation."
        if worknet_key == "ardi":
            return "Ardi is planned and waiting for preflight, gas, or qualification."
        return "Planned."
    if code == "ok":
        return "Completed."
    if code == "failed":
        return "Failed."
    if code == "missing_runtime_command":
        return "Missing runtime command."
    if code == "missing_parameters":
        return "Missing required parameters."
    if code == "queued_for_confirmation":
        return "Queued for confirmation."
    if code == "awaiting_confirmation":
        return "Awaiting confirmation."
    if code == "available_manual":
        return "Available as a manual action."
    if code == "skipped_after_primary_work":
        return "Skipped after primary work completed."
    if code == "blocked_after_previous_step":
        return "Blocked because a previous step did not complete."
    if code == "started_background":
        return "Started in the background."
    if code == "background_running":
        return "Already running in the background."
    return None


def review_line_detail(text: Any) -> str:
    value = str(text or "").strip()
    if not value:
        return value
    for separator in ("   ", ":"):
        if separator not in value:
            continue
        head, tail = value.split(separator, 1)
        if tail.strip() and len(head.strip()) <= 32:
            return tail.strip()
    return value


def review_all_steps_prepared(work_done: list[str]) -> bool:
    if not work_done:
        return False
    ready_markers = ("ready", "completed", "background task started", "running")
    blocker_markers = ("planned", "manual action", "waiting", "needs")
    details = [review_line_detail(item).lower() for item in work_done if str(item).strip()]
    return bool(details) and all(
        any(marker in detail for marker in ready_markers)
        and not any(marker in detail for marker in blocker_markers)
        for detail in details
    )


def build_review_headline(
    worknet_key: str,
    work_done: list[str],
    failures: list[str],
    strategy_changes: list[str],
) -> Optional[str]:
    if worknet_key == "mine":
        if any(
            token in str(item)
            for item in work_done + strategy_changes
            for token in ("dataset", "selection_required", "awaiting_dataset")
        ):
            return "Mine is waiting for dataset selection."
        if review_all_steps_prepared(work_done):
            return "Mine is ready to start."
        if work_done:
            return "Mine made progress."
    if worknet_key == "gov":
        if failures and any("awp power" in item.lower() for item in failures):
            return "Gov needs AWP Power before signed actions."
        if review_all_steps_prepared(work_done):
            return "Gov checks are ready."
        if work_done:
            return "Gov made progress."
    if worknet_key == "predict":
        if failures and any(
            token in item.lower()
            for item in failures
            for token in ("1000 awp", "stake", "eligibility")
        ):
            return "Predict needs stake or eligibility review."
        if review_all_steps_prepared(work_done):
            return "Predict checks are ready."
        if strategy_changes and any("restart" in item.lower() for item in strategy_changes):
            return "Predict loop may need restart."
        if work_done:
            return "Predict loop made progress."
    if worknet_key == "ardi":
        if failures and any(
            token in item.lower()
            for item in failures
            for token in ("gas", "stake", "commit/reveal")
        ):
            return "Ardi needs gas or stake review."
        if review_all_steps_prepared(work_done):
            return "Ardi checks are ready."
        if work_done:
            return "Ardi made progress."
    if failures:
        return review_line_detail(failures[0])
    if work_done:
        return review_line_detail(work_done[0])
    return None


def review_status_code(
    worknet_key: str,
    work_done: list[str],
    failures: list[str],
    strategy_changes: list[str],
) -> str:
    if worknet_key == "mine" and any("dataset" in item.lower() for item in work_done + strategy_changes):
        return "awaiting_dataset"
    if worknet_key == "gov" and any("awp power" in item.lower() for item in failures + strategy_changes):
        return "observe_only"
    if worknet_key == "predict" and any("restart" in item.lower() for item in strategy_changes):
        return "restart_available"
    if failures and work_done:
        return "partial"
    if failures:
        return "blocked"
    if review_all_steps_prepared(work_done):
        return "ready"
    if work_done:
        return "progressed"
    return "idle"


def summarize_worknet_review(
    worknet_key: str,
    latest_run: dict[str, Any],
) -> dict[str, list[str]]:
    executed_steps = latest_run.get("executedSteps", []) if isinstance(latest_run, dict) else []
    if not isinstance(executed_steps, list):
        return {}
    if worknet_key == "mine":
        start_step = find_executed_step(executed_steps, "start mine worker")
        start_payload = step_result_payload(start_step)
        if isinstance(start_payload, dict) and str(start_payload.get("state") or "") == "selection_required":
            return {
                "workDone": [
                    "Mine runtime is waiting for a dataset selection."
                ],
                "strategyChanges": [
                    "Select a Mine dataset before starting the worker."
                ],
            }
    if worknet_key == "gov":
        helper_step = find_executed_step(executed_steps, "gov phase-aware helper")
        helper_payload = step_result_payload(helper_step)
        phase = None
        if isinstance(helper_payload, dict):
            raw_phase = helper_payload.get("phase")
            if isinstance(raw_phase, str) and raw_phase.strip():
                phase = humanize_phase_value(raw_phase.strip())
        state_step = find_executed_step(executed_steps, "gov private state")
        state_payload = step_result_payload(state_step)
        no_power = (
            isinstance(state_payload, dict)
            and str(state_payload.get("error") or "") == "STATE_PRINCIPAL_NOT_IN_EPOCH"
        )
        if phase and no_power:
            return {
                "workDone": [
                    f"Gov helper reported phase {phase}."
                ],
                "failures": [
                    "The principal has no AWP Power in the current Gov epoch."
                ],
                "strategyChanges": [
                    "Do not submit Gov actions until AWP Power is available.",
                    "Route any signed or stake-backed action through the confirmation queue.",
                ],
            }
        if phase:
            return {
                "workDone": [
                    f"Gov helper reported phase {phase}."
                ],
                "strategyChanges": [
                    "Continue with phase-aware Gov actions only when helper output allows them.",
                ],
            }
    return {}


def strategy_changes_from_guidance(guidance: Any, *, worknet_key: str = "") -> list[str]:
    if not isinstance(guidance, dict):
        return []
    next_action = str(guidance.get("nextAction") or "")
    mapping = {
        "stake_required": "Confirm stake or KYA eligibility before stake-backed execution.",
        "retry_stake_check": "Retry the stake eligibility check before continuing.",
        "acquire_awp_power_or_observe_gov": "Acquire AWP Power or keep Gov in observe mode.",
        "fund_gas_and_or_satisfy_stake": "Fund Base gas and satisfy Ardi stake requirements.",
        "fetch_context": "Refresh Predict market context before selecting an action.",
        "confirm_predict_submission": "Confirm Predict tickets and reasoning before submission.",
        "wait_for_predict_market": "Wait for an eligible Predict market before submitting.",
        "monitor_background_run": "Monitor the background run before changing strategy.",
    }
    message = mapping.get(next_action)
    changes: list[str] = [message] if message else []
    if worknet_key == "predict":
        if next_action == "confirm_predict_submission":
            changes.append("Keep the confirmation gate enabled for the Predict submission.")
        elif next_action == "wait_for_predict_market":
            changes.append("Do not submit until context exposes an actionable market.")
        elif next_action in {"stake_required", "retry_stake_check"}:
            changes.append("Predict can still run lower-risk context checks while stake eligibility is unresolved.")
    elif worknet_key == "gov":
        if next_action == "acquire_awp_power_or_observe_gov":
            changes.append("Gov should stay read-only until AWP Power is available.")
    elif worknet_key == "ardi":
        if next_action == "fund_gas_and_or_satisfy_stake":
            changes.append("Ardi commits should stay blocked until gas and stake checks pass.")
    caution = review_runtime_safety_hint(worknet_key)
    if caution and next_action in {"confirm_predict_submission", "acquire_awp_power_or_observe_gov", "fund_gas_and_or_satisfy_stake"}:
        changes.append(caution)
    return [item for item in changes if isinstance(item, str) and item.strip()]


def build_epoch_review_from_run_payload(
    latest_run: Any,
    pending_queue: Any,
    *,
    state: Optional[dict[str, Any]] = None,
    knowledge_catalog: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("epoch review dependencies are required")
    annotate_execution_actions = dependencies["annotate_execution_actions"]
    append_unique_action_detail = dependencies["append_unique_action_detail"]
    append_unique_text = dependencies["append_unique_text"]
    background_observations_from_run = dependencies["background_observations_from_run"]
    background_strategy_change_from_summary = dependencies["background_strategy_change_from_summary"]
    build_daily_summary = dependencies["build_daily_summary"]
    build_reporter_note = dependencies["build_reporter_note"]
    build_review_headline = dependencies["build_review_headline"]
    compact_knowledge_context = dependencies["compact_knowledge_context"]
    humanize_review_action_description = dependencies["humanize_review_action_description"]
    humanize_review_action_label = dependencies["humanize_review_action_label"]
    humanize_review_confirmation_label = dependencies["humanize_review_confirmation_label"]
    humanize_review_failure = dependencies["humanize_review_failure"]
    humanize_review_status_token = dependencies["humanize_review_status_token"]
    humanize_review_step = dependencies["humanize_review_step"]
    humanize_review_step_label = dependencies["humanize_review_step_label"]
    knowledge_action_description = dependencies["knowledge_action_description"]
    knowledge_context_for_worknet = dependencies["knowledge_context_for_worknet"]
    knowledge_refresh_action_description = dependencies["knowledge_refresh_action_description"]
    knowledge_related_reference_highlights = dependencies["knowledge_related_reference_highlights"]
    knowledge_related_source_highlights = dependencies["knowledge_related_source_highlights"]
    knowledge_source_action_description = dependencies["knowledge_source_action_description"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    now_iso = dependencies["now_iso"]
    prioritize_review_actions = dependencies["prioritize_review_actions"]
    public_earnings_hint_for_worknet = dependencies["public_earnings_hint_for_worknet"]
    review_action_command = dependencies["review_action_command"]
    review_all_steps_prepared = dependencies["review_all_steps_prepared"]
    review_background_action_label = dependencies["review_background_action_label"]
    review_runtime_safety_hint = dependencies["review_runtime_safety_hint"]
    review_status_code = dependencies["review_status_code"]
    review_status_display = dependencies["review_status_display"]
    reward_hints_from_run = dependencies["reward_hints_from_run"]
    run_worknet_command = dependencies["run_worknet_command"]
    runtime_message = dependencies["runtime_message"]
    runtime_payload_error_summary = dependencies["runtime_payload_error_summary"]
    runtime_payload_has_blocker = dependencies["runtime_payload_has_blocker"]
    state_context = dependencies["state_context"]
    step_result_payload = dependencies["step_result_payload"]
    strategy_changes_from_guidance = dependencies["strategy_changes_from_guidance"]
    summarize_worknet_review = dependencies["summarize_worknet_review"]
    workstation_background_command = dependencies["workstation_background_command"]
    workstation_confirmation_command = dependencies["workstation_confirmation_command"]
    workstation_follow_up_command = dependencies["workstation_follow_up_command"]
    workstation_pause_command = dependencies["workstation_pause_command"]

    state = state or state_context()
    knowledge_catalog = knowledge_catalog or load_or_build_knowledge_catalog(state)
    playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
    worknet_key = str(playbook.get("worknetKey") or "")
    knowledge_context = knowledge_context_for_worknet(knowledge_catalog, worknet_key)
    knowledge_reference_highlights = knowledge_related_reference_highlights(
        knowledge_catalog,
        knowledge_context,
    )
    knowledge_source_highlights = knowledge_related_source_highlights(
        knowledge_catalog,
        knowledge_context,
    )
    background_observations = background_observations_from_run(latest_run, state=state)
    background_by_label = {
        str(item.get("label")): item
        for item in background_observations
        if isinstance(item, dict) and item.get("label")
    }
    work_done: list[str] = []
    failures: list[str] = []
    strategy_changes: list[str] = []
    user_actions: list[str] = []
    user_action_details: list[dict[str, Any]] = []
    estimated_rewards: list[str] = []
    processed_background_labels: set[str] = set()
    for step in latest_run.get("executedSteps", []):
        label = step.get("label") or "unnamed step"
        display_label = humanize_review_step_label(worknet_key, str(label))
        status = step.get("status")
        payload = step_result_payload(step) if isinstance(step, dict) else None
        message = runtime_message(payload)
        if status in {"planned", "ok"} and runtime_payload_has_blocker(payload):
            detail = humanize_review_failure(worknet_key, step, payload) or runtime_payload_error_summary(payload) or message or status
            failures.append(f"{display_label}: {detail}")
        elif status in {"planned", "ok"}:
            detail = (
                humanize_review_step(worknet_key, step, payload)
                or message
                or humanize_review_status_token(worknet_key, str(label), status)
                or str(status)
            )
            work_done.append(f"{display_label}: {detail}")
        elif status == "started_background":
            observation = background_by_label.get(str(label), {})
            processed_background_labels.add(str(label))
            summary = observation.get("summary", {}) if isinstance(observation, dict) else {}
            headline = summary.get("headline") if isinstance(summary, dict) else None
            log_path = observation.get("logPath") if isinstance(observation, dict) else None
            detail = "Background task started"
            if isinstance(headline, str) and headline.strip():
                qualifier = "running" if observation.get("alive") else "stopped"
                detail += f"; {qualifier}: {headline.strip()}"
            if log_path:
                detail += f" (log: {log_path})"
            work_done.append(f"{display_label}: {detail}")
            summary_state = str(summary.get("state") or "") if isinstance(summary, dict) else ""
            summary_detail = summary.get("detail") if isinstance(summary, dict) else None
            if summary_state == "llm_error":
                failures.append(f"{display_label}: {summary_detail or headline or 'Background LLM call failed.'}")
        elif status in {"available_manual", "skipped_after_primary_work", "blocked_after_previous_step"}:
            continue
        elif status in {"queued_for_confirmation", "missing_runtime_command", "failed", "missing_parameters"}:
            detail = (
                humanize_review_failure(worknet_key, step, payload)
                or message
                or step.get("reason")
                or step.get("result", {}).get("stderr")
                or humanize_review_status_token(worknet_key, str(label), status)
                or str(status)
            )
            if status == "missing_parameters" and isinstance(step.get("parameterErrors"), list):
                detail = "; ".join(str(item) for item in step.get("parameterErrors", []))
            failures.append(f"{display_label}: {detail}")
    confirmation_items = (
        pending_queue
        if isinstance(pending_queue, list) and pending_queue
        else latest_run.get("confirmationQueue", [])
    )
    has_confirmation_actions = bool(confirmation_items)
    for queued in confirmation_items:
        label = str(queued.get("label") or "").strip()
        if label:
            display = humanize_review_confirmation_label(worknet_key, label)
            append_unique_text(user_actions, display)
            append_unique_action_detail(
                user_action_details,
                label=display,
                description=humanize_review_action_description(
                    worknet_key,
                    label,
                    requires_confirmation=True,
                ),
                command=workstation_confirmation_command(label, execute=False),
            )
    runtime_guidance = latest_run.get("runtimeGuidance", {})
    follow_up_actions = latest_run.get("followUpActions", [])
    if isinstance(follow_up_actions, list) and follow_up_actions:
        for item in follow_up_actions:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            command = item.get("command")
            if label:
                display = humanize_review_action_label(worknet_key, str(label))
                append_unique_text(user_actions, display)
                append_unique_action_detail(
                    user_action_details,
                    label=display,
                    description=humanize_review_action_description(worknet_key, str(label)),
                    command=review_action_command(
                        worknet_key,
                        str(label),
                        command=str(command) if isinstance(command, str) else None,
                        safe_to_auto_run=bool(item.get("safeToAutoRun")),
                        requires_confirmation=bool(item.get("requiresConfirmation")),
                    ),
                )
    elif isinstance(runtime_guidance, dict):
        for label in runtime_guidance.get("userActions", []):
            command = runtime_guidance.get("actionMap", {}).get(label)
            display = humanize_review_action_label(worknet_key, str(label))
            append_unique_text(user_actions, display)
            append_unique_action_detail(
                user_action_details,
                label=display,
                description=humanize_review_action_description(worknet_key, str(label)),
                command=command if isinstance(command, str) else None,
            )
    summary_override = summarize_worknet_review(worknet_key, latest_run)
    if isinstance(summary_override.get("workDone"), list) and summary_override.get("workDone"):
        work_done = [str(item) for item in summary_override["workDone"] if str(item).strip()]
    if isinstance(summary_override.get("failures"), list) and summary_override.get("failures"):
        failures = [str(item) for item in summary_override["failures"] if str(item).strip()]
    if isinstance(summary_override.get("strategyChanges"), list):
        for item in summary_override.get("strategyChanges", []):
            append_unique_text(strategy_changes, str(item) if str(item).strip() else None)
    if isinstance(summary_override.get("userActions"), list):
        for item in summary_override.get("userActions", []):
            append_unique_text(user_actions, str(item) if str(item).strip() else None)
    estimated_rewards.extend(reward_hints_from_run(latest_run))
    append_unique_text(estimated_rewards, public_earnings_hint_for_worknet(state, worknet_key))
    active_background_count = sum(1 for item in background_observations if item.get("alive"))
    if active_background_count == 1:
        append_unique_text(user_actions, "Pause active background task")
        append_unique_action_detail(
            user_action_details,
            label="Pause active background task",
            description="Stop the currently running background task.",
            command=workstation_pause_command(execute=True),
        )
    restart_source = latest_run.get("sourceFollowUpAction", {}) if isinstance(latest_run, dict) else {}
    restart_label = str(restart_source.get("label") or "")
    for observation in background_observations:
        if not isinstance(observation, dict):
            continue
        label = str(observation.get("label") or "")
        if not label:
            continue
        summary = observation.get("summary", {})
        headline = summary.get("headline") if isinstance(summary, dict) else None
        if label not in processed_background_labels:
            detail = headline.strip() if isinstance(headline, str) and headline.strip() else "No background log summary is available yet."
            log_path = observation.get("logPath")
            if log_path:
                detail += f" (log: {log_path})"
            work_done.append(f"{label}: {detail}")
        append_unique_text(
            strategy_changes,
            background_strategy_change_from_summary(
                summary if isinstance(summary, dict) else {},
                alive=bool(observation.get("alive")),
            ),
        )
        if observation.get("alive"):
            inspect_label = review_background_action_label(label, inspect=True)
            stop_label = review_background_action_label(label, stop=True)
            append_unique_text(user_actions, inspect_label)
            append_unique_text(user_actions, stop_label)
            append_unique_action_detail(
                user_action_details,
                label=inspect_label,
                description="Inspect the latest background task log.",
                command=workstation_background_command(label, tail_lines=80),
            )
            append_unique_action_detail(
                user_action_details,
                label=stop_label,
                description="Stop this background task.",
                command=workstation_background_command(label, stop=True, execute=False),
            )
        elif restart_label and restart_label == label:
            restart_display = review_background_action_label(label, restart=True)
            append_unique_text(user_actions, restart_display)
            append_unique_action_detail(
                user_action_details,
                label=restart_display,
                description="Restart this background task.",
                command=workstation_follow_up_command(label, execute=True),
            )
    if not estimated_rewards:
        estimated_rewards.append("No reward estimate is available yet.")
    if failures:
        append_unique_text(strategy_changes, "Review failures before continuing automation.")
        append_unique_text(strategy_changes, review_runtime_safety_hint(worknet_key))
    if has_confirmation_actions:
        append_unique_text(strategy_changes, "Pending confirmations require manual review before execution.")
        append_unique_text(strategy_changes, review_runtime_safety_hint(worknet_key))
    ready_scene = (
        bool(worknet_key)
        and review_all_steps_prepared(work_done)
        and not failures
        and not has_confirmation_actions
        and not user_actions
    )
    if ready_scene:
        worknet_name = str(playbook.get("requiredSkill") or worknet_key or "WorkNet").strip()
        continue_label = f"Start {worknet_name}"
        append_unique_text(user_actions, continue_label)
        append_unique_action_detail(
            user_action_details,
            label=continue_label,
            description="Start the selected WorkNet route.",
            command=run_worknet_command(worknet_key, execute=True, auto_advance=True),
        )
    if isinstance(knowledge_context, dict) and str(knowledge_context.get("freshnessStatus") or "") == "affected":
        label = str(knowledge_context.get("label") or worknet_key or "WorkNet").strip()
        append_unique_text(strategy_changes, f"{label} has upstream source changes; review knowledge context before continuing.")
        append_unique_text(user_actions, f"Review {label} context")
        append_unique_action_detail(
            user_action_details,
            label=f"Review {label} context",
            description=knowledge_action_description(knowledge_context),
            command=knowledge_context.get("queryCommand"),
        )
        primary_command = str(knowledge_context.get("primaryCommand") or "").strip()
        query_command = str(knowledge_context.get("queryCommand") or "").strip()
        if primary_command and primary_command != query_command:
            append_unique_text(user_actions, f"Refresh {label} context")
            append_unique_action_detail(
                user_action_details,
                label=f"Refresh {label} context",
                description=knowledge_refresh_action_description(knowledge_context),
                command=primary_command,
            )
    for item in knowledge_source_highlights[:3]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        append_unique_text(user_actions, f"Review source {label}")
        append_unique_action_detail(
            user_action_details,
            label=f"Review source {label}",
            description=knowledge_source_action_description(item),
            command=item.get("queryCommand"),
        )
        primary_command = str(item.get("primaryCommand") or "").strip()
        query_command = str(item.get("queryCommand") or "").strip()
        if primary_command and primary_command != query_command:
            append_unique_text(user_actions, f"Refresh source {label}")
            append_unique_action_detail(
                user_action_details,
                label=f"Refresh source {label}",
                description=f"Refresh {label} before continuing automation.",
                command=primary_command,
            )
    for item in strategy_changes_from_guidance(runtime_guidance, worknet_key=worknet_key):
        if (
            item == "Background loop is active; monitor status before changing strategy."
            and active_background_count == 0
        ):
            continue
        append_unique_text(strategy_changes, item)
    if isinstance(runtime_guidance, dict) and runtime_guidance.get("state") == "selection_required":
        append_unique_text(strategy_changes, "Mine needs dataset selection before continuing.")
    status = review_status_code(worknet_key, work_done, failures, strategy_changes)
    user_actions, user_action_details = prioritize_review_actions(
        worknet_key,
        status,
        user_actions,
        user_action_details,
    )
    user_action_details = annotate_execution_actions(user_action_details)
    headline = build_review_headline(worknet_key, work_done, failures, strategy_changes)
    reporter_note = build_reporter_note(
        knowledge_context,
        knowledge_reference_highlights,
        knowledge_source_highlights,
    )
    daily_summary = build_daily_summary(
        worknet_key,
        headline,
        estimated_rewards,
        user_actions,
        reporter_note=reporter_note,
    )
    review = {
        "generatedAt": now_iso(),
        "worknetKey": worknet_key or None,
        "worknetName": playbook.get("requiredSkill") if isinstance(playbook, dict) else None,
        "status": status,
        "statusDisplay": review_status_display(status),
        "resumeStatus": None,
        "resumeStatusDisplay": None,
        "executionState": status,
        "executionStateDisplay": review_status_display(status),
        "executionHeadline": headline,
        "headline": headline,
        "dailySummary": daily_summary,
        "reporterNote": reporter_note,
        "knowledgeContext": compact_knowledge_context(knowledge_context),
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "primaryUserAction": user_actions[0] if user_actions else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "workDone": work_done,
        "estimatedRewards": estimated_rewards,
        "failures": failures,
        "strategyChanges": strategy_changes,
        "userActions": user_actions,
        "userActionDetails": user_action_details,
        "progress": "[5/5] Review",
        "stateRoot": state["root"],
    }
    return review
