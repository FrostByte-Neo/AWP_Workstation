#!/usr/bin/env python3
"""Query the workstation knowledge catalog by source key."""

from __future__ import annotations

import argparse

from awp_workstation_lib import build_knowledge_catalog, load_cached_knowledge_catalog, print_json


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
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}

    if args.changed:
        changed_items = [
            {
                "key": item.get("key"),
                "name": item.get("name"),
                "status": item.get("status"),
                "changedFields": item.get("changedFields", []),
                "note": item.get("note"),
            }
            for item in source_drift.get("items", [])
            if isinstance(item, dict) and item.get("status") not in {"unchanged", "no-baseline"}
        ]
        impacted = [
            {
                "sourceKey": item.get("sourceKey"),
                "sourceName": item.get("sourceName"),
                "priority": item.get("priority"),
                "driftStatus": item.get("driftStatus"),
                "impactedTopics": [entry.get("key") for entry in item.get("impactedTopics", []) if isinstance(entry, dict)],
                "impactedFacts": [entry.get("key") for entry in item.get("impactedFacts", []) if isinstance(entry, dict)],
                "impactedWorknets": list(item.get("impactedWorknets", [])),
                "reviewCommands": item.get("reviewCommands"),
            }
            for item in source_impact.get("impacts", [])
            if isinstance(item, dict)
        ]
        print_json(
            {
                "query": "changed",
                "sourceDriftSummary": source_drift.get("summary"),
                "sourceImpactSummary": source_impact.get("summary"),
                "changedSources": changed_items,
                "impacts": impacted,
                "reviewQueue": source_impact.get("reviewQueue"),
            }
        )
        return

    source_key = args.source_key.strip()
    source_record = None

    sources = catalog.get("sources", {})
    for item in sources.get("officialWebSources", []):
        if item.get("key") == source_key:
            source_record = item
            break
    if source_record is None:
        for item in sources.get("localSources", []):
            if item.get("key") == source_key:
                source_record = item
                break

    drift_item = next(
        (
            item
            for item in source_drift.get("items", [])
            if isinstance(item, dict) and item.get("key") == source_key
        ),
        None,
    )
    impact_item = next(
        (
            item
            for item in source_impact.get("impacts", [])
            if isinstance(item, dict) and item.get("sourceKey") == source_key
        ),
        None,
    )
    result = {
        "sourceKey": source_key,
        "source": source_record,
        "drift": drift_item,
        "impact": impact_item,
        "facts": [item for item in catalog.get("sourceFacts", []) if source_key in item.get("sourceKeys", [])],
        "evidence": [item for item in catalog.get("sourceEvidence", []) if item.get("sourceKey") == source_key],
        "dossiers": [item for item in catalog.get("topicDossiers", []) if source_key in item.get("sourceKeys", [])],
        "glossary": [item for item in catalog.get("glossary", []) if source_key in item.get("sourceKeys", [])],
        "worknets": [item for item in catalog.get("worknets", []) if source_key in item.get("sourceKeys", [])],
    }
    print_json(result)


if __name__ == "__main__":
    main()
