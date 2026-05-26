#!/usr/bin/env python3
"""Ensure an official AWP skill checkout exists under workstation state."""

from __future__ import annotations

import argparse
from pathlib import Path

from awp_workstation_lib import (
    atomic_write_json,
    looks_official_skill_uri,
    now_iso,
    print_json,
    run_command,
    safe_slug,
    state_context,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-key", required=True, help="Logical skill key, such as gov or ardi.")
    parser.add_argument("--uri", required=True, help="Git URI for the skill checkout.")
    parser.add_argument(
        "--mode",
        default="ensure",
        choices=["ensure", "status"],
        help="Ensure the checkout exists or only report current status.",
    )
    args = parser.parse_args()

    state = state_context()
    managed_root = Path(state["skills"]) / "checkouts"
    managed_root.mkdir(parents=True, exist_ok=True)
    target = managed_root / safe_slug(args.skill_key)

    if not looks_official_skill_uri(args.uri):
        payload = {
            "ok": False,
            "skillKey": args.skill_key,
            "uri": args.uri,
            "status": "rejected",
            "reason": "only official github.com/awp-worknet/* skill URIs can be auto-managed",
            "managedPath": str(target),
            "generatedAt": now_iso(),
        }
        print_json(payload)
        return

    git_dir = target / ".git"
    operation = None
    command_result = None

    if args.mode == "ensure":
        if git_dir.exists():
            operation = "pull"
            command_result = run_command(["git", "-C", str(target), "pull", "--ff-only"], timeout=300)
        else:
            operation = "clone"
            command_result = run_command(["git", "clone", args.uri, str(target)], timeout=300)

    payload = {
        "ok": True if command_result is None else bool(command_result.get("ok")),
        "skillKey": args.skill_key,
        "uri": args.uri,
        "mode": args.mode,
        "operation": operation,
        "status": "managed-installed" if git_dir.exists() or (command_result and command_result.get("ok")) else "official-remote",
        "managedPath": str(target),
        "generatedAt": now_iso(),
    }
    if command_result is not None:
        payload["command"] = {
            "code": command_result.get("code"),
            "stdout": command_result.get("stdout"),
            "stderr": command_result.get("stderr"),
        }
        if not command_result.get("ok"):
            payload["reason"] = "git clone/pull failed; network approval or a reachable upstream may be required"

    atomic_write_json(Path(state["skills"]) / f"{safe_slug(args.skill_key)}-last-sync.json", payload)
    print_json(payload)


if __name__ == "__main__":
    main()
