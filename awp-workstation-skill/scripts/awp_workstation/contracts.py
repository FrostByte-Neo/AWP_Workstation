"""Public response contract fields and projection helpers."""

from __future__ import annotations

from typing import Any


PREFLIGHT_PUBLIC_FIELDS = [
    "walletReady",
    "registered",
    "agentAddress",
    "recipient",
    "nextAction",
    "blockingIssues",
    "plainLanguageSummary",
    "progress",
]

CAPABILITY_PUBLIC_FIELDS = [
    "worknetId",
    "name",
    "symbol",
    "status",
    "skillsUri",
    "officialSkill",
    "minStake",
    "runnable",
    "automationLevel",
    "riskLevel",
    "recommendedRole",
    "reason",
]

PLAYBOOK_PUBLIC_FIELDS = [
    "goal",
    "role",
    "loop",
    "requiredSkill",
    "resumeStatus",
    "resumeStatusDisplay",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
    "primaryUserAction",
    "primaryUserActionDisplay",
    "primaryUserActionCommand",
    "userActionDetails",
    "commands",
    "successMetrics",
    "failureModes",
    "humanConfirmations",
]

REVIEW_PUBLIC_FIELDS = [
    "generatedAt",
    "worknetKey",
    "worknetName",
    "status",
    "statusDisplay",
    "resumeStatus",
    "resumeStatusDisplay",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
    "headline",
    "dailySummary",
    "reporterNote",
    "knowledgeContext",
    "knowledgeReferenceHighlights",
    "knowledgeSourceHighlights",
    "primaryUserAction",
    "primaryUserActionDisplay",
    "primaryUserActionCommand",
    "workDone",
    "estimatedRewards",
    "failures",
    "strategyChanges",
    "userActions",
    "userActionDetails",
    "progress",
]

PLAYBOOK_COMMAND_PUBLIC_FIELDS = [
    "argv",
    "category",
    "command",
    "commandGroupKey",
    "commandGroupLabel",
    "commandTier",
    "commandTierLabel",
    "commandTierRank",
    "cwd",
    "description",
    "executionPolicy",
    "label",
    "rawLabel",
    "requires_confirmation",
    "selectedByDefault",
]

USER_ACTION_DETAIL_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "command",
    "description",
    "displayLabel",
    "label",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
]

PUBLIC_ACTION_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "description",
    "label",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
]

START_RESPONSE_FIELDS = [
    "_internal",
    "executionHeadline",
    "executionState",
    "executionStateDisplay",
    "intro",
    "knowledgeFocusTopics",
    "knowledgeOverview",
    "knowledgeReferenceHighlights",
    "knowledgeReviewQueueSummary",
    "knowledgeSourceHighlights",
    "primaryUserAction",
    "primaryUserActionCommand",
    "primaryUserActionDisplay",
    "progress",
    "recoveryDecision",
    "resumeStatus",
    "resumeStatusDisplay",
    "userActionDetails",
    "user_actions",
    "user_message",
]

RUN_RESPONSE_FIELDS = [
    "confirmationQueue",
    "executedSteps",
    "executionHeadline",
    "executionState",
    "executionStateDisplay",
    "followUpActions",
    "headline",
    "knowledgeContext",
    "knowledgeReferenceHighlights",
    "knowledgeSourceHighlights",
    "mode",
    "nextAction",
    "playbookSource",
    "primaryUserAction",
    "primaryUserActionCommand",
    "primaryUserActionDisplay",
    "progress",
    "recoveryDecision",
    "resumeStatus",
    "resumeStatusDisplay",
    "resumedFromState",
    "runtimeGuidance",
    "selectedWorknetKey",
    "selectedWorknetName",
    "stateRoot",
    "status",
    "userActionDetails",
    "userMessage",
    "warnings",
]

WORKSTATION_STATUS_INTERNAL_FIELDS = [
    "_internal",
    "answer",
    "error",
    "executionHeadline",
    "executionState",
    "executionStateDisplay",
    "generatedAt",
    "headline",
    "intent",
    "knowledgeCaveat",
    "knowledgeFocusTopics",
    "knowledgeOverview",
    "knowledgeRecord",
    "missingCaches",
    "knowledgeReferenceHighlights",
    "knowledgeReviewQueueSummary",
    "knowledgeSourceHighlights",
    "latestReview",
    "primaryUserAction",
    "primaryUserActionCommand",
    "primaryUserActionDisplay",
    "progress",
    "query",
    "readOnly",
    "recoveryDecision",
    "researchActionGroups",
    "resumeStatus",
    "resumeStatusDisplay",
    "sourceEvidenceHighlights",
    "sourceFactHighlights",
    "sourceKey",
    "sourceName",
    "sourceRecord",
    "sourceTopicHighlights",
    "sourceWorknetHighlights",
    "status",
    "targetWorknetDisplay",
    "userActionDetails",
    "userActions",
    "worknetKey",
    "worknetName",
]

PARAMETER_SCHEMA_ITEM_FIELDS = [
    "displayName",
    "name",
    "placeholder",
    "placeholderDisplay",
    "prompt",
    "promptDisplay",
]

FOLLOW_UP_ACTION_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "argv",
    "command",
    "description",
    "displayLabel",
    "label",
    "requiresConfirmation",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
    "safeToAutoRun",
]

CONFIRMED_ACTION_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "chain",
    "command",
    "displayLabel",
    "estimatedCost",
    "incompleteFields",
    "label",
    "risk",
    "requiredInputs",
    "requiresConfirmation",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
    "target",
]

CONFIRMATION_SECURITY_FIELDS = [
    "chain",
    "target",
    "estimatedCost",
    "risk",
]

CONFIRMATION_QUEUE_ITEM_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "chain",
    "command",
    "description",
    "displayLabel",
    "estimatedCost",
    "incompleteFields",
    "label",
    "risk",
    "requiredInputs",
    "requiresConfirmation",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
    "target",
]

SELECTED_CONFIRMATION_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "chain",
    "displayLabel",
    "estimatedCost",
    "incompleteFields",
    "label",
    "risk",
    "requiredInputs",
    "requiredInputsDisplay",
    "target",
]

BACKGROUND_RECORD_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "alive",
    "argv",
    "cwd",
    "displayLabel",
    "label",
    "logPath",
    "logTail",
    "pid",
    "startedAt",
    "summary",
    "summaryDisplay",
]

BACKGROUND_SUMMARY_FIELDS = [
    "detail",
    "headline",
    "state",
]

SELECTED_BACKGROUND_PREVIEW_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "alive",
    "displayLabel",
    "label",
    "logPath",
    "pid",
    "stopCommand",
]

SELECTED_BACKGROUND_ERROR_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "alive",
    "displayLabel",
    "error",
    "label",
    "logPath",
    "pid",
    "stopCommand",
]

RECOVERY_DECISION_FIELDS = [
    "actions",
    "decision",
    "headline",
    "lastWorknetName",
    "message",
    "preferredWorknetName",
    "primaryActionLabel",
    "restartActionLabel",
    "staleReason",
    "status",
    "statusDisplay",
    "switchActionLabel",
]

EXECUTED_STEP_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "argv",
    "category",
    "cwd",
    "detailDisplay",
    "displayLabel",
    "executionPolicy",
    "label",
    "resultSummary",
    "status",
    "statusDisplay",
    "stepGroupKey",
    "stepGroupLabel",
    "stepGroupRank",
    "stepTier",
    "stepTierLabel",
    "stepTierRank",
]

RUNTIME_GUIDANCE_FIELDS = [
    "actionMap",
    "message",
    "messageDisplay",
    "messageRaw",
    "nextCommand",
    "nextCommandDisplay",
    "nextCommandRaw",
    "preview",
    "previewDisplay",
    "previewRaw",
    "state",
    "userActionDetails",
    "userActions",
    "userActionsDisplay",
    "userActionsRaw",
]

RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS = [
    "actionMap",
    "message",
    "messageDisplay",
    "messageRaw",
    "nextAction",
    "nextCommand",
    "nextCommandDisplay",
    "nextCommandRaw",
    "preview",
    "previewDisplay",
    "previewRaw",
    "state",
    "userActionDetails",
    "userActions",
    "userActionsDisplay",
    "userActionsRaw",
]

RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "command",
    "commandDisplay",
    "commandRaw",
    "description",
    "descriptionDisplay",
    "displayLabel",
    "label",
    "labelRaw",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
]

RUN_RESPONSE_BRIEFING_FIELDS = [
    "executionHeadline",
    "executionState",
    "executionStateDisplay",
    "headline",
    "knowledgeContext",
    "knowledgeReferenceHighlights",
    "knowledgeSourceHighlights",
    "primaryUserAction",
    "primaryUserActionCommand",
    "primaryUserActionDisplay",
    "recoveryDecision",
    "resumeStatus",
    "resumeStatusDisplay",
    "userActionDetails",
    "userMessage",
]

RESUME_RECOVERY_BRIEFING_FIELDS = [
    "decision",
    "headline",
    "message",
    "status",
]

EXECUTED_STEP_RESULT_DISPLAY_FIELDS = [
    "code",
    "codeDisplay",
    "preview",
    "previewDisplay",
    "previewRaw",
    "stderrDisplay",
    "stderrDisplayDisplay",
    "stderrDisplayRaw",
    "stdoutDisplay",
    "structuredPreviewDisplay",
    "summary",
    "summaryDisplay",
    "summaryRaw",
]

EXECUTED_STEP_STDOUT_DISPLAY_FIELDS = [
    "detail",
    "detailDisplay",
    "detailRaw",
    "errorSummary",
    "errorSummaryDisplay",
    "guidance",
    "kind",
    "message",
    "messageDisplay",
    "messageRaw",
    "nextCommandDisplay",
    "preview",
    "previewDisplay",
    "previewRaw",
    "state",
    "stateDisplay",
    "structuredPreviewDisplay",
    "summary",
]

WORKSTATION_STATUS_PUBLIC_FIELDS = [
    "query",
    "intent",
    "progress",
    "headline",
    "answer",
    "status",
    "readOnly",
    "missingCaches",
    "error",
    "resumeStatus",
    "resumeStatusDisplay",
    "executionState",
    "executionStateDisplay",
    "executionHeadline",
    "worknetKey",
    "worknetName",
    "sourceKey",
    "sourceName",
    "knowledgeCaveat",
    "recoveryDecision",
    "knowledgeReviewQueueSummary",
    "knowledgeOverview",
    "knowledgeFocusTopics",
    "knowledgeReferenceHighlights",
    "knowledgeSourceHighlights",
    "sourceTopicHighlights",
    "sourceFactHighlights",
    "sourceWorknetHighlights",
    "sourceEvidenceHighlights",
    "researchActionGroups",
    "primaryUserAction",
    "primaryUserActionDisplay",
    "primaryUserActionCommand",
    "userActions",
    "userActionDetails",
]

RESEARCH_HIGHLIGHT_GROUP_LABELS = {
    "current": "Current item",
    "control": "Control",
    "sources": "Priority sources",
    "topics": "Topics",
    "worknets": "WorkNet entries",
    "references": "References",
    "facts": "Facts",
    "evidence": "Evidence",
    "background": "Background tasks",
    "review": "Review",
    "confirmations": "Pending confirmations",
}

RESEARCH_HIGHLIGHT_GROUP_RANKS = {
    "current": 0,
    "control": 1,
    "sources": 2,
    "topics": 3,
    "worknets": 4,
    "references": 5,
    "facts": 6,
    "evidence": 7,
    "background": 8,
    "review": 9,
    "confirmations": 10,
}

RESEARCH_HIGHLIGHT_TIER_LABELS = {
    "current": "Current",
    "overview": "Overview",
    "related": "Related",
    "queued": "Queued",
}

RESEARCH_HIGHLIGHT_TIER_RANKS = {
    "current": 0,
    "overview": 1,
    "related": 2,
    "queued": 3,
}

EXECUTION_ACTION_GROUP_LABEL_OVERRIDES = {
    "current": "Current action",
    "control": "Control actions",
    "sources": "Source actions",
    "topics": "Knowledge actions",
    "worknets": "Work routes",
    "background": "Background tasks",
    "review": "Review",
    "confirmations": "Pending confirmations",
    "references": "References",
}

PLAYBOOK_COMMAND_GROUP_LABELS = {
    "current": "Current execution",
    "setup": "Setup",
    "inspect": "Inspection and diagnostics",
    "control": "Runtime control",
    "confirmations": "Pending confirmations",
}

STEP_GROUP_LABELS = {
    "current": "Current execution step",
    "setup": "Setup step",
    "inspect": "Inspection step",
    "control": "Control step",
    "confirmations": "Pending confirmation step",
    "background": "Background step",
    "sources": "Source step",
    "topics": "Knowledge step",
    "review": "Review step",
    "references": "Reference step",
    "worknets": "Work route step",
}

WORKSTATION_PREFERENCES_PUBLIC_FIELDS = [
    "generatedAt",
    "message",
    "appliedChanges",
    "userPreferences",
    "stateRoot",
]


def project_fields(record: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {field: record.get(field) for field in fields}


def normalize_parameter_schema_item_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, PARAMETER_SCHEMA_ITEM_FIELDS)


def normalize_runtime_guidance_user_action_detail_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS)


def normalize_runtime_guidance_contract_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS)


def normalize_executed_step_result_display_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, EXECUTED_STEP_RESULT_DISPLAY_FIELDS)


def normalize_executed_step_stdout_display_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, EXECUTED_STEP_STDOUT_DISPLAY_FIELDS)


def normalize_background_summary_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, BACKGROUND_SUMMARY_FIELDS)
