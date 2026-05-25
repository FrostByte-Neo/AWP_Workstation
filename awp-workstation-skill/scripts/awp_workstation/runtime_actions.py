"""Runtime follow-up action construction helpers."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.action_groups import annotate_execution_actions
from awp_workstation.action_text import humanize_public_action_label
from awp_workstation.commands import PREDICT_PERSONAS, render_argv
from awp_workstation.parameters import extract_command_parameter_schema
from awp_workstation.state import SKILL_ROOT


def guidance_action(
    label: str,
    command: Optional[str],
    *,
    argv: Optional[list[str]] = None,
    cwd: Optional[str] = None,
    safe_to_auto_run: bool = False,
    requires_confirmation: bool = False,
    preferred: bool = False,
    parameter_schema: Optional[list[dict[str, Any]]] = None,
    long_running: bool = False,
) -> dict[str, Any]:
    payload = {
        "label": label,
        "displayLabel": humanize_public_action_label(label),
        "command": command,
        "argv": argv,
        "cwd": cwd,
        "safeToAutoRun": safe_to_auto_run,
        "requiresConfirmation": requires_confirmation,
        "selectedByDefault": preferred,
        "parameterSchema": parameter_schema or [],
        "longRunning": long_running,
    }
    annotated = annotate_execution_actions([payload])
    return annotated[0] if annotated else payload


def skill_script_action(
    label: str,
    script_name: str,
    *args: str,
    preferred: bool = False,
) -> dict[str, Any]:
    argv = ["python3", str(SKILL_ROOT / "scripts" / script_name), *args]
    return guidance_action(
        label,
        render_argv(argv),
        argv=argv,
        cwd=str(SKILL_ROOT / "scripts"),
        safe_to_auto_run=True,
        preferred=preferred,
    )


def find_executed_step(executed_steps: list[dict[str, Any]], label: str) -> Optional[dict[str, Any]]:
    for step in executed_steps:
        if isinstance(step, dict) and step.get("label") == label:
            return step
    return None


def step_command_string(step: Optional[dict[str, Any]]) -> Optional[str]:
    if not isinstance(step, dict):
        return None
    argv = step.get("argv")
    if not isinstance(argv, list) or not argv:
        return None
    return render_argv([str(item) for item in argv])


def step_guidance_action(
    label: str,
    step: Optional[dict[str, Any]],
    *,
    preferred: bool = False,
    safe_to_auto_run: bool = True,
) -> Optional[dict[str, Any]]:
    if not isinstance(step, dict):
        return None
    argv = step.get("argv")
    if not isinstance(argv, list) or not argv:
        return None
    return guidance_action(
        label,
        render_argv([str(item) for item in argv]),
        argv=[str(item) for item in argv],
        cwd=str(step.get("cwd")) if step.get("cwd") else None,
        safe_to_auto_run=safe_to_auto_run,
        preferred=preferred,
    )


def python_template_action(
    label: str,
    *,
    cwd: str,
    python_bin: str,
    script_rel: str,
    args: list[str],
    requires_confirmation: bool = False,
    safe_to_auto_run: bool = False,
    preferred: bool = False,
) -> dict[str, Any]:
    argv = [python_bin, script_rel, *args]
    return guidance_action(
        label,
        render_argv(argv),
        argv=argv,
        cwd=cwd,
        requires_confirmation=requires_confirmation,
        safe_to_auto_run=safe_to_auto_run,
        preferred=preferred,
        parameter_schema=extract_command_parameter_schema(argv),
    )


def predict_persona_actions(state_root: str) -> list[dict[str, Any]]:
    return [
        guidance_action(
            f"Select {persona} persona",
            f"predict-agent set-persona {persona}",
            argv=["predict-agent", "set-persona", persona],
            cwd=state_root,
            safe_to_auto_run=False,
        )
        for persona in PREDICT_PERSONAS
    ]


def predict_loop_actions(state_root: str) -> list[dict[str, Any]]:
    return [
        guidance_action(
            "Start Predict loop with notifications",
            "predict-agent loop --interval 120 --agent-id predict-worker --notify",
            argv=["predict-agent", "loop", "--interval", "120", "--agent-id", "predict-worker", "--notify"],
            cwd=state_root,
            safe_to_auto_run=True,
            long_running=True,
        ),
        guidance_action(
            "Start Predict loop",
            "predict-agent loop --interval 120 --agent-id predict-worker",
            argv=["predict-agent", "loop", "--interval", "120", "--agent-id", "predict-worker"],
            cwd=state_root,
            safe_to_auto_run=True,
            preferred=True,
            long_running=True,
        ),
    ]


def predict_stake_support_actions(state_root: str) -> list[dict[str, Any]]:
    return [
        guidance_action("Open AWP staking UI", "https://awp.pro/staking"),
        guidance_action("Open KYA eligibility", "https://kya.link/"),
        guidance_action(
            "Check Predict stake eligibility",
            "predict-agent stake",
            argv=["predict-agent", "stake"],
            cwd=state_root,
            safe_to_auto_run=True,
        ),
    ]


def gov_signed_template_actions(helper_step: Optional[dict[str, Any]], helper_payload: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(helper_step, dict):
        return []
    argv = helper_step.get("argv")
    cwd = helper_step.get("cwd")
    if not isinstance(argv, list) or not argv or not cwd:
        return []
    python_bin = str(argv[0])
    available = helper_payload.get("available") if isinstance(helper_payload, dict) else None
    ops = {
        str(item.get("op"))
        for item in available or []
        if isinstance(item, dict) and item.get("op")
    }
    actions: list[dict[str, Any]] = []
    if "submit-order" in ops:
        actions.append(
            python_template_action(
                "       Gov          ",
                cwd=str(cwd),
                python_bin=python_bin,
                script_rel="scripts/trade/submit-order.py",
                args=[
                    "--market", "<market_id>",
                    "--worknet", "<worknet_id>",
                    "--side", "<buy|sell>",
                    "--kind", "limit",
                    "--price", "<price>",
                    "--quantity", "<quantity>",
                    "--yes",
                ],
                requires_confirmation=True,
            )
        )
    if "submit-vote" in ops:
        actions.append(
            python_template_action(
                "       Gov       ",
                cwd=str(cwd),
                python_bin=python_bin,
                script_rel="scripts/vote/submit-vote.py",
                args=[
                    "--market", "<market_id>",
                    "--vote", "<vote_weights_csv>",
                    "--prediction", "<prediction_weights_csv>",
                    "--vote-revision", "<vote_revision>",
                    "--yes",
                ],
                requires_confirmation=True,
            )
        )
    if "split-position" in ops:
        actions.append(
            python_template_action(
                "       Gov split",
                cwd=str(cwd),
                python_bin=python_bin,
                script_rel="scripts/positions/split.py",
                args=[
                    "--market", "<market_id>",
                    "--quantity", "<quantity>",
                    "--yes",
                ],
                requires_confirmation=True,
            )
        )
    if "merge-position" in ops:
        actions.append(
            python_template_action(
                "       Gov merge",
                cwd=str(cwd),
                python_bin=python_bin,
                script_rel="scripts/positions/merge.py",
                args=[
                    "--market", "<market_id>",
                    "--quantity", "<quantity>",
                    "--yes",
                ],
                requires_confirmation=True,
            )
        )
    return actions
