"""Capability and wallet helper functions."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.execution_states import execution_state_display
from awp_workstation.reporting import knowledge_source_labels_text
from awp_workstation.runtime import command_exists, parse_json_loose, run_command
from awp_workstation.worknets import resolve_worknet


def awp_wallet_snapshot() -> dict[str, Any]:
    if not command_exists("awp-wallet"):
        return {
            "installed": False,
            "walletReady": False,
            "address": None,
            "receive": None,
            "status": None,
            "chains": None,
            "error": "awp-wallet not found in PATH",
        }
    status = run_command(["awp-wallet", "status"])
    receive = run_command(["awp-wallet", "receive"])
    chains = run_command(["awp-wallet", "chains"])
    status_payload = parse_json_loose(status["stdout"])
    receive_payload = parse_json_loose(receive["stdout"])
    chains_payload = parse_json_loose(chains["stdout"])
    address = None
    if isinstance(status_payload, dict):
        address = status_payload.get("address")
    if not address and isinstance(receive_payload, dict):
        address = receive_payload.get("eoaAddress") or receive_payload.get("address")
    return {
        "installed": True,
        "walletReady": bool(address),
        "address": address,
        "receive": receive_payload,
        "status": status_payload,
        "chains": chains_payload,
        "statusCommand": status,
        "receiveCommand": receive,
        "chainsCommand": chains,
        "error": None if address else "wallet address not detected",
    }


def infer_runnable(profile: dict[str, Any], local_source: Optional[dict[str, Any]]) -> bool:
    if local_source and local_source.get("available") and profile["key"] in {"mine", "kya"}:
        return True
    return False


def inspection_status_blocks_runtime(status: str) -> bool:
    return status in {
        "runtime-error",
        "installed-needs-bootstrap",
        "partial",
        "missing",
        "remote-profile-only",
        "network-blocked",
        "empty-official-repo",
    }


def inspection_status_enables_runtime(status: str) -> bool:
    return status == "ready"


def humanize_skill_inspection_status(status: Any) -> Optional[str]:
    code = str(status or "").strip().lower()
    if not code:
        return None
    mapping = {
        "ready": "Ready",
        "runtime-error": "Runtime error",
        "installed-needs-bootstrap": "Needs bootstrap",
        "partial": "Partial install",
        "missing": "Runtime missing",
        "remote-profile-only": "Remote profile only",
        "network-blocked": "Network blocked",
        "empty-official-repo": "Empty official repo",
    }
    return mapping.get(code, code)


def capability_knowledge_caveat(
    knowledge_context: Any,
    knowledge_source_highlights: Any = None,
) -> Optional[str]:
    if not isinstance(knowledge_context, dict):
        return None
    if str(knowledge_context.get("freshnessStatus") or "") != "affected":
        return None
    label = str(knowledge_context.get("label") or knowledge_context.get("key") or "WorkNet").strip()
    source_labels = knowledge_source_labels_text(
        knowledge_source_highlights,
        affected_only=True,
        limit=3,
    )
    if source_labels:
        return f"{label} needs source review before capability status is final. Sources: {source_labels}."
    return f"{label} needs source review before capability status is final."


def derive_capability_execution_state(report: Any) -> dict[str, Any]:
    report = report if isinstance(report, dict) else {}
    knowledge_context = report.get("knowledgeContext") if isinstance(report.get("knowledgeContext"), dict) else None
    knowledge_source_highlights = report.get("knowledgeSourceHighlights")
    caveat = capability_knowledge_caveat(knowledge_context, knowledge_source_highlights)
    name = str(report.get("name") or report.get("symbol") or report.get("worknetId") or "WorkNet").strip()
    cli_status = str(report.get("cliStatus") or "").strip()
    runnable = bool(report.get("runnable"))
    automation = str(report.get("automationLevel") or "").strip()
    role = str(report.get("recommendedRole") or "").strip()
    worknet_key = (
        str(report.get("worknetKey") or "").strip().lower()
        or str((resolve_worknet(str(report.get("worknetId") or "")) or {}).get("key") or "").strip().lower()
        or str((resolve_worknet(str(report.get("name") or "")) or {}).get("key") or "").strip().lower()
        or str((resolve_worknet(str(report.get("symbol") or "")) or {}).get("key") or "").strip().lower()
    )

    if caveat:
        execution_state = "review_required"
        headline = caveat
    elif worknet_key == "gov" and cli_status == "ready":
        execution_state = "observe_only"
        headline = f"{name} is ready for observation; signed Gov actions still need eligibility checks."
    elif worknet_key == "ardi" and cli_status == "ready" and not runnable:
        execution_state = "blocked"
        headline = f"{name} is blocked until gas or stake prerequisites are satisfied."
    elif role == "identity":
        execution_state = "manual_review"
        headline = f"{name} requires identity review."
    elif role == "observer" or automation == "manual-only":
        execution_state = "manual_review"
        headline = f"{name} requires manual review."
    elif cli_status == "ready" and runnable:
        execution_state = "ready_to_execute"
        headline = f"{name} is ready to execute."
    elif cli_status == "installed-needs-bootstrap":
        execution_state = "needs_runtime_setup"
        headline = f"{name} needs runtime bootstrap."
    elif cli_status == "partial":
        execution_state = "partial_ready"
        headline = f"{name} is partially ready and needs review."
    elif cli_status == "runtime-error":
        execution_state = "runtime_error"
        headline = f"{name} runtime reported an error."
    elif cli_status == "network-blocked":
        execution_state = "network_blocked"
        headline = f"{name} runtime probes are blocked by the network."
    elif cli_status in {"remote-profile-only", "empty-official-repo"}:
        execution_state = "manual_review"
        headline = f"{name} needs manual review before execution."
    elif runnable:
        execution_state = "prepared"
        headline = f"{name} is prepared."
    else:
        execution_state = "needs_runtime_setup"
        headline = f"{name} needs runtime setup."
    return {
        "executionState": execution_state,
        "executionStateDisplay": execution_state_display(execution_state),
        "executionHeadline": headline,
    }


def knowledge_topic_execution_state(
    *,
    label: str,
    affected: bool,
    capability_report: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if affected:
        return {
            "executionState": "review_required",
            "executionStateDisplay": execution_state_display("review_required"),
            "executionHeadline": f"{label} needs source review before execution.",
        }
    if isinstance(capability_report, dict):
        return derive_capability_execution_state(capability_report)
    return {
        "executionState": None,
        "executionStateDisplay": None,
        "executionHeadline": None,
    }
