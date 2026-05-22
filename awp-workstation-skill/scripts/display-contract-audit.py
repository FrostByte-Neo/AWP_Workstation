#!/usr/bin/env python3
"""Inspect encyclopedia display-contract stability."""

from __future__ import annotations

import argparse

from awp_workstation_lib import build_display_contract_audit, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Return only the high-level contract counts plus unresolved items.",
    )
    args = parser.parse_args()

    audit = build_display_contract_audit()
    if not args.summary:
        print_json(audit)
        return

    unresolved = [
        {
            "key": item.get("key"),
            "title": item.get("title"),
            "status": item.get("status"),
            "sampleRef": item.get("sampleRef"),
            "missingFields": item.get("missingFields", [])[:10],
            "extraFields": item.get("extraFields", [])[:10],
        }
        for item in audit.get("items", [])
        if isinstance(item, dict) and item.get("status") != "covered"
    ]
    print_json(
        {
            "generatedAt": audit.get("generatedAt"),
            "summary": audit.get("summary"),
            "unresolved": unresolved[:10],
        }
    )


if __name__ == "__main__":
    main()
