#!/usr/bin/env python3
"""Query the workstation knowledge catalog by topic, dossier, or source fact key."""

from __future__ import annotations

import argparse

from awp_workstation_lib import (
    build_knowledge_catalog,
    build_knowledge_query_result,
    load_cached_knowledge_catalog,
    print_json,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--topic",
        required=True,
        help="Topic key such as atlas, protocol-core, mine, predict, gov, ardi, kya, or awp-skill.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the knowledge catalog instead of using the cached copy.",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Do not rebuild or write caches; fail with a JSON error if the catalog is missing.",
    )
    args = parser.parse_args()

    if args.read_only and args.rebuild:
        parser.error("--read-only cannot be combined with --rebuild")
    cached_catalog = load_cached_knowledge_catalog()
    if args.read_only and not cached_catalog:
        print_json({
            "status": "cache_missing",
            "error": "knowledge catalog cache is missing; rerun without --read-only or use --rebuild",
        })
        return
    catalog = build_knowledge_catalog(rebuild_derived=True) if args.rebuild else (cached_catalog or build_knowledge_catalog())
    print_json(build_knowledge_query_result(args.topic.strip().lower(), catalog=catalog))


if __name__ == "__main__":
    main()
