#!/usr/bin/env python3
"""Emit workstation preflight JSON."""

import argparse

from awp_workstation_lib import build_preflight_report, print_json, public_preflight_view


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Compatibility flag; JSON is always emitted.")
    parser.add_argument("--full", action="store_true", help="Emit the full workstation preflight record.")
    args = parser.parse_args()
    report = build_preflight_report()
    print_json(report if args.full else public_preflight_view(report))


if __name__ == "__main__":
    main()
