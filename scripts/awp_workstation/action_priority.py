"""Action priority scoring helpers."""

from __future__ import annotations

from typing import Any, Optional


def action_priority_key(
    execution_state: Optional[str],
    resume_status: Optional[str],
    *,
    label: Any,
    command: Optional[str] = None,
    worknet_key: Optional[str] = None,
) -> tuple[int, str]:
    status = str(execution_state or resume_status or "").strip()
    text = str(label or "").strip()
    command_text = str(command or "").strip()
    lowered = text.lower()
    is_source_view = lowered.startswith("review source")
    is_source_refresh = lowered.startswith("refresh source")
    is_source = is_source_view or is_source_refresh
    is_knowledge_refresh = lowered.startswith(("refresh ", "rebuild "))
    is_knowledge_view = lowered.startswith(("review ", "view "))
    is_knowledge = is_knowledge_view or is_knowledge_refresh
    is_continue = lowered.startswith(("continue ", "start ", "run "))
    is_restart = lowered.startswith("restart ")
    is_switch_default = lowered.startswith(("start ", "switch "))
    is_confirmation = lowered.startswith("confirm ") or "--confirm-label" in command_text
    is_dataset = text in {
        "Select Basic Amazon Products Dataset",
        "Select Basic Amazon Products Pending Dataset",
        "Select Amazon Reviews Dataset",
    }
    is_review = lowered.startswith(("review latest epoch", "review pending")) or command_text.startswith("python3 scripts/review-epoch.py")
    is_research = lowered.startswith(("research ", "review awp")) or "--intent research" in command_text
    is_background_inspect = "--background-label" in command_text and not "--stop-background-label" in command_text
    is_background_stop = "--stop-background-label" in command_text or lowered.startswith("stop ")
    is_pause = "--pause" in command_text or lowered.startswith("pause ")
    is_playbook = command_text.startswith("python3 scripts/build-playbook.py")
    is_query_source = command_text.startswith("python3 scripts/query-source.py")
    is_query_knowledge = command_text.startswith("python3 scripts/query-knowledge.py")
    is_run_command = command_text.startswith("python3 scripts/run-workstation.py")
    is_scan = command_text.startswith("python3 scripts/scan-worknets.py")
    is_inspect = (
        command_text.startswith("python3 /")
        or command_text.startswith("python3 scripts/inspect-skill.py")
        or (command_text and not command_text.startswith("python3 scripts/"))
    )
    is_gov_observe = text in {
        "Start Gov",
        "Review Gov",
        "Review latest epoch",
    }
    is_remediation = (
        lowered.startswith(("inspect ", "install ", "create ", "retry ", "run full preflight"))
        or text in {
            "Start Predict",
            "Check Predict status",
            "Check Predict stake eligibility",
            "Run full preflight",
        }
    )

    score = 50
    if is_confirmation:
        score = 0
    elif status == "review_required":
        if is_knowledge_refresh:
            score = 0
        elif is_source_refresh:
            score = 5
        elif is_knowledge_view:
            score = 10
        elif is_source_view:
            score = 15
        elif is_review:
            score = 20
        elif is_continue:
            score = 25
        elif is_remediation or is_inspect or is_playbook or is_run_command:
            score = 30
    elif status == "prefer_fresh_start":
        if is_switch_default:
            score = 0
        elif is_restart:
            score = 5
        elif is_continue:
            score = 10
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "awaiting_dataset":
        if is_dataset:
            score = 0
        elif is_continue:
            score = 5
        elif is_remediation:
            score = 10
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "observe_only":
        if is_gov_observe:
            score = 0
        elif is_scan:
            score = 5
        elif is_continue:
            score = 10
        elif is_remediation:
            score = 15
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "restart_available":
        if is_restart:
            score = 0
        elif is_continue:
            score = 5
        elif is_remediation:
            score = 15
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "follow_runtime_guidance":
        if is_remediation or is_dataset or is_gov_observe or is_run_command or is_continue:
            score = 0
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status in {"knowledge_review_needed", "stale_knowledge_pending"}:
        if is_knowledge_refresh:
            score = 0
        elif is_source_refresh:
            score = 5
        elif is_knowledge_view:
            score = 10
        elif is_source_view:
            score = 15
        elif is_run_command or is_playbook or is_continue:
            score = 25
        elif is_review:
            score = 30
    elif status == "source_review_needed":
        if is_source_refresh:
            score = 0
        elif is_source_view:
            score = 5
        elif is_knowledge_refresh:
            score = 10
        elif is_knowledge_view:
            score = 15
        elif is_run_command or is_playbook or is_continue:
            score = 25
        elif is_review:
            score = 30
    elif status in {"knowledge_ready", "source_ready", "switch_suggested", "runnable"}:
        if worknet_key == "predict" and lowered.startswith("start predict"):
            score = 0
        elif worknet_key == "gov" and is_gov_observe:
            score = 0
        elif worknet_key == "ardi" and is_remediation:
            score = 0
        elif is_run_command and lowered.startswith(("start ", "continue ", "run ")):
            score = 0
        elif is_scan:
            score = 5
        elif is_playbook:
            score = 10
        elif is_run_command or is_inspect or is_remediation:
            score = 10
        elif is_knowledge_view or is_source_view:
            score = 15
        elif is_review:
            score = 25
        elif is_source_refresh or is_knowledge_refresh:
            score = 30
    elif status in {"blocked", "partial", "needs_runtime_setup", "runtime_error", "network_blocked", "partial_ready", "manual_review"}:
        if is_remediation or is_inspect:
            score = 0
        elif is_scan:
            score = 5
        elif is_continue:
            score = 10
        elif is_restart:
            score = 15
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 75
        elif is_source:
            score = 90
    elif status in {"prepared", "not_started"}:
        if is_continue:
            score = 0
        elif is_restart:
            score = 5
        elif is_remediation or is_inspect or is_run_command or is_playbook:
            score = 15
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "ready_to_execute":
        if is_inspect or is_playbook or is_run_command or is_continue:
            score = 0
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "ready_for_follow_up":
        if is_continue or is_remediation or is_run_command:
            score = 0
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "background_running":
        if is_background_inspect:
            score = 0
        elif is_pause or is_background_stop:
            score = 5
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "executed":
        if is_review:
            score = 0
        elif is_continue or is_run_command:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    else:
        if is_continue:
            score = 10
        elif is_restart:
            score = 15
        elif is_remediation or is_dataset or is_gov_observe or is_inspect or is_playbook or is_run_command:
            score = 20
        elif is_review:
            score = 30
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90

    if score >= 50 and is_query_source:
        score = max(score, 90)
    elif score >= 50 and is_query_knowledge:
        score = max(score, 80)
    elif is_review:
        score = min(score, 30)
    elif is_run_command:
        score = min(score, 5 if status in {"prepared", "not_started", "restart_available"} else 15)
    elif command_text:
        score = min(score, 25)
    return score, lowered


def prioritize_action_entries(
    entries: list[dict[str, Any]],
    *,
    execution_state: Optional[str],
    resume_status: Optional[str] = None,
    worknet_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    ordered = sorted(
        [
            (index, item)
            for index, item in enumerate(entries)
            if isinstance(item, dict) and str(item.get("label") or "").strip()
        ],
        key=lambda pair: (
            action_priority_key(
                execution_state,
                resume_status,
                label=pair[1].get("label"),
                command=str(pair[1].get("command") or "").strip() or None,
                worknet_key=worknet_key,
            ),
            pair[0],
        ),
    )
    return [dict(item) for _, item in ordered]
