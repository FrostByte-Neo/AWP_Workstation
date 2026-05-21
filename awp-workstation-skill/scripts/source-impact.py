#!/usr/bin/env python3
"""Inspect or refresh knowledge impact from upstream source drift."""

from __future__ import annotations

import argparse

from awp_workstation_lib import (
    build_source_drift_impact_report,
    load_cached_source_impact,
    print_json,
    refresh_official_sources,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh official sources before emitting the impact report.",
    )
    parser.add_argument(
        "--source-key",
        action="append",
        dest="source_keys",
        help="Refresh only the selected official source key. Can be passed multiple times.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-source fetch timeout in seconds when --refresh is used.",
    )
    args = parser.parse_args()
    if args.refresh:
        payload = refresh_official_sources(
            source_keys=args.source_keys,
            timeout=max(1, int(args.timeout)),
        )
        print_json(payload.get("impact", {}))
        return
    payload = load_cached_source_impact() or build_source_drift_impact_report()
    print_json(payload)


if __name__ == "__main__":
    main()
