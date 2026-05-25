"""Knowledge query/display response contracts."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.contracts import project_fields


KNOWLEDGE_QUEUE_PRIORITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}
KNOWLEDGE_PRIORITY_LABELS = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
KNOWLEDGE_QUEUE_KIND_ORDER = {"source": 0, "topic": 1, "fact": 2, "worknet": 3, "evidence": 4}
KNOWLEDGE_DIRECTORY_FACT_KEYS = {
    "staking-facts": "staking",
    "dao-facts": "dao",
    "testnet-facts": "benchmark-testnet",
    "blog-facts": "blog",
}
KNOWLEDGE_AUTOMATION_LABELS = {
    "full": "Full automation",
    "supervised": "Supervised automation",
    "manual-only": "Manual only",
    "partial": "Partial automation",
    "guided": "Guided automation",
}
KNOWLEDGE_RISK_LABELS = {
    "low": "Low risk",
    "medium": "Medium risk",
    "high": "High risk",
}
KNOWLEDGE_ROLE_LABELS = {
    "operator": "Operator",
    "strategist": "Strategist",
    "governor": "Governor",
    "observer": "Observer",
    "identity": "Identity",
    "event-operator": "Event operator",
}
KNOWLEDGE_WORKNET_STATUS_LABELS = {
    "active": "Active",
    "public": "Public",
    "discoverable": "Discoverable",
    "service": "Service",
}
KNOWLEDGE_SOURCE_KIND_LABELS = {
    "protocol": "Protocol",
    "directory": "Directory",
    "paper": "Paper",
    "skill": "Skill",
    "skill-doc": "Skill documentation",
    "aip": "AIP specification",
    "live-api": "Live API",
    "worknet": "WorkNet",
    "protocol-surface": "Protocol surface",
    "worknet-surface": "WorkNet surface",
    "docs": "Documentation",
    "service": "Service",
}
KNOWLEDGE_DRIFT_STATUS_LABELS = {
    "content_changed": "Content changed",
    "changed": "Changed",
    "unchanged": "Unchanged",
    "no-baseline": "No baseline",
}
KNOWLEDGE_FRESHNESS_STATUS_LABELS = {
    "affected": "Needs review",
    "stable": "Stable",
}
KNOWLEDGE_FRESHNESS_BUCKET_LABELS = {
    "topic": "Topic",
    "fact": "Fact",
    "worknet": "WorkNet",
}
KNOWLEDGE_TRUST_TIER_LABELS = {
    1: "Primary",
    2: "Secondary",
    3: "Supporting",
}
KNOWLEDGE_CHANGED_FIELD_LABELS = {
    "sha256": "Content hash",
    "bytes": "Byte size",
    "status": "HTTP status",
    "ok": "Availability",
}
KNOWLEDGE_QUEUE_KIND_LABELS = {
    "source": "Source",
    "topic": "Topic",
    "fact": "Fact",
    "worknet": "WorkNet",
    "evidence": "Evidence",
}
KNOWLEDGE_EVIDENCE_TYPE_LABELS = {
    "normative-overview": "Normative overview",
    "runtime-doc": "Runtime documentation",
    "runtime-inspection": "Runtime inspection",
    "aip": "AIP",
    "skill-doc": "Skill documentation",
    "live-api": "Live API",
    "protocol-surface": "Protocol surface",
    "skill-uri": "Skill URI",
    "docs-surface": "Documentation surface",
}
KNOWLEDGE_STABILITY_LABELS = {
    "high": "High stability",
    "medium": "Medium stability",
    "low": "Low stability",
}
KNOWLEDGE_RUNTIME_SPEC_STATE_LABELS = {
    "local-runtime-evidence": "Local runtime evidence",
    "runtime-doc-available": "Runtime documentation available",
    "thin-repo-only": "Thin repository only",
    "thin-repo-plus-hub": "Thin repository plus hub listing",
    "unknown": "Unknown runtime state",
}


KNOWLEDGE_HIGHLIGHT_BASE_FIELDS = [
    "recordKind",
    "recordKey",
    "fullRecordKey",
    "key",
    "label",
    "headline",
    "preview",
    "command",
    "queryCommand",
    "primaryCommand",
    "freshnessStatus",
    "freshnessStatusDisplay",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
]

TOPIC_HIGHLIGHT_FIELDS = [
    *KNOWLEDGE_HIGHLIGHT_BASE_FIELDS,
    "summary",
    "summaryPreview",
    "summaryFull",
    "affectedSourceKeys",
    "worknetKey",
    "worknetName",
    "automationLevel",
    "riskLevel",
    "runtimeSummary",
    "runtimeProbeCount",
    "status",
    "statusDisplay",
]

REFERENCE_HIGHLIGHT_FIELDS = [
    *KNOWLEDGE_HIGHLIGHT_BASE_FIELDS,
    "summary",
    "summaryPreview",
    "summaryFull",
    "runtimeSummary",
    "runtimeProbeCount",
]

SOURCE_HIGHLIGHT_FIELDS = [
    *KNOWLEDGE_HIGHLIGHT_BASE_FIELDS,
    "summary",
    "summaryPreview",
    "summaryFull",
    "highestPriority",
    "worknetKey",
    "kindDisplay",
    "runtimeSummary",
    "runtimeProbeCount",
]

FACT_HIGHLIGHT_FIELDS = [
    *KNOWLEDGE_HIGHLIGHT_BASE_FIELDS,
    "topic",
    "summary",
    "summaryPreview",
    "summaryFull",
    "factsPreview",
    "factCount",
    "runtimeSummary",
    "runtimeProbeCount",
]

WORKNET_HIGHLIGHT_FIELDS = [
    *KNOWLEDGE_HIGHLIGHT_BASE_FIELDS,
    "name",
    "goal",
    "goalPreview",
    "goalFull",
    "cautionPreview",
    "statusDisplay",
    "riskLevelDisplay",
    "recommendedRoleDisplay",
    "runtimeSummary",
    "runtimeProbeCount",
]

EVIDENCE_HIGHLIGHT_FIELDS = [
    *KNOWLEDGE_HIGHLIGHT_BASE_FIELDS,
    "claim",
    "claimPreview",
    "claimFull",
    "claimDisplay",
    "previewDisplay",
    "locatorDisplay",
    "commandDisplay",
    "stabilityDisplay",
    "topicKey",
]

REVIEW_QUEUE_HIGHLIGHT_FIELDS = [
    *KNOWLEDGE_HIGHLIGHT_BASE_FIELDS,
    "kind",
    "kindDisplay",
    "labelDisplay",
    "priority",
    "priorityDisplay",
    "description",
]

CHANGED_SOURCE_HIGHLIGHT_FIELDS = [
    *SOURCE_HIGHLIGHT_FIELDS,
    "nameDisplay",
    "statusDisplay",
    "changedFieldsDisplay",
]

KNOWLEDGE_REVIEW_QUEUE_SUMMARY_FIELDS = [
    "available",
    "hasPendingReviews",
    "pendingReviewCount",
    "changedSourceCount",
    "topicCount",
    "factCount",
    "evidenceCount",
    "worknetCount",
    "highestPriority",
    "highestPriorityDisplay",
    "focusSources",
    "focusSourcesDisplay",
    "focusTopics",
    "headline",
    "primaryActionLabel",
    "primaryActionCommand",
    "refreshActionLabel",
    "refreshActionCommand",
    "generatedAt",
    "sourceImpactGeneratedAt",
]

AFFECTED_TOPIC_FIELDS = [
    "key",
    "label",
    "headline",
    "primaryCommand",
    "affectedSourceKeys",
]

FRESHNESS_ITEM_FIELDS = [
    "key",
    "label",
    "bucket",
    "bucketDisplay",
    "status",
    "statusDisplay",
    "highestPriority",
    "highestPriorityDisplay",
    "changedSourceKeys",
    "changedSourcesDisplay",
    "reviewHints",
]

FRESHNESS_DISPLAY_FIELDS = [
    "status",
    "statusDisplay",
    "highestPriority",
    "highestPriorityDisplay",
    "summary",
    "items",
]

DRIFT_DISPLAY_FIELDS = [
    "key",
    "name",
    "nameDisplay",
    "status",
    "statusDisplay",
    "changedFields",
    "changedFieldsDisplay",
    "note",
    "previous",
    "current",
]

SOURCE_IMPACT_ITEM_FIELDS = [
    "sourceKey",
    "sourceName",
    "sourceNameDisplay",
    "priority",
    "priorityDisplay",
    "driftStatus",
    "driftStatusDisplay",
    "changedFields",
    "changedFieldsDisplay",
    "note",
    "impactedTopicsDisplay",
    "impactedFactsDisplay",
    "impactedWorknetsDisplay",
    "reviewHint",
    "reviewCommands",
]

SOURCE_IMPACT_DISPLAY_FIELDS = [
    "affected",
    "summary",
    "items",
]

SOURCE_RECORD_DISPLAY_FIELDS = [
    "key",
    "name",
    "nameDisplay",
    "url",
    "kind",
    "kindDisplay",
    "trustTier",
    "trustTierDisplay",
    "worknetKey",
    "canonicalWorknetId",
    "predecessorWorknetIds",
    "officialSkillUri",
    "minStakeHint",
    "minStakeHintDisplay",
    "runtimeSpecState",
    "runtimeSpecStateDisplay",
    "headline",
    "summary",
    "summaryDisplay",
    "summaryPreview",
    "runtimeSummary",
    "runtimeProbeCount",
]

CITATION_DISPLAY_FIELDS = [
    "sourceKey",
    "sourceName",
    "sourceNameDisplay",
    "url",
    "locator",
    "locatorDisplay",
    "claim",
    "claimDisplay",
    "evidenceType",
    "evidenceTypeDisplay",
    "stability",
    "stabilityDisplay",
]

DOSSIER_DISPLAY_FIELDS = [
    "key",
    "kind",
    "title",
    "summary",
    "defaultEntrypoint",
    "whyItExists",
    "operatorLoop",
    "economics",
    "risks",
    "sourceKeys",
    "officialUrls",
    "canonicalWorknetId",
    "predecessorWorknetIds",
    "officialSkillUri",
    "minStakeHint",
    "minStakeHintDisplay",
    "runtimeSpecState",
    "runtimeSpecStateDisplay",
]

SOURCE_FACT_DISPLAY_FIELDS = [
    "key",
    "topic",
    "summary",
    "facts",
    "sourceKeys",
    "canonicalWorknetId",
    "predecessorWorknetIds",
    "officialSkillUri",
    "minStakeHint",
    "minStakeHintDisplay",
    "runtimeSpecState",
    "runtimeSpecStateDisplay",
    "runtimeSummary",
    "runtimeProbeCount",
]

WORKNET_DISPLAY_FIELDS = [
    "key",
    "worknetId",
    "name",
    "status",
    "statusDisplay",
    "symbol",
    "installUri",
    "sourceKeys",
    "sourceKeysDisplay",
    "canonicalWorknetId",
    "predecessorWorknetIds",
    "officialSkillUri",
    "minStakeHint",
    "minStakeHintDisplay",
    "runtimeSpecState",
    "runtimeSpecStateDisplay",
    "goal",
    "goalDisplay",
    "loop",
    "loopDisplay",
    "automationLevel",
    "automationLevelDisplay",
    "riskLevel",
    "riskLevelDisplay",
    "recommendedRole",
    "recommendedRoleDisplay",
    "cautionDisplay",
    "runtimeSummary",
    "runtimeProbeCount",
    "runnable",
    "canStartWithoutStake",
    "safeLongRun",
    "cliStatus",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
]

GLOSSARY_ITEM_FIELDS = [
    "term",
    "aliases",
    "plainLanguage",
    "definition",
    "whyItMatters",
    "relatedTopics",
]

GLOSSARY_QUERY_MATCH_FIELDS = [
    *GLOSSARY_ITEM_FIELDS,
    "sourceKeys",
]

CONCEPT_DIRECTORY_ITEM_FIELDS = [
    "key",
    "title",
    "kind",
    "aliases",
    "plainLanguage",
    "whyItMatters",
    "summary",
    "operatorLoop",
    "sourceKeys",
    "evidenceKeys",
    "relatedTopics",
    "relatedWorknets",
    "coverageState",
    "coverageStateDisplay",
    "coverageNote",
]

REVIEW_SCOPE_FIELDS = [
    "topicCount",
    "factCount",
    "worknetCount",
    "evidenceCount",
]

KNOWLEDGE_QUERY_FIELDS = [
    "topic",
    "status",
    "resolvedTopicKey",
    "resolvedTopicLabel",
    "progress",
    "headline",
    "summary",
    "plainLanguage",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
    "primaryCommand",
    "primaryUserAction",
    "primaryUserActionDisplay",
    "primaryUserActionCommand",
    "userActionDetails",
    "researchActionGroups",
    "recommendations",
    "citations",
    "citationsDisplay",
    "glossary",
    "concept",
    "conceptDisplay",
    "dossier",
    "dossierDisplay",
    "sourceFact",
    "sourceFactDisplay",
    "evidence",
    "evidenceDisplay",
    "worknet",
    "worknetDisplay",
    "runtimeProbeDisplay",
    "runtimeProbeHighlights",
    "sourceImpact",
    "sourceImpactDisplay",
    "freshness",
    "freshnessDisplay",
    "relatedSourceHighlights",
    "relatedReferenceHighlights",
]

KNOWLEDGE_OVERVIEW_FIELDS = [
    "generatedAt",
    "headline",
    "summary",
    "topicCount",
    "rawTopicIndexCount",
    "referenceEntryCount",
    "sourceDirectoryCount",
    "affectedSourceDirectoryCount",
    "stableTopicCount",
    "affectedTopicCount",
    "worknetTopicCount",
    "glossaryTermCount",
    "officialSourceCount",
    "pendingReviewCount",
    "changedSourceCount",
    "highestPriority",
    "primaryActionLabel",
    "primaryActionCommand",
]

KNOWLEDGE_DIRECTORY_ENTRY_FIELDS = [
    "key",
    "rawKey",
    "canonicalTopicKey",
    "label",
    "kind",
    "headline",
    "summary",
    "summaryPreview",
    "plainLanguage",
    "runtimeSummary",
    "runtimeProbeCount",
    "canonicalWorknetId",
    "predecessorWorknetIds",
    "officialSkillUri",
    "minStakeHint",
    "minStakeHintDisplay",
    "runtimeSpecState",
    "runtimeSpecStateDisplay",
    "queryCommand",
    "primaryCommand",
    "freshnessStatus",
    "highestPriority",
    "affectedSourceKeys",
    "sourceKeys",
    "officialUrls",
    "aliases",
    "worknetKey",
    "worknetName",
    "automationLevel",
    "riskLevel",
    "recommendedRole",
    "surfaceLevel",
    "recommendations",
    "citations",
]

SOURCE_DIRECTORY_ENTRY_FIELDS = [
    "key",
    "label",
    "name",
    "headline",
    "summary",
    "summaryPreview",
    "queryCommand",
    "primaryCommand",
    "url",
    "kind",
    "kindDisplay",
    "trustTier",
    "trustTierDisplay",
    "worknetKey",
    "canonicalWorknetId",
    "predecessorWorknetIds",
    "officialSkillUri",
    "minStakeHint",
    "minStakeHintDisplay",
    "runtimeSpecState",
    "runtimeSpecStateDisplay",
    "freshnessStatus",
    "highestPriority",
    "runtimeSummary",
    "runtimeProbeCount",
    "driftStatus",
    "driftStatusDisplay",
    "changedFieldsDisplay",
    "impactedTopicsDisplay",
    "impactedWorknetsDisplay",
    "reviewHint",
]

KNOWLEDGE_ATLAS_GAP_FIELDS = [
    "key",
    "label",
    "category",
    "status",
    "summary",
    "worknetKey",
    "worknetName",
    "sourceKey",
    "sourceName",
    "recommendedActionLabel",
    "recommendedActionCommand",
]

KNOWLEDGE_ATLAS_QUERY_FIELDS = [
    "topic",
    "status",
    "resolvedTopicKey",
    "resolvedTopicLabel",
    "progress",
    "headline",
    "summary",
    "plainLanguage",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
    "primaryCommand",
    "primaryUserAction",
    "primaryUserActionDisplay",
    "primaryUserActionCommand",
    "userActionDetails",
    "researchActionGroups",
    "recommendations",
    "knowledgeOverview",
    "reviewQueueSummary",
    "focusTopics",
    "worknetDirectory",
    "topicDirectory",
    "referenceDirectory",
    "sourceDirectory",
    "glossaryDirectory",
    "conceptDirectory",
    "atlasGaps",
]

KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS = [
    "topic",
    "status",
    "progress",
    "headline",
    "summary",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
    "primaryCommand",
    "primaryUserAction",
    "primaryUserActionDisplay",
    "primaryUserActionCommand",
    "userActionDetails",
    "researchActionGroups",
    "recommendations",
    "citations",
    "reviewQueueSummary",
    "reviewQueueTopEntries",
    "reviewQueueTopEntriesDisplay",
    "sourceDriftSummary",
    "sourceImpactSummary",
    "changedSources",
    "changedSourcesDisplay",
    "impacts",
    "impactsDisplay",
    "reviewQueue",
    "knowledgeReviewQueue",
]

SOURCE_QUERY_FIELDS = [
    "sourceKey",
    "sourceName",
    "sourceNameDisplay",
    "status",
    "progress",
    "headline",
    "summary",
    "summaryPreview",
    "summaryDisplay",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
    "primaryCommand",
    "primaryUserAction",
    "primaryUserActionDisplay",
    "primaryUserActionCommand",
    "userActionDetails",
    "researchActionGroups",
    "recommendations",
    "reviewScope",
    "topicHighlights",
    "factHighlights",
    "worknetHighlights",
    "evidenceHighlights",
    "source",
    "sourceDisplay",
    "drift",
    "driftDisplay",
    "impact",
    "impactDisplay",
    "facts",
    "factsDisplay",
    "evidence",
    "evidenceDisplay",
    "dossiers",
    "dossiersDisplay",
    "glossary",
    "glossaryDisplay",
    "worknets",
    "worknetsDisplay",
    "runtimeProbeDisplay",
    "runtimeProbeHighlights",
    "citationsDisplay",
]

CHANGED_SOURCES_QUERY_FIELDS = [
    "query",
    "status",
    "progress",
    "headline",
    "summary",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
    "primaryCommand",
    "primaryUserAction",
    "primaryUserActionDisplay",
    "primaryUserActionCommand",
    "userActionDetails",
    "researchActionGroups",
    "recommendations",
    "sourceDriftSummary",
    "sourceImpactSummary",
    "changedSources",
    "changedSourcesDisplay",
    "changedSourceHighlights",
    "impacts",
    "impactsDisplay",
    "reviewQueue",
    "knowledgeReviewQueueSummary",
    "reviewQueueTopEntriesDisplay",
]

GLOSSARY_QUERY_FIELDS = [
    "query",
    "match",
    "matchDisplay",
]

KNOWLEDGE_HIGHLIGHT_FIELDS_BY_KIND = {
    "topic": TOPIC_HIGHLIGHT_FIELDS,
    "reference": REFERENCE_HIGHLIGHT_FIELDS,
    "source": SOURCE_HIGHLIGHT_FIELDS,
    "fact": FACT_HIGHLIGHT_FIELDS,
    "worknet": WORKNET_HIGHLIGHT_FIELDS,
    "evidence": EVIDENCE_HIGHLIGHT_FIELDS,
}


def normalize_knowledge_highlight_payload(record: Any, fields: list[str]) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, fields)


def normalize_freshness_payload(record: Any, fields: list[str]) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, fields)


def normalize_drift_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, DRIFT_DISPLAY_FIELDS)


def normalize_source_impact_item_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, SOURCE_IMPACT_ITEM_FIELDS)


def normalize_source_impact_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, SOURCE_IMPACT_DISPLAY_FIELDS)


def normalize_source_record_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, SOURCE_RECORD_DISPLAY_FIELDS)


def normalize_citation_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, CITATION_DISPLAY_FIELDS)


def normalize_dossier_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, DOSSIER_DISPLAY_FIELDS)


def normalize_source_fact_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, SOURCE_FACT_DISPLAY_FIELDS)


def normalize_worknet_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, WORKNET_DISPLAY_FIELDS)


def normalize_glossary_item_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, GLOSSARY_ITEM_FIELDS)


def normalize_glossary_query_match_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, GLOSSARY_QUERY_MATCH_FIELDS)


def normalize_concept_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, CONCEPT_DIRECTORY_ITEM_FIELDS)


def normalize_review_scope_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, REVIEW_SCOPE_FIELDS)


def normalize_query_payload(record: Any, fields: list[str]) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, fields)


def normalize_knowledge_overview_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, KNOWLEDGE_OVERVIEW_FIELDS)


def normalize_knowledge_directory_entry_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, KNOWLEDGE_DIRECTORY_ENTRY_FIELDS)


def normalize_source_directory_entry_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, SOURCE_DIRECTORY_ENTRY_FIELDS)


def normalize_knowledge_atlas_gap_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, KNOWLEDGE_ATLAS_GAP_FIELDS)


def normalize_knowledge_review_queue_summary(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, KNOWLEDGE_REVIEW_QUEUE_SUMMARY_FIELDS)


def normalize_affected_topic_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, AFFECTED_TOPIC_FIELDS)


def knowledge_highlight_fields(kind: Any, fields: Optional[list[str]] = None) -> list[str]:
    if isinstance(fields, list):
        return fields
    return KNOWLEDGE_HIGHLIGHT_FIELDS_BY_KIND.get(str(kind or "").strip().lower(), KNOWLEDGE_HIGHLIGHT_BASE_FIELDS)
