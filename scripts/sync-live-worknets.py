#!/usr/bin/env python3
"""Fetch live AWP worknet data and cache it for workstation scans."""

from __future__ import annotations

import argparse

from awp_workstation_lib import print_json, sync_live_worknets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", help="Optional agent address for agent-specific enrichment.")
    parser.add_argument("--limit", type=int, default=100, help="Page size for worknets.list.")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages to request.")
    args = parser.parse_args()
    print_json(
        sync_live_worknets(
            agent_address=args.address,
            limit=max(1, int(args.limit)),
            max_pages=max(1, int(args.max_pages)),
        )
    )


if __name__ == "__main__":
    main()
