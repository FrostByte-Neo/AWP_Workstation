#!/usr/bin/env python3
"""Run the unified workstation verification audit."""

from __future__ import annotations

import argparse
import sys

from awp_workstation_lib import build_verification_audit, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Return only the high-level suite counts plus unresolved items.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when the verification status is not covered.",
    )
    args = parser.parse_args()

    audit = build_verification_audit()
    if args.summary:
        print_json(
            {
                "generatedAt": audit.get("generatedAt"),
                "status": audit.get("status"),
                "summary": audit.get("summary"),
                "unresolved": (audit.get("unresolved") or [])[:20],
            }
        )
    else:
        print_json(audit)

    if args.strict and audit.get("status") != "covered":
        sys.exit(1)


if __name__ == "__main__":
    main()
