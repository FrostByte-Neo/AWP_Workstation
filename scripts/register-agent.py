#!/usr/bin/env python3
"""Build or execute the workstation's best available AWP registration path."""

from __future__ import annotations

import argparse

from awp_workstation_lib import (
    build_registration_plan,
    print_json,
    run_command,
    trim_output,
    parse_json_loose,
    state_context,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Execute the first available registration-plan command.")
    args = parser.parse_args()

    state = state_context()
    plan = build_registration_plan(state=state)
    if not args.execute:
        print_json(plan)
        return

    if plan.get("nextAction") == "retry_registration_preflight":
        plan["execute"] = {
            "ok": False,
            "reason": "official awp-skill preflight says the AWP API is not reachable yet; retry preflight before executing registration",
        }
        print_json(plan)
        return

    commands = plan.get("commands", [])
    if not commands:
        plan["execute"] = {
            "ok": False,
            "reason": "no executable registration command is available yet",
        }
        print_json(plan)
        return

    command = commands[0]
    result = run_command(command["argv"], cwd=command.get("cwd"), timeout=300)
    plan["execute"] = {
        "label": command.get("label"),
        "ok": result.get("ok"),
        "code": result.get("code"),
        "stdout": trim_output(parse_json_loose(result.get("stdout", ""))),
        "stderr": trim_output(result.get("stderr", "")),
    }
    print_json(plan)


if __name__ == "__main__":
    main()
