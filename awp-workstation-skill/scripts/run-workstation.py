#!/usr/bin/env python3
"""Run or plan the workstation loop."""

import argparse

from awp_workstation_lib import print_json, run_workstation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="autopilot", help="Execution mode.")
    parser.add_argument("--worknet", help="Worknet key, alias, or ID.")
    parser.add_argument("--playbook", help="Path to an existing playbook JSON file.")
    parser.add_argument("--follow-up-label", help="Execute or queue one saved runtime follow-up action by label.")
    parser.add_argument("--confirm-label", help="Confirm one queued value-bearing action by label.")
    parser.add_argument("--background-label", help="Inspect one active background task by label.")
    parser.add_argument("--stop-background-label", help="Stop one active background task by label.")
    parser.add_argument("--pause", action="store_true", help="Stop the default active background task when exactly one is running.")
    parser.add_argument("--tail-lines", type=int, default=40, help="How many log lines to show when inspecting a background task.")
    parser.add_argument("--auto-advance", action="store_true", help="After a successful safe step, auto-run one default follow-up when available.")
    parser.add_argument("--input", action="append", help="Parameter override in key=value form for queued actions.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute non-confirmation commands instead of planning only.",
    )
    args = parser.parse_args()
    print_json(
        run_workstation(
            mode=args.mode,
            worknet_identifier=args.worknet,
            playbook_path=args.playbook,
            follow_up_label=args.follow_up_label,
            confirm_label=args.confirm_label,
            background_label=args.background_label,
            stop_background_label=args.stop_background_label,
            pause=args.pause,
            tail_lines=args.tail_lines,
            auto_advance=args.auto_advance,
            provided_inputs=args.input,
            execute=args.execute,
        )
    )


if __name__ == "__main__":
    main()
