#!/usr/bin/env python3
"""Evaluate whether the workstation should notify the user."""

import argparse

from awp_workstation_lib import (
    build_workstation_monitor,
    dispatch_workstation_notification,
    print_json,
    record_workstation_monitor_delivery,
    workstation_monitor_view,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--read-only", action="store_true", help="Use cached state only and do not refresh status or review caches.")
    parser.add_argument("--timeline-limit", type=int, default=12, help="How many recent timeline events to embed in the monitor payload.")
    parser.add_argument(
        "--emit-adapter",
        choices=["codex-heartbeat", "cron", "desktop", "telegram-webhook", "discord-webhook", "email"],
        help="Optional notification adapter to emit after monitor evaluation.",
    )
    parser.add_argument("--webhook-url", help="Webhook URL for Telegram or Discord adapters.")
    parser.add_argument("--email-to", help="Email recipient for the email adapter.")
    parser.add_argument("--dry-run", action="store_true", help="Build the adapter payload but do not send it.")
    parser.add_argument("--record-delivery", action="store_true", help="Mark the current digest as delivered after evaluating the monitor payload.")
    parser.add_argument("--full", action="store_true", help="Emit the full internal monitor contract.")
    args = parser.parse_args()

    report = build_workstation_monitor(
        read_only=args.read_only,
        timeline_limit=args.timeline_limit,
    )
    if args.emit_adapter:
        report["delivery"] = dispatch_workstation_notification(
            report,
            adapter_key=args.emit_adapter,
            webhook_url=args.webhook_url,
            email_to=args.email_to,
            dry_run=args.dry_run,
        )
    if args.record_delivery:
        report = record_workstation_monitor_delivery(report)
    print_json(report if args.full else workstation_monitor_view(report))


if __name__ == "__main__":
    main()
