#!/usr/bin/env python3
"""Export workstation-owned AWP knowledge as JSON."""

from __future__ import annotations

import argparse

from awp_workstation_lib import (
    build_knowledge_catalog,
    load_cached_knowledge_catalog,
    print_json,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the knowledge catalog instead of using the cached copy.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Return only the high-level encyclopedia overview.",
    )
    parser.add_argument(
        "--topic-index",
        action="store_true",
        help="Return the topic index plus the high-level overview.",
    )
    args = parser.parse_args()

    catalog = (
        build_knowledge_catalog(rebuild_derived=True)
        if args.rebuild
        else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    )
    if not args.summary and not args.topic_index:
        print_json(catalog)
        return

    payload = {"generatedAt": catalog.get("generatedAt")}
    if args.summary or args.topic_index:
        payload["knowledgeOverview"] = catalog.get("knowledgeOverview")
    if args.topic_index:
        payload["topicDirectory"] = catalog.get("topicDirectory")
        payload["referenceIndex"] = catalog.get("referenceIndex")
        payload["topicIndex"] = catalog.get("topicIndex")
    print_json(payload)


if __name__ == "__main__":
    main()
