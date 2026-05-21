#!/usr/bin/env python3
"""Run awp-skill's official preflight and persist the best known result."""

from __future__ import annotations

import argparse

from awp_workstation_lib import awp_wallet_snapshot, print_json, run_awp_skill_preflight


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", help="Optional address override.")
    args = parser.parse_args()

    wallet = awp_wallet_snapshot()
    address = args.address or wallet.get("address")
    print_json(run_awp_skill_preflight(address=address))


if __name__ == "__main__":
    main()
