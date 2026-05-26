#!/usr/bin/env python3
"""Emit the structured knowledge review queue derived from upstream drift."""

from __future__ import annotations

import argparse

from awp_workstation_lib import (
    build_knowledge_review_queue,
    knowledge_display_review_queue_entries,
    knowledge_review_queue_summary_text,
    load_cached_knowledge_catalog,
    load_cached_knowledge_review_queue,
    print_json,
    refresh_official_sources,
    summarize_knowledge_review_queue,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh official sources before emitting the queue.",
    )
    parser.add_argument(
        "--source-key",
        action="append",
        dest="source_keys",
        help="Refresh only the selected official source key. Can be passed multiple times.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-source fetch timeout in seconds when --refresh is used.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the queue from current cached drift/impact state.",
    )
    args = parser.parse_args()
    if args.refresh:
        refresh_official_sources(
            source_keys=args.source_keys,
            timeout=max(1, int(args.timeout)),
        )
        payload = build_knowledge_review_queue()
        catalog = load_cached_knowledge_catalog()
        summary = summarize_knowledge_review_queue(payload)
        enriched = dict(payload)
        enriched["headline"] = summary.get("headline")
        enriched["summaryText"] = knowledge_review_queue_summary_text(summary)
        enriched["summaryDisplay"] = summary
        enriched["entriesDisplay"] = knowledge_display_review_queue_entries(payload.get("entries", []), catalog=catalog)
        print_json(enriched)
        return
    payload = build_knowledge_review_queue() if args.rebuild else (load_cached_knowledge_review_queue() or build_knowledge_review_queue())
    catalog = load_cached_knowledge_catalog()
    summary = summarize_knowledge_review_queue(payload)
    enriched = dict(payload)
    enriched["headline"] = summary.get("headline")
    enriched["summaryText"] = knowledge_review_queue_summary_text(summary)
    enriched["summaryDisplay"] = summary
    enriched["entriesDisplay"] = knowledge_display_review_queue_entries(payload.get("entries", []), catalog=catalog)
    print_json(enriched)


if __name__ == "__main__":
    main()
