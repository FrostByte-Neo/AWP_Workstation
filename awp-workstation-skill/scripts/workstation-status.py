#!/usr/bin/env python3
"""Answer user-facing workstation status questions in JSON."""

import argparse

from awp_workstation_lib import (
    build_workstation_status,
    print_json,
    public_workstation_status_view,
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
    parser.add_argument("--full", action="store_true", help="Emit the full internal briefing record.")
    args = parser.parse_args()
    report = build_workstation_status(
        query=args.query,
        intent=args.intent,
        worknet_identifier=args.worknet,
        source_identifier=args.source_key,
        read_only=args.read_only,
    )
    print_json(report if args.full else public_workstation_status_view(report))


if __name__ == "__main__":
    main()
