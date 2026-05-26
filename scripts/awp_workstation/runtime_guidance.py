"""Runtime guidance synthesis for WorkNet run results."""

from __future__ import annotations

import shlex
from typing import Any, Callable, Optional

from awp_workstation.commands import render_argv
from awp_workstation.parameters import extract_command_parameter_schema
from awp_workstation.runtime_actions import (
    find_executed_step,
    gov_signed_template_actions,
    guidance_action,
    predict_loop_actions,
    predict_persona_actions,
    predict_stake_support_actions,
    skill_script_action,
    step_guidance_action,
)
from awp_workstation.runtime_payloads import runtime_message, step_result_payload


RuntimeGuidanceFromStep = Callable[[dict[str, Any]], Optional[dict[str, Any]]]


def predict_runtime_guidance(
    executed_steps: list[dict[str, Any]],
    *,
    runtime_guidance_from_step: RuntimeGuidanceFromStep,
    state_root: str,
) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    legacy_label_prefix = " " * 7
    persona_step = next(
        (
            step for step in executed_steps
            if isinstance(step, dict)
            and isinstance(step.get("label"), str)
            and (
                str(step.get("label")).startswith("Select ")
                or str(step.get("label")).startswith(legacy_label_prefix)
            )
        ),
        None,
    )
    status_step = find_executed_step(executed_steps, "predict status")
    stake_step = find_executed_step(executed_steps, "predict stake eligibility")
    context_step = find_executed_step(executed_steps, "       Predict context") or find_executed_step(executed_steps, "predict context")
    status_payload = step_result_payload(status_step) if status_step else None
    stake_payload = step_result_payload(stake_step) if stake_step else None
    status_guidance = runtime_guidance_from_step(status_step) if status_step else None
    stake_error_code = None
    stake_suggestion = None
    if isinstance(stake_payload, dict):
        error = stake_payload.get("error")
        if isinstance(error, dict):
            stake_error_code = str(error.get("code") or "")
            stake_suggestion = error.get("suggestion")

    if isinstance(persona_step, dict):
        persona_payload = step_result_payload(persona_step)
        persona_data = persona_payload.get("data") if isinstance(persona_payload, dict) else None
        persona_name = None
        if isinstance(persona_data, dict) and isinstance(persona_data.get("persona"), str):
            persona_name = str(persona_data.get("persona"))
        if not persona_name:
            argv = persona_step.get("argv")
            if isinstance(argv, list) and argv:
                persona_name = str(argv[-1])
        persona_ok = bool(persona_payload.get("ok")) if isinstance(persona_payload, dict) else False
        persona_error_code = None
        if isinstance(persona_payload, dict):
            error = persona_payload.get("error")
            if isinstance(error, dict):
                persona_error_code = str(error.get("code") or "")
        if persona_ok or persona_error_code == "PERSONA_COOLDOWN":
            follow_up = predict_loop_actions(state_root)
            message = f"Predict persona selected: {persona_name or 'custom'}."
            if persona_error_code == "PERSONA_COOLDOWN":
                message = "Predict persona is still in cooldown; continue with the cached persona."
            guidance = {
                "message": message,
                "userActions": [item["label"] for item in follow_up],
                "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
                "nextCommand": ["predict-agent", "loop", "--interval", "120", "--agent-id", "predict-worker"],
                "nextAction": "start_predict_loop",
                "state": None,
            }
            return guidance, follow_up

    persona = None
    if isinstance(status_payload, dict):
        data = status_payload.get("data")
        if isinstance(data, dict):
            persona = data.get("persona")
    persona_value = str(persona or "").strip().lower()

    if isinstance(status_payload, dict) and persona_value in {"", "none", "null"}:
        follow_up = predict_persona_actions(state_root)
        guidance = {
            "message": "Predict needs a persona before the autonomous loop can start.",
            "userActions": [item["label"] for item in follow_up],
            "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
            "nextCommand": ["predict-agent", "set-persona", "<PERSONA>"],
            "nextAction": "select_predict_persona",
            "state": None,
        }
        return guidance, follow_up

    if isinstance(status_payload, dict) and persona_value not in {"", "none", "null"}:
        follow_up = predict_loop_actions(state_root)
        if stake_error_code in {"NOT_STAKED", "STAKE_FETCH_FAILED"}:
            follow_up.extend(predict_stake_support_actions(state_root))
        guidance = {
            "message": f"Predict persona selected: {persona_value}.",
            "userActions": [item["label"] for item in follow_up],
            "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
            "nextCommand": ["predict-agent", "loop", "--interval", "120", "--agent-id", "predict-worker"],
            "nextAction": "start_predict_loop",
            "state": None,
        }
        if stake_error_code == "NOT_STAKED":
            guidance["detail"] = stake_suggestion or runtime_message(stake_payload)
        elif stake_error_code == "STAKE_FETCH_FAILED":
            guidance["detail"] = stake_suggestion or runtime_message(stake_payload)
        return guidance, follow_up

    if isinstance(stake_payload, dict):
        if stake_error_code == "NOT_STAKED":
            follow_up = [
                guidance_action(
                    "View Predict context",
                    "predict-agent context",
                    argv=["predict-agent", "context"],
                    cwd=state_root,
                    safe_to_auto_run=True,
                    preferred=True,
                ),
                *predict_stake_support_actions(state_root),
            ]
            guidance = {
                "message": "Predict stake-backed submissions require 1000 AWP or KYA delegated eligibility.",
                "userActions": [item["label"] for item in follow_up],
                "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
                "nextCommand": ["predict-agent", "stake"],
                "nextAction": "stake_required",
                "state": None,
                "detail": stake_suggestion or runtime_message(stake_payload),
            }
            return guidance, follow_up
        if stake_error_code == "STAKE_FETCH_FAILED":
            follow_up = [
                guidance_action(
                    "View Predict context",
                    "predict-agent context",
                    argv=["predict-agent", "context"],
                    cwd=state_root,
                    safe_to_auto_run=True,
                    preferred=True,
                ),
                guidance_action(
                    "Check Predict stake eligibility",
                    "predict-agent stake",
                    argv=["predict-agent", "stake"],
                    cwd=state_root,
                    safe_to_auto_run=True,
                ),
            ]
            guidance = {
                "message": "Predict stake eligibility could not be verified; retry the stake check.",
                "userActions": [item["label"] for item in follow_up],
                "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
                "nextCommand": ["predict-agent", "stake"],
                "nextAction": "retry_stake_check",
                "state": None,
                "detail": stake_suggestion or runtime_message(stake_payload),
            }
            return guidance, follow_up

    if isinstance(status_guidance, dict):
        follow_up = [
            guidance_action(
                "View Predict context",
                "predict-agent context",
                argv=["predict-agent", "context"],
                cwd=state_root,
                safe_to_auto_run=True,
                preferred=True,
            ),
        ]
        guidance = dict(status_guidance)
        guidance["message"] = "Predict runtime needs fresh market context."
        guidance["userActions"] = [item["label"] for item in follow_up]
        guidance["actionMap"] = {item["label"]: item["command"] for item in follow_up if item.get("command")}
        guidance["nextCommand"] = ["predict-agent", "context"]
        guidance["nextAction"] = "fetch_context"
        return guidance, follow_up

    context_payload = step_result_payload(context_step) if context_step else None
    context_guidance = runtime_guidance_from_step(context_step) if context_step else None
    if isinstance(context_payload, dict) and isinstance(context_guidance, dict):
        next_command = context_guidance.get("nextCommand")
        recommendation = context_payload.get("data", {}).get("recommendation") if isinstance(context_payload.get("data"), dict) else None
        recommendation_action = recommendation.get("action") if isinstance(recommendation, dict) else None
        market_id = recommendation.get("market_id") if isinstance(recommendation, dict) else None
        if recommendation_action == "submit" and isinstance(next_command, list) and next_command:
            submit_command = render_argv(next_command)
            message = "Predict context selected a submission candidate; confirm tickets and reasoning before sending."
            if market_id:
                message = f"Predict context selected market {market_id}; confirm tickets and reasoning before sending."
            follow_up = [
                guidance_action(
                    "Submit Predict position",
                    submit_command,
                    argv=[str(item) for item in next_command],
                    cwd=state_root,
                    requires_confirmation=True,
                    parameter_schema=extract_command_parameter_schema([str(item) for item in next_command]),
                ),
                guidance_action(
                    "View Predict context",
                    "predict-agent context",
                    argv=["predict-agent", "context"],
                    cwd=state_root,
                    safe_to_auto_run=False,
                ),
            ]
            guidance = {
                "message": message,
                "userActions": [item["label"] for item in follow_up],
                "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
                "nextCommand": next_command,
                "nextAction": "confirm_predict_submission",
                "state": None,
            }
            return guidance, follow_up
        follow_up = [
            guidance_action(
                "View Predict context",
                "predict-agent context",
                argv=["predict-agent", "context"],
                cwd=state_root,
                safe_to_auto_run=True,
                preferred=True,
            )
        ]
        guidance = {
            "message": runtime_message(context_payload) or "Predict context is waiting for an actionable market.",
            "userActions": [item["label"] for item in follow_up],
            "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
            "nextCommand": ["predict-agent", "context"],
            "nextAction": "wait_for_predict_market",
            "state": None,
        }
        return guidance, follow_up

    return None, []


def gov_runtime_guidance(executed_steps: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    helper_step = find_executed_step(executed_steps, "gov phase-aware helper")
    state_step = find_executed_step(executed_steps, "gov private state")
    helper_payload = step_result_payload(helper_step) if helper_step else None
    state_payload = step_result_payload(state_step) if state_step else None
    phase = None
    if isinstance(helper_payload, dict) and isinstance(helper_payload.get("phase"), str):
        phase = str(helper_payload.get("phase"))
    available = helper_payload.get("available") if isinstance(helper_payload, dict) else None
    blocked = helper_payload.get("blocked") if isinstance(helper_payload, dict) else None

    actions: list[dict[str, Any]] = []
    helper_action = step_guidance_action("       Gov             ", helper_step, preferred=True)
    if helper_action:
        actions.append(helper_action)
    markets_step = find_executed_step(executed_steps, "gov public markets")
    markets_action = step_guidance_action("       Gov markets", markets_step)
    if markets_action:
        actions.append(markets_action)
    actions.append(skill_script_action("       staking       ", "query-knowledge.py", "--topic", "staking"))

    if isinstance(state_payload, dict) and str(state_payload.get("error") or "") == "STATE_PRINCIPAL_NOT_IN_EPOCH":
        message = "Gov                                         principal              AWP Power                                             "
        detail = str(state_payload.get("detail") or "")
        if phase:
            message = f"Gov        phase     {phase}             principal              AWP Power                                             "
        guidance = {
            "message": message,
            "userActions": [item["label"] for item in actions],
            "actionMap": {item["label"]: item["command"] for item in actions if item.get("command")},
            "nextCommand": None,
            "nextAction": "acquire_awp_power_or_observe_gov",
            "state": phase,
            "detail": detail,
        }
        return guidance, actions

    if isinstance(helper_payload, dict):
        actions.extend(gov_signed_template_actions(helper_step, helper_payload))
        action_map = {item["label"]: item["command"] for item in actions if item.get("command")}
        message = f"Gov runtime phase: {phase}." if phase else "Gov runtime phase is ready for review."
        if isinstance(available, list):
            available_ops = [str(item.get("op")) for item in available[:3] if isinstance(item, dict) and item.get("op")]
            if available_ops:
                message += " Available operations: " + ", ".join(available_ops) + "."
        if isinstance(blocked, list):
            blocked_ops = [str(item.get("op")) for item in blocked[:2] if isinstance(item, dict) and item.get("op")]
            if blocked_ops:
                message += " Blocked by phase: " + ", ".join(blocked_ops) + "."
        guidance = {
            "message": message,
            "userActions": [item["label"] for item in actions],
            "actionMap": action_map,
            "nextCommand": None,
            "nextAction": "review_gov_phase",
            "state": phase,
        }
        return guidance, actions

    return None, []


def ardi_runtime_guidance(
    executed_steps: list[dict[str, Any]],
    *,
    runtime_guidance_from_step: RuntimeGuidanceFromStep,
    state_root: str,
) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    gas_step = find_executed_step(executed_steps, "ardi gas check")
    stake_step = find_executed_step(executed_steps, "ardi stake guidance")
    preflight_step = find_executed_step(executed_steps, "ardi preflight")
    gas_payload = step_result_payload(gas_step) if gas_step else None
    stake_payload = step_result_payload(stake_step) if stake_step else None

    actions: list[dict[str, Any]] = []
    gas_suggestion = None
    if isinstance(gas_payload, dict):
        data = gas_payload.get("data")
        if isinstance(data, dict):
            gas_suggestion = data.get("suggestion")
    if gas_suggestion:
        actions.append(
            guidance_action(
                "    Base Gas",
                str(gas_suggestion),
                requires_confirmation=True,
            )
        )
    actions.append(
        guidance_action(
            "Run Ardi preflight",
            "ardi-agent preflight",
            argv=["ardi-agent", "preflight"],
            cwd=state_root,
            safe_to_auto_run=True,
            preferred=True,
        )
    )

    stake_suggestion = None
    if isinstance(stake_payload, dict):
        data = stake_payload.get("data")
        if isinstance(data, dict):
            stake_suggestion = data.get("suggestion")
    if stake_suggestion:
        actions.append(guidance_action("Open KYA eligibility", "https://kya.link/"))
        actions.append(
            guidance_action(
                "Buy and stake Ardi",
                "ardi-agent buy-and-stake",
                argv=["ardi-agent", "buy-and-stake"],
                cwd=state_root,
                requires_confirmation=True,
            )
        )
        actions.append(
            guidance_action(
                "       Ardi stake       ",
                "ardi-agent stake",
                argv=["ardi-agent", "stake"],
                cwd=state_root,
                safe_to_auto_run=True,
            )
        )

    if gas_suggestion or stake_suggestion:
        message = "Ardi runtime                                   commit/reveal          "
        if gas_suggestion and stake_suggestion:
            message = "Ardi runtime                                Base gas             stake                          commit/reveal          "
        elif gas_suggestion:
            message = "Ardi runtime                                Base gas                   preflight   "
        elif stake_suggestion:
            message = "Ardi runtime                             stake          "
        guidance = {
            "message": message,
            "userActions": [item["label"] for item in actions],
            "actionMap": {item["label"]: item["command"] for item in actions if item.get("command")},
            "nextCommand": ["ardi-agent", "preflight"] if preflight_step else ["ardi-agent", "stake"],
            "nextAction": "fund_gas_and_or_satisfy_stake",
            "state": None,
            "detail": "; ".join(item for item in [str(gas_suggestion or ""), str(stake_suggestion or "")] if item),
        }
        return guidance, actions

    status_step = find_executed_step(executed_steps, "ardi status")
    status_guidance = runtime_guidance_from_step(status_step) if status_step else None
    if isinstance(status_guidance, dict):
        actions = [
            guidance_action(
                "       Ardi preflight",
                "ardi-agent preflight",
                argv=["ardi-agent", "preflight"],
                cwd=state_root,
                safe_to_auto_run=True,
                preferred=True,
            )
        ]
        guidance = dict(status_guidance)
        guidance["message"] = "Ardi runtime                          preflight   "
        guidance["userActions"] = [item["label"] for item in actions]
        guidance["actionMap"] = {item["label"]: item["command"] for item in actions if item.get("command")}
        guidance["nextCommand"] = ["ardi-agent", "preflight"]
        guidance["nextAction"] = "review"
        return guidance, actions

    return None, []


def synthesize_run_guidance(
    playbook: dict[str, Any],
    executed_steps: list[dict[str, Any]],
    *,
    runtime_guidance_from_step: RuntimeGuidanceFromStep,
    state_root: str,
) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    worknet_key = str(playbook.get("worknetKey") or "")
    if worknet_key == "predict":
        return predict_runtime_guidance(
            executed_steps,
            runtime_guidance_from_step=runtime_guidance_from_step,
            state_root=state_root,
        )
    if worknet_key == "gov":
        return gov_runtime_guidance(executed_steps)
    if worknet_key == "ardi":
        return ardi_runtime_guidance(
            executed_steps,
            runtime_guidance_from_step=runtime_guidance_from_step,
            state_root=state_root,
        )
    if worknet_key == "mine":
        primary = find_executed_step(executed_steps, "start mine worker")
        if primary:
            guidance = runtime_guidance_from_step(primary)
            if isinstance(guidance, dict):
                actions = [
                    guidance_action(
                        label,
                        guidance.get("actionMap", {}).get(label),
                        argv=shlex.split(str(guidance.get("actionMap", {}).get(label))) if isinstance(guidance.get("actionMap", {}).get(label), str) else None,
                        cwd=str(primary.get("cwd")) if primary.get("cwd") else None,
                        safe_to_auto_run=True,
                        preferred=index == 0,
                    )
                    for index, label in enumerate(guidance.get("userActions", []))
                ]
                return guidance, [item for item in actions if item.get("label")]
    for step in reversed(executed_steps):
        guidance = runtime_guidance_from_step(step)
        if isinstance(guidance, dict):
            actions = [
                guidance_action(
                    label,
                    guidance.get("actionMap", {}).get(label),
                    argv=shlex.split(str(guidance.get("actionMap", {}).get(label))) if isinstance(guidance.get("actionMap", {}).get(label), str) else None,
                    cwd=str(step.get("cwd")) if step.get("cwd") else None,
                    safe_to_auto_run=True,
                    preferred=index == 0,
                )
                for index, label in enumerate(guidance.get("userActions", []))
            ]
            return guidance, [item for item in actions if item.get("label")]
    return None, []
