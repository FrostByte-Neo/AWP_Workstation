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
        help="Topic key such as protocol-core, mine, predict, gov, ardi, kya, or awp-skill.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the knowledge catalog instead of using the cached copy.",
    )
    args = parser.parse_args()

    catalog = (
        build_knowledge_catalog(rebuild_derived=True)
        if args.rebuild
        else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    )
    print_json(build_knowledge_query_result(args.topic.strip().lower(), catalog=catalog))


if __name__ == "__main__":
    main()
