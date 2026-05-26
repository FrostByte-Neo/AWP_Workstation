#!/usr/bin/env python3
"""Answer user-facing workstation status questions in JSON."""

import argparse

from awp_workstation_lib import (
    build_timeline_view,
    build_workstation_monitor,
    build_workstation_status,
    print_json,
    public_workstation_status_view,
    workstation_actions_only_view,
    workstation_monitor_view,
    workstation_status_brief_view,
    workstation_timeline_view,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", help="Free-form user question such as 'what is running', 'research Mine', or 'pause current work'.")
    parser.add_argument(
        "--intent",
        choices=[
            "status",
            "research",
            "earnings",
            "failures",
            "pause",
            "continue",
            "switch-worknet",
            "safety",
            "review-queue",
        ],
        help="Optional explicit intent override.",
    )
    parser.add_argument("--worknet", help="Optional target worknet key, alias, or ID.")
    parser.add_argument("--source-key", help="Optional target source key or source label such as awp-skill or community-skill.")
    parser.add_argument("--read-only", action="store_true", help="Use cached status data only; do not rebuild caches or write status output.")
    parser.add_argument("--brief", action="store_true", help="Emit a short one-line status contract.")
    parser.add_argument("--actions-only", action="store_true", help="Emit only the next actions and commands.")
    parser.add_argument("--timeline", action="store_true", help="Emit the recent timeline event stream instead of the status report.")
    parser.add_argument("--monitor", action="store_true", help="Emit the monitor judgement view instead of the status report.")
    parser.add_argument("--timeline-limit", type=int, default=20, help="How many recent timeline events to return.")
    parser.add_argument("--full", action="store_true", help="Emit the full internal briefing record.")
    args = parser.parse_args()

    if args.timeline and args.monitor:
        parser.error("--timeline cannot be combined with --monitor")

    if args.monitor:
        monitor = build_workstation_monitor(
            read_only=args.read_only,
            timeline_limit=args.timeline_limit,
        )
        print_json(monitor if args.full else workstation_monitor_view(monitor))
        return

    if args.timeline:
        timeline = build_timeline_view(limit=args.timeline_limit)
        print_json(timeline if args.full else workstation_timeline_view(timeline))
        return

    report = build_workstation_status(
        query=args.query,
        intent=args.intent,
        worknet_identifier=args.worknet,
        source_identifier=args.source_key,
        read_only=args.read_only,
    )
    if args.full:
        print_json(report)
    elif args.actions_only:
        print_json(workstation_actions_only_view(report))
    elif args.brief:
        print_json(workstation_status_brief_view(report))
    else:
        print_json(public_workstation_status_view(report))


if __name__ == "__main__":
    main()
