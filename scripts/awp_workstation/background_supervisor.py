"""Shared supervisor-state helpers for background tasks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional


WAITING_BACKGROUND_STATES = {
    "waiting_for_market",
    "waiting_for_timeslot_reset",
    "waiting_for_chip_feed",
    "waiting_for_service",
    "rate_limited",
    "llm_running",
    "challenge_ready",
    "iteration_started",
    "starting",
    "selection_required",
}

SUPERVISOR_STATUS_PRIORITY = {
    "background_failed": 0,
    "background_stopped": 1,
    "background_stalled": 2,
    "auth_required": 3,
    "registration_required": 4,
    "stake_required": 5,
    "awaiting_dataset": 6,
    "background_waiting": 7,
    "background_running": 8,
    "ready_to_start": 9,
    "background_completed": 10,
}


def _hours_since(timestamp: Any, *, parse_iso_datetime: Any) -> Optional[float]:
    parsed = parse_iso_datetime(timestamp)
    if parsed is None:
        return None
    return max(0.0, (datetime.now(parsed.tzinfo) - parsed).total_seconds() / 3600.0)


def _background_progress_hours(record: dict[str, Any], *, parse_iso_datetime: Any) -> Optional[float]:
    log_path = Path(str(record.get("logPath") or "").strip()) if str(record.get("logPath") or "").strip() else None
    if log_path and log_path.exists():
        modified = datetime.fromtimestamp(log_path.stat().st_mtime).astimezone()
        return max(0.0, (datetime.now(modified.tzinfo) - modified).total_seconds() / 3600.0)
    return _hours_since(record.get("startedAt"), parse_iso_datetime=parse_iso_datetime)


def _payload_action_bundle(payload: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(payload, dict):
        return None, None
    internal = _payload_internal(payload)
    labels = payload.get("user_actions")
    action_map = internal.get("action_map") if isinstance(internal.get("action_map"), dict) else None
    if isinstance(labels, list):
        for item in labels:
            label = str(item or "").strip()
            if not label:
                continue
            command = str(action_map.get(label) or "").strip() if isinstance(action_map, dict) else ""
            return label, command or None
    next_command = str(internal.get("next_command") or "").strip()
    next_action = str(internal.get("next_action") or "").strip()
    if next_command:
        return _humanize_next_action(next_action or next_command), next_command
    return None, None


def _payload_internal(payload: Any) -> dict[str, Any]:
    internal = payload.get("_internal") if isinstance(payload, dict) else None
    return internal if isinstance(internal, dict) else {}


def _payload_data(payload: Any) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else {}


def _payload_error(payload: Any) -> dict[str, Any]:
    error = payload.get("error") if isinstance(payload, dict) else None
    return error if isinstance(error, dict) else {}


def _payload_runtime_status(payload: Any) -> dict[str, Any]:
    internal = _payload_internal(payload)
    status = internal.get("status") if isinstance(internal, dict) else None
    return status if isinstance(status, dict) else {}


def _humanize_next_action(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "Continue"
    mapping = {
        "ready": "Continue",
        "retry": "Retry",
        "stake_required": "Check stake",
        "fetch_context": "Fetch context",
        "compose_reasoning_then_submit": "Compose reasoning and submit",
        "select_persona": "Select persona",
    }
    normalized = text.lower()
    if normalized in mapping:
        return mapping[normalized]
    return text.replace("_", " ").strip().title()


def _first_text(*values: Any) -> Optional[str]:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _text_blob(*values: Any) -> str:
    return " ".join(str(value or "").strip().lower() for value in values if str(value or "").strip())


def _predict_open_orders(data: dict[str, Any]) -> list[dict[str, Any]]:
    orders = data.get("open_orders")
    return [item for item in orders if isinstance(item, dict)] if isinstance(orders, list) else []


def _predict_recent_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    results = data.get("recent_results")
    return [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def _predict_orders_signature(data: dict[str, Any]) -> str:
    orders = _predict_open_orders(data)
    if not orders:
        return ""
    total_tickets = 0
    total_filled = 0
    first_bits = ""
    for order in orders:
        try:
            total_tickets += int(order.get("tickets") or 0)
        except (TypeError, ValueError):
            pass
        try:
            total_filled += int(order.get("tickets_filled") or 0)
        except (TypeError, ValueError):
            pass
    first = orders[0]
    first_bits = ":".join(
        [
            str(first.get("market_id") or "").strip(),
            str(first.get("direction") or "").strip(),
            str(first.get("tickets_filled") or "").strip(),
            str(first.get("tickets") or "").strip(),
            str(first.get("status") or "").strip(),
        ]
    )
    return ":".join([str(len(orders)), str(total_filled), str(total_tickets), first_bits])


def _predict_recent_results_signature(data: dict[str, Any]) -> str:
    results = _predict_recent_results(data)
    if not results:
        return ""
    wins = 0
    payout_total = 0
    for item in results:
        if item.get("won") is True:
            wins += 1
        try:
            payout_total += int(item.get("payout_chips") or 0)
        except (TypeError, ValueError):
            pass
    first = results[0]
    first_bits = ":".join(
        [
            str(first.get("market_id") or "").strip(),
            str(first.get("direction") or "").strip(),
            "won" if first.get("won") is True else "lost",
            str(first.get("payout_chips") or "").strip(),
            str(first.get("tickets_filled") or "").strip(),
        ]
    )
    return ":".join([str(len(results)), str(wins), str(payout_total), first_bits])


def _mine_session_signature(record: dict[str, Any], payload: dict[str, Any]) -> str:
    internal = _payload_internal(payload)
    data = _payload_data(payload)
    runtime_status = _payload_runtime_status(payload)
    progress = runtime_status.get("progress") if isinstance(runtime_status.get("progress"), dict) else {}
    earnings_summary = runtime_status.get("earnings_summary") if isinstance(runtime_status.get("earnings_summary"), dict) else {}
    queues = runtime_status.get("queues") if isinstance(runtime_status.get("queues"), dict) else {}
    handoff = queues.get("agent_handoff") if isinstance(queues.get("agent_handoff"), dict) else {}
    session = internal.get("session") if isinstance(internal.get("session"), dict) else {}
    session_id = _first_text(
        record.get("externalSessionId"),
        session.get("session_id") if isinstance(session, dict) else None,
        data.get("session_id"),
        data.get("sessionId"),
    ) or ""
    datasets = (
        session.get("selected_dataset_ids")
        if isinstance(session, dict) and isinstance(session.get("selected_dataset_ids"), list)
        else data.get("selected_dataset_ids")
    )
    dataset_signature = ",".join(str(item).strip() for item in datasets if str(item).strip()) if isinstance(datasets, list) else ""
    recent_errors = internal.get("recent_errors")
    recent_error = str(recent_errors[-1]).strip() if isinstance(recent_errors, list) and recent_errors else ""
    handoff_total = sum(int(value or 0) for value in handoff.values()) if isinstance(handoff, dict) else 0
    return ":".join(
        [
            session_id,
            str(runtime_status.get("mining_state") or "").strip(),
            str(runtime_status.get("phase") or "").strip(),
            dataset_signature,
            str(earnings_summary.get("submitted") or "").strip(),
            str(earnings_summary.get("target") or "").strip(),
            str(earnings_summary.get("progress_percent") or progress.get("epoch_completion_percent") or "").strip(),
            str(earnings_summary.get("remaining") or progress.get("epoch_remaining") or "").strip(),
            str(progress.get("session_processed_items") or "").strip(),
            str(progress.get("session_submitted_items") or "").strip(),
            str(progress.get("session_failed_items") or "").strip(),
            str(queues.get("backlog") or "").strip(),
            str(queues.get("auth_pending") or "").strip(),
            str(queues.get("submit_pending") or "").strip(),
            str(handoff_total),
            str(runtime_status.get("last_iteration") or "").strip(),
            str(runtime_status.get("last_activity_at") or "").strip(),
            recent_error,
        ]
    )


def background_progress_signal(record: Any) -> Optional[str]:
    if not isinstance(record, dict):
        return None
    summary = record.get("summary", {}) if isinstance(record.get("summary"), dict) else {}
    status_payload = record.get("statusPayload") if isinstance(record.get("statusPayload"), dict) else None
    next_action_label, _ = _payload_action_bundle(status_payload)
    internal = _payload_internal(status_payload)
    data = _payload_data(status_payload)
    error = _payload_error(status_payload)
    worknet_key = str(record.get("worknetKey") or "").strip().lower()
    runtime_status = _payload_runtime_status(status_payload)
    nested_mining_state = str(runtime_status.get("mining_state") or "").strip().lower()
    state = str(summary.get("state") or nested_mining_state or record.get("runtimeState") or "").strip().lower()
    detail = str(summary.get("detail") or summary.get("headline") or "").strip()
    progress = str(internal.get("progress") or "").strip()
    next_action = str(internal.get("next_action") or "").strip()
    error_code = str(error.get("code") or "").strip()
    if worknet_key == "mine":
        return ":".join(
            [
                "mine",
                state,
                next_action_label or next_action,
                progress,
                error_code,
                _mine_session_signature(record, status_payload or {}),
                detail,
            ]
        )
    if worknet_key == "predict":
        persona_line = str(summary.get("personaLine") or "").strip()
        target_line = str(summary.get("targetLine") or "").strip()
        timeslot = data.get("timeslot") if isinstance(data.get("timeslot"), dict) else {}
        return ":".join(
            [
                "predict",
                state,
                str(data.get("persona") or "").strip() or persona_line,
                str(data.get("total_predictions") or "").strip(),
                str(timeslot.get("submissions_used") or "").strip(),
                str(timeslot.get("submissions_remaining") or "").strip(),
                str(timeslot.get("slot_limit") or "").strip(),
                str(data.get("balance") or "").strip(),
                progress,
                error_code,
                _predict_orders_signature(data),
                _predict_recent_results_signature(data),
                target_line,
                detail,
                next_action_label or next_action,
            ]
        )
    return ":".join(
        [
            worknet_key or "background",
            state,
            next_action_label or next_action,
            progress,
            error_code,
            detail,
        ]
    )


def background_supervisor_snapshot(
    record: Any,
    *,
    parse_iso_datetime: Any,
) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {
            "state": None,
            "display": None,
            "status": None,
            "reminderType": None,
            "headline": None,
            "message": None,
            "reason": None,
            "progressHours": None,
        }
    summary = record.get("summary", {}) if isinstance(record.get("summary"), dict) else {}
    status_payload = record.get("statusPayload") if isinstance(record.get("statusPayload"), dict) else None
    next_action_label, next_action_command = _payload_action_bundle(status_payload)
    internal = _payload_internal(status_payload)
    error = _payload_error(status_payload)
    worknet_key = str(record.get("worknetKey") or "").strip().lower()
    background_state = str(summary.get("state") or "").strip().lower()
    next_action = str(internal.get("next_action") or "").strip().lower()
    error_code = str(error.get("code") or "").strip().lower()
    retryable = bool(error.get("retryable"))
    alive = bool(record.get("alive"))
    progress_hours = _hours_since(record.get("lastProgressAt"), parse_iso_datetime=parse_iso_datetime)
    if progress_hours is None:
        progress_hours = _background_progress_hours(record, parse_iso_datetime=parse_iso_datetime)
    headline = str(summary.get("headline") or "").strip() or "Background work is running."
    detail = str(summary.get("detail") or "").strip() or headline
    payload_message = _first_text(
        status_payload.get("user_message") if isinstance(status_payload, dict) else None,
        status_payload.get("message") if isinstance(status_payload, dict) else None,
        detail,
        headline,
    ) or detail
    text_blob = _text_blob(background_state, headline, detail, payload_message, error_code, next_action)

    if worknet_key == "mine":
        if background_state == "selection_required" or "select a dataset" in text_blob:
            return {
                "state": "waiting_for_dataset",
                "display": "Waiting for dataset",
                "status": "awaiting_dataset",
                "reminderType": "action_required",
                "headline": headline or "Mine is waiting for dataset selection.",
                "message": "Mine reached dataset selection and needs an operator choice before continuing.",
                "reason": "mine runtime is blocked on dataset selection",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if (
            background_state == "auth_required"
            or "wallet session expired" in text_blob
            or "authentication failed" in text_blob
            or "re-initialize" in text_blob
            or error_code == "unauthorized"
        ):
            return {
                "state": "auth_required",
                "display": "Authentication required",
                "status": "auth_required",
                "reminderType": "action_required",
                "headline": headline or "Mine authentication is required.",
                "message": "Mine runtime needs a refreshed wallet session before work can continue.",
                "reason": "mine runtime reported an authentication requirement",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state in {"discovering", "deduplicating", "preparing_proof", "collecting", "structuring", "submitting"}:
            display_mapping = {
                "discovering": "Discovering",
                "deduplicating": "Deduplicating",
                "preparing_proof": "Preparing proof",
                "collecting": "Collecting",
                "structuring": "Structuring",
                "submitting": "Submitting",
            }
            message_mapping = {
                "discovering": "Mine is discovering new URLs for the active dataset.",
                "deduplicating": "Mine is deduplicating the active batch before export.",
                "preparing_proof": "Mine is preparing proof for the active batch.",
                "collecting": "Mine is collecting pages from the active dataset.",
                "structuring": "Mine is structuring the collected records.",
                "submitting": "Mine is exporting and submitting processed records.",
            }
            return {
                "state": background_state,
                "display": display_mapping.get(background_state, "Running"),
                "status": "background_running",
                "reminderType": "running",
                "headline": headline or message_mapping.get(background_state) or "Mine worker is running.",
                "message": detail or message_mapping.get(background_state) or headline,
                "reason": "mine worker is actively progressing through the work loop",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "paused":
            return {
                "state": "paused",
                "display": "Paused",
                "status": "background_waiting",
                "reminderType": "info",
                "headline": headline or "Mine worker is paused.",
                "message": "Mine worker is paused and can be resumed when you are ready.",
                "reason": "mine runtime is paused",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "idle" or "no active mining session" in text_blob:
            return {
                "state": "ended_idle",
                "display": "Ended",
                "status": "background_completed",
                "reminderType": "info",
                "headline": headline or "Mine session is idle.",
                "message": "Mine has no active collection session right now; start a new round when ready.",
                "reason": "mine runtime is idle with no active collection session",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "ready" or "mining environment is ready" in text_blob:
            return {
                "state": "ready_to_start",
                "display": "Ready",
                "status": "ready_to_start",
                "reminderType": "info",
                "headline": headline or "Mine runtime is ready.",
                "message": "Mine runtime is ready and can start a new collection round.",
                "reason": "mine runtime reports ready state",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if error_code == "registration_required":
            return {
                "state": "registration_required",
                "display": "Registration required",
                "status": "registration_required",
                "reminderType": "action_required",
                "headline": headline or "Mine registration is required.",
                "message": "Mine needs AWP registration before the worker can continue.",
                "reason": "mine runtime is blocked on registration",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "error":
            if (
                error_code in {"network_error", "http_error"}
                or "temporarily unavailable" in text_blob
                or "cannot reach the platform" in text_blob
            ):
                return {
                    "state": "waiting_for_service",
                    "display": "Waiting for service",
                    "status": "background_waiting",
                    "reminderType": "attention",
                    "headline": headline or "Mine is waiting for the platform to recover.",
                    "message": payload_message,
                    "reason": "mine runtime hit a retryable platform or network error",
                    "progressHours": progress_hours,
                    "nextActionLabel": next_action_label,
                    "nextActionCommand": next_action_command,
                }
            return {
                "state": "error",
                "display": "Failed",
                "status": "background_failed",
                "reminderType": "alert",
                "headline": headline or "Mine runtime failed.",
                "message": payload_message,
                "reason": "mine runtime reported an error state",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
    if worknet_key == "predict":
        if background_state == "waiting_for_market":
            return {
                "state": "waiting_for_market",
                "display": "Waiting for market",
                "status": "background_waiting",
                "reminderType": "running",
                "headline": headline or "Predict is waiting for a market.",
                "message": "Predict is healthy but has no eligible market right now.",
                "reason": "predict loop is waiting for a submittable market",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "orders_open":
            return {
                "state": "orders_open",
                "display": "Orders open",
                "status": "background_running",
                "reminderType": "running",
                "headline": headline or "Predict has open orders working.",
                "message": detail,
                "reason": "predict loop has live open orders in the market",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "recent_result_recorded":
            return {
                "state": "recent_result_recorded",
                "display": "Recent result",
                "status": "background_running",
                "reminderType": "running",
                "headline": headline or "Predict recorded a recent market result.",
                "message": detail,
                "reason": "predict loop recently recorded a settled result",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "waiting_for_timeslot_reset" or "no submissions remaining in this timeslot" in text_blob:
            return {
                "state": "waiting_for_timeslot_reset",
                "display": "Waiting for timeslot reset",
                "status": "background_waiting",
                "reminderType": "running",
                "headline": headline or "Predict is waiting for the next timeslot.",
                "message": "Predict used the current timeslot allocation and is waiting for the next reset.",
                "reason": "predict loop used all submissions for the current timeslot",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "waiting_for_chip_feed" or "waiting for chip feed" in text_blob:
            return {
                "state": "waiting_for_chip_feed",
                "display": "Waiting for chip feed",
                "status": "background_waiting",
                "reminderType": "running",
                "headline": headline or "Predict is waiting for chip feed.",
                "message": "Predict paused because the agent balance is exhausted and is waiting for the next chip feed.",
                "reason": "predict loop is waiting for chip feed after balance exhaustion",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "rate_limited" or "rate limited" in text_blob:
            return {
                "state": "rate_limited",
                "display": "Rate limited",
                "status": "background_waiting",
                "reminderType": "running",
                "headline": headline or "Predict is rate limited.",
                "message": payload_message,
                "reason": "predict loop is waiting for a rate limit window",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if next_action == "stake_required" or error_code == "stake_required":
            return {
                "state": "stake_required",
                "display": "Stake required",
                "status": "stake_required",
                "reminderType": "action_required",
                "headline": headline or "Predict stake is required.",
                "message": "Predict cannot continue until the stake requirement is satisfied.",
                "reason": "predict runtime reported missing stake eligibility",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state in {"llm_running", "challenge_ready", "iteration_started", "starting", "submitted_iteration"}:
            return {
                "state": background_state,
                "display": "Submitted" if background_state == "submitted_iteration" else "Running",
                "status": "background_running",
                "reminderType": "running",
                "headline": headline,
                "message": detail,
                "reason": "predict loop is actively progressing",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if (
            background_state == "iteration_error"
            or (background_state == "error" and retryable)
            or (error_code in {"status_failed", "stake_fetch_failed"} and retryable)
        ):
            return {
                "state": "waiting_for_service",
                "display": "Retrying after error",
                "status": "background_waiting",
                "reminderType": "attention",
                "headline": headline or "Predict is retrying after an error.",
                "message": payload_message,
                "reason": "predict loop hit a retryable service or iteration error",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "llm_error":
            return {
                "state": "llm_error",
                "display": "Failed",
                "status": "background_failed",
                "reminderType": "alert",
                "headline": headline or "Predict loop failed.",
                "message": detail or "Predict loop hit an LLM error.",
                "reason": "predict loop reported an llm error",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
        if background_state == "error":
            return {
                "state": "error",
                "display": "Failed",
                "status": "background_failed",
                "reminderType": "alert",
                "headline": headline or "Predict loop failed.",
                "message": payload_message,
                "reason": "predict loop reported an unrecoverable error state",
                "progressHours": progress_hours,
                "nextActionLabel": next_action_label,
                "nextActionCommand": next_action_command,
            }
    if not alive:
        return {
            "state": "stopped",
            "display": "Stopped",
            "status": "background_stopped",
            "reminderType": "action_required",
            "headline": headline or "Background work has stopped.",
            "message": detail or "The background task is no longer alive.",
            "reason": "background task is registered but not alive",
            "progressHours": progress_hours,
            "nextActionLabel": next_action_label,
            "nextActionCommand": next_action_command,
        }
    if background_state in WAITING_BACKGROUND_STATES:
        return {
            "state": background_state or "waiting",
            "display": "Waiting",
            "status": "background_waiting",
            "reminderType": "running",
            "headline": headline,
            "message": detail,
            "reason": "background task is waiting on a safe upstream condition",
            "progressHours": progress_hours,
            "nextActionLabel": next_action_label,
            "nextActionCommand": next_action_command,
        }
    if progress_hours is not None and progress_hours >= 2.0:
        return {
            "state": "stalled",
            "display": "Stalled",
            "status": "background_stalled",
            "reminderType": "attention",
            "headline": headline or "Background work may be stalled.",
            "message": f"No new progress was recorded for about {int(progress_hours)} hour(s); inspect logs before continuing.",
            "reason": "background task appears alive but progress has not advanced recently",
            "progressHours": progress_hours,
            "nextActionLabel": next_action_label,
            "nextActionCommand": next_action_command,
        }
    return {
        "state": background_state or "running",
        "display": "Running",
        "status": "background_running",
        "reminderType": "running",
        "headline": headline,
        "message": detail,
        "reason": "background task is still active",
        "progressHours": progress_hours,
        "nextActionLabel": next_action_label,
        "nextActionCommand": next_action_command,
    }


def _background_task_label(record: dict[str, Any]) -> str:
    worknet_name = str(record.get("worknetName") or "").strip()
    label = str(record.get("label") or "").strip()
    if worknet_name and label and worknet_name.lower() not in label.lower():
        return f"{worknet_name} ({label})"
    return worknet_name or label or "Background task"


def _supervisor_priority_key(item: dict[str, Any]) -> tuple[int, float]:
    status = str(item.get("status") or "").strip()
    priority = SUPERVISOR_STATUS_PRIORITY.get(status, 50)
    progress_hours = item.get("progressHours")
    try:
        progress_value = float(progress_hours)
    except (TypeError, ValueError):
        progress_value = -1.0
    return priority, -progress_value


def aggregate_background_supervisors(
    records: Any,
    *,
    parse_iso_datetime: Any,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        supervisor = background_supervisor_snapshot(record, parse_iso_datetime=parse_iso_datetime)
        items.append(
            {
                "label": str(record.get("label") or "").strip() or None,
                "worknetKey": str(record.get("worknetKey") or "").strip() or None,
                "worknetName": str(record.get("worknetName") or "").strip() or None,
                "taskLabel": _background_task_label(record),
                **supervisor,
            }
        )
    if not items:
        return {
            "count": 0,
            "items": [],
            "status": None,
            "state": None,
            "display": None,
            "headline": None,
            "message": None,
            "reason": None,
            "reminderType": None,
            "nextActionLabel": None,
            "nextActionCommand": None,
            "selectedLabel": None,
            "latestSuccess": None,
            "latestFailure": None,
        }

    ordered = sorted(items, key=_supervisor_priority_key)
    primary = ordered[0]
    active_count = len(ordered)
    summaries = [
        f"{item['taskLabel']}: {str(item.get('display') or item.get('headline') or 'running').strip()}"
        for item in ordered[:3]
    ]
    summary_tail = ""
    if active_count > 3:
        summary_tail = f" {active_count - 3} more task(s) are also active."

    primary_label = str(primary.get("taskLabel") or "Background task").strip()
    primary_status = str(primary.get("status") or "").strip()
    primary_headline = str(primary.get("headline") or "").strip()
    primary_message = str(primary.get("message") or primary_headline or "").strip()
    primary_reason = str(primary.get("reason") or "").strip()

    if primary_status in {"background_failed", "background_stopped", "background_stalled", "auth_required", "registration_required", "stake_required", "awaiting_dataset"}:
        headline = f"{active_count} background task(s) active; {primary_label} needs attention."
        message = f"{primary_label}: {primary_message}." if primary_message else f"{primary_label} needs attention."
        if summaries[1:]:
            message += " Other tasks: " + "; ".join(summaries[1:]) + "."
        message += summary_tail
    elif primary_status == "background_waiting":
        headline = f"{active_count} background task(s) active; {primary_label} is waiting."
        message = "; ".join(summaries) + "." + summary_tail
    else:
        headline = f"{active_count} background task(s) active."
        message = "; ".join(summaries) + "." + summary_tail

    latest_success = None
    latest_failure = None
    if primary_status in {"background_running", "background_waiting", "ready_to_start", "background_completed"}:
        latest_success = primary_message or primary_headline or None
    else:
        latest_failure = primary_message or primary_headline or None

    return {
        "count": active_count,
        "items": ordered,
        "status": primary_status or "background_running",
        "state": primary.get("state"),
        "display": primary.get("display"),
        "headline": headline,
        "message": message,
        "reason": primary_reason or "multiple background tasks are active",
        "reminderType": primary.get("reminderType") or "running",
        "nextActionLabel": primary.get("nextActionLabel"),
        "nextActionCommand": primary.get("nextActionCommand"),
        "selectedLabel": primary.get("label"),
        "selectedTaskLabel": primary_label,
        "latestSuccess": latest_success,
        "latestFailure": latest_failure,
    }


def merge_background_observation(
    record: Any,
    observation: Any,
    *,
    now_iso: Any,
    parse_iso_datetime: Any,
) -> dict[str, Any]:
    source = dict(record) if isinstance(record, dict) else {}
    observed = dict(observation) if isinstance(observation, dict) else {}
    updated = {**source, **observed}
    updated["lastObservedAt"] = now_iso()
    if "alive" in observed:
        updated["alive"] = bool(observed.get("alive"))
    if isinstance(observed.get("statusPayload"), (dict, list)):
        updated["statusPayload"] = observed.get("statusPayload")
    if isinstance(observed.get("statusResult"), dict):
        updated["statusResult"] = observed.get("statusResult")
    if isinstance(observed.get("summary"), dict):
        updated["summary"] = observed.get("summary")
    supervisor = background_supervisor_snapshot(updated, parse_iso_datetime=parse_iso_datetime)
    updated["supervisorState"] = supervisor.get("state")
    updated["supervisorDisplay"] = supervisor.get("display")
    updated["supervisorHeadline"] = supervisor.get("headline")
    updated["supervisorMessage"] = supervisor.get("message")
    updated["supervisorStatus"] = supervisor.get("status")
    updated["supervisorReminderType"] = supervisor.get("reminderType")
    updated["supervisorNextActionLabel"] = supervisor.get("nextActionLabel")
    updated["supervisorNextActionCommand"] = supervisor.get("nextActionCommand")
    signal = background_progress_signal(updated)
    previous_signal = str(source.get("lastProgressSignal") or "").strip() or None
    if signal:
        updated["lastProgressSignal"] = signal
        if signal != previous_signal:
            updated["lastProgressAt"] = updated["lastObservedAt"]
    if not updated.get("lastProgressAt"):
        updated["lastProgressAt"] = source.get("startedAt") or updated["lastObservedAt"]
    return updated
