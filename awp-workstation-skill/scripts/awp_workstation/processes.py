"""Background process registry and process-control helpers."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from awp_workstation.commands import render_argv
from awp_workstation.runtime import parse_json_loose, run_command, trim_output
from awp_workstation.storage import atomic_write_json, load_json
from awp_workstation.utils import now_iso, safe_slug


BACKGROUND_PROCESS_HANDLES: dict[int, subprocess.Popen[Any]] = {}


def active_processes_path(state: dict[str, Any]) -> Path:
    return Path(state["runs"]) / "active-processes.json"


def process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def forget_background_process_handle(pid: int) -> None:
    handle = BACKGROUND_PROCESS_HANDLES.pop(pid, None)
    if handle is None:
        return
    try:
        handle.poll()
    except OSError:
        pass


def load_active_processes(state: dict[str, Any]) -> list[dict[str, Any]]:
    path = active_processes_path(state)
    records = load_json(path, [])
    if not isinstance(records, list):
        return []
    alive: list[dict[str, Any]] = []
    changed = False
    for item in records:
        if not isinstance(item, dict):
            changed = True
            continue
        if str(item.get("kind") or "") == "managed-external":
            if item.get("stoppedAt"):
                changed = True
                continue
            alive.append(item)
            continue
        pid = item.get("pid")
        if isinstance(pid, int) and process_is_alive(pid):
            alive.append(item)
        else:
            changed = True
    if changed:
        atomic_write_json(path, alive)
    return alive


def register_active_process(state: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    active = load_active_processes(state)
    label = str(record.get("label") or "")
    external_session_id = str(record.get("externalSessionId") or "")
    updated: list[dict[str, Any]] = []
    replaced = False
    for item in active:
        if not isinstance(item, dict):
            continue
        same_label = label and str(item.get("label") or "") == label
        same_external_session = (
            external_session_id
            and str(item.get("externalSessionId") or "") == external_session_id
        )
        if same_label or same_external_session:
            updated.append({**item, **record})
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(record)
    active = updated
    atomic_write_json(active_processes_path(state), active)
    return active


def tail_text(path: Optional[str], lines: int = 40) -> list[str]:
    if not path:
        return []
    target = Path(path)
    if not target.exists():
        return []
    try:
        content = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return content[-lines:]


def summarize_background_log(record: dict[str, Any], log_tail: list[str]) -> dict[str, Any]:
    label = str(record.get("label") or "")
    normalized_label = label.strip()
    argv = [str(item) for item in record.get("argv", [])] if isinstance(record.get("argv"), list) else []
    summary = {
        "state": "running",
        "headline": "Background process is running.",
        "detail": log_tail[-1] if log_tail else None,
    }
    if (
        (normalized_label.startswith("Predict") and "loop" in normalized_label.lower())
        or (argv[:2] == ["predict-agent", "loop"])
    ):
        persona = None
        target = None
        last_wait = None
        for line in log_tail:
            text = line.strip()
            if "persona=" in text and "timeslot=" in text:
                persona = text
            if "target=" in text:
                target = text
            if "sleeping " in text:
                last_wait = text
        for line in reversed(log_tail):
            text = line.strip()
            if "failed to parse LLM response" in text or "LLM call failed" in text:
                return {
                    "state": "llm_error",
                    "headline": "Predict loop hit an LLM error.",
                    "detail": text,
                    "personaLine": persona,
                    "targetLine": target,
                }
            if "no submittable markets" in text:
                return {
                    "state": "waiting_for_market",
                    "headline": "Predict loop is waiting for a submittable market.",
                    "detail": text,
                    "personaLine": persona,
                }
            if "calling LLM via openclaw" in text:
                return {
                    "state": "llm_running",
                    "headline": "Predict loop is calling the LLM.",
                    "detail": target or text,
                    "personaLine": persona,
                    "targetLine": target,
                }
            if "got challenge nonce=" in text:
                return {
                    "state": "challenge_ready",
                    "headline": "Predict loop received a challenge nonce.",
                    "detail": text,
                    "personaLine": persona,
                    "targetLine": target,
                }
            if "balance=" in text and "persona=" in text:
                return {
                    "state": "iteration_started",
                    "headline": "Predict loop started an iteration.",
                    "detail": text,
                    "personaLine": persona,
                }
            if "starting (interval=" in text:
                return {
                    "state": "starting",
                    "headline": "Predict loop is starting.",
                    "detail": text,
                }
        if last_wait:
            summary["detail"] = last_wait
    return summary


def find_active_process(state: dict[str, Any], label: str) -> Optional[dict[str, Any]]:
    for item in load_active_processes(state):
        if isinstance(item, dict) and str(item.get("label")) == label:
            return item
    return None


def remove_active_process(state: dict[str, Any], label: str) -> list[dict[str, Any]]:
    active = [
        item for item in load_active_processes(state)
        if not (isinstance(item, dict) and str(item.get("label")) == label)
    ]
    atomic_write_json(active_processes_path(state), active)
    return active


def record_command_argv(record: dict[str, Any], key: str) -> Optional[list[str]]:
    value = record.get(key)
    if isinstance(value, list) and value:
        return [str(item) for item in value]
    return None


def stop_background_process(
    state: dict[str, Any],
    label: str,
    *,
    execute: bool,
    prefer_pause: bool = False,
    sigkill_after_seconds: float = 2.0,
) -> dict[str, Any]:
    record = find_active_process(state, label)
    if record is None:
        raise ValueError(f"unknown background label: {label}")
    if str(record.get("kind") or "") == "managed-external":
        pause_argv = record_command_argv(record, "pauseArgv")
        stop_argv = pause_argv if prefer_pause and pause_argv else record_command_argv(record, "stopArgv")
        preview = {
            "label": label,
            "kind": "managed-external",
            "externalSessionId": record.get("externalSessionId"),
            "stopCommand": render_argv(stop_argv) if stop_argv else None,
            "alive": True,
        }
        if not execute:
            return {
                "status": "needs_confirmation",
                "selectedBackground": preview,
                "activeBackgroundProcesses": load_active_processes(state),
            }
        if not stop_argv:
            preview["error"] = "managed external task does not expose a stop command"
            return {
                "status": "failed",
                "selectedBackground": preview,
                "activeBackgroundProcesses": load_active_processes(state),
            }
        result = run_command(stop_argv, cwd=str(record.get("cwd")) if record.get("cwd") else None)
        preview["result"] = {
            "ok": result.get("ok"),
            "code": result.get("code"),
            "stdout": trim_output(parse_json_loose(result.get("stdout", ""))),
            "stderr": trim_output(result.get("stderr", "")),
        }
        if result.get("ok"):
            remaining = remove_active_process(state, label)
            preview["alive"] = False
            return {
                "status": "stopped",
                "selectedBackground": preview,
                "activeBackgroundProcesses": remaining,
            }
        return {
            "status": "failed",
            "selectedBackground": preview,
            "activeBackgroundProcesses": load_active_processes(state),
        }
    pid = record.get("pid")
    preview = {
        "label": label,
        "pid": pid,
        "logPath": record.get("logPath"),
        "stopCommand": f"kill -TERM {pid}" if isinstance(pid, int) else None,
        "alive": process_is_alive(pid) if isinstance(pid, int) else False,
    }
    if not execute or not isinstance(pid, int):
        return {
            "status": "needs_confirmation",
            "selectedBackground": preview,
            "activeBackgroundProcesses": load_active_processes(state),
        }
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        preview["error"] = str(exc)
        return {
            "status": "failed",
            "selectedBackground": preview,
            "activeBackgroundProcesses": load_active_processes(state),
        }
    deadline = time.time() + sigkill_after_seconds
    while time.time() < deadline and process_is_alive(pid):
        time.sleep(0.1)
    if process_is_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    forget_background_process_handle(pid)
    remaining = remove_active_process(state, label)
    preview["alive"] = process_is_alive(pid)
    return {
        "status": "stopped" if not preview["alive"] else "stop_requested",
        "selectedBackground": preview,
        "activeBackgroundProcesses": remaining,
    }


def launch_background_command(
    argv: list[str],
    *,
    cwd: Optional[str],
    state: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    log_dir = Path(state["runs"]) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    slug = safe_slug(label) or "background-task"
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    log_path = log_dir / f"{slug}-{stamp}.log"
    with log_path.open("ab") as handle:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    record = {
        "label": label,
        "argv": [str(item) for item in argv],
        "cwd": cwd,
        "pid": process.pid,
        "logPath": str(log_path),
        "startedAt": now_iso(),
    }
    BACKGROUND_PROCESS_HANDLES[process.pid] = process
    register_active_process(state, record)
    return record
