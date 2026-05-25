"""Preflight and onboarding report builders."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional


def runtime_probe_payload(
    state: Optional[dict[str, Any]] = None,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("runtime probe dependencies are required")
    command_exists = dependencies["command_exists"]
    command_help_probe = dependencies["command_help_probe"]
    now_iso = dependencies["now_iso"]
    shutil = dependencies["shutil"]
    state_context = dependencies["state_context"]

    state = state or state_context()
    managed_root = Path(state["skills"]) / "checkouts"
    awp_skill_root = managed_root / "awp-skill"
    awp_wallet_root = managed_root / "awp-wallet"
    generic_skill_path = shutil.which("skill")
    generic_skill_probe = None
    generic_skill_kind = None
    if generic_skill_path:
        generic_skill_probe = command_help_probe(["skill", "--help"])
        text = str(generic_skill_probe.get("text", "")).lower()
        if "expression can be" in text or "signal" in text or "kill processes" in text:
            generic_skill_kind = "linux-process-skill"
        else:
            generic_skill_kind = "unknown-skill-command"

    relay_start = awp_skill_root / "scripts" / "relay-start.py"
    awp_daemon = awp_skill_root / "scripts" / "awp-daemon.py"
    relay_probe = None
    daemon_probe = None
    if relay_start.exists():
        relay_probe = command_help_probe(["python3", str(relay_start), "--help"])
    if awp_daemon.exists():
        daemon_probe = command_help_probe(["python3", str(awp_daemon), "--help"])

    return {
        "generatedAt": now_iso(),
        "gitAvailable": command_exists("git"),
        "python3Available": command_exists("python3"),
        "awpWalletCli": {
            "available": command_exists("awp-wallet"),
            "path": shutil.which("awp-wallet"),
        },
        "awpSkillCli": {
            "available": command_exists("awp-skill"),
            "path": shutil.which("awp-skill"),
        },
        "genericSkillCommand": {
            "available": bool(generic_skill_path),
            "path": generic_skill_path,
            "kind": generic_skill_kind,
            "probe": generic_skill_probe,
        },
        "managedCheckouts": {
            "root": str(managed_root),
            "awpSkill": {
                "path": str(awp_skill_root),
                "exists": awp_skill_root.exists(),
                "relayStartExists": relay_start.exists(),
                "awpDaemonExists": awp_daemon.exists(),
                "relayHelp": relay_probe,
                "daemonHelp": daemon_probe,
            },
            "awpWallet": {
                "path": str(awp_wallet_root),
                "exists": awp_wallet_root.exists(),
            },
        },
    }


def build_registration_plan_payload(
    state: Optional[dict[str, Any]] = None,
    wallet: Optional[dict[str, Any]] = None,
    *,
    include_probe: bool = True,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build registration plan dependencies are required")
    awp_wallet_snapshot = dependencies["awp_wallet_snapshot"]
    build_dependency_command = dependencies["build_dependency_command"]
    now_iso = dependencies["now_iso"]
    run_awp_skill_preflight = dependencies["run_awp_skill_preflight"]
    runtime_probe = dependencies["runtime_probe"]
    state_context = dependencies["state_context"]

    state = state or state_context()
    wallet = wallet or awp_wallet_snapshot()
    probe = runtime_probe(state) if include_probe else {}
    official_preflight = (
        run_awp_skill_preflight(state=state, address=wallet.get("address"))
        if include_probe and wallet.get("address")
        else {"available": False, "result": None}
    )
    managed_awp_skill = Path(probe.get("managedCheckouts", {}).get("awpSkill", {}).get("path", ""))
    relay_start = managed_awp_skill / "scripts" / "relay-start.py"

    commands: list[dict[str, Any]] = []
    issues: list[str] = []
    next_action = "install_awp_skill_dependency"

    if not wallet.get("walletReady"):
        issues.append("agent work wallet is not ready")
    if not probe.get("gitAvailable"):
        issues.append("git is not available for managed dependency checkout")
    if probe.get("genericSkillCommand", {}).get("kind") == "linux-process-skill":
        issues.append("system `skill` command is a Linux process-signal utility, not an AWP skill runtime")

    if not probe.get("managedCheckouts", {}).get("awpSkill", {}).get("exists"):
        commands.append(
            build_dependency_command(
                "awp-skill",
                "https://github.com/awp-core/awp-skill",
            )
        )
    elif relay_start.exists():
        commands.append(
            {
                "label": "run awp-skill gasless onboarding",
                "cwd": str(managed_awp_skill),
                "argv": ["python3", str(relay_start), "--mode", "principal"],
                "category": "registration",
                "requires_confirmation": False,
            }
        )
        next_action = "run_awp_skill_registration"
    else:
        issues.append("managed awp-skill checkout exists but relay-start.py was not found")

    if not commands and not issues:
        next_action = "registration_ready"

    plan = {
        "generatedAt": now_iso(),
        "walletReady": wallet.get("walletReady", False),
        "agentAddress": wallet.get("address"),
        "nextAction": next_action,
        "issues": issues,
        "commands": commands,
        "runtimeProbe": probe,
        "awpSkillPreflight": official_preflight,
    }
    preflight_result = official_preflight.get("result") if isinstance(official_preflight, dict) else None
    if isinstance(preflight_result, dict):
        plan["officialNextAction"] = preflight_result.get("nextAction")
        plan["officialMessage"] = preflight_result.get("message")
        if preflight_result.get("nextAction") == "retry_preflight":
            issue = "official awp-skill preflight could not reach the AWP API"
            if issue not in plan["issues"]:
                plan["issues"].append(issue)
            if plan["nextAction"] == "run_awp_skill_registration":
                plan["nextAction"] = "retry_registration_preflight"
    return plan


def build_preflight_report_payload(
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build preflight report dependencies are required")
    atomic_write_json = dependencies["atomic_write_json"]
    awp_wallet_snapshot = dependencies["awp_wallet_snapshot"]
    build_capability_bundle = dependencies["build_capability_bundle"]
    build_knowledge_review_queue = dependencies["build_knowledge_review_queue"]
    build_preflight_plain_language_summary = dependencies["build_preflight_plain_language_summary"]
    build_recovery_decision = dependencies["build_recovery_decision"]
    build_recovery_state = dependencies["build_recovery_state"]
    build_registration_plan = dependencies["build_registration_plan"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    load_cached_capability_bundle = dependencies["load_cached_capability_bundle"]
    load_cached_knowledge_review_queue = dependencies["load_cached_knowledge_review_queue"]
    load_json = dependencies["load_json"]
    probe_cached_official_registration = dependencies["probe_cached_official_registration"]
    probe_registration = dependencies["probe_registration"]
    resolve_worknet = dependencies["resolve_worknet"]
    state_context = dependencies["state_context"]
    summarize_knowledge_review_queue = dependencies["summarize_knowledge_review_queue"]

    state = state_context()
    preferences = ensure_user_preferences(state)
    wallet = awp_wallet_snapshot()
    registration_plan = build_registration_plan(state=state, wallet=wallet)
    recovery = build_recovery_state(state)
    recovery_decision = build_recovery_decision(
        recovery,
        worknet_name=str(recovery.get("lastWorknetKey") or ""),
        preferred_profile=resolve_worknet(str(preferences.get("preferredWorknet") or "")),
    )
    cached_registered, cached_recipient, cached_official = probe_cached_official_registration(state)
    cached_preflight = load_json(Path(state["cache"]) / "preflight.json", {})
    cached_bundle = load_cached_capability_bundle(state)
    knowledge_review_queue = load_cached_knowledge_review_queue(state) or build_knowledge_review_queue(state=state)
    knowledge_review_queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
    fast_resume_mode = bool(
        recovery.get("pendingConfirmations")
        or recovery.get("activeBackgroundCount")
        or (recovery.get("hasRuntimeGuidance") and recovery.get("followUpActionCount"))
    )
    bundle: Optional[dict[str, Any]] = None
    registered: Optional[bool] = None
    recipient: Optional[str] = None
    registration_issues: list[str] = []
    rpc_source_mode = None
    missing_managed_skills: list[str] = []
    if fast_resume_mode and isinstance(cached_preflight, dict):
        registered = cached_preflight.get("registered")
        recipient = cached_preflight.get("recipient")
        rpc_source_mode = cached_preflight.get("rpcSourceMode")
        missing_managed_skills = list(cached_preflight.get("missingManagedSkills", []))
    if not missing_managed_skills and isinstance(cached_bundle, dict):
        rpc_source_mode = rpc_source_mode or cached_bundle.get("sourceMode")
        missing_managed_skills = [
            item["key"]
            for item in cached_bundle.get("skillRegistry", [])
            if isinstance(item, dict) and item.get("status") in {"official-remote", "missing"}
        ]
    if registered not in {True, False} and cached_registered in {True, False} and (
        fast_resume_mode or isinstance(cached_bundle, dict)
    ):
        registered = cached_registered
        recipient = cached_recipient
        if rpc_source_mode is None and isinstance(cached_bundle, dict):
            rpc_source_mode = cached_bundle.get("sourceMode")
    if registered not in {True, False}:
        bundle = build_capability_bundle()
        registered, recipient, registration_issues = probe_registration(bundle, wallet.get("address"))
        rpc_source_mode = bundle["sourceMode"]
        missing_managed_skills = [
            item["key"]
            for item in bundle.get("skillRegistry", [])
            if isinstance(item, dict) and item.get("status") in {"official-remote", "missing"}
        ]
    elif rpc_source_mode is None:
        rpc_source_mode = "cached"
    registered_source = "rpc" if registered in {True, False} else None
    if registered is None and cached_registered in {True, False}:
        registered = cached_registered
        recipient = cached_recipient
        registered_source = "awp-skill-cache"
    blocking_issues: list[str] = []
    registration_runtime_needed = registered in {False, None}
    if not wallet.get("installed"):
        blocking_issues.append("awp-wallet is not installed")
    if wallet.get("installed") and not wallet.get("walletReady"):
        blocking_issues.append("awp-wallet did not return an agent address")
    blocking_issues.extend(registration_issues)
    if registration_runtime_needed:
        blocking_issues.extend(
            issue
            for issue in registration_plan.get("issues", [])
            if issue not in blocking_issues
        )
    if registered is True:
        registration_plan["nextAction"] = "registration_already_confirmed"
        if cached_official and isinstance(cached_official, dict):
            cached_result = cached_official.get("result", {})
            if isinstance(cached_result, dict):
                registration_plan["officialNextAction"] = cached_result.get("nextAction")
                registration_plan["officialMessage"] = cached_result.get("message")
        registration_plan["issues"] = [
            issue
            for issue in registration_plan.get("issues", [])
            if issue != "official awp-skill preflight could not reach the AWP API"
        ]
        blocking_issues = [
            issue
            for issue in blocking_issues
            if "registration status is unknown" not in issue
            and "official awp-skill preflight could not reach the AWP API" not in issue
        ]
    if recovery.get("pendingConfirmations"):
        next_action = "resume_pending_confirmations"
    elif recovery.get("activeBackgroundCount"):
        next_action = "monitor_background_runs"
    elif recovery.get("hasRuntimeGuidance") and recovery.get("followUpActionCount"):
        next_action = "resume_runtime_guidance"
    elif recovery.get("resumeAvailable") and recovery.get("hasLatestRun"):
        next_action = "resume_previous_run"
    elif not wallet.get("walletReady"):
        next_action = "install_or_setup_wallet"
    elif registered is False:
        next_action = registration_plan.get("nextAction", "register_agent")
    elif registered is None and registration_plan.get("commands"):
        next_action = registration_plan.get("nextAction", "prepare_registration_runtime")
    else:
        next_action = "scan_worknets"
    plain_language_summary = build_preflight_plain_language_summary(
        next_action,
        knowledge_review_queue_summary=knowledge_review_queue_summary,
        include_queue_note=True,
    )
    report = {
        "walletReady": wallet.get("walletReady", False),
        "registered": registered,
        "agentAddress": wallet.get("address"),
        "recipient": recipient,
        "nextAction": next_action,
        "blockingIssues": blocking_issues,
        "stateRoot": state["root"],
        "stateWarnings": state["warnings"],
        "stateBootstrap": state.get("bootstrap"),
        "rpcSourceMode": rpc_source_mode,
        "availableChains": wallet.get("chains"),
        "userPreferences": preferences,
        "recovery": recovery,
        "recoveryDecision": recovery_decision,
        "missingManagedSkills": missing_managed_skills,
        "knowledgeReviewQueueSummary": knowledge_review_queue_summary,
        "skillRegistryPath": str(Path(state["skills"]) / "install-status.json"),
        "registrationPlan": registration_plan,
        "awpSkillPreflight": registration_plan.get("awpSkillPreflight"),
        "registeredSource": registered_source,
        "cachedOfficialPreflight": cached_official,
        "plainLanguageSummary": plain_language_summary,
        "progress": "[1/5] Preflight",
    }
    atomic_write_json(Path(state["cache"]) / "preflight.json", report)
    return report

