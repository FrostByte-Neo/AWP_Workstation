#!/usr/bin/env python3
"""Emit workstation worknet capability reports."""

import argparse

from awp_workstation_lib import (
    build_capability_bundle,
    print_json,
    public_capability_view,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Compatibility flag; JSON is always emitted.")
    parser.add_argument("--full", action="store_true", help="Emit the full internal capability reports.")
    args = parser.parse_args()
    bundle = build_capability_bundle()
    reports = bundle["reports"] if args.full else [public_capability_view(item) for item in bundle["reports"]]
    print_json(reports)


if __name__ == "__main__":
    main()
