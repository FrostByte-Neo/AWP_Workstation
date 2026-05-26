"""Runtime probe execution and display-support helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from awp_workstation.runtime import command_exists, parse_json_loose, run_command, trim_output


def command_probe_available(command: dict[str, Any]) -> bool:
    argv = command.get("argv")
    if not isinstance(argv, list) or not argv:
        return False
    cwd = command.get("cwd")
    head = str(argv[0])
    if os.path.isabs(head):
        return Path(head).exists()
    if head == "python3":
        if len(argv) < 2:
            return command_exists("python3")
        script = Path(str(argv[1]))
        if script.is_absolute():
            return script.exists()
        if cwd:
            return (Path(str(cwd)) / script).exists()
        return script.exists()
    return command_exists(head)


def run_inspection_probe(command: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    argv = [str(item) for item in command.get("argv", [])]
    cwd = command.get("cwd")
    result = run_command(argv, cwd=str(cwd) if cwd else None, timeout=timeout)
    combined = "\n".join(part for part in [result.get("stdout", ""), result.get("stderr", "")] if part)
    payload = parse_json_loose(result.get("stdout", ""))
    return {
        "label": command.get("label"),
        "argv": argv,
        "cwd": cwd,
        "ok": result.get("ok", False),
        "code": result.get("code"),
        "result": payload if isinstance(payload, (dict, list)) else None,
        "text": trim_output(combined, limit=1200),
    }


def contains_non_ascii_text(text: Any) -> bool:
    return bool(re.search(r"[^\x00-\x7f]", str(text or "")))


def should_replace_display_text(current: Any, candidate: Any) -> bool:
    current_text = str(current or "").strip()
    candidate_text = str(candidate or "").strip()
    if not candidate_text:
        return False
    if not current_text:
        return True
    if current_text == candidate_text:
        return True
    return contains_non_ascii_text(candidate_text) and not contains_non_ascii_text(current_text)


def probe_failures_are_network_only(probe_results: list[dict[str, Any]]) -> bool:
    failed = [item for item in probe_results if isinstance(item, dict) and item.get("ok") is False]
    if not failed:
        return False
    for item in failed:
        result = item.get("result")
        if isinstance(result, dict):
            code = str(result.get("error") or result.get("title") or "")
            if code == "NETWORK_ERROR":
                continue
        text = str(item.get("text", ""))
        if "NETWORK_ERROR" in text or "Name or service not known" in text:
            continue
        return False
    return True


def probe_failures_are_expected_state(probe_results: list[dict[str, Any]]) -> bool:
    failed = [item for item in probe_results if isinstance(item, dict) and item.get("ok") is False]
    if not failed:
        return False
    for item in failed:
        result = item.get("result")
        if not isinstance(result, dict):
            return False
        code = str(result.get("error") or result.get("title") or result.get("error_code") or "")
        if not code:
            return False
        if code in {"NETWORK_ERROR"}:
            return False
    return True


def runtime_probe_blockers(skill_key: str, inspection: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    probe_results = inspection.get("probeResults", []) if isinstance(inspection, dict) else []
    if skill_key == "predict":
        for item in probe_results:
            if not isinstance(item, dict) or item.get("label") != "predict stake eligibility":
                continue
            result = item.get("result")
            if not isinstance(result, dict):
                continue
            error = result.get("error")
            if isinstance(error, dict):
                suggestion = error.get("suggestion")
                if suggestion:
                    blockers.append(str(suggestion))
                else:
                    user_message = result.get("user_message")
                    if user_message:
                        blockers.append(str(user_message).splitlines()[0])
    if skill_key == "gov":
        for item in probe_results:
            if not isinstance(item, dict) or item.get("label") != "gov private state":
                continue
            result = item.get("result")
            if not isinstance(result, dict):
                continue
            code = str(result.get("error") or result.get("title") or "")
            detail = str(result.get("detail") or "")
            if code == "STATE_PRINCIPAL_NOT_IN_EPOCH":
                blockers.append("Principal has no AWP Power this epoch, so Gov signed actions are blocked until stake or power is available.")
            elif detail:
                blockers.append(detail)
    if skill_key == "ardi":
        for item in probe_results:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            result = item.get("result")
            if not isinstance(result, dict):
                continue
            if label == "ardi gas check" and result.get("status") == "error":
                suggestion = result.get("data", {}).get("suggestion") if isinstance(result.get("data"), dict) else None
                if suggestion:
                    blockers.append(str(suggestion))
                else:
                    blockers.append("Ardi requires Base gas before commits and reveals can start")
            if label == "ardi stake guidance" and result.get("status") == "error":
                suggestion = result.get("data", {}).get("suggestion") if isinstance(result.get("data"), dict) else None
                if suggestion:
                    blockers.append(str(suggestion))
                else:
                    blockers.append("Ardi requires either KYA delegated stake or a self-staked 10000 AWP path before commits can start")
    return blockers


def humanize_capability_reason_part(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return raw
    replacements = {
        "official runtime checkout is installed locally": "Official runtime checkout is installed locally.",
        "official install URI known, but runtime not installed locally": "Official install URI is known, but the runtime is not installed locally.",
        "no verified local runtime found": "No verified local runtime was found.",
        "runtime probe failed": "Runtime probe failed.",
        "runtime exists but still needs bootstrap before safe execution": "Runtime exists but still needs bootstrap before safe execution.",
        "workstation only has remote runtime guidance, not a local install": "Workstation only has remote runtime guidance, not a local install.",
        "local runtime is present, but its live probes are blocked by the current network environment": "Local runtime is present, but live probes are blocked by the current network environment.",
        "official runtime checkout currently only exposes license or metadata files, so there is nothing safe to auto-run yet": "Official runtime checkout currently only exposes license or metadata files, so there is nothing safe to auto-run yet.",
        "Predict can start with virtual chips now; staking remains an enhancement path rather than a hard prerequisite for the loop": "Predict can start with virtual chips now; staking is an enhancement path, not a hard prerequisite for the loop.",
        "If you want the stake-backed path later, use the official staking or KYA route and then re-run Predict stake checks": "For the stake-backed path, use the official staking or KYA route and then re-run Predict stake checks.",
        "stake gate still blocks submissions until 1000 AWP or KYA delegated eligibility is satisfied": "Stake gate blocks submissions until 1000 AWP or KYA delegated eligibility is satisfied.",
        "Principal has no AWP Power this epoch, so Gov signed actions are blocked until stake/power is available": "Principal has no AWP Power this epoch, so Gov signed actions are blocked until stake or power is available.",
        "Ardi requires Base gas before commits and reveals can start": "Ardi requires Base gas before commits and reveals can start.",
        "Ardi requires either KYA delegated stake or a self-staked 10000 AWP path before commits can start": "Ardi requires either KYA delegated stake or a self-staked 10000 AWP path before commits can start.",
    }
    if raw in replacements:
        return replacements[raw]
    local_prefix = "local source present at "
    if raw.startswith(local_prefix):
        return f"Local source present at {raw[len(local_prefix):]}"
    probe_prefix = "runtime probe failed for "
    if raw.startswith(probe_prefix):
        return f"Runtime probe failed for {raw[len(probe_prefix):]}"
    observe_prefix = "user preference still suggests observing Predict outcomes for the first "
    observe_suffix = " hours even though the official loop can start now"
    if raw.startswith(observe_prefix) and raw.endswith(observe_suffix):
        hours = raw[len(observe_prefix):-len(observe_suffix)]
        return f"Predict can start now, but user preferences request observing outcomes for {hours} hours first."
    if raw.startswith("Send at least ") and " ETH to " in raw and " on Base" in raw:
        try:
            amount = raw.split("Send at least ", 1)[1].split(" ETH to ", 1)[0].strip()
            address = raw.split(" ETH to ", 1)[1].split(" on Base", 1)[0].strip()
            return f"Send at least {amount} ETH to {address} on Base before running Ardi gas-dependent actions."
        except Exception:
            return "Fund the Base wallet before running Ardi gas-dependent actions."
    if raw.startswith("Reach the 10000 AWP threshold on EITHER Ardi"):
        return "Reach the 10000 AWP threshold through Ardi or KYA before running Ardi commits."
    return raw
