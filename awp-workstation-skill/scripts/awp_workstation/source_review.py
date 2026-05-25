"""Source refresh, impact, and knowledge review queue builders."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Optional

from awp_workstation.commands import query_knowledge_command, query_source_command
from awp_workstation.contracts import project_fields
from awp_workstation.knowledge_contracts import CONCEPT_DIRECTORY_ITEM_FIELDS
from awp_workstation.knowledge_data import (
    load_derived_concept_directory,
    load_derived_evidence_records,
    load_derived_glossary_terms,
    load_derived_source_facts,
    load_official_web_sources,
)
from awp_workstation.reference_exports import write_reference_export
from awp_workstation.runtime import fetch_url
from awp_workstation.source_drift import build_source_drift_report, load_cached_source_drift
from awp_workstation.source_inventory import source_filename
from awp_workstation.state import state_context
from awp_workstation.storage import atomic_write_json, load_json
from awp_workstation.utils import now_iso, safe_slug
from awp_workstation.worknets import load_worknet_profiles


SOURCE_IMPACT_SCHEMA_VERSION = 2
KNOWLEDGE_REVIEW_QUEUE_SCHEMA_VERSION = 1

OFFICIAL_WEB_SOURCES: list[dict[str, Any]] = load_official_web_sources()
DERIVED_SOURCE_FACTS: list[dict[str, Any]] = load_derived_source_facts()
DERIVED_EVIDENCE_RECORDS: list[dict[str, Any]] = load_derived_evidence_records()
DERIVED_GLOSSARY_TERMS: list[dict[str, Any]] = load_derived_glossary_terms()
DERIVED_CONCEPT_DIRECTORY: list[dict[str, Any]] = load_derived_concept_directory()
KNOWN_WORKNETS: list[dict[str, Any]] = load_worknet_profiles()


def build_source_fact_catalog() -> dict[str, Any]:
    state = state_context()
    catalog = {
        "generatedAt": now_iso(),
        "facts": DERIVED_SOURCE_FACTS,
    }
    atomic_write_json(Path(state["cache"]) / "source-facts.json", catalog)
    write_reference_export("source-facts.json", catalog)
    return catalog


def build_source_evidence_catalog() -> dict[str, Any]:
    state = state_context()
    source_map = {item["key"]: item for item in OFFICIAL_WEB_SOURCES}
    records: list[dict[str, Any]] = []
    for item in DERIVED_EVIDENCE_RECORDS:
        record = dict(item)
        source = source_map.get(item["sourceKey"])
        if source is not None:
            record["sourceName"] = source["name"]
            record["sourceUrl"] = source["url"]
            record["trustTier"] = source.get("trustTier")
        records.append(record)
    catalog = {
        "generatedAt": now_iso(),
        "records": records,
    }
    atomic_write_json(Path(state["cache"]) / "source-evidence.json", catalog)
    write_reference_export("source-evidence.json", catalog)
    return catalog


def build_glossary_catalog() -> dict[str, Any]:
    state = state_context()
    catalog = {
        "generatedAt": now_iso(),
        "terms": DERIVED_GLOSSARY_TERMS,
    }
    atomic_write_json(Path(state["cache"]) / "glossary.json", catalog)
    write_reference_export("glossary.json", catalog)
    return catalog


def build_concept_catalog() -> dict[str, Any]:
    state = state_context()
    coverage_labels = {
        "well-defined": "well defined",
        "thin": "thin coverage",
        "unknown": "unknown coverage",
    }
    concepts = [
        project_fields(
            {
                **item,
                "coverageStateDisplay": coverage_labels.get(str(item.get("coverageState") or "").strip(), item.get("coverageState")),
            },
            CONCEPT_DIRECTORY_ITEM_FIELDS,
        )
        for item in DERIVED_CONCEPT_DIRECTORY
    ]
    catalog = {
        "generatedAt": now_iso(),
        "concepts": concepts,
    }
    atomic_write_json(Path(state["cache"]) / "concept-catalog.json", catalog)
    write_reference_export("concept-catalog.json", catalog)
    return catalog


def refresh_official_sources(
    state: Optional[dict[str, Any]] = None,
    source_keys: Optional[list[str]] = None,
    timeout: int = 30,
) -> dict[str, Any]:
    state = state or state_context()
    snapshot_root = Path(state["cache"]) / "upstream-sources"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    selected = OFFICIAL_WEB_SOURCES
    if source_keys:
        allow = set(source_keys)
        selected = [source for source in OFFICIAL_WEB_SOURCES if source["key"] in allow]

    previous_snapshot = load_json(Path(state["cache"]) / "source-snapshot.json", None)
    results: list[dict[str, Any]] = []
    for source in selected:
        fetched_at = now_iso()
        response = fetch_url(str(source["url"]), timeout=timeout)
        filename = source_filename(source)
        target = snapshot_root / filename
        entry = {
            "key": source["key"],
            "url": source["url"],
            "name": source["name"],
            "kind": source.get("kind"),
            "fetchedAt": fetched_at,
            "path": str(target),
            "ok": bool(response.get("ok")),
            "status": response.get("status"),
            "contentType": response.get("contentType"),
            "sha256": None,
            "bytes": 0,
            "error": response.get("error"),
        }
        if response.get("ok"):
            body = response.get("body", b"")
            target.write_bytes(body)
            entry["bytes"] = len(body)
            entry["sha256"] = hashlib.sha256(body).hexdigest()
            entry["headers"] = response.get("headers")
        results.append(entry)

    snapshot = {
        "generatedAt": now_iso(),
        "snapshotRoot": str(snapshot_root),
        "results": results,
    }
    history_root = Path(state["cache"]) / "source-snapshot-history"
    history_root.mkdir(parents=True, exist_ok=True)
    atomic_write_json(history_root / f"source-snapshot-{safe_slug(snapshot['generatedAt'])}.json", snapshot)
    atomic_write_json(Path(state["cache"]) / "source-snapshot.json", snapshot)
    write_reference_export("source-snapshot.json", snapshot)
    drift = build_source_drift_report(
        state=state,
        current_snapshot=snapshot,
        previous_snapshot=previous_snapshot,
    )
    impact = build_source_drift_impact_report(
        state=state,
        drift_report=drift,
    )
    return {
        **snapshot,
        "drift": drift,
        "impact": impact,
    }


def source_drift_impact_report_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "source-impact.json"


def impact_priority_for_source(key: str, source_kind: Optional[str]) -> str:
    if key in {"awp-skill", "awp-skill-readme-raw", "aip-001-raw", "aip-002-raw"}:
        return "high"
    if source_kind in {"aip", "skill", "skill-doc", "live-api"}:
        return "high"
    if source_kind in {"protocol", "protocol-surface", "worknet", "worknet-surface"}:
        return "medium"
    return "low"


def build_source_drift_impact_report(
    *,
    state: Optional[dict[str, Any]] = None,
    drift_report: Optional[dict[str, Any]] = None,
    topic_dossiers: Optional[dict[str, Any]] = None,
    source_facts: Optional[dict[str, Any]] = None,
    source_evidence: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state or state_context()
    drift_report = drift_report or load_cached_source_drift(state) or build_source_drift_report(state=state)
    topic_dossiers = topic_dossiers or build_topic_dossier_catalog()
    source_facts = source_facts or build_source_fact_catalog()
    source_evidence = source_evidence or build_source_evidence_catalog()

    dossier_items = topic_dossiers.get("dossiers", []) if isinstance(topic_dossiers, dict) else []
    fact_items = source_facts.get("facts", []) if isinstance(source_facts, dict) else []
    evidence_items = source_evidence.get("records", []) if isinstance(source_evidence, dict) else []
    source_meta = {item["key"]: item for item in OFFICIAL_WEB_SOURCES}
    changed_sources = [
        item
        for item in drift_report.get("items", [])
        if isinstance(item, dict) and item.get("status") not in {"unchanged", "no-baseline"}
    ] if isinstance(drift_report, dict) else []

    impacts: list[dict[str, Any]] = []
    impacted_topic_keys: set[str] = set()
    impacted_fact_keys: set[str] = set()
    impacted_evidence_keys: set[str] = set()
    impacted_worknet_keys: set[str] = set()
    highest_priority = "low"
    priority_rank = {"low": 0, "medium": 1, "high": 2}

    for changed in changed_sources:
        key = str(changed.get("key") or "")
        if not key:
            continue
        meta = source_meta.get(key, {})
        source_kind = meta.get("kind") if isinstance(meta, dict) else None
        impacted_dossiers = [
            item
            for item in dossier_items
            if isinstance(item, dict) and key in item.get("sourceKeys", [])
        ]
        impacted_facts = [
            item
            for item in fact_items
            if isinstance(item, dict) and key in item.get("sourceKeys", [])
        ]
        impacted_evidence = [
            item
            for item in evidence_items
            if isinstance(item, dict) and str(item.get("sourceKey") or "") == key
        ]
        impacted_worknets = [
            item["key"]
            for item in KNOWN_WORKNETS
            if key in item.get("source_keys", [])
        ]
        priority = impact_priority_for_source(key, str(source_kind or ""))
        if priority_rank[priority] > priority_rank[highest_priority]:
            highest_priority = priority
        impacted_topic_keys.update(str(item.get("key")) for item in impacted_dossiers if item.get("key"))
        impacted_fact_keys.update(str(item.get("key")) for item in impacted_facts if item.get("key"))
        impacted_evidence_keys.update(str(item.get("key")) for item in impacted_evidence if item.get("key"))
        impacted_worknet_keys.update(str(item) for item in impacted_worknets if item)
        impacts.append(
            {
                "sourceKey": key,
                "sourceName": changed.get("name") or meta.get("name") or key,
                "sourceKind": source_kind,
                "driftStatus": changed.get("status"),
                "priority": priority,
                "changedFields": list(changed.get("changedFields", [])) if isinstance(changed.get("changedFields"), list) else [],
                "note": changed.get("note"),
                "impactedTopics": [
                    {
                        "key": item.get("key"),
                        "title": item.get("title"),
                    }
                    for item in impacted_dossiers
                ],
                "impactedFacts": [
                    {
                        "key": item.get("key"),
                        "topic": item.get("topic"),
                    }
                    for item in impacted_facts
                ],
                "impactedEvidence": [
                    {
                        "key": item.get("key"),
                        "topicKey": item.get("topicKey"),
                    }
                    for item in impacted_evidence
                ],
                "impactedWorknets": impacted_worknets,
                "reviewHint": (
                    "Review the changed source before trusting dependent topics, facts, evidence, or WorkNet guidance."
                    if impacted_dossiers or impacted_facts or impacted_evidence or impacted_worknets
                    else "Review this source change before relying on related WorkNet guidance."
                ),
                "reviewCommands": {
                    "source": query_source_command(key, rebuild=True),
                    "topics": {
                        str(item.get("key")): query_knowledge_command(str(item.get("key")), rebuild=True)
                        for item in impacted_dossiers
                        if item.get("key")
                    },
                    "facts": {
                        str(item.get("key")): query_knowledge_command(str(item.get("key")), rebuild=True)
                        for item in impacted_facts
                        if item.get("key")
                    },
                    "worknets": {
                        str(item): query_knowledge_command(str(item), rebuild=True)
                        for item in impacted_worknets
                        if str(item).strip()
                    },
                },
            }
        )

    report = {
        "generatedAt": now_iso(),
        "schemaVersion": SOURCE_IMPACT_SCHEMA_VERSION,
        "driftGeneratedAt": drift_report.get("generatedAt") if isinstance(drift_report, dict) else None,
        "summary": {
            "changedSources": len(changed_sources),
            "impactedTopics": len(impacted_topic_keys),
            "impactedFacts": len(impacted_fact_keys),
            "impactedEvidence": len(impacted_evidence_keys),
            "impactedWorknets": len(impacted_worknet_keys),
            "highestPriority": highest_priority,
        },
        "impacts": impacts,
        "reviewQueue": {
            "topicKeys": sorted(impacted_topic_keys),
            "factKeys": sorted(impacted_fact_keys),
            "evidenceKeys": sorted(impacted_evidence_keys),
            "worknetKeys": sorted(impacted_worknet_keys),
        },
    }
    atomic_write_json(source_drift_impact_report_path(state), report)
    write_reference_export("source-impact.json", report)
    return report


def load_cached_source_impact(state: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    state = state or state_context()
    payload = load_json(source_drift_impact_report_path(state), None)
    if not isinstance(payload, dict):
        return None
    if payload.get("schemaVersion") != SOURCE_IMPACT_SCHEMA_VERSION:
        return None
    if "impacts" not in payload or "reviewQueue" not in payload:
        return None
    return payload


def topic_freshness_report_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "topic-freshness.json"


def build_topic_freshness_catalog(
    *,
    state: Optional[dict[str, Any]] = None,
    source_impact: Optional[dict[str, Any]] = None,
    topic_dossiers: Optional[dict[str, Any]] = None,
    source_facts: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state or state_context()
    source_impact = source_impact or load_cached_source_impact(state) or build_source_drift_impact_report(state=state)
    topic_dossiers = topic_dossiers or build_topic_dossier_catalog()
    source_facts = source_facts or build_source_fact_catalog()

    priority_rank = {"low": 0, "medium": 1, "high": 2}

    def empty_entry(key: str, label: Optional[str], bucket: str) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "bucket": bucket,
            "status": "stable",
            "highestPriority": "low",
            "changedSourceKeys": [],
            "impactItems": [],
            "reviewHints": [],
        }

    topics = {
        str(item.get("key")): empty_entry(str(item.get("key")), item.get("title"), "topic")
        for item in topic_dossiers.get("dossiers", [])
        if isinstance(item, dict) and item.get("key")
    }
    facts = {
        str(item.get("key")): empty_entry(str(item.get("key")), item.get("topic"), "fact")
        for item in source_facts.get("facts", [])
        if isinstance(item, dict) and item.get("key")
    }
    worknets = {
        str(item.get("key")): empty_entry(str(item.get("key")), item.get("name"), "worknet")
        for item in KNOWN_WORKNETS
        if item.get("key")
    }

    def apply_impact(entry_map: dict[str, dict[str, Any]], key: str, impact: dict[str, Any]) -> None:
        entry = entry_map.setdefault(key, empty_entry(key, None, "topic"))
        entry["status"] = "affected"
        source_key = str(impact.get("sourceKey") or "")
        if source_key and source_key not in entry["changedSourceKeys"]:
            entry["changedSourceKeys"].append(source_key)
        priority = str(impact.get("priority") or "low")
        if priority_rank.get(priority, 0) > priority_rank.get(entry["highestPriority"], 0):
            entry["highestPriority"] = priority
        summary = {
            "sourceKey": impact.get("sourceKey"),
            "sourceName": impact.get("sourceName"),
            "priority": impact.get("priority"),
            "driftStatus": impact.get("driftStatus"),
        }
        if summary not in entry["impactItems"]:
            entry["impactItems"].append(summary)
        hint = impact.get("reviewHint")
        if isinstance(hint, str) and hint.strip() and hint not in entry["reviewHints"]:
            entry["reviewHints"].append(hint.strip())

    for impact in source_impact.get("impacts", []) if isinstance(source_impact, dict) else []:
        if not isinstance(impact, dict):
            continue
        for item in impact.get("impactedTopics", []):
            if isinstance(item, dict) and item.get("key"):
                apply_impact(topics, str(item["key"]), impact)
        for item in impact.get("impactedFacts", []):
            if isinstance(item, dict) and item.get("key"):
                apply_impact(facts, str(item["key"]), impact)
        for key in impact.get("impactedWorknets", []):
            text = str(key).strip()
            if text:
                apply_impact(worknets, text, impact)

    def materialize(entry_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [entry_map[key] for key in sorted(entry_map.keys())]

    report = {
        "generatedAt": now_iso(),
        "sourceImpactGeneratedAt": source_impact.get("generatedAt") if isinstance(source_impact, dict) else None,
        "summary": {
            "affectedTopics": sum(1 for item in topics.values() if item["status"] == "affected"),
            "affectedFacts": sum(1 for item in facts.values() if item["status"] == "affected"),
            "affectedWorknets": sum(1 for item in worknets.values() if item["status"] == "affected"),
        },
        "topics": materialize(topics),
        "facts": materialize(facts),
        "worknets": materialize(worknets),
    }
    atomic_write_json(topic_freshness_report_path(state), report)
    write_reference_export("topic-freshness.json", report)
    return report


def load_cached_topic_freshness(state: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    state = state or state_context()
    payload = load_json(topic_freshness_report_path(state), None)
    return payload if isinstance(payload, dict) else None


def knowledge_review_queue_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "knowledge-review-queue.json"


def build_knowledge_review_queue(
    *,
    state: Optional[dict[str, Any]] = None,
    source_impact: Optional[dict[str, Any]] = None,
    topic_freshness: Optional[dict[str, Any]] = None,
    source_evidence: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state or state_context()
    source_impact = source_impact or load_cached_source_impact(state) or build_source_drift_impact_report(state=state)
    topic_freshness = topic_freshness or load_cached_topic_freshness(state) or build_topic_freshness_catalog(
        state=state,
        source_impact=source_impact,
    )
    source_evidence = source_evidence or build_source_evidence_catalog()

    entries: list[dict[str, Any]] = []
    topic_labels: dict[str, str] = {}
    fact_labels: dict[str, str] = {}
    worknet_labels: dict[str, str] = {}
    for item in topic_freshness.get("topics", []):
        if isinstance(item, dict) and item.get("key"):
            topic_labels[str(item["key"])] = str(item.get("label") or item["key"])
    for item in topic_freshness.get("facts", []):
        if isinstance(item, dict) and item.get("key"):
            fact_labels[str(item["key"])] = str(item.get("label") or item["key"])
    for item in topic_freshness.get("worknets", []):
        if isinstance(item, dict) and item.get("key"):
            worknet_labels[str(item["key"])] = str(item.get("label") or item["key"])
    evidence_by_key = {
        str(item.get("key")): item
        for item in source_evidence.get("records", [])
        if isinstance(item, dict) and item.get("key")
    }

    for impact in source_impact.get("impacts", []):
        if not isinstance(impact, dict):
            continue
        priority = str(impact.get("priority") or "low")
        source_key = str(impact.get("sourceKey") or "")
        source_name = str(impact.get("sourceName") or source_key)
        review_commands = impact.get("reviewCommands", {}) if isinstance(impact.get("reviewCommands"), dict) else {}
        entries.append(
            {
                "kind": "source",
                "key": source_key,
                "label": source_name,
                "priority": priority,
                "reason": impact.get("reviewHint"),
                "command": review_commands.get("source"),
            }
        )
        topic_commands = review_commands.get("topics", {}) if isinstance(review_commands.get("topics"), dict) else {}
        for key in impact.get("impactedTopics", []):
            topic_key = str(key.get("key") if isinstance(key, dict) else key).strip()
            if not topic_key:
                continue
            entries.append(
                {
                    "kind": "topic",
                    "key": topic_key,
                    "label": topic_labels.get(topic_key, topic_key),
                    "priority": priority,
                    "reason": impact.get("reviewHint"),
                    "command": topic_commands.get(topic_key),
                }
            )
        fact_commands = review_commands.get("facts", {}) if isinstance(review_commands.get("facts"), dict) else {}
        for key in impact.get("impactedFacts", []):
            fact_key = str(key.get("key") if isinstance(key, dict) else key).strip()
            if not fact_key:
                continue
            entries.append(
                {
                    "kind": "fact",
                    "key": fact_key,
                    "label": fact_labels.get(fact_key, fact_key),
                    "priority": priority,
                    "reason": impact.get("reviewHint"),
                    "command": fact_commands.get(fact_key),
                }
            )
        worknet_commands = review_commands.get("worknets", {}) if isinstance(review_commands.get("worknets"), dict) else {}
        for key in impact.get("impactedWorknets", []):
            worknet_key = str(key).strip()
            if not worknet_key:
                continue
            entries.append(
                {
                    "kind": "worknet",
                    "key": worknet_key,
                    "label": worknet_labels.get(worknet_key, worknet_key),
                    "priority": priority,
                    "reason": impact.get("reviewHint"),
                    "command": worknet_commands.get(worknet_key),
                }
            )
        for evidence in impact.get("impactedEvidence", []):
            if not isinstance(evidence, dict) or not evidence.get("key"):
                continue
            evidence_key = str(evidence["key"])
            evidence_record = evidence_by_key.get(evidence_key, {})
            topic_key = str(evidence_record.get("topicKey") or evidence.get("topicKey") or "").strip()
            entries.append(
                {
                    "kind": "evidence",
                    "key": evidence_key,
                    "label": evidence_key,
                    "priority": priority,
                    "reason": impact.get("reviewHint"),
                    "command": query_knowledge_command(topic_key, rebuild=True) if topic_key else None,
                }
            )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in entries:
        key = (str(item.get("kind")), str(item.get("key")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    report = {
        "generatedAt": now_iso(),
        "schemaVersion": KNOWLEDGE_REVIEW_QUEUE_SCHEMA_VERSION,
        "sourceImpactGeneratedAt": source_impact.get("generatedAt") if isinstance(source_impact, dict) else None,
        "summary": {
            "entries": len(deduped),
            "sources": sum(1 for item in deduped if item["kind"] == "source"),
            "topics": sum(1 for item in deduped if item["kind"] == "topic"),
            "facts": sum(1 for item in deduped if item["kind"] == "fact"),
            "evidence": sum(1 for item in deduped if item["kind"] == "evidence"),
            "worknets": sum(1 for item in deduped if item["kind"] == "worknet"),
        },
        "entries": deduped,
    }
    atomic_write_json(knowledge_review_queue_path(state), report)
    write_reference_export("knowledge-review-queue.json", report)
    return report


def load_cached_knowledge_review_queue(state: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    state = state or state_context()
    payload = load_json(knowledge_review_queue_path(state), None)
    if not isinstance(payload, dict):
        return None
    if payload.get("schemaVersion") != KNOWLEDGE_REVIEW_QUEUE_SCHEMA_VERSION:
        return None
    if "entries" not in payload:
        return None
    return payload
