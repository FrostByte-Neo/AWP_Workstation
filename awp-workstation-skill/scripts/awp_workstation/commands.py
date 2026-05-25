"""Command-line renderers for workstation user actions."""

from __future__ import annotations

import shlex
from typing import Optional


PREDICT_PERSONAS = ["degen", "analyst"]


def render_argv(argv: list[str]) -> str:
    if not argv:
        return ""
    return shlex.join([str(item) for item in argv])


def workstation_follow_up_command(label: str, *, execute: bool) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--follow-up-label",
        label,
    ]
    if execute:
        argv.append("--execute")
    return render_argv(argv)


def workstation_confirmation_command(label: str, *, execute: bool) -> str:
    
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--confirm-label",
        label,
    ]
    if execute:
        argv.append("--execute")
    return render_argv(argv)


def workstation_background_command(
    label: str,
    *,
    stop: bool = False,
    execute: bool = False,
    tail_lines: Optional[int] = None,
) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
    ]
    argv.extend(["--stop-background-label" if stop else "--background-label", label])
    if tail_lines is not None:
        argv.extend(["--tail-lines", str(tail_lines)])
    if execute:
        argv.append("--execute")
    return render_argv(argv)


def workstation_pause_command(*, execute: bool) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--pause",
    ]
    if execute:
        argv.append("--execute")
    return render_argv(argv)


def query_source_command(source_key: str, *, rebuild: bool = False) -> str:
    argv = [
        "python3",
        "scripts/query-source.py",
        "--source-key",
        source_key,
    ]
    if rebuild:
        argv.append("--rebuild")
    return render_argv(argv)


def query_knowledge_command(topic_key: str, *, rebuild: bool = False) -> str:
    argv = [
        "python3",
        "scripts/query-knowledge.py",
        "--topic",
        topic_key,
    ]
    if rebuild:
        argv.append("--rebuild")
    return render_argv(argv)


def knowledge_review_queue_command(*, refresh: bool = False) -> str:
    argv = [
        "python3",
        "scripts/knowledge-review-queue.py",
    ]
    if refresh:
        argv.append("--refresh")
    return render_argv(argv)


def start_workstation_command() -> str:
    return render_argv(["python3", "scripts/start-workstation.py"])


def review_epoch_command(*, full: bool = False) -> str:
    argv = ["python3", "scripts/review-epoch.py"]
    if full:
        argv.append("--full")
    return render_argv(argv)


def workstation_status_command(
    *,
    query: Optional[str] = None,
    intent: Optional[str] = None,
    worknet: Optional[str] = None,
    full: bool = False,
) -> str:
    argv = ["python3", "scripts/workstation-status.py"]
    if query is not None:
        argv.extend(["--query", query])
    if intent is not None:
        argv.extend(["--intent", intent])
    if worknet is not None:
        argv.extend(["--worknet", worknet])
    if full:
        argv.append("--full")
    return render_argv(argv)


def workstation_preflight_command(*, full: bool = False) -> str:
    argv = ["python3", "scripts/workstation-preflight.py"]
    if full:
        argv.append("--full")
    return render_argv(argv)


def scan_worknets_command() -> str:
    return render_argv(["python3", "scripts/scan-worknets.py"])


def build_playbook_command(worknet_identifier: str, *, full: bool = False) -> str:
    argv = [
        "python3",
        "scripts/build-playbook.py",
        "--worknet",
        worknet_identifier,
    ]
    if full:
        argv.append("--full")
    return render_argv(argv)


def run_worknet_command(
    worknet_identifier: str,
    *,
    execute: bool,
    auto_advance: bool = False,
) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--worknet",
        worknet_identifier,
    ]
    if execute:
        argv.append("--execute")
    if auto_advance:
        argv.append("--auto-advance")
    return render_argv(argv)


def workstation_preferences_command(
    *,
    preferred_worknet: Optional[str] = None,
    allow_asset_actions: Optional[bool] = None,
    autopilot_mode: Optional[str] = None,
    allow_third_party_skills: Optional[bool] = None,
    observe_before_predict_hours: Optional[int] = None,
    risk_profile: Optional[str] = None,
) -> str:
    argv = [
        "python3",
        "scripts/workstation-preferences.py",
    ]
    if preferred_worknet is not None:
        argv.extend(["--preferred-worknet", preferred_worknet])
    if allow_asset_actions is not None:
        argv.extend(["--allow-asset-actions", "true" if allow_asset_actions else "false"])
    if autopilot_mode is not None:
        argv.extend(["--autopilot-mode", autopilot_mode])
    if allow_third_party_skills is not None:
        argv.extend(["--allow-third-party-skills", "true" if allow_third_party_skills else "false"])
    if observe_before_predict_hours is not None:
        argv.extend(["--observe-before-predict-hours", str(observe_before_predict_hours)])
    if risk_profile is not None:
        argv.extend(["--risk-profile", risk_profile])
    return render_argv(argv)
