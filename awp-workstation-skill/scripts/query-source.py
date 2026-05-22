#!/usr/bin/env python3
"""Query the workstation knowledge catalog by source key."""

from __future__ import annotations

import argparse

from awp_workstation_lib import (
    build_changed_sources_query_result,
    build_knowledge_catalog,
    build_source_query_result,
    load_cached_knowledge_catalog,
    print_json,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-key", help="Source key such as aip-001-raw or awp-staking.")
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Return the currently changed upstream sources plus their impacted topics/facts/worknets.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the knowledge catalog instead of using the cached copy.",
    )
    args = parser.parse_args()
    if not args.source_key and not args.changed:
        parser.error("provide --source-key or --changed")

    catalog = build_knowledge_catalog() if args.rebuild else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    if args.changed:
        print_json(build_changed_sources_query_result(catalog=catalog))
        return

    source_key = args.source_key.strip()
    print_json(build_source_query_result(source_key, catalog=catalog))


if __name__ == "__main__":
    main()
