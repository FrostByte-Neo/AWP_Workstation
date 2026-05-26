#!/usr/bin/env python3
"""Fetch and snapshot official upstream AWP sources."""

from __future__ import annotations

import argparse

from awp_workstation_lib import print_json, refresh_official_sources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-key",
        action="append",
        dest="source_keys",
        help="Fetch only the selected official source key. Can be passed multiple times.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-source fetch timeout in seconds.",
    )
    args = parser.parse_args()
    print_json(
        refresh_official_sources(
            source_keys=args.source_keys,
            timeout=max(1, int(args.timeout)),
        )
    )


if __name__ == "__main__":
    main()
