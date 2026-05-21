#!/usr/bin/env python3
"""Query the workstation glossary by term or alias."""

from __future__ import annotations

import argparse

from awp_workstation_lib import build_glossary_catalog, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--term", required=True, help="Glossary term or alias.")
    args = parser.parse_args()

    catalog = build_glossary_catalog()
    query = args.term.strip().lower()
    match = None
    for item in catalog.get("terms", []):
        candidates = [str(item.get("term", "")).lower()]
        candidates.extend(str(alias).lower() for alias in item.get("aliases", []))
        if query in candidates:
            match = item
            break
    print_json({"query": query, "match": match})


if __name__ == "__main__":
    main()
