#!/usr/bin/env python3
"""Shared helpers for the AWP workstation skill."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import shlex
import signal
import subprocess
import tempfile
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_EXPORT_ROOT = SKILL_ROOT / "references" / "generated"
STATE_ENV_VAR = "AWP_WORKSTATION_HOME"
DEFAULT_STATE_ROOT = Path.home() / ".awp-workstation"
DEFAULT_FALLBACK_STATE_ROOT = Path("/tmp/awp-workstation")
DEFAULT_RPC_URL = os.environ.get("AWP_RPC_URL", "https://api.awp.sh/v2")
SOURCE_IMPACT_SCHEMA_VERSION = 2
KNOWLEDGE_REVIEW_QUEUE_SCHEMA_VERSION = 1
KNOWLEDGE_CATALOG_SCHEMA_VERSION = 12
OFFICIAL_SKILL_ALLOWLIST_PREFIXES = ("https://github.com/awp-worknet/",)
DEFAULT_FETCH_USER_AGENT = "awp-workstation-skill/0.1.0"
WORKNET_ID_BASE = 100_000_000
CHAIN_ALIAS_TO_ID = {
    "ethereum": 1,
    "bsc": 56,
    "base": 8453,
    "arbitrum": 42161,
    "optimism": 10,
    "polygon": 137,
}

COMMAND_HINT_RE = re.compile(
    r"(python3\s+scripts/[A-Za-z0-9._/\-]+(?:\s+--?[A-Za-z0-9._/\-<>$]+(?:\s+[A-Za-z0-9._/\-<>:$]+)?)*)"
)
PLACEHOLDER_TOKEN_RE = re.compile(r"^<([^>]+)>$")

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
    "knowledgeReferenceHighlights",
    "knowledgeReviewQueueSummary",
    "knowledgeSourceHighlights",
    "latestReview",
    "primaryUserAction",
    "primaryUserActionCommand",
    "primaryUserActionDisplay",
    "progress",
    "query",
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

CONFIRMATION_QUEUE_ITEM_FIELDS = [
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
    "requiredInputs",
    "requiresConfirmation",
    "researchGroupKey",
    "researchGroupLabel",
    "researchGroupRank",
    "researchTier",
    "researchTierLabel",
    "researchTierRank",
]

SELECTED_CONFIRMATION_FIELDS = [
    "actionGroupKey",
    "actionGroupLabel",
    "actionGroupRank",
    "actionTier",
    "actionTierLabel",
    "actionTierRank",
    "displayLabel",
    "label",
    "requiredInputs",
    "requiredInputsDisplay",
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

EXECUTED_STEP_RESULT_DISPLAY_FIELDS = [
    "code",
    "codeDisplay",
    "preview",
    "previewDisplay",
    "previewRaw",
    "stderrDisplay",
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
    "current": "当前条目",
    "control": "百科总控",
    "sources": "高优先来源",
    "topics": "高层主题",
    "worknets": "WorkNet 入口",
    "references": "底层参考",
    "facts": "事实记录",
    "evidence": "证据条目",
    "background": "后台任务",
    "review": "复盘与复核",
    "confirmations": "待确认动作",
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
    "current": "当前",
    "overview": "总览",
    "related": "关联",
    "queued": "待重审",
}

RESEARCH_HIGHLIGHT_TIER_RANKS = {
    "current": 0,
    "overview": 1,
    "related": 2,
    "queued": 3,
}

EXECUTION_ACTION_GROUP_LABEL_OVERRIDES = {
    "current": "当前动作",
    "control": "控制动作",
    "sources": "来源相关",
    "topics": "知识相关",
    "worknets": "工作路线",
    "background": "后台任务",
    "review": "复盘与复核",
    "confirmations": "待确认动作",
    "references": "底层参考",
}

PLAYBOOK_COMMAND_GROUP_LABELS = {
    "current": "当前执行",
    "setup": "环境准备",
    "inspect": "检查与诊断",
    "control": "运行控制",
    "confirmations": "待确认动作",
}

STEP_GROUP_LABELS = {
    "current": "当前执行步骤",
    "setup": "环境准备步骤",
    "inspect": "检查步骤",
    "control": "控制步骤",
    "confirmations": "待确认步骤",
    "background": "后台步骤",
    "sources": "来源相关步骤",
    "topics": "知识相关步骤",
    "review": "复盘步骤",
    "references": "参考步骤",
    "worknets": "工作路线步骤",
}

WORKSTATION_PREFERENCES_PUBLIC_FIELDS = [
    "generatedAt",
    "message",
    "appliedChanges",
    "userPreferences",
    "stateRoot",
]

DEFAULT_USER_PREFERENCES: dict[str, Any] = {
    "allowAssetActions": False,
    "allowThirdPartySkills": False,
    "autopilotMode": "non-financial-only",
    "preferredWorknet": "mine",
    "observeBeforePredictHours": 24,
    "riskProfile": "conservative",
    "updatedAt": None,
}

SAFETY_RULES: list[dict[str, str]] = [
    {
        "id": "no-private-keys",
        "level": "critical",
        "rule": "Never ask for, receive, print, or store a private key, seed phrase, or personal wallet password.",
    },
    {
        "id": "work-wallet-only",
        "level": "high",
        "rule": "Default to the agent work wallet and remind the user not to store personal assets in it.",
    },
    {
        "id": "confirm-value-actions",
        "level": "critical",
        "rule": "All stake, allocate, deallocate, bind, recipient, delegate, claim, order, vote, transfer, and inscribe actions require explicit confirmation.",
    },
    {
        "id": "gasless-registration-disclose",
        "level": "medium",
        "rule": "Gasless registration may run automatically, but the workstation must explain what happened in plain language.",
    },
    {
        "id": "no-handwritten-calldata",
        "level": "critical",
        "rule": "Do not handwrite calldata or interact with contracts directly when an official skill or CLI exists.",
    },
    {
        "id": "third-party-default-off",
        "level": "high",
        "rule": "Third-party skills, non-official APIs, and automated capital strategies stay off until the user approves them.",
    },
]

OFFICIAL_WEB_SOURCES: list[dict[str, Any]] = [
    {
        "key": "awp-home",
        "name": "AWP home",
        "url": "https://awp.pro/",
        "kind": "protocol",
        "trustTier": 1,
        "summary": "Protocol entry point and quickstart.",
    },
    {
        "key": "awp-worknets",
        "name": "AWP worknet directory",
        "url": "https://awp.pro/worknet",
        "kind": "directory",
        "trustTier": 1,
        "summary": "Public worknet list and high-level worknet descriptions.",
    },
    {
        "key": "awp-aip",
        "name": "AWP AIP registry",
        "url": "https://awp.pro/aip",
        "kind": "directory",
        "trustTier": 1,
        "summary": "Public proposal index for worknet specs.",
    },
    {
        "key": "awp-whitepaper",
        "name": "AWP whitepaper",
        "url": "https://awp.pro/awp-whitepaper.pdf",
        "kind": "paper",
        "trustTier": 1,
        "summary": "Canonical protocol paper for RootNet, WorkNet, emission, staking, and DAO mechanics.",
    },
    {
        "key": "awp-skill",
        "name": "awp-core/awp-skill",
        "url": "https://github.com/awp-core/awp-skill",
        "kind": "skill",
        "trustTier": 1,
        "summary": "Protocol-official RootNet skill and JSON-RPC reference.",
    },
    {
        "key": "awp-skill-readme-raw",
        "name": "awp-skill README raw",
        "url": "https://raw.githubusercontent.com/awp-core/awp-skill/main/README.md",
        "kind": "skill-doc",
        "trustTier": 1,
        "summary": "Raw upstream README suitable for workstation diffing and future refresh.",
    },
    {
        "key": "aip-001-raw",
        "name": "AIP-001 Mine raw",
        "url": "https://raw.githubusercontent.com/awp-core/AIPs/main/AIPS/aip-001.md",
        "kind": "aip",
        "trustTier": 1,
        "worknetKey": "mine",
        "summary": "Mine WorkNet primary spec.",
    },
    {
        "key": "aip-002-raw",
        "name": "AIP-002 Predict raw",
        "url": "https://raw.githubusercontent.com/awp-core/AIPs/main/AIPS/aip-002.md",
        "kind": "aip",
        "trustTier": 1,
        "worknetKey": "predict",
        "summary": "Predict WorkNet primary spec.",
    },
    {
        "key": "awp-live-query",
        "name": "AWP live JSON-RPC",
        "url": "https://api.awp.sh/v2",
        "kind": "live-api",
        "trustTier": 1,
        "summary": "Official live JSON-RPC used to resolve current worknet IDs, skills URIs, and statuses.",
    },
    {
        "key": "minework-home",
        "name": "Mine home",
        "url": "https://minework.net/",
        "kind": "worknet",
        "trustTier": 1,
        "worknetKey": "mine",
        "summary": "Official Mine operator surface and dataset/economic summary.",
    },
    {
        "key": "mine-skill-raw",
        "name": "Mine skill raw",
        "url": "https://raw.githubusercontent.com/awp-worknet/mine-skill/main/SKILL.md",
        "kind": "skill-doc",
        "trustTier": 1,
        "worknetKey": "mine",
        "summary": "Raw official Mine skill spec.",
    },
    {
        "key": "agentpredict-home",
        "name": "Predict home",
        "url": "https://agentpredict.work/",
        "kind": "worknet",
        "trustTier": 1,
        "worknetKey": "predict",
        "summary": "Official Predict operator surface.",
    },
    {
        "key": "predict-skill-raw",
        "name": "Predict skill raw",
        "url": "https://raw.githubusercontent.com/awp-worknet/prediction-skill/main/SKILL.md",
        "kind": "skill-doc",
        "trustTier": 1,
        "worknetKey": "predict",
        "summary": "Raw official Predict skill spec.",
    },
    {
        "key": "awp-staking",
        "name": "AWP staking",
        "url": "https://awp.pro/staking",
        "kind": "protocol-surface",
        "trustTier": 1,
        "summary": "Official staking surface for veAWP and AWP Power.",
    },
    {
        "key": "awp-dao",
        "name": "AWP DAO",
        "url": "https://awp.pro/dao",
        "kind": "protocol-surface",
        "trustTier": 1,
        "summary": "Official governance surface for proposals and veAWP voting.",
    },
    {
        "key": "awp-testnet",
        "name": "AWP testnet benchmark",
        "url": "https://awp.pro/testnet",
        "kind": "worknet-surface",
        "trustTier": 1,
        "summary": "Official Benchmark testnet onboarding and activity checker.",
    },
    {
        "key": "awp-blog",
        "name": "AWP blog",
        "url": "https://awp.pro/blog",
        "kind": "docs",
        "trustTier": 1,
        "summary": "Official updates, guides, and conceptual deep dives.",
    },
    {
        "key": "gov-works",
        "name": "GovNet",
        "url": "https://gov.works/",
        "kind": "worknet",
        "trustTier": 1,
        "worknetKey": "gov",
        "summary": "Official governance market page and gov skill reference.",
    },
    {
        "key": "gov-markets-api",
        "name": "Gov markets API",
        "url": "https://api.gov.works/v1/markets",
        "kind": "live-api",
        "trustTier": 1,
        "worknetKey": "gov",
        "summary": "Official live GovNet market feed listing current worknet share symbols and market phases.",
    },
    {
        "key": "gov-skill-raw",
        "name": "Gov skill raw",
        "url": "https://raw.githubusercontent.com/awp-worknet/gov-skill/main/SKILL.md",
        "kind": "skill-doc",
        "trustTier": 1,
        "worknetKey": "gov",
        "summary": "Raw official Gov skill spec.",
    },
    {
        "key": "ardinals-agents",
        "name": "Ardi operator page",
        "url": "https://www.ardinals.com/agents",
        "kind": "worknet",
        "trustTier": 1,
        "worknetKey": "ardi",
        "summary": "Official Ardi agent onboarding page.",
    },
    {
        "key": "ardi-skill-raw",
        "name": "Ardi skill raw",
        "url": "https://raw.githubusercontent.com/awp-worknet/ardi-skill/main/SKILL.md",
        "kind": "skill-doc",
        "trustTier": 1,
        "worknetKey": "ardi",
        "summary": "Raw official Ardi skill spec.",
    },
    {
        "key": "kya-human",
        "name": "KYA verify human",
        "url": "https://kya.link/verify/human",
        "kind": "service",
        "trustTier": 1,
        "worknetKey": "kya",
        "summary": "Official KYA human verification and kya-skill reference.",
    },
    {
        "key": "kya-skill-raw",
        "name": "KYA skill raw",
        "url": "https://raw.githubusercontent.com/awp-worknet/kya-skill/main/SKILL.md",
        "kind": "skill-doc",
        "trustTier": 1,
        "worknetKey": "kya",
        "summary": "Raw official KYA skill spec.",
    },
    {
        "key": "tmr-skill",
        "name": "TMR skill URI",
        "url": "https://github.com/awp-worknet/tmr-skill",
        "kind": "skill",
        "trustTier": 1,
        "worknetKey": "tmr",
        "summary": "Official live skill URI currently returned for the TMR worknet.",
    },
    {
        "key": "community-skill",
        "name": "Community skill URI",
        "url": "https://github.com/awp-worknet/com-skill",
        "kind": "skill",
        "trustTier": 1,
        "worknetKey": "community",
        "summary": "Official live skill URI currently returned for the Community worknet.",
    },
]

CORE_DEPENDENCY_SKILLS: list[dict[str, Any]] = [
    {
        "key": "awp-skill",
        "name": "AWP RootNet Skill",
        "installUri": "https://github.com/awp-core/awp-skill",
        "official": True,
        "autoInstallEligible": False,
        "reason": "Protocol dependency used for registration, staking, allocation, and network query flows.",
    },
    {
        "key": "awp-wallet",
        "name": "AWP Wallet",
        "installUri": "https://github.com/awp-core/awp-wallet",
        "official": True,
        "autoInstallEligible": False,
        "reason": "Local work-wallet CLI used by workstation and child skills.",
    },
]

DERIVED_SOURCE_FACTS: list[dict[str, Any]] = [
    {
        "key": "protocol-core",
        "topic": "Protocol Core",
        "sourceKeys": ["awp-home", "awp-whitepaper", "awp-skill", "awp-skill-readme-raw"],
        "facts": [
            "AWP is a decentralized agent-work protocol with RootNet plus task-specific WorkNets.",
            "Current mainnet chain set is Base, Ethereum, Arbitrum, and BSC.",
            "The public protocol endpoints documented by the official RootNet skill are POST https://api.awp.sh/v2, wss://api.awp.sh/ws/live, and GET https://api.awp.sh/api/health.",
            "Recipient routing matters because agent emissions resolve to the configured recipient address.",
        ],
    },
    {
        "key": "awp-skill-ops",
        "topic": "AWP RootNet Skill",
        "sourceKeys": ["awp-skill", "awp-skill-readme-raw"],
        "facts": [
            "The official RootNet skill is the dependency for registration, staking, allocation, governance, and worknet management.",
            "Its install guidance explicitly says to install awp-skill, install awp-wallet, make awp-wallet discoverable on PATH, then initialize a fresh agent work wallet.",
            "The official guidance says not to ask the user for a password, private key, seed phrase, or other secret during wallet initialization.",
        ],
    },
    {
        "key": "mine-aip",
        "topic": "Mine WorkNet",
        "sourceKeys": ["aip-001-raw", "minework-home", "mine-skill-raw"],
        "facts": [
            "Mine is the first AWP WorkNet and is a permissionless data collection network for crawling, cleaning, and extracting structured web data.",
            "Mine uses daily UTC epochs and $aMine on Base with an exponential-decay emission schedule.",
            "Miners do not need stake, but validators must meet a minimum AWP stake requirement.",
            "The miner workflow is crawl, clean, extract, submit, then participate in epoch settlement and credit-score gating.",
        ],
    },
    {
        "key": "predict-aip",
        "topic": "Predict WorkNet",
        "sourceKeys": ["aip-002-raw", "agentpredict-home", "predict-skill-raw"],
        "facts": [
            "Predict is an AI-native prediction market WorkNet where agents submit predictions together with reasoning on a live CLOB.",
            "Predict uses virtual chips and a chip feed every four hours, which means agents can participate without acquiring tokens first.",
            "Predict has daily UTC epochs and a three-way reward split described in its AIP: owner, participation, and alpha.",
            "The reasoning text is part of the product, so low-duplication and rate-limit discipline are first-class operational concerns.",
        ],
    },
    {
        "key": "predict-skill-facts",
        "topic": "Predict Runtime",
        "sourceKeys": ["predict-skill-raw", "awp-live-query"],
        "facts": [
            "As of May 20, 2026, the official live AWP API resolves Predict to Base worknetId 845300000003 with skills URI https://github.com/awp-worknet/prediction-skill.",
            "The official Predict runtime says every operation should flow through predict-agent commands rather than direct API calls.",
            "The official Predict runtime documents a 1000 AWP allocation requirement on worknetId 845300000003, with KYA delegated staking as an alternative path.",
        ],
    },
    {
        "key": "gov-skill-facts",
        "topic": "GovNet",
        "sourceKeys": ["gov-works", "gov-skill-raw", "gov-markets-api"],
        "facts": [
            "GovNet exposes market listing, order submission, voting, chip split/merge, book watching, and settlement reads.",
            "Public reads work without a wallet, while signed reads and writes resolve the principal through awp-wallet.",
            "GovNet documents both REST and WebSocket endpoints under api.gov.works.",
            "Because signed state changes go through EIP-712 and awp-wallet, trade and vote actions belong in the workstation confirmation queue.",
        ],
    },
    {
        "key": "ardi-skill-facts",
        "topic": "Ardi",
        "sourceKeys": ["ardinals-agents", "ardi-skill-raw"],
        "facts": [
            "Ardi is an agent-only Base worknet for reasoning over riddles and inscribing dictionary NFTs.",
            "All on-chain Ardi actions must go through ardi-agent commands, not direct RPC or handcrafted calldata.",
            "Operational caps include five commits per agent per epoch, five Ardinals held per agent address, and a total supply cap of 21,000 inscriptions.",
            "The skill requires following _internal.next_command exactly, which makes Ardi a command-journal-driven worknet.",
        ],
    },
    {
        "key": "kya-skill-facts",
        "topic": "KYA",
        "sourceKeys": ["kya-human", "kya-skill-raw"],
        "facts": [
            "KYA is a single-shot identity and delegated-staking tool, not a recurring daemon or cron job.",
            "Its config defaults target kya.link, api.awp.sh, and Base mainnet RPC for AWP registry reads.",
            "KYA explicitly says AWP registration is mandatory and that an unregistered agent must hand off to awp-skill for free gasless onboarding before resuming.",
            "Messaging surfaces must emit handoff URLs as plain text and must not ask the user to type wallet session secrets into chat.",
        ],
    },
    {
        "key": "live-worknet-canonical",
        "topic": "Live WorkNet Canonical IDs",
        "sourceKeys": ["awp-live-query"],
        "facts": [
            "As of May 20, 2026, official live read-only queries resolve Base Mine to 845300000002, Predict to 845300000003, Gov to 845300000010, Community to 845300000011, KYA to 845300000012, TMR to 845300000013, and Ardi to 845300000014.",
            "The same live query surface also exposes pending predecessor entries for Gov, Community, KYA, TMR, and Ardi at 845300000005, 845300000006, 845300000007, 845300000008, and 845300000009 respectively.",
        ],
    },
    {
        "key": "tmr",
        "topic": "TMR",
        "sourceKeys": ["awp-live-query", "tmr-skill"],
        "facts": [
            "As of May 20, 2026, official live queries resolve TMR to Base worknetId 845300000013 with skill URI https://github.com/awp-worknet/tmr-skill.",
            "Compared with Mine, Predict, Gov, Ardi, and KYA, the current official TMR source surface is still thin, so the workstation treats it as discoverable but not yet safe to auto-run.",
        ],
    },
    {
        "key": "community",
        "topic": "Community",
        "sourceKeys": ["awp-live-query", "community-skill"],
        "facts": [
            "As of May 20, 2026, official live queries resolve Community to Base worknetId 845300000011 with skill URI https://github.com/awp-worknet/com-skill.",
            "The current official Community source surface is still thinner than the major worknets, so the workstation keeps it in discover-but-don't-auto-run mode until upstream runtime detail improves.",
        ],
    },
    {
        "key": "staking-facts",
        "topic": "Staking and AWP Power",
        "sourceKeys": ["awp-staking", "awp-whitepaper"],
        "facts": [
            "Locking AWP mints a veAWP position NFT and yields AWP Power.",
            "AWP Power scales with both stake size and remaining lock duration.",
            "Some WorkNets require AWP Power for qualification or assignment priority.",
        ],
    },
    {
        "key": "dao-facts",
        "topic": "DAO Governance",
        "sourceKeys": ["awp-dao", "awp-whitepaper"],
        "facts": [
            "veAWP holders propose changes and vote with weight proportional to AWP Power.",
            "The public governance surface currently shows a 4 percent quorum, 8 hour voting delay, 24 hour voting period, and 200K AWP proposal threshold.",
            "A new signal proposal path is documented as gasless sentiment polling rather than on-chain action.",
        ],
    },
    {
        "key": "testnet-facts",
        "topic": "Benchmark Testnet",
        "sourceKeys": ["awp-testnet"],
        "facts": [
            "The public testnet worknet token is $aBench.",
            "Joining the Benchmark testnet starts with installing awp-skill, which creates a wallet and registers the agent automatically and gaslessly.",
            "The testnet surface includes an airdrop checker, agent activity checker, and benchmark leaderboard.",
        ],
    },
    {
        "key": "blog-facts",
        "topic": "Official Guides",
        "sourceKeys": ["awp-blog"],
        "facts": [
            "The official blog contains practical onboarding and conceptual WorkNet explanations.",
            "The published guide sequence includes articles on launching a WorkNet, what AWP is, getting an agent earning quickly, fair launch, and what a WorkNet is.",
        ],
    },
]

DERIVED_TOPIC_DOSSIERS: list[dict[str, Any]] = [
    {
        "key": "protocol-core",
        "kind": "protocol",
        "title": "AWP Protocol Core",
        "summary": "Two-layer agent economy with RootNet for coordination and WorkNets for task-specific execution.",
        "defaultEntrypoint": "awp-skill",
        "whyItExists": "Gives agents a permissionless place to work, earn, and coordinate across many task networks.",
        "operatorLoop": [
            "prepare a dedicated agent work wallet",
            "register or verify agent readiness on RootNet",
            "scan live or cached WorkNet opportunities",
            "pick a safe work loop and route rewards to the resolved recipient",
        ],
        "economics": [
            "AWP is the reserve, staking, and governance asset.",
            "WorkNets issue their own work tokens and may also distribute AWP.",
            "AWP Power comes from staking and affects governance and work priority.",
        ],
        "risks": [
            "wrong recipient routing can send rewards to the wrong address",
            "staking or allocation actions move value and require confirmation",
            "upstream skill drift must not redefine workstation behavior",
        ],
        "sourceKeys": ["awp-home", "awp-whitepaper", "awp-skill", "awp-skill-readme-raw"],
    },
    {
        "key": "awp-skill",
        "kind": "skill",
        "title": "AWP RootNet Skill",
        "summary": "The official dependency skill for registration, staking, allocation, governance, and live protocol reads.",
        "defaultEntrypoint": "awp-skill",
        "whyItExists": "Lets the workstation delegate protocol-native actions to the official runtime instead of hand-rolling contract calls.",
        "operatorLoop": [
            "install awp-skill and awp-wallet",
            "initialize the agent work wallet without asking for secrets",
            "use awp-skill for RootNet registration and lifecycle actions",
        ],
        "economics": [
            "bind, set-recipient, and worknet registration support gasless execution through relay endpoints",
        ],
        "risks": [
            "if a child skill asks for a private key to start work, treat it as suspicious",
            "the workstation should keep awp-skill as a dependency, not a user-facing product surface",
        ],
        "sourceKeys": ["awp-skill", "awp-skill-readme-raw"],
    },
    {
        "key": "mine",
        "kind": "worknet",
        "title": "Mine WorkNet",
        "summary": "Permissionless web-data worknet for crawl, clean, extract, submit, and epoch settlement.",
        "defaultEntrypoint": "mine skill / run_tool.py",
        "whyItExists": "Turns agent web-crawling capability into tokenized structured-data production.",
        "operatorLoop": [
            "discover URLs and datasets",
            "crawl raw pages",
            "clean normalized text",
            "extract schema-conforming records",
            "submit and maintain heartbeat until settlement",
        ],
        "economics": [
            "$aMine is on Base and follows the WorkNet emission schedule.",
            "Miners do not need stake; validators do.",
            "Mine also distributes AWP alongside $aMine in launch phase.",
        ],
        "risks": [
            "quality gates can reject pending submissions at epoch end",
            "shared-IP decay compresses throughput",
            "repeat-crawl and validator checks penalize fabricated data",
        ],
        "sourceKeys": ["aip-001-raw", "minework-home"],
    },
    {
        "key": "predict",
        "kind": "worknet",
        "title": "Predict WorkNet",
        "summary": "AI-native CLOB prediction market where reasoning quality is part of the product.",
        "defaultEntrypoint": "predict-agent",
        "whyItExists": "Lets agents compete on directional predictions and monetize differentiated reasoning.",
        "operatorLoop": [
            "read market context and candidate windows",
            "form a direction thesis with original reasoning",
            "submit prediction or order through the official runtime",
            "track settlement and alpha quality across epochs",
        ],
        "economics": [
            "Predict uses virtual chips with a four-hour feed cadence.",
            "Emission is split across owner, participation, and alpha buckets.",
            "Liquidity is bootstrapped on Base against AWP.",
        ],
        "risks": [
            "duplicate reasoning fails the quality gate",
            "rate-limit discipline matters because markets refresh on short windows",
            "official local runtime is still missing in this workstation",
        ],
        "sourceKeys": ["aip-002-raw", "agentpredict-home", "predict-skill-raw"],
    },
    {
        "key": "gov",
        "kind": "worknet",
        "title": "GovNet",
        "summary": "Weekly emission market and governance-style worknet for orders, votes, chips, and settlement.",
        "defaultEntrypoint": "gov-skill",
        "whyItExists": "Prices WorkNet value and routes emission expectations through agent action.",
        "operatorLoop": [
            "list markets and watch phases",
            "read principal state and chip balances",
            "vote or place orders only with confirmation",
            "monitor fills and settlement outputs",
        ],
        "economics": [
            "chips and worknet shares mediate weekly value expression",
            "signed reads and writes resolve identity through EMG-SIG-V1",
        ],
        "risks": [
            "market phase timing errors can invalidate the plan",
            "doc/server drift exists for some endpoints",
            "all signed writes belong in the confirmation queue",
        ],
        "sourceKeys": ["gov-works", "gov-skill-raw"],
    },
    {
        "key": "ardi",
        "kind": "worknet",
        "title": "Ardi",
        "summary": "Agent-only Base worknet for solving riddles, committing answers, revealing, and inscribing dictionary NFTs.",
        "defaultEntrypoint": "ardi-agent",
        "whyItExists": "Turns agent reasoning over language riddles into an on-chain inscription game.",
        "operatorLoop": [
            "run ardi-agent preflight",
            "follow _internal.next_command exactly",
            "commit high-confidence answers",
            "wait for reveal and inscribe if selected",
        ],
        "economics": [
            "requires Base gas plus either staked AWP on Ardi or the KYA delegated path",
            "daily ARDI emission accrues to held Ardinals and must be claimed",
        ],
        "risks": [
            "manual shell loops are discouraged when auto-mine exists",
            "epoch timing and reveal windows are strict",
            "bond and gas management are operationally important",
        ],
        "sourceKeys": ["ardinals-agents", "ardi-skill-raw"],
    },
    {
        "key": "kya",
        "kind": "worknet-service",
        "title": "KYA",
        "summary": "Identity and delegated-staking service for attestations, recipient routing, and match-making.",
        "defaultEntrypoint": "kya-skill",
        "whyItExists": "Verifies the human or social layer behind an agent and unlocks delegated-staking paths.",
        "operatorLoop": [
            "check existing attestations",
            "handoff to awp-skill registration if preflight says so",
            "run attestation or KYC flow",
            "set recipient or grant delegate only with confirmation",
        ],
        "economics": [
            "delegated staking can avoid direct AWP stake for some flows",
        ],
        "risks": [
            "handoff URLs must be sent as plain text in non-TTY environments",
            "this is event-driven and should never become an unattended loop",
        ],
        "sourceKeys": ["kya-human", "kya-skill-raw"],
    },
    {
        "key": "tmr",
        "kind": "worknet",
        "title": "TMR",
        "summary": "Officially active AWP worknet with a live skill URI, but still thin public operator docs in this workstation.",
        "defaultEntrypoint": "tmr-skill once inspected",
        "whyItExists": "Represents a live official worknet that should be discoverable even before the workstation has full runtime guidance.",
        "operatorLoop": [
            "confirm the live worknet ID and skill URI",
            "install or inspect the official skill before execution",
            "treat all task semantics as unknown until the runtime is verified locally",
        ],
        "economics": [
            "live official queries currently show a zero minimum-stake hint",
        ],
        "risks": [
            "public task documentation is still sparse",
            "the workstation should not auto-run TMR until the skill is inspected locally",
        ],
        "sourceKeys": ["awp-live-query", "tmr-skill"],
    },
    {
        "key": "community",
        "kind": "worknet",
        "title": "Community",
        "summary": "Officially active AWP worknet with a live skill URI, but still thin public operator docs in this workstation.",
        "defaultEntrypoint": "com-skill once inspected",
        "whyItExists": "Captures the active community worknet so the workstation can point users at the official skill path without pretending to know the full task loop.",
        "operatorLoop": [
            "confirm the live worknet ID and skill URI",
            "install or inspect the official skill before execution",
            "treat the work loop as supervised until runtime docs are available locally",
        ],
        "economics": [
            "live official queries currently show a zero minimum-stake hint",
        ],
        "risks": [
            "public task documentation is still sparse",
            "the workstation should not auto-run Community until the skill is inspected locally",
        ],
        "sourceKeys": ["awp-live-query", "community-skill"],
    },
    {
        "key": "staking",
        "kind": "protocol-surface",
        "title": "AWP Staking",
        "summary": "Stake AWP to mint veAWP and derive AWP Power for governance and work priority.",
        "defaultEntrypoint": "awp.pro/staking or awp-skill staking flow",
        "whyItExists": "Turns locked AWP into governance and qualification weight.",
        "operatorLoop": [
            "decide whether a worknet truly needs stake",
            "estimate lock size and duration",
            "confirm the staking action before execution",
            "track veAWP position state and downstream qualification impact",
        ],
        "economics": [
            "AWP Power increases with amount and remaining lock duration",
            "some WorkNets use AWP Power for qualification or priority",
        ],
        "risks": [
            "locking duration affects liquidity and should not be hidden from the user",
            "staking is always value-moving and belongs behind confirmation",
        ],
        "sourceKeys": ["awp-staking", "awp-whitepaper"],
    },
    {
        "key": "dao",
        "kind": "protocol-surface",
        "title": "AWP DAO",
        "summary": "Protocol governance surface for proposals, votes, and signal actions weighted by AWP Power.",
        "defaultEntrypoint": "awp.pro/dao",
        "whyItExists": "Lets the network steer protocol parameters and treasury direction through veAWP voting.",
        "operatorLoop": [
            "read live proposals and phases",
            "evaluate whether the action is an on-chain vote or a gasless signal",
            "confirm every signed governance action",
        ],
        "economics": [
            "proposal threshold is documented as 200K AWP on the public surface",
            "quorum and timing are protocol-level operator constraints",
        ],
        "risks": [
            "governance actions can affect protocol-wide value flows",
            "phase timing matters even for non-market actions",
        ],
        "sourceKeys": ["awp-dao", "awp-whitepaper"],
    },
    {
        "key": "benchmark-testnet",
        "kind": "testnet",
        "title": "Benchmark Testnet",
        "summary": "Testnet worknet for asking questions, solving problems, and building benchmarks.",
        "defaultEntrypoint": "awp.pro/testnet",
        "whyItExists": "Provides a low-stakes public proving ground for agent work and onboarding.",
        "operatorLoop": [
            "install awp-skill",
            "let the agent create a wallet and register gaslessly",
            "discover the Benchmark worknet and start answering or asking questions",
        ],
        "economics": [
            "the public testnet work token is $aBench",
        ],
        "risks": [
            "testnet activity should not be mistaken for mainnet earnings",
        ],
        "sourceKeys": ["awp-testnet"],
    },
    {
        "key": "blog",
        "kind": "docs",
        "title": "AWP Official Guides",
        "summary": "Official practical and conceptual writing that explains WorkNets and onboarding in plain language.",
        "defaultEntrypoint": "awp.pro/blog",
        "whyItExists": "Complements specs with product-facing guidance and onboarding narratives.",
        "operatorLoop": [
            "use blog posts to translate protocol details into simpler guidance",
            "sync derived facts when a new official guide materially changes operator assumptions",
        ],
        "economics": [
            "blog posts do not define consensus rules but do influence onboarding defaults",
        ],
        "risks": [
            "editorial guidance can drift faster than normative specs",
        ],
        "sourceKeys": ["awp-blog"],
    },
]

DERIVED_EVIDENCE_RECORDS: list[dict[str, Any]] = [
    {
        "key": "protocol-two-layer",
        "topicKey": "protocol-core",
        "claim": "AWP uses a two-layer architecture: RootNet coordinates, WorkNets execute task-specific economies.",
        "sourceKey": "awp-whitepaper",
        "locator": "whitepaper abstract and definitions",
        "evidenceType": "normative-overview",
        "stability": "high",
        "rationale": "The whitepaper defines RootNet and WorkNet as the protocol's architectural split.",
    },
    {
        "key": "protocol-endpoints",
        "topicKey": "protocol-core",
        "claim": "The official RootNet skill documents POST https://api.awp.sh/v2, wss://api.awp.sh/ws/live, and GET https://api.awp.sh/api/health as public protocol endpoints.",
        "sourceKey": "awp-skill-readme-raw",
        "locator": "README endpoint section",
        "evidenceType": "runtime-doc",
        "stability": "medium",
        "rationale": "The workstation should use the official skill's published endpoint surface instead of inventing its own.",
    },
    {
        "key": "awp-skill-install-sequence",
        "topicKey": "awp-skill",
        "claim": "Official onboarding says to install awp-skill, install awp-wallet, ensure awp-wallet is on PATH, then initialize a fresh work wallet.",
        "sourceKey": "awp-skill-readme-raw",
        "locator": "README installation and quickstart",
        "evidenceType": "runtime-doc",
        "stability": "medium",
        "rationale": "This sequence governs how the workstation should explain onboarding.",
    },
    {
        "key": "awp-skill-gasless-ops",
        "topicKey": "awp-skill",
        "claim": "The official RootNet skill documents gasless Bind, Set Recipient, and Worknet Registration relay flows.",
        "sourceKey": "awp-skill-readme-raw",
        "locator": "README gasless support table",
        "evidenceType": "runtime-doc",
        "stability": "medium",
        "rationale": "These are the operations the workstation can plan around without requiring native gas.",
    },
    {
        "key": "mine-worknet-summary",
        "topicKey": "mine",
        "claim": "Mine is the first AWP WorkNet for permissionless web data collection, cleaning, and structured extraction.",
        "sourceKey": "aip-001-raw",
        "locator": "AIP-001 abstract and motivation",
        "evidenceType": "aip",
        "stability": "high",
        "rationale": "This is the normative source for the Mine work definition.",
    },
    {
        "key": "mine-emission-and-stake",
        "topicKey": "mine",
        "claim": "Mine runs on Base with $aMine, daily UTC epochs, no miner stake requirement, and validator stake requirement.",
        "sourceKey": "aip-001-raw",
        "locator": "AIP-001 terminology, token, and role sections",
        "evidenceType": "aip",
        "stability": "high",
        "rationale": "These details determine whether the workstation can recommend Mine to a new user.",
    },
    {
        "key": "predict-worknet-summary",
        "topicKey": "predict",
        "claim": "Predict is an AI-native prediction market WorkNet where agents submit predictions with reasoning on a CLOB.",
        "sourceKey": "aip-002-raw",
        "locator": "AIP-002 abstract and worknet page summary",
        "evidenceType": "aip",
        "stability": "high",
        "rationale": "This explains why reasoning quality is a first-class operational dimension.",
    },
    {
        "key": "predict-virtual-chips",
        "topicKey": "predict",
        "claim": "Predict uses virtual chips and periodic chip feeds, lowering the barrier to starting work without immediately acquiring tokens.",
        "sourceKey": "aip-002-raw",
        "locator": "AIP-002 chip economy and participation design",
        "evidenceType": "aip",
        "stability": "medium",
        "rationale": "This informs the workstation default of recommending low-friction entry paths first.",
    },
    {
        "key": "predict-official-runtime",
        "topicKey": "predict",
        "claim": "As of May 20, 2026, the official live AWP API resolves Predict to Base worknetId 845300000003 with skills URI https://github.com/awp-worknet/prediction-skill, and the official skill says to operate through predict-agent commands.",
        "sourceKey": "predict-skill-raw",
        "locator": "SKILL.md quick start, stake requirement, and install sections",
        "evidenceType": "skill-doc",
        "stability": "medium",
        "rationale": "This replaces the earlier assumption that Predict lacked a confirmed official runtime.",
    },
    {
        "key": "live-canonical-base-worknets",
        "topicKey": "protocol-core",
        "claim": "As of May 20, 2026, official live read-only queries resolve Base Mine to 845300000002, Predict to 845300000003, Gov to 845300000010, Community to 845300000011, KYA to 845300000012, TMR to 845300000013, and Ardi to 845300000014, with pending predecessor entries at 845300000005 through 845300000009.",
        "sourceKey": "awp-live-query",
        "locator": "worknets.get + worknets.getSkills live snapshots captured by workstation on 2026-05-20",
        "evidenceType": "live-api",
        "stability": "low",
        "rationale": "This is the current canonical map that the workstation should use when live list/search metadata drifts.",
    },
    {
        "key": "gov-public-vs-signed",
        "topicKey": "gov",
        "claim": "GovNet public reads work without a wallet, while signed reads and writes resolve the principal through awp-wallet.",
        "sourceKey": "gov-skill-raw",
        "locator": "SKILL.md read vs signed section",
        "evidenceType": "skill-doc",
        "stability": "medium",
        "rationale": "This is why the workstation can expose safe inspection before gated signed actions.",
    },
    {
        "key": "gov-auth-discipline",
        "topicKey": "gov",
        "claim": "Gov skill standardizes retry and failure handling for domain mismatch, nonce drift, and time skew errors.",
        "sourceKey": "gov-skill-raw",
        "locator": "SKILL.md error handling discipline",
        "evidenceType": "skill-doc",
        "stability": "medium",
        "rationale": "The workstation should inherit the idea that these failures are operational states, not user mysteries.",
    },
    {
        "key": "ardi-agent-only",
        "topicKey": "ardi",
        "claim": "Ardi requires all chain actions to go through ardi-agent and explicitly discourages ad hoc loop scripting when auto-mine exists.",
        "sourceKey": "ardi-skill-raw",
        "locator": "SKILL.md agent-only and auto-mine guidance",
        "evidenceType": "skill-doc",
        "stability": "medium",
        "rationale": "This justifies the workstation rule that Ardi must follow the official next-command journal.",
    },
    {
        "key": "ardi-operational-caps",
        "topicKey": "ardi",
        "claim": "Ardi documents strict operational caps such as five commits per epoch and a 21,000 total inscription cap.",
        "sourceKey": "ardi-skill-raw",
        "locator": "SKILL.md limits and constraints",
        "evidenceType": "skill-doc",
        "stability": "medium",
        "rationale": "These caps affect safe automation planning.",
    },
    {
        "key": "kya-registration-handoff",
        "topicKey": "kya",
        "claim": "KYA requires prior AWP registration and says unregistered agents must hand off to awp-skill for gasless onboarding before continuing.",
        "sourceKey": "kya-skill-raw",
        "locator": "SKILL.md prerequisites and handoff text",
        "evidenceType": "skill-doc",
        "stability": "medium",
        "rationale": "This is why the workstation treats KYA as a service tool, not a bootstrap replacement.",
    },
    {
        "key": "kya-handoff-url-plain-text",
        "topicKey": "kya",
        "claim": "KYA magic-link and handoff flows require plain-text URL emission in non-TTY environments.",
        "sourceKey": "kya-skill-raw",
        "locator": "SKILL.md messaging and non-TTY guidance",
        "evidenceType": "skill-doc",
        "stability": "medium",
        "rationale": "The workstation must preserve this behavior when translating actions into chat.",
    },
    {
        "key": "staking-awp-power",
        "topicKey": "staking",
        "claim": "Locking AWP mints veAWP and yields AWP Power that scales with stake size and remaining lock duration.",
        "sourceKey": "awp-staking",
        "locator": "staking page main description",
        "evidenceType": "protocol-surface",
        "stability": "medium",
        "rationale": "This is the user-facing summary of staking economics.",
    },
    {
        "key": "dao-public-params",
        "topicKey": "dao",
        "claim": "The public DAO surface currently shows 4 percent quorum, 8 hour voting delay, 24 hour voting period, and 200K AWP proposal threshold.",
        "sourceKey": "awp-dao",
        "locator": "DAO page governance summary line",
        "evidenceType": "protocol-surface",
        "stability": "medium",
        "rationale": "These visible parameters matter when the workstation explains governance timing.",
    },
    {
        "key": "testnet-gasless-start",
        "topicKey": "benchmark-testnet",
        "claim": "The public Benchmark testnet says awp-skill creates a wallet and registers automatically and gaslessly before discovering the testnet worknet.",
        "sourceKey": "awp-testnet",
        "locator": "testnet join section",
        "evidenceType": "protocol-surface",
        "stability": "medium",
        "rationale": "This offers a public example of the intended agent-first onboarding path.",
    },
    {
        "key": "tmr-live-skill-uri",
        "topicKey": "tmr",
        "claim": "As of May 20, 2026, the live AWP surface resolves TMR to Base worknetId 845300000013 with official skill URI https://github.com/awp-worknet/tmr-skill, but the public operator surface is still too thin for safe unattended execution.",
        "sourceKey": "tmr-skill",
        "locator": "official live skill URI returned by AWP plus repository landing page",
        "evidenceType": "skill-uri",
        "stability": "medium",
        "rationale": "This is the core reason the workstation exposes TMR as discoverable but not auto-runnable.",
    },
    {
        "key": "community-live-skill-uri",
        "topicKey": "community",
        "claim": "As of May 20, 2026, the live AWP surface resolves Community to Base worknetId 845300000011 with official skill URI https://github.com/awp-worknet/com-skill, but the public operator surface is still too thin for safe unattended execution.",
        "sourceKey": "community-skill",
        "locator": "official live skill URI returned by AWP plus repository landing page",
        "evidenceType": "skill-uri",
        "stability": "medium",
        "rationale": "This is the core reason the workstation exposes Community as discoverable but not auto-runnable.",
    },
    {
        "key": "blog-operator-guides",
        "topicKey": "blog",
        "claim": "The official blog is part of the documentation surface and currently includes practical onboarding plus WorkNet concept guides.",
        "sourceKey": "awp-blog",
        "locator": "blog index visible article list",
        "evidenceType": "docs-surface",
        "stability": "low",
        "rationale": "Useful for explanation tone, but less normative than AIPs and skill docs.",
    },
]

DERIVED_GLOSSARY_TERMS: list[dict[str, Any]] = [
    {
        "term": "AWP",
        "aliases": ["Agent Work Protocol", "$AWP"],
        "plainLanguage": "让 AI agent 真正工作和赚钱的协议网络。",
        "definition": "The reserve asset and protocol layer that coordinates agent work across WorkNets.",
        "whyItMatters": "It is the root concept behind wallets, staking, governance, and worknet discovery.",
        "relatedTopics": ["protocol-core", "awp-skill", "staking", "dao"],
        "sourceKeys": ["awp-home", "awp-whitepaper"],
    },
    {
        "term": "RootNet",
        "aliases": ["root network"],
        "plainLanguage": "负责注册、奖励路由、stake、治理的总控层。",
        "definition": "The constitutional layer that manages emission, staking, WorkNet lifecycle, and DAO governance.",
        "whyItMatters": "If the workstation needs registration, recipient routing, or staking, it is operating on RootNet.",
        "relatedTopics": ["protocol-core", "awp-skill", "staking", "dao"],
        "sourceKeys": ["awp-whitepaper", "awp-skill-readme-raw"],
    },
    {
        "term": "WorkNet",
        "aliases": ["work network"],
        "plainLanguage": "一种具体的 agent 工作市场，各自有任务、代币和规则。",
        "definition": "A protocol-defined economic organization where agents perform a specific type of work and earn the WorkNet token.",
        "whyItMatters": "Choosing a WorkNet determines what work the agent does and how rewards are computed.",
        "relatedTopics": ["protocol-core", "mine", "predict", "gov", "ardi", "kya", "benchmark-testnet"],
        "sourceKeys": ["awp-whitepaper", "awp-worknets"],
    },
    {
        "term": "skillURI",
        "aliases": ["skillsUri", "skill URI", "skillURL"],
        "plainLanguage": "某个 WorkNet 发布给 agent 的官方技能说明地址。",
        "definition": "The published location of a WorkNet's official agent instructions or skill repository.",
        "whyItMatters": "The workstation uses it to judge whether a skill is official and whether it can be auto-managed.",
        "relatedTopics": ["protocol-core", "awp-skill", "gov", "ardi", "kya"],
        "sourceKeys": ["awp-skill-readme-raw", "gov-skill-raw", "ardi-skill-raw", "kya-skill-raw"],
    },
    {
        "term": "epoch",
        "aliases": ["settlement window", "task window"],
        "plainLanguage": "一段固定结算周期，周期结束后统一算分和发奖励。",
        "definition": "A settlement period used to batch work evaluation, score updates, and reward accounting.",
        "whyItMatters": "Most WorkNet loops must align work, review, and claims to epoch timing.",
        "relatedTopics": ["mine", "predict", "ardi", "gov"],
        "sourceKeys": ["aip-001-raw", "aip-002-raw", "ardi-skill-raw"],
    },
    {
        "term": "CLOB",
        "aliases": ["orderbook", "central limit order book"],
        "plainLanguage": "Predict 里下单和撮合预测的订单簿。",
        "definition": "The central limit order book used by Predict for market-making and prediction entry.",
        "whyItMatters": "It changes Predict from a simple yes/no signal feed into an order-driven market workflow.",
        "relatedTopics": ["predict"],
        "sourceKeys": ["aip-002-raw", "agentpredict-home"],
    },
    {
        "term": "staking",
        "aliases": ["stake", "veAWP"],
        "plainLanguage": "把 AWP 锁起来，换成治理权和某些 WorkNet 的资格/优先级。",
        "definition": "Locking AWP to mint veAWP and derive AWP Power over time.",
        "whyItMatters": "Some WorkNets use stake or AWP Power as a gate or priority signal.",
        "relatedTopics": ["staking", "dao", "protocol-core", "mine", "ardi"],
        "sourceKeys": ["awp-staking", "awp-whitepaper"],
    },
    {
        "term": "AWP Power",
        "aliases": ["power", "ve power"],
        "plainLanguage": "由 stake 规模和锁仓时间决定的治理/优先级权重。",
        "definition": "The governance and qualification weight derived from a veAWP position.",
        "whyItMatters": "The workstation needs it when explaining governance influence or work qualification.",
        "relatedTopics": ["staking", "dao", "protocol-core"],
        "sourceKeys": ["awp-staking", "awp-whitepaper", "awp-dao"],
    },
    {
        "term": "recipient",
        "aliases": ["reward recipient", "resolved recipient"],
        "plainLanguage": "奖励最后要打到的地址。",
        "definition": "The address that ultimately receives protocol or WorkNet rewards for an agent.",
        "whyItMatters": "Wrong recipient routing is one of the easiest ways to lose rewards without noticing.",
        "relatedTopics": ["protocol-core", "awp-skill", "kya"],
        "sourceKeys": ["awp-skill-readme-raw", "kya-skill-raw"],
    },
    {
        "term": "allocation",
        "aliases": ["allocate", "delegated staking allocation"],
        "plainLanguage": "把 stake 或权重指向某个 agent / WorkNet。",
        "definition": "Assigning stake-derived influence or capital toward a target agent or WorkNet.",
        "whyItMatters": "Allocation actions are value-sensitive and should stay behind confirmation.",
        "relatedTopics": ["awp-skill", "protocol-core", "kya", "gov"],
        "sourceKeys": ["awp-skill-readme-raw", "kya-skill-raw", "gov-skill-raw"],
    },
    {
        "term": "principal",
        "aliases": ["owner account"],
        "plainLanguage": "真正持有资金和授权的主体账户。",
        "definition": "The account role that holds funds while an agent executes work on its behalf.",
        "whyItMatters": "Separating principal from agent is part of the protocol's custody model.",
        "relatedTopics": ["protocol-core", "gov", "kya"],
        "sourceKeys": ["awp-whitepaper", "gov-skill-raw"],
    },
    {
        "term": "agent",
        "aliases": ["agent account", "worker agent"],
        "plainLanguage": "负责执行工作的账号或 runtime。",
        "definition": "The executing work identity that performs tasks, signs payloads, and accumulates work history.",
        "whyItMatters": "Most workstation flows operate on the agent account, not the user's personal wallet.",
        "relatedTopics": ["protocol-core", "awp-skill", "mine", "predict", "gov", "ardi", "kya"],
        "sourceKeys": ["awp-whitepaper", "awp-home", "aip-001-raw", "aip-002-raw"],
    },
    {
        "term": "gasless registration",
        "aliases": ["free registration", "gasless onboarding"],
        "plainLanguage": "不用先充 gas 就能完成 agent 注册。",
        "definition": "A relay-assisted registration flow that onboards an agent without needing native gas in the wallet first.",
        "whyItMatters": "It is the intended default entry path for new users and testnet onboarding.",
        "relatedTopics": ["awp-skill", "benchmark-testnet", "kya"],
        "sourceKeys": ["awp-skill-readme-raw", "awp-testnet", "kya-skill-raw"],
    },
]

KNOWLEDGE_COVERAGE_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "key": "trigger-surface",
        "title": "Skill Trigger Surface",
        "intent": "The workstation should be discoverable from English and Chinese user prompts.",
    },
    {
        "key": "protocol-encyclopedia",
        "title": "Protocol Encyclopedia",
        "intent": "RootNet, WorkNet, staking, DAO, recipient, and endpoint knowledge should be captured locally.",
    },
    {
        "key": "worknet-coverage",
        "title": "WorkNet Coverage",
        "intent": "Mine, Predict, KYA, Ardi, Gov, TMR, and Community should all be represented.",
    },
    {
        "key": "glossary-coverage",
        "title": "Glossary Coverage",
        "intent": "Key terms from the goal such as RootNet, WorkNet, skillURI, epoch, CLOB, and staking must be explainable.",
    },
    {
        "key": "source-traceability",
        "title": "Source Traceability",
        "intent": "Derived claims should link back to official source keys, locators, and stability labels.",
    },
    {
        "key": "registration-flow",
        "title": "Registration Flow",
        "intent": "The workstation should understand and eventually execute awp-skill gasless registration.",
    },
    {
        "key": "live-rpc-scan",
        "title": "Live RPC Scan",
        "intent": "The workstation should know the AWP RPC methods and report when live access is unavailable.",
    },
    {
        "key": "skill-inspector",
        "title": "Skill Inspector",
        "intent": "Official worknet skills should have install, preflight, and dry-run guidance even before the runtime is locally installed.",
    },
    {
        "key": "recovery-state",
        "title": "Recovery State",
        "intent": "The workstation should persist and restore playbooks, runs, and pending confirmations.",
    },
    {
        "key": "live-canonical-quality",
        "title": "Live Canonical Quality",
        "intent": "Live WorkNet entries should resolve to canonical IDs and official skills with clear confidence.",
    },
    {
        "key": "upstream-drift-watch",
        "title": "Upstream Drift Watch",
        "intent": "Official docs and skill sources should be refreshable and diffable so workstation knowledge can track upstream changes.",
    },
]

LOCAL_SOURCE_CANDIDATES: list[dict[str, Any]] = [
    {
        "key": "awp-wallet",
        "name": "awp-wallet",
        "path": "/root/.nanobot/workspace/awp-wallet",
        "upstream": "https://github.com/awp-core/awp-wallet",
        "summary": "Local AWP wallet CLI clone.",
        "important_files": [
            "SKILL.md",
            "README.md",
            "docs/CLAUDE-WEB3-GUIDE.md",
            "scripts/wallet-cli.js",
        ],
    },
    {
        "key": "mine",
        "name": "mine",
        "path": "/root/.nanobot/workspace/mine",
        "upstream": "https://minework.net/",
        "summary": "Local Mine runtime and skill.",
        "important_files": [
            "SKILL.md",
            "README.md",
            "references/protocol-miner.md",
            "scripts/run_tool.py",
        ],
    },
    {
        "key": "kya",
        "name": "kya-skill",
        "path": "/root/.nanobot/workspace/kya-skill",
        "upstream": "https://github.com/awp-worknet/kya-skill",
        "summary": "Local KYA skill clone.",
        "important_files": [
            "SKILL.md",
            "README.md",
            "scripts/kya_lib.py",
            "scripts/relay-set-recipient.py",
        ],
    },
    {
        "key": "awp-data",
        "name": "awp-data",
        "path": "/root/.nanobot/workspace/awp-data",
        "upstream": "https://git.basevec.com/sp-demand/awp-data.git",
        "summary": "Local AWP data workspace with limited docs.",
        "important_files": [
            "README.md",
        ],
    },
]

KNOWN_WORKNETS: list[dict[str, Any]] = [
    {
        "key": "mine",
        "aliases": [
            "mine",
            "amine",
            "001",
            "002",
            "worknet #001",
            "worknet #002",
            "base:001",
            "base:002",
            "base:mine",
            "845300000002",
            "mine worknet",
        ],
        "worknet_id": "845300000002",
        "name": "Mine WorkNet",
        "symbol": "aMine",
        "status": "active",
        "skills_uri": "https://github.com/awp-worknet/mine-skill",
        "install_uri": "https://github.com/awp-worknet/mine-skill",
        "local_source_key": "mine",
        "source_keys": ["aip-001-raw", "minework-home", "mine-skill-raw", "awp-live-query"],
        "min_stake": None,
        "automation_level": "full",
        "risk_level": "medium",
        "recommended_role": "operator",
        "goal": "Earn by contributing high-quality structured web data.",
        "loop": "discover -> dedupe -> crawl -> clean -> extract -> submit -> heartbeat",
        "commands": [
            {
                "label": "mine readiness",
                "cwd": "/root/.nanobot/workspace/mine",
                "argv": ["python3", "scripts/run_tool.py", "agent-status"],
                "category": "read",
                "requires_confirmation": False,
            },
            {
                "label": "mine status",
                "cwd": "/root/.nanobot/workspace/mine",
                "argv": ["python3", "scripts/run_tool.py", "agent-control", "status"],
                "category": "read",
                "requires_confirmation": False,
            },
            {
                "label": "start mine worker",
                "cwd": "/root/.nanobot/workspace/mine",
                "argv": ["python3", "scripts/run_tool.py", "agent-start"],
                "category": "work",
                "requires_confirmation": False,
                "long_running": True,
            },
            {
                "label": "pause mine worker",
                "cwd": "/root/.nanobot/workspace/mine",
                "argv": ["python3", "scripts/run_tool.py", "agent-control", "pause"],
                "category": "work",
                "requires_confirmation": False,
            },
        ],
        "success_metrics": [
            "accepted submissions",
            "low duplicate rate",
            "stable heartbeat",
            "clean worker health",
        ],
        "failure_modes": [
            "platform auth churn",
            "dataset mismatch",
            "crawler timeout",
            "rate limiting or cooldown",
        ],
        "human_confirmations": [
            "Confirm before using a third-party or non-allowlisted Mine skill source.",
        ],
    },
    {
        "key": "predict",
        "aliases": [
            "predict",
            "apred",
            "002",
            "003",
            "worknet #002",
            "worknet #003",
            "base:002",
            "base:003",
            "base:predict",
            "845300000003",
            "prediction",
        ],
        "worknet_id": "845300000003",
        "name": "Predict WorkNet",
        "symbol": "aPRED",
        "status": "active",
        "skills_uri": "https://github.com/awp-worknet/prediction-skill",
        "install_uri": "https://github.com/awp-worknet/prediction-skill",
        "local_source_key": None,
        "source_keys": ["aip-002-raw", "agentpredict-home", "predict-skill-raw", "awp-live-query"],
        "min_stake": 1000,
        "automation_level": "supervised",
        "risk_level": "high",
        "recommended_role": "strategist",
        "goal": "Submit original price predictions with disciplined reasoning.",
        "loop": "context -> signals -> thesis -> order -> monitor -> review",
        "commands": [],
        "success_metrics": [
            "low reasoning repetition",
            "rate-limit discipline",
            "positive settlement quality",
        ],
        "failure_modes": [
            "duplicate reasoning",
            "overtrading",
            "thin context",
            "missing verified local runtime",
            "stake gate still blocks submissions until 1000 AWP or KYA delegated eligibility is satisfied",
        ],
        "human_confirmations": [
            "Confirm every capital-bearing order or ticket action.",
            "Confirm the stake or KYA-sponsored eligibility path before enabling the autonomous Predict loop.",
        ],
    },
    {
        "key": "kya",
        "aliases": [
            "kya",
            "verify",
            "attest",
            "base:kya",
            "845300000004",
            "845300000007",
            "845300000012",
            "kya worknet",
            "awp kya network",
            "awp kya worknet",
        ],
        "predecessor_worknet_ids": ["845300000004", "845300000007"],
        "worknet_id": "845300000012",
        "name": "KYA",
        "symbol": "aKYA",
        "status": "service",
        "skills_uri": "https://github.com/awp-worknet/kya-skill",
        "install_uri": "https://github.com/awp-worknet/kya-skill",
        "local_source_key": "kya",
        "source_keys": ["kya-human", "kya-skill-raw", "awp-live-query"],
        "min_stake": 0,
        "automation_level": "guided",
        "risk_level": "medium",
        "recommended_role": "identity",
        "goal": "Verify or bind the agent identity and delegated staking path.",
        "loop": "prepare -> sign -> submit -> poll -> review",
        "commands": [
            {
                "label": "run KYA KYC",
                "cwd": "/root/.nanobot/workspace/kya-skill",
                "argv": ["python3", "scripts/sign-kyc.py"],
                "category": "identity",
                "requires_confirmation": True,
            },
            {
                "label": "claim X via KYA",
                "cwd": "/root/.nanobot/workspace/kya-skill",
                "argv": ["python3", "scripts/sign-claim.py"],
                "category": "identity",
                "requires_confirmation": True,
            },
            {
                "label": "set recipient via KYA relay",
                "cwd": "/root/.nanobot/workspace/kya-skill",
                "argv": [
                    "python3",
                    "scripts/relay-set-recipient.py",
                    "--worknet",
                    "845300000012",
                ],
                "category": "staking",
                "requires_confirmation": True,
            },
        ],
        "success_metrics": [
            "active attestation",
            "correct recipient routing",
            "clean signing audit trail",
        ],
        "failure_modes": [
            "wrong address pair",
            "rejected attestation",
            "relay denial",
        ],
        "human_confirmations": [
            "Confirm which agent address should be verified.",
            "Confirm any recipient or delegate change before submission.",
        ],
    },
    {
        "key": "ardi",
        "aliases": [
            "ardi",
            "ardinals",
            "845300000009",
            "845300000014",
            "awp ardi worknet",
        ],
        "predecessor_worknet_ids": ["845300000009"],
        "worknet_id": "845300000014",
        "name": "Ardi",
        "symbol": "aARDI",
        "status": "public",
        "skills_uri": "https://github.com/awp-worknet/ardi-skill",
        "install_uri": "https://github.com/awp-worknet/ardi-skill",
        "local_source_key": None,
        "source_keys": ["ardinals-agents", "ardi-skill-raw", "awp-live-query"],
        "min_stake": 10000,
        "automation_level": "supervised",
        "risk_level": "high",
        "recommended_role": "event-operator",
        "goal": "Solve riddles, commit, reveal, and inscribe within the round window.",
        "loop": "preflight -> fund gas -> satisfy stake path -> commit -> reveal -> inscribe",
        "commands": [],
        "success_metrics": [
            "valid commits",
            "successful reveal timing",
            "mint cap respected",
        ],
        "failure_modes": [
            "insufficient Base gas",
            "stake ineligible",
            "missed reveal window",
        ],
        "human_confirmations": [
            "Confirm funding the Base wallet before Ardi execution.",
            "Confirm the stake path before any buy, swap, or stake action.",
        ],
    },
    {
        "key": "gov",
        "aliases": [
            "gov",
            "govnet",
            "governance",
            "government",
            "845300000005",
            "845300000010",
            "awp government network",
            "awp government worknet",
        ],
        "predecessor_worknet_ids": ["845300000005"],
        "worknet_id": "845300000010",
        "name": "GovNet",
        "symbol": "aGOV",
        "status": "public",
        "skills_uri": "https://github.com/awp-worknet/gov-skill",
        "install_uri": "https://github.com/awp-worknet/gov-skill",
        "local_source_key": None,
        "source_keys": ["gov-works", "gov-skill-raw", "gov-markets-api", "awp-live-query"],
        "min_stake": 1,
        "automation_level": "supervised",
        "risk_level": "high",
        "recommended_role": "governor",
        "goal": "Express weekly worknet value views through stake, allocation, vote, and trade.",
        "loop": "init -> stake -> allocate -> vote -> monitor -> settle",
        "commands": [],
        "success_metrics": [
            "correct phase timing",
            "clear rationale",
            "tracked settlement delta",
        ],
        "failure_modes": [
            "voting or trading outside phase windows",
            "unreviewed capital movement",
            "missing market context",
        ],
        "human_confirmations": [
            "Confirm every stake, allocation, vote, and trade action.",
        ],
    },
    {
        "key": "tmr",
        "aliases": [
            "tmr",
            "atmr",
            "atrm",
            "845300000008",
            "845300000013",
            "awp tmr network",
            "awp tmr worknet",
        ],
        "predecessor_worknet_ids": ["845300000008"],
        "worknet_id": "845300000013",
        "name": "TMR",
        "symbol": "aTMR",
        "status": "public",
        "skills_uri": "https://github.com/awp-worknet/tmr-skill",
        "install_uri": "https://github.com/awp-worknet/tmr-skill",
        "local_source_key": None,
        "source_keys": ["awp-live-query", "tmr-skill"],
        "min_stake": 0,
        "automation_level": "manual-only",
        "risk_level": "medium",
        "recommended_role": "observer",
        "goal": "Expose the official TMR worknet without pretending the task loop is fully understood yet.",
        "loop": "confirm canonical ID -> inspect official skill -> document -> wait",
        "commands": [],
        "success_metrics": [],
        "failure_modes": ["public operator docs remain thin", "official skill has not been inspected locally yet"],
        "human_confirmations": [
            "Confirm before auto-installing or executing the official TMR skill.",
        ],
    },
    {
        "key": "community",
        "aliases": [
            "community",
            "acom",
            "845300000006",
            "845300000011",
            "awp community network",
            "awp community worknet",
        ],
        "predecessor_worknet_ids": ["845300000006"],
        "worknet_id": "845300000011",
        "name": "Community",
        "symbol": "aCOM",
        "status": "public",
        "skills_uri": "https://github.com/awp-worknet/com-skill",
        "install_uri": "https://github.com/awp-worknet/com-skill",
        "local_source_key": None,
        "source_keys": ["awp-live-query", "community-skill"],
        "min_stake": 0,
        "automation_level": "manual-only",
        "risk_level": "medium",
        "recommended_role": "observer",
        "goal": "Expose the official Community worknet while keeping execution conservative until the skill is inspected locally.",
        "loop": "confirm canonical ID -> inspect official skill -> document -> wait",
        "commands": [],
        "success_metrics": [],
        "failure_modes": ["public operator docs remain thin", "official skill has not been inspected locally yet"],
        "human_confirmations": [
            "Confirm before auto-installing or executing the official Community skill.",
        ],
    },
]

HUMANIZED_KNOWLEDGE_SOURCE_LABELS: dict[str, str] = {
    "awp home": "AWP 官方主页",
    "awp-home": "AWP 官方主页",
    "awp whitepaper": "AWP 白皮书",
    "awp-whitepaper": "AWP 白皮书",
    "awp-core/awp-skill": "awp-skill 官方仓库",
    "awp-skill": "awp-skill 官方仓库",
    "awp-skill-readme-raw": "awp-skill 官方说明",
    "awp-skill readme raw": "awp-skill 官方说明",
    "awp live json-rpc": "AWP 官方实时接口",
    "awp-live-query": "AWP 官方实时接口",
    "aip-001-raw": "AIP-001 Mine 规范",
    "aip-002-raw": "AIP-002 Predict 规范",
    "predict skill raw": "Predict 官方 skill 说明",
    "community skill uri": "Community 官方 skill 来源",
    "community-skill": "Community 官方 skill 来源",
    "gov skill raw": "Gov 官方 skill 说明",
    "gov-skill-raw": "Gov 官方 skill 说明",
    "gov markets api": "Gov 官方市场接口",
    "tmr skill uri": "TMR 官方 skill 来源",
    "tmr-skill": "TMR 官方 skill 来源",
    "minework-home": "Mine 官方主页",
    "mine-skill-raw": "Mine 官方 skill 说明",
    "agentpredict-home": "Predict 官方主页",
    "predict-skill-raw": "Predict 官方 skill 说明",
    "gov-works": "Gov 官方页面",
    "gov-markets-api": "Gov 官方市场接口",
    "ardinals agents": "Ardi 官方页面",
    "ardinals-agents": "Ardi 官方页面",
    "ardi-skill-raw": "Ardi 官方 skill 说明",
    "ardi skill raw": "Ardi 官方 skill 说明",
    "kya skill raw": "KYA 官方 skill 说明",
    "kya-human": "KYA 官方验证页面",
    "kya-skill-raw": "KYA 官方 skill 说明",
    "awp dao": "AWP DAO 官方页面",
    "awp-dao": "AWP DAO 官方页面",
    "awp staking": "AWP Staking 官方页面",
    "awp-staking": "AWP Staking 官方页面",
    "awp testnet": "AWP Testnet 官方页面",
    "awp-testnet": "AWP Testnet 官方页面",
    "awp blog": "AWP 官方博客",
    "awp-blog": "AWP 官方博客",
}

CANONICAL_TOPIC_NARRATIVES: dict[str, dict[str, str]] = {
    "protocol-core": {
        "plain": "AWP 是一个让工作代理找任务、赚钱和协作的双层网络：RootNet 负责总控，WorkNet 负责具体工作。",
        "why": "Workstation 先要吃透这层结构，才能替用户屏蔽协议细节，只保留注册、选活、执行和复盘这些真正需要的动作。",
        "caution": "这里最关键的风险点是收款地址路由、资产动作确认，以及上游技能变化不能直接改写本地工作站行为。",
    },
    "awp-skill": {
        "plain": "awp-skill 是 AWP 的官方 RootNet 技能，负责注册、质押、分配、工作网查询和核心协议读写。",
        "why": "它是 workstation 连接官方协议面的主入口，也是后续注册、资格判断和实时查询的依赖层。",
        "caution": "一旦这个官方 skill 发生上游变化，protocol-core、注册流程和风险边界都要跟着复核。",
    },
    "mine": {
        "plain": "Mine 是 AWP 默认优先级最高的数据工作网，核心就是找网页、抓网页、清洗内容、抽结构化数据，再提交拿收益。",
        "why": "它通常不要求 miner 先 stake，最适合作为新用户进入 AWP 的第一条长期工作流。",
        "loop": "默认节奏是先发现网址和数据集，再去重、抓取、清洗、抽结构化字段，最后提交并维持保活。",
        "caution": "真正影响收益的是提交确认率、重复率、IP 衰减和 epoch 结束时的质量门槛。",
    },
    "predict": {
        "plain": "Predict 是 AWP 的推理型预测工作网，工作代理通过读取市场上下文和外部信号形成观点，再提交方向、价格和仓位。",
        "why": "它更像把研究能力直接变成收益，但前提是控制重复推理、频率和风控，而不是无脑多跑。",
        "loop": "默认节奏是先读市场上下文，再拉信号、形成判断、给出委托，之后持续观察和复盘。",
        "caution": "它天然比 Mine 更偏高风险，因为判断失误、过度重复推理和频率限制都会直接伤害结果。",
    },
    "gov": {
        "plain": "GovNet 是按阶段运行的治理/交易型 WorkNet，核心动作是看公开市场、投票、下单、盯当前阶段，再等结算。",
        "why": "它承接的是对 WorkNet 价值和每周排放的判断，不只是读信息，还会碰到真正的资产动作。",
        "loop": "默认节奏是先初始化和看当前阶段，再质押、分配、投票、观察，最后等结算。",
        "caution": "所有投票、下单、质押和其他不可逆动作都必须先进确认队列，不能静默自动执行。",
    },
    "staking": {
        "plain": "Staking 就是把 AWP 锁起来，换成 veAWP 和 AWP Power，用来拿治理权、资格和某些 WorkNet 的优先级。",
        "why": "它是增强项，不是新用户上手前置；只有真的需要资格或优先级时才该考虑。",
        "caution": "Staking 天然是价值移动动作，会锁定流动性，所以必须明确提示期限、影响和确认步骤。",
    },
    "dao": {
        "plain": "DAO 是 AWP 的治理面，负责提案、投票和协议方向调整。",
        "why": "用户未必要天天碰 DAO，但 workstation 必须理解它，因为 staking、AWP Power 和 GovNet 都会跟它连起来。",
        "caution": "治理判断和投票不是纯观察动作，任何签名或有价值影响的步骤都必须单独确认。",
    },
    "ardi": {
        "plain": "Ardi 是按结算周期解谜的 WorkNet，工作代理要读题、挑高置信答案、先提交答案承诺，等窗口到再揭示并铭刻。",
        "why": "它不是持续刷任务型循环，更像带时间窗口的事件驱动工作网。",
        "loop": "默认节奏是先读谜题和上下文，再选最多 5 个答案，提交承诺后等揭示窗口，最后再铭刻。",
        "caution": "它最怕错过当前阶段，或者偏离官方 `_internal.next_command`，所以运行时 guidance 必须被严格遵守。",
    },
    "kya": {
        "plain": "KYA 更像一次性的身份、认证和委托工具网，主要负责身份认证、收款地址路由和委托质押。",
        "why": "它不是拿来长期循环刷收益的，而是帮其他工作流解决身份和权限前置问题。",
        "loop": "默认节奏是先确认已有身份状态，再决定是否走注册交接、身份验证、设置收款地址或授予委托权限。",
        "caution": "凡是跟身份绑定、收款地址设置或委托质押有关的动作，都要强调签名和确认边界。",
    },
    "tmr": {
        "plain": "TMR 是官方已激活但公开资料仍偏薄的 WorkNet，目前工作站主要把它当成已发现但不可贸然自动运行的目标。",
        "why": "这类 WorkNet 需要先补齐官方 skill、流程和风险资料，才能安全进入自动化层。",
        "loop": "默认节奏是先确认官方登记的 WorkNet ID 和技能来源，再检查本地有没有可用说明，最后只保留观察和资料整理。",
        "caution": "在资料不足前，最稳妥的动作是继续整理来源、比对官方技能来源地址，而不是强行执行。",
    },
    "community": {
        "plain": "Community 是官方已激活但公开操作资料仍偏薄的 WorkNet，目前更适合观察、整理资料和等待官方运行时信号。",
        "why": "它已经进入发现面，但还没达到 workstation 可以放心自动化的资料密度。",
        "loop": "默认节奏是先核对官方登记的 WorkNet ID 和技能来源，再检查官方 skill 说明，最后持续整理资料和等待更明确的执行信号。",
        "caution": "只要官方技能来源地址或 README 再变，这条知识就要优先复核，避免工作站误判可运行性。",
    },
    "awp-skill-ops": {
        "plain": "这条参考记录的是 awp-skill 这层官方总控能力：注册、免 gas 中继、收款地址绑定、质押、分配和实时协议查询都依赖它。",
        "why": "Workstation 之所以能替用户屏蔽协议细节，核心就是把这层能力稳稳接住，再往上翻译成注册、选活和执行动作。",
        "caution": "如果 awp-skill 的安装、端点或中继能力发生变化，注册路径、风险边界和自动化假设都要一起复核。",
    },
    "mine-aip": {
        "plain": "这条参考记录的是 Mine 的协议定义：它是 AWP 的首个数据工作网，重点是抓取、清洗和提交结构化网页数据。",
        "why": "当你要确认 Mine 的奖励规则、结算节奏和 stake 边界时，最该回到这条 AIP，而不是只看二手说明。",
        "caution": "它定义的是协议边界，不会告诉你本地运行时当前是不是装好；执行前仍要结合 workstation 扫描和本地运行状态。",
    },
    "predict-aip": {
        "plain": "这条参考记录的是 Predict 的协议定义：它把预测判断、理由和下单行为合在同一套市场工作流里。",
        "why": "当你要确认虚拟筹码、奖励拆分和市场节奏时，最该回到这条 AIP。",
        "caution": "它定义的是市场机制，不等于本地 skill 已经就绪；真正执行前还要核对官方运行时和当前资格条件。",
    },
    "predict-skill-facts": {
        "plain": "这条参考记录的是 Predict 官方运行时和实时登记信息，包括当前技能来源、工作网 ID，以及必须通过 predict-agent 执行的约束。",
        "why": "它比 AIP 更接近今天到底该怎么跑，所以适合拿来确认本地安装、命令入口和资格路径。",
        "caution": "如果官方 skill 或实时映射刚变，先重读这条参考，再决定要不要继续自动挂循环。",
    },
    "gov-skill-facts": {
        "plain": "这条参考记录的是 Gov 的官方运行时约束，包括公开市场读取、私有状态、签名动作和阶段判断。",
        "why": "Gov 真正难的不是看信息，而是分清哪些动作只读、哪些动作会碰签名和资产。",
        "caution": "所有投票、下单、质押和其他不可逆动作都必须先确认，不能因为参考条目存在就默认自动执行。",
    },
    "ardi-skill-facts": {
        "plain": "这条参考记录的是 Ardi 官方运行时约束，包括预检、Gas、资格路径，以及提交承诺、揭示和铭刻的执行顺序。",
        "why": "Ardi 更像时间窗口很强的事件工作流，所以这条参考比泛化说明更能决定当前到底能不能继续。",
        "caution": "一旦官方下一步命令变化，就不要手写 shell 流程顶上去，必须回到 ardi-agent 给出的路径。",
    },
    "kya-skill-facts": {
        "plain": "这条参考记录的是 KYA 官方运行时约束，包括身份验证、收款地址路由和委托质押前置条件。",
        "why": "KYA 不靠长期循环赚钱，但它会决定其他工作流能不能合法继续。",
        "caution": "凡是牵涉身份绑定、收款地址设置或委托质押的动作，都必须先看签名边界和确认步骤。",
    },
    "live-worknet-canonical": {
        "plain": "这条参考记录的是当前官方实时接口认定的 WorkNet 名称、ID 和技能来源映射，工作站靠它确认自己没有连错网。",
        "why": "当官网文案、旧资料或本地缓存互相打架时，先以这份实时映射为准，避免把任务发到错误的 WorkNet。",
        "caution": "它更像实时登记册，不负责解释完整玩法；如果某条 WorkNet 的技能来源刚变，仍要回到对应档案继续复核。",
    },
}


def canonical_topic_narrative(
    topic: str,
    *,
    dossier_key: Optional[str] = None,
    worknet_key: Optional[str] = None,
    glossary_term: Optional[str] = None,
) -> Optional[dict[str, str]]:
    candidates = [
        str(topic or "").strip().lower(),
        str(dossier_key or "").strip().lower(),
        str(worknet_key or "").strip().lower(),
        str(glossary_term or "").strip().lower(),
    ]
    for key in candidates:
        if key and key in CANONICAL_TOPIC_NARRATIVES:
            return CANONICAL_TOPIC_NARRATIVES[key]
    return None


def canonical_worknet_scan_reason(
    profile: dict[str, Any],
    *,
    runnable: bool,
    can_start_without_stake: Optional[bool],
) -> Optional[str]:
    key = str(profile.get("key") or "").strip().lower()
    name = str(profile.get("name") or key)
    narrative = canonical_topic_narrative(key, dossier_key=key, worknet_key=key)
    plain = str((narrative or {}).get("plain") or "").strip()
    if key == "mine":
        if runnable:
            return f"{plain} 当前这条路已经能直接开始，而且默认就是无质押的长期数据工作流。"
        return f"{plain} 但你本地运行环境还没准备好，先修 Mine 运行环境和数据集入口。"
    if key == "predict":
        if runnable:
            return f"{plain} 当前可以先观察市场，也可以在接受高风险前提下挂静默循环。"
        return f"{plain} 现在更适合先观察市场上下文，等运行环境和资格条件稳定后再执行。"
    if key == "gov":
        if runnable:
            return f"{plain} 当前更适合先做公开观察；交易和投票类动作仍要先确认。"
        return f"{plain} 现在先看公开市场和当前阶段，不建议直接自动执行。"
    if key == "ardi":
        if runnable:
            return f"{plain} 当前可以先跑预检，但提交承诺、揭示和铭刻仍要严格跟官方下一步命令。"
        return f"{plain} 当前先补手续费和资格路径，再继续。"
    if key == "kya":
        return plain or f"{name} 更像一次性身份和委托工具，不会长期自动跑。"
    if key in {"tmr", "community"}:
        return f"{plain} 当前只建议观察和整理资料，不建议直接自动执行。"
    if plain and runnable and can_start_without_stake is True:
        return f"{plain} 当前可以直接开始，而且现在不用 stake 就能起步。"
    if plain and runnable:
        return f"{plain} 当前已经具备继续执行的条件。"
    if plain:
        return plain
    return None


def canonical_worknet_switch_summary_text(
    profile: dict[str, Any],
    *,
    runnable: bool,
    can_start_without_stake: Optional[bool],
) -> Optional[str]:
    key = str(profile.get("key") or "").strip().lower()
    name = str(profile.get("name") or key)
    narrative = canonical_topic_narrative(key, dossier_key=key, worknet_key=key)
    plain = str((narrative or {}).get("plain") or "").strip()
    if key == "mine":
        if runnable:
            return f"{plain} 当前可以直接切过去，而且默认就是无质押的数据工作流。"
        return f"{plain} 但现在还没准备好自动运行，先检查本地运行环境和数据集入口。"
    if key == "predict":
        if runnable:
            return f"{plain} 当前可以切过去观察市场，也可以直接挂静默循环；真实收益仍要等市场结算。"
        return f"{plain} 现在更适合先观察市场上下文，等运行环境条件稳定后再自动运行。"
    if key == "gov":
        if runnable:
            return f"{plain} 现在适合先切过去做公开观察；交易和投票类动作仍会先确认。"
        return f"{plain} 已可发现，但当前更适合先看公开市场和当前阶段，再决定是否继续。"
    if key == "ardi":
        if runnable:
            return f"{plain} 可以先切过去跑预检；后续提交承诺、揭示和铭刻仍要跟官方下一步命令。"
        return f"{plain} 还不适合直接自动运行，先补齐它要求的手续费或资格条件。"
    if key == "kya":
        return plain or f"{name} 更像一次性身份和委托工具，不会长期自动跑。"
    if key in {"tmr", "community"}:
        return f"{plain} 当前只建议查看档案，不建议自动执行。"
    if plain and runnable and can_start_without_stake is True:
        return f"{plain} 当前可以直接切过去，而且现在不用 stake 就能开始。"
    if plain and runnable:
        return f"{plain} 当前可以切过去。"
    if plain:
        return f"{plain} 当前还不建议自动运行。"
    return None


def build_preflight_plain_language_summary(
    next_action: str,
    *,
    knowledge_review_queue_summary: Optional[dict[str, Any]] = None,
    include_queue_note: bool = True,
) -> str:
    next_action = str(next_action or "").strip()
    protocol_intro = (
        (canonical_topic_narrative("protocol-core") or {}).get("plain")
        or "AWP 是一个让 agent 找工作、赚钱和协作的网络。"
    )
    message = (
        f"{protocol_intro} Workstation 会先检查 agent 工作钱包、确认是否已注册、扫描可做的 WorkNet，"
        "并在任何涉及质押、投票、下单或其他价值动作前先确认，不会要求你提供私钥。"
    )
    if next_action == "install_awp_skill_dependency":
        message += " 当前还缺官方 RootNet 依赖，所以先补 awp-skill。"
    elif next_action in {"run_awp_skill_registration", "register_agent"}:
        message += " 当前下一步是继续官方免 gas 注册。"
    elif next_action == "retry_registration_preflight":
        message += " 当前官方注册运行时已经就位，但 AWP API 暂时不可达，所以先不要继续提交注册。"
    elif next_action == "install_or_setup_wallet":
        message += " 当前先把 agent work wallet 准备好，再继续后面的注册和选网。"
    elif next_action == "prepare_registration_runtime":
        message += " 当前钱包已经基本就绪，但还要先补齐注册运行时。"
    elif next_action == "scan_worknets":
        message += " 当前钱包和注册状态已经通过基础检查，下一步就是挑一条合适的 WorkNet 开始。"
    elif next_action == "resume_previous_run":
        message += " 当前已经发现上一次的工作记录，可以直接续上。"
    elif next_action == "resume_runtime_guidance":
        message += " 当前上一次运行已经留下明确下一步，不需要重新选 WorkNet。"
    elif next_action == "resume_pending_confirmations":
        message += " 当前先处理待确认动作，再继续后面的工作。"
    elif next_action == "monitor_background_runs":
        message += " 当前已经有后台任务在跑，先看状态而不是重新开一条新路线。"
    if include_queue_note and isinstance(knowledge_review_queue_summary, dict) and knowledge_review_queue_summary.get("hasPendingReviews"):
        pending = int(knowledge_review_queue_summary.get("pendingReviewCount", 0) or 0)
        message += f" 最近还有 {pending} 条知识待重审，说明部分上游资料刚发生变化。"
    return message.strip()


def strip_sentence_end(text: Any) -> str:
    return str(text or "").strip().rstrip(".。!！?？")


def canonical_worknet_plain_text(worknet_key: Optional[str]) -> Optional[str]:
    key = str(worknet_key or "").strip().lower()
    if not key:
        return None
    narrative = canonical_topic_narrative(key, dossier_key=key, worknet_key=key)
    plain = str((narrative or {}).get("plain") or "").strip()
    return plain or None


def canonical_worknet_loop_text(worknet_key: Optional[str]) -> Optional[str]:
    key = str(worknet_key or "").strip().lower()
    if not key:
        return None
    narrative = canonical_topic_narrative(key, dossier_key=key, worknet_key=key)
    loop = str((narrative or {}).get("loop") or "").strip()
    return loop or None


def canonical_worknet_caution_text(worknet_key: Optional[str]) -> Optional[str]:
    key = str(worknet_key or "").strip().lower()
    if not key:
        return None
    narrative = canonical_topic_narrative(key, dossier_key=key, worknet_key=key)
    caution = str((narrative or {}).get("caution") or "").strip()
    return caution or None


def prepend_canonical_worknet_plain(message: Optional[str], worknet_key: Optional[str]) -> Optional[str]:
    body = str(message or "").strip()
    plain = canonical_worknet_plain_text(worknet_key)
    if not plain:
        return body or None
    if not body:
        return plain
    if body.startswith(plain):
        return body
    return f"{plain} {body}".strip()

OFFICIAL_REMOTE_SKILL_MANIFESTS: dict[str, dict[str, Any]] = {
    "awp-skill": {
        "runtimeName": "awp-skill python scripts",
        "summary": "Official RootNet runtime for registration, status, staking, allocation, and worknet queries.",
        "sourceKeys": ["awp-skill-readme-raw", "awp-live-query"],
        "requiredBins": ["python3", "awp-wallet"],
        "optionalBins": [],
        "env": ["EVM_CHAIN"],
        "bootstrapCommands": [],
        "inspectionCommands": [
            {
                "label": "awp-skill preflight",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/preflight.py"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "awp-skill query worknet 2",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/query-worknet.py", "--worknet", "2"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": False,
            },
        ],
    },
    "mine": {
        "runtimeName": "mine run_tool runtime",
        "summary": "Local Mine runtime with worker status, control, and platform-mediated autonomous crawl/submit loops.",
        "sourceKeys": ["minework-home", "mine-skill-raw"],
        "requiredBins": ["python3"],
        "optionalBins": [],
        "env": [],
        "bootstrapCommands": [
            {
                "label": "bootstrap mine runtime",
                "cwdKind": "skill-root",
                "argv": ["bash", "./scripts/bootstrap.sh"],
                "category": "install",
                "requires_confirmation": False,
            }
        ],
        "inspectionCommands": [
            {
                "label": "mine agent status",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/run_tool.py", "agent-status"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "mine control status",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/run_tool.py", "agent-control", "status"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
        ],
    },
    "kya": {
        "runtimeName": "kya signing scripts",
        "summary": "KYA identity and matchmaking runtime for claim, KYC, set-recipient, and grant-delegate signing flows.",
        "sourceKeys": ["kya-skill-raw", "kya-human"],
        "requiredBins": ["python3"],
        "optionalBins": ["awp-wallet"],
        "env": ["KYA_API_BASE", "KYA_KYC_BASE", "KYA_CHAIN_ID", "AWP_RELAY_BASE", "BASE_RPC_URL"],
        "bootstrapCommands": [],
        "inspectionCommands": [
            {
                "label": "kya sign claim help",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/sign-claim.py", "--help"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "kya relay recipient help",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/relay-set-recipient.py", "--help"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "kya kyc help",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/sign-kyc.py", "--help"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": False,
            },
        ],
    },
    "ardi": {
        "runtimeName": "ardi-agent",
        "summary": "Official Ardi runtime that owns preflight, stake guidance, context, commit/reveal/inscribe flow, and the Linux auto-mine bootstrap.",
        "sourceKeys": ["ardi-skill-raw", "ardinals-agents"],
        "requiredBins": ["ardi-agent", "awp-wallet"],
        "optionalBins": [],
        "env": ["ARDI_COORDINATOR_URL", "ARDI_BASE_RPC", "AWP_WALLET_BIN", "ARDI_DEBUG"],
        "bootstrapCommands": [
            {
                "label": "bootstrap ardi-agent runtime",
                "cwdKind": "skill-root",
                "argv": ["bash", "./scripts/bootstrap.sh"],
                "category": "install",
                "requires_confirmation": False,
            }
        ],
        "inspectionCommands": [
            {
                "label": "ardi status",
                "cwdKind": "state-root",
                "argv": ["ardi-agent", "status"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "ardi gas check",
                "cwdKind": "state-root",
                "argv": ["ardi-agent", "gas"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "ardi preflight",
                "cwdKind": "state-root",
                "argv": ["ardi-agent", "preflight"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": False,
            },
            {
                "label": "ardi stake guidance",
                "cwdKind": "state-root",
                "argv": ["ardi-agent", "stake"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
        ],
    },
    "predict": {
        "runtimeName": "predict-agent",
        "summary": "Official Rust-based Predict runtime that owns preflight, stake checks, context, loop mode, and manual submissions.",
        "binaryRuntime": True,
        "sourceKeys": ["predict-skill-raw", "awp-live-query"],
        "requiredBins": ["predict-agent", "awp-wallet"],
        "optionalBins": ["openclaw"],
        "env": ["PREDICT_SERVER_URL"],
        "bootstrapCommands": [
            {
                "label": "install predict-agent binary",
                "cwdKind": "skill-root",
                "argv": ["bash", "install.sh"],
                "category": "install",
                "requires_confirmation": False,
            }
        ],
        "inspectionCommands": [
            {
                "label": "predict wallet safety",
                "cwdKind": "state-root",
                "argv": ["predict-agent", "wallet"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "predict status",
                "cwdKind": "state-root",
                "argv": ["predict-agent", "status"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "predict preflight",
                "cwdKind": "state-root",
                "argv": ["predict-agent", "preflight"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": False,
            },
            {
                "label": "predict stake eligibility",
                "cwdKind": "state-root",
                "argv": ["predict-agent", "stake"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
        ],
    },
    "gov": {
        "runtimeName": "gov-skill python scripts",
        "summary": "Official GovNet runtime with public readers, signed reads, order entry, voting, and phase-aware helpers.",
        "sourceKeys": ["gov-skill-raw", "gov-markets-api"],
        "requiredBins": ["python3"],
        "optionalBins": ["awp-wallet"],
        "env": [
            "GOVNET_NONCE_DIR",
            "GOVNET_API_BASE",
            "GOVNET_WS_URL",
            "GOVNET_VOTE_TYPED_DATA_VARIANT",
        ],
        "bootstrapCommands": [
            {
                "label": "create gov skill venv",
                "cwdKind": "skill-root",
                "argv": ["python3", "-m", "venv", ".venv"],
                "category": "install",
                "requires_confirmation": False,
            },
            {
                "label": "install gov skill deps",
                "cwdKind": "skill-root",
                "argv": [".venv/bin/pip", "install", "eth-hash", "eth-account", "websockets", "pytest"],
                "category": "install",
                "requires_confirmation": False,
            },
        ],
        "inspectionCommands": [
            {
                "label": "gov public markets",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/public/markets.py"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "gov phase-aware helper",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/helpers/what-can-i-do.py"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
            {
                "label": "gov private state",
                "cwdKind": "skill-root",
                "argv": ["python3", "scripts/private/state.py"],
                "category": "inspect",
                "requires_confirmation": False,
                "autoRunOnInspect": True,
            },
        ],
    },
    "tmr": {
        "runtimeName": "tmr-skill",
        "summary": "Official live TMR skill URI is known, but the workstation still lacks enough upstream runtime detail to auto-run it safely.",
        "sourceKeys": ["awp-live-query", "tmr-skill"],
        "requiredBins": [],
        "optionalBins": [],
        "env": [],
        "inspectionCommands": [],
    },
    "community": {
        "runtimeName": "com-skill",
        "summary": "Official live Community skill URI is known, but the workstation still lacks enough upstream runtime detail to auto-run it safely.",
        "sourceKeys": ["awp-live-query", "community-skill"],
        "requiredBins": [],
        "optionalBins": [],
        "env": [],
        "inspectionCommands": [],
    },
}


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def hours_since_iso(value: Any) -> Optional[float]:
    parsed = parse_iso_datetime(value)
    if parsed is None:
        return None
    delta = datetime.now(timezone.utc) - parsed
    return max(0.0, delta.total_seconds() / 3600.0)


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def parse_json_loose(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def run_command(
    argv: list[str], cwd: Optional[str] = None, timeout: int = 120
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "code": 127, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "code": 124,
            "stdout": "",
            "stderr": f"timed out after {timeout}s",
        }
    return {
        "ok": result.returncode == 0,
        "code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


REPO_METADATA_FILENAMES = {
    ".gitattributes",
    ".gitignore",
    ".gitmodules",
    "copying",
    "copying.md",
    "license",
    "license.md",
    "notice",
    "notice.md",
}


def repository_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    return [
        str(path.relative_to(root))
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    ]


def repository_file_is_metadata(relative_path: str) -> bool:
    name = Path(relative_path).name.lower()
    return name in REPO_METADATA_FILENAMES


def repository_is_effectively_empty(root: Path) -> bool:
    files = repository_files(root)
    if not files:
        return True
    return all(repository_file_is_metadata(path) for path in files)


def command_help_probe(argv: list[str], timeout: int = 20) -> dict[str, Any]:
    result = run_command(argv, timeout=timeout)
    combined = "\n".join(part for part in [result.get("stdout", ""), result.get("stderr", "")] if part)
    return {
        "ok": result.get("ok", False),
        "code": result.get("code"),
        "text": trim_output(combined, limit=1200),
    }


def fetch_url(url: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": DEFAULT_FETCH_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            headers = dict(response.headers.items())
            content_type = response.headers.get_content_type()
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        body = b""
        headers = dict(exc.headers.items()) if exc.headers else {}
        content_type = headers.get("Content-Type", "")
        return {
            "ok": False,
            "status": exc.code,
            "headers": headers,
            "contentType": content_type,
            "body": body,
            "error": f"http {exc.code}",
        }
    except (urllib.error.URLError, OSError) as exc:
        return {
            "ok": False,
            "status": None,
            "headers": {},
            "contentType": "",
            "body": b"",
            "error": str(exc),
        }
    return {
        "ok": True,
        "status": status,
        "headers": headers,
        "contentType": content_type,
        "body": body,
        "error": None,
    }


def trim_output(
    value: Any,
    limit: int = 800,
    *,
    max_items: int = 5,
    max_keys: int = 24,
    max_depth: int = 5,
    _depth: int = 0,
) -> Any:
    if isinstance(value, str):
        if len(value) > limit:
            return value[:limit] + "...(truncated)"
        return value
    if isinstance(value, list):
        if _depth >= max_depth:
            return [f"...({len(value)} items truncated at depth {max_depth})"] if value else []
        trimmed = [
            trim_output(
                item,
                limit=limit,
                max_items=max_items,
                max_keys=max_keys,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            trimmed.append(f"...({len(value) - max_items} more items truncated)")
        return trimmed
    if isinstance(value, dict):
        if _depth >= max_depth:
            return {"_truncated": f"{len(value)} keys hidden at depth {max_depth}"}
        items = list(value.items())
        trimmed: dict[str, Any] = {}
        for key, item in items[:max_keys]:
            trimmed[str(key)] = trim_output(
                item,
                limit=limit,
                max_items=max_items,
                max_keys=max_keys,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
        if len(items) > max_keys:
            trimmed["_truncatedKeys"] = len(items) - max_keys
        return trimmed
    return value


def compact_preview_text(
    value: Any,
    *,
    max_chars: int = 180,
    max_sentences: int = 2,
) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    sentence_endings = set("。！？!?；;")
    if len(text) <= max_chars and sum(1 for char in text if char in sentence_endings) <= max_sentences:
        return text
    preview_chars: list[str] = []
    sentence_count = 0
    for char in text:
        preview_chars.append(char)
        if char in sentence_endings:
            sentence_count += 1
            if sentence_count >= max_sentences:
                break
        if len(preview_chars) >= max_chars:
            break
    preview = "".join(preview_chars).strip()
    if len(preview) < len(text):
        cut_index = len(preview)
        if (
            cut_index < len(text)
            and preview
            and re.match(r"[A-Za-z0-9_-]", preview[-1])
            and re.match(r"[A-Za-z0-9_-]", text[cut_index])
        ):
            boundary = max(
                preview.rfind(" "),
                preview.rfind("。"),
                preview.rfind("！"),
                preview.rfind("？"),
                preview.rfind("；"),
                preview.rfind("，"),
                preview.rfind(","),
                preview.rfind(":"),
                preview.rfind("："),
                preview.rfind("/"),
                preview.rfind("-"),
                preview.rfind("_"),
            )
            if boundary >= max(0, len(preview) - 24):
                preview = preview[:boundary].strip()
            else:
                while preview and re.match(r"[A-Za-z0-9_-]", preview[-1]):
                    preview = preview[:-1]
                preview = preview.strip()
        preview = preview.rstrip("。！？!?；;，, …") + "…"
    return preview


def preview_candidate_fragments(value: Any) -> list[str]:
    text = re.sub(r"\s+", " ", str(value or "").strip()).strip()
    if not text:
        return []
    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: Any) -> None:
        fragment = strip_sentence_end(str(candidate or "").strip()).strip(" ，,；;：:、")
        if not fragment:
            return
        normalized = fragment.lower()
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append(fragment)

    for delimiter in ("，", ",", "：", ":", "；", ";", "、", "（", "("):
        prefix, _, _ = text.partition(delimiter)
        if len(prefix.strip()) >= 8:
            add(prefix)
    for delimiter in ("。", "！", "？", "!", "?"):
        prefix, _, _ = text.partition(delimiter)
        if prefix.strip():
            add(prefix)
    add(text)
    return candidates


def join_sentences(parts: list[str]) -> str:
    cleaned = []
    for part in parts:
        text = (part or "").strip()
        if not text:
            continue
        cleaned.append(text.rstrip("."))
    return ". ".join(cleaned)


def join_product_sentences(parts: list[str]) -> str:
    cleaned = []
    for part in parts:
        text = str(part or "").strip()
        if not text:
            continue
        cleaned.append(strip_sentence_end(text))
    return "。 ".join(cleaned)


def normalize_worknet_token(text: str) -> str:
    value = text.strip().lower()
    for prefix in ("awp ",):
        if value.startswith(prefix):
            value = value[len(prefix):]
    for suffix in (" worknet", " work net", " network"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
    cleaned = []
    for char in value:
        if char.isalnum():
            cleaned.append(char)
    return "".join(cleaned)


def normalize_knowledge_source_token(text: Any) -> str:
    value = str(text or "").strip().lower()
    cleaned = []
    for char in value:
        if char.isalnum():
            cleaned.append(char)
    return "".join(cleaned)


def normalize_worknet_id(value: Any) -> Any:
    if isinstance(value, int):
        return str(value)
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text.isdigit():
        return text
    if ":" in text:
        prefix, local = text.split(":", 1)
        if prefix in CHAIN_ALIAS_TO_ID and local.isdigit():
            return str(CHAIN_ALIAS_TO_ID[prefix] * WORKNET_ID_BASE + int(local))
    return value


def safe_slug(text: str) -> str:
    cleaned = []
    for char in text.lower():
        if char.isalnum():
            cleaned.append(char)
        else:
            cleaned.append("-")
    slug = "".join(cleaned).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "item"


def project_fields(record: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {field: record.get(field) for field in fields}


def planned_skill_root(skill_key: str, state: dict[str, Any]) -> Path:
    return Path(state["skills"]) / "checkouts" / safe_slug(skill_key)


def official_remote_manifest(skill_key: str) -> dict[str, Any]:
    return OFFICIAL_REMOTE_SKILL_MANIFESTS.get(skill_key, {})


def preferred_python_for_root(root: Optional[Path]) -> Optional[str]:
    if root is None:
        return None
    candidates = [
        root / ".venv" / "bin" / "python",
        root / ".venv" / "bin" / "python3",
        root / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def rewrite_python_argv(argv: list[Any], *, skill_root: Optional[Path]) -> list[str]:
    values = [str(item) for item in argv]
    if not values:
        return values
    head = values[0]
    if head not in {"python", "python3"}:
        return values
    if len(values) >= 3 and values[1] == "-m" and values[2] == "venv":
        return values
    preferred = preferred_python_for_root(skill_root)
    if preferred:
        values[0] = preferred
    return values


def rewrite_command_for_skill_root(command: dict[str, Any], *, skill_root: Optional[Path]) -> dict[str, Any]:
    updated = dict(command)
    argv = updated.get("argv")
    if isinstance(argv, list):
        updated["argv"] = rewrite_python_argv(argv, skill_root=skill_root)
    return updated


def resolve_manifest_cwd(cwd_kind: str, *, skill_root: Optional[Path], state: dict[str, Any]) -> Optional[str]:
    if cwd_kind == "skill-root":
        return str(skill_root) if skill_root else None
    if cwd_kind == "skill-scripts":
        return str(skill_root / "scripts") if skill_root else None
    if cwd_kind == "state-root":
        return str(state["root"])
    return None


def build_manifest_commands(
    skill_key: str,
    *,
    state: dict[str, Any],
    skill_root: Optional[Path],
    section: str,
) -> list[dict[str, Any]]:
    manifest = official_remote_manifest(skill_key)
    if not manifest:
        return []
    root = skill_root or planned_skill_root(skill_key, state)
    commands: list[dict[str, Any]] = []
    for spec in manifest.get(section, []):
        command = {
            "label": spec.get("label"),
            "cwd": resolve_manifest_cwd(str(spec.get("cwdKind", "")), skill_root=root, state=state),
            "argv": list(spec.get("argv", [])),
            "category": spec.get("category", "inspect"),
            "requires_confirmation": bool(spec.get("requires_confirmation", False)),
        }
        if spec.get("autoRunOnInspect") is not None:
            command["autoRunOnInspect"] = bool(spec.get("autoRunOnInspect"))
        commands.append(rewrite_command_for_skill_root(command, skill_root=root))
    return commands


def infer_command_execution_policy(
    command: dict[str, Any],
    *,
    inspection_status: Optional[str] = None,
) -> str:
    if command.get("requires_confirmation"):
        return "confirm"
    label = str(command.get("label", "")).lower()
    category = str(command.get("category", "")).lower()
    if label.startswith("inspect ") and label.endswith(" skill"):
        return "manual-review"
    if category in {"inspect", "read"} or command.get("autoRunOnInspect"):
        return "probe"
    if category in {"install", "repair", "registration"}:
        return "setup" if inspection_status != "ready" else "manual-setup"
    if any(token in label for token in ("pause", "stop", "cancel", "resume")):
        return "manual-control"
    if category == "work":
        if label.startswith("start ") or label.startswith("run ") or command.get("long_running"):
            return "primary-work"
        return "manual-control"
    return "manual"


def annotate_playbook_commands(
    commands: list[dict[str, Any]],
    *,
    inspection_status: Optional[str] = None,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for command in commands:
        updated = dict(command)
        policy = infer_command_execution_policy(updated, inspection_status=inspection_status)
        updated["executionPolicy"] = policy
        updated["selectedByDefault"] = policy in {"probe", "setup", "primary-work", "confirm"}
        if policy == "confirm":
            group_key = "confirmations"
            tier = "current"
        elif policy in {"setup", "manual-setup"}:
            group_key = "setup"
            tier = "overview"
        elif policy in {"probe", "manual-review"}:
            group_key = "inspect"
            tier = "related"
        elif policy in {"manual-control"}:
            group_key = "control"
            tier = "related"
        else:
            group_key = "current"
            tier = "current"
        updated["commandGroupKey"] = group_key
        updated["commandGroupLabel"] = PLAYBOOK_COMMAND_GROUP_LABELS.get(group_key, group_key)
        updated["commandTier"] = tier
        updated["commandTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get(tier, tier)
        updated["commandTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
        annotated.append(updated)
    return annotated


def dedupe_playbook_commands(commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for command in commands:
        argv = tuple(str(item) for item in command.get("argv", []))
        cwd = str(command.get("cwd") or "")
        key = (cwd, argv)
        if argv and key in seen:
            continue
        if argv:
            seen.add(key)
        deduped.append(command)
    return deduped


def runtime_message(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("user_message", "message", "detail", "summary", "title"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().splitlines()[0]
    return None


def runtime_action_map(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    internal = payload.get("_internal")
    if not isinstance(internal, dict):
        return {}
    action_map = internal.get("action_map")
    if not isinstance(action_map, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in action_map.items():
        if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
            normalized[key.strip()] = value.strip()
    return normalized


def runtime_guidance_worknet_key(
    worknet_key: Optional[str],
    *,
    labels: Any = None,
    action_map: Any = None,
    message: Any = None,
) -> str:
    candidate = str(worknet_key or "").strip().lower()
    if candidate:
        return candidate
    labels_list = [str(item).strip().lower() for item in labels if isinstance(item, str)] if isinstance(labels, list) else []
    commands = [str(value).strip().lower() for value in action_map.values()] if isinstance(action_map, dict) else []
    message_text = str(message or "").strip().lower()
    if (
        any(item in {"start mining", "check status", "re-initialize", "run diagnostics"} for item in labels_list)
        or any("agent-start" in command or "agent-control status" in command or "run_tool.py doctor" in command for command in commands)
        or "mining environment" in message_text
        or "mining session" in message_text
    ):
        return "mine"
    return ""


def runtime_guidance_worknet_name(worknet_key: Optional[str]) -> str:
    key = str(worknet_key or "").strip().lower()
    if not key:
        return "当前"
    explicit_names = {
        "awp-skill": "AWP RootNet Skill",
        "awp-wallet": "AWP Wallet",
    }
    if key in explicit_names:
        return explicit_names[key]
    profile = resolve_worknet(key)
    if isinstance(profile, dict):
        name = str(profile.get("name") or profile.get("key") or key).strip()
        if name.endswith(" WorkNet"):
            name = name[:-len(" WorkNet")].strip()
        if name:
            return name
    return key.replace("-", " ").strip().title() or "当前"


def humanize_runtime_guidance_message_display(
    worknet_key: Optional[str],
    message: Any,
    *,
    state: Any = None,
) -> Optional[str]:
    text = str(message or "").strip()
    resolved_worknet = runtime_guidance_worknet_name(worknet_key)
    state_text = str(state or "").strip().lower()
    lowered = text.lower()
    if lowered.startswith("wallet ready:"):
        address = text.split(":", 1)[1].strip() if ":" in text else ""
        if address:
            return f"{resolved_worknet} 钱包已就绪：{address}。"
        return f"{resolved_worknet} 钱包已就绪。"
    if worknet_key == "predict" and lowered.startswith("agent status:"):
        match = re.search(
            r"agent status:\s*(\d+)\s+total predictions,\s*([0-9.]+)\s+chips balance,\s*persona:\s*([a-z0-9_-]+)",
            lowered,
        )
        if match:
            total_predictions, balance, persona = match.groups()
            return f"Predict 运行状态已同步：累计 {total_predictions} 次预测，当前余额 {balance} 芯片，persona 是 {persona}。"
        return "Predict 运行状态已同步。"
    if worknet_key == "predict" and "failed to fetch status" in lowered and "coordinator" in lowered:
        return "Predict 当前还没连上协调器，先检查协调器连通性。"
    if worknet_key == "predict" and "failed to fetch stake status" in lowered:
        return "Predict 这轮卡在资格检查，当前还没拿到稳定的 stake 结果。"
    if worknet_key == "gov" and "name or service not known" in lowered:
        return "Gov 当前连不上上游服务，先检查网络或域名解析。"
    if worknet_key == "gov" and ("principal has no awp power this epoch" in lowered or "state_principal_not_in_epoch" in lowered):
        return "这期你的 principal 还没有 AWP Power，所以 Gov 的签名读写动作还不能做。"
    if worknet_key == "ardi" and "all base rpcs failed" in lowered:
        return "Ardi 当前连不上 Base RPC，先检查网络或可用 RPC。"
    if worknet_key == "mine":
        if state_text == "ready" or "mining environment is ready" in lowered:
            return "Mine 运行环境已经就绪，现在可以开始采集。"
        if state_text == "idle" or "no active mining session" in lowered:
            return "Mine 当前没有活跃采集会话，启动新一轮后才会开始产出。"
        if state_text == "auth_required" or "wallet session expired" in lowered:
            return "Mine 的钱包会话已经失效，先重新初始化运行环境。"
    if state_text == "auth_required" and resolved_worknet != "当前":
        return f"{resolved_worknet} 的钱包会话已经失效，先重新初始化运行环境。"
    if state_text == "selection_required" and resolved_worknet != "当前":
        return f"{resolved_worknet} 正在等你选下一步。"
    if state_text == "waiting_for_market" and resolved_worknet != "当前":
        return f"{resolved_worknet} 当前没有合适目标，先等下一轮。"
    return compact_preview_text(text, max_chars=160, max_sentences=2) if text else None


def humanize_runtime_next_command_display(
    worknet_key: Optional[str],
    next_command: Any,
) -> Optional[str]:
    rendered = None
    if isinstance(next_command, list) and next_command:
        rendered = render_argv([str(part) for part in next_command])
    else:
        rendered = str(next_command or "").strip() or None
    if not rendered:
        return None
    humanized = humanize_runtime_probe_check_label(
        "",
        command=rendered,
        skill_key=worknet_key,
    )
    return humanized or rendered


def humanize_runtime_guidance_action_label(
    worknet_key: Optional[str],
    label: Any,
    *,
    command: Any = None,
) -> str:
    text = str(label or "").strip()
    if not text:
        return text
    mapped = humanize_playbook_command_label(text)
    if mapped != text:
        return mapped
    command_text = str(command or "").strip().lower()
    resolved_worknet = runtime_guidance_worknet_key(
        worknet_key,
        labels=[text],
        action_map={"_": command_text} if command_text else None,
    )
    worknet_name = runtime_guidance_worknet_name(resolved_worknet)
    lowered = text.lower()
    if resolved_worknet == "mine":
        if lowered == "start mining" or "agent-start" in command_text:
            return "开始 Mine 采集"
        if lowered == "check status":
            if "agent-control status" in command_text:
                return "查看 Mine 控制状态"
            return "查看 Mine 运行状态"
        if lowered == "re-initialize" or "bootstrap.sh" in command_text:
            return "重新初始化 Mine 运行环境"
        if lowered == "run diagnostics" or "run_tool.py doctor" in command_text:
            return "运行 Mine 诊断"
    if lowered in {"re-initialize", "reinitialize"}:
        return f"重新初始化 {worknet_name} 运行环境" if worknet_name != "当前" else "重新初始化运行环境"
    if lowered == "run diagnostics":
        return f"运行 {worknet_name} 诊断" if worknet_name != "当前" else "运行诊断"
    if lowered in {"check status", "status"}:
        return f"查看 {worknet_name} 运行状态" if worknet_name != "当前" else "查看运行状态"
    return humanize_public_action_label(text)


def humanize_runtime_guidance_action_description(
    worknet_key: Optional[str],
    label: Any,
    *,
    command: Any = None,
    message: Any = None,
    state: Any = None,
) -> str:
    text = str(label or "").strip()
    if not text:
        return "继续这条建议动作。"
    command_text = str(command or "").strip().lower()
    lowered = text.lower()
    resolved_worknet = runtime_guidance_worknet_key(
        worknet_key,
        labels=[text],
        action_map={"_": command_text} if command_text else None,
        message=message,
    )
    if resolved_worknet == "mine":
        if lowered == "start mining" or "agent-start" in command_text:
            return "开始新一轮 Mine 采集，让 worker 真正进入赚钱循环。"
        if lowered == "check status":
            return "再看一次 Mine 当前状态，确认现在能不能直接继续。"
        if lowered == "re-initialize" or "bootstrap.sh" in command_text:
            return "重新初始化 Mine 本地运行环境和钱包会话，再回来继续。"
        if lowered == "run diagnostics" or "run_tool.py doctor" in command_text:
            return "先跑 Mine 诊断，确认是钱包会话、依赖还是环境路径出了问题。"
    if lowered in {"re-initialize", "reinitialize"}:
        return "重新初始化当前运行环境和会话。"
    if lowered == "run diagnostics":
        return "先跑诊断，确认现在卡在环境、依赖还是权限。"
    if lowered in {"check status", "status"}:
        return "再看一次当前状态，确认现在能不能继续。"
    display_message = humanize_runtime_guidance_message_display(resolved_worknet, message, state=state)
    if display_message:
        return display_message
    return humanize_public_action_description(text, str(message or "继续这个建议动作。").strip() or "继续这个建议动作。")


def runtime_guidance_preview_display(guidance: Any) -> Optional[str]:
    if not isinstance(guidance, dict):
        return None
    message = str(guidance.get("messageDisplay") or guidance.get("message") or "").strip()
    actions = [
        str(item).strip()
        for item in guidance.get("userActionsDisplay", [])
        if isinstance(item, str) and str(item).strip()
    ] if isinstance(guidance.get("userActionsDisplay"), list) else []
    if not actions:
        actions = [
            str(item.get("displayLabel") or item.get("label") or "").strip()
            for item in guidance.get("userActionDetails", [])
            if isinstance(item, dict) and str(item.get("displayLabel") or item.get("label") or "").strip()
        ] if isinstance(guidance.get("userActionDetails"), list) else []
    if message and actions:
        action_text = f"下一步可先用“{actions[0]}”。"
        return compact_preview_text(
            join_product_sentences([message, action_text]),
            max_chars=180,
            max_sentences=2,
        )
    if message:
        return compact_preview_text(message, max_chars=180, max_sentences=2)
    if actions:
        return compact_preview_text(
            f"下一步可先用“{actions[0]}”。",
            max_chars=180,
            max_sentences=2,
        )
    next_command_display = str(guidance.get("nextCommandDisplay") or "").strip()
    if next_command_display:
        return compact_preview_text(
            f"下一步命令：{next_command_display}",
            max_chars=180,
            max_sentences=2,
        )
    return None


def build_raw_user_action_details(
    labels: Any,
    action_map: Any,
    *,
    worknet_key: Optional[str] = None,
    guidance_state: Any = None,
    default_description: Optional[str] = None,
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    if not isinstance(labels, list):
        return details
    resolved_worknet = runtime_guidance_worknet_key(
        worknet_key,
        labels=labels,
        action_map=action_map,
        message=default_description,
    )
    for label in labels:
        if not isinstance(label, str) or not label.strip():
            continue
        text = label.strip()
        command = str(action_map.get(label) or "").strip() if isinstance(action_map, dict) else ""
        append_unique_action_detail(
            details,
            label=text,
            display_label=humanize_runtime_guidance_action_label(
                resolved_worknet,
                text,
                command=command,
            ),
            description=humanize_runtime_guidance_action_description(
                resolved_worknet,
                text,
                command=command,
                message=default_description,
                state=guidance_state,
            ),
            command=command or None,
        )
    return details


def annotate_runtime_user_action_details(
    details: Any,
    *,
    worknet_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    if not isinstance(details, list):
        return []
    annotated: list[dict[str, Any]] = []
    for item in details:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        raw_label = str(normalized.get("label") or "").strip()
        raw_command = str(normalized.get("command") or "").strip()
        display_label = str(normalized.get("displayLabel") or raw_label).strip() or raw_label
        description_display = str(normalized.get("description") or "").strip()
        if raw_label:
            normalized["labelRaw"] = raw_label
        if display_label:
            normalized["displayLabel"] = display_label
        if description_display:
            normalized["descriptionDisplay"] = description_display
        if raw_command:
            normalized["commandRaw"] = raw_command
            normalized["commandDisplay"] = humanize_runtime_probe_check_label(
                "",
                command=raw_command,
                skill_key=worknet_key,
            ) or display_label or raw_command
        annotated.append(normalized)
    return annotated


def annotate_runtime_guidance_payload(
    guidance: Any,
    *,
    worknet_key: Optional[str] = None,
) -> Any:
    if not isinstance(guidance, dict):
        return guidance
    normalized = dict(guidance)
    resolved_worknet = runtime_guidance_worknet_key(
        worknet_key,
        labels=normalized.get("userActions"),
        action_map=normalized.get("actionMap"),
        message=normalized.get("message"),
    )
    message_display = humanize_runtime_guidance_message_display(
        resolved_worknet,
        normalized.get("message"),
        state=normalized.get("state"),
    )
    raw_message = str(normalized.get("message") or "").strip()
    if message_display:
        if raw_message and raw_message != message_display:
            normalized["messageRaw"] = raw_message
        normalized["message"] = message_display
        normalized["messageDisplay"] = message_display
    next_command = normalized.get("nextCommand")
    next_command_raw = None
    if isinstance(next_command, list) and next_command:
        next_command_raw = render_argv([str(part) for part in next_command])
        normalized["nextCommandRaw"] = next_command_raw
        normalized["nextCommandDisplay"] = humanize_runtime_next_command_display(
            resolved_worknet or None,
            next_command,
        ) or next_command_raw
    elif isinstance(next_command, str) and next_command.strip():
        next_command_raw = next_command.strip()
        normalized["nextCommandRaw"] = next_command_raw
        normalized["nextCommandDisplay"] = humanize_runtime_next_command_display(
            resolved_worknet or None,
            next_command,
        ) or next_command_raw
    raw_user_actions = [
        str(item).strip()
        for item in normalized.get("userActions", [])
        if isinstance(item, str) and str(item).strip()
    ] if isinstance(normalized.get("userActions"), list) else []
    if raw_user_actions:
        normalized["userActionsRaw"] = raw_user_actions
    user_action_details = build_raw_user_action_details(
        normalized.get("userActions"),
        normalized.get("actionMap"),
        worknet_key=resolved_worknet or None,
        guidance_state=normalized.get("state"),
        default_description=message_display or str(normalized.get("message") or "继续这个建议动作。").strip() or None,
    )
    if user_action_details:
        user_action_details = annotate_execution_actions(user_action_details)
        user_action_details = annotate_runtime_user_action_details(
            user_action_details,
            worknet_key=resolved_worknet or None,
        )
    normalized["userActionDetails"] = user_action_details
    if isinstance(normalized.get("userActions"), list):
        normalized["userActionsDisplay"] = [
            humanize_runtime_guidance_action_label(
                resolved_worknet,
                item,
                command=normalized.get("actionMap", {}).get(item) if isinstance(normalized.get("actionMap"), dict) and isinstance(item, str) else None,
            )
            for item in normalized.get("userActions", [])
            if isinstance(item, str) and item.strip()
        ]
    display_preview = runtime_guidance_preview_display(normalized)
    if display_preview:
        normalized["preview"] = display_preview
        normalized["previewDisplay"] = display_preview
    raw_preview = None
    if raw_message or raw_user_actions or next_command_raw:
        raw_preview = runtime_guidance_preview_display(
            {
                "message": raw_message or None,
                "userActionsDisplay": raw_user_actions,
                "nextCommandDisplay": next_command_raw,
                "userActionDetails": [
                    {"label": item}
                    for item in raw_user_actions
                ],
            }
        )
    if raw_preview:
        normalized["previewRaw"] = raw_preview
    return normalized


def annotate_raw_follow_up_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        updated = dict(item)
        label = str(updated.get("label") or "").strip()
        if label and not isinstance(updated.get("displayLabel"), str):
            updated["displayLabel"] = humanize_public_action_label(label)
        normalized.append(updated)
    return annotate_execution_actions(normalized)


def annotate_raw_confirmation_queue(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        updated = dict(item)
        label = str(updated.get("label") or "").strip()
        if label and not isinstance(updated.get("displayLabel"), str):
            updated["displayLabel"] = humanize_public_action_label(label)
        normalized.append(updated)
    return annotate_execution_actions(normalized)


def annotate_runtime_action_payloads(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    worknet_key = runtime_payload_worknet_key(normalized)
    normalized["runtimeGuidance"] = annotate_runtime_guidance_payload(
        normalized.get("runtimeGuidance"),
        worknet_key=worknet_key or None,
    )
    normalized["followUpActions"] = annotate_raw_follow_up_actions(normalized.get("followUpActions"))
    normalized["confirmationQueue"] = annotate_raw_confirmation_queue(normalized.get("confirmationQueue"))
    normalized["executedSteps"] = annotate_executed_steps(
        normalized.get("executedSteps"),
        worknet_key=worknet_key or None,
    )
    if isinstance(normalized.get("activeBackgroundProcesses"), list):
        normalized["activeBackgroundProcesses"] = [
            annotate_background_record(item)
            for item in normalized.get("activeBackgroundProcesses", [])
            if isinstance(item, dict)
        ]
    if isinstance(normalized.get("selectedBackground"), dict):
        normalized["selectedBackground"] = annotate_background_record(normalized.get("selectedBackground"))
    if isinstance(normalized.get("selectedConfirmation"), dict):
        normalized["selectedConfirmation"] = annotate_selected_confirmation(normalized.get("selectedConfirmation"))
    if isinstance(normalized.get("sourceFollowUpAction"), dict):
        follow_up = annotate_raw_follow_up_actions([normalized.get("sourceFollowUpAction")])
        normalized["sourceFollowUpAction"] = follow_up[0] if follow_up else normalized.get("sourceFollowUpAction")
    if isinstance(normalized.get("confirmedAction"), dict):
        confirmed = annotate_raw_confirmation_queue([normalized.get("confirmedAction")])
        normalized["confirmedAction"] = confirmed[0] if confirmed else normalized.get("confirmedAction")
    return normalized


def annotate_parameter_schema_items(items: Any) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        prompt = str(item.get("prompt") or "").strip()
        placeholder = str(item.get("placeholder") or "").strip()
        display_name = name.replace("_", " ").strip() if name else None
        rendered.append(
            {
                **item,
                "displayName": display_name,
                "promptDisplay": prompt or display_name,
                "placeholderDisplay": placeholder or None,
            }
        )
    return rendered


def annotate_background_record(record: Any) -> Any:
    if not isinstance(record, dict):
        return record
    normalized = dict(record)
    label = str(normalized.get("label") or "").strip()
    if label:
        normalized["displayLabel"] = humanize_public_action_label(label)
    normalized["actionGroupKey"] = "background"
    normalized["actionGroupLabel"] = EXECUTION_ACTION_GROUP_LABEL_OVERRIDES.get("background")
    normalized["actionGroupRank"] = RESEARCH_HIGHLIGHT_GROUP_RANKS.get("background")
    normalized["actionTier"] = "current"
    normalized["actionTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get("current")
    normalized["actionTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get("current")
    summary = normalized.get("summary")
    if isinstance(summary, dict):
        normalized["summaryDisplay"] = dict(summary)
    return normalized


def annotate_selected_confirmation(selection: Any) -> Any:
    if not isinstance(selection, dict):
        return selection
    normalized = dict(selection)
    label = str(normalized.get("label") or "").strip()
    if label:
        normalized["displayLabel"] = humanize_public_action_label(label)
    normalized["actionGroupKey"] = "confirmations"
    normalized["actionGroupLabel"] = EXECUTION_ACTION_GROUP_LABEL_OVERRIDES.get("confirmations")
    normalized["actionGroupRank"] = RESEARCH_HIGHLIGHT_GROUP_RANKS.get("confirmations")
    normalized["actionTier"] = "current"
    normalized["actionTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get("current")
    normalized["actionTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get("current")
    if isinstance(normalized.get("requiredInputs"), list):
        normalized["requiredInputsDisplay"] = annotate_parameter_schema_items(normalized.get("requiredInputs"))
    return normalized


def runtime_payload_worknet_key(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    playbook = payload.get("playbook")
    if isinstance(playbook, dict):
        worknet_key = str(playbook.get("worknetKey") or "").strip().lower()
        if worknet_key:
            return worknet_key
    for field in ("selectedWorknetKey", "worknetKey"):
        worknet_key = str(payload.get(field) or "").strip().lower()
        if worknet_key:
            return worknet_key
    return ""


def executed_step_result_payload(step: Any) -> Any:
    if not isinstance(step, dict):
        return None
    result = step.get("result")
    if not isinstance(result, dict):
        return None
    return result.get("stdout")


def executed_step_parameter_display_name(step: dict[str, Any], name: str) -> str:
    target = str(name or "").strip()
    if not target:
        return "输入项"
    for spec in step.get("parameterSchema", []) if isinstance(step.get("parameterSchema"), list) else []:
        if not isinstance(spec, dict):
            continue
        spec_name = str(spec.get("name") or "").strip()
        if spec_name != target:
            continue
        prompt = str(spec.get("prompt") or "").strip()
        placeholder = str(spec.get("placeholder") or "").strip()
        if prompt:
            return prompt
        if placeholder:
            return placeholder
        break
    return target.replace("_", " ").strip() or target


def humanize_parameter_error_message(step: dict[str, Any], error: Any) -> Optional[str]:
    text = str(error or "").strip()
    if not text:
        return None
    if text.startswith("missing input: "):
        name = text[len("missing input: "):].strip()
        return f"还缺少输入：{executed_step_parameter_display_name(step, name)}。"
    if text.startswith("invalid value for "):
        remainder = text[len("invalid value for "):].strip()
        name, _, value = remainder.partition(":")
        label = executed_step_parameter_display_name(step, name.strip())
        if value.strip():
            return f"{label}的输入值无效：{value.strip()}。"
        return f"{label}的输入值无效。"
    return text


def humanize_executed_step_reason_text(reason: Any) -> Optional[str]:
    text = str(reason or "").strip()
    if not text:
        return None
    if text == "primary work step already executed; remaining control commands stay manual":
        return "主工作步骤已经执行过了，剩余控制步骤先保留给你手动处理。"
    if text.lower().endswith(" failed"):
        failed_label = text[:-len(" failed")].strip()
        display = humanize_executed_step_label(failed_label) or failed_label or "前一步"
        return f"{display} 执行失败，后续自动推进先暂停。"
    return text


def join_display_sentences(items: list[str]) -> Optional[str]:
    cleaned: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        cleaned.append(text.rstrip("。；;"))
    if not cleaned:
        return None
    return "；".join(cleaned) + "。"


def humanize_executed_step_status_display(status: Any) -> Optional[str]:
    code = str(status or "").strip().lower()
    if not code:
        return None
    mapping = {
        "available_manual": "等待手动继续",
        "planned": "已准备好",
        "ok": "已完成",
        "failed": "执行失败",
        "queued_for_confirmation": "等待确认",
        "awaiting_confirmation": "等待确认",
        "missing_runtime_command": "无可执行命令",
        "missing_parameters": "缺少输入",
        "started_background": "已转入后台",
        "background_running": "后台运行中",
        "blocked_after_previous_step": "暂不继续",
        "skipped_after_primary_work": "保留手动控制",
    }
    return mapping.get(code, code)


def humanize_runtime_payload_state(state: Any) -> Optional[str]:
    code = str(state or "").strip().lower()
    if not code:
        return None
    mapping = {
        "ready": "环境已就绪",
        "idle": "当前空闲",
        "selection_required": "等待你选择下一步",
        "auth_required": "需要重新初始化钱包会话",
        "waiting_for_market": "当前没有合适市场",
        "llm_running": "后台推理中",
        "llm_error": "后台推理报错",
        "challenge_ready": "谜题已经准备好",
        "iteration_started": "新一轮已经开始",
        "starting": "正在启动",
        "running": "正在运行",
        "error": "返回错误",
    }
    return mapping.get(code, code.replace("_", " ").strip())


def structured_preview_text(value: Any, *, max_chars: int = 220) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return compact_preview_text(value, max_chars=max_chars, max_sentences=2)
    trimmed = trim_output(value, limit=180, max_items=4, max_keys=12, max_depth=4)
    try:
        text = json.dumps(trimmed, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(trimmed)
    return compact_preview_text(text, max_chars=max_chars, max_sentences=2)


def executed_step_payload_summary_display(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
) -> Optional[str]:
    if not isinstance(payload, dict):
        return structured_preview_text(payload)
    label = str(step.get("label") or "").strip()
    status = str(step.get("status") or "").strip().lower()
    state = str(payload.get("state") or "").strip().lower()
    state_display = humanize_runtime_payload_state(state)
    message = runtime_message(payload)
    message_display = humanize_runtime_guidance_message_display(
        worknet_key or None,
        message,
        state=state,
    )
    if status in {"planned", "ok", "failed"} and runtime_payload_has_blocker(payload):
        return (
            humanize_review_failure(worknet_key, step, payload)
            or runtime_payload_error_summary(payload)
            or message_display
            or state_display
            or message
            or structured_preview_text(payload)
        )
    if state not in {"auth_required", "waiting_for_market", "llm_error", "error"}:
        review_detail = humanize_review_step(worknet_key, step, payload)
        if review_detail:
            return review_detail
    if message_display:
        return message_display
    if state_display and message:
        preview = compact_preview_text(message, max_chars=160, max_sentences=2) or message
        if state_display in preview:
            return preview
        return f"{state_display}：{preview}"
    return state_display or message or structured_preview_text(payload) or humanize_review_status_token(worknet_key, label, status)


def humanize_started_background_detail(step: dict[str, Any]) -> Optional[str]:
    guidance = step.get("runtimeGuidance")
    message = runtime_message(guidance) if isinstance(guidance, dict) else None
    log_path = None
    background = step.get("backgroundProcess")
    if isinstance(background, dict):
        value = background.get("logPath")
        if isinstance(value, str) and value.strip():
            log_path = value.strip()
    detail = message or "这一步已经转入后台运行。"
    if log_path and log_path not in detail:
        detail = f"{detail} 日志位置：{log_path}。"
    return detail


def humanize_executed_step_reason_display(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
) -> Optional[str]:
    status = str(step.get("status") or "").strip().lower()
    reason_display = humanize_executed_step_reason_text(step.get("reason"))
    if reason_display:
        return reason_display
    if status == "missing_parameters" and isinstance(step.get("parameterErrors"), list):
        rendered = [
            item
            for item in (
                humanize_parameter_error_message(step, item)
                for item in step.get("parameterErrors", [])
            )
            if isinstance(item, str) and item.strip()
        ]
        if rendered:
            return join_display_sentences(rendered)
    if status in {"planned", "ok", "failed"} and runtime_payload_has_blocker(payload):
        return (
            humanize_review_failure(worknet_key, step, payload)
            or runtime_payload_error_summary(payload)
            or runtime_message(payload)
        )
    if status == "failed":
        stderr = step.get("result", {}).get("stderr") if isinstance(step.get("result"), dict) else None
        if isinstance(stderr, str) and stderr.strip():
            return stderr.strip().splitlines()[0]
    if status in {"queued_for_confirmation", "awaiting_confirmation", "missing_runtime_command"}:
        label = str(step.get("label") or "").strip()
        return humanize_review_status_token(worknet_key, label, status)
    return None


def humanize_executed_step_detail_display(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
) -> Optional[str]:
    status = str(step.get("status") or "").strip().lower()
    label = str(step.get("label") or "").strip()
    message = runtime_message(payload)
    reason_display = humanize_executed_step_reason_display(worknet_key, step, payload)
    if status == "started_background":
        return humanize_started_background_detail(step)
    if status == "background_running":
        return "这一步启动的后台任务仍在运行。"
    if status in {"planned", "ok"} and runtime_payload_has_blocker(payload):
        return reason_display or humanize_review_status_token(worknet_key, label, status)
    if status in {"planned", "ok"}:
        return executed_step_payload_summary_display(worknet_key, step, payload) or humanize_review_status_token(worknet_key, label, status)
    if status in {"available_manual", "skipped_after_primary_work", "blocked_after_previous_step"}:
        return reason_display or humanize_review_status_token(worknet_key, label, status)
    if status in {"queued_for_confirmation", "awaiting_confirmation", "missing_runtime_command", "failed", "missing_parameters"}:
        return reason_display or executed_step_payload_summary_display(worknet_key, step, payload) or humanize_review_status_token(worknet_key, label, status)
    return reason_display or humanize_review_status_token(worknet_key, label, status) or message


def build_executed_step_stdout_display(
    worknet_key: str,
    step: dict[str, Any],
    payload: Any,
) -> Optional[dict[str, Any]]:
    if payload is None:
        return None
    summary = executed_step_payload_summary_display(worknet_key, step, payload)
    preview = structured_preview_text(payload)
    if isinstance(payload, dict):
        display: dict[str, Any] = {
            "kind": "structured",
            "summary": summary,
            "preview": preview,
        }
        if preview:
            display["previewRaw"] = preview
        state = str(payload.get("state") or "").strip()
        if state:
            display["state"] = state
            display["stateDisplay"] = humanize_runtime_payload_state(state)
        message = runtime_message(payload)
        if message:
            display["message"] = message
            display["messageRaw"] = message
            message_display = humanize_runtime_guidance_message_display(
                worknet_key or None,
                message,
                state=state or None,
            )
            if message_display:
                display["message"] = message_display
                display["messageDisplay"] = message_display
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            display["detail"] = detail.strip()
            display["detailRaw"] = detail.strip()
        error_summary = runtime_payload_error_summary(payload)
        if error_summary and error_summary != message:
            display["errorSummary"] = error_summary
        guidance = extract_runtime_guidance_from_payload(payload, worknet_key=worknet_key or None)
        if isinstance(guidance, dict):
            guidance = dict(guidance)
            if should_replace_display_text(guidance.get("messageDisplay"), summary):
                raw_guidance_message = str(guidance.get("message") or "").strip()
                if raw_guidance_message and raw_guidance_message != summary and "messageRaw" not in guidance:
                    guidance["messageRaw"] = raw_guidance_message
                guidance["message"] = summary
                guidance["messageDisplay"] = summary
            humanized_next_command = humanize_runtime_next_command_display(
                worknet_key or None,
                guidance.get("nextCommand"),
            )
            if humanized_next_command:
                guidance["nextCommandDisplay"] = humanized_next_command
            guidance_preview = runtime_guidance_preview_display(guidance)
            if guidance_preview:
                guidance["previewDisplay"] = guidance_preview
            display["guidance"] = guidance
            next_command = guidance.get("nextCommand")
            if isinstance(next_command, list) and next_command:
                display["nextCommandDisplay"] = humanize_runtime_next_command_display(
                    worknet_key or None,
                    next_command,
                ) or render_argv([str(part) for part in next_command])
            preview_display = str(guidance.get("previewDisplay") or "").strip()
            if preview_display:
                display["previewDisplay"] = preview_display
        if should_replace_display_text(display.get("messageDisplay"), summary):
            if isinstance(display.get("message"), str) and display.get("message") != summary and "messageRaw" not in display:
                display["messageRaw"] = display.get("message")
            display["message"] = summary
            display["messageDisplay"] = summary
        detail_display = str(display.get("messageDisplay") or display.get("summary") or "").strip()
        if detail_display:
            if isinstance(display.get("detail"), str) and display.get("detail") != detail_display and "detailRaw" not in display:
                display["detailRaw"] = display.get("detail")
            display["detail"] = detail_display
            display["detailDisplay"] = detail_display
        error_display = str(display.get("summary") or display.get("messageDisplay") or "").strip()
        if error_display:
            if isinstance(display.get("errorSummary"), str) and display.get("errorSummary") != error_display and "errorSummaryRaw" not in display:
                display["errorSummaryRaw"] = display.get("errorSummary")
            display["errorSummary"] = error_display
            display["errorSummaryDisplay"] = error_display
        if not isinstance(display.get("previewDisplay"), str):
            preview_display = str(display.get("messageDisplay") or display.get("summary") or "").strip()
            if preview_display:
                display["previewDisplay"] = compact_preview_text(
                    preview_display,
                    max_chars=180,
                    max_sentences=2,
                )
        if isinstance(display.get("previewDisplay"), str):
            display["preview"] = display["previewDisplay"]
            display["structuredPreviewDisplay"] = display["previewDisplay"]
        return display
    return {
        "kind": type(payload).__name__,
        "summary": summary or preview,
        "preview": summary or preview,
        "previewRaw": preview,
        "previewDisplay": summary or preview,
        "structuredPreviewDisplay": summary or preview,
    }


def build_executed_step_result_display(
    worknet_key: str,
    step: dict[str, Any],
) -> Optional[dict[str, Any]]:
    result = step.get("result")
    if not isinstance(result, dict):
        return None
    payload = executed_step_result_payload(step)
    stdout_display = build_executed_step_stdout_display(worknet_key, step, payload)
    stderr = result.get("stderr")
    stderr_display = compact_preview_text(stderr, max_chars=180, max_sentences=2) if isinstance(stderr, str) and stderr.strip() else None
    code = result.get("code")
    summary = None
    if isinstance(stdout_display, dict):
        summary = str(stdout_display.get("summary") or "").strip() or None
    summary = summary or stderr_display
    if not summary and code is not None:
        summary = f"命令已返回退出码 {code}。"
    raw_summary = None
    if isinstance(stdout_display, dict):
        raw_summary = str(
            stdout_display.get("summaryRaw")
            or stdout_display.get("previewRaw")
            or stdout_display.get("messageRaw")
            or ""
        ).strip() or None
    raw_summary = raw_summary or stderr_display
    preview_display = None
    if isinstance(stdout_display, dict):
        preview_display = str(stdout_display.get("previewDisplay") or stdout_display.get("summary") or "").strip() or None
    preview_display = preview_display or summary
    preview_raw = None
    if isinstance(stdout_display, dict):
        preview_raw = str(stdout_display.get("previewRaw") or "").strip() or None
    preview_raw = preview_raw or stderr_display or raw_summary
    payload = {
        "code": code,
        "codeDisplay": f"退出码 {code}" if code is not None else None,
        "summary": summary,
        "summaryDisplay": summary,
        "summaryRaw": raw_summary,
        "preview": preview_display,
        "previewDisplay": preview_display,
        "previewRaw": preview_raw,
        "structuredPreviewDisplay": preview_display,
        "stdoutDisplay": stdout_display,
        "stderrDisplay": stderr_display,
        "stderrDisplayRaw": stderr_display,
    }
    if not isinstance(payload.get("previewDisplay"), str):
        preview_text = str(summary or "").strip()
        if preview_text:
            payload["preview"] = preview_text
            payload["previewDisplay"] = preview_text
            payload["structuredPreviewDisplay"] = preview_text
    return payload


def annotate_executed_step(step: Any, *, worknet_key: Optional[str] = None) -> Any:
    if not isinstance(step, dict):
        return step
    normalized = dict(step)
    label = str(normalized.get("label") or "").strip()
    command = render_argv(normalized.get("argv", [])) if isinstance(normalized.get("argv"), list) else None
    policy = str(normalized.get("executionPolicy") or "").strip().lower()
    status = str(normalized.get("status") or "").strip().lower()
    display_label = humanize_executed_step_label(
        label,
        category=normalized.get("category"),
        execution_policy=normalized.get("executionPolicy"),
    ) if label else None
    if display_label:
        normalized["displayLabel"] = display_label
    if status in {"queued_for_confirmation", "awaiting_confirmation"} or policy == "confirmation":
        group_key = "confirmations"
        tier = "current"
    elif status == "started_background":
        group_key = "background"
        tier = "current"
    elif policy in {"probe", "manual-review"} or str(normalized.get("category") or "").strip().lower() == "inspect":
        group_key = "inspect"
        tier = "related"
    elif policy in {"setup", "manual-setup"}:
        group_key = "setup"
        tier = "overview"
    else:
        action_meta = annotate_execution_actions([
            {
                "label": label,
                "command": command,
                "executionPolicy": normalized.get("executionPolicy"),
                "status": normalized.get("status"),
            }
        ])
        action_group_key = str(action_meta[0].get("actionGroupKey") or "").strip() if action_meta else ""
        action_tier = str(action_meta[0].get("actionTier") or "").strip() if action_meta else ""
        group_key = action_group_key or "current"
        tier = action_tier or "current"
    normalized["stepGroupKey"] = group_key
    normalized["stepGroupLabel"] = STEP_GROUP_LABELS.get(group_key, group_key)
    normalized["stepGroupRank"] = RESEARCH_HIGHLIGHT_GROUP_RANKS.get(group_key)
    normalized["stepTier"] = tier
    normalized["stepTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get(tier, tier)
    normalized["stepTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
    normalized["actionGroupKey"] = group_key
    normalized["actionGroupLabel"] = STEP_GROUP_LABELS.get(group_key, group_key)
    normalized["actionGroupRank"] = RESEARCH_HIGHLIGHT_GROUP_RANKS.get(group_key)
    normalized["actionTier"] = tier
    normalized["actionTierLabel"] = RESEARCH_HIGHLIGHT_TIER_LABELS.get(tier, tier)
    normalized["actionTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
    resolved_worknet_key = str(worknet_key or normalized.get("worknetKey") or "").strip().lower()
    payload = executed_step_result_payload(normalized)
    normalized["statusDisplay"] = humanize_executed_step_status_display(status)
    detail_display = humanize_executed_step_detail_display(resolved_worknet_key, normalized, payload)
    if detail_display:
        normalized["detailDisplay"] = detail_display
    reason_display = humanize_executed_step_reason_display(resolved_worknet_key, normalized, payload)
    if reason_display:
        normalized["reasonDisplay"] = reason_display
    result_display = build_executed_step_result_display(resolved_worknet_key, normalized)
    if isinstance(result_display, dict):
        normalized["resultDisplay"] = result_display
        if result_display.get("summary"):
            normalized["resultSummary"] = result_display.get("summary")
        if result_display.get("previewDisplay"):
            normalized["previewDisplay"] = result_display.get("previewDisplay")
        if result_display.get("stdoutDisplay") is not None:
            normalized["stdoutDisplay"] = result_display.get("stdoutDisplay")
        if result_display.get("stderrDisplay"):
            normalized["stderrDisplay"] = result_display.get("stderrDisplay")
    elif detail_display or reason_display or normalized.get("statusDisplay"):
        normalized["resultSummary"] = detail_display or reason_display or normalized.get("statusDisplay")
    if isinstance(normalized.get("parameterErrors"), list):
        normalized["parameterErrorsDisplay"] = [
            humanize_parameter_error_message(normalized, item) or str(item)
            for item in normalized.get("parameterErrors", [])
        ]
    if isinstance(normalized.get("parameterSchema"), list):
        normalized["parameterSchemaDisplay"] = annotate_parameter_schema_items(normalized.get("parameterSchema"))
    if isinstance(normalized.get("runtimeGuidance"), dict):
        normalized["runtimeGuidance"] = annotate_runtime_guidance_payload(
            normalized.get("runtimeGuidance"),
            worknet_key=resolved_worknet_key or None,
        )
    if isinstance(normalized.get("backgroundProcess"), dict):
        normalized["backgroundProcess"] = annotate_background_record(normalized.get("backgroundProcess"))
    return normalized


def annotate_executed_steps(
    steps: Any,
    *,
    worknet_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    if not isinstance(steps, list):
        return []
    return [
        annotated
        for annotated in (
            annotate_executed_step(step, worknet_key=worknet_key)
            for step in steps
        )
        if isinstance(annotated, dict)
    ]


def runtime_next_command(payload: Any) -> Optional[list[str]]:
    if not isinstance(payload, dict):
        return None
    internal = payload.get("_internal")
    if not isinstance(internal, dict):
        return None
    value = internal.get("next_command")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return shlex.split(value)
    except ValueError:
        return None


def extract_runtime_guidance_from_payload(
    payload: Any,
    *,
    worknet_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    message = runtime_message(payload)
    actions = payload.get("user_actions")
    user_actions = [str(item) for item in actions if isinstance(item, str) and str(item).strip()] if isinstance(actions, list) else []
    action_map = runtime_action_map(payload)
    next_command = runtime_next_command(payload)
    next_action = None
    internal = payload.get("_internal")
    if isinstance(internal, dict) and isinstance(internal.get("next_action"), str):
        next_action = str(internal.get("next_action"))
    state = payload.get("state") if isinstance(payload.get("state"), str) else None
    if not any([message, user_actions, action_map, next_command, next_action, state]):
        return None
    return annotate_runtime_guidance_payload({
        "message": message,
        "userActions": user_actions,
        "actionMap": action_map,
        "nextCommand": next_command,
        "nextAction": next_action,
        "state": state,
    }, worknet_key=worknet_key)


def render_argv(argv: list[str]) -> str:
    if not argv:
        return ""
    return shlex.join([str(item) for item in argv])


def guidance_action(
    label: str,
    command: Optional[str],
    *,
    argv: Optional[list[str]] = None,
    cwd: Optional[str] = None,
    safe_to_auto_run: bool = False,
    requires_confirmation: bool = False,
    preferred: bool = False,
    parameter_schema: Optional[list[dict[str, Any]]] = None,
    long_running: bool = False,
) -> dict[str, Any]:
    payload = {
        "label": label,
        "displayLabel": humanize_public_action_label(label),
        "command": command,
        "argv": argv,
        "cwd": cwd,
        "safeToAutoRun": safe_to_auto_run,
        "requiresConfirmation": requires_confirmation,
        "selectedByDefault": preferred,
        "parameterSchema": parameter_schema or [],
        "longRunning": long_running,
    }
    annotated = annotate_execution_actions([payload])
    return annotated[0] if annotated else payload


def skill_script_action(
    label: str,
    script_name: str,
    *args: str,
    preferred: bool = False,
) -> dict[str, Any]:
    argv = ["python3", str(SKILL_ROOT / "scripts" / script_name), *args]
    return guidance_action(
        label,
        render_argv(argv),
        argv=argv,
        cwd=str(SKILL_ROOT / "scripts"),
        safe_to_auto_run=True,
        preferred=preferred,
    )


PREDICT_PERSONAS = [
    "degen",
    "conservative",
    "sniper",
    "contrarian",
    "chartist",
    "macro",
    "sentiment",
]


def workstation_follow_up_command(label: str, *, execute: bool) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--follow-up-label",
        label,
    ]
    if execute:
        argv.append("--execute")
    return render_argv(argv)


def workstation_confirmation_command(label: str, *, execute: bool) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--confirm-label",
        label,
    ]
    if execute:
        argv.append("--execute")
    return render_argv(argv)


def workstation_background_command(
    label: str,
    *,
    stop: bool = False,
    execute: bool = False,
    tail_lines: Optional[int] = None,
) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
    ]
    argv.extend(["--stop-background-label" if stop else "--background-label", label])
    if tail_lines is not None:
        argv.extend(["--tail-lines", str(tail_lines)])
    if execute:
        argv.append("--execute")
    return render_argv(argv)


def workstation_pause_command(*, execute: bool) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--pause",
    ]
    if execute:
        argv.append("--execute")
    return render_argv(argv)


def query_source_command(source_key: str, *, rebuild: bool = False) -> str:
    argv = [
        "python3",
        "scripts/query-source.py",
        "--source-key",
        source_key,
    ]
    if rebuild:
        argv.append("--rebuild")
    return render_argv(argv)


def query_knowledge_command(topic_key: str, *, rebuild: bool = False) -> str:
    argv = [
        "python3",
        "scripts/query-knowledge.py",
        "--topic",
        topic_key,
    ]
    if rebuild:
        argv.append("--rebuild")
    return render_argv(argv)


def knowledge_review_queue_command(*, refresh: bool = False) -> str:
    argv = [
        "python3",
        "scripts/knowledge-review-queue.py",
    ]
    if refresh:
        argv.append("--refresh")
    return render_argv(argv)


def start_workstation_command() -> str:
    return render_argv(["python3", "scripts/start-workstation.py"])


def review_epoch_command(*, full: bool = False) -> str:
    argv = ["python3", "scripts/review-epoch.py"]
    if full:
        argv.append("--full")
    return render_argv(argv)


def workstation_status_command(
    *,
    query: Optional[str] = None,
    intent: Optional[str] = None,
    worknet: Optional[str] = None,
    full: bool = False,
) -> str:
    argv = ["python3", "scripts/workstation-status.py"]
    if query is not None:
        argv.extend(["--query", query])
    if intent is not None:
        argv.extend(["--intent", intent])
    if worknet is not None:
        argv.extend(["--worknet", worknet])
    if full:
        argv.append("--full")
    return render_argv(argv)


def workstation_preflight_command(*, full: bool = False) -> str:
    argv = ["python3", "scripts/workstation-preflight.py"]
    if full:
        argv.append("--full")
    return render_argv(argv)


def scan_worknets_command() -> str:
    return render_argv(["python3", "scripts/scan-worknets.py"])


def build_playbook_command(worknet_identifier: str, *, full: bool = False) -> str:
    argv = [
        "python3",
        "scripts/build-playbook.py",
        "--worknet",
        worknet_identifier,
    ]
    if full:
        argv.append("--full")
    return render_argv(argv)


def run_worknet_command(
    worknet_identifier: str,
    *,
    execute: bool,
    auto_advance: bool = False,
) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--worknet",
        worknet_identifier,
    ]
    if execute:
        argv.append("--execute")
    if auto_advance:
        argv.append("--auto-advance")
    return render_argv(argv)


def workstation_preferences_command(
    *,
    preferred_worknet: Optional[str] = None,
    allow_asset_actions: Optional[bool] = None,
    autopilot_mode: Optional[str] = None,
    allow_third_party_skills: Optional[bool] = None,
    observe_before_predict_hours: Optional[int] = None,
    risk_profile: Optional[str] = None,
) -> str:
    argv = [
        "python3",
        "scripts/workstation-preferences.py",
    ]
    if preferred_worknet is not None:
        argv.extend(["--preferred-worknet", preferred_worknet])
    if allow_asset_actions is not None:
        argv.extend(["--allow-asset-actions", "true" if allow_asset_actions else "false"])
    if autopilot_mode is not None:
        argv.extend(["--autopilot-mode", autopilot_mode])
    if allow_third_party_skills is not None:
        argv.extend(["--allow-third-party-skills", "true" if allow_third_party_skills else "false"])
    if observe_before_predict_hours is not None:
        argv.extend(["--observe-before-predict-hours", str(observe_before_predict_hours)])
    if risk_profile is not None:
        argv.extend(["--risk-profile", risk_profile])
    return render_argv(argv)


def summarize_knowledge_review_queue(queue: Any) -> dict[str, Any]:
    if not isinstance(queue, dict):
        return normalize_knowledge_review_queue_summary({
            "available": False,
            "hasPendingReviews": False,
            "pendingReviewCount": 0,
            "changedSourceCount": 0,
            "topicCount": 0,
            "factCount": 0,
            "evidenceCount": 0,
            "worknetCount": 0,
            "highestPriority": None,
            "focusSources": [],
            "focusTopics": [],
            "headline": "当前还没有生成知识待重审队列。",
            "primaryActionLabel": None,
            "primaryActionCommand": None,
            "refreshActionLabel": "刷新知识待重审队列",
            "refreshActionCommand": knowledge_review_queue_command(refresh=True),
            "generatedAt": None,
            "sourceImpactGeneratedAt": None,
        })

    priority_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    summary = queue.get("summary", {}) if isinstance(queue.get("summary"), dict) else {}
    entries = queue.get("entries", []) if isinstance(queue.get("entries"), list) else []
    source_labels: list[str] = []
    topic_labels: list[str] = []
    highest_priority: Optional[str] = None

    for item in entries:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        priority = str(item.get("priority") or "low")
        if priority_rank.get(priority, 0) > priority_rank.get(str(highest_priority or "low"), 0):
            highest_priority = priority
        if item.get("kind") == "source" and label not in source_labels:
            source_labels.append(label)
        if item.get("kind") == "topic" and label not in topic_labels:
            topic_labels.append(label)

    pending_review_count = int(summary.get("entries", len(entries)) or 0)
    changed_source_count = int(summary.get("sources", len(source_labels)) or 0)
    topic_count = int(summary.get("topics", len(topic_labels)) or 0)
    fact_count = int(summary.get("facts", 0) or 0)
    evidence_count = int(summary.get("evidence", 0) or 0)
    worknet_count = int(summary.get("worknets", 0) or 0)
    focus_sources = source_labels[:3]
    focus_topics = topic_labels[:3]
    focus_sources_display = [humanize_knowledge_source_label(item) for item in focus_sources]
    has_pending_reviews = pending_review_count > 0

    if has_pending_reviews:
        headline = f"最近有 {changed_source_count} 个上游来源发生变化，当前有 {pending_review_count} 条知识待重审"
        if topic_count:
            headline += f"，涉及 {topic_count} 个主题"
        if focus_topics:
            headline += f"，优先看 {'、'.join(focus_topics)}"
        headline += "。"
    else:
        headline = "当前没有待重审的知识条目。"

    return normalize_knowledge_review_queue_summary({
        "available": True,
        "hasPendingReviews": has_pending_reviews,
        "pendingReviewCount": pending_review_count,
        "changedSourceCount": changed_source_count,
        "topicCount": topic_count,
        "factCount": fact_count,
        "evidenceCount": evidence_count,
        "worknetCount": worknet_count,
        "highestPriority": highest_priority,
        "highestPriorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(str(highest_priority or "").strip()),
        "focusSources": focus_sources,
        "focusSourcesDisplay": focus_sources_display,
        "focusTopics": focus_topics,
        "headline": headline,
        "primaryActionLabel": "查看知识待重审队列" if has_pending_reviews else None,
        "primaryActionCommand": query_knowledge_command("review-queue") if has_pending_reviews else None,
        "refreshActionLabel": "刷新知识待重审队列",
        "refreshActionCommand": knowledge_review_queue_command(refresh=True),
        "generatedAt": queue.get("generatedAt"),
        "sourceImpactGeneratedAt": queue.get("sourceImpactGeneratedAt"),
    })


def append_user_action(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    *,
    label: Optional[str],
    description: str,
    command: Optional[str],
) -> None:
    text = str(label or "").strip()
    resolved_command = str(command or "").strip()
    if not text or not resolved_command:
        return
    if any(isinstance(item, dict) and item.get("label") == text for item in actions):
        return
    actions.append({"label": text, "description": description})
    action_map[text] = resolved_command


def merge_recovery_decision_actions(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    decision: Any,
    *,
    prefer_front: bool = False,
) -> None:
    if not isinstance(decision, dict):
        return
    items = decision.get("actions")
    if not isinstance(items, list):
        return
    desired_order: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        command = item.get("command") if isinstance(item.get("command"), str) else None
        if not label or not isinstance(command, str) or not command.strip():
            continue
        action_map[label] = command.strip()
        desired_order.append(
            {
                "label": label,
                "description": str(item.get("description") or "继续这个恢复动作。"),
            }
        )

    if prefer_front and desired_order:
        existing_by_label = {
            str(item.get("label")): item
            for item in actions
            if isinstance(item, dict) and isinstance(item.get("label"), str) and item.get("label").strip()
        }
        ordered: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in desired_order:
            label = item["label"]
            ordered.append(
                existing_by_label.get(
                    label,
                    {
                        "label": label,
                        "description": item["description"],
                    },
                )
            )
            seen.add(label)
        for item in actions:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label or label in seen:
                continue
            ordered.append(item)
        actions[:] = ordered
    else:
        for item in desired_order:
            if any(isinstance(existing, dict) and existing.get("label") == item["label"] for existing in actions):
                continue
            actions.append(item)


def maybe_promote_recovery_decision(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    decision: Any,
) -> None:
    if not isinstance(decision, dict):
        return
    status = str(decision.get("status") or "").strip()
    if status not in {"resume_available", "restart_available", "prefer_fresh_start", "needs_confirmation", "follow_runtime_guidance", "background_running"}:
        return
    merge_recovery_decision_actions(actions, action_map, decision, prefer_front=True)


def merge_payload_user_actions(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    payload: Any,
) -> None:
    if not isinstance(payload, dict):
        return
    items = payload.get("user_actions")
    source_map = payload.get("_internal", {}).get("action_map", {})
    if not isinstance(items, list) or not isinstance(source_map, dict):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        description = str(item.get("description") or "继续这个建议动作。")
        command = source_map.get(label)
        append_user_action(
            actions,
            action_map,
            label=label,
            description=description,
            command=command if isinstance(command, str) else None,
        )


def merge_payload_user_action_details(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    payload: Any,
    *,
    limit: Optional[int] = None,
) -> None:
    if not isinstance(payload, dict):
        return
    items = payload.get("userActionDetails")
    if not isinstance(items, list):
        return
    for item in items[:limit] if isinstance(limit, int) and limit >= 0 else items:
        if not isinstance(item, dict):
            continue
        label = item.get("displayLabel") or item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        append_user_action(
            actions,
            action_map,
            label=label,
            description=str(item.get("description") or "继续这个建议动作。").strip(),
            command=str(item.get("command") or "").strip() or None,
        )


def find_user_action_label(
    actions: list[dict[str, Any]],
    *,
    exact: Optional[str] = None,
    prefix: Optional[str] = None,
    contains: Optional[str] = None,
) -> Optional[str]:
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        if exact and label == exact:
            return label
        if prefix and label.startswith(prefix):
            return label
        if contains and contains in label:
            return label
    return None


def frontload_user_action_labels(
    actions: list[dict[str, Any]],
    labels: list[Any],
) -> list[dict[str, Any]]:
    if not isinstance(actions, list) or not actions:
        return actions
    wanted = [str(label or "").strip() for label in labels if str(label or "").strip()]
    if not wanted:
        return actions
    existing_by_label = {
        str(item.get("label") or "").strip(): item
        for item in actions
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    }
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for label in wanted:
        item = existing_by_label.get(label)
        if not isinstance(item, dict):
            continue
        ordered.append(item)
        seen.add(label)
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label or label in seen:
            continue
        ordered.append(item)
    return ordered


def annotate_research_action_details(
    user_action_details: list[dict[str, Any]],
    *,
    current_labels: list[Any],
    control_labels: list[Any],
    source_labels: list[Any],
    topic_labels: list[Any],
    worknet_labels: list[Any],
    reference_labels: list[Any],
    background_labels: Optional[list[Any]] = None,
    review_labels: Optional[list[Any]] = None,
    confirmation_labels: Optional[list[Any]] = None,
    current_tier: str = "current",
    control_tier: str = "overview",
    source_tier: str = "overview",
    topic_tier: str = "overview",
    worknet_tier: str = "overview",
    reference_tier: str = "overview",
    background_tier: str = "current",
    review_tier: str = "related",
    confirmation_tier: str = "current",
    group_label_overrides: Optional[dict[str, str]] = None,
    group_rank_overrides: Optional[dict[str, int]] = None,
    tier_label_overrides: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    normalized_buckets = [
        ("current", current_tier, {str(item or "").strip() for item in current_labels if str(item or "").strip()}),
        ("confirmations", confirmation_tier, {str(item or "").strip() for item in (confirmation_labels or []) if str(item or "").strip()}),
        ("background", background_tier, {str(item or "").strip() for item in (background_labels or []) if str(item or "").strip()}),
        ("control", control_tier, {str(item or "").strip() for item in control_labels if str(item or "").strip()}),
        ("sources", source_tier, {str(item or "").strip() for item in source_labels if str(item or "").strip()}),
        ("topics", topic_tier, {str(item or "").strip() for item in topic_labels if str(item or "").strip()}),
        ("worknets", worknet_tier, {str(item or "").strip() for item in worknet_labels if str(item or "").strip()}),
        ("review", review_tier, {str(item or "").strip() for item in (review_labels or []) if str(item or "").strip()}),
        ("references", reference_tier, {str(item or "").strip() for item in reference_labels if str(item or "").strip()}),
    ]
    group_labels = dict(RESEARCH_HIGHLIGHT_GROUP_LABELS)
    if isinstance(group_label_overrides, dict):
        group_labels.update(
            {
                str(key).strip(): str(value).strip()
                for key, value in group_label_overrides.items()
                if str(key).strip() and str(value).strip()
            }
        )
    group_ranks = dict(RESEARCH_HIGHLIGHT_GROUP_RANKS)
    if isinstance(group_rank_overrides, dict):
        group_ranks.update(
            {
                str(key).strip(): int(value)
                for key, value in group_rank_overrides.items()
                if str(key).strip() and isinstance(value, int)
            }
        )
    tier_labels = dict(RESEARCH_HIGHLIGHT_TIER_LABELS)
    if isinstance(tier_label_overrides, dict):
        tier_labels.update(
            {
                str(key).strip(): str(value).strip()
                for key, value in tier_label_overrides.items()
                if str(key).strip() and str(value).strip()
            }
        )
    annotated: list[dict[str, Any]] = []
    for item in user_action_details if isinstance(user_action_details, list) else []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            annotated.append(dict(item))
            continue
        normalized = dict(item)
        for group_key, tier, labels in normalized_buckets:
            if label not in labels:
                continue
            normalized["researchGroupKey"] = group_key
            normalized["researchGroupLabel"] = group_labels.get(group_key, group_key)
            normalized["researchGroupRank"] = group_ranks.get(group_key)
            normalized["researchTier"] = tier
            normalized["researchTierLabel"] = tier_labels.get(tier, tier)
            normalized["researchTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
            normalized["actionGroupKey"] = group_key
            normalized["actionGroupLabel"] = group_labels.get(group_key, group_key)
            normalized["actionGroupRank"] = group_ranks.get(group_key)
            normalized["actionTier"] = tier
            normalized["actionTierLabel"] = tier_labels.get(tier, tier)
            normalized["actionTierRank"] = RESEARCH_HIGHLIGHT_TIER_RANKS.get(tier)
            break
        annotated.append(normalized)
    return annotated


def research_action_group_payload(
    user_action_details: list[dict[str, Any]],
    *,
    key: str,
    label: str,
    summary: str,
    labels: list[Any],
) -> Optional[dict[str, Any]]:
    wanted = {str(item or "").strip() for item in labels if str(item or "").strip()}
    if not wanted:
        return None
    items = [
        dict(item)
        for item in user_action_details
        if isinstance(item, dict) and str(item.get("label") or "").strip() in wanted
    ]
    if not items:
        return None
    return {
        "key": key,
        "label": label,
        "summary": summary,
        "count": len(items),
        "actions": items,
    }


def build_research_action_groups(
    user_action_details: list[dict[str, Any]],
    *,
    current_labels: list[Any],
    control_labels: list[Any],
    source_labels: list[Any],
    topic_labels: list[Any],
    worknet_labels: list[Any],
    reference_labels: list[Any],
    control_first: bool = True,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    ordered_group_specs = (
        research_action_group_payload(
            user_action_details,
            key="current",
            label="当前条目",
            summary="先处理当前这条主题、来源或队列本身的动作。",
            labels=current_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="control",
            label="百科总控",
            summary="先进入待重审总队列，再决定先追哪条上游变化。",
            labels=control_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="sources",
            label="高优先来源",
            summary="直接回到最近发生变化或最值得先看的官方来源。",
            labels=source_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="topics",
            label="高层主题",
            summary="按主题理解协议、RootNet、WorkNet 和各条工作路线。",
            labels=topic_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="worknets",
            label="WorkNet 入口",
            summary="回到所有 WorkNet 的可运行性、风险和入口动作对比。",
            labels=worknet_labels,
        ),
        research_action_group_payload(
            user_action_details,
            key="references",
            label="底层参考",
            summary="需要追协议细节、运行时约束和证据时，再下钻这些参考条目。",
            labels=reference_labels,
        ),
    )
    if control_first:
        ordered_payloads = ordered_group_specs
    else:
        ordered_payloads = (
            ordered_group_specs[0],
            ordered_group_specs[2],
            ordered_group_specs[3],
            ordered_group_specs[4],
            ordered_group_specs[1],
            ordered_group_specs[5],
        )
    for payload in ordered_payloads:
        if isinstance(payload, dict):
            groups.append(payload)
    return groups


def execution_action_label_buckets(
    actions: list[dict[str, Any]],
) -> dict[str, list[str]]:
    buckets = {
        "current": [],
        "control": [],
        "sources": [],
        "topics": [],
        "worknets": [],
        "background": [],
        "review": [],
        "confirmations": [],
        "references": [],
    }
    for item in actions if isinstance(actions, list) else []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        command = str(item.get("command") or "").strip()
        execution_policy = str(item.get("executionPolicy") or "").strip().lower()
        status = str(item.get("status") or "").strip().lower()
        requires_confirmation = bool(item.get("requiresConfirmation"))
        if not label:
            continue
        if (
            label.startswith("确认 ")
            or requires_confirmation
            or execution_policy == "confirmation"
            or status in {"queued_for_confirmation", "awaiting_confirmation"}
        ):
            buckets["confirmations"].append(label)
        elif execution_policy == "manual-control" or label.startswith("暂停 ") or label.lower().startswith("pause "):
            buckets["control"].append(label)
        elif label == "暂停当前运行" or label.startswith("停止 ") or "--background-label" in command or "--stop-background-label" in command:
            buckets["background"].append(label)
        elif label in {"查看上次复盘", "查看知识待重审队列", "刷新知识待重审队列"} or "review-epoch.py" in command:
            buckets["review"].append(label)
        elif label.startswith("查看来源 ") or label.startswith("重读来源 "):
            buckets["sources"].append(label)
        elif label.startswith("查看参考 "):
            buckets["references"].append(label)
        elif label.startswith("查看 ") and label.endswith(" 档案") or label.startswith("重审 "):
            buckets["topics"].append(label)
        elif (
            label == "查看 WorkNet 扫描"
            or "playbook" in label.lower()
            or label.startswith("把 ") and "WorkNet" in label
            or label.startswith("查看当前默认 ")
        ):
            buckets["worknets"].append(label)
        elif label in {"研究 AWP 百科", "查看预检", "锁定为非资金模式"}:
            buckets["control"].append(label)
        else:
            buckets["current"].append(label)
    return buckets


def annotate_execution_actions(
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    buckets = execution_action_label_buckets(actions)
    return annotate_research_action_details(
        actions,
        current_labels=buckets["current"],
        control_labels=buckets["control"],
        source_labels=buckets["sources"],
        topic_labels=buckets["topics"],
        worknet_labels=buckets["worknets"],
        reference_labels=buckets["references"],
        background_labels=buckets["background"],
        review_labels=buckets["review"],
        confirmation_labels=buckets["confirmations"],
        group_label_overrides=EXECUTION_ACTION_GROUP_LABEL_OVERRIDES,
        control_tier="overview",
        source_tier="related",
        topic_tier="related",
        worknet_tier="related",
        reference_tier="related",
        background_tier="current",
        review_tier="related",
        confirmation_tier="current",
    )


def annotate_recovery_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets = execution_action_label_buckets(actions)
    return annotate_research_action_details(
        actions,
        current_labels=[*buckets["current"], *buckets["confirmations"]],
        control_labels=buckets["control"],
        source_labels=buckets["sources"],
        topic_labels=buckets["topics"],
        worknet_labels=buckets["worknets"],
        reference_labels=buckets["references"],
        background_labels=buckets["background"],
        review_labels=buckets["review"],
        confirmation_labels=[],
        group_label_overrides={
            **EXECUTION_ACTION_GROUP_LABEL_OVERRIDES,
            "current": "恢复动作",
            "worknets": "恢复路线",
            "review": "恢复复盘",
        },
        group_rank_overrides={
            "current": 0,
            "worknets": 1,
            "review": 2,
        },
        control_tier="overview",
        source_tier="related",
        topic_tier="related",
        worknet_tier="related",
        reference_tier="related",
        background_tier="current",
        review_tier="related",
    )


def dedupe_action_entries(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        command = str(item.get("command") or "").strip()
        if not label or not command:
            continue
        key = (label, command)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "label": label,
                "description": str(item.get("description") or "继续这个恢复动作。"),
                "command": command,
            }
        )
    return deduped


def recovery_decision_actions_from_ui(
    user_actions: list[dict[str, Any]],
    action_map: dict[str, str],
    *,
    primary_label: Optional[str] = None,
    restart_label: Optional[str] = None,
    switch_label: Optional[str] = None,
) -> list[dict[str, Any]]:
    priority_labels = [
        label
        for label in [primary_label, restart_label, switch_label, "查看上次复盘"]
        if isinstance(label, str) and label.strip()
    ]
    items_by_label = {
        str(item.get("label")): item
        for item in user_actions
        if isinstance(item, dict) and isinstance(item.get("label"), str) and item.get("label").strip()
    }
    actions: list[dict[str, Any]] = []
    for label in priority_labels:
        item = items_by_label.get(label)
        command = action_map.get(label)
        if item is None or not isinstance(command, str) or not command.strip():
            continue
        actions.append(
            {
                "label": label,
                "description": str(item.get("description") or "继续这个恢复动作。"),
                "command": command.strip(),
            }
        )
    return dedupe_action_entries(actions)


def recovery_decision_actions_from_recovery(
    recovery: Any,
    *,
    preferred_profile: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    recovery = recovery if isinstance(recovery, dict) else {}
    preferred_profile = preferred_profile if isinstance(preferred_profile, dict) else None
    worknet_key = str(recovery.get("lastWorknetKey") or "").strip()
    worknet_profile = resolve_worknet(worknet_key) if worknet_key else None
    worknet_name = (
        str(worknet_profile.get("name"))
        if isinstance(worknet_profile, dict) and worknet_profile.get("name")
        else worknet_key
    )
    preferred_key = str(preferred_profile.get("key")) if isinstance(preferred_profile, dict) and preferred_profile.get("key") else None
    actions: list[dict[str, Any]] = []
    active_background = recovery.get("activeBackgroundProcesses", []) if isinstance(recovery.get("activeBackgroundProcesses"), list) else []
    has_runtime_guidance = bool(recovery.get("hasRuntimeGuidance") and recovery.get("followUpActionCount"))

    if (
        recovery.get("hasLatestPlaybook")
        and worknet_key
        and not active_background
        and not has_runtime_guidance
        and (
            not recovery.get("preferFreshStartOverResume")
            or (preferred_key is not None and preferred_key == worknet_key)
        )
    ):
        actions.append(
            {
                "label": f"继续 {worknet_name}",
                "description": "继续沿用最近一次保存的 WorkNet playbook。",
                "command": run_worknet_command(worknet_key, execute=True, auto_advance=True),
            }
        )

    default_confirmation_label = str(recovery.get("defaultConfirmationLabel") or "").strip()
    if default_confirmation_label:
        actions.append(
            {
                "label": default_confirmation_label,
                "description": "确认并执行这个待确认动作。",
                "command": workstation_confirmation_command(default_confirmation_label, execute=False),
            }
        )

    source_follow_up_label = str(recovery.get("sourceFollowUpLabel") or "").strip()
    if source_follow_up_label and recovery.get("oldRunStopped"):
        restart_display = source_follow_up_label[3:] if source_follow_up_label.startswith("启动 ") else source_follow_up_label
        actions.append(
            {
                "label": f"重新启动 {restart_display}",
                "description": "按上一次保存的运行参数重新启动。",
                "command": workstation_follow_up_command(source_follow_up_label, execute=True),
            }
        )

    default_follow_up_label = str(recovery.get("defaultFollowUpLabel") or "").strip()
    follow_up_actions = recovery.get("followUpActions", []) if isinstance(recovery.get("followUpActions"), list) else []
    if default_follow_up_label and follow_up_actions:
        matched = next(
            (
                item
                for item in follow_up_actions
                if isinstance(item, dict) and str(item.get("label") or "").strip() == default_follow_up_label
            ),
            None,
        )
        if isinstance(matched, dict):
            command = review_action_command(
                worknet_key,
                default_follow_up_label,
                command=str(matched.get("command")) if isinstance(matched.get("command"), str) else None,
                safe_to_auto_run=bool(matched.get("safeToAutoRun")),
                requires_confirmation=bool(matched.get("requiresConfirmation")),
            )
            if command:
                actions.append(
                    {
                        "label": default_follow_up_label,
                        "description": "继续这条 runtime 建议动作。",
                        "command": command,
                    }
                )

    if active_background:
        if len(active_background) == 1:
            actions.append(
                {
                    "label": "暂停当前运行",
                    "description": "停止当前唯一的后台工作循环。",
                    "command": workstation_pause_command(execute=True),
                }
            )
        for item in active_background[:3]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if label:
                actions.append(
                    {
                        "label": f"查看 {label}",
                        "description": "先看这个后台任务的最近状态和日志。",
                        "command": workstation_background_command(label, tail_lines=80),
                    }
                )
                actions.append(
                    {
                        "label": f"停止 {label}",
                        "description": "停止这个后台任务。",
                        "command": workstation_background_command(label, stop=True, execute=False),
                    }
                )

    if (
        recovery.get("preferFreshStartOverResume")
        and preferred_profile is not None
        and str(preferred_profile.get("key") or "").strip()
        and str(preferred_profile.get("key")) != worknet_key
    ):
        preferred_key = str(preferred_profile["key"])
        preferred_name = str(preferred_profile.get("name") or preferred_key)
        actions.append(
            {
                "label": f"改按默认 {preferred_name} 开始",
                "description": "跳过旧 run，直接按你当前保存的默认 WorkNet 重新起步。",
                "command": run_worknet_command(preferred_key, execute=True, auto_advance=True),
            }
        )

    if recovery.get("hasLatestRun"):
        actions.append(
            {
                "label": "查看上次复盘",
                "description": "先看最近一次工作记录、收益样本和下一步动作。",
                "command": review_epoch_command(),
            }
        )

    return dedupe_action_entries(actions)


def recovery_decision_actions_from_run_response(
    response: dict[str, Any],
    *,
    primary_label: Optional[str] = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: Optional[str], description: str, command: Optional[str]) -> None:
        text = str(label or "").strip()
        resolved = str(command or "").strip()
        if not text or not resolved or text in seen:
            return
        actions.append(
            {
                "label": text,
                "description": description,
                "command": resolved,
            }
        )
        seen.add(text)

    queue = normalized_confirmation_queue(response.get("confirmationQueue", []))
    if queue:
        label = str(queue[0].get("label") or "").strip()
        if label:
            add(
                label,
                "确认并执行这个待确认动作。",
                workstation_confirmation_command(label, execute=False),
            )

    follow_up_actions = normalized_follow_up_actions(response.get("followUpActions", []))
    if follow_up_actions:
        default_follow_up = choose_default_follow_up_action(follow_up_actions) or follow_up_actions[0]
        label = str(default_follow_up.get("label") or "").strip()
        if label:
            command = review_action_command(
                str(response.get("selectedWorknetKey") or ""),
                label,
                command=str(default_follow_up.get("command")) if isinstance(default_follow_up.get("command"), str) else None,
                safe_to_auto_run=bool(default_follow_up.get("safeToAutoRun")),
                requires_confirmation=bool(default_follow_up.get("requiresConfirmation")),
            )
            add(
                label,
                "继续这条 runtime 建议动作。",
                command,
            )

    active = response.get("activeBackgroundProcesses", [])
    if isinstance(active, list) and active:
        if len(active) == 1 and isinstance(active[0], dict):
            add(
                "暂停当前运行",
                "停止当前唯一的后台工作循环。",
                workstation_pause_command(execute=True),
            )
        for item in active[:3]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if label:
                add(
                    f"查看 {label}",
                    "先看这个后台任务的最近状态和日志。",
                    workstation_background_command(label, tail_lines=80),
                )
                add(
                    f"停止 {label}",
                    "停止这个后台任务。",
                    workstation_background_command(label, stop=True, execute=False),
                )

    selected = response.get("selectedBackground")
    if isinstance(selected, dict):
        label = str(selected.get("label") or "").strip()
        if label:
            add(
                f"查看 {label}",
                "先看这个后台任务的最近状态和日志。",
                workstation_background_command(label, tail_lines=80),
            )
            add(
                f"停止 {label}",
                "停止这个后台任务。",
                workstation_background_command(label, stop=True, execute=False),
            )

    if response.get("playbookSource") == "preferred-worknet-over-stale-run":
        worknet_key = str(response.get("selectedWorknetKey") or "").strip()
        worknet_name = str(response.get("selectedWorknetName") or worknet_key).strip()
        if worknet_key:
            add(
                f"开始 {worknet_name}",
                "直接按当前默认 WorkNet 的 playbook 继续。",
                run_worknet_command(worknet_key, execute=True, auto_advance=True),
            )
    elif response.get("playbookSource") == "last-selected":
        worknet_key = str(response.get("selectedWorknetKey") or "").strip()
        worknet_name = str(response.get("selectedWorknetName") or worknet_key).strip()
        if worknet_key:
            add(
                f"继续 {worknet_name}",
                "继续沿用最近一次保存的 WorkNet playbook。",
                run_worknet_command(worknet_key, execute=True, auto_advance=True),
            )

    return dedupe_action_entries(actions)


def resolve_workstation_status_intent(query: Optional[str], explicit_intent: Optional[str] = None) -> str:
    if isinstance(explicit_intent, str) and explicit_intent.strip():
        return explicit_intent.strip().lower()
    text = str(query or "").strip().lower()
    if not text:
        return "status"
    if any(token in text for token in ("今天赚了多少", "赚了多少", "收益", "earn", "earning", "reward", "payout")):
        return "earnings"
    if any(token in text for token in ("为什么失败", "失败", "why failed", "why fail", "failure", "error")):
        return "failures"
    if any(token in text for token in ("不要动资金", "不要动资产", "don't move funds", "dont move funds", "non-financial", "risk")):
        return "safety"
    if any(token in text for token in ("待重审", "过时", "stale", "review queue", "upstream", "source drift")):
        return "review-queue"
    if any(token in text for token in ("研究", "百科", "资料", "文档", "guide", "research", "learn", "what is", "了解", "知识", "来源", "source", "仓库", "repo", "repository")):
        return "research"
    if any(token in text for token in ("暂停", "pause", "stop current", "stop running")):
        return "pause"
    if any(token in text for token in ("继续", "resume", "restart", "接着跑", "继续跑")):
        return "continue"
    if any(token in text for token in ("换一个", "换个", "换到", "切到", "切换", "switch", "only run", "只跑", "run mine", "run predict", "run gov", "run ardi", "run tmr", "run community")):
        return "switch-worknet"
    return "status"


def detect_worknet_from_text(query: Optional[str], explicit_identifier: Optional[str] = None) -> Optional[dict[str, Any]]:
    if isinstance(explicit_identifier, str) and explicit_identifier.strip():
        return resolve_worknet(explicit_identifier)
    text = str(query or "").strip().lower()
    if not text:
        return None
    normalized_query = normalize_worknet_token(text)
    for profile in KNOWN_WORKNETS:
        candidates = [
            profile.get("key"),
            profile.get("name"),
            profile.get("symbol"),
            *profile.get("aliases", []),
        ]
        for candidate in candidates:
            candidate_text = str(candidate or "").strip().lower()
            if not candidate_text:
                continue
            normalized_candidate = normalize_worknet_token(candidate_text)
            if candidate_text in text or (normalized_candidate and normalized_candidate in normalized_query):
                return profile
    return None


def knowledge_source_records_from_catalog(catalog: Any) -> dict[str, dict[str, Any]]:
    source_records: dict[str, dict[str, Any]] = {}
    sources = catalog.get("sources", {}) if isinstance(catalog, dict) and isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
    if not source_records:
        for item in OFFICIAL_WEB_SOURCES:
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
    return source_records


def source_record_match_candidates(source_record: Any) -> list[str]:
    if not isinstance(source_record, dict):
        return []
    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: Any) -> None:
        text = str(candidate or "").strip()
        if not text:
            return
        normalized = text.lower()
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append(text)

    add(source_record.get("key"))
    add(source_record.get("name"))
    add(humanize_knowledge_source_label(source_record.get("key")))
    add(humanize_knowledge_source_label(source_record.get("name")))
    url = str(source_record.get("url") or "").strip()
    add(url)
    if url:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.strip()
        path = parsed.path.rstrip("/")
        add(host)
        if host and path:
            add(f"{host}{path}")
        add(path)
        segments = [segment for segment in path.split("/") if segment]
        if segments:
            add(segments[-1])
        if len(segments) >= 2:
            add("/".join(segments[-2:]))
    return candidates


def detect_source_from_text(
    query: Optional[str],
    explicit_identifier: Optional[str] = None,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    source_text = explicit_identifier if isinstance(explicit_identifier, str) and explicit_identifier.strip() else query
    raw_text = str(source_text or "").strip()
    if not raw_text:
        return None
    text = raw_text.lower()
    normalized_query = normalize_knowledge_source_token(raw_text)
    if not normalized_query:
        return None
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    best_match: Optional[dict[str, Any]] = None
    best_score = 0
    explicit = isinstance(explicit_identifier, str) and explicit_identifier.strip()

    for source_record in knowledge_source_records_from_catalog(catalog).values():
        score = 0
        for candidate in source_record_match_candidates(source_record):
            candidate_text = str(candidate or "").strip().lower()
            normalized_candidate = normalize_knowledge_source_token(candidate)
            if not candidate_text or not normalized_candidate:
                continue
            if candidate_text == text or normalized_candidate == normalized_query:
                score = max(score, 1000 + len(normalized_candidate))
                continue
            if explicit and len(normalized_query) >= 6 and normalized_query in normalized_candidate:
                score = max(score, 700 + len(normalized_candidate))
            if len(candidate_text) >= 6 and candidate_text in text:
                score = max(score, 600 + len(normalized_candidate))
            if len(normalized_candidate) >= 6 and normalized_candidate in normalized_query:
                score = max(score, 500 + len(normalized_candidate))
        if score > best_score:
            best_score = score
            best_match = source_record
    return best_match


def priority_label(priority: Optional[str]) -> str:
    mapping = {
        "critical": "最高优先级",
        "high": "高优先级",
        "medium": "中优先级",
        "low": "低优先级",
    }
    text = str(priority or "").strip().lower()
    return mapping.get(text, text or "未知优先级")


def knowledge_review_queue_note_for_target(
    queue: Any,
    target_key: Optional[str],
    *,
    target_label: Optional[str] = None,
) -> Optional[str]:
    if not isinstance(queue, dict):
        return None
    key = str(target_key or "").strip()
    if not key:
        return None
    matches = [
        item
        for item in queue.get("entries", [])
        if isinstance(item, dict) and str(item.get("key") or "").strip() == key
    ]
    if not matches:
        return None
    rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    highest = "low"
    for item in matches:
        priority = str(item.get("priority") or "low")
        if rank.get(priority, 0) > rank.get(highest, 0):
            highest = priority
    label = str(target_label or key)
    return f"{label} 相关知识当前有 {len(matches)} 条待重审项，{priority_label(highest)}。"


def find_executed_step(executed_steps: list[dict[str, Any]], label: str) -> Optional[dict[str, Any]]:
    for step in executed_steps:
        if isinstance(step, dict) and step.get("label") == label:
            return step
    return None


def step_command_string(step: Optional[dict[str, Any]]) -> Optional[str]:
    if not isinstance(step, dict):
        return None
    argv = step.get("argv")
    if not isinstance(argv, list) or not argv:
        return None
    return render_argv([str(item) for item in argv])


def step_guidance_action(
    label: str,
    step: Optional[dict[str, Any]],
    *,
    preferred: bool = False,
    safe_to_auto_run: bool = True,
) -> Optional[dict[str, Any]]:
    if not isinstance(step, dict):
        return None
    argv = step.get("argv")
    if not isinstance(argv, list) or not argv:
        return None
    return guidance_action(
        label,
        render_argv([str(item) for item in argv]),
        argv=[str(item) for item in argv],
        cwd=str(step.get("cwd")) if step.get("cwd") else None,
        safe_to_auto_run=safe_to_auto_run,
        preferred=preferred,
    )


def python_template_action(
    label: str,
    *,
    cwd: str,
    python_bin: str,
    script_rel: str,
    args: list[str],
    requires_confirmation: bool = False,
    safe_to_auto_run: bool = False,
    preferred: bool = False,
) -> dict[str, Any]:
    argv = [python_bin, script_rel, *args]
    return guidance_action(
        label,
        render_argv(argv),
        argv=argv,
        cwd=cwd,
        requires_confirmation=requires_confirmation,
        safe_to_auto_run=safe_to_auto_run,
        preferred=preferred,
        parameter_schema=extract_command_parameter_schema(argv),
    )


def predict_persona_actions(state_root: str) -> list[dict[str, Any]]:
    return [
        guidance_action(
            f"设为 {persona} 风格",
            f"predict-agent set-persona {persona}",
            argv=["predict-agent", "set-persona", persona],
            cwd=state_root,
            safe_to_auto_run=False,
        )
        for persona in PREDICT_PERSONAS
    ]


def predict_loop_actions(state_root: str) -> list[dict[str, Any]]:
    return [
        guidance_action(
            "启动 Predict 循环（逐轮汇报）",
            "predict-agent loop --interval 120 --agent-id predict-worker --notify",
            argv=["predict-agent", "loop", "--interval", "120", "--agent-id", "predict-worker", "--notify"],
            cwd=state_root,
            safe_to_auto_run=True,
            long_running=True,
        ),
        guidance_action(
            "启动 Predict 静默循环",
            "predict-agent loop --interval 120 --agent-id predict-worker",
            argv=["predict-agent", "loop", "--interval", "120", "--agent-id", "predict-worker"],
            cwd=state_root,
            safe_to_auto_run=True,
            preferred=True,
            long_running=True,
        ),
    ]


def predict_stake_support_actions(state_root: str) -> list[dict[str, Any]]:
    return [
        guidance_action("官方 AWP 质押 UI", "https://awp.pro/staking"),
        guidance_action("走 KYA 委托路径", "https://kya.link/"),
        guidance_action(
            "重跑 Predict stake 检查",
            "predict-agent stake",
            argv=["predict-agent", "stake"],
            cwd=state_root,
            safe_to_auto_run=True,
        ),
    ]


def placeholder_spec(token: str, *, param_name: Optional[str]) -> Optional[dict[str, Any]]:
    match = PLACEHOLDER_TOKEN_RE.match(token)
    if not match:
        return None
    raw = match.group(1).strip()
    if not raw:
        return None
    choices = [part.strip() for part in raw.split("|") if part.strip()]
    name = (param_name or raw).strip().lower().replace(" ", "_").replace("-", "_")
    spec = {
        "name": name,
        "placeholder": token,
        "prompt": raw,
    }
    if len(choices) > 1:
        spec["choices"] = choices
    return spec


def extract_command_parameter_schema(argv: list[str]) -> list[dict[str, Any]]:
    schema: list[dict[str, Any]] = []
    last_flag: Optional[str] = None
    for item in argv:
        text = str(item)
        if text.startswith("--"):
            last_flag = text[2:].replace("-", "_")
            continue
        spec = placeholder_spec(text, param_name=last_flag)
        if spec is not None:
            schema.append(spec)
            last_flag = None
        elif text and not text.startswith("-"):
            last_flag = None
    return schema


def parse_input_assignments(values: Optional[list[str]]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values or []:
        if "=" not in str(item):
            continue
        key, value = str(item).split("=", 1)
        key = key.strip().lower().replace("-", "_")
        if key:
            parsed[key] = value
    return parsed


def build_confirmation_execute_command(label: str, parameter_schema: list[dict[str, Any]]) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--confirm-label",
        label,
    ]
    for spec in parameter_schema:
        name = str(spec.get("name") or "value")
        prompt = str(spec.get("prompt") or "value")
        argv.extend(["--input", f"{name}={prompt}"])
    argv.append("--execute")
    return render_argv(argv)


def resolve_parameterized_argv(
    argv: list[str],
    parameter_schema: list[dict[str, Any]],
    provided_inputs: dict[str, str],
) -> tuple[Optional[list[str]], list[str]]:
    required_names = [str(spec.get("name")) for spec in parameter_schema if spec.get("name")]
    missing = [name for name in required_names if name not in provided_inputs]
    if missing:
        return None, [f"missing input: {name}" for name in missing]
    placeholder_to_value: dict[str, str] = {}
    errors: list[str] = []
    for spec in parameter_schema:
        name = str(spec.get("name") or "")
        placeholder = str(spec.get("placeholder") or "")
        if not name or not placeholder:
            continue
        value = provided_inputs.get(name, "")
        choices = spec.get("choices")
        if isinstance(choices, list) and choices and value not in [str(choice) for choice in choices]:
            errors.append(f"invalid value for {name}: {value}")
            continue
        placeholder_to_value[placeholder] = value
    if errors:
        return None, errors
    resolved: list[str] = []
    for item in argv:
        text = str(item)
        resolved.append(placeholder_to_value.get(text, text))
    return resolved, []


def predict_runtime_guidance(executed_steps: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    state_root = str(state_context()["root"])
    persona_step = next(
        (
            step for step in executed_steps
            if isinstance(step, dict) and isinstance(step.get("label"), str) and str(step.get("label")).startswith("设为 ")
        ),
        None,
    )
    status_step = find_executed_step(executed_steps, "predict status")
    stake_step = find_executed_step(executed_steps, "predict stake eligibility")
    context_step = find_executed_step(executed_steps, "查看 Predict context") or find_executed_step(executed_steps, "predict context")
    status_payload = step_result_payload(status_step) if status_step else None
    stake_payload = step_result_payload(stake_step) if stake_step else None
    status_guidance = runtime_guidance_from_step(status_step) if status_step else None
    stake_error_code = None
    stake_suggestion = None
    if isinstance(stake_payload, dict):
        error = stake_payload.get("error")
        if isinstance(error, dict):
            stake_error_code = str(error.get("code") or "")
            stake_suggestion = error.get("suggestion")

    if isinstance(persona_step, dict):
        persona_payload = step_result_payload(persona_step)
        persona_data = persona_payload.get("data") if isinstance(persona_payload, dict) else None
        persona_name = None
        if isinstance(persona_data, dict) and isinstance(persona_data.get("persona"), str):
            persona_name = str(persona_data.get("persona"))
        if not persona_name:
            argv = persona_step.get("argv")
            if isinstance(argv, list) and argv:
                persona_name = str(argv[-1])
        persona_ok = bool(persona_payload.get("ok")) if isinstance(persona_payload, dict) else False
        persona_error_code = None
        if isinstance(persona_payload, dict):
            error = persona_payload.get("error")
            if isinstance(error, dict):
                persona_error_code = str(error.get("code") or "")
        if persona_ok or persona_error_code == "PERSONA_COOLDOWN":
            follow_up = predict_loop_actions(state_root)
            message = f"Predict persona 已设为 {persona_name or 'custom'}。下一步直接启动循环，不再手动逐笔提交。"
            if persona_error_code == "PERSONA_COOLDOWN":
                message = "Predict persona 当前处于 cooldown，继续用现有 persona 启动循环即可。"
            guidance = {
                "message": message,
                "userActions": [item["label"] for item in follow_up],
                "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
                "nextCommand": ["predict-agent", "loop", "--interval", "120", "--agent-id", "predict-worker"],
                "nextAction": "start_predict_loop",
                "state": None,
            }
            return guidance, follow_up

    persona = None
    if isinstance(status_payload, dict):
        data = status_payload.get("data")
        if isinstance(data, dict):
            persona = data.get("persona")
    persona_value = str(persona or "").strip().lower()

    if isinstance(status_payload, dict) and persona_value in {"", "none", "null"}:
        follow_up = predict_persona_actions(state_root)
        guidance = {
            "message": "Predict 已满足基础运行条件，但还没有 persona。先选一个分析风格，再启动循环。",
            "userActions": [item["label"] for item in follow_up],
            "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
            "nextCommand": ["predict-agent", "set-persona", "<PERSONA>"],
            "nextAction": "select_predict_persona",
            "state": None,
        }
        return guidance, follow_up

    if isinstance(status_payload, dict) and persona_value not in {"", "none", "null"}:
        follow_up = predict_loop_actions(state_root)
        if stake_error_code in {"NOT_STAKED", "STAKE_FETCH_FAILED"}:
            follow_up.extend(predict_stake_support_actions(state_root))
        guidance = {
            "message": f"Predict persona 已设为 {persona_value}。下一步直接启动循环，不再手动逐笔提交。",
            "userActions": [item["label"] for item in follow_up],
            "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
            "nextCommand": ["predict-agent", "loop", "--interval", "120", "--agent-id", "predict-worker"],
            "nextAction": "start_predict_loop",
            "state": None,
        }
        if stake_error_code == "NOT_STAKED":
            guidance["detail"] = stake_suggestion or runtime_message(stake_payload)
        elif stake_error_code == "STAKE_FETCH_FAILED":
            guidance["detail"] = stake_suggestion or runtime_message(stake_payload)
        return guidance, follow_up

    if isinstance(stake_payload, dict):
        if stake_error_code == "NOT_STAKED":
            follow_up = [
                guidance_action(
                    "查看 Predict context",
                    "predict-agent context",
                    argv=["predict-agent", "context"],
                    cwd=state_root,
                    safe_to_auto_run=True,
                    preferred=True,
                ),
                *predict_stake_support_actions(state_root),
            ]
            guidance = {
                "message": "Predict runtime 已就绪，但当前还没满足 1000 AWP 或 KYA 委托资格。",
                "userActions": [item["label"] for item in follow_up],
                "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
                "nextCommand": ["predict-agent", "stake"],
                "nextAction": "stake_required",
                "state": None,
                "detail": stake_suggestion or runtime_message(stake_payload),
            }
            return guidance, follow_up
        if stake_error_code == "STAKE_FETCH_FAILED":
            follow_up = [
                guidance_action(
                    "查看 Predict context",
                    "predict-agent context",
                    argv=["predict-agent", "context"],
                    cwd=state_root,
                    safe_to_auto_run=True,
                    preferred=True,
                ),
                guidance_action(
                    "重跑 Predict stake 检查",
                    "predict-agent stake",
                    argv=["predict-agent", "stake"],
                    cwd=state_root,
                    safe_to_auto_run=True,
                ),
            ]
            guidance = {
                "message": "Predict runtime 已就绪，但 stake 资格检查这次没有拿到稳定结果。",
                "userActions": [item["label"] for item in follow_up],
                "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
                "nextCommand": ["predict-agent", "stake"],
                "nextAction": "retry_stake_check",
                "state": None,
                "detail": stake_suggestion or runtime_message(stake_payload),
            }
            return guidance, follow_up

    if isinstance(status_guidance, dict):
        follow_up = [
            guidance_action(
                "查看 Predict context",
                "predict-agent context",
                argv=["predict-agent", "context"],
                cwd=state_root,
                safe_to_auto_run=True,
                preferred=True,
            ),
        ]
        guidance = dict(status_guidance)
        guidance["message"] = "Predict runtime 已就绪，可以先拉 market context 再决定是否继续。"
        guidance["userActions"] = [item["label"] for item in follow_up]
        guidance["actionMap"] = {item["label"]: item["command"] for item in follow_up if item.get("command")}
        guidance["nextCommand"] = ["predict-agent", "context"]
        guidance["nextAction"] = "fetch_context"
        return guidance, follow_up

    context_payload = step_result_payload(context_step) if context_step else None
    context_guidance = runtime_guidance_from_step(context_step) if context_step else None
    if isinstance(context_payload, dict) and isinstance(context_guidance, dict):
        next_command = context_guidance.get("nextCommand")
        recommendation = context_payload.get("data", {}).get("recommendation") if isinstance(context_payload.get("data"), dict) else None
        recommendation_action = recommendation.get("action") if isinstance(recommendation, dict) else None
        market_id = recommendation.get("market_id") if isinstance(recommendation, dict) else None
        if recommendation_action == "submit" and isinstance(next_command, list) and next_command:
            submit_command = render_argv(next_command)
            message = "Predict context 已就绪，提交前先确认方向、tickets 和 reasoning。"
            if market_id:
                message = f"Predict context 已就绪，当前推荐市场是 {market_id}；提交前先确认方向、tickets 和 reasoning。"
            follow_up = [
                guidance_action(
                    "准备 Predict 提交",
                    submit_command,
                    argv=[str(item) for item in next_command],
                    cwd=state_root,
                    requires_confirmation=True,
                    parameter_schema=extract_command_parameter_schema([str(item) for item in next_command]),
                ),
                guidance_action(
                    "重跑 Predict context",
                    "predict-agent context",
                    argv=["predict-agent", "context"],
                    cwd=state_root,
                    safe_to_auto_run=False,
                ),
            ]
            guidance = {
                "message": message,
                "userActions": [item["label"] for item in follow_up],
                "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
                "nextCommand": next_command,
                "nextAction": "confirm_predict_submission",
                "state": None,
            }
            return guidance, follow_up
        follow_up = [
            guidance_action(
                "重跑 Predict context",
                "predict-agent context",
                argv=["predict-agent", "context"],
                cwd=state_root,
                safe_to_auto_run=True,
                preferred=True,
            )
        ]
        guidance = {
            "message": runtime_message(context_payload) or "当前没有可提交的 Predict 市场，先等待下一轮。",
            "userActions": [item["label"] for item in follow_up],
            "actionMap": {item["label"]: item["command"] for item in follow_up if item.get("command")},
            "nextCommand": ["predict-agent", "context"],
            "nextAction": "wait_for_predict_market",
            "state": None,
        }
        return guidance, follow_up

    return None, []


def gov_signed_template_actions(helper_step: Optional[dict[str, Any]], helper_payload: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(helper_step, dict):
        return []
    argv = helper_step.get("argv")
    cwd = helper_step.get("cwd")
    if not isinstance(argv, list) or not argv or not cwd:
        return []
    python_bin = str(argv[0])
    available = helper_payload.get("available") if isinstance(helper_payload, dict) else None
    ops = {
        str(item.get("op"))
        for item in available or []
        if isinstance(item, dict) and item.get("op")
    }
    actions: list[dict[str, Any]] = []
    if "submit-order" in ops:
        actions.append(
            python_template_action(
                "准备 Gov 限价单",
                cwd=str(cwd),
                python_bin=python_bin,
                script_rel="scripts/trade/submit-order.py",
                args=[
                    "--market", "<market_id>",
                    "--worknet", "<worknet_id>",
                    "--side", "<buy|sell>",
                    "--kind", "limit",
                    "--price", "<price>",
                    "--quantity", "<quantity>",
                    "--yes",
                ],
                requires_confirmation=True,
            )
        )
    if "submit-vote" in ops:
        actions.append(
            python_template_action(
                "准备 Gov 投票",
                cwd=str(cwd),
                python_bin=python_bin,
                script_rel="scripts/vote/submit-vote.py",
                args=[
                    "--market", "<market_id>",
                    "--vote", "<vote_weights_csv>",
                    "--prediction", "<prediction_weights_csv>",
                    "--vote-revision", "<vote_revision>",
                    "--yes",
                ],
                requires_confirmation=True,
            )
        )
    if "split-position" in ops:
        actions.append(
            python_template_action(
                "准备 Gov split",
                cwd=str(cwd),
                python_bin=python_bin,
                script_rel="scripts/positions/split.py",
                args=[
                    "--market", "<market_id>",
                    "--quantity", "<quantity>",
                    "--yes",
                ],
                requires_confirmation=True,
            )
        )
    if "merge-position" in ops:
        actions.append(
            python_template_action(
                "准备 Gov merge",
                cwd=str(cwd),
                python_bin=python_bin,
                script_rel="scripts/positions/merge.py",
                args=[
                    "--market", "<market_id>",
                    "--quantity", "<quantity>",
                    "--yes",
                ],
                requires_confirmation=True,
            )
        )
    return actions


def gov_runtime_guidance(executed_steps: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    helper_step = find_executed_step(executed_steps, "gov phase-aware helper")
    state_step = find_executed_step(executed_steps, "gov private state")
    helper_payload = step_result_payload(helper_step) if helper_step else None
    state_payload = step_result_payload(state_step) if state_step else None
    phase = None
    if isinstance(helper_payload, dict) and isinstance(helper_payload.get("phase"), str):
        phase = str(helper_payload.get("phase"))
    available = helper_payload.get("available") if isinstance(helper_payload, dict) else None
    blocked = helper_payload.get("blocked") if isinstance(helper_payload, dict) else None

    actions: list[dict[str, Any]] = []
    helper_action = step_guidance_action("查看 Gov 可做动作", helper_step, preferred=True)
    if helper_action:
        actions.append(helper_action)
    markets_step = find_executed_step(executed_steps, "gov public markets")
    markets_action = step_guidance_action("查看 Gov markets", markets_step)
    if markets_action:
        actions.append(markets_action)
    actions.append(skill_script_action("阅读 staking 说明", "query-knowledge.py", "--topic", "staking"))

    if isinstance(state_payload, dict) and str(state_payload.get("error") or "") == "STATE_PRINCIPAL_NOT_IN_EPOCH":
        message = "Gov 当前有公开市场可看，但你的 principal 这期没有 AWP Power，所以签名交易和投票还不能做。"
        detail = str(state_payload.get("detail") or "")
        if phase:
            message = f"Gov 当前 phase 是 {phase}，但你的 principal 这期没有 AWP Power，所以签名交易和投票还不能做。"
        guidance = {
            "message": message,
            "userActions": [item["label"] for item in actions],
            "actionMap": {item["label"]: item["command"] for item in actions if item.get("command")},
            "nextCommand": None,
            "nextAction": "acquire_awp_power_or_observe_gov",
            "state": phase,
            "detail": detail,
        }
        return guidance, actions

    if isinstance(helper_payload, dict):
        actions.extend(gov_signed_template_actions(helper_step, helper_payload))
        action_map = {item["label"]: item["command"] for item in actions if item.get("command")}
        message = f"Gov 当前 phase 是 {phase}。" if phase else "Gov runtime 已就绪。"
        if isinstance(available, list):
            available_ops = [str(item.get("op")) for item in available[:3] if isinstance(item, dict) and item.get("op")]
            if available_ops:
                message += " 当前最直接可做的是 " + " / ".join(available_ops) + "。"
        if isinstance(blocked, list):
            blocked_ops = [str(item.get("op")) for item in blocked[:2] if isinstance(item, dict) and item.get("op")]
            if blocked_ops:
                message += " 被 phase 挡住的有 " + " / ".join(blocked_ops) + "。"
        guidance = {
            "message": message,
            "userActions": [item["label"] for item in actions],
            "actionMap": action_map,
            "nextCommand": None,
            "nextAction": "review_gov_phase",
            "state": phase,
        }
        return guidance, actions

    return None, []


def ardi_runtime_guidance(executed_steps: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    gas_step = find_executed_step(executed_steps, "ardi gas check")
    stake_step = find_executed_step(executed_steps, "ardi stake guidance")
    preflight_step = find_executed_step(executed_steps, "ardi preflight")
    gas_payload = step_result_payload(gas_step) if gas_step else None
    stake_payload = step_result_payload(stake_step) if stake_step else None

    actions: list[dict[str, Any]] = []
    gas_suggestion = None
    if isinstance(gas_payload, dict):
        data = gas_payload.get("data")
        if isinstance(data, dict):
            gas_suggestion = data.get("suggestion")
    if gas_suggestion:
        actions.append(
            guidance_action(
                "补 Base Gas",
                str(gas_suggestion),
                requires_confirmation=True,
            )
        )
    actions.append(
        guidance_action(
            "重跑 Ardi preflight",
            "ardi-agent preflight",
            argv=["ardi-agent", "preflight"],
            cwd=str(state_context()["root"]),
            safe_to_auto_run=True,
            preferred=True,
        )
    )

    stake_suggestion = None
    if isinstance(stake_payload, dict):
        data = stake_payload.get("data")
        if isinstance(data, dict):
            stake_suggestion = data.get("suggestion")
    if stake_suggestion:
        actions.append(guidance_action("走 KYA 委托路径", "https://kya.link/"))
        actions.append(
            guidance_action(
                "自动买并质押",
                "ardi-agent buy-and-stake",
                argv=["ardi-agent", "buy-and-stake"],
                cwd=str(state_context()["root"]),
                requires_confirmation=True,
            )
        )
        actions.append(
            guidance_action(
                "重跑 Ardi stake 检查",
                "ardi-agent stake",
                argv=["ardi-agent", "stake"],
                cwd=str(state_context()["root"]),
                safe_to_auto_run=True,
            )
        )

    if gas_suggestion or stake_suggestion:
        message = "Ardi runtime 已就绪，但现在还不能进 commit/reveal 循环。"
        if gas_suggestion and stake_suggestion:
            message = "Ardi runtime 已就绪，但现在先要补 Base gas，并满足 stake 资格，之后才能进 commit/reveal 循环。"
        elif gas_suggestion:
            message = "Ardi runtime 已就绪，但现在先要补 Base gas，之后再继续 preflight。"
        elif stake_suggestion:
            message = "Ardi runtime 已就绪，但现在还缺 stake 资格。"
        guidance = {
            "message": message,
            "userActions": [item["label"] for item in actions],
            "actionMap": {item["label"]: item["command"] for item in actions if item.get("command")},
            "nextCommand": ["ardi-agent", "preflight"] if preflight_step else ["ardi-agent", "stake"],
            "nextAction": "fund_gas_and_or_satisfy_stake",
            "state": None,
            "detail": "; ".join(item for item in [str(gas_suggestion or ""), str(stake_suggestion or "")] if item),
        }
        return guidance, actions

    status_step = find_executed_step(executed_steps, "ardi status")
    status_guidance = runtime_guidance_from_step(status_step) if status_step else None
    if isinstance(status_guidance, dict):
        actions = [
            guidance_action(
                "重跑 Ardi preflight",
                "ardi-agent preflight",
                argv=["ardi-agent", "preflight"],
                cwd=str(state_context()["root"]),
                safe_to_auto_run=True,
                preferred=True,
            )
        ]
        guidance = dict(status_guidance)
        guidance["message"] = "Ardi runtime 已就绪，可以继续 preflight。"
        guidance["userActions"] = [item["label"] for item in actions]
        guidance["actionMap"] = {item["label"]: item["command"] for item in actions if item.get("command")}
        guidance["nextCommand"] = ["ardi-agent", "preflight"]
        guidance["nextAction"] = "review"
        return guidance, actions

    return None, []


def synthesize_run_guidance(playbook: dict[str, Any], executed_steps: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
    worknet_key = str(playbook.get("worknetKey") or "")
    if worknet_key == "predict":
        return predict_runtime_guidance(executed_steps)
    if worknet_key == "gov":
        return gov_runtime_guidance(executed_steps)
    if worknet_key == "ardi":
        return ardi_runtime_guidance(executed_steps)
    if worknet_key == "mine":
        primary = find_executed_step(executed_steps, "start mine worker")
        if primary:
            guidance = runtime_guidance_from_step(primary)
            if isinstance(guidance, dict):
                actions = [
                    guidance_action(
                        label,
                        guidance.get("actionMap", {}).get(label),
                        argv=shlex.split(str(guidance.get("actionMap", {}).get(label))) if isinstance(guidance.get("actionMap", {}).get(label), str) else None,
                        cwd=str(primary.get("cwd")) if primary.get("cwd") else None,
                        safe_to_auto_run=True,
                        preferred=index == 0,
                    )
                    for index, label in enumerate(guidance.get("userActions", []))
                ]
                return guidance, [item for item in actions if item.get("label")]
    for step in reversed(executed_steps):
        guidance = runtime_guidance_from_step(step)
        if isinstance(guidance, dict):
            actions = [
                guidance_action(
                    label,
                    guidance.get("actionMap", {}).get(label),
                    argv=shlex.split(str(guidance.get("actionMap", {}).get(label))) if isinstance(guidance.get("actionMap", {}).get(label), str) else None,
                    cwd=str(step.get("cwd")) if step.get("cwd") else None,
                    safe_to_auto_run=True,
                    preferred=index == 0,
                )
                for index, label in enumerate(guidance.get("userActions", []))
            ]
            return guidance, [item for item in actions if item.get("label")]
    return None, []


def command_probe_available(command: dict[str, Any]) -> bool:
    argv = command.get("argv")
    if not isinstance(argv, list) or not argv:
        return False
    cwd = command.get("cwd")
    head = str(argv[0])
    if os.path.isabs(head):
        return Path(head).exists()
    if head == "python3":
        if len(argv) < 2:
            return command_exists("python3")
        script = Path(str(argv[1]))
        if script.is_absolute():
            return script.exists()
        if cwd:
            return (Path(str(cwd)) / script).exists()
        return script.exists()
    return command_exists(head)


def run_inspection_probe(command: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    argv = [str(item) for item in command.get("argv", [])]
    cwd = command.get("cwd")
    result = run_command(argv, cwd=str(cwd) if cwd else None, timeout=timeout)
    combined = "\n".join(part for part in [result.get("stdout", ""), result.get("stderr", "")] if part)
    payload = parse_json_loose(result.get("stdout", ""))
    return {
        "label": command.get("label"),
        "argv": argv,
        "cwd": cwd,
        "ok": result.get("ok", False),
        "code": result.get("code"),
        "result": payload if isinstance(payload, (dict, list)) else None,
        "text": trim_output(combined, limit=1200),
    }


def probe_result_worknet_key(skill_key: str, probe: dict[str, Any]) -> str:
    normalized_skill = str(skill_key or "").strip().lower()
    if normalized_skill in {item["key"] for item in KNOWN_WORKNETS}:
        return normalized_skill
    payload = probe.get("result")
    labels = payload.get("user_actions") if isinstance(payload, dict) else None
    action_map = payload.get("_internal", {}).get("action_map") if isinstance(payload, dict) and isinstance(payload.get("_internal"), dict) else None
    message = payload.get("user_message") if isinstance(payload, dict) else None
    return runtime_guidance_worknet_key(
        None,
        labels=labels,
        action_map=action_map,
        message=message,
    )


def runtime_probe_effective_status(probe: dict[str, Any]) -> str:
    payload = probe.get("result")
    if isinstance(payload, dict):
        if payload.get("ok") is False:
            return "failed"
        if str(payload.get("status") or "").strip().lower() == "error":
            return "failed"
        if runtime_payload_has_blocker(payload):
            return "failed"
    return "ok" if probe.get("ok") else "failed"


def contains_cjk_text(text: Any) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))


def should_replace_display_text(current: Any, candidate: Any) -> bool:
    current_text = str(current or "").strip()
    candidate_text = str(candidate or "").strip()
    if not candidate_text:
        return False
    if not current_text:
        return True
    if current_text == candidate_text:
        return True
    return contains_cjk_text(candidate_text) and not contains_cjk_text(current_text)


def humanize_runtime_probe_plain_text_summary(
    worknet_key: str,
    label: str,
    text: Any,
) -> Optional[str]:
    raw = str(text or "").strip()
    if not raw:
        return None
    lowered = raw.lower()
    if worknet_key == "kya":
        if label == "kya sign claim help":
            return "KYA 签名认领脚本已就绪，可继续生成带交接链接的认领流程。"
        if label == "kya relay recipient help":
            return "KYA 收款地址 relay 脚本已就绪，可继续设置收款地址并发起委托质押请求。"
        if label == "kya kyc help":
            return "KYA 验证脚本已就绪，可继续身份验证流程。"
    if worknet_key == "gov" and "name or service not known" in lowered:
        return "Gov 当前连不上上游服务，先检查网络或域名解析。"
    if worknet_key == "gov" and label == "gov private state":
        if "state_principal_not_in_epoch" in lowered or "no awp power" in lowered:
            return "这期你的 principal 还没有 AWP Power，所以 Gov 的签名读写动作还不能做。"
        if "traceback" in lowered or "state.py" in lowered:
            return "Gov 私有状态脚本当前没拿到稳定结果，先检查网络和这期的 AWP Power。"
    if worknet_key == "ardi" and "all base rpcs failed" in lowered:
        return "Ardi 当前连不上 Base RPC，先检查网络或可用 RPC。"
    if lowered.startswith("wallet ready:"):
        address = raw.split(":", 1)[1].strip() if ":" in raw else ""
        worknet_name = runtime_guidance_worknet_name(worknet_key)
        if address:
            return f"{worknet_name} 钱包已就绪：{address}。"
        return f"{worknet_name} 钱包已就绪。"
    return None


def humanize_runtime_probe_summary_display(
    worknet_key: str,
    label: str,
    *,
    status: str,
    payload: Any,
    text: Any,
) -> Optional[str]:
    step_like = {
        "label": label,
        "status": status,
    }
    if isinstance(payload, dict):
        if status == "failed":
            failure = humanize_review_failure(worknet_key, step_like, payload)
            if failure:
                return failure
        review = humanize_review_step(worknet_key, step_like, payload)
        if review:
            return review
        message_display = humanize_runtime_guidance_message_display(
            worknet_key or None,
            payload.get("user_message") or payload.get("message"),
            state=payload.get("state"),
        )
        if message_display:
            return message_display
        error_summary = runtime_payload_error_summary(payload)
        if error_summary:
            return humanize_runtime_probe_plain_text_summary(worknet_key, label, error_summary) or error_summary
    return humanize_runtime_probe_plain_text_summary(worknet_key, label, text)


def annotate_probe_result_display(
    probe: dict[str, Any],
    *,
    skill_key: str,
) -> dict[str, Any]:
    normalized = dict(probe)
    payload = normalized.get("result")
    worknet_key = probe_result_worknet_key(skill_key, normalized)
    effective_status = runtime_probe_effective_status(normalized)
    step_like = {
        "label": normalized.get("label"),
        "status": effective_status,
        "result": {
            "code": normalized.get("code"),
            "stdout": payload,
            "stderr": None if isinstance(payload, (dict, list)) else normalized.get("text"),
        },
    }
    result_display = build_executed_step_result_display(worknet_key, step_like)
    text_display = compact_preview_text(normalized.get("text"), max_chars=220, max_sentences=2)
    if text_display:
        normalized["textDisplay"] = text_display
    if isinstance(result_display, dict):
        normalized["resultDisplay"] = result_display
        if result_display.get("summary"):
            normalized["resultSummary"] = result_display.get("summary")
        if result_display.get("stdoutDisplay") is not None:
            normalized["stdoutDisplay"] = result_display.get("stdoutDisplay")
        if result_display.get("stderrDisplay"):
            normalized["stderrDisplay"] = result_display.get("stderrDisplay")
        if result_display.get("previewDisplay"):
            normalized["previewDisplay"] = result_display.get("previewDisplay")
    if isinstance(payload, dict):
        state = str(payload.get("state") or "").strip()
        if state:
            normalized["stateDisplay"] = humanize_runtime_payload_state(state)
        message_display = humanize_runtime_guidance_message_display(
            worknet_key or None,
            payload.get("user_message") or payload.get("message"),
            state=payload.get("state"),
        )
        if message_display:
            normalized["messageDisplay"] = message_display
        guidance = extract_runtime_guidance_from_payload(payload, worknet_key=worknet_key or None)
        if isinstance(guidance, dict):
            normalized["runtimeGuidanceDisplay"] = guidance
            user_actions_display = guidance.get("userActionsDisplay")
            if isinstance(user_actions_display, list) and user_actions_display:
                normalized["userActionsDisplay"] = user_actions_display
            next_command_display = guidance.get("nextCommandDisplay")
            if isinstance(next_command_display, str) and next_command_display.strip():
                normalized["nextCommandDisplay"] = next_command_display.strip()
            preview_display = guidance.get("previewDisplay")
            if isinstance(preview_display, str) and preview_display.strip():
                normalized["previewDisplay"] = preview_display.strip()
    humanized_summary = humanize_runtime_probe_summary_display(
        worknet_key,
        str(normalized.get("label") or "").strip(),
        status=effective_status,
        payload=payload,
        text=normalized.get("text"),
    )
    if isinstance(humanized_summary, str) and humanized_summary.strip():
        normalized["resultSummary"] = humanized_summary.strip()
        if should_replace_display_text(normalized.get("messageDisplay"), humanized_summary):
            normalized["messageDisplay"] = humanized_summary.strip()
        if should_replace_display_text(normalized.get("previewDisplay"), humanized_summary):
            normalized["previewDisplay"] = humanized_summary.strip()
        if should_replace_display_text(normalized.get("textDisplay"), humanized_summary):
            normalized["textDisplay"] = humanized_summary.strip()
        if isinstance(normalized.get("resultDisplay"), dict):
            result_display = dict(normalized["resultDisplay"])
            current_summary = str(result_display.get("summary") or "").strip()
            if current_summary and current_summary != humanized_summary and not str(result_display.get("summaryRaw") or "").strip():
                result_display["summaryRaw"] = current_summary
            result_display["summary"] = humanized_summary.strip()
            result_display["summaryDisplay"] = humanized_summary.strip()
            current_preview = str(result_display.get("preview") or result_display.get("previewDisplay") or "").strip()
            if current_preview and current_preview != humanized_summary and not str(result_display.get("previewRaw") or "").strip():
                result_display["previewRaw"] = current_preview
            result_display["preview"] = humanized_summary.strip()
            result_display["previewDisplay"] = humanized_summary.strip()
            result_display["structuredPreviewDisplay"] = humanized_summary.strip()
            current_stderr = str(result_display.get("stderrDisplay") or "").strip()
            if current_stderr:
                if current_stderr != humanized_summary and not str(result_display.get("stderrDisplayRaw") or "").strip():
                    result_display["stderrDisplayRaw"] = current_stderr
                result_display["stderrDisplay"] = humanized_summary.strip()
                result_display["stderrDisplayDisplay"] = humanized_summary.strip()
            normalized["resultDisplay"] = result_display
        if isinstance(normalized.get("runtimeGuidanceDisplay"), dict):
            guidance_display = dict(normalized["runtimeGuidanceDisplay"])
            if should_replace_display_text(guidance_display.get("messageDisplay"), humanized_summary):
                raw_guidance_message = str(guidance_display.get("message") or "").strip()
                if raw_guidance_message and raw_guidance_message != humanized_summary and "messageRaw" not in guidance_display:
                    guidance_display["messageRaw"] = raw_guidance_message
                guidance_display["message"] = humanized_summary.strip()
                guidance_display["messageDisplay"] = humanized_summary.strip()
            if should_replace_display_text(guidance_display.get("previewDisplay"), humanized_summary):
                guidance_display["previewDisplay"] = humanized_summary.strip()
            next_command_display = humanize_runtime_next_command_display(
                worknet_key or None,
                guidance_display.get("nextCommand"),
            )
            if next_command_display:
                guidance_display["nextCommandDisplay"] = next_command_display
            normalized["runtimeGuidanceDisplay"] = guidance_display
    if not isinstance(normalized.get("previewDisplay"), str):
        fallback_preview = str(
            normalized.get("messageDisplay")
            or normalized.get("resultSummary")
            or normalized.get("textDisplay")
            or ""
        ).strip()
        if fallback_preview:
            normalized["previewDisplay"] = fallback_preview
    return normalized


def annotate_probe_results_display(
    probe_results: Any,
    *,
    skill_key: str,
) -> list[dict[str, Any]]:
    if not isinstance(probe_results, list):
        return []
    return [
        annotate_probe_result_display(item, skill_key=skill_key)
        for item in probe_results
        if isinstance(item, dict)
    ]


def annotate_skill_inspection_record(record: Any) -> Any:
    if not isinstance(record, dict):
        return record
    normalized = dict(record)
    skill_key = str(normalized.get("skillKey") or "").strip().lower()
    normalized["probeResults"] = annotate_probe_results_display(
        normalized.get("probeResults"),
        skill_key=skill_key,
    )
    return normalized


def annotate_skill_inspection_catalog_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    inspections = normalized.get("inspections")
    if isinstance(inspections, list):
        normalized["inspections"] = [
            annotate_skill_inspection_record(item)
            for item in inspections
            if isinstance(item, dict)
        ]
    return normalized


def annotate_capability_bundle_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    skill_inspections = normalized.get("skillInspections")
    if isinstance(skill_inspections, list):
        normalized["skillInspections"] = [
            annotate_skill_inspection_record(item)
            for item in skill_inspections
            if isinstance(item, dict)
        ]
    reports = normalized.get("reports")
    if isinstance(reports, list):
        annotated_reports: list[dict[str, Any]] = []
        for item in reports:
            if not isinstance(item, dict):
                continue
            report = dict(item)
            if isinstance(report.get("skillInspection"), dict):
                report["skillInspection"] = annotate_skill_inspection_record(report.get("skillInspection"))
            annotated_reports.append(report)
        normalized["reports"] = annotated_reports
    return normalized


def probe_failures_are_network_only(probe_results: list[dict[str, Any]]) -> bool:
    failed = [item for item in probe_results if isinstance(item, dict) and item.get("ok") is False]
    if not failed:
        return False
    for item in failed:
        result = item.get("result")
        if isinstance(result, dict):
            code = str(result.get("error") or result.get("title") or "")
            if code == "NETWORK_ERROR":
                continue
        text = str(item.get("text", ""))
        if "NETWORK_ERROR" in text or "Name or service not known" in text:
            continue
        return False
    return True


def probe_failures_are_expected_state(probe_results: list[dict[str, Any]]) -> bool:
    failed = [item for item in probe_results if isinstance(item, dict) and item.get("ok") is False]
    if not failed:
        return False
    for item in failed:
        result = item.get("result")
        if not isinstance(result, dict):
            return False
        code = str(result.get("error") or result.get("title") or result.get("error_code") or "")
        if not code:
            return False
        if code in {"NETWORK_ERROR"}:
            return False
    return True


def runtime_probe_blockers(skill_key: str, inspection: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    probe_results = inspection.get("probeResults", []) if isinstance(inspection, dict) else []
    if skill_key == "predict":
        for item in probe_results:
            if not isinstance(item, dict) or item.get("label") != "predict stake eligibility":
                continue
            result = item.get("result")
            if not isinstance(result, dict):
                continue
            error = result.get("error")
            if isinstance(error, dict):
                suggestion = error.get("suggestion")
                if suggestion:
                    blockers.append(str(suggestion))
                else:
                    user_message = result.get("user_message")
                    if user_message:
                        blockers.append(str(user_message).splitlines()[0])
    if skill_key == "gov":
        for item in probe_results:
            if not isinstance(item, dict) or item.get("label") != "gov private state":
                continue
            result = item.get("result")
            if not isinstance(result, dict):
                continue
            code = str(result.get("error") or result.get("title") or "")
            detail = str(result.get("detail") or "")
            if code == "STATE_PRINCIPAL_NOT_IN_EPOCH":
                blockers.append("当前主体这期还没有 AWP Power，所以 Gov 的签名动作会被挡住，直到质押或 AWP Power 到位。")
            elif detail:
                blockers.append(detail)
    if skill_key == "ardi":
        for item in probe_results:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            result = item.get("result")
            if not isinstance(result, dict):
                continue
            if label == "ardi gas check" and result.get("status") == "error":
                suggestion = result.get("data", {}).get("suggestion") if isinstance(result.get("data"), dict) else None
                if suggestion:
                    blockers.append(str(suggestion))
                else:
                    blockers.append("Ardi requires Base gas before commits and reveals can start")
            if label == "ardi stake guidance" and result.get("status") == "error":
                suggestion = result.get("data", {}).get("suggestion") if isinstance(result.get("data"), dict) else None
                if suggestion:
                    blockers.append(str(suggestion))
                else:
                    blockers.append("Ardi requires either KYA delegated stake or a self-staked 10000 AWP path before commits can start")
    return blockers


def humanize_capability_reason_part(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return raw
    replacements = {
        "official runtime checkout is installed locally": "官方运行环境源码已安装到本地",
        "official install URI known, but runtime not installed locally": "已知官方安装地址，但运行环境还没装到本地",
        "no verified local runtime found": "还没有找到可验证的本地运行环境",
        "runtime probe failed": "运行时探针失败",
        "runtime exists but still needs bootstrap before safe execution": "运行环境已存在，但安全执行前还要先完成初始化。",
        "workstation only has remote runtime guidance, not a local install": "当前只有远程运行指引，还没有本地安装。",
        "local runtime is present, but its live probes are blocked by the current network environment": "本地运行环境已存在，但实时探针被当前网络环境挡住了。",
        "official runtime checkout currently only exposes license or metadata files, so there is nothing safe to auto-run yet": "官方运行环境源码目前只有许可证或元数据文件，暂时没有可安全自动运行的内容。",
        "Predict can start with virtual chips now; staking remains an enhancement path rather than a hard prerequisite for the loop": "Predict 现在可以先用虚拟筹码开跑；质押仍是增强路径，不是这条循环的硬前置。",
        "If you want the stake-backed path later, use the official staking or KYA route and then re-run Predict stake checks": "如果之后想走质押增强路径，就按官方质押或 KYA 路线补齐资格后再重跑 Predict 检查。",
        "Principal has no AWP Power this epoch, so Gov signed actions are blocked until stake/power is available": "当前主体这期还没有 AWP Power，所以 Gov 的签名动作会被挡住，直到质押或 AWP Power 到位。",
        "Ardi requires Base gas before commits and reveals can start": "Ardi 在进入提交承诺和揭示前，先要补 Base Gas。",
        "Ardi requires either KYA delegated stake or a self-staked 10000 AWP path before commits can start": "Ardi 在进入提交承诺前，先要满足 KYA 委托或自质押 10000 AWP 其中一条路径。",
    }
    if raw in replacements:
        return replacements[raw]
    local_prefix = "local source present at "
    if raw.startswith(local_prefix):
        return f"本地源码已存在于 {raw[len(local_prefix):]}"
    probe_prefix = "runtime probe failed for "
    if raw.startswith(probe_prefix):
        return f"运行时探针失败：{raw[len(probe_prefix):]}"
    observe_prefix = "user preference still suggests observing Predict outcomes for the first "
    observe_suffix = " hours even though the official loop can start now"
    if raw.startswith(observe_prefix) and raw.endswith(observe_suffix):
        hours = raw[len(observe_prefix):-len(observe_suffix)]
        return f"按当前用户偏好，即使官方循环现在能启动，也建议先观察 Predict {hours} 小时"
    if raw.startswith("Send at least ") and " ETH to " in raw and " on Base" in raw:
        try:
            amount = raw.split("Send at least ", 1)[1].split(" ETH to ", 1)[0].strip()
            address = raw.split(" ETH to ", 1)[1].split(" on Base", 1)[0].strip()
            return f"先往 Base 主网的工作钱包 {address} 补至少 {amount} ETH 手续费，再回来重跑 Ardi Gas 检查。"
        except Exception:
            return "先补 Base 主网手续费，再回来重跑 Ardi Gas 检查。"
    if raw.startswith("Reach the 10000 AWP threshold on EITHER Ardi"):
        return "先满足 Ardi 或 KYA 其中一条 10000 AWP 资格路径，再回来重跑 Ardi 资格检查。"
    return raw


def humanize_playbook_goal(worknet_key: str, raw_goal: str) -> str:
    plain = canonical_worknet_plain_text(worknet_key)
    if plain:
        return plain
    return raw_goal


def humanize_playbook_role(role: str) -> str:
    text = str(role or "").strip()
    return KNOWLEDGE_ROLE_LABELS.get(text, text)


def humanize_playbook_loop(worknet_key: str, raw_loop: str) -> str:
    loop = canonical_worknet_loop_text(worknet_key)
    if loop:
        return loop
    return raw_loop


def humanize_playbook_success_metric(metric: str) -> str:
    mapping = {
        "valid commits": "有效提交答案承诺",
        "successful reveal timing": "按时完成揭示",
        "mint cap respected": "不超过铭刻上限",
        "low reasoning repetition": "推理重复率低",
        "rate-limit discipline": "频率控制稳定",
        "positive settlement quality": "结算质量保持正向",
        "correct phase timing": "阶段判断正确",
        "clear rationale": "判断理由清晰",
        "tracked settlement delta": "能持续跟踪结算结果",
    }
    text = str(metric or "").strip()
    return mapping.get(text, text)


def humanize_playbook_failure_mode(mode: str) -> str:
    mapping = {
        "insufficient Base gas": "Base 手续费不足",
        "stake ineligible": "资格路径还没满足",
        "missed reveal window": "错过揭示窗口",
        "duplicate reasoning": "推理内容重复",
        "overtrading": "交易过频或过度出手",
        "thin context": "市场上下文不足",
        "missing verified local runtime": "缺少可验证的本地运行环境",
        "stake gate still blocks submissions until 1000 AWP or KYA delegated eligibility is satisfied": "在满足 1000 AWP 或 KYA 委托资格前，正式提交仍会被挡住",
        "voting or trading outside phase windows": "在错误阶段投票或交易",
        "unreviewed capital movement": "未经确认就推进资金动作",
        "missing market context": "市场上下文不足",
        "public operator docs remain thin": "公开操作资料仍然偏薄",
        "official skill has not been inspected locally yet": "本地还没把官方 skill 路径审清楚",
    }
    text = str(mode or "").strip()
    return mapping.get(text, text)


def humanize_playbook_confirmation_item(text: str) -> str:
    mapping = {
        "Confirm funding the Base wallet before Ardi execution.": "Ardi 开始前先确认补 Base 手续费。",
        "Confirm the stake path before any buy, swap, or stake action.": "任何买入、兑换或质押前，先确认资格路径。",
        "Confirm every capital-bearing order or ticket action.": "每笔带资金风险的下单或 ticket 动作都要先确认。",
        "Confirm the stake or KYA-sponsored eligibility path before enabling the autonomous Predict loop.": "开启 Predict 自动循环前，先确认质押或 KYA 资格路径。",
        "Confirm every stake, allocation, vote, and trade action.": "每一笔质押、分配、投票和交易都要先确认。",
        "Confirm before auto-installing or executing the official Community skill.": "自动安装或执行 Community 官方 skill 前先确认。",
        "Confirm before auto-installing or executing the official TMR skill.": "自动安装或执行 TMR 官方 skill 前先确认。",
    }
    normalized = str(text or "").strip()
    return mapping.get(normalized, normalized)


def find_probe_result(inspection: dict[str, Any], label: str) -> Optional[dict[str, Any]]:
    probe_results = inspection.get("probeResults", []) if isinstance(inspection, dict) else []
    for item in probe_results:
        if isinstance(item, dict) and item.get("label") == label:
            return item
    return None


def predict_persona_value(inspection: dict[str, Any]) -> Optional[str]:
    step = find_probe_result(inspection, "predict status")
    payload = step_result_payload(step) if step else None
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("persona"), str):
        value = str(data.get("persona")).strip()
        return value or None
    return None


def persona_from_log_lines(lines: list[str]) -> Optional[str]:
    for line in reversed(lines):
        match = re.search(r"persona=([A-Za-z0-9_-]+)", line)
        if match:
            value = match.group(1).strip()
            return value or None
    return None


def predict_persona_hint(state: dict[str, Any], inspection: dict[str, Any]) -> Optional[str]:
    current = predict_persona_value(inspection)
    if current and current.strip().lower() not in {"none", "null"}:
        return current
    cached = load_json(Path(state["cache"]) / "skill-inspections.json", {})
    if isinstance(cached, dict):
        for item in cached.get("inspections", []):
            if not isinstance(item, dict) or item.get("skillKey") != "predict":
                continue
            cached_persona = predict_persona_value(item)
            if cached_persona and cached_persona.strip().lower() not in {"none", "null"}:
                return cached_persona
    for item in load_active_processes(state):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "")
        argv = [str(part) for part in item.get("argv", [])] if isinstance(item.get("argv"), list) else []
        if label.startswith("启动 Predict ") and ("loop" in label or "循环" in label) or argv[:2] == ["predict-agent", "loop"]:
            persona = persona_from_log_lines(tail_text(item.get("logPath"), lines=80))
            if persona and persona.lower() not in {"none", "null"}:
                return persona
    log_root = Path(state["runs"]) / "logs"
    if log_root.exists():
        candidates = sorted(log_root.glob("*predict-loop*.log"))
        for path in reversed(candidates[-5:]):
            persona = persona_from_log_lines(tail_text(str(path), lines=80))
            if persona and persona.lower() not in {"none", "null"}:
                return persona
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    if isinstance(latest_run, dict):
        for step in latest_run.get("executedSteps", []):
            if not isinstance(step, dict):
                continue
            label = str(step.get("label") or "")
            if label.startswith("设为 "):
                argv = step.get("argv")
                if isinstance(argv, list) and argv:
                    value = str(argv[-1]).strip()
                    if value and value.lower() not in {"none", "null"}:
                        return value
    return None


def predict_loop_ready(state: dict[str, Any], inspection: dict[str, Any]) -> bool:
    persona = (predict_persona_hint(state, inspection) or "").strip().lower()
    return persona not in {"", "none", "null"}


def derive_runtime_remediation(
    skill_key: str,
    *,
    state: dict[str, Any],
    skill_root: Optional[Path],
    probe_results: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    notes: list[str] = []
    commands: list[dict[str, Any]] = []
    combined_text = "\n".join(str(item.get("text", "")) for item in probe_results if isinstance(item, dict))

    if skill_root is not None and repository_is_effectively_empty(skill_root):
        notes.append(
            "The official checkout currently only contains license or metadata files, so there is no upstream runtime to bootstrap yet."
        )
        return notes, commands

    if skill_key == "mine" and "dataclass() got an unexpected keyword argument 'slots'" in combined_text:
        notes.append("Mine runtime needs Python 3.11+; the current default python3 is too old for dataclass(slots=True).")
        python311 = shutil.which("python3.11")
        if python311 and skill_root is not None:
            commands.append(
                {
                    "label": "bootstrap mine with python3.11",
                    "cwd": str(skill_root),
                    "argv": ["env", f"PYTHON_BIN={python311}", "bash", "./scripts/bootstrap.sh"],
                    "category": "repair",
                    "requires_confirmation": False,
                }
            )
        elif skill_root is not None:
            commands.append(
                {
                    "label": "bootstrap mine with Python 3.11+",
                    "cwd": str(skill_root),
                    "argv": ["bash", "./scripts/bootstrap.sh"],
                    "category": "repair",
                    "requires_confirmation": False,
                }
            )
    if skill_key == "awp-skill" and "Could not reach AWP API" in combined_text:
        notes.append("awp-skill runtime is installed, but its own preflight could not reach the AWP API from this environment.")
    if skill_key == "gov" and "No module named 'eth_hash'" in combined_text and skill_root is not None:
        notes.append("gov-skill checkout is present, but its Python dependencies are not installed yet.")
        commands.extend(
            [
                {
                    "label": "create gov skill venv",
                    "cwd": str(skill_root),
                    "argv": ["python3", "-m", "venv", ".venv"],
                    "category": "repair",
                    "requires_confirmation": False,
                },
                {
                    "label": "install gov skill deps",
                    "cwd": str(skill_root),
                    "argv": [str(skill_root / ".venv" / "bin" / "pip"), "install", "eth-hash", "eth-account", "websockets", "pytest"],
                    "category": "repair",
                    "requires_confirmation": False,
                },
            ]
        )
    if skill_key == "predict" and skill_root is not None:
        install_script = skill_root / "install.sh"
        cargo_toml = skill_root / "Cargo.toml"
        if install_script.exists() and cargo_toml.exists() and not command_exists("predict-agent"):
            notes.append("predict-skill checkout is present, but predict-agent is not installed yet. The official install script pulls a GitHub release binary.")
            commands.append(
                {
                    "label": "install predict-agent binary",
                    "cwd": str(skill_root),
                    "argv": ["bash", "install.sh"],
                    "category": "repair",
                    "requires_confirmation": False,
                }
            )
            if shutil.which("cargo"):
                notes.append("Rust toolchain is present, so building predict-agent from source is also possible if release downloads stay blocked.")
                commands.append(
                    {
                        "label": "build predict-agent from source",
                        "cwd": str(skill_root),
                        "argv": ["cargo", "build", "--release"],
                        "category": "repair",
                        "requires_confirmation": False,
                    }
                )
            else:
                notes.append("Rust toolchain is not installed here, so source-build fallback is not currently available.")

    return notes, commands


def public_preflight_view(report: dict[str, Any]) -> dict[str, Any]:
    return project_fields(report, PREFLIGHT_PUBLIC_FIELDS)


def humanize_public_capability_report(report: dict[str, Any]) -> dict[str, Any]:
    normalized = project_fields(report, CAPABILITY_PUBLIC_FIELDS)
    normalized["status"] = KNOWLEDGE_WORKNET_STATUS_LABELS.get(
        str(normalized.get("status") or "").strip().lower(),
        normalized.get("status"),
    )
    normalized["automationLevel"] = KNOWLEDGE_AUTOMATION_LABELS.get(
        str(normalized.get("automationLevel") or "").strip(),
        normalized.get("automationLevel"),
    )
    normalized["riskLevel"] = KNOWLEDGE_RISK_LABELS.get(
        str(normalized.get("riskLevel") or "").strip(),
        normalized.get("riskLevel"),
    )
    normalized["recommendedRole"] = KNOWLEDGE_ROLE_LABELS.get(
        str(normalized.get("recommendedRole") or "").strip(),
        normalized.get("recommendedRole"),
    )
    return normalized


def public_capability_view(report: dict[str, Any]) -> dict[str, Any]:
    return humanize_public_capability_report(report)


def humanize_playbook_command_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return text
    mapping = {
        "inspect mine skill": "检查 Mine skill",
        "mine agent status": "查看 Mine 运行状态",
        "mine control status": "查看 Mine 控制状态",
        "start mine worker": "启动 Mine 采集循环",
        "pause mine worker": "暂停 Mine 采集循环",
        "inspect predict skill": "检查 Predict skill",
        "predict wallet safety": "检查 Predict 钱包状态",
        "predict status": "查看 Predict 运行状态",
        "predict preflight": "重跑 Predict 预检",
        "predict stake eligibility": "检查 Predict 资格路径",
        "inspect gov skill": "检查 Gov skill",
        "gov public markets": "查看 Gov 公开市场",
        "gov phase-aware helper": "查看 Gov 当前阶段",
        "gov private state": "查看 Gov 私有状态",
        "inspect ardi skill": "检查 Ardi skill",
        "ardi status": "查看 Ardi 运行状态",
        "ardi gas check": "检查 Ardi 手续费",
        "ardi preflight": "重跑 Ardi 预检",
        "ardi stake guidance": "检查 Ardi 资格路径",
        "inspect community skill": "检查 Community skill",
        "inspect tmr skill": "检查 TMR skill",
        "inspect kya skill": "检查 KYA skill",
        "awp-skill preflight": "检查 AWP RootNet 预检",
        "kya relay recipient help": "查看 KYA 收款地址帮助",
        "kya sign claim help": "查看 KYA 签名认领帮助",
        "create gov skill venv": "创建 Gov 运行环境",
        "install gov skill deps": "安装 Gov 依赖",
    }
    if text in mapping:
        return mapping[text]
    if text.startswith("inspect ") and text.endswith(" skill"):
        return "检查 " + text[len("inspect "):]
    return text


def humanize_playbook_command_description(command: dict[str, Any]) -> str:
    label = str(command.get("label") or "").strip()
    if label in {"inspect mine skill", "inspect predict skill", "inspect gov skill", "inspect ardi skill", "inspect community skill", "inspect tmr skill", "inspect kya skill"}:
        return "先检查这条 WorkNet 的官方 skill、目录结构和本地运行准备情况。"
    if label in {"mine agent status", "predict status", "ardi status"}:
        return "查看当前运行状态，确认现在是不是已经具备继续条件。"
    if label == "mine control status":
        return "查看当前控制状态和是否已经存在活跃任务。"
    if label in {"predict preflight", "ardi preflight"}:
        return "重跑预检，确认现在能不能继续推进。"
    if label in {"predict stake eligibility", "ardi stake guidance"}:
        return "检查资格路径，看离正式运行还差什么。"
    if label == "ardi gas check":
        return "检查 Base 手续费是否足够，避免后续动作卡住。"
    if label == "gov public markets":
        return "直接看当前公开市场和可见机会。"
    if label == "gov phase-aware helper":
        return "查看当前所处阶段和最直接可做的动作。"
    if label == "gov private state":
        return "读取私有状态，确认签名动作前的关键前置条件。"
    if label == "start mine worker":
        return "启动 Mine 的主采集循环。"
    if label == "pause mine worker":
        return "暂停当前 Mine 采集循环。"
    if label == "create gov skill venv":
        return "创建 Gov 本地运行环境。"
    if label == "install gov skill deps":
        return "安装 Gov 运行依赖。"
    return "执行这条 playbook 命令。"


def humanize_executed_step_label(
    label: Any,
    *,
    category: Any = None,
    execution_policy: Any = None,
) -> Optional[str]:
    text = str(label or "").strip()
    if not text:
        return None
    playbook_label = humanize_playbook_command_label(text)
    if playbook_label != text:
        return playbook_label
    review_label = humanize_review_step_label("", text)
    if review_label != text:
        return review_label
    action_label = humanize_public_action_label(text)
    if action_label != text:
        return action_label
    category_text = str(category or "").strip().lower()
    policy_text = str(execution_policy or "").strip().lower()
    lowered = text.lower()
    if category_text == "inspect" or policy_text in {"probe", "manual-review"}:
        if lowered.startswith("inspect "):
            return "检查 " + text[len("inspect "):]
        return f"检查 {text}"
    if policy_text in {"manual-control"}:
        if lowered.startswith("pause "):
            return "暂停 " + text[len("pause "):]
        if lowered.startswith("stop "):
            return "停止 " + text[len("stop "):]
    if policy_text == "confirmation":
        return f"确认 {text}"
    return text


def humanize_public_playbook_commands(playbook: dict[str, Any]) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    commands = playbook.get("commands", [])
    for item in commands if isinstance(commands, list) else []:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        raw_label = str(item.get("label") or "").strip()
        human_label = humanize_playbook_command_label(raw_label)
        normalized["rawLabel"] = raw_label or None
        normalized["label"] = human_label or raw_label
        normalized["description"] = humanize_playbook_command_description(item)
        argv = item.get("argv")
        normalized["command"] = render_argv([str(part) for part in argv]) if isinstance(argv, list) and argv else item.get("command")
        rendered.append(normalized)
    return rendered


def public_playbook_view(playbook: dict[str, Any]) -> dict[str, Any]:
    normalized = project_fields(playbook, PLAYBOOK_PUBLIC_FIELDS)
    normalized["commands"] = humanize_public_playbook_commands(playbook)
    return normalized


def build_playbook_user_action_details(playbook: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    knowledge_actions = [
        item for item in playbook.get("knowledgeActions", [])
        if isinstance(item, dict)
    ] if isinstance(playbook.get("knowledgeActions"), list) else []
    command_actions = humanize_public_playbook_commands(playbook)
    combined = []
    if str(playbook.get("executionState") or "") == "review_required":
        combined.extend(knowledge_actions)
        combined.extend(command_actions)
    else:
        combined.extend(command_actions)
        combined.extend(knowledge_actions)
    for item in combined:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        command = str(item.get("command") or "").strip()
        if not label or not command:
            continue
        entries.append(
            {
                "label": label,
                "description": str(item.get("description") or "继续这个建议动作。").strip(),
                "command": command,
            }
        )
    prioritized = prioritize_action_entries(
        entries,
        execution_state=str(playbook.get("executionState") or "").strip() or None,
        resume_status=str(playbook.get("resumeStatus") or "").strip() or None,
        worknet_key=str(playbook.get("worknetKey") or "").strip() or None,
    )
    details: list[dict[str, Any]] = []
    for item in prioritized:
        append_unique_action_detail(
            details,
            label=str(item.get("label") or "").strip(),
            description=str(item.get("description") or "继续这个建议动作。").strip(),
            command=str(item.get("command") or "").strip() or None,
        )
    return details


def public_review_view(review: dict[str, Any]) -> dict[str, Any]:
    return project_fields(review, REVIEW_PUBLIC_FIELDS)


def public_workstation_status_view(report: dict[str, Any]) -> dict[str, Any]:
    return project_fields(report, WORKSTATION_STATUS_PUBLIC_FIELDS)


def public_workstation_preferences_view(report: dict[str, Any]) -> dict[str, Any]:
    return project_fields(report, WORKSTATION_PREFERENCES_PUBLIC_FIELDS)


def progress_message(step: int, total: int, title: str, detail: str) -> str:
    return f"[{step}/{total}] {title}: {detail}"


def source_filename(source: dict[str, Any]) -> str:
    parsed = urllib.parse.urlparse(str(source["url"]))
    path = parsed.path or ""
    suffix = Path(path).suffix.lower()
    if not suffix:
        suffix = ".txt" if source.get("kind") in {"skill-doc", "aip"} else ".bin"
    return f"{safe_slug(str(source['key']))}{suffix}"


def looks_like_state_root(root: Path) -> bool:
    markers = [
        root / "skills" / "install-status.json",
        root / "cache" / "preflight.json",
        root / "runs" / "latest-run.json",
        root / "user" / "preferences.json",
    ]
    return any(marker.exists() for marker in markers)


def candidate_state_roots(preferred: Path) -> list[Path]:
    discovered: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        key = str(resolved)
        if key in seen or resolved == preferred:
            return
        if not resolved.exists() or not resolved.is_dir():
            return
        if not looks_like_state_root(resolved):
            return
        seen.add(key)
        discovered.append(resolved)

    workspace_root = SKILL_ROOT.parent
    add(workspace_root)
    try:
        for child in sorted(workspace_root.iterdir()):
            if child.is_dir() and child.name.startswith(".tmp-state"):
                add(child)
    except OSError:
        pass

    cwd = Path.cwd()
    add(cwd)
    try:
        for child in sorted(cwd.iterdir()):
            if child.is_dir() and child.name.startswith(".tmp-state"):
                add(child)
    except OSError:
        pass

    return discovered


def state_candidate_summary(root: Path) -> dict[str, Any]:
    install_status = load_json(root / "skills" / "install-status.json", [])
    records = install_status if isinstance(install_status, list) else []
    managed_installed = sum(
        1 for item in records if isinstance(item, dict) and item.get("status") == "managed-installed"
    )
    external_local = sum(
        1 for item in records if isinstance(item, dict) and item.get("status") == "external-local"
    )
    official_remote = sum(
        1 for item in records if isinstance(item, dict) and item.get("status") == "official-remote"
    )
    preflight = load_json(root / "cache" / "preflight.json", {})
    registered = preflight.get("registered") if isinstance(preflight, dict) else None
    next_action = preflight.get("nextAction") if isinstance(preflight, dict) else None
    latest_run_exists = (root / "runs" / "latest-run.json").exists()
    history_exists = (root / "runs" / "history.jsonl").exists()
    reviews_exist = (root / "reviews" / "latest-review.json").exists()
    playbooks_exist = (root / "playbooks" / "last-selected.json").exists()
    active_processes = load_json(root / "runs" / "active-processes.json", [])
    active_background_count = len(active_processes) if isinstance(active_processes, list) else 0
    official_preflight_cache = (root / "cache" / "official-awp-skill-preflight.json").exists()
    official_live_cache = (root / "cache" / "official-live-worknets.json").exists()
    score = (
        managed_installed * 20
        + external_local * 4
        + official_remote * 2
        + (25 if registered is True else 0)
        + (8 if official_preflight_cache else 0)
        + (8 if official_live_cache else 0)
        + (6 if latest_run_exists else 0)
        + (3 if history_exists else 0)
        + (2 if reviews_exist else 0)
        + (2 if playbooks_exist else 0)
        + min(active_background_count, 3) * 2
    )
    return {
        "root": str(root),
        "managedInstalled": managed_installed,
        "externalLocal": external_local,
        "officialRemote": official_remote,
        "registered": registered,
        "nextAction": next_action,
        "latestRunExists": latest_run_exists,
        "historyExists": history_exists,
        "reviewsExist": reviews_exist,
        "playbooksExist": playbooks_exist,
        "activeBackgroundCount": active_background_count,
        "officialPreflightCache": official_preflight_cache,
        "officialLiveCache": official_live_cache,
        "score": score,
    }


def preferred_state_needs_bootstrap(summary: dict[str, Any]) -> bool:
    return (
        summary.get("managedInstalled", 0) == 0
        and summary.get("registered") is not True
        and not summary.get("latestRunExists")
        and summary.get("nextAction") in {None, "install_awp_skill_dependency", "install_or_setup_wallet"}
    )


def replace_state_root_references(value: Any, source_root: str, target_root: str) -> Any:
    if isinstance(value, str):
        return value.replace(source_root, target_root) if source_root in value else value
    if isinstance(value, list):
        return [replace_state_root_references(item, source_root, target_root) for item in value]
    if isinstance(value, dict):
        return {
            str(key): replace_state_root_references(item, source_root, target_root)
            for key, item in value.items()
        }
    return value


def rewrite_json_state_paths(path: Path, source_root: str, target_root: str) -> None:
    payload = load_json(path, None)
    if payload is None:
        return
    rewritten = replace_state_root_references(payload, source_root, target_root)
    atomic_write_json(path, rewritten)


def rewrite_jsonl_state_paths(path: Path, source_root: str, target_root: str) -> None:
    if not path.exists():
        return
    rewritten_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            rewritten_lines.append(line)
            continue
        rewritten_lines.append(
            json.dumps(
                replace_state_root_references(payload, source_root, target_root),
                ensure_ascii=True,
            )
        )
    path.write_text("\n".join(rewritten_lines) + ("\n" if rewritten_lines else ""), encoding="utf-8")


def repair_adopted_state_references(target_root: Path, source_root: str) -> None:
    target_root_str = str(target_root)
    if source_root == target_root_str:
        return
    for rel in (
        "runs/latest-run.json",
        "runs/pending-confirmations.json",
        "runs/active-processes.json",
        "reviews/latest-review.json",
        "playbooks/last-selected.json",
    ):
        rewrite_json_state_paths(target_root / rel, source_root, target_root_str)
    playbooks_root = target_root / "playbooks"
    if playbooks_root.exists():
        for item in playbooks_root.glob("*.json"):
            rewrite_json_state_paths(item, source_root, target_root_str)
    rewrite_jsonl_state_paths(target_root / "runs" / "history.jsonl", source_root, target_root_str)


def select_state_bootstrap_candidate(preferred: Path) -> Optional[dict[str, Any]]:
    preferred_summary = state_candidate_summary(preferred)
    if not preferred_state_needs_bootstrap(preferred_summary):
        return None
    candidates = [state_candidate_summary(root) for root in candidate_state_roots(preferred)]
    candidates = [
        item
        for item in candidates
        if item.get("score", 0) > preferred_summary.get("score", 0)
        and (
            item.get("managedInstalled", 0) > preferred_summary.get("managedInstalled", 0)
            or item.get("registered") is True
            or item.get("latestRunExists")
        )
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            int(item.get("score", 0)),
            int(item.get("managedInstalled", 0)),
            1 if item.get("registered") is True else 0,
            1 if item.get("latestRunExists") else 0,
        ),
        reverse=True,
    )
    return candidates[0]


def adopt_state_root(source_root: Path, target_root: Path, source_summary: dict[str, Any]) -> dict[str, Any]:
    copied_dirs: list[str] = []
    copied_files: list[str] = []
    for rel in ("skills/checkouts", "playbooks", "runs", "reviews"):
        source = source_root / rel
        if not source.exists():
            continue
        shutil.copytree(source, target_root / rel, dirs_exist_ok=True)
        copied_dirs.append(rel)
    for rel in (
        "cache/official-awp-skill-preflight.json",
        "cache/official-live-worknets.json",
        "user/preferences.json",
    ):
        source = source_root / rel
        if not source.exists():
            continue
        destination = target_root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_files.append(rel)
    repair_adopted_state_references(target_root, str(source_root))
    payload = {
        "adoptedAt": now_iso(),
        "sourceRoot": str(source_root),
        "targetRoot": str(target_root),
        "copiedDirs": copied_dirs,
        "copiedFiles": copied_files,
        "sourceSummary": source_summary,
    }
    atomic_write_json(target_root / "cache" / "state-bootstrap.json", payload)
    return payload


def maybe_bootstrap_preferred_state(preferred: Path) -> Optional[dict[str, Any]]:
    if os.environ.get(STATE_ENV_VAR):
        return None
    try:
        default_root = DEFAULT_STATE_ROOT.resolve()
        preferred_root = preferred.resolve()
    except OSError:
        return None
    if preferred_root != default_root:
        return None
    candidate = select_state_bootstrap_candidate(preferred_root)
    if not isinstance(candidate, dict):
        return None
    return adopt_state_root(Path(str(candidate["root"])), preferred_root, candidate)


def state_context() -> dict[str, Any]:
    preferred = Path(os.environ.get(STATE_ENV_VAR, str(DEFAULT_STATE_ROOT))).expanduser()
    root = preferred
    warnings: list[str] = []
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        root = DEFAULT_FALLBACK_STATE_ROOT
        root.mkdir(parents=True, exist_ok=True)
        warnings.append(
            f"state root {preferred} was not writable; using fallback {root}"
        )
    layout = {
        "root": root,
        "cache": root / "cache",
        "skills": root / "skills",
        "playbooks": root / "playbooks",
        "runs": root / "runs",
        "reviews": root / "reviews",
        "user": root / "user",
    }
    for path in layout.values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    bootstrap = maybe_bootstrap_preferred_state(root)
    if isinstance(bootstrap, dict):
        layout["bootstrap"] = bootstrap
        warnings.append(
            f"adopted richer workstation state from {bootstrap.get('sourceRoot')} into {bootstrap.get('targetRoot')}"
        )
    else:
        cached_bootstrap = load_json(Path(root) / "cache" / "state-bootstrap.json", None)
        if (
            isinstance(cached_bootstrap, dict)
            and str(cached_bootstrap.get("targetRoot") or "") == str(root)
        ):
            layout["bootstrap"] = cached_bootstrap
        else:
            layout["bootstrap"] = None
    if isinstance(layout.get("bootstrap"), dict):
        source_root = layout["bootstrap"].get("sourceRoot")
        if isinstance(source_root, str) and source_root:
            repair_adopted_state_references(Path(root), source_root)
    layout["warnings"] = warnings
    layout["preferredRoot"] = str(preferred)
    layout["root"] = str(root)
    return layout


def ensure_user_preferences(state: dict[str, Any]) -> dict[str, Any]:
    path = Path(state["user"]) / "preferences.json"
    current = load_json(path, {})
    merged = dict(DEFAULT_USER_PREFERENCES)
    if isinstance(current, dict):
        merged.update(current)
    if not merged.get("updatedAt"):
        merged["updatedAt"] = now_iso()
    atomic_write_json(path, merged)
    return merged


def update_user_preferences(
    *,
    state: Optional[dict[str, Any]] = None,
    preferred_worknet: Optional[str] = None,
    allow_asset_actions: Optional[bool] = None,
    autopilot_mode: Optional[str] = None,
    allow_third_party_skills: Optional[bool] = None,
    observe_before_predict_hours: Optional[int] = None,
    risk_profile: Optional[str] = None,
) -> dict[str, Any]:
    state = state or state_context()
    current = ensure_user_preferences(state)
    updated = dict(current)
    applied_changes: list[dict[str, Any]] = []

    def apply_change(key: str, value: Any) -> None:
        if updated.get(key) == value:
            return
        applied_changes.append(
            {
                "field": key,
                "previous": current.get(key),
                "current": value,
            }
        )
        updated[key] = value

    if preferred_worknet is not None:
        profile = resolve_worknet(preferred_worknet)
        if profile is None:
            raise ValueError(f"unknown worknet for preference: {preferred_worknet}")
        apply_change("preferredWorknet", str(profile["key"]))
    if allow_asset_actions is not None:
        apply_change("allowAssetActions", bool(allow_asset_actions))
    if autopilot_mode is not None:
        text = str(autopilot_mode).strip()
        if not text:
            raise ValueError("autopilot mode must not be empty")
        apply_change("autopilotMode", text)
    if allow_third_party_skills is not None:
        apply_change("allowThirdPartySkills", bool(allow_third_party_skills))
    if observe_before_predict_hours is not None:
        hours = int(observe_before_predict_hours)
        if hours < 0:
            raise ValueError("observeBeforePredictHours must be >= 0")
        apply_change("observeBeforePredictHours", hours)
    if risk_profile is not None:
        text = str(risk_profile).strip()
        if not text:
            raise ValueError("risk profile must not be empty")
        apply_change("riskProfile", text)

    if applied_changes:
        updated["updatedAt"] = now_iso()
        if current.get("updatedAt") != updated.get("updatedAt"):
            applied_changes.append(
                {
                    "field": "updatedAt",
                    "previous": current.get("updatedAt"),
                    "current": updated.get("updatedAt"),
                }
            )
        atomic_write_json(Path(state["user"]) / "preferences.json", updated)
    else:
        updated["updatedAt"] = current.get("updatedAt")

    message_parts: list[str] = []
    if preferred_worknet is not None:
        profile = resolve_worknet(preferred_worknet)
        if profile is not None:
            message_parts.append(f"默认 WorkNet 已设为 {profile['name']}")
    if allow_asset_actions is False or str(autopilot_mode or "") == "non-financial-only":
        message_parts.append("自动模式已锁定为非资金优先")
    if allow_asset_actions is True:
        message_parts.append("资产动作开关已允许，但实际执行仍会按技能和确认规则约束")
    if not message_parts:
        message_parts.append("已更新 Workstation 偏好" if applied_changes else "Workstation 偏好没有变化")

    return {
        "generatedAt": now_iso(),
        "message": "；".join(message_parts) + "。",
        "appliedChanges": applied_changes,
        "userPreferences": updated,
        "stateRoot": state["root"],
    }


def official_preflight_cache_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "official-awp-skill-preflight.json"


def official_live_worknets_cache_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "official-live-worknets.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")
        temp_name = handle.name
    Path(temp_name).replace(path)


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True))
        handle.write("\n")


def active_processes_path(state: dict[str, Any]) -> Path:
    return Path(state["runs"]) / "active-processes.json"


def process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def load_active_processes(state: dict[str, Any]) -> list[dict[str, Any]]:
    path = active_processes_path(state)
    records = load_json(path, [])
    if not isinstance(records, list):
        return []
    alive: list[dict[str, Any]] = []
    changed = False
    for item in records:
        if not isinstance(item, dict):
            changed = True
            continue
        pid = item.get("pid")
        if isinstance(pid, int) and process_is_alive(pid):
            alive.append(item)
        else:
            changed = True
    if changed:
        atomic_write_json(path, alive)
    return alive


def register_active_process(state: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    active = load_active_processes(state)
    active.append(record)
    atomic_write_json(active_processes_path(state), active)
    return active


def tail_text(path: Optional[str], lines: int = 40) -> list[str]:
    if not path:
        return []
    target = Path(path)
    if not target.exists():
        return []
    try:
        content = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return content[-lines:]


def summarize_background_log(record: dict[str, Any], log_tail: list[str]) -> dict[str, Any]:
    label = str(record.get("label") or "")
    argv = [str(item) for item in record.get("argv", [])] if isinstance(record.get("argv"), list) else []
    summary = {
        "state": "running",
        "headline": "后台任务正在运行。",
        "detail": log_tail[-1] if log_tail else None,
    }
    if (label.startswith("启动 Predict ") and ("loop" in label or "循环" in label)) or (argv[:2] == ["predict-agent", "loop"]):
        persona = None
        target = None
        last_wait = None
        for line in log_tail:
            text = line.strip()
            if "persona=" in text and "timeslot=" in text:
                persona = text
            if "target=" in text:
                target = text
            if "sleeping " in text:
                last_wait = text
        for line in reversed(log_tail):
            text = line.strip()
            if "failed to parse LLM response" in text or "LLM call failed" in text:
                return {
                    "state": "llm_error",
                    "headline": "Predict loop 最近一轮在 LLM 输出解析阶段失败，已进入等待重试。",
                    "detail": text,
                    "personaLine": persona,
                    "targetLine": target,
                }
            if "no submittable markets" in text:
                return {
                    "state": "waiting_for_market",
                    "headline": "Predict loop 最近一轮没有可提交市场，正在等待下一轮。",
                    "detail": text,
                    "personaLine": persona,
                }
            if "calling LLM via openclaw" in text:
                return {
                    "state": "llm_running",
                    "headline": "Predict loop 正在调用 LLM 生成本轮决策。",
                    "detail": target or text,
                    "personaLine": persona,
                    "targetLine": target,
                }
            if "got challenge nonce=" in text:
                return {
                    "state": "challenge_ready",
                    "headline": "Predict loop 已拿到 challenge，正在准备本轮推理。",
                    "detail": text,
                    "personaLine": persona,
                    "targetLine": target,
                }
            if "balance=" in text and "persona=" in text:
                return {
                    "state": "iteration_started",
                    "headline": "Predict loop 已开始新一轮检查。",
                    "detail": text,
                    "personaLine": persona,
                }
            if "starting (interval=" in text:
                return {
                    "state": "starting",
                    "headline": "Predict loop 已启动，正在准备第一轮。",
                    "detail": text,
                }
        if last_wait:
            summary["detail"] = last_wait
    return summary


def find_active_process(state: dict[str, Any], label: str) -> Optional[dict[str, Any]]:
    for item in load_active_processes(state):
        if isinstance(item, dict) and str(item.get("label")) == label:
            return item
    return None


def remove_active_process(state: dict[str, Any], label: str) -> list[dict[str, Any]]:
    active = [
        item for item in load_active_processes(state)
        if not (isinstance(item, dict) and str(item.get("label")) == label)
    ]
    atomic_write_json(active_processes_path(state), active)
    return active


def inspect_background_process(
    state: dict[str, Any],
    label: str,
    *,
    tail_lines: int = 40,
) -> dict[str, Any]:
    record = find_active_process(state, label)
    if record is None:
        raise ValueError(f"unknown background label: {label}")
    return summarize_background_record(record, tail_lines=tail_lines)


def summarize_background_record(
    record: dict[str, Any],
    *,
    tail_lines: int = 40,
) -> dict[str, Any]:
    log_tail = tail_text(record.get("logPath"), lines=tail_lines)
    return {
        "label": str(record.get("label") or ""),
        "pid": record.get("pid"),
        "cwd": record.get("cwd"),
        "argv": record.get("argv"),
        "logPath": record.get("logPath"),
        "startedAt": record.get("startedAt"),
        "alive": process_is_alive(int(record["pid"])) if isinstance(record.get("pid"), int) else False,
        "logTail": log_tail,
        "summary": summarize_background_log(record, log_tail),
    }


def stop_background_process(
    state: dict[str, Any],
    label: str,
    *,
    execute: bool,
    sigkill_after_seconds: float = 2.0,
) -> dict[str, Any]:
    record = find_active_process(state, label)
    if record is None:
        raise ValueError(f"unknown background label: {label}")
    pid = record.get("pid")
    preview = {
        "label": label,
        "pid": pid,
        "logPath": record.get("logPath"),
        "stopCommand": f"kill -TERM {pid}" if isinstance(pid, int) else None,
        "alive": process_is_alive(pid) if isinstance(pid, int) else False,
    }
    if not execute or not isinstance(pid, int):
        return {
            "status": "needs_confirmation",
            "selectedBackground": preview,
            "activeBackgroundProcesses": load_active_processes(state),
        }
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        preview["error"] = str(exc)
        return {
            "status": "failed",
            "selectedBackground": preview,
            "activeBackgroundProcesses": load_active_processes(state),
        }
    deadline = time.time() + sigkill_after_seconds
    while time.time() < deadline and process_is_alive(pid):
        time.sleep(0.1)
    if process_is_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    remaining = remove_active_process(state, label)
    preview["alive"] = process_is_alive(pid)
    return {
        "status": "stopped" if not preview["alive"] else "stop_requested",
        "selectedBackground": preview,
        "activeBackgroundProcesses": remaining,
    }


def launch_background_command(
    argv: list[str],
    *,
    cwd: Optional[str],
    state: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    log_dir = Path(state["runs"]) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    slug = safe_slug(label) or "background-task"
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    log_path = log_dir / f"{slug}-{stamp}.log"
    with log_path.open("ab") as handle:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    record = {
        "label": label,
        "argv": [str(item) for item in argv],
        "cwd": cwd,
        "pid": process.pid,
        "logPath": str(log_path),
        "startedAt": now_iso(),
    }
    register_active_process(state, record)
    return record


def write_reference_export(filename: str, payload: Any) -> str:
    REFERENCE_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REFERENCE_EXPORT_ROOT / filename
    atomic_write_json(path, payload)
    return str(path)


def rpc_call(method: str, params: Any = None, timeout: int = 15) -> dict[str, Any]:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {} if params is None else params,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        DEFAULT_RPC_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_FETCH_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            body_text = exc.read().decode("utf-8")
        except OSError:
            body_text = str(exc)
        return {"ok": False, "error": f"http {exc.code}", "body": parse_json_loose(body_text)}
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "error": str(exc), "body": None}
    payload = parse_json_loose(raw)
    if isinstance(payload, dict) and payload.get("error"):
        return {"ok": False, "error": payload["error"], "body": payload}
    return {"ok": True, "error": None, "body": payload}


def rpc_try_many(method: str, params_options: list[Any]) -> dict[str, Any]:
    errors: list[str] = []
    for params in params_options:
        response = rpc_call(method, params=params)
        if response.get("ok"):
            return response
        error = response.get("error")
        if error:
            errors.append(str(error))
    return {"ok": False, "error": "; ".join(errors) if errors else "no successful call", "body": None}


def rpc_result_body(payload: Any) -> Any:
    if isinstance(payload, dict) and "result" in payload:
        return payload["result"]
    return payload


def first_present(record: Any, keys: list[str], default: Any = None) -> Any:
    if not isinstance(record, dict):
        return default
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return default


def normalize_worknet_entries(payload: Any) -> list[dict[str, Any]]:
    body = rpc_result_body(payload)
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    if isinstance(body, dict):
        for key in ("items", "worknets", "data", "rows", "results"):
            value = body.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def normalize_search_entries(payload: Any) -> list[dict[str, Any]]:
    body = rpc_result_body(payload)
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    if isinstance(body, dict):
        for key in ("items", "worknets", "data", "rows", "results"):
            value = body.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def looks_official_skill_uri(uri: Optional[str]) -> bool:
    if not uri:
        return False
    return uri.startswith(OFFICIAL_SKILL_ALLOWLIST_PREFIXES) or "github.com/awp-core/awp-skill" in uri


def discover_local_sources() -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    for candidate in LOCAL_SOURCE_CANDIDATES:
        root = Path(candidate["path"])
        record = dict(candidate)
        record["available"] = root.exists()
        record["path"] = str(root)
        important = []
        for relative in candidate.get("important_files", []):
            file_path = root / relative
            if file_path.exists():
                important.append(str(file_path))
        record["present_files"] = important
        discovered.append(record)
    return discovered


def skill_registry_from_inventory(
    inventory: dict[str, Any], state: Optional[dict[str, Any]] = None
) -> list[dict[str, Any]]:
    local_by_key = {
        item["key"]: item for item in inventory.get("localSources", []) if isinstance(item, dict)
    }
    managed_root = (
        Path(state["skills"]) / "checkouts" if state is not None else DEFAULT_FALLBACK_STATE_ROOT / "skills"
    )
    records: list[dict[str, Any]] = []

    for dependency in CORE_DEPENDENCY_SKILLS:
        local_source = local_by_key.get(dependency["key"])
        managed_path = managed_root / safe_slug(dependency["key"])
        records.append(
            {
                "key": dependency["key"],
                "name": dependency["name"],
                "installUri": dependency["installUri"],
                "official": dependency["official"],
                "autoInstallEligible": dependency["autoInstallEligible"],
                "status": (
                    "managed-installed"
                    if managed_path.exists()
                    else ("external-local" if local_source and local_source.get("available") else "missing")
                ),
                "managedPath": str(managed_path),
                "localPath": local_source.get("path") if isinstance(local_source, dict) else None,
                "reason": dependency["reason"],
            }
        )

    for profile in KNOWN_WORKNETS:
        install_uri = profile.get("install_uri")
        if not install_uri and not profile.get("local_source_key"):
            continue
        local_source = local_by_key.get(profile.get("local_source_key"))
        managed_path = managed_root / profile["key"]
        if managed_path.exists():
            status = "managed-installed"
        elif local_source and local_source.get("available"):
            status = "external-local"
        elif install_uri and looks_official_skill_uri(install_uri):
            status = "official-remote"
        elif install_uri:
            status = "third-party-remote"
        else:
            status = "unknown"
        records.append(
            {
                "key": profile["key"],
                "name": profile["name"],
                "installUri": install_uri,
                "official": looks_official_skill_uri(install_uri),
                "autoInstallEligible": bool(install_uri and looks_official_skill_uri(install_uri)),
                "status": status,
                "managedPath": str(managed_path),
                "localPath": local_source.get("path") if isinstance(local_source, dict) else None,
                "reason": profile["goal"],
            }
        )
    return records


def resolve_skill_root(
    skill_key: str,
    inventory: Optional[dict[str, Any]] = None,
    state: Optional[dict[str, Any]] = None,
) -> tuple[Optional[Path], str]:
    state = state or state_context()
    inventory = inventory or build_source_inventory()
    managed_root = Path(state["skills"]) / "checkouts"
    managed_path = managed_root / safe_slug(skill_key)
    if managed_path.exists():
        return managed_path, "managed"

    local_sources = {
        item["key"]: item for item in inventory.get("localSources", []) if isinstance(item, dict)
    }
    profile = next((item for item in KNOWN_WORKNETS if item["key"] == skill_key), None)
    if profile and profile.get("local_source_key"):
        local_source = local_sources.get(profile["local_source_key"])
        if local_source and local_source.get("available"):
            return Path(str(local_source["path"])), "local-source"
    if skill_key in local_sources and local_sources[skill_key].get("available"):
        return Path(str(local_sources[skill_key]["path"])), "local-source"
    return None, "missing"


def extract_command_hints_from_skill_md(path: Path, limit: int = 20) -> list[str]:
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    hints: list[str] = []
    for match in COMMAND_HINT_RE.finditer(text):
        cmd = " ".join(match.group(1).split())
        if cmd not in hints:
            hints.append(cmd)
        if len(hints) >= limit:
            break
    return hints


def inspect_skill_runtime(
    skill_key: str,
    *,
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state or state_context()
    inventory = inventory or build_source_inventory()
    root, origin = resolve_skill_root(skill_key, inventory=inventory, state=state)
    manifest = official_remote_manifest(skill_key)
    expected_root = root or planned_skill_root(skill_key, state)
    bootstrap_commands = build_manifest_commands(
        skill_key,
        state=state,
        skill_root=root,
        section="bootstrapCommands",
    )
    inspection_commands = build_manifest_commands(
        skill_key,
        state=state,
        skill_root=root,
        section="inspectionCommands",
    )
    required_bins = [str(item) for item in manifest.get("requiredBins", [])]
    optional_bins = [str(item) for item in manifest.get("optionalBins", [])]
    bin_status = {
        "required": {name: command_exists(name) for name in required_bins},
        "optional": {name: command_exists(name) for name in optional_bins},
    }
    missing_required_bins = [name for name, ok in bin_status["required"].items() if not ok]
    probe_results = annotate_probe_results_display([
        run_inspection_probe(command)
        for command in inspection_commands
        if command.get("autoRunOnInspect") and command_probe_available(command)
    ], skill_key=skill_key)
    remediation_notes, remediation_commands = derive_runtime_remediation(
        skill_key,
        state=state,
        skill_root=root,
        probe_results=probe_results,
    )
    failing_probe_labels = [
        str(item.get("label"))
        for item in probe_results
        if isinstance(item, dict) and item.get("ok") is False
    ]
    network_only_failures = probe_failures_are_network_only(probe_results)
    expected_state_failures = probe_failures_are_expected_state(probe_results)
    if root is None:
        status = "remote-profile-only" if manifest else "missing"
        warnings = ["skill root not found"]
        if manifest:
            warnings.append("official remote profile exists, but the skill checkout is not installed locally")
            if missing_required_bins:
                warnings.append("missing required runtime bins: " + ", ".join(missing_required_bins))
        return {
            "skillKey": skill_key,
            "status": status,
            "origin": origin,
            "root": None,
            "expectedRoot": str(expected_root),
            "skillMdExists": False,
            "readmeExists": False,
            "repositoryFileCount": 0,
            "repositoryFilesSample": [],
            "substantiveFileCount": 0,
            "scripts": [],
            "commandHints": [],
            "manifestSummary": manifest.get("summary"),
            "runtimeName": manifest.get("runtimeName"),
            "requiredBins": required_bins,
            "optionalBins": optional_bins,
            "binStatus": bin_status,
            "env": list(manifest.get("env", [])),
            "bootstrapCommands": bootstrap_commands,
            "inspectionCommands": inspection_commands,
            "probeResults": probe_results,
            "remediationNotes": remediation_notes,
            "remediationCommands": remediation_commands,
            "warnings": warnings,
        }

    skill_md = root / "SKILL.md"
    readme = root / "README.md"
    scripts_dir = root / "scripts"
    repo_files = repository_files(root)
    substantive_files = [
        path for path in repo_files if not repository_file_is_metadata(path)
    ]
    empty_official_repo = origin == "managed" and repository_is_effectively_empty(root)
    script_files = []
    if scripts_dir.exists():
        script_files = [
            str(path.relative_to(root))
            for path in sorted(scripts_dir.rglob("*"))
            if path.is_file()
        ]
    command_hints = extract_command_hints_from_skill_md(skill_md)
    warnings: list[str] = []
    if not skill_md.exists():
        warnings.append("SKILL.md missing")
    if origin == "managed" and not script_files and not bool(manifest.get("binaryRuntime")):
        warnings.append("managed skill has no script files")
    if empty_official_repo:
        warnings.append("managed checkout currently only contains license or metadata files")
    if missing_required_bins:
        warnings.append("missing required runtime bins: " + ", ".join(missing_required_bins))
    if failing_probe_labels:
        if network_only_failures:
            warnings.append("auto inspection probe hit network limits: " + ", ".join(failing_probe_labels))
        elif expected_state_failures:
            warnings.append("auto inspection probe hit protocol state blockers: " + ", ".join(failing_probe_labels))
        else:
            warnings.append("auto inspection probe failed: " + ", ".join(failing_probe_labels))
    status = "ready" if skill_md.exists() else "partial"
    if empty_official_repo:
        status = "empty-official-repo"
    elif manifest and missing_required_bins:
        status = "installed-needs-bootstrap"
    elif network_only_failures:
        status = "network-blocked"
    elif failing_probe_labels and not expected_state_failures:
        status = "runtime-error"
    return {
        "skillKey": skill_key,
        "status": status,
        "origin": origin,
        "root": str(root),
        "skillMdExists": skill_md.exists(),
        "readmeExists": readme.exists(),
        "repositoryFileCount": len(repo_files),
        "repositoryFilesSample": repo_files[:20],
        "substantiveFileCount": len(substantive_files),
        "scripts": script_files,
        "scriptCount": len(script_files),
        "commandHints": command_hints,
        "manifestSummary": manifest.get("summary"),
        "runtimeName": manifest.get("runtimeName"),
        "requiredBins": required_bins,
        "optionalBins": optional_bins,
        "binStatus": bin_status,
        "env": list(manifest.get("env", [])),
        "bootstrapCommands": bootstrap_commands,
        "inspectionCommands": inspection_commands,
        "probeResults": probe_results,
        "remediationNotes": remediation_notes,
        "remediationCommands": remediation_commands,
        "warnings": warnings,
    }


def build_skill_inspection_catalog(
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state or state_context()
    inventory = inventory or build_source_inventory()
    keys = {"awp-skill", "awp-wallet"}
    keys.update(item["key"] for item in KNOWN_WORKNETS)
    inspections = [inspect_skill_runtime(key, state=state, inventory=inventory) for key in sorted(keys)]
    payload = annotate_skill_inspection_catalog_payload({
        "generatedAt": now_iso(),
        "inspections": inspections,
    })
    atomic_write_json(Path(state["cache"]) / "skill-inspections.json", payload)
    write_reference_export("skill-inspections.json", payload)
    return payload


def load_cached_skill_inspection_catalog(
    state: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    state = state or state_context()
    payload = load_json(Path(state["cache"]) / "skill-inspections.json", None)
    if not isinstance(payload, dict):
        return None
    inspections = payload.get("inspections")
    if not isinstance(inspections, list):
        return None
    return annotate_skill_inspection_catalog_payload(payload)


def build_recovery_state(state: dict[str, Any]) -> dict[str, Any]:
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    pending = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    latest_playbook = load_json(Path(state["playbooks"]) / "last-selected.json", {})
    latest_review = load_json(Path(state["reviews"]) / "latest-review.json", {})
    latest_run_playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
    active_processes = [
        inspect_background_process(state, str(item.get("label")), tail_lines=20)
        for item in load_active_processes(state)
        if isinstance(item, dict) and item.get("label")
    ]
    pending_count = len(pending) if isinstance(pending, list) else 0
    executed_count = len(latest_run.get("executedSteps", [])) if isinstance(latest_run, dict) else 0
    follow_up_actions = normalized_follow_up_actions(latest_run.get("followUpActions", [])) if isinstance(latest_run, dict) else []
    normalized_pending = normalized_confirmation_queue(pending)
    default_follow_up = choose_default_follow_up_action(follow_up_actions)
    default_confirmation = choose_default_confirmation(normalized_pending)
    runtime_guidance = latest_run.get("runtimeGuidance", {}) if isinstance(latest_run, dict) else {}
    runtime_guidance = runtime_guidance if isinstance(runtime_guidance, dict) else {}
    source_follow_up = latest_run.get("sourceFollowUpAction", {}) if isinstance(latest_run, dict) else {}
    last_worknet_key = (
        latest_run_playbook.get("worknetKey")
        if isinstance(latest_run_playbook, dict) and latest_run_playbook.get("worknetKey")
        else (latest_playbook.get("worknetKey") if isinstance(latest_playbook, dict) else None)
    )
    latest_run_generated_at = latest_run.get("generatedAt") if isinstance(latest_run, dict) else None
    latest_run_age_hours = hours_since_iso(latest_run_generated_at)
    latest_review_worknet_key = str(latest_review.get("worknetKey") or "") if isinstance(latest_review, dict) and latest_review.get("worknetKey") else None
    latest_review_matches_last_worknet = bool(
        latest_review_worknet_key
        and last_worknet_key
        and latest_review_worknet_key == str(last_worknet_key)
    )
    latest_review_status = (
        str(latest_review.get("status") or "")
        if isinstance(latest_review, dict) and (latest_review_matches_last_worknet or not last_worknet_key or not latest_review_worknet_key)
        else ""
    )
    latest_review_headline = (
        latest_review.get("headline")
        if isinstance(latest_review, dict) and (latest_review_matches_last_worknet or not last_worknet_key or not latest_review_worknet_key)
        else None
    )
    old_run_stopped = bool(latest_run) and not active_processes and str(runtime_guidance.get("nextAction") or "") == "monitor_background_run"
    stale_statuses = {"restart_available", "blocked", "partial", "observe_only", "awaiting_dataset"}
    stale_due_to_review = latest_review_status in stale_statuses
    stale_due_to_age = bool(latest_run) and not active_processes and pending_count == 0 and latest_run_age_hours is not None and latest_run_age_hours >= 2.0
    stale_latest_run = bool(latest_run) and (old_run_stopped or stale_due_to_review or stale_due_to_age)
    prefer_fresh_start = bool(latest_run) and not active_processes and pending_count == 0 and (
        latest_review_status in {"blocked", "partial", "observe_only", "awaiting_dataset"}
        or stale_due_to_age
        or (stale_latest_run and latest_review_status == "restart_available")
    )
    stale_reason = None
    if prefer_fresh_start and latest_review_status in {"blocked", "partial", "observe_only", "awaiting_dataset"}:
        stale_reason = f"latest review status is {latest_review_status}"
    elif stale_due_to_review and latest_review_status == "restart_available":
        stale_reason = "latest run stopped and only restart guidance remains"
    elif stale_due_to_age:
        stale_reason = f"latest run is {latest_run_age_hours:.1f} hours old"
    return {
        "resumeAvailable": bool(latest_playbook or latest_run or pending_count),
        "pendingConfirmations": pending_count,
        "pendingConfirmationLabels": [item.get("label") for item in normalized_pending],
        "defaultConfirmationLabel": default_confirmation.get("label") if isinstance(default_confirmation, dict) else None,
        "hasLatestRun": bool(latest_run),
        "hasLatestPlaybook": bool(latest_playbook),
        "lastWorknetId": (
            latest_run_playbook.get("worknetId")
            if isinstance(latest_run_playbook, dict) and latest_run_playbook.get("worknetId") is not None
            else (latest_playbook.get("worknetId") if isinstance(latest_playbook, dict) else None)
        ),
        "lastWorknetKey": last_worknet_key,
        "lastMode": latest_run.get("mode") if isinstance(latest_run, dict) else None,
        "executedStepCount": executed_count,
        "hasRuntimeGuidance": bool(runtime_guidance),
        "runtimeGuidanceMessage": runtime_guidance.get("message") if isinstance(runtime_guidance, dict) else None,
        "runtimeGuidanceNextAction": runtime_guidance.get("nextAction") if isinstance(runtime_guidance, dict) else None,
        "followUpActionCount": len(follow_up_actions),
        "autoRunnableFollowUpCount": sum(1 for item in follow_up_actions if item.get("safeToAutoRun") and not item.get("requiresConfirmation") and item.get("argv")),
        "defaultFollowUpLabel": default_follow_up.get("label") if isinstance(default_follow_up, dict) else None,
        "defaultFollowUpCommand": default_follow_up.get("command") if isinstance(default_follow_up, dict) else None,
        "followUpActions": follow_up_actions,
        "sourceFollowUpLabel": source_follow_up.get("label") if isinstance(source_follow_up, dict) else None,
        "activeBackgroundCount": len(active_processes),
        "activeBackgroundLabels": [item.get("label") for item in active_processes],
        "activeBackgroundProcesses": active_processes,
        "latestRunGeneratedAt": latest_run_generated_at,
        "latestRunAgeHours": round(latest_run_age_hours, 2) if latest_run_age_hours is not None else None,
        "latestReviewStatus": latest_review_status or None,
        "latestReviewStatusDisplay": review_status_display(latest_review_status) if latest_review_status else None,
        "latestReviewHeadline": latest_review_headline,
        "latestReviewWorknetKey": latest_review_worknet_key,
        "latestReviewMatchesLastWorknet": latest_review_matches_last_worknet,
        "oldRunStopped": old_run_stopped,
        "staleLatestRun": stale_latest_run,
        "staleLatestRunReason": stale_reason,
        "preferFreshStartOverResume": prefer_fresh_start,
    }


def build_skill_sync_command(skill_record: dict[str, Any]) -> Optional[dict[str, Any]]:
    status = skill_record.get("status")
    install_uri = skill_record.get("installUri")
    if status not in {"official-remote", "managed-installed"}:
        return None
    if not install_uri or not looks_official_skill_uri(install_uri):
        return None
    return {
        "label": f"sync {skill_record.get('key')} skill",
        "cwd": str(SKILL_ROOT / "scripts"),
        "argv": [
            "python3",
            str(SKILL_ROOT / "scripts" / "manage-skill.py"),
            "--skill-key",
            str(skill_record.get("key")),
            "--uri",
            str(install_uri),
            "--mode",
            "ensure",
        ],
        "category": "install",
        "requires_confirmation": False,
    }


def build_skill_inspect_command(skill_key: str) -> dict[str, Any]:
    return {
        "label": f"inspect {skill_key} skill",
        "cwd": str(SKILL_ROOT / "scripts"),
        "argv": [
            "python3",
            str(SKILL_ROOT / "scripts" / "inspect-skill.py"),
            "--skill-key",
            skill_key,
        ],
        "category": "inspect",
        "requires_confirmation": False,
    }


def runtime_probe(state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    state = state or state_context()
    managed_root = Path(state["skills"]) / "checkouts"
    awp_skill_root = managed_root / "awp-skill"
    awp_wallet_root = managed_root / "awp-wallet"
    generic_skill_path = shutil.which("skill")
    generic_skill_probe = None
    generic_skill_kind = None
    if generic_skill_path:
        generic_skill_probe = command_help_probe(["skill", "--help"])
        text = str(generic_skill_probe.get("text", "")).lower()
        if "expression can be" in text or "signal" in text or "kill processes" in text:
            generic_skill_kind = "linux-process-skill"
        else:
            generic_skill_kind = "unknown-skill-command"

    relay_start = awp_skill_root / "scripts" / "relay-start.py"
    awp_daemon = awp_skill_root / "scripts" / "awp-daemon.py"
    relay_probe = None
    daemon_probe = None
    if relay_start.exists():
        relay_probe = command_help_probe(["python3", str(relay_start), "--help"])
    if awp_daemon.exists():
        daemon_probe = command_help_probe(["python3", str(awp_daemon), "--help"])

    return {
        "generatedAt": now_iso(),
        "gitAvailable": command_exists("git"),
        "python3Available": command_exists("python3"),
        "awpWalletCli": {
            "available": command_exists("awp-wallet"),
            "path": shutil.which("awp-wallet"),
        },
        "awpSkillCli": {
            "available": command_exists("awp-skill"),
            "path": shutil.which("awp-skill"),
        },
        "genericSkillCommand": {
            "available": bool(generic_skill_path),
            "path": generic_skill_path,
            "kind": generic_skill_kind,
            "probe": generic_skill_probe,
        },
        "managedCheckouts": {
            "root": str(managed_root),
            "awpSkill": {
                "path": str(awp_skill_root),
                "exists": awp_skill_root.exists(),
                "relayStartExists": relay_start.exists(),
                "awpDaemonExists": awp_daemon.exists(),
                "relayHelp": relay_probe,
                "daemonHelp": daemon_probe,
            },
            "awpWallet": {
                "path": str(awp_wallet_root),
                "exists": awp_wallet_root.exists(),
            },
        },
    }


def awp_skill_checkout_root(state: Optional[dict[str, Any]] = None) -> Path:
    state = state or state_context()
    return Path(state["skills"]) / "checkouts" / "awp-skill"


def run_awp_skill_preflight(
    state: Optional[dict[str, Any]] = None,
    *,
    address: Optional[str] = None,
) -> dict[str, Any]:
    state = state or state_context()
    root = awp_skill_checkout_root(state)
    script = root / "scripts" / "preflight.py"
    if not script.exists():
        return {
            "available": False,
            "path": str(script),
            "ok": False,
            "result": None,
            "command": None,
            "error": "awp-skill preflight.py not found",
        }
    argv = ["python3", str(script)]
    if address:
        argv.extend(["--address", address])
    result = run_command(argv, cwd=str(root), timeout=60)
    payload = parse_json_loose(result.get("stdout", ""))
    record = {
        "available": True,
        "path": str(script),
        "ok": result.get("ok", False),
        "result": payload if isinstance(payload, dict) else None,
        "command": {
            "argv": argv,
            "cwd": str(root),
            "code": result.get("code"),
            "stderr": trim_output(result.get("stderr", "")),
        },
        "error": None if result.get("ok", False) else trim_output(result.get("stderr", "") or result.get("stdout", "")),
    }
    cache_path = official_preflight_cache_path(state)
    existing = load_json(cache_path, {})
    candidate_result = record.get("result") if isinstance(record.get("result"), dict) else {}
    existing_result = existing.get("result") if isinstance(existing, dict) else {}
    candidate_registered = None
    if isinstance(candidate_result, dict):
        candidate_registered = candidate_result.get("state", {}).get("registered")
    existing_registered = None
    if isinstance(existing_result, dict):
        existing_registered = existing_result.get("state", {}).get("registered")

    should_write = True
    if existing and existing_registered in {True, False} and candidate_registered is None:
        should_write = False
    if should_write:
        atomic_write_json(cache_path, record)
    return record


def build_dependency_command(
    dependency_key: str,
    install_uri: str,
    *,
    category: str = "install",
    requires_confirmation: bool = False,
) -> dict[str, Any]:
    return {
        "label": f"ensure {dependency_key} dependency",
        "cwd": str(SKILL_ROOT / "scripts"),
        "argv": [
            "python3",
            str(SKILL_ROOT / "scripts" / "manage-dependency.py"),
            "--dependency-key",
            dependency_key,
            "--uri",
            install_uri,
            "--mode",
            "ensure",
        ],
        "category": category,
        "requires_confirmation": requires_confirmation,
    }


def build_registration_plan(
    state: Optional[dict[str, Any]] = None,
    wallet: Optional[dict[str, Any]] = None,
    *,
    include_probe: bool = True,
) -> dict[str, Any]:
    state = state or state_context()
    wallet = wallet or awp_wallet_snapshot()
    probe = runtime_probe(state) if include_probe else {}
    official_preflight = (
        run_awp_skill_preflight(state=state, address=wallet.get("address"))
        if include_probe and wallet.get("address")
        else {"available": False, "result": None}
    )
    managed_awp_skill = Path(probe.get("managedCheckouts", {}).get("awpSkill", {}).get("path", ""))
    relay_start = managed_awp_skill / "scripts" / "relay-start.py"

    commands: list[dict[str, Any]] = []
    issues: list[str] = []
    next_action = "install_awp_skill_dependency"

    if not wallet.get("walletReady"):
        issues.append("agent work wallet is not ready")
    if not probe.get("gitAvailable"):
        issues.append("git is not available for managed dependency checkout")
    if probe.get("genericSkillCommand", {}).get("kind") == "linux-process-skill":
        issues.append("system `skill` command is a Linux process-signal utility, not an AWP skill runtime")

    if not probe.get("managedCheckouts", {}).get("awpSkill", {}).get("exists"):
        commands.append(
            build_dependency_command(
                "awp-skill",
                "https://github.com/awp-core/awp-skill",
            )
        )
    elif relay_start.exists():
        commands.append(
            {
                "label": "run awp-skill gasless onboarding",
                "cwd": str(managed_awp_skill),
                "argv": ["python3", str(relay_start), "--mode", "principal"],
                "category": "registration",
                "requires_confirmation": False,
            }
        )
        next_action = "run_awp_skill_registration"
    else:
        issues.append("managed awp-skill checkout exists but relay-start.py was not found")

    if not commands and not issues:
        next_action = "registration_ready"

    plan = {
        "generatedAt": now_iso(),
        "walletReady": wallet.get("walletReady", False),
        "agentAddress": wallet.get("address"),
        "nextAction": next_action,
        "issues": issues,
        "commands": commands,
        "runtimeProbe": probe,
        "awpSkillPreflight": official_preflight,
    }
    preflight_result = official_preflight.get("result") if isinstance(official_preflight, dict) else None
    if isinstance(preflight_result, dict):
        plan["officialNextAction"] = preflight_result.get("nextAction")
        plan["officialMessage"] = preflight_result.get("message")
        if preflight_result.get("nextAction") == "retry_preflight":
            issue = "official awp-skill preflight could not reach the AWP API"
            if issue not in plan["issues"]:
                plan["issues"].append(issue)
            if plan["nextAction"] == "run_awp_skill_registration":
                plan["nextAction"] = "retry_registration_preflight"
    return plan


def recommend_worknet_actions(
    bundle: dict[str, Any],
    *,
    preferences: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    reports = [item for item in bundle.get("reports", []) if isinstance(item, dict)]
    all_runnable = [item for item in reports if item.get("runnable")]
    earning_runnable = [
        item
        for item in reports
        if item.get("runnable")
        and item.get("recommendedRole") not in {"identity", "observer"}
        and item.get("automationLevel") != "manual-only"
    ]
    no_stake = [item for item in earning_runnable if item.get("canStartWithoutStake") is True]
    predict_profile = resolve_worknet("predict")
    mine_profile = resolve_worknet("mine")
    preferred_key = str((preferences or {}).get("preferredWorknet") or "").strip().lower()
    predictable = next(
        (
            item
            for item in reports
            if predict_profile
            and str(item.get("worknetId")) == str(predict_profile.get("worknet_id"))
        ),
        None,
    )
    mine = next(
        (
            item
            for item in reports
            if mine_profile
            and str(item.get("worknetId")) == str(mine_profile.get("worknet_id"))
        ),
        None,
    )
    preferred_profile = resolve_worknet(preferred_key) if preferred_key else None
    preferred = next(
        (
            item
            for item in reports
            if preferred_profile
            and str(item.get("worknetId")) == str(preferred_profile.get("worknet_id"))
        ),
        None,
    )

    recommendation = "建议先完成预检，再决定跑哪个 WorkNet。"
    actions: list[dict[str, Any]] = []
    action_map: dict[str, str] = {}

    def describe_worknet_action(
        profile: dict[str, Any],
        report: Optional[dict[str, Any]],
        *,
        background: bool = False,
        fallback: Optional[str] = None,
    ) -> str:
        report = report if isinstance(report, dict) else {}
        key = str(profile.get("key") or "").strip().lower()
        if background and key == "predict":
            return "让 Predict 先在后台持续观察市场、形成观点，不逐轮打断你。"
        summary = canonical_worknet_switch_summary_text(
            profile,
            runnable=bool(report.get("runnable")),
            can_start_without_stake=report.get("canStartWithoutStake") is True,
        )
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip()
        return f"按 {profile.get('name') or profile.get('key') or '这个 WorkNet'} 的默认节奏继续。"

    preferred_runnable = bool(
        preferred
        and preferred.get("runnable")
        and preferred.get("recommendedRole") not in {"identity", "observer"}
        and preferred.get("automationLevel") != "manual-only"
    )

    if preferred_runnable and preferred_profile and preferred_profile["key"] != "mine":
        preferred_name = str(preferred.get("name") or preferred_profile.get("name") or preferred_profile["key"])
        if preferred_profile["key"] == "predict":
            preferred_summary = describe_worknet_action(preferred_profile, preferred)
            mine_summary = (
                describe_worknet_action(mine_profile, mine)
                if mine_profile and isinstance(mine, dict) and mine.get("runnable")
                else "Mine 仍然是更稳的无质押备选。"
            )
            recommendation = f"你已经把 {preferred_name} 设为默认 WorkNet。{preferred_summary} 如果你现在更想走稳一点的无质押路线，{mine_summary}"
        else:
            recommendation = f"你已经把 {preferred_name} 设为默认 WorkNet。{describe_worknet_action(preferred_profile, preferred)}"
        label = f"只跑 {preferred_name}"
        actions.append(
            {
                "label": label,
                "description": describe_worknet_action(
                    preferred_profile,
                    preferred,
                    fallback="按你保存的默认 WorkNet 优先启动。",
                ),
            }
        )
        action_map[label] = build_playbook_command(str(preferred_profile["key"]))
        if preferred_profile["key"] == "predict":
            actions.append(
                {
                    "label": "启动 Predict 静默循环",
                    "description": describe_worknet_action(
                        preferred_profile,
                        preferred,
                        background=True,
                        fallback="让 Predict 在后台持续运行，不逐轮打断你。",
                    ),
                }
            )
            action_map["启动 Predict 静默循环"] = run_worknet_command("predict", execute=True, auto_advance=True)
        if mine and mine.get("runnable"):
            actions.append(
                {
                    "label": "改回只跑 Mine",
                    "description": describe_worknet_action(
                        mine_profile or resolve_worknet("mine") or {"key": "mine", "name": "Mine WorkNet"},
                        mine,
                        fallback="如果你想回到更稳的无质押数据工作流，可以切回 Mine。",
                    ),
                }
            )
            action_map["改回只跑 Mine"] = build_playbook_command("mine")
    elif mine and mine.get("runnable"):
        predict_ready = bool(predictable and predictable.get("runnable"))
        mine_summary = describe_worknet_action(
            mine_profile or resolve_worknet("mine") or {"key": "mine", "name": "Mine WorkNet"},
            mine,
            fallback="建议先从 Mine 开始。",
        )
        if predict_ready:
            predict_summary = describe_worknet_action(
                predict_profile or resolve_worknet("predict") or {"key": "predict", "name": "Predict WorkNet"},
                predictable,
                background=True,
                fallback="同时把 Predict 挂到静默循环里。",
            )
            recommendation = f"建议先跑 Mine。{mine_summary} 同时，{predict_summary}"
        else:
            recommendation = f"建议先跑 Mine。{mine_summary} Predict 先观察 24 小时更稳。"
        actions.append(
            {
                "label": "只跑 Mine",
                "description": describe_worknet_action(
                    mine_profile or resolve_worknet("mine") or {"key": "mine", "name": "Mine WorkNet"},
                    mine,
                    fallback="先从无质押的数据工作流开始。",
                ),
            }
        )
        action_map["只跑 Mine"] = build_playbook_command("mine")
        if predict_ready:
            actions.append(
                {
                    "label": "启动 Predict 静默循环",
                    "description": describe_worknet_action(
                        predict_profile or resolve_worknet("predict") or {"key": "predict", "name": "Predict WorkNet"},
                        predictable,
                        background=True,
                        fallback="让 Predict 在后台持续运行，不逐轮打断你。",
                    ),
                }
            )
            action_map["启动 Predict 静默循环"] = run_worknet_command("predict", execute=True, auto_advance=True)
    elif no_stake:
        first = no_stake[0]
        first_profile = resolve_worknet(str(first.get("worknetId") or first.get("name") or ""))
        recommendation = f"建议先跑 {first.get('name')}。{describe_worknet_action(first_profile or {'key': first.get('name'), 'name': first.get('name')}, first, fallback='因为它当前不需要 stake。')}"
        label = f"只跑 {first.get('name')}"
        actions.append(
            {
                "label": label,
                "description": describe_worknet_action(
                    first_profile or {"key": first.get("name"), "name": first.get("name")},
                    first,
                    fallback="先从当前最容易启动的工作流开始。",
                ),
            }
        )
        action_map[label] = build_playbook_command(str(first.get("worknetId")))
    elif mine and str(mine.get("cliStatus")) == "runtime-error":
        recommendation = "建议先修复 Mine 运行时，再决定是否切到需要安装官方 runtime 的其他 WorkNet。"
        actions.append(
            {
                "label": "检查 Mine 运行时",
                "description": "先看本地 Mine 运行时为什么没有通过自检。",
            }
        )
        action_map["检查 Mine 运行时"] = "python3 scripts/inspect-skill.py --skill-key mine"
        remediation_commands = mine.get("skillInspection", {}).get("remediationCommands", [])
        if isinstance(remediation_commands, list) and remediation_commands:
            command = remediation_commands[0]
            label = "修复 Mine 运行时"
            actions.insert(
                0,
                {
                    "label": label,
                    "description": "按检测到的环境问题优先修复 Mine 本地运行时。",
                },
            )
            action_map[label] = " ".join(str(item) for item in command.get("argv", []))

    if predictable and not predictable.get("runnable"):
        actions.append(
            {
                "label": "观察 Predict",
                "description": describe_worknet_action(
                    predict_profile or resolve_worknet("predict") or {"key": "predict", "name": "Predict WorkNet"},
                    predictable,
                    fallback="先整理预测市场上下文，等官方 runtime 明确后再执行。",
                ),
            }
        )
        action_map["观察 Predict"] = query_knowledge_command("predict")

    if not actions:
        actions.append(
            {
                "label": "查看 WorkNet 档案",
                "description": "先理解每个 WorkNet 的要求和风险。",
            }
        )
        action_map["查看 WorkNet 档案"] = "python3 scripts/query-knowledge.py --topic protocol-core"

    return {
        "recommendation": recommendation,
        "actions": actions,
        "actionMap": action_map,
        "runnableCount": len(all_runnable),
        "earningRunnableCount": len(earning_runnable),
        "supportRunnableCount": max(0, len(all_runnable) - len(earning_runnable)),
        "noStakeRunnableCount": len(no_stake),
    }


def build_source_inventory(state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    state = state or state_context()
    local_sources = discover_local_sources()
    local_by_key = {item["key"]: item for item in local_sources}
    missing = [item["key"] for item in local_sources if not item.get("available")]
    managed_root = Path(state["skills"]) / "checkouts"
    managed_status = {
        key: (managed_root / key).exists()
        for key in ("predict", "gov", "ardi", "tmr", "community", "awp-skill")
    }
    known_gaps: list[str] = []
    if not managed_status["predict"]:
        known_gaps.append(
            "No local Predict runtime is installed yet, even though the official prediction-skill URI is now confirmed."
        )
    missing_managed = [
        key
        for key in ("gov", "tmr", "community")
        if not managed_status.get(key, False)
    ]
    if missing_managed:
        label_map = {"gov": "Gov", "tmr": "TMR", "community": "Community"}
        known_gaps.append(
            "No local "
            + ", ".join(label_map[key] for key in missing_managed)
            + " runtime is installed yet."
        )
    empty_managed = [
        key
        for key in ("tmr", "community")
        if managed_status.get(key, False) and repository_is_effectively_empty(managed_root / key)
    ]
    if empty_managed:
        label_map = {"tmr": "TMR", "community": "Community"}
        known_gaps.append(
            "Some official worknet skills are installed locally but currently only expose license or metadata files: "
            + ", ".join(label_map[key] for key in empty_managed)
            + "."
        )
    known_gaps.append(
        "Some official worknet skills are discoverable via live API but still sparse as public operator docs or raw SKILL snapshots."
    )
    return {
        "generatedAt": now_iso(),
        "officialWebSources": OFFICIAL_WEB_SOURCES,
        "localSources": local_sources,
        "localSourceKeys": list(local_by_key.keys()),
        "missingLocalSources": missing,
        "sourceCoverage": {
            "officialSourceCount": len(OFFICIAL_WEB_SOURCES),
            "localSourceCount": len(local_sources),
            "worknetProfiles": [profile["key"] for profile in KNOWN_WORKNETS],
        },
        "knownGaps": known_gaps,
    }


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


def source_drift_report_path(state: dict[str, Any]) -> Path:
    return Path(state["cache"]) / "source-drift.json"


def snapshot_results_map(snapshot: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return {}
    results = snapshot.get("results")
    if not isinstance(results, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in results:
        if isinstance(item, dict) and isinstance(item.get("key"), str):
            mapped[str(item["key"])] = item
    return mapped


def build_source_drift_report(
    *,
    state: Optional[dict[str, Any]] = None,
    current_snapshot: Optional[dict[str, Any]] = None,
    previous_snapshot: Any = None,
) -> dict[str, Any]:
    state = state or state_context()
    current_snapshot = current_snapshot or load_json(Path(state["cache"]) / "source-snapshot.json", {})
    if previous_snapshot is None:
        previous_snapshot = load_json(Path(state["cache"]) / "source-snapshot.previous.json", None)
    current_map = snapshot_results_map(current_snapshot)
    previous_map = snapshot_results_map(previous_snapshot)
    items: list[dict[str, Any]] = []
    all_keys = sorted(set(current_map.keys()) | set(previous_map.keys()))
    changed = 0
    content_changed = 0
    availability_changed = 0
    unreachable = 0
    for key in all_keys:
        current = current_map.get(key)
        previous = previous_map.get(key)
        name = (
            current.get("name")
            if isinstance(current, dict) and current.get("name")
            else (previous.get("name") if isinstance(previous, dict) else key)
        )
        status = "unchanged"
        changed_fields: list[str] = []
        note = None
        if previous is None:
            status = "no-baseline"
            note = "这个来源键当前还没有上一版快照可供比较。"
        elif current is None:
            status = "missing-current"
            changed_fields.append("results")
            note = "上一版快照里有这个来源键，但当前快照里已经没有了。"
        else:
            if bool(previous.get("ok")) != bool(current.get("ok")):
                changed_fields.append("availability")
            if previous.get("status") != current.get("status"):
                changed_fields.append("http_status")
            if previous.get("contentType") != current.get("contentType"):
                changed_fields.append("content_type")
            if previous.get("sha256") != current.get("sha256"):
                changed_fields.append("sha256")
            if previous.get("bytes") != current.get("bytes"):
                changed_fields.append("bytes")
            if previous.get("error") != current.get("error"):
                changed_fields.append("error")
            if "availability" in changed_fields:
                status = "availability_changed"
            elif any(field in changed_fields for field in ("sha256", "bytes", "content_type")):
                status = "content_changed"
            elif changed_fields:
                status = "metadata_changed"
            if status == "availability_changed":
                note = "这个来源从可访问变成不可访问，或者反过来。"
            elif status == "content_changed":
                note = "和上一版快照相比，抓取内容的哈希或字节大小发生了变化。"
            elif status == "metadata_changed":
                note = "即使内容哈希可能没变，HTTP 元数据也已经发生变化。"
        if status != "unchanged":
            changed += 1
        if status == "content_changed":
            content_changed += 1
        if status == "availability_changed":
            availability_changed += 1
        if isinstance(current, dict) and not current.get("ok"):
            unreachable += 1
        items.append(
            {
                "key": key,
                "name": name,
                "status": status,
                "changedFields": changed_fields,
                "note": note,
                "previous": {
                    "ok": previous.get("ok") if isinstance(previous, dict) else None,
                    "status": previous.get("status") if isinstance(previous, dict) else None,
                    "sha256": previous.get("sha256") if isinstance(previous, dict) else None,
                    "bytes": previous.get("bytes") if isinstance(previous, dict) else None,
                    "fetchedAt": previous.get("fetchedAt") if isinstance(previous, dict) else None,
                },
                "current": {
                    "ok": current.get("ok") if isinstance(current, dict) else None,
                    "status": current.get("status") if isinstance(current, dict) else None,
                    "sha256": current.get("sha256") if isinstance(current, dict) else None,
                    "bytes": current.get("bytes") if isinstance(current, dict) else None,
                    "fetchedAt": current.get("fetchedAt") if isinstance(current, dict) else None,
                },
            }
        )
    report = {
        "generatedAt": now_iso(),
        "baselineGeneratedAt": previous_snapshot.get("generatedAt") if isinstance(previous_snapshot, dict) else None,
        "currentGeneratedAt": current_snapshot.get("generatedAt") if isinstance(current_snapshot, dict) else None,
        "baselineAvailable": bool(previous_map),
        "summary": {
            "trackedSources": len(items),
            "changedSources": changed,
            "contentChanged": content_changed,
            "availabilityChanged": availability_changed,
            "currentlyUnreachable": unreachable,
        },
        "items": items,
    }
    if isinstance(previous_snapshot, dict):
        atomic_write_json(Path(state["cache"]) / "source-snapshot.previous.json", previous_snapshot)
    atomic_write_json(source_drift_report_path(state), report)
    write_reference_export("source-drift.json", report)
    return report


def load_cached_source_drift(state: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    state = state or state_context()
    payload = load_json(source_drift_report_path(state), None)
    return payload if isinstance(payload, dict) else None


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
                    "重读受影响的上游来源，并重新核对关联主题、事实和运行时指引。"
                    if impacted_dossiers or impacted_facts or impacted_evidence or impacted_worknets
                    else "来源已经发生变化，但本地还没有任何主题、事实、证据或 WorkNet 映射指向它。"
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


def resolve_worknet(identifier: str) -> Optional[dict[str, Any]]:
    text = identifier.strip().lower()
    for item in KNOWN_WORKNETS:
        if text == item["key"]:
            return item
        if text == str(item["worknet_id"]).lower():
            return item
        if text == item["name"].lower():
            return item
        if text in {alias.lower() for alias in item.get("aliases", [])}:
            return item
    return None


def awp_wallet_snapshot() -> dict[str, Any]:
    if not command_exists("awp-wallet"):
        return {
            "installed": False,
            "walletReady": False,
            "address": None,
            "receive": None,
            "status": None,
            "chains": None,
            "error": "awp-wallet not found in PATH",
        }
    status = run_command(["awp-wallet", "status"])
    receive = run_command(["awp-wallet", "receive"])
    chains = run_command(["awp-wallet", "chains"])
    status_payload = parse_json_loose(status["stdout"])
    receive_payload = parse_json_loose(receive["stdout"])
    chains_payload = parse_json_loose(chains["stdout"])
    address = None
    if isinstance(status_payload, dict):
        address = status_payload.get("address")
    if not address and isinstance(receive_payload, dict):
        address = receive_payload.get("eoaAddress") or receive_payload.get("address")
    return {
        "installed": True,
        "walletReady": bool(address),
        "address": address,
        "receive": receive_payload,
        "status": status_payload,
        "chains": chains_payload,
        "statusCommand": status,
        "receiveCommand": receive,
        "chainsCommand": chains,
        "error": None if address else "wallet address not detected",
    }


def infer_runnable(profile: dict[str, Any], local_source: Optional[dict[str, Any]]) -> bool:
    if local_source and local_source.get("available") and profile["key"] in {"mine", "kya"}:
        return True
    return False


def inspection_status_blocks_runtime(status: str) -> bool:
    return status in {
        "runtime-error",
        "installed-needs-bootstrap",
        "partial",
        "missing",
        "remote-profile-only",
        "network-blocked",
        "empty-official-repo",
    }


def inspection_status_enables_runtime(status: str) -> bool:
    return status == "ready"


def humanize_skill_inspection_status(status: Any) -> Optional[str]:
    code = str(status or "").strip().lower()
    if not code:
        return None
    mapping = {
        "ready": "已就绪",
        "runtime-error": "运行时报错",
        "installed-needs-bootstrap": "还要补初始化",
        "partial": "部分已就绪",
        "missing": "缺少本地运行环境",
        "remote-profile-only": "只有远程资料",
        "network-blocked": "网络受阻",
        "empty-official-repo": "官方仓库为空",
    }
    return mapping.get(code, code)


def fallback_capability_reports(
    inventory: dict[str, Any], state: Optional[dict[str, Any]] = None
) -> list[dict[str, Any]]:
    state = state or state_context()
    preferences = ensure_user_preferences(state)
    local_by_key = {
        item["key"]: item for item in inventory.get("localSources", []) if isinstance(item, dict)
    }
    skill_registry = {
        item["key"]: item for item in skill_registry_from_inventory(inventory, state=state)
    }
    skill_inspections = {
        item["skillKey"]: item
        for item in build_skill_inspection_catalog(state=state, inventory=inventory).get("inspections", [])
        if isinstance(item, dict)
    }
    reports: list[dict[str, Any]] = []
    for profile in KNOWN_WORKNETS:
        local_source = local_by_key.get(profile.get("local_source_key"))
        local_skill_path: Optional[str] = None
        skill_root: Optional[Path] = None
        if local_source and local_source.get("available"):
            skill_root = Path(str(local_source["path"]))
            local_skill_path = str(skill_root / "SKILL.md")
        inspection = skill_inspections.get(profile["key"], {})
        skills_uri = profile.get("skills_uri")
        official_skill = looks_official_skill_uri(profile.get("install_uri") or skills_uri)
        inspection_status = str(inspection.get("status", "missing"))
        manifest = official_remote_manifest(profile["key"])
        execution_blockers = runtime_probe_blockers(profile["key"], inspection)
        predict_loop_is_ready = profile["key"] == "predict" and predict_loop_ready(state, inspection)
        runnable = infer_runnable(profile, local_source)
        runtime_ready_for_execution = inspection_status_enables_runtime(inspection_status) and (
            inspection.get("scriptCount", 0) > 0
            or bool(manifest.get("binaryRuntime"))
        )
        if runtime_ready_for_execution:
            runnable = runnable or profile["key"] in {"gov", "ardi", "predict", "tmr", "community", "mine", "kya"}
        if inspection_status_blocks_runtime(inspection_status):
            runnable = False
        if execution_blockers and not predict_loop_is_ready:
            runnable = False
        predict_observe_hours = int(preferences.get("observeBeforePredictHours", 24) or 0)
        if profile["key"] == "predict" and predict_loop_is_ready:
            runnable = True
        can_start_without_stake = True if profile["key"] == "predict" and predict_loop_is_ready else profile["min_stake"] in (None, 0)
        reason_parts = [canonical_worknet_scan_reason(profile, runnable=runnable, can_start_without_stake=can_start_without_stake) or profile.get("goal", "")]
        install_status = skill_registry.get(profile["key"], {}).get("status")
        if local_source and local_source.get("available"):
            reason_parts.append(f"local source present at {local_source['path']}")
        elif install_status == "managed-installed":
            reason_parts.append("official runtime checkout is installed locally")
        elif profile.get("install_uri"):
            reason_parts.append("official install URI known, but runtime not installed locally")
        else:
            reason_parts.append("no verified local runtime found")
        if inspection_status == "runtime-error":
            probe_labels = [
                str(item.get("label"))
                for item in inspection.get("probeResults", [])
                if isinstance(item, dict) and item.get("ok") is False
            ]
            if probe_labels:
                reason_parts.append("runtime probe failed for " + ", ".join(probe_labels))
            else:
                reason_parts.append("runtime probe failed")
        elif inspection_status == "installed-needs-bootstrap":
            reason_parts.append("runtime exists but still needs bootstrap before safe execution")
        elif inspection_status == "remote-profile-only":
            reason_parts.append("workstation only has remote runtime guidance, not a local install")
        elif inspection_status == "network-blocked":
            reason_parts.append("local runtime is present, but its live probes are blocked by the current network environment")
        elif inspection_status == "empty-official-repo":
            reason_parts.append("official runtime checkout currently only exposes license or metadata files, so there is nothing safe to auto-run yet")
        if profile["key"] == "predict" and predict_loop_is_ready and predict_observe_hours > 0:
            reason_parts.append(f"user preference still suggests observing Predict outcomes for the first {predict_observe_hours} hours even though the official loop can start now")
            reason_parts.append("Predict can start with virtual chips now; staking remains an enhancement path rather than a hard prerequisite for the loop")
        if profile["key"] == "predict" and predict_loop_is_ready:
            if execution_blockers:
                reason_parts.append("If you want the stake-backed path later, use the official staking or KYA route and then re-run Predict stake checks")
        else:
            reason_parts.extend(execution_blockers)
        normalized_reason_parts = [
            humanize_capability_reason_part(part)
            for part in reason_parts
            if isinstance(part, str) and str(part).strip()
        ]
        primary_reason = str(normalized_reason_parts[0] or "").strip() if normalized_reason_parts else ""
        technical_reason = join_product_sentences(normalized_reason_parts[1:])
        public_reason = primary_reason
        if technical_reason:
            public_reason = (
                f"{strip_sentence_end(primary_reason)}。 技术补充：{technical_reason}"
                if primary_reason
                else technical_reason
            )
        reports.append(
            {
                "worknetId": profile["worknet_id"],
                "name": profile["name"],
                "symbol": profile["symbol"],
                "status": profile["status"],
                "skillsUri": skills_uri,
                "officialSkill": official_skill,
                "minStake": profile["min_stake"],
                "runnable": runnable,
                "automationLevel": profile["automation_level"],
                "riskLevel": profile["risk_level"],
                "recommendedRole": profile["recommended_role"],
                "reason": public_reason,
                "localSkillPath": local_skill_path,
                "installStatus": skill_registry.get(profile["key"], {}).get("status"),
                "apiStatus": "unknown",
                "cliStatus": inspection_status,
                "canStartWithoutStake": can_start_without_stake,
                "safeLongRun": runnable and profile["key"] == "mine",
                "skillInspection": inspection,
            }
        )
    return reports


def match_profile_from_rpc(entry: dict[str, Any]) -> Optional[dict[str, Any]]:
    candidate_values = [
        str(first_present(entry, ["worknetId", "id", "worknet_id", "subnetId"], "")).lower(),
        str(first_present(entry, ["name"], "")).lower(),
        str(first_present(entry, ["symbol", "tokenSymbol"], "")).lower(),
    ]
    normalized_candidates = {normalize_worknet_token(value) for value in candidate_values if value}
    for profile in KNOWN_WORKNETS:
        aliases = {profile["key"], str(profile["worknet_id"]).lower(), profile["name"].lower()}
        aliases.update(alias.lower() for alias in profile.get("aliases", []))
        normalized_aliases = {normalize_worknet_token(value) for value in aliases if value}
        if any(value and value in aliases for value in candidate_values):
            return profile
        if normalized_candidates.intersection(normalized_aliases):
            return profile
    return None


def resolve_live_worknet_id(
    entry: dict[str, Any],
    profile: Optional[dict[str, Any]],
    auxiliary_candidates: Optional[list[dict[str, Any]]] = None,
) -> tuple[Any, str, list[dict[str, Any]]]:
    observed = normalize_worknet_id(first_present(entry, ["worknetId", "id", "worknet_id", "subnetId"]))
    if profile:
        canonical = normalize_worknet_id(profile.get("worknet_id"))
        predecessor_ids = {
            normalize_worknet_id(value)
            for value in profile.get("predecessor_worknet_ids", [])
            if normalize_worknet_id(value) not in (None, "")
        }
        if canonical not in (None, "") and observed in predecessor_ids:
            return canonical, "profile-successor", [
                {
                    "query": "entry",
                    "ok": True,
                    "match": "predecessor_worknet_id",
                    "candidateId": observed,
                    "promotedId": canonical,
                }
            ]
    if observed not in (None, ""):
        return observed, "entry", []
    if profile and str(profile.get("worknet_id", "")).isdigit():
        return str(profile["worknet_id"]), "profile", []

    auxiliary_candidates = auxiliary_candidates or []
    search_queries = []
    name = str(first_present(entry, ["name"], "")).strip()
    symbol = str(first_present(entry, ["symbol", "tokenSymbol"], "")).strip()
    if name:
        search_queries.append(name)
    if symbol:
        search_queries.append(symbol)
    if profile:
        for candidate in [
            profile.get("name", ""),
            profile.get("key", ""),
            *profile.get("aliases", []),
            profile.get("symbol", ""),
        ]:
            text = str(candidate or "").strip()
            if text and text not in search_queries:
                search_queries.append(text)

    normalized_name = normalize_worknet_token(name)
    normalized_symbol = normalize_worknet_token(symbol)
    for candidate in auxiliary_candidates:
        cid = normalize_worknet_id(first_present(candidate, ["worknetId", "id", "worknet_id", "subnetId"]))
        if cid in (None, ""):
            continue
        cname = normalize_worknet_token(str(first_present(candidate, ["name"], "")))
        csymbol = normalize_worknet_token(str(first_present(candidate, ["symbol", "tokenSymbol"], "")))
        if normalized_name and cname == normalized_name:
            return cid, "ranked-name", [{"query": "listRanked", "ok": True, "match": "name", "candidateId": cid}]
        if normalized_symbol and csymbol == normalized_symbol:
            return cid, "ranked-symbol", [{"query": "listRanked", "ok": True, "match": "symbol", "candidateId": cid}]

    search_attempts: list[dict[str, Any]] = []
    for query in search_queries:
        response = rpc_call("worknets.search", params={"query": query, "limit": 20})
        if not response.get("ok"):
            search_attempts.append({"query": query, "ok": False, "error": response.get("error")})
            continue
        candidates = normalize_search_entries(response.get("body"))
        ranked: list[tuple[int, dict[str, Any]]] = []
        for candidate in candidates:
            cid = normalize_worknet_id(first_present(candidate, ["worknetId", "id", "worknet_id", "subnetId"]))
            if cid in (None, ""):
                continue
            score = 0
            cname = normalize_worknet_token(str(first_present(candidate, ["name"], "")))
            csymbol = normalize_worknet_token(str(first_present(candidate, ["symbol", "tokenSymbol"], "")))
            if normalized_name and cname == normalized_name:
                score += 100
            if normalized_symbol and csymbol == normalized_symbol:
                score += 80
            if profile and str(profile.get("worknet_id", "")) == str(cid):
                score += 200
            if score > 0:
                ranked.append((score, candidate))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        search_attempts.append(
            {
                "query": query,
                "ok": True,
                "candidateCount": len(candidates),
                "rankedCount": len(ranked),
                "topCandidateId": normalize_worknet_id(first_present(ranked[0][1], ["worknetId", "id", "worknet_id", "subnetId"])) if ranked else None,
            }
        )
        if ranked:
            chosen = ranked[0][1]
            cid = normalize_worknet_id(first_present(chosen, ["worknetId", "id", "worknet_id", "subnetId"]))
            if cid not in (None, ""):
                return cid, f"search:{query}", search_attempts
    return None, "unresolved", search_attempts


def resolution_confidence(resolved_via: str) -> str:
    if resolved_via == "entry":
        return "high"
    if resolved_via == "profile-successor":
        return "medium"
    if resolved_via == "profile":
        return "medium"
    if resolved_via.startswith("ranked"):
        return "medium"
    if resolved_via.startswith("search:"):
        return "medium"
    return "low"


def enrich_reports_with_rpc(
    reports: list[dict[str, Any]], inventory: dict[str, Any], agent_address: Optional[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rpc_meta: dict[str, Any] = {"used": False, "errors": []}
    response = rpc_call("worknets.list", params={})
    if not response.get("ok"):
        rpc_meta["errors"].append(trim_output(response.get("error")))
        return reports, rpc_meta
    entries = normalize_worknet_entries(response.get("body"))
    if not entries:
        rpc_meta["errors"].append("worknets.list returned no usable entries")
        return reports, rpc_meta
    by_name = {item["name"]: item for item in reports}
    by_id = {str(item["worknetId"]): item for item in reports}
    for entry in entries:
        profile = match_profile_from_rpc(entry)
        existing = None
        entry_id = first_present(entry, ["worknetId", "id", "worknet_id", "subnetId"])
        entry_name = first_present(entry, ["name"], "Unknown WorkNet")
        if entry_id is not None and str(entry_id) in by_id:
            existing = by_id[str(entry_id)]
        elif entry_name in by_name:
            existing = by_name[entry_name]
        if existing is None:
            existing = {
                "worknetId": entry_id or f"unknown:{entry_name.lower().replace(' ', '-')}",
                "name": entry_name,
                "symbol": first_present(entry, ["symbol", "tokenSymbol"], "UNKNOWN"),
                "status": first_present(entry, ["status", "state"], "unknown"),
                "skillsUri": first_present(entry, ["skillsUri", "skillsURI", "skillUri", "skillURI"]),
                "officialSkill": False,
                "minStake": first_present(entry, ["minStake", "min_stake"]),
                "runnable": False,
                "automationLevel": "unknown",
                "riskLevel": "unknown",
                "recommendedRole": "observer",
                "reason": "discovered through live RPC, not yet profiled by the workstation",
                "localSkillPath": None,
                "installStatus": None,
                "apiStatus": "ready",
                "cliStatus": "unknown",
                "canStartWithoutStake": None,
                "safeLongRun": False,
            }
            reports.append(existing)
            by_id[str(existing["worknetId"])] = existing
        existing["worknetId"] = entry_id or existing["worknetId"]
        existing["name"] = entry_name
        existing["symbol"] = first_present(entry, ["symbol", "tokenSymbol"], existing["symbol"])
        existing["status"] = first_present(entry, ["status", "state"], existing["status"])
        existing["skillsUri"] = first_present(
            entry,
            ["skillsUri", "skillsURI", "skillUri", "skillURI"],
            existing["skillsUri"],
        )
        existing["minStake"] = first_present(entry, ["minStake", "min_stake"], existing["minStake"])
        existing["officialSkill"] = looks_official_skill_uri(existing.get("skillsUri")) or existing.get("officialSkill", False)
        existing["apiStatus"] = "ready"
        if existing.get("canStartWithoutStake") is None:
            existing["canStartWithoutStake"] = existing.get("minStake") in (None, 0)
        if profile:
            existing["automationLevel"] = profile["automation_level"]
            existing["riskLevel"] = profile["risk_level"]
            existing["recommendedRole"] = profile["recommended_role"]
            existing["safeLongRun"] = bool(existing.get("runnable")) and profile["key"] == "mine"
        diagnostics: dict[str, Any] = {}
        if entry_id is not None:
            skills_call = rpc_try_many(
                "worknets.getSkills",
                [{"worknetId": entry_id}, {"id": entry_id}],
            )
            if skills_call.get("ok"):
                diagnostics["skills"] = trim_output(rpc_result_body(skills_call["body"]))
            token_call = rpc_try_many(
                "tokens.getWorknetTokenPrice",
                [{"worknetId": entry_id}, {"id": entry_id}, {"symbol": existing["symbol"]}],
            )
            if token_call.get("ok"):
                diagnostics["tokenPrice"] = trim_output(rpc_result_body(token_call["body"]))
            if agent_address:
                agent_call = rpc_try_many(
                    "staking.getAgentInfo",
                    [
                        {"worknetId": entry_id, "agentAddress": agent_address},
                        {"id": entry_id, "agent": agent_address},
                    ],
                )
                if agent_call.get("ok"):
                    diagnostics["agentInfo"] = trim_output(rpc_result_body(agent_call["body"]))
                earnings_call = rpc_try_many(
                    "worknets.getEarnings",
                    [
                        {"worknetId": entry_id, "agentAddress": agent_address},
                        {"id": entry_id, "agent": agent_address},
                    ],
                )
                if earnings_call.get("ok"):
                    diagnostics["earnings"] = trim_output(rpc_result_body(earnings_call["body"]))
        if diagnostics:
            existing["rpcDiagnostics"] = diagnostics
    rpc_meta["used"] = True
    rpc_meta["entryCount"] = len(entries)
    return reports, rpc_meta


def enrich_reports_with_cached_live_worknets(
    reports: list[dict[str, Any]], snapshot: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta: dict[str, Any] = {
        "used": True,
        "source": "official-live-worknets-cache",
        "generatedAt": snapshot.get("generatedAt"),
        "entryCount": len(snapshot.get("entries", [])),
        "errors": snapshot.get("errors", []),
    }
    by_name = {item["name"]: item for item in reports}
    by_id = {str(item["worknetId"]): item for item in reports}

    for entry in snapshot.get("entries", []):
        if not isinstance(entry, dict):
            continue
        profile = match_profile_from_rpc(entry)
        wid = normalize_worknet_id(entry.get("worknetId")) or (profile["worknet_id"] if profile else None)
        name = entry.get("name", "Unknown WorkNet")
        observed_name = entry.get("observedName", name)
        existing = None
        if wid is not None and str(wid) in by_id:
            existing = by_id[str(wid)]
        elif name in by_name:
            existing = by_name[name]
        else:
            existing = {
                "worknetId": wid or f"unknown:{safe_slug(str(name))}",
                "name": profile["name"] if profile else name,
                "symbol": entry.get("symbol", "UNKNOWN"),
                "status": entry.get("status", "unknown"),
                "skillsUri": entry.get("skillsUri"),
                "officialSkill": entry.get("officialSkill", False),
                "minStake": entry.get("minStake"),
                "runnable": False,
                "automationLevel": "unknown",
                "riskLevel": "unknown",
                "recommendedRole": "observer",
                "reason": "discovered from cached live official worknet scan",
            }
            reports.append(existing)
        existing["worknetId"] = wid or existing["worknetId"]
        existing["observedName"] = observed_name
        if entry.get("observedWorknetId") not in (None, ""):
            existing["observedWorknetId"] = entry.get("observedWorknetId")
        existing["resolvedVia"] = entry.get("resolvedVia", existing.get("resolvedVia"))
        existing["resolutionConfidence"] = entry.get(
            "resolutionConfidence",
            existing.get("resolutionConfidence", "low"),
        )
        if not profile:
            existing["name"] = name
        existing["symbol"] = entry.get("symbol", existing.get("symbol"))
        existing["status"] = entry.get("status", existing.get("status"))
        observed_skills_uri = entry.get("skillsUri")
        if observed_skills_uri not in (None, ""):
            existing["observedSkillsUri"] = observed_skills_uri
        canonical_skills_uri = profile.get("skills_uri") or profile.get("install_uri") if profile else None
        if canonical_skills_uri:
            existing["skillsUri"] = canonical_skills_uri
        elif profile and profile.get("key") == "predict" and isinstance(observed_skills_uri, str) and "mine-skill" in observed_skills_uri:
            existing["skillsUri"] = None
            existing["liveWarnings"] = list({*(existing.get("liveWarnings", [])), "observed skillsUri looked mismatched for Predict and was not promoted"})
            existing["officialSkill"] = False
        elif observed_skills_uri not in (None, ""):
            existing["skillsUri"] = observed_skills_uri
        if existing.get("skillsUri") is not None:
            existing["officialSkill"] = looks_official_skill_uri(existing.get("skillsUri")) or bool(entry.get("officialSkill"))

        observed_min_stake = entry.get("minStake")
        existing["observedMinStake"] = observed_min_stake
        canonical_min_stake = profile.get("min_stake") if profile else existing.get("minStake")
        if canonical_min_stake is not None and observed_min_stake not in (None, ""):
            try:
                existing["minStake"] = max(int(canonical_min_stake), int(observed_min_stake))
            except (TypeError, ValueError):
                existing["minStake"] = canonical_min_stake
        elif observed_min_stake not in (None, ""):
            existing["minStake"] = observed_min_stake
        else:
            existing["minStake"] = canonical_min_stake
        existing["apiStatus"] = "cached-live"
        if existing.get("canStartWithoutStake") is None:
            existing["canStartWithoutStake"] = existing.get("minStake") in (None, 0, "0")
        if profile:
            existing["automationLevel"] = profile["automation_level"]
            existing["riskLevel"] = profile["risk_level"]
            existing["recommendedRole"] = profile["recommended_role"]
            existing["safeLongRun"] = bool(existing.get("runnable")) and profile["key"] == "mine"
        diagnostics = {}
        if entry.get("tokenPrice") is not None:
            diagnostics["tokenPrice"] = entry.get("tokenPrice")
        if entry.get("agentInfo") is not None:
            diagnostics["agentInfo"] = entry.get("agentInfo")
        if entry.get("earnings") is not None:
            diagnostics["earnings"] = entry.get("earnings")
        if diagnostics:
            existing["rpcDiagnostics"] = diagnostics
    return reports, meta


def build_capability_bundle() -> dict[str, Any]:
    state = state_context()
    inventory = build_source_inventory()
    preferences = ensure_user_preferences(state)
    wallet = awp_wallet_snapshot()
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    skill_inspections = build_skill_inspection_catalog(state=state, inventory=inventory)
    reports = fallback_capability_reports(inventory, state=state)
    cached_live = load_cached_live_worknets(state)
    if cached_live:
        reports, rpc_meta = enrich_reports_with_cached_live_worknets(reports, cached_live)
        source_mode = "live-cache"
    else:
        reports, rpc_meta = enrich_reports_with_rpc(reports, inventory, wallet.get("address"))
        source_mode = "rpc" if rpc_meta.get("used") else "catalog"
    reports = attach_knowledge_to_capability_reports(reports, catalog=knowledge_catalog)
    reports = [
        (
            {
                **item,
                **derive_capability_execution_state(item),
                "resumeStatus": None,
                "resumeStatusDisplay": None,
            }
            if isinstance(item, dict)
            else item
        )
        for item in reports
    ]
    skill_registry = skill_registry_from_inventory(inventory, state=state)
    bundle = annotate_capability_bundle_payload({
        "generatedAt": now_iso(),
        "sourceMode": source_mode,
        "rpc": rpc_meta,
        "inventory": inventory,
        "skillRegistry": skill_registry,
        "skillInspections": skill_inspections["inspections"],
        "userPreferences": preferences,
        "reports": reports,
    })
    atomic_write_json(Path(state["cache"]) / "source-inventory.json", inventory)
    atomic_write_json(Path(state["skills"]) / "install-status.json", skill_registry)
    atomic_write_json(Path(state["cache"]) / "capability-scan.json", bundle)
    write_reference_export("source-inventory.json", inventory)
    write_reference_export("skill-registry.json", skill_registry)
    write_reference_export("skill-inspections.json", skill_inspections)
    write_reference_export("capability-catalog.json", bundle)
    return bundle


def load_cached_capability_bundle(state: dict[str, Any]) -> Optional[dict[str, Any]]:
    payload = load_json(Path(state["cache"]) / "capability-scan.json", None)
    if not isinstance(payload, dict):
        return None
    reports = payload.get("reports")
    if not isinstance(reports, list):
        return None
    return annotate_capability_bundle_payload(payload)


def probe_registration(bundle: dict[str, Any], agent_address: Optional[str]) -> tuple[Optional[bool], Optional[str], list[str]]:
    if not agent_address:
        return None, None, ["agent address missing"]
    issues: list[str] = []
    for report in bundle.get("reports", []):
        diagnostics = report.get("rpcDiagnostics")
        if not isinstance(diagnostics, dict):
            continue
        agent_info = diagnostics.get("agentInfo")
        if not isinstance(agent_info, dict):
            continue
        recipient = first_present(agent_info, ["recipient", "rewardRecipient", "resolvedRecipient"])
        stake = first_present(agent_info, ["stake", "allocatedStake", "allocation"])
        if recipient or stake:
            return True, recipient, issues
    if bundle.get("rpc", {}).get("used"):
        return False, None, issues
    issues.append("live RPC unavailable; registration status is unknown")
    return None, None, issues


def probe_cached_official_registration(state: dict[str, Any]) -> tuple[Optional[bool], Optional[str], Optional[dict[str, Any]]]:
    payload = load_json(official_preflight_cache_path(state), {})
    if not isinstance(payload, dict):
        return None, None, None
    result = payload.get("result")
    if not isinstance(result, dict):
        return None, None, payload
    state_obj = result.get("state", {})
    if not isinstance(state_obj, dict):
        return None, None, payload
    registered = state_obj.get("registered")
    recipient = state_obj.get("recipient")
    if registered not in {True, False, None}:
        registered = None
    return registered, recipient, payload


def sync_live_worknets(
    state: Optional[dict[str, Any]] = None,
    *,
    agent_address: Optional[str] = None,
    limit: int = 100,
    max_pages: int = 5,
) -> dict[str, Any]:
    state = state or state_context()
    wallet = awp_wallet_snapshot()
    agent_address = agent_address or wallet.get("address")
    entries: list[dict[str, Any]] = []
    ranked_entries: list[dict[str, Any]] = []
    errors: list[str] = []

    for page in range(1, max_pages + 1):
        response = rpc_call("worknets.list", params={"page": page, "limit": limit})
        if not response.get("ok"):
            errors.append(str(response.get("error")))
            break
        page_entries = normalize_worknet_entries(response.get("body"))
        if not page_entries:
            break
        entries.extend(page_entries)
        if len(page_entries) < limit:
            break

    for page in range(1, max_pages + 1):
        response = rpc_call("worknets.listRanked", params={"page": page, "limit": limit})
        if not response.get("ok"):
            errors.append(f"listRanked: {response.get('error')}")
            break
        page_entries = normalize_worknet_entries(response.get("body"))
        if not page_entries:
            break
        ranked_entries.extend(page_entries)
        if len(page_entries) < limit:
            break

    normalized: list[dict[str, Any]] = []
    for entry in entries:
        profile = match_profile_from_rpc(entry)
        wid, resolved_via, search_attempts = resolve_live_worknet_id(entry, profile, auxiliary_candidates=ranked_entries)
        observed_id = normalize_worknet_id(first_present(entry, ["worknetId", "id", "worknet_id", "subnetId"]))
        observed_name = first_present(entry, ["name"], "Unknown WorkNet")
        observed_status = first_present(entry, ["status", "state"], "unknown")
        item = {
            "worknetId": wid,
            "name": observed_name,
            "symbol": first_present(entry, ["symbol", "tokenSymbol"], "UNKNOWN"),
            "status": observed_status,
            "skillsUri": first_present(entry, ["skillsUri", "skillsURI", "skillUri", "skillURI"]),
            "minStake": first_present(entry, ["minStake", "min_stake"]),
            "officialSkill": False,
            "tokenPrice": None,
            "agentInfo": None,
            "earnings": None,
            "errors": [],
            "resolvedVia": resolved_via,
            "resolutionConfidence": resolution_confidence(resolved_via),
            "searchAttempts": search_attempts,
            "observedName": observed_name,
            "observedStatus": observed_status,
        }
        if observed_id not in (None, "") and str(observed_id) != str(wid):
            item["observedWorknetId"] = observed_id
        if profile is not None and not item["skillsUri"]:
            item["skillsUri"] = profile.get("skills_uri") or profile.get("install_uri")
        if wid is not None:
            worknet_call = rpc_try_many("worknets.get", [{"worknetId": wid}, {"id": wid}])
            if worknet_call.get("ok"):
                raw = rpc_result_body(worknet_call["body"])
                if isinstance(raw, dict):
                    item["name"] = first_present(raw, ["name"], item["name"])
                    item["symbol"] = first_present(raw, ["symbol", "tokenSymbol"], item["symbol"])
                    item["status"] = first_present(raw, ["status", "state"], item["status"])
                    item["minStake"] = first_present(raw, ["minStake", "min_stake"], item["minStake"])
                    owner = first_present(raw, ["owner"])
                    if owner not in (None, ""):
                        item["owner"] = owner
                    created_at = first_present(raw, ["createdAt", "created_at"])
                    if created_at not in (None, ""):
                        item["createdAt"] = created_at
                    lp_pool = first_present(raw, ["lpPool", "lp_pool"])
                    if lp_pool not in (None, ""):
                        item["lpPool"] = lp_pool
            else:
                item["errors"].append(f"worknets.get: {worknet_call.get('error')}")
            skills_call = rpc_try_many("worknets.getSkills", [{"worknetId": wid}, {"id": wid}])
            if skills_call.get("ok"):
                raw = rpc_result_body(skills_call["body"])
                if isinstance(raw, dict):
                    item["skillsUri"] = first_present(raw, ["skillsURI", "skills_uri", "skillsUri", "skillUri"], item["skillsUri"])
                elif isinstance(raw, str) and raw:
                    item["skillsUri"] = raw
            else:
                item["errors"].append(f"getSkills: {skills_call.get('error')}")

            item["officialSkill"] = looks_official_skill_uri(item.get("skillsUri"))

            token_call = rpc_try_many("tokens.getWorknetTokenPrice", [{"worknetId": wid}, {"id": wid}])
            if token_call.get("ok"):
                item["tokenPrice"] = trim_output(rpc_result_body(token_call["body"]))
            else:
                item["errors"].append(f"tokenPrice: {token_call.get('error')}")

            if agent_address:
                agent_call = rpc_try_many(
                    "worknets.getAgentInfo",
                    [{"worknetId": wid, "agent": agent_address}, {"id": wid, "agent": agent_address}],
                )
                if agent_call.get("ok"):
                    item["agentInfo"] = trim_output(rpc_result_body(agent_call["body"]))
                else:
                    item["errors"].append(f"agentInfo: {agent_call.get('error')}")

                earnings_call = rpc_try_many(
                    "worknets.getEarnings",
                    [{"worknetId": wid, "limit": 3}, {"id": wid, "limit": 3}],
                )
                if earnings_call.get("ok"):
                    item["earnings"] = trim_output(rpc_result_body(earnings_call["body"]))
                else:
                    item["errors"].append(f"earnings: {earnings_call.get('error')}")

        item["officialSkill"] = looks_official_skill_uri(item.get("skillsUri"))
        normalized.append(item)

    payload = {
        "generatedAt": now_iso(),
        "agentAddress": agent_address,
        "ok": bool(normalized),
        "errors": errors,
        "entries": normalized,
        "rankedIndexCount": len(ranked_entries),
    }
    atomic_write_json(official_live_worknets_cache_path(state), payload)
    write_reference_export("official-live-worknets.json", payload)
    return payload


def load_cached_live_worknets(state: dict[str, Any]) -> Optional[dict[str, Any]]:
    payload = load_json(official_live_worknets_cache_path(state), None)
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return payload
    return None


def build_preflight_report() -> dict[str, Any]:
    state = state_context()
    preferences = ensure_user_preferences(state)
    wallet = awp_wallet_snapshot()
    registration_plan = build_registration_plan(state=state, wallet=wallet)
    recovery = build_recovery_state(state)
    recovery_decision = build_recovery_decision(
        recovery,
        worknet_name=str(recovery.get("lastWorknetKey") or ""),
        preferred_profile=resolve_worknet(str(preferences.get("preferredWorknet") or "")),
    )
    cached_registered, cached_recipient, cached_official = probe_cached_official_registration(state)
    cached_preflight = load_json(Path(state["cache"]) / "preflight.json", {})
    cached_bundle = load_cached_capability_bundle(state)
    knowledge_review_queue = load_cached_knowledge_review_queue(state) or build_knowledge_review_queue(state=state)
    knowledge_review_queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
    fast_resume_mode = bool(
        recovery.get("pendingConfirmations")
        or recovery.get("activeBackgroundCount")
        or (recovery.get("hasRuntimeGuidance") and recovery.get("followUpActionCount"))
    )
    bundle: Optional[dict[str, Any]] = None
    registered: Optional[bool] = None
    recipient: Optional[str] = None
    registration_issues: list[str] = []
    rpc_source_mode = None
    missing_managed_skills: list[str] = []
    if fast_resume_mode and isinstance(cached_preflight, dict):
        registered = cached_preflight.get("registered")
        recipient = cached_preflight.get("recipient")
        rpc_source_mode = cached_preflight.get("rpcSourceMode")
        missing_managed_skills = list(cached_preflight.get("missingManagedSkills", []))
    if not missing_managed_skills and isinstance(cached_bundle, dict):
        rpc_source_mode = rpc_source_mode or cached_bundle.get("sourceMode")
        missing_managed_skills = [
            item["key"]
            for item in cached_bundle.get("skillRegistry", [])
            if isinstance(item, dict) and item.get("status") in {"official-remote", "missing"}
        ]
    if registered not in {True, False} and cached_registered in {True, False} and (
        fast_resume_mode or isinstance(cached_bundle, dict)
    ):
        registered = cached_registered
        recipient = cached_recipient
        if rpc_source_mode is None and isinstance(cached_bundle, dict):
            rpc_source_mode = cached_bundle.get("sourceMode")
    if registered not in {True, False}:
        bundle = build_capability_bundle()
        registered, recipient, registration_issues = probe_registration(bundle, wallet.get("address"))
        rpc_source_mode = bundle["sourceMode"]
        missing_managed_skills = [
            item["key"]
            for item in bundle.get("skillRegistry", [])
            if isinstance(item, dict) and item.get("status") in {"official-remote", "missing"}
        ]
    elif rpc_source_mode is None:
        rpc_source_mode = "cached"
    registered_source = "rpc" if registered in {True, False} else None
    if registered is None and cached_registered in {True, False}:
        registered = cached_registered
        recipient = cached_recipient
        registered_source = "awp-skill-cache"
    blocking_issues: list[str] = []
    registration_runtime_needed = registered in {False, None}
    if not wallet.get("installed"):
        blocking_issues.append("awp-wallet is not installed")
    if wallet.get("installed") and not wallet.get("walletReady"):
        blocking_issues.append("awp-wallet did not return an agent address")
    blocking_issues.extend(registration_issues)
    if registration_runtime_needed:
        blocking_issues.extend(
            issue
            for issue in registration_plan.get("issues", [])
            if issue not in blocking_issues
        )
    if registered is True:
        registration_plan["nextAction"] = "registration_already_confirmed"
        if cached_official and isinstance(cached_official, dict):
            cached_result = cached_official.get("result", {})
            if isinstance(cached_result, dict):
                registration_plan["officialNextAction"] = cached_result.get("nextAction")
                registration_plan["officialMessage"] = cached_result.get("message")
        registration_plan["issues"] = [
            issue
            for issue in registration_plan.get("issues", [])
            if issue != "official awp-skill preflight could not reach the AWP API"
        ]
        blocking_issues = [
            issue
            for issue in blocking_issues
            if "registration status is unknown" not in issue
            and "official awp-skill preflight could not reach the AWP API" not in issue
        ]
    if recovery.get("pendingConfirmations"):
        next_action = "resume_pending_confirmations"
    elif recovery.get("activeBackgroundCount"):
        next_action = "monitor_background_runs"
    elif recovery.get("hasRuntimeGuidance") and recovery.get("followUpActionCount"):
        next_action = "resume_runtime_guidance"
    elif recovery.get("resumeAvailable") and recovery.get("hasLatestRun"):
        next_action = "resume_previous_run"
    elif not wallet.get("walletReady"):
        next_action = "install_or_setup_wallet"
    elif registered is False:
        next_action = registration_plan.get("nextAction", "register_agent")
    elif registered is None and registration_plan.get("commands"):
        next_action = registration_plan.get("nextAction", "prepare_registration_runtime")
    else:
        next_action = "scan_worknets"
    plain_language_summary = build_preflight_plain_language_summary(
        next_action,
        knowledge_review_queue_summary=knowledge_review_queue_summary,
        include_queue_note=True,
    )
    report = {
        "walletReady": wallet.get("walletReady", False),
        "registered": registered,
        "agentAddress": wallet.get("address"),
        "recipient": recipient,
        "nextAction": next_action,
        "blockingIssues": blocking_issues,
        "stateRoot": state["root"],
        "stateWarnings": state["warnings"],
        "stateBootstrap": state.get("bootstrap"),
        "rpcSourceMode": rpc_source_mode,
        "availableChains": wallet.get("chains"),
        "userPreferences": preferences,
        "recovery": recovery,
        "recoveryDecision": recovery_decision,
        "missingManagedSkills": missing_managed_skills,
        "knowledgeReviewQueueSummary": knowledge_review_queue_summary,
        "skillRegistryPath": str(Path(state["skills"]) / "install-status.json"),
        "registrationPlan": registration_plan,
        "awpSkillPreflight": registration_plan.get("awpSkillPreflight"),
        "registeredSource": registered_source,
        "cachedOfficialPreflight": cached_official,
        "plainLanguageSummary": plain_language_summary,
        "progress": "[1/5] Preflight",
    }
    atomic_write_json(Path(state["cache"]) / "preflight.json", report)
    return report


def build_start_response() -> dict[str, Any]:
    state = state_context()
    preflight = build_preflight_report()
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    knowledge_overview = (
        knowledge_catalog.get("knowledgeOverview", {})
        if isinstance(knowledge_catalog.get("knowledgeOverview"), dict)
        else {}
    )
    knowledge_focus_topics = knowledge_focus_topics_payload(knowledge_catalog)
    knowledge_reference_highlights = knowledge_reference_highlights_payload(knowledge_catalog)
    knowledge_source_highlights = knowledge_source_highlights_payload(knowledge_catalog)
    registration_plan = preflight.get("registrationPlan", {})
    preferences = (
        preflight.get("userPreferences", {})
        if isinstance(preflight.get("userPreferences"), dict)
        else ensure_user_preferences(state)
    )
    knowledge_review_queue_summary = (
        preflight.get("knowledgeReviewQueueSummary", {})
        if isinstance(preflight.get("knowledgeReviewQueueSummary"), dict)
        else {}
    )
    queue_headline_for_message: Optional[str] = None
    recovery_decision = (
        preflight.get("recoveryDecision")
        if isinstance(preflight.get("recoveryDecision"), dict)
        else None
    )
    recommendation: Optional[dict[str, Any]] = None
    cached_bundle = load_cached_capability_bundle(state)
    preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))

    user_actions: list[dict[str, Any]] = []
    action_map: dict[str, str] = {}
    progress = progress_message(1, 5, "AWP 启动", "已完成预检，正在准备最佳下一步")

    intro = (
        "AWP 是一个让 agent 工作和赚钱的网络。Workstation 会帮你检查钱包、确认是否已注册、扫描可做的工作，并在涉及资金前先征求确认。"
    )
    preflight_intro = build_preflight_plain_language_summary(
        str(preflight.get("nextAction") or ""),
        knowledge_review_queue_summary=knowledge_review_queue_summary,
        include_queue_note=False,
    )

    if preflight.get("nextAction") == "install_awp_skill_dependency":
        progress = progress_message(1, 5, "依赖准备", "缺少 awp-skill，先准备官方 RootNet 依赖")
        user_message = (
            "你的 agent work wallet 已经就绪，但当前环境里还没有可用的 awp-skill 运行时，所以还不能直接走官方 gasless 注册。"
        )
        command = registration_plan.get("commands", [{}])[0] if registration_plan.get("commands") else None
        if isinstance(command, dict):
            label = "安装 awp-skill 依赖"
            user_actions.append(
                {
                    "label": label,
                    "description": "准备 RootNet 官方依赖，之后再尝试注册。",
                }
            )
            action_map[label] = " ".join(command.get("argv", []))
        user_actions.append(
            {
                "label": "先看 WorkNet",
                "description": "先用本地百科理解有哪些工作和风险。",
            }
        )
        action_map["先看 WorkNet"] = "python3 scripts/scan-worknets.py"
    elif preflight.get("nextAction") in {"run_awp_skill_registration", "register_agent"}:
        progress = progress_message(2, 5, "注册准备", "已找到注册路径，可以继续官方 gasless onboarding")
        user_message = "你的环境已经具备继续注册的条件，下一步可以走官方 gasless onboarding。"
        command = registration_plan.get("commands", [{}])[0] if registration_plan.get("commands") else None
        if isinstance(command, dict):
            label = "继续注册"
            user_actions.append({"label": label, "description": "继续官方 agent 注册流程。"})
            action_map[label] = " ".join(command.get("argv", []))
        official_message = registration_plan.get("officialMessage")
        if official_message:
            user_message += " " + str(official_message)
    elif preflight.get("nextAction") == "retry_registration_preflight":
        progress = progress_message(2, 5, "注册等待", "官方注册脚本已就位，但当前 API 不可达")
        user_message = "官方 awp-skill 运行时已经准备好，但它自己的预检也确认当前无法连到 AWP API，所以现在不建议继续提交注册。"
        official_message = registration_plan.get("officialMessage")
        if official_message:
            user_message += " " + str(official_message)
        user_actions.append(
            {
                "label": "重试官方预检",
                "description": "网络恢复后，先重新检查官方注册前置条件。",
            }
        )
        action_map["重试官方预检"] = "python3 scripts/register-agent.py"
        user_actions.append(
            {
                "label": "先看 WorkNet",
                "description": "注册未通时，先了解有哪些工作和风险。",
            }
        )
        action_map["先看 WorkNet"] = "python3 scripts/scan-worknets.py"
    elif preflight.get("nextAction") == "resume_runtime_guidance":
        recovery = preflight.get("recovery", {})
        worknet_key = str(recovery.get("lastWorknetKey") or "")
        progress = progress_message(4, 5, "继续运行", "上一次运行已经给出明确下一步，可以直接续上")
        user_message = humanize_runtime_guidance_message(recovery)
        default_label = recovery.get("defaultFollowUpLabel")
        default_command = recovery.get("defaultFollowUpCommand")
        if default_label and default_command:
            user_actions.append(
                {
                    "label": "继续当前运行",
                    "description": (
                        f"按默认下一步继续：{default_label}"
                        if not worknet_key
                        else runtime_follow_up_description(worknet_key, str(default_label))
                    ),
                }
            )
            action_map["继续当前运行"] = "python3 scripts/run-workstation.py --mode autopilot --execute"
        for item in recovery.get("followUpActions", []):
            if not isinstance(item, dict) or not item.get("label"):
                continue
            label = str(item["label"])
            command = item.get("command")
            user_actions.append(
                {
                    "label": label,
                    "description": runtime_follow_up_description(worknet_key, label),
                }
            )
            if item.get("requiresConfirmation"):
                action_map[label] = workstation_follow_up_command(label, execute=False)
            elif item.get("safeToAutoRun") and item.get("argv"):
                action_map[label] = workstation_follow_up_command(label, execute=True)
            elif isinstance(command, str) and command.strip():
                action_map[label] = command.strip()
        if isinstance(recovery_decision, dict):
            maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
    elif preflight.get("nextAction") == "monitor_background_runs":
        recovery = preflight.get("recovery", {})
        active = recovery.get("activeBackgroundProcesses", [])
        progress = progress_message(4, 5, "后台运行", f"当前有 {recovery.get('activeBackgroundCount', 0)} 个后台任务")
        user_message = "已有工作循环在后台运行，可以直接看日志或停止它。"
        if len(active) == 1 and isinstance(active[0], dict):
            summary = active[0].get("summary", {})
            headline = summary.get("headline") if isinstance(summary, dict) else None
            if isinstance(headline, str) and headline.strip():
                user_message = headline.strip()
        if isinstance(recovery_decision, dict) and str(recovery_decision.get("status") or "").strip() == "background_running":
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
        if not user_actions:
            if recovery.get("activeBackgroundCount") == 1:
                user_actions.append(
                    {
                        "label": "暂停当前运行",
                        "description": "停止当前唯一的后台工作循环。",
                    }
                )
                action_map["暂停当前运行"] = workstation_pause_command(execute=True)
            for item in active:
                if not isinstance(item, dict) or not item.get("label"):
                    continue
                label = str(item["label"])
                user_actions.append(
                    {
                        "label": f"查看 {label}",
                        "description": (
                            str(item.get("summary", {}).get("headline"))
                            if isinstance(item.get("summary"), dict) and item.get("summary", {}).get("headline")
                            else "查看这个后台任务的最近日志。"
                        ),
                    }
                )
                action_map[f"查看 {label}"] = workstation_background_command(label, tail_lines=40)
                user_actions.append(
                    {
                        "label": f"停止 {label}",
                        "description": "停止这个后台任务。",
                    }
                )
                action_map[f"停止 {label}"] = workstation_background_command(label, stop=True, execute=False)
            if isinstance(recovery_decision, dict):
                maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
    elif preflight.get("nextAction") == "resume_previous_run":
        latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
        recovery = preflight.get("recovery", {}) if isinstance(preflight.get("recovery"), dict) else {}
        source_follow_up = latest_run.get("sourceFollowUpAction", {}) if isinstance(latest_run, dict) else {}
        restart_label = str(source_follow_up.get("label") or "")
        observations = background_observations_from_run(latest_run, state=state)
        last_background = observations[0] if observations else None
        worknet_name = (
            latest_run.get("playbook", {}).get("requiredSkill")
            if isinstance(latest_run.get("playbook"), dict)
            else None
        )
        progress = progress_message(4, 5, "继续运行", "发现上一次的工作记录，可以直接续上")
        if isinstance(last_background, dict):
            summary = last_background.get("summary", {})
            headline = summary.get("headline") if isinstance(summary, dict) else None
            if isinstance(headline, str) and headline.strip():
                if last_background.get("alive"):
                    user_message = headline.strip()
                else:
                    user_message = f"上次看到的状态是：{headline.strip()}"
            else:
                user_message = f"上一次 {worknet_name or 'AWP'} 工作循环已经停下，可以继续从最近的记录续跑。"
        else:
            user_message = f"上一次 {worknet_name or 'AWP'} 工作循环已经停下，可以继续从最近的记录续跑。"
        if restart_label:
            resume_label = review_background_action_label(restart_label, restart=True)
            user_actions.append(
                {
                    "label": resume_label,
                    "description": "按上一次保存的运行参数重新启动。",
                }
            )
            action_map[resume_label] = workstation_follow_up_command(restart_label, execute=True)
        if recovery.get("preferFreshStartOverResume") and preferred_profile and str(preferred_profile.get("key")) != str(recovery.get("lastWorknetKey") or ""):
            bundle_for_resume = cached_bundle or build_capability_bundle()
            preferred_report = next(
                (
                    item
                    for item in bundle_for_resume.get("reports", [])
                    if isinstance(item, dict)
                    and str(item.get("worknetId")) == str(preferred_profile.get("worknet_id"))
                ),
                None,
            )
            preferred_runnable = bool(
                preferred_report
                and preferred_report.get("runnable")
                and preferred_report.get("recommendedRole") not in {"identity", "observer"}
                and preferred_report.get("automationLevel") != "manual-only"
            )
            if preferred_runnable:
                preferred_name = str(preferred_report.get("name") or preferred_profile.get("name") or preferred_profile["key"])
                stale_reason = humanize_recovery_stale_reason(recovery.get("staleLatestRunReason"))
                user_message += (
                    f" 这份旧记录已经不算活跃；如果你不想继续旧的 {worknet_name or 'WorkNet'}，"
                    f"也可以直接改按当前默认的 {preferred_name} 重新开始。"
                )
                if stale_reason:
                    user_message += f" 当前判断依据是：{stale_reason}。"
                user_actions.append(
                    {
                        "label": f"改按默认 {preferred_name} 开始",
                        "description": "跳过旧 run，直接按你当前保存的默认 WorkNet 重新起步。",
                    }
                )
                action_map[f"改按默认 {preferred_name} 开始"] = run_worknet_command(
                    str(preferred_profile["key"]),
                    execute=True,
                    auto_advance=True,
                )
        user_actions.append(
            {
                "label": "查看上次复盘",
                "description": "先看最近一次工作记录、收益样本和下一步动作。",
            }
        )
        action_map["查看上次复盘"] = "python3 scripts/review-epoch.py"
        resume_briefing = build_resume_recovery_briefing(
            recovery,
            user_actions,
            worknet_name=worknet_name,
            preferred_profile=preferred_profile,
            context_message=user_message,
            action_map=action_map,
        )
        if isinstance(resume_briefing.get("message"), str) and resume_briefing.get("message"):
            user_message = str(resume_briefing["message"])
        if isinstance(resume_briefing.get("decision"), dict):
            recovery_decision = resume_briefing.get("decision")
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
        if not restart_label:
            if recommendation is None:
                recommendation = recommend_worknet_actions(
                    cached_bundle or build_capability_bundle(),
                    preferences=preferences,
                )
            user_actions.extend(recommendation["actions"])
            action_map.update(recommendation["actionMap"])
    elif preflight.get("nextAction") in {"scan_worknets", "resume_pending_confirmations"}:
        bundle_for_recommendation = cached_bundle or build_capability_bundle()
        if recommendation is None:
            recommendation = recommend_worknet_actions(
                bundle_for_recommendation,
                preferences=preferences,
            )
        earning_runnable_count = recommendation.get("earningRunnableCount", 0)
        support_runnable_count = recommendation.get("supportRunnableCount", 0)
        detail = f"已发现 {earning_runnable_count} 个当前可直接赚钱项"
        if support_runnable_count:
            detail += f"，另有 {support_runnable_count} 个辅助工具"
        progress = progress_message(3, 5, "WorkNet 扫描", detail)
        user_message = recommendation["recommendation"]
        preferred_report = next(
            (
                item
                for item in bundle_for_recommendation.get("reports", [])
                if isinstance(item, dict)
                and preferred_profile
                and str(item.get("worknetId")) == str(preferred_profile.get("worknet_id"))
            ),
            None,
        )
        preferred_runnable = bool(
            preferred_report
            and preferred_report.get("runnable")
            and preferred_report.get("recommendedRole") not in {"identity", "observer"}
            and preferred_report.get("automationLevel") != "manual-only"
        )
        if preflight.get("nextAction") == "scan_worknets" and preferred_profile and preferred_runnable:
            preferred_name = str(preferred_report.get("name") or preferred_profile.get("name") or preferred_profile["key"])
            user_message += f" 你当前保存的默认 WorkNet 是 {preferred_name}，现在可以直接按这个偏好开始。"
            user_actions.append(
                {
                    "label": f"启动默认 {preferred_name}",
                    "description": (
                        canonical_worknet_switch_summary_text(
                            preferred_profile,
                            runnable=bool(preferred_report.get("runnable")),
                            can_start_without_stake=preferred_report.get("canStartWithoutStake") is True,
                        )
                        or "直接按你保存的默认 WorkNet 生成 playbook 并进入默认执行路径。"
                    ),
                }
            )
            action_map[f"启动默认 {preferred_name}"] = run_worknet_command(
                str(preferred_profile["key"]),
                execute=True,
                auto_advance=True,
            )
        user_actions.extend(recommendation["actions"])
        action_map.update(recommendation["actionMap"])
        if preflight.get("nextAction") == "resume_pending_confirmations":
            recovery = preflight.get("recovery", {})
            user_actions.insert(
                0,
                {
                    "label": "继续待确认动作",
                    "description": "先恢复上一次停在确认队列里的动作。",
                },
            )
            action_map["继续待确认动作"] = "python3 scripts/run-workstation.py --mode autopilot"
            for label in recovery.get("pendingConfirmationLabels", []):
                if not isinstance(label, str) or not label.strip():
                    continue
                user_actions.append(
                    {
                        "label": label,
                        "description": "确认并执行这个待确认动作。",
                    }
                )
                action_map[label] = workstation_confirmation_command(label, execute=False)
            if isinstance(recovery_decision, dict):
                maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
    else:
        user_message = "Workstation 已完成基础预检，但还需要更多运行时准备。"

    if str(preflight.get("nextAction") or "") in {
        "install_awp_skill_dependency",
        "run_awp_skill_registration",
        "register_agent",
        "retry_registration_preflight",
        "scan_worknets",
    }:
        if preflight_intro and preflight_intro not in user_message:
            user_message = f"{preflight_intro} {user_message}".strip()

    if knowledge_review_queue_summary.get("hasPendingReviews"):
        queue_headline = str(knowledge_review_queue_summary.get("headline") or "").strip()
        queue_headline_for_message = queue_headline or None
        if queue_headline:
            if user_message.endswith(("。", "！", "？", ".", "!", "?")):
                user_message += queue_headline
            else:
                user_message += "。" + queue_headline
        queue_label = str(knowledge_review_queue_summary.get("primaryActionLabel") or "").strip()
        queue_command = str(knowledge_review_queue_summary.get("primaryActionCommand") or "").strip()
        if queue_label and queue_command and not any(item.get("label") == queue_label for item in user_actions):
            user_actions.append(
                {
                    "label": queue_label,
                    "description": "非阻塞地查看最近哪些官方资料发生变化，以及哪些知识条目需要重审。",
                }
            )
            action_map[queue_label] = queue_command

    if preflight.get("registered") is not True and registration_plan.get("officialNextAction") == "retry_preflight":
        user_message += " 官方 awp-skill 预检也确认当前无法连到 AWP API，等网络可用后再继续注册。"

    append_user_action(
        user_actions,
        action_map,
        label="研究 AWP 百科",
        description="先看高层主题、重点 WorkNet 和当前待重审知识。",
        command=workstation_status_command(intent="research"),
    )

    execution_state = derive_execution_state(
        recovery=preflight.get("recovery"),
        next_action=preflight.get("nextAction"),
    )
    resume_status = str(recovery_decision.get("status") or "").strip() if isinstance(recovery_decision, dict) else None
    user_actions = prioritize_ui_actions(
        user_actions,
        action_map,
        execution_state=execution_state.get("executionState"),
        resume_status=resume_status,
        worknet_key=str(preflight.get("recovery", {}).get("lastWorknetKey") or "").strip() or None,
    )
    user_action_details = action_details_from_ui_actions(user_actions, action_map)
    user_action_details = annotate_execution_actions(user_action_details)
    user_actions = annotate_execution_actions(user_actions)
    public_user_actions = humanize_public_action_entries(user_actions)
    public_preflight = dict(preflight)
    public_preflight["recoveryDecision"] = humanize_public_recovery_decision(preflight.get("recoveryDecision"))
    user_message = align_run_execution_user_message(
        user_message,
        execution_state=execution_state.get("executionState"),
        execution_headline=execution_state.get("executionHeadline"),
        primary_action=user_actions[0]["label"] if user_actions else None,
        worknet_context_key=str(preflight.get("recovery", {}).get("lastWorknetKey") or ""),
        include_canonical_plain=False,
        extra_parts=[queue_headline_for_message] if queue_headline_for_message else None,
    )
    payload = {
        "progress": progress,
        "intro": intro,
        "user_message": user_message,
        "user_actions": public_user_actions,
        "resumeStatus": resume_status or None,
        "resumeStatusDisplay": recovery_status_display(resume_status) if resume_status else None,
        "executionState": execution_state.get("executionState"),
        "executionStateDisplay": execution_state.get("executionStateDisplay"),
        "executionHeadline": execution_state.get("executionHeadline"),
        "primaryUserAction": user_actions[0]["label"] if user_actions else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "userActionDetails": user_action_details,
        "recoveryDecision": humanize_public_recovery_decision(recovery_decision),
        "knowledgeReviewQueueSummary": knowledge_review_queue_summary,
        "knowledgeOverview": knowledge_overview,
        "knowledgeFocusTopics": knowledge_focus_topics,
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "_internal": {
            "action_map": action_map,
            "preflight": public_preflight,
            "capability_bundle_path": str(Path(state["cache"]) / "capability-scan.json"),
        },
    }
    atomic_write_json(Path(state["cache"]) / "start-response.json", payload)
    return payload


def build_work_playbook(worknet_identifier: str) -> dict[str, Any]:
    profile = resolve_worknet(worknet_identifier)
    if profile is None:
        raise ValueError(f"unknown worknet: {worknet_identifier}")
    state = state_context()
    preferences = ensure_user_preferences(state)
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    knowledge_context = compact_knowledge_context(
        knowledge_context_for_worknet(knowledge_catalog, str(profile.get("key") or ""))
    )
    knowledge_reference_highlights = knowledge_related_reference_highlights(
        knowledge_catalog,
        knowledge_context,
    ) if isinstance(knowledge_context, dict) else []
    knowledge_source_highlights = knowledge_related_source_highlights(
        knowledge_catalog,
        knowledge_context,
    ) if isinstance(knowledge_context, dict) else []
    knowledge_caveat = capability_knowledge_caveat(knowledge_context, knowledge_source_highlights)
    inventory = build_source_inventory()
    local_sources = {item["key"]: item for item in inventory.get("localSources", [])}
    local_source = local_sources.get(profile.get("local_source_key"))
    resolved_root, _resolved_origin = resolve_skill_root(profile["key"], inventory=inventory, state=state)
    skill_registry = {
        item["key"]: item for item in skill_registry_from_inventory(inventory, state=state)
    }
    skill_record = skill_registry.get(profile["key"], {})
    inspection = inspect_skill_runtime(profile["key"], state=state, inventory=inventory)
    inspection_status = str(inspection.get("status", "missing"))
    manifest = official_remote_manifest(profile["key"])
    commands: list[dict[str, Any]] = []
    install_command = (
        build_skill_sync_command(skill_record)
        if isinstance(skill_record, dict) and skill_record.get("status") == "official-remote"
        else None
    )
    if install_command is not None:
        commands.append(install_command)
    manifest_bootstrap_commands = build_manifest_commands(
        profile["key"],
        state=state,
        skill_root=resolved_root,
        section="bootstrapCommands",
    )
    manifest_inspection_commands = build_manifest_commands(
        profile["key"],
        state=state,
        skill_root=resolved_root,
        section="inspectionCommands",
    )
    if skill_record.get("installUri") or profile.get("install_uri"):
        commands.append(build_skill_inspect_command(profile["key"]))
    if inspection_status != "ready":
        commands.extend(manifest_bootstrap_commands)
    commands.extend(manifest_inspection_commands)
    local_root = resolved_root if isinstance(resolved_root, Path) else None
    commands.extend(
        rewrite_command_for_skill_root(command, skill_root=local_root)
        for command in list(profile.get("commands", []))
    )
    remediation_commands = inspection.get("remediationCommands", []) if isinstance(inspection, dict) else []
    if inspection_status != "ready" and isinstance(remediation_commands, list):
        commands.extend(remediation_commands)
    commands = dedupe_playbook_commands(commands)
    commands = annotate_playbook_commands(commands, inspection_status=inspection_status)
    success_metrics_raw = [str(item) for item in profile.get("success_metrics", []) if str(item).strip()]
    failure_modes_raw = [str(item) for item in profile.get("failure_modes", []) if str(item).strip()]
    human_confirmations_raw = [str(item) for item in profile.get("human_confirmations", []) if str(item).strip()]
    success_metrics = [humanize_playbook_success_metric(item) for item in success_metrics_raw]
    failure_modes = [humanize_playbook_failure_mode(item) for item in failure_modes_raw]
    human_confirmations = [humanize_playbook_confirmation_item(item) for item in human_confirmations_raw]
    if isinstance(knowledge_context, dict):
        label = str(knowledge_context.get("label") or profile.get("name") or profile.get("key") or "当前 WorkNet").strip()
        source_labels = knowledge_source_labels_text(
            knowledge_source_highlights,
            affected_only=True,
            limit=3,
        )
        if knowledge_caveat:
            append_unique_text(
                failure_modes,
                (
                    f"{label} 的上游来源 {source_labels} 刚发生变化，当前 playbook 的可运行性假设可能已经过时。"
                    if source_labels
                    else f"{label} 的上游来源刚发生变化，当前 playbook 的可运行性假设可能已经过时。"
                ),
            )
            append_unique_text(
                human_confirmations,
                (
                    f"在继续这份 {label} playbook 前，先复核 {source_labels} 和本地百科条目。"
                    if source_labels
                    else f"在继续这份 {label} playbook 前，先复核最新官方来源和本地百科条目。"
                ),
            )
    playbook = {
        "generatedAt": now_iso(),
        "worknetKey": profile["key"],
        "worknetId": profile["worknet_id"],
        "goal": humanize_playbook_goal(profile["key"], str(profile["goal"])),
        "goalRaw": profile["goal"],
        "role": humanize_playbook_role(str(profile["recommended_role"])),
        "roleRaw": profile["recommended_role"],
        "loop": humanize_playbook_loop(profile["key"], str(profile["loop"])),
        "loopRaw": profile["loop"],
        "goalNarrative": knowledge_context.get("summary") if isinstance(knowledge_context, dict) else None,
        "loopNarrative": canonical_worknet_loop_text(profile["key"]),
        "riskNarrative": canonical_worknet_caution_text(profile["key"]),
        "knowledgeCaveat": knowledge_caveat,
        "knowledgeContext": knowledge_context,
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "knowledgeActions": [
            {
                "label": f"查看 {knowledge_context.get('label') or profile['name']} 档案",
                "description": knowledge_action_description(knowledge_context),
                "command": knowledge_context.get("queryCommand"),
            },
            {
                "label": f"重审 {knowledge_context.get('label') or profile['name']}",
                "description": knowledge_refresh_action_description(knowledge_context),
                "command": knowledge_context.get("primaryCommand"),
            },
        ] if isinstance(knowledge_context, dict) else [],
        "requiredSkill": profile["name"],
        "requiredRuntime": manifest.get("runtimeName"),
        "requiredSkillInstallUri": profile.get("install_uri"),
        "requiredSkillLocalPath": local_source.get("path") if isinstance(local_source, dict) else None,
        "requiredSkillStatus": skill_record.get("status"),
        "skillInspection": inspection,
        "executionModel": "probe_then_single_primary_work",
        "commands": commands,
        "successMetrics": success_metrics,
        "successMetricsRaw": success_metrics_raw,
        "failureModes": failure_modes,
        "failureModesRaw": failure_modes_raw,
        "humanConfirmations": human_confirmations,
        "humanConfirmationsRaw": human_confirmations_raw,
        "preferencesSnapshot": preferences,
        "recoveryPath": str(Path(state["playbooks"]) / f"{profile['key']}.json"),
        "stateRoot": state["root"],
        "progress": "[3/5] Playbook build",
    }
    if knowledge_source_highlights:
        playbook["knowledgeActions"].extend(
            {
                "label": f"查看来源 {item.get('label') or item.get('key')}",
                "description": knowledge_source_action_description(item),
                "command": item.get("queryCommand"),
            }
            for item in knowledge_source_highlights[:3]
            if isinstance(item, dict) and (item.get("queryCommand"))
        )
        for item in knowledge_source_highlights[:2]:
            if not isinstance(item, dict):
                continue
            primary_command = str(item.get("primaryCommand") or "").strip()
            query_command = str(item.get("queryCommand") or "").strip()
            if primary_command and primary_command != query_command:
                playbook["knowledgeActions"].append(
                    {
                        "label": f"重读来源 {item.get('label') or item.get('key')}",
                        "description": f"重新拉取 {item.get('label') or item.get('key')}，确认上游变化有没有影响这份 playbook。",
                        "command": primary_command,
                    }
                )
    playbook["knowledgeActions"] = dedupe_action_entries(playbook["knowledgeActions"])
    playbook_state = derive_playbook_execution_state(
        profile,
        inspection_status=inspection_status,
        knowledge_caveat=knowledge_caveat,
    )
    playbook.update(
        {
            "resumeStatus": None,
            "resumeStatusDisplay": None,
            "executionState": playbook_state.get("executionState"),
            "executionStateDisplay": playbook_state.get("executionStateDisplay"),
            "executionHeadline": playbook_state.get("executionHeadline"),
        }
    )
    user_action_details = build_playbook_user_action_details(playbook)
    user_action_details = annotate_execution_actions(user_action_details)
    playbook["primaryUserAction"] = user_action_details[0]["label"] if user_action_details else None
    playbook["primaryUserActionDisplay"] = user_action_details[0]["displayLabel"] if user_action_details else None
    playbook["primaryUserActionCommand"] = user_action_details[0]["command"] if user_action_details else None
    playbook["userActionDetails"] = user_action_details
    slug = profile["key"]
    atomic_write_json(Path(state["playbooks"]) / f"{slug}.json", playbook)
    atomic_write_json(Path(state["playbooks"]) / "last-selected.json", playbook)
    return playbook


def load_playbook(
    path: Optional[str],
    worknet_identifier: Optional[str],
) -> tuple[dict[str, Any], list[str], str]:
    warnings: list[str] = []
    state = state_context()
    if path:
        payload = load_json(Path(path), None)
        if isinstance(payload, dict):
            return payload, warnings, "path"
        raise ValueError(f"playbook not found or invalid: {path}")
    if worknet_identifier:
        return build_work_playbook(worknet_identifier), warnings, "worknet"
    latest_path = Path(state["playbooks"]) / "last-selected.json"
    payload = load_json(latest_path, None)
    if isinstance(payload, dict):
        return payload, warnings, "last-selected"
    preferences = ensure_user_preferences(state)
    preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))
    if preferred_profile is not None:
        warnings.append(
            f"no last-selected playbook was found, so workstation fell back to preferredWorknet={preferred_profile['key']}"
        )
        return build_work_playbook(str(preferred_profile["key"])), warnings, "preferred-worknet"
    raise ValueError("no playbook path or worknet provided")


def step_result_payload(step: Any) -> Any:
    if not isinstance(step, dict):
        return None
    result = step.get("result")
    if not isinstance(result, dict):
        return None
    if "stdout" in result:
        return result.get("stdout")
    return result


def runtime_guidance_from_step(
    step: dict[str, Any],
    *,
    worknet_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    resolved_worknet = str(worknet_key or step.get("worknetKey") or "").strip().lower()
    return extract_runtime_guidance_from_payload(
        step_result_payload(step),
        worknet_key=resolved_worknet or None,
    )


def command_status_without_execution(command: dict[str, Any], *, execute: bool) -> str:
    policy = str(command.get("executionPolicy", "manual"))
    if command.get("requires_confirmation"):
        return "queued_for_confirmation"
    if not command.get("argv"):
        return "missing_runtime_command"
    if execute:
        return "available_manual"
    if policy in {"probe", "setup", "primary-work"}:
        return "planned"
    return "available_manual"


def mine_reward_hint_from_guidance(guidance: Optional[dict[str, Any]]) -> Optional[str]:
    if not isinstance(guidance, dict):
        return None
    state = str(guidance.get("state") or "")
    if state == "selection_required":
        return "Mine 还没有开始产出；先选一个 dataset，再让 worker 持续运行。"
    message = str(guidance.get("message") or "")
    if "begin earning" in message.lower():
        return "Mine 还没有开始产出；当前 worker 仍是 idle。"
    return None


def reward_hints_from_run(latest_run: dict[str, Any]) -> list[str]:
    playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
    worknet_key = str(playbook.get("worknetKey") or "")
    steps = latest_run.get("executedSteps", []) if isinstance(latest_run, dict) else []
    hints: list[str] = []
    if worknet_key == "mine":
        for step in reversed(steps):
            guidance = runtime_guidance_from_step(step) if isinstance(step, dict) else None
            hint = mine_reward_hint_from_guidance(guidance)
            if hint:
                hints.append(hint)
                break
    elif worknet_key == "predict":
        for step in steps:
            payload = step_result_payload(step) if isinstance(step, dict) else None
            if not isinstance(payload, dict):
                continue
            data = payload.get("data")
            if isinstance(data, dict) and data.get("balance") not in (None, ""):
                hints.append(
                    f"Predict 当前可见 chips 余额为 {data.get('balance')}；真实奖励仍要等市场结算。"
                )
                break
    elif worknet_key == "gov":
        hints.append("Gov 暂时没有可靠收益估计；先看公开市场，等有 AWP Power 后再进入签名动作。")
    elif worknet_key == "ardi":
        hints.append("Ardi 暂时没有可靠收益估计；先补 Gas 和资格条件，再进入提交承诺、揭示和铭刻节奏。")
    return hints


def format_awp_amount(value: Any, *, decimals: int = 18, places: int = 3) -> Optional[str]:
    try:
        raw = int(str(value))
    except (TypeError, ValueError):
        return None
    sign = "-" if raw < 0 else ""
    raw = abs(raw)
    base = 10 ** decimals
    whole, fraction = divmod(raw, base)
    text = f"{sign}{whole:,}"
    if places > 0:
        fraction_text = f"{fraction:0{decimals}d}"[:places].rstrip("0")
        if fraction_text:
            text += f".{fraction_text}"
    return f"{text} AWP"


def append_unique_text(items: list[str], value: Optional[str]) -> None:
    if not isinstance(value, str):
        return
    text = value.strip()
    if not text or text in items:
        return
    items.append(text)


def recent_public_earnings_samples(
    state: dict[str, Any],
    worknet_key: str,
) -> tuple[Optional[str], list[dict[str, Any]]]:
    profile = resolve_worknet(worknet_key)
    if profile is None:
        return None, []
    worknet_id = str(profile.get("worknet_id"))
    name = str(profile.get("name") or worknet_key)
    samples: list[dict[str, Any]] = []
    bundle = load_cached_capability_bundle(state)
    if isinstance(bundle, dict):
        for item in bundle.get("reports", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("worknetId")) != worknet_id:
                continue
            diagnostics = item.get("rpcDiagnostics", {})
            if isinstance(diagnostics, dict) and isinstance(diagnostics.get("earnings"), list):
                samples = [entry for entry in diagnostics.get("earnings", []) if isinstance(entry, dict)]
                break
    if not samples:
        live = load_cached_live_worknets(state)
        if isinstance(live, dict):
            for item in live.get("entries", []):
                if not isinstance(item, dict):
                    continue
                if str(item.get("worknetId")) != worknet_id:
                    continue
                if isinstance(item.get("earnings"), list):
                    samples = [entry for entry in item.get("earnings", []) if isinstance(entry, dict)]
                    break
    return name, samples


def public_earnings_hint_for_worknet(state: dict[str, Any], worknet_key: str) -> Optional[str]:
    name, samples = recent_public_earnings_samples(state, worknet_key)
    if not name or not samples:
        return None
    formatted: list[str] = []
    for sample in samples[:3]:
        text = format_awp_amount(sample.get("awp_amount"))
        if text:
            formatted.append(text)
    if not formatted:
        return None
    epochs = [sample.get("epoch_id") for sample in samples[:3] if sample.get("epoch_id") not in (None, "")]
    epoch_suffix = ""
    if epochs:
        epoch_suffix = f"（最近可见结算周期: {', '.join(str(item) for item in epochs)}）"
    if len(formatted) == 1:
        return f"{name} 最近一个公开结算周期的可见奖励样本约为 {formatted[0]}{epoch_suffix}；这是公开样本，不是你的已实现收益。"
    return (
        f"{name} 最近 {len(formatted)} 个公开结算周期的可见奖励样本约在 {formatted[-1]} 到 {formatted[0]} 之间"
        f"{epoch_suffix}；这是公开样本，不是你的已实现收益。"
    )


def background_observations_from_run(
    latest_run: dict[str, Any],
    *,
    state: dict[str, Any],
    tail_lines: int = 60,
) -> list[dict[str, Any]]:
    active_records = {
        str(item.get("label")): summarize_background_record(item, tail_lines=tail_lines)
        for item in load_active_processes(state)
        if isinstance(item, dict) and item.get("label")
    }
    observations: list[dict[str, Any]] = []
    seen: set[str] = set()
    steps = latest_run.get("executedSteps", []) if isinstance(latest_run, dict) else []
    for step in reversed(steps):
        if not isinstance(step, dict) or step.get("status") != "started_background":
            continue
        record = step.get("backgroundProcess")
        if not isinstance(record, dict):
            continue
        label = str(record.get("label") or "")
        if not label or label in seen:
            continue
        observation = active_records.get(label) or summarize_background_record(record, tail_lines=tail_lines)
        observations.append(observation)
        seen.add(label)
    for label, observation in active_records.items():
        if label in seen:
            continue
        observations.append(observation)
    return observations


def background_strategy_change_from_summary(summary: dict[str, Any], *, alive: bool) -> Optional[str]:
    state = str(summary.get("state") or "")
    if state == "llm_error":
        return "Predict loop 最近卡在 LLM 输出解析阶段；先看日志，再决定是否重启。"
    if not alive:
        return "最近一次后台工作循环已经停下；如果还想继续，先看日志再决定是否重启。"
    if state == "waiting_for_market":
        return "Predict 当前没有可提交市场；保持观察或稍后再看下一轮。"
    if state == "llm_running":
        return "Predict 当前正在跑本轮推理；不要频繁重启，让它先完成这一轮。"
    if state in {"challenge_ready", "iteration_started", "starting"}:
        return "工作循环已经在后台运行，接下来重点看日志和下一次复盘。"
    return None


def review_background_action_label(label: str, *, restart: bool = False, inspect: bool = False, stop: bool = False) -> str:
    display = label[3:] if label.startswith("启动 ") else label
    if restart:
        return f"重新启动 {display}"
    if inspect:
        return f"查看 {display}"
    if stop:
        return f"停止 {display}"
    return display


def humanize_runtime_guidance_message(recovery: dict[str, Any]) -> str:
    raw = str(recovery.get("runtimeGuidanceMessage") or "").strip()
    worknet_key = str(recovery.get("lastWorknetKey") or "")
    next_action = str(recovery.get("runtimeGuidanceNextAction") or "")
    default_label = str(recovery.get("defaultFollowUpLabel") or "").strip()
    if worknet_key == "mine":
        if raw.lower().startswith("please select a dataset"):
            if default_label:
                return f"Mine 已经准备好，先选一个 dataset 开始第一轮采集。默认建议先从 {default_label} 开始。"
            return "Mine 已经准备好，先选一个 dataset 开始第一轮采集。"
        if "mining environment is ready" in raw.lower():
            return "Mine 运行环境已经就绪，可以直接开始第一轮采集。"
    if worknet_key == "gov" and next_action == "acquire_awp_power_or_observe_gov":
        return "Gov 这期还没有你的 AWP Power，先做公开观察；等 AWP Power 到位后再处理投票和交易。"
    if worknet_key == "predict" and next_action == "wait_for_predict_market":
        return "Predict 当前没有合适市场，先等下一轮，再回来继续。"
    return raw or "上一次运行已经给出明确下一步。"


def humanize_recovery_stale_reason(reason: Optional[str]) -> Optional[str]:
    text = str(reason or "").strip()
    if not text:
        return None
    mapping = {
        "latest run stopped and only restart guidance remains": "上一次工作循环已经停下，现在只剩重启路径可选",
        "latest review status is blocked": "最近一次复盘已经明确卡住",
        "latest review status is partial": "最近一次复盘显示上一次运行只完成了一部分",
        "latest review status is observe_only": "最近一次复盘显示这条旧路线目前更适合观察，不适合继续强推自动执行",
        "latest review status is awaiting_dataset": "最近一次复盘显示旧路线还停在 dataset 选择，没有真正开跑",
    }
    if text in mapping:
        return mapping[text]
    if text.startswith("latest run is ") and text.endswith(" hours old"):
        return "上一次运行已经放了太久，继续恢复旧现场的价值不高"
    return text


def build_recovery_decision(
    recovery: Any,
    *,
    worknet_name: Optional[str] = None,
    preferred_profile: Optional[dict[str, Any]] = None,
    primary_label: Optional[str] = None,
    restart_label: Optional[str] = None,
    switch_label: Optional[str] = None,
    actions: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    recovery = recovery if isinstance(recovery, dict) else {}
    preferred_profile = preferred_profile if isinstance(preferred_profile, dict) else None
    resolved_actions = dedupe_action_entries(
        list(actions or []) + recovery_decision_actions_from_recovery(
            recovery,
            preferred_profile=preferred_profile,
        )
    )
    inferred_continue_label = next(
        (item["label"] for item in resolved_actions if str(item.get("label", "")).startswith("继续 ")),
        None,
    )
    inferred_restart_label = (
        str(restart_label).strip()
        if isinstance(restart_label, str) and restart_label.strip()
        else next((item["label"] for item in resolved_actions if str(item.get("label", "")).startswith("重新启动 ")), None)
    )
    inferred_switch_label = (
        str(switch_label).strip()
        if isinstance(switch_label, str) and switch_label.strip()
        else next((item["label"] for item in resolved_actions if str(item.get("label", "")).startswith("改按默认 ")), None)
    )

    last_worknet_key = str(recovery.get("lastWorknetKey") or "").strip() or None

    def prioritize_actions(preferred_label: Optional[str], *, status_hint: str) -> list[dict[str, Any]]:
        prioritized = prioritize_action_entries(
            resolved_actions,
            execution_state=None,
            resume_status=status_hint,
            worknet_key=last_worknet_key,
        )
        label = str(preferred_label or "").strip()
        if not label:
            return prioritized
        first = [item for item in prioritized if str(item.get("label")) == label]
        rest = [item for item in prioritized if str(item.get("label")) != label]
        return annotate_recovery_actions(first + rest)

    last_profile = resolve_worknet(str(recovery.get("lastWorknetKey") or ""))
    last_name = (
        str(last_profile.get("name"))
        if isinstance(last_profile, dict) and last_profile.get("name")
        else str(worknet_name or recovery.get("lastWorknetKey") or "上一次 WorkNet")
    )
    preferred_name = (
        str(preferred_profile.get("name"))
        if preferred_profile is not None and preferred_profile.get("name")
        else str(preferred_profile.get("key") or "默认 WorkNet")
        if preferred_profile is not None
        else None
    )
    stale_reason = humanize_recovery_stale_reason(recovery.get("staleLatestRunReason")) or "旧 run 已经不适合继续恢复"

    if (
        recovery.get("preferFreshStartOverResume")
        and preferred_profile is not None
        and last_profile is not None
        and str(preferred_profile.get("key")) != str(last_profile.get("key"))
    ):
        message = f"旧的 {last_name} 这次不建议再当成活跃现场继续。{stale_reason}。"
        if restart_label:
            message += f" 如果你只是想把旧路线临时接上，可以用“{restart_label}”。"
        if switch_label and preferred_name:
            message += f" 如果你想按当前默认偏好重新开工，更建议直接用“{switch_label}”，切回 {preferred_name}。"
        elif preferred_name:
            message += f" 如果你现在更想重新开工，更建议改按当前默认的 {preferred_name} 重新开始。"
        primary_action_label = inferred_switch_label or inferred_restart_label or inferred_continue_label or (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        resolved_actions = prioritize_actions(primary_action_label, status_hint="prefer_fresh_start")
        return {
            "decision": "prefer_fresh_start",
            "status": "prefer_fresh_start",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": stale_reason,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": f"旧的 {last_name} 这次不再继续。",
            "message": message,
        }

    if recovery.get("pendingConfirmations"):
        confirmation_label = str(recovery.get("defaultConfirmationLabel") or "").strip()
        message = "继续前先处理确认队列。"
        if confirmation_label:
            message = f"继续前先确认“{confirmation_label}”，因为它涉及资金类或不可逆动作。"
        primary_action_label = confirmation_label or (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        resolved_actions = prioritize_actions(primary_action_label, status_hint="needs_confirmation")
        return {
            "decision": "needs_confirmation",
            "status": "needs_confirmation",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": None,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": "当前有待确认动作。",
            "message": message,
        }

    if recovery.get("oldRunStopped"):
        primary_action_label = inferred_restart_label or inferred_continue_label or (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        message = f"上一次 {last_name} 已经停下。"
        if restart_label:
            message += f" 如果你想沿着同一条路线继续，直接用“{restart_label}”。"
        elif primary_action_label:
            message += f" 如果你现在就要继续，先用“{primary_action_label}”。"
        resolved_actions = prioritize_actions(primary_action_label, status_hint="restart_available" if restart_label else "resume_available")
        return {
            "decision": "restart_available" if restart_label else "resume_available",
            "status": "restart_available" if restart_label else "resume_available",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": stale_reason if recovery.get("staleLatestRun") else None,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": f"上一次 {last_name} 工作循环已经停下，可以继续从最近的记录续跑。",
            "message": message,
        }

    if recovery.get("activeBackgroundCount"):
        primary_action_label = (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        resolved_actions = prioritize_actions(primary_action_label, status_hint="background_running")
        return {
            "decision": "background_running",
            "status": "background_running",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": None,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": "已有工作循环在后台运行。",
            "message": "当前已经有后台任务在跑。继续的正确动作不是重新开一条新路线，而是先看日志、等下一次复盘，或者按下面动作查看/停止当前任务。",
        }

    if recovery.get("hasRuntimeGuidance") and recovery.get("followUpActionCount"):
        primary_action_label = (
            str(primary_label).strip()
            if isinstance(primary_label, str) and primary_label.strip()
            else (resolved_actions[0]["label"] if resolved_actions else None)
        )
        resolved_actions = prioritize_actions(primary_action_label, status_hint="follow_runtime_guidance")
        return {
            "decision": "follow_runtime_guidance",
            "status": "follow_runtime_guidance",
            "lastWorknetName": last_name,
            "preferredWorknetName": preferred_name,
            "staleReason": None,
            "primaryActionLabel": primary_action_label,
            "restartActionLabel": inferred_restart_label,
            "switchActionLabel": inferred_switch_label,
            "actions": resolved_actions,
            "headline": "上一次运行已经给出明确下一步。",
            "message": "上一次运行已经留下明确下一步。直接按下面第一条动作继续，不需要重新选 WorkNet。",
        }

    primary_action_label = inferred_continue_label or (
        str(primary_label).strip()
        if isinstance(primary_label, str) and primary_label.strip()
        else (resolved_actions[0]["label"] if resolved_actions else None)
    )
    message = f"当前会沿用最近一次保存的 {last_name} 路线继续。"
    if primary_action_label:
        message += f" 如果你现在就要继续，先用“{primary_action_label}”。"
    resolved_actions = prioritize_actions(primary_action_label, status_hint="resume_available")
    return {
        "decision": "resume_available",
        "status": "resume_available",
        "lastWorknetName": last_name,
        "preferredWorknetName": preferred_name,
        "staleReason": None,
        "primaryActionLabel": primary_action_label,
        "restartActionLabel": inferred_restart_label,
        "switchActionLabel": inferred_switch_label,
        "actions": resolved_actions,
        "headline": f"继续沿用最近一次的 {last_name}。",
        "message": message,
    }


def build_resume_recovery_briefing(
    recovery: Any,
    user_actions: list[dict[str, Any]],
    *,
    worknet_name: Optional[str] = None,
    preferred_profile: Optional[dict[str, Any]] = None,
    context_message: Optional[str] = None,
    action_map: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    recovery = recovery if isinstance(recovery, dict) else {}
    preferred_profile = preferred_profile if isinstance(preferred_profile, dict) else None
    restart_label = find_user_action_label(user_actions, prefix="重新启动 ")
    switch_label = find_user_action_label(user_actions, prefix="改按默认 ")
    primary_label = user_actions[0]["label"] if user_actions else None
    context = str(context_message or "").strip()
    decision = build_recovery_decision(
        recovery,
        worknet_name=worknet_name,
        preferred_profile=preferred_profile,
        primary_label=primary_label,
        restart_label=restart_label,
        switch_label=switch_label,
        actions=recovery_decision_actions_from_ui(
            user_actions,
            action_map if isinstance(action_map, dict) else {},
            primary_label=primary_label,
            restart_label=restart_label,
            switch_label=switch_label,
        ),
    )

    def combine(message: str) -> str:
        body = message.strip()
        if not context or context == body:
            return body
        return f"{context} {body}".strip()
    return {
        "headline": context or str(decision.get("headline") or ""),
        "message": combine(str(decision.get("message") or "")),
        "status": str(decision.get("status") or "resume_available"),
        "decision": decision,
    }


def run_response_primary_action(response: dict[str, Any]) -> Optional[str]:
    queue = normalized_confirmation_queue(response.get("confirmationQueue", []))
    if queue:
        label = queue[0].get("label")
        if isinstance(label, str) and label.strip():
            return label.strip()
    follow_up_actions = normalized_follow_up_actions(response.get("followUpActions", []))
    if follow_up_actions:
        default_follow_up = choose_default_follow_up_action(follow_up_actions) or follow_up_actions[0]
        label = default_follow_up.get("label")
        if isinstance(label, str) and label.strip():
            return label.strip()
    runtime_guidance = response.get("runtimeGuidance", {})
    if isinstance(runtime_guidance, dict):
        actions = runtime_guidance.get("userActions", [])
        if isinstance(actions, list):
            for item in actions:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    active = response.get("activeBackgroundProcesses", [])
    if isinstance(active, list) and len(active) == 1 and isinstance(active[0], dict):
        label = active[0].get("label")
        if isinstance(label, str) and label.strip():
            return f"查看 {label.strip()}"
    selected = response.get("selectedBackground")
    if isinstance(selected, dict):
        label = selected.get("label")
        if isinstance(label, str) and label.strip():
            return f"查看 {label.strip()}"
    return None


def build_run_response_briefing(
    response: dict[str, Any],
    *,
    preferences: Optional[dict[str, Any]] = None,
    recovery: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    playbook_source = str(response.get("playbookSource") or "").strip()
    selected_key = str(response.get("selectedWorknetKey") or "").strip().lower()
    selected_name = str(response.get("selectedWorknetName") or response.get("selectedWorknetKey") or "WorkNet").strip()
    next_action = str(response.get("nextAction") or "").strip()
    status = str(response.get("status") or "").strip()
    runtime_guidance = response.get("runtimeGuidance", {})
    runtime_guidance = runtime_guidance if isinstance(runtime_guidance, dict) else {}
    active_background = response.get("activeBackgroundProcesses", [])
    selected_background = response.get("selectedBackground")
    recovery = recovery if isinstance(recovery, dict) else {}
    primary_action = run_response_primary_action(response)
    preferred_profile = resolve_worknet(str((preferences or {}).get("preferredWorknet") or ""))
    decision = build_recovery_decision(
        recovery,
        worknet_name=selected_name,
        preferred_profile=preferred_profile,
        primary_label=primary_action,
        actions=recovery_decision_actions_from_run_response(
            response,
            primary_label=primary_action,
        ),
    )
    queue = normalized_confirmation_queue(response.get("confirmationQueue", []))
    worknet_context_key = selected_key or str(recovery.get("lastWorknetKey") or "").strip().lower()
    knowledge_catalog = load_or_build_knowledge_catalog()
    knowledge_context = compact_knowledge_context(
        knowledge_context_for_worknet(knowledge_catalog, worknet_context_key)
    )
    knowledge_reference_highlights = knowledge_related_reference_highlights(
        knowledge_catalog,
        knowledge_context,
    ) if isinstance(knowledge_context, dict) else []
    knowledge_source_highlights = knowledge_related_source_highlights(
        knowledge_catalog,
        knowledge_context,
    ) if isinstance(knowledge_context, dict) else []

    headline = None
    user_message = None
    if playbook_source == "preferred-worknet-over-stale-run":
        stale_reason = str(decision.get("staleReason") or "旧 run 已经不适合继续恢复")
        headline = f"旧的 {decision.get('lastWorknetName') or selected_name} 这次不再继续，已改按默认 {selected_name} 起步。"
        user_message = f"{stale_reason}。当前继续路径会直接改按 {selected_name} 的 playbook 走。"
    elif playbook_source == "preferred-worknet":
        headline = f"没有现成 playbook，已改按默认 {selected_name} 起步。"
        user_message = f"当前 state 里没有最近选择的 playbook，所以 workstation 直接回退到默认的 {selected_name}。"
    elif status == "background_running":
        if isinstance(active_background, list) and len(active_background) == 1 and isinstance(active_background[0], dict):
            summary = active_background[0].get("summary", {})
            background_headline = summary.get("headline") if isinstance(summary, dict) else None
            headline = str(background_headline).strip() if isinstance(background_headline, str) and background_headline.strip() else "后台任务仍在运行。"
            user_message = "当前已经有后台任务在跑。继续的正确动作不是再起一条新路线，而是先看日志、等复盘，或按需停止它。"
        else:
            headline = str(runtime_guidance.get("message") or "后台任务仍在运行。").strip()
            user_message = "当前已经有后台任务在跑。继续的正确动作是先看后台状态，而不是重新开始。"
        user_message = prepend_canonical_worknet_plain(user_message, worknet_context_key)
    elif isinstance(selected_background, dict):
        label = str(selected_background.get("label") or "当前后台任务").strip()
        if status == "stopped":
            headline = f"{label} 已停止。"
            user_message = "当前后台任务已经停下；如果还想继续，需要重新开始一条工作路径。"
        elif status == "failed":
            headline = f"{label} 停止失败。"
            user_message = "停止后台任务时遇到了错误，先看日志或进程状态再决定下一步。"
        elif status == "needs_confirmation":
            headline = f"{label} 等待停止确认。"
            user_message = "这是一个会影响当前后台任务的动作，正式停止前还需要再确认一次。"
    elif response.get("confirmationQueue"):
        first_label = queue[0].get("label") if queue else None
        headline = "当前有待确认动作。"
        if isinstance(first_label, str) and first_label.strip():
            user_message = f"继续前先确认“{first_label.strip()}”，因为它涉及资金类或不可逆动作。"
        else:
            user_message = "继续前先处理确认队列里的动作。"
        caution = canonical_worknet_caution_text(worknet_context_key)
        if caution and caution not in user_message:
            user_message = f"{user_message} {caution}".strip()
        user_message = prepend_canonical_worknet_plain(user_message, worknet_context_key)
        decision = {
            **decision,
            "decision": "needs_confirmation",
            "status": "needs_confirmation",
            "headline": headline,
            "message": user_message,
            "primaryActionLabel": str(first_label).strip() if isinstance(first_label, str) and first_label.strip() else decision.get("primaryActionLabel"),
        }
    elif next_action == "follow_runtime_guidance":
        headline = str(runtime_guidance.get("message") or f"{selected_name} 已有明确下一步。").strip()
        user_message = "上一次运行已经留下明确下一步；继续时直接沿着这条 guidance 走，不需要重新选 WorkNet。"
        loop = canonical_worknet_loop_text(worknet_context_key)
        if loop:
            user_message = f"{user_message} {loop}".strip()
        user_message = prepend_canonical_worknet_plain(user_message, worknet_context_key)
        decision = {
            **decision,
            "decision": "follow_runtime_guidance",
            "status": "follow_runtime_guidance",
            "headline": headline,
            "message": user_message,
        }
    elif playbook_source == "last-selected" and selected_name:
        headline = str(decision.get("headline") or f"继续沿用上次选择的 {selected_name}。")
        if next_action == "execute_when_ready":
            user_message = str(decision.get("message") or f"当前会沿用最近一次保存的 {selected_name} playbook。")
        elif next_action == "review_epoch":
            user_message = f"{selected_name} 这轮命令已经跑完，下一步先看复盘。"
        else:
            user_message = str(decision.get("message") or f"当前会沿用最近一次保存的 {selected_name} 路线继续。")
    elif playbook_source == "worknet" and selected_name:
        headline = f"已切到 {selected_name}。"
        if next_action == "execute_when_ready":
            user_message = f"{selected_name} 的 playbook 已准备好。"
            if primary_action:
                user_message += f" 如果你现在就要继续，先用“{primary_action}”。"
        else:
            user_message = f"{selected_name} 的工作路径已经准备好，接下来按当前下一步继续。"
    elif next_action == "review_epoch":
        headline = f"{selected_name or '这条工作路径'} 这轮已经跑完。"
        user_message = "当前最该做的是先看复盘，再决定要不要继续下一轮。"
    elif next_action == "execute_when_ready" and selected_name:
        headline = f"{selected_name} 已准备好。"
        user_message = "当前还在计划阶段。"
        if primary_action:
            user_message += f" 如果你现在就要继续，先用“{primary_action}”。"
    if headline is None:
        headline = str(runtime_guidance.get("message") or "Work loop 状态已更新。").strip()
    if user_message is None:
        user_message = headline
    if selected_key and playbook_source in {"preferred-worknet-over-stale-run", "preferred-worknet", "last-selected", "worknet"}:
        user_message = prepend_canonical_worknet_plain(user_message, selected_key)
    if isinstance(knowledge_context, dict) and str(knowledge_context.get("freshnessStatus") or "") == "affected":
        label = str(knowledge_context.get("label") or selected_name or worknet_context_key or "当前 WorkNet").strip()
        source_note = reporter_source_note(knowledge_source_highlights)
        reminder = f"{label} 这条高层知识当前也有上游变更，继续自动运行前最好先复核官方来源。"
        if source_note:
            reminder = f"{reminder} {source_note}".strip()
        if reminder not in str(user_message):
            user_message = f"{str(user_message).strip()} {reminder}".strip()
    user_action_details = action_details_from_decision(decision)
    if isinstance(knowledge_context, dict):
        label = str(knowledge_context.get("label") or selected_name or worknet_context_key or "当前 WorkNet").strip()
        append_unique_action_detail(
            user_action_details,
            label=f"查看 {label} 档案",
            description=knowledge_action_description(knowledge_context),
            command=knowledge_context.get("queryCommand"),
        )
        primary_knowledge_command = str(knowledge_context.get("primaryCommand") or "").strip()
        query_command = str(knowledge_context.get("queryCommand") or "").strip()
        if primary_knowledge_command and primary_knowledge_command != query_command:
            append_unique_action_detail(
                user_action_details,
                label=f"重审 {label}",
                description=knowledge_refresh_action_description(knowledge_context),
                command=primary_knowledge_command,
            )
    for item in knowledge_source_highlights[:2]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        append_unique_action_detail(
            user_action_details,
            label=f"查看来源 {label}",
            description=knowledge_source_action_description(item),
            command=item.get("queryCommand"),
        )
        primary_command = str(item.get("primaryCommand") or "").strip()
        query_command = str(item.get("queryCommand") or "").strip()
        if primary_command and primary_command != query_command:
            append_unique_action_detail(
                user_action_details,
                label=f"重读来源 {label}",
                description=f"重新拉取 {label}，确认上游变化有没有影响当前工作路线。",
                command=primary_command,
            )
    resume_status = str(decision.get("status") or "").strip() or None
    execution_state = derive_runtime_execution_state(
        response,
        headline=headline,
        recovery=recovery,
    )
    user_action_details = prioritize_action_entries(
        user_action_details,
        execution_state=execution_state.get("executionState"),
        resume_status=resume_status,
        worknet_key=worknet_context_key,
    )
    user_action_details = annotate_execution_actions(user_action_details)
    if primary_action is None and isinstance(decision.get("primaryActionLabel"), str) and decision.get("primaryActionLabel"):
        primary_action = str(decision.get("primaryActionLabel"))
    primary_user_action_display = None
    primary_user_action_command = None
    if primary_action:
        matched = next(
            (item for item in user_action_details if str(item.get("label") or "").strip() == str(primary_action).strip()),
            None,
        )
        if isinstance(matched, dict):
            if isinstance(matched.get("displayLabel"), str) and matched.get("displayLabel"):
                primary_user_action_display = str(matched["displayLabel"])
            if isinstance(matched.get("command"), str) and matched.get("command"):
                primary_user_action_command = str(matched["command"])
    if primary_action is None and user_action_details:
        primary_action = str(user_action_details[0].get("label") or "").strip() or None
    if primary_user_action_display is None and user_action_details:
        primary_user_action_display = str(user_action_details[0].get("displayLabel") or "") or None
    if primary_user_action_command is None and user_action_details:
        primary_user_action_command = str(user_action_details[0].get("command") or "") or None
    user_message = align_run_execution_user_message(
        user_message,
        execution_state=execution_state.get("executionState"),
        execution_headline=execution_state.get("executionHeadline"),
        primary_action=primary_action,
        worknet_context_key=worknet_context_key,
    )
    return {
        "headline": headline,
        "userMessage": user_message,
        "resumeStatus": resume_status,
        "resumeStatusDisplay": recovery_status_display(resume_status) if resume_status else None,
        "executionState": execution_state.get("executionState"),
        "executionStateDisplay": execution_state.get("executionStateDisplay"),
        "executionHeadline": execution_state.get("executionHeadline"),
        "primaryUserAction": primary_action,
        "primaryUserActionDisplay": primary_user_action_display,
        "primaryUserActionCommand": primary_user_action_command,
        "userActionDetails": user_action_details,
        "knowledgeContext": knowledge_context,
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "recoveryDecision": decision if decision.get("decision") else None,
    }


def runtime_follow_up_description(worknet_key: str, label: str) -> str:
    if worknet_key == "mine":
        if label == "Basic Amazon Products Dataset":
            return "先用这个数据集开始第一轮采集。"
        if label == "Basic Amazon Products Pending Dataset":
            return "切到待审核版 Amazon 商品数据开始采集。"
        if label == "Amazon Reviews Dataset":
            return "改跑评论数据，先熟悉提交流程。"
        return "用这个数据集开始 Mine 的下一轮工作。"
    if worknet_key == "gov":
        if label == "查看 Gov 可做动作":
            return "先看这期 Gov 还能做哪些公开动作。"
        if label == "查看 Gov markets":
            return "直接看当前公开市场、所处阶段和时间窗口。"
        if label == "阅读 staking 说明":
            return "先弄清怎么拿到 AWP Power，再回来继续。"
        return "先继续 Gov 的公开观察步骤。"
    if worknet_key == "predict":
        if "静默 loop" in label or "静默循环" in label:
            return "把 Predict 挂到后台持续运行。"
        if "汇报每轮" in label:
            return "启动 Predict，并在每轮后汇报结果。"
    return "继续上一次运行建议的下一步。"


def humanize_review_step(worknet_key: str, step: dict[str, Any], payload: Any) -> Optional[str]:
    label = str(step.get("label") or "")
    status = str(step.get("status") or "").strip().lower()
    message = runtime_message(payload)
    state = str(payload.get("state") or "") if isinstance(payload, dict) else ""
    if worknet_key == "mine":
        if label == "mine agent status" and status == "ok":
            loop = canonical_worknet_loop_text("mine")
            if loop:
                return f"Mine 运行环境已经就绪。{loop}"
            return "Mine 运行环境已经就绪。"
        if label == "mine control status" and status == "ok":
            loop = canonical_worknet_loop_text("mine")
            if loop:
                return f"Mine 当前没有活跃任务会话，等你选定数据集后就能开始。{loop}"
            return "Mine 当前没有活跃任务会话，等你选定数据集后就能开始。"
        if label == "start mine worker" and state == "selection_required":
            return "Mine 已进入数据集选择阶段，下一步只需要选一个数据集开始第一轮采集。"
        if label == "start mine worker" and message:
            return f"Mine 采集循环已返回下一步提示：{message}"
    if worknet_key == "gov":
        if label == "gov public markets" and status == "ok":
            items = payload.get("items") if isinstance(payload, dict) else None
            if isinstance(items, list) and items:
                first = items[0] if isinstance(items[0], dict) else {}
                market_name = str(first.get("name") or "").strip()
                if market_name:
                    return f"Gov 已读取本期 {len(items)} 个公开市场，当前最先看到的是 {market_name}。"
                return f"Gov 已读取本期 {len(items)} 个公开市场和时间窗口。"
            return "Gov 已读取本期公开市场和时间窗口。"
        if label == "gov phase-aware helper" and (status == "ok" or payload):
            phase = humanize_phase_value(payload.get("phase") if isinstance(payload, dict) else None)
            caution = canonical_worknet_caution_text("gov")
            if isinstance(phase, str) and phase.strip():
                if caution:
                    return f"Gov 已确认当前处于{phase}阶段，先按这一阶段的公开动作观察。{caution}"
                return f"Gov 已确认当前处于{phase}阶段，先按这一阶段的公开动作观察。"
            if caution:
                return f"Gov 已确认这期可做的公开动作。{caution}"
            return "Gov 已确认这期可做的公开动作。"
    if worknet_key == "predict":
        if label == "predict wallet safety" and status == "ok":
            data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
            address = str(data.get("address") or "").strip()
            if address:
                return f"Predict 钱包已就绪：{address}。"
            return "Predict 钱包已就绪。"
        lowered = str(message or "").strip().lower()
        if label in {"predict context", "查看 Predict context"}:
            if "no candidate market found" in lowered or "no suitable market" in lowered:
                return "Predict 当前没有合适市场，先等下一轮，再回来重拉上下文。"
            if message:
                return f"Predict 上下文已更新：{message}"
        if label == "predict status":
            data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
            balance = str(data.get("balance") or "").strip()
            total_predictions = str(data.get("total_predictions") or "").strip()
            timeslot = data.get("timeslot") if isinstance(data.get("timeslot"), dict) else {}
            remaining = str(timeslot.get("submissions_remaining") or "").strip()
            if total_predictions or balance or remaining:
                details: list[str] = []
                if total_predictions:
                    details.append(f"累计 {total_predictions} 次预测")
                if balance:
                    details.append(f"当前余额 {balance} 芯片")
                if remaining:
                    details.append(f"本时段还剩 {remaining} 次提交")
                return f"Predict 运行状态已同步：{'，'.join(details)}。"
            if message:
                return f"Predict 运行状态已更新：{message}"
            if status == "ok":
                return "Predict 运行状态已经更新。"
        if label == "predict stake eligibility":
            if message:
                return f"Predict 已完成资格检查：{message}"
            if status == "ok":
                return "Predict 已完成当前这轮资格检查。"
    if worknet_key == "ardi":
        if label == "ardi status":
            data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
            balance_eth = data.get("balance_eth")
            coord_reachable = data.get("coord_reachable")
            agent_state = data.get("agent_state") if isinstance(data.get("agent_state"), dict) else {}
            remaining_mint_cap = agent_state.get("remainingMintCap")
            details: list[str] = []
            if balance_eth is not None:
                details.append(f"Base ETH 余额 {balance_eth:.6f} ETH" if isinstance(balance_eth, (int, float)) else f"Base ETH 余额 {balance_eth} ETH")
            if coord_reachable is True:
                details.append("协调器可达")
            elif coord_reachable is False:
                details.append("协调器暂时不可达")
            if remaining_mint_cap is not None:
                details.append(f"当前还剩 {remaining_mint_cap} 次可铸造额度")
            if details:
                return f"Ardi 当前状态已更新：{'，'.join(details)}。"
            if message:
                return f"Ardi 当前状态已更新：{message}"
            if status == "ok":
                return "Ardi 当前状态已更新。"
        if label == "ardi preflight":
            if message:
                return f"Ardi 预检已返回最新结果：{message}"
            if status == "ok":
                return "Ardi 预检已完成。"
    return None


def humanize_review_failure(worknet_key: str, step: dict[str, Any], payload: Any) -> Optional[str]:
    label = str(step.get("label") or "")
    detail = runtime_payload_error_summary(payload) or runtime_message(payload)
    lowered_detail = str(detail or "").lower()
    if worknet_key == "gov" and label == "gov private state":
        return "这期你的 principal 还没有 AWP Power，所以签名投票和交易还不能做。"
    if worknet_key == "gov" and label in {"gov public markets", "gov phase-aware helper"}:
        if "name or service not known" in lowered_detail:
            return "Gov 当前连不上上游服务，先检查网络或域名解析。"
        if detail:
            return f"Gov 当前还没拉到最新公开数据：{detail}"
    if worknet_key == "predict":
        error = payload.get("error") if isinstance(payload, dict) else None
        error_code = str(error.get("code") or "") if isinstance(error, dict) else ""
        suggestion = str(error.get("suggestion") or "").strip() if isinstance(error, dict) else ""
        if label == "predict stake eligibility":
            if error_code == "NOT_STAKED":
                return "Predict 这轮还不能正式提交，因为 1000 AWP 资格或 KYA 委托路径还没到位。"
            if error_code == "STAKE_FETCH_FAILED":
                return "Predict 这轮卡在资格检查，当前还没拿到稳定的 stake 结果。"
            if suggestion:
                return f"Predict 这轮还不能正式提交：{suggestion}"
        if label in {"查看 Predict context", "predict context"}:
            if detail:
                return f"Predict 当前没有合适市场或上下文还不够稳定：{detail}"
            return "Predict 当前没有合适市场，先等下一轮，不要为了出手而重复推理。"
        if label == "predict status" and detail:
            if "check coordinator connectivity" in lowered_detail:
                return "Predict 运行时当前还没进入稳定循环，先检查协调器连通性。"
            return f"Predict 运行时当前还没进入稳定循环：{detail}"
        if label == "predict wallet safety" and detail:
            return f"Predict 钱包检查还没通过：{detail}"
    if worknet_key == "ardi":
        data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
        suggestion = str(data.get("suggestion") or "").strip() if isinstance(data, dict) else ""
        if label == "ardi status":
            if "all base rpcs failed" in lowered_detail:
                return "Ardi 当前连不上 Base RPC，先检查网络或可用 RPC。"
            if detail:
                return f"Ardi 当前状态还没拉到稳定结果：{detail}"
        if label == "ardi gas check":
            if suggestion:
                return f"Ardi 这轮还没进入提交承诺和揭示阶段，因为 Base Gas 还没补齐：{suggestion}"
            return "Ardi 这轮还没进入提交承诺和揭示阶段，因为 Base Gas 还没补齐。"
        if label == "ardi stake guidance":
            if suggestion.startswith("Reach the 10000 AWP threshold on EITHER Ardi"):
                return "Ardi 这轮还没进入提交承诺和揭示阶段，因为资格路径还没满足：先满足 Ardi 或 KYA 任一条 10000 AWP 资格路径，再回来重跑。"
            if suggestion:
                return f"Ardi 这轮还没进入提交承诺和揭示阶段，因为资格路径还没满足：{suggestion}"
            return "Ardi 这轮还没进入提交承诺和揭示阶段，因为资格路径还没满足。"
        if label == "ardi preflight" and detail:
            return f"Ardi 预检还没通过，所以这轮还不能进入提交承诺和揭示阶段：{detail}"
    if worknet_key == "mine" and label == "start mine worker":
        if detail:
            return f"Mine 还没真正开始采集：{detail}"
        return "Mine 还没真正开始采集。"
    return None


def humanize_review_step_label(worknet_key: str, label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return "未命名步骤"
    mapping = {
        "mine agent status": "Mine 环境检查",
        "mine control status": "Mine 控制状态",
        "start mine worker": "启动 Mine 采集循环",
        "predict status": "Predict 运行状态",
        "predict stake eligibility": "Predict 资格检查",
        "predict context": "Predict 上下文",
        "查看 Predict context": "Predict 上下文",
        "gov public markets": "Gov 公开市场",
        "gov phase-aware helper": "Gov 阶段判断",
        "gov private state": "Gov 私有状态",
        "ardi status": "Ardi 当前状态",
        "ardi gas check": "Ardi 手续费检查",
        "ardi stake guidance": "Ardi 资格检查",
        "ardi preflight": "Ardi 预检",
    }
    return mapping.get(text, text)


def humanize_review_status_token(
    worknet_key: str,
    label: str,
    status: Any,
) -> Optional[str]:
    code = str(status or "").strip().lower()
    if not code:
        return None
    if code == "planned":
        if worknet_key == "mine" and label == "start mine worker":
            return "Mine 采集循环已经准备好，但还没真正启动。"
        if worknet_key == "predict":
            return "Predict 这一步已经准备好，但还没真正执行。"
        if worknet_key == "gov":
            return "Gov 这一步已经准备好，但还没真正执行。"
        if worknet_key == "ardi":
            return "Ardi 这一步已经准备好，但还没真正执行。"
        return "这一步已经准备好，但还没真正执行。"
    if code == "ok":
        return "这一步已经完成。"
    if code == "failed":
        return "这一步执行失败。"
    if code == "missing_runtime_command":
        return "当前缺少可执行的 runtime 命令。"
    if code == "missing_parameters":
        return "这一步还缺少必要输入。"
    if code == "queued_for_confirmation":
        return "这一步已经进入确认队列。"
    if code == "awaiting_confirmation":
        return "这一步正在等待确认。"
    if code == "available_manual":
        return "这一步已经准备好，等你手动继续。"
    if code == "skipped_after_primary_work":
        return "主工作步骤已经执行过了，这一步保留给后续手动控制。"
    if code == "blocked_after_previous_step":
        return "前一步已经决定先停在这里，这一步暂不继续。"
    if code == "started_background":
        return "这一步已经转入后台运行。"
    if code == "background_running":
        return "这一步启动的后台任务仍在运行。"
    return None


def review_action_command(
    worknet_key: str,
    label: str,
    *,
    command: Optional[str],
    safe_to_auto_run: bool,
    requires_confirmation: bool,
) -> Optional[str]:
    if requires_confirmation:
        return workstation_follow_up_command(label, execute=False)
    if safe_to_auto_run:
        return workstation_follow_up_command(label, execute=True)
    if isinstance(command, str) and command.strip():
        return command.strip()
    return None


def humanize_review_action_entry(
    worknet_key: str,
    label: str,
    *,
    command: Optional[str],
    safe_to_auto_run: bool,
    requires_confirmation: bool,
) -> str:
    resolved_command = review_action_command(
        worknet_key,
        label,
        command=command,
        safe_to_auto_run=safe_to_auto_run,
        requires_confirmation=requires_confirmation,
    )
    prefix = label
    if worknet_key == "mine":
        prefix = label
    elif worknet_key == "gov":
        prefix = label
    if resolved_command:
        return f"{prefix}: {resolved_command}"
    return prefix


def humanize_review_action_label(worknet_key: str, label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return text
    mapping = {
        "查看 Gov markets": "查看 Gov 公开市场",
        "查看 Gov 可做动作": "查看 Gov 当前可做动作",
        "阅读 staking 说明": "阅读质押说明",
        "查看 Predict context": "查看 Predict 市场上下文",
        "predict context": "查看 Predict 市场上下文",
        "重跑 Predict stake 检查": "重跑 Predict 资格检查",
        "启动 Predict loop（静默）": "启动 Predict 静默循环",
        "启动 Predict loop（汇报每轮）": "启动 Predict 循环并逐轮汇报",
        "启动 Predict 静默循环": "启动 Predict 静默循环",
        "启动 Predict 循环（逐轮汇报）": "启动 Predict 循环并逐轮汇报",
        "补 Base Gas": "补 Base 手续费",
        "重跑 Ardi preflight": "重跑 Ardi 预检",
        "重跑 Ardi stake 检查": "重跑 Ardi 资格检查",
        "submit gov order": "提交 Gov 限价单",
        "Basic Amazon Products Dataset": "开始 Amazon 商品基础数据集",
        "Basic Amazon Products Pending Dataset": "开始 Amazon 商品待审核数据集",
        "Amazon Reviews Dataset": "开始 Amazon 评论数据集",
    }
    return mapping.get(text, text)


def humanize_public_action_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return text
    return humanize_review_action_label("", text)


def humanize_review_confirmation_label(worknet_key: str, label: str) -> str:
    display = humanize_review_action_label(worknet_key, label)
    prefix = f"确认并执行 {display}"
    if worknet_key == "gov":
        prefix = f"确认 Gov 动作 {display}"
    elif worknet_key == "predict":
        prefix = f"确认 Predict 动作 {display}"
    elif worknet_key == "ardi":
        prefix = f"确认 Ardi 动作 {display}"
    return prefix


def humanize_review_confirmation_entry(worknet_key: str, label: str) -> str:
    prefix = humanize_review_confirmation_label(worknet_key, label)
    return f"{prefix}: {workstation_confirmation_command(label, execute=False)}"


def append_unique_action_detail(
    items: list[dict[str, Any]],
    *,
    label: Optional[str],
    display_label: Optional[str] = None,
    description: Optional[str],
    command: Optional[str],
) -> None:
    text = str(label or "").strip()
    resolved_command = str(command or "").strip()
    if not text or not resolved_command:
        return
    if any(isinstance(item, dict) and item.get("label") == text for item in items):
        return
    items.append(
        {
            "label": text,
            "displayLabel": str(display_label or humanize_public_action_label(text)).strip() or humanize_public_action_label(text),
            "description": str(description or "继续这个建议动作。").strip(),
            "command": resolved_command,
        }
    )


def humanize_public_action_description(label: str, description: str) -> str:
    text = str(description or "").strip()
    label_text = str(label or "").strip()
    if not text:
        return text
    replacements = {
        "WorkNet playbook": "工作路线",
        "默认 WorkNet 的 playbook": "默认工作路线",
        "runtime 建议动作": "工作站刚建议的下一步",
        "后台工作循环": "后台工作任务",
        "后台任务": "后台工作任务",
        "官方 runtime": "官方运行环境",
        "本地 runtime": "本地运行环境",
        "runtime ": "运行环境 ",
        " dataset ": " 数据集 ",
    }
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    direct_map = {
        "继续沿用最近一次保存的 WorkNet playbook。": "继续沿用上一次保存的这条工作路线。",
        "继续这个恢复动作。": "继续这条恢复路线。",
        "继续这个建议动作。": "继续这条建议动作。",
        "继续这条 runtime 建议动作。": "继续工作站刚建议的这一步。",
        "直接按当前默认 WorkNet 的 playbook 继续。": "直接按当前默认工作路线继续。",
        "确认并执行这个待确认动作。": "确认后才会真正执行这一步。",
        "停止当前唯一的后台工作循环。": "停止当前唯一的后台工作任务。",
        "先看这个后台任务的最近状态和日志。": "先看这个后台工作任务的最近状态和日志。",
        "停止这个后台任务。": "停止这个后台工作任务。",
    }
    if text in direct_map:
        normalized = direct_map[text]
    if label_text == "查看上次复盘":
        normalized = "先看最近一次工作记录、收益样本和下一步动作。"
    return normalized


def humanize_public_action_entries(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    entries: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        normalized = dict(item)
        normalized["label"] = label
        normalized["description"] = humanize_public_action_description(
            label,
            str(item.get("description") or "继续这个建议动作。").strip(),
        )
        entries.append(normalized)
    return entries


def humanize_public_recovery_decision(decision: Any) -> Any:
    if not isinstance(decision, dict):
        return decision
    normalized = dict(decision)
    normalized["statusDisplay"] = recovery_status_display(decision.get("status"))
    raw_actions = decision.get("actions") if isinstance(decision.get("actions"), list) else []
    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in raw_actions
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    normalized_actions = humanize_public_action_entries(raw_actions)
    normalized["actions"] = annotate_recovery_actions(prioritize_ui_actions(
        normalized_actions,
        action_map,
        execution_state=None,
        resume_status=str(decision.get("status") or "").strip() or None,
        worknet_key=None,
    ))
    if normalized["actions"]:
        normalized["primaryActionLabel"] = str(normalized["actions"][0].get("label") or "").strip() or normalized.get("primaryActionLabel")
    return normalized


def action_details_from_ui_actions(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        description = humanize_public_action_description(
            label,
            str(item.get("description") or "继续这个建议动作。").strip(),
        )
        command = action_map.get(label)
        append_unique_action_detail(
            details,
            label=label,
            description=description,
            command=command if isinstance(command, str) else None,
        )
    return details


def prioritize_ui_actions(
    actions: list[dict[str, Any]],
    action_map: dict[str, str],
    *,
    execution_state: Optional[str],
    resume_status: Optional[str] = None,
    worknet_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        entries.append(
            {
                "label": label,
                "description": str(item.get("description") or "继续这个建议动作。").strip(),
                "command": str(action_map.get(label) or "").strip() or None,
            }
        )
    prioritized = prioritize_action_entries(
        entries,
        execution_state=execution_state,
        resume_status=resume_status,
        worknet_key=worknet_key,
    )
    return [
        {
            "label": str(item.get("label") or "").strip(),
            "description": str(item.get("description") or "继续这个建议动作。").strip(),
        }
        for item in prioritized
        if str(item.get("label") or "").strip()
    ]


def action_details_from_decision(decision: Any) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    if not isinstance(decision, dict):
        return details
    actions = decision.get("actions")
    if not isinstance(actions, list):
        return details
    for item in actions:
        if not isinstance(item, dict):
            continue
        append_unique_action_detail(
            details,
            label=str(item.get("label") or "").strip(),
            description=humanize_public_action_description(
                str(item.get("label") or "").strip(),
                str(item.get("description") or "继续这个建议动作。").strip(),
            ),
            command=str(item.get("command") or "").strip(),
        )
    return details


def humanize_review_action_description(
    worknet_key: str,
    label: str,
    *,
    requires_confirmation: bool = False,
) -> str:
    text = str(label or "").strip()
    if requires_confirmation:
        if worknet_key == "gov":
            return "确认后才会真正提交这条 Gov 签名动作。"
        if worknet_key == "predict":
            return "确认后才会真正提交这条 Predict 正式动作。"
        if worknet_key == "ardi":
            return "确认后才会真正执行这条 Ardi 动作。"
        return "确认并执行这个待确认动作。"
    mapping = {
        "查看 Gov markets": "直接看当前公开市场、所处阶段和时间窗口。",
        "查看 Gov 可做动作": "先看这期 Gov 还有哪些公开动作和受限动作。",
        "阅读 staking 说明": "先看质押和 AWP Power 怎么影响后续资格。",
        "查看 Predict context": "重新看一轮 Predict 的市场上下文，再决定要不要继续。",
        "predict context": "重新看一轮 Predict 的市场上下文，再决定要不要继续。",
        "重跑 Predict stake 检查": "重查 Predict 的资格路径，看现在能不能继续。",
        "启动 Predict loop（静默）": "让 Predict 在后台持续观察并形成观点，不逐轮打断你。",
        "启动 Predict loop（汇报每轮）": "启动 Predict，并在每轮结束后汇报结果。",
        "启动 Predict 静默循环": "让 Predict 在后台持续观察并形成观点，不逐轮打断你。",
        "启动 Predict 循环（逐轮汇报）": "启动 Predict，并在每轮结束后汇报结果。",
        "重跑 Ardi preflight": "重新检查 Ardi 的手续费、资格和下一步命令。",
        "重跑 Ardi stake 检查": "重查 Ardi 的资格路径，看现在能不能继续。",
        "补 Base Gas": "先补 Base 链手续费，再回来继续 Ardi。",
        "自动买并质押": "通过官方路径自动买入并质押，补齐 Ardi 资格。",
        "走 KYA 委托路径": "改走 KYA 委托资格路径，再回来继续。",
        "Basic Amazon Products Dataset": "先从 Amazon 商品基础数据集开始第一轮采集。",
        "Basic Amazon Products Pending Dataset": "切到 Amazon 商品待审核数据集开始采集。",
        "Amazon Reviews Dataset": "先用 Amazon 评论数据熟悉提交流程。",
    }
    if text in mapping:
        return mapping[text]
    return runtime_follow_up_description(worknet_key, text)


def action_priority_key(
    execution_state: Optional[str],
    resume_status: Optional[str],
    *,
    label: Any,
    command: Optional[str] = None,
    worknet_key: Optional[str] = None,
) -> tuple[int, str]:
    status = str(execution_state or resume_status or "").strip()
    text = str(label or "").strip()
    command_text = str(command or "").strip()
    lowered = text.lower()
    is_source_view = text.startswith("查看来源 ")
    is_source_refresh = text.startswith("重读来源 ")
    is_source = is_source_view or is_source_refresh
    is_knowledge_refresh = text.startswith("重审 ")
    is_knowledge_view = text.startswith("查看 ") and text.endswith(" 档案")
    is_knowledge = is_knowledge_view or is_knowledge_refresh
    is_continue = text.startswith("继续 ")
    is_restart = text.startswith("重新启动 ")
    is_switch_default = text.startswith("改按默认 ")
    is_confirmation = text.startswith("确认 ") or "--confirm-label" in command_text
    is_dataset = text in {
        "开始 Amazon 商品基础数据集",
        "开始 Amazon 商品待审核数据集",
        "开始 Amazon 评论数据集",
    }
    is_review = text == "查看上次复盘" or command_text.startswith("python3 scripts/review-epoch.py")
    is_research = text == "研究 AWP 百科" or "--intent research" in command_text
    is_background_inspect = "--background-label" in command_text and not "--stop-background-label" in command_text
    is_background_stop = "--stop-background-label" in command_text or text.startswith("停止 ")
    is_pause = "--pause" in command_text or text == "暂停当前运行"
    is_playbook = command_text.startswith("python3 scripts/build-playbook.py")
    is_query_source = command_text.startswith("python3 scripts/query-source.py")
    is_query_knowledge = command_text.startswith("python3 scripts/query-knowledge.py")
    is_run_command = command_text.startswith("python3 scripts/run-workstation.py")
    is_scan = command_text.startswith("python3 scripts/scan-worknets.py")
    is_inspect = (
        command_text.startswith("python3 /")
        or command_text.startswith("python3 scripts/inspect-skill.py")
        or (command_text and not command_text.startswith("python3 scripts/"))
    )
    is_gov_observe = text in {
        "查看 Gov 公开市场",
        "查看 Gov 当前可做动作",
        "阅读质押说明",
    }
    is_remediation = (
        text.startswith("重跑 ")
        or text.startswith("补 ")
        or text.startswith("检查 ")
        or text in {
            "查看 Predict 市场上下文",
            "启动 Predict 静默循环",
            "启动 Predict 循环并逐轮汇报",
            "暂停当前运行",
        }
    )

    score = 50
    if is_confirmation:
        score = 0
    elif status == "review_required":
        if is_knowledge_refresh:
            score = 0
        elif is_source_refresh:
            score = 5
        elif is_knowledge_view:
            score = 10
        elif is_source_view:
            score = 15
        elif is_review:
            score = 20
        elif is_continue:
            score = 25
        elif is_remediation or is_inspect or is_playbook or is_run_command:
            score = 30
    elif status == "prefer_fresh_start":
        if is_switch_default:
            score = 0
        elif is_restart:
            score = 5
        elif is_continue:
            score = 10
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "awaiting_dataset":
        if is_dataset:
            score = 0
        elif is_continue:
            score = 5
        elif is_remediation:
            score = 10
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "observe_only":
        if is_gov_observe:
            score = 0
        elif is_scan:
            score = 5
        elif is_continue:
            score = 10
        elif is_remediation:
            score = 15
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "restart_available":
        if is_restart:
            score = 0
        elif is_continue:
            score = 5
        elif is_remediation:
            score = 15
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "follow_runtime_guidance":
        if is_remediation or is_dataset or is_gov_observe or is_run_command or is_continue:
            score = 0
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status in {"knowledge_review_needed", "stale_knowledge_pending"}:
        if is_knowledge_refresh:
            score = 0
        elif is_source_refresh:
            score = 5
        elif is_knowledge_view:
            score = 10
        elif is_source_view:
            score = 15
        elif is_run_command or is_playbook or is_continue:
            score = 25
        elif is_review:
            score = 30
    elif status == "source_review_needed":
        if is_source_refresh:
            score = 0
        elif is_source_view:
            score = 5
        elif is_knowledge_refresh:
            score = 10
        elif is_knowledge_view:
            score = 15
        elif is_run_command or is_playbook or is_continue:
            score = 25
        elif is_review:
            score = 30
    elif status in {"knowledge_ready", "source_ready", "switch_suggested", "runnable"}:
        if worknet_key == "predict" and text == "启动 Predict 静默循环":
            score = 0
        elif worknet_key == "gov" and is_gov_observe:
            score = 0
        elif worknet_key == "ardi" and is_remediation:
            score = 0
        elif is_run_command and str(label or "").startswith("开始 "):
            score = 0
        elif is_scan:
            score = 5
        elif is_playbook:
            score = 10
        elif is_run_command or is_inspect or is_remediation:
            score = 10
        elif is_knowledge_view or is_source_view:
            score = 15
        elif is_review:
            score = 25
        elif is_source_refresh or is_knowledge_refresh:
            score = 30
    elif status in {"blocked", "partial", "needs_runtime_setup", "runtime_error", "network_blocked", "partial_ready", "manual_review"}:
        if is_remediation or is_inspect:
            score = 0
        elif is_scan:
            score = 5
        elif is_continue:
            score = 10
        elif is_restart:
            score = 15
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 75
        elif is_source:
            score = 90
    elif status == "prepared":
        if is_continue:
            score = 0
        elif is_restart:
            score = 5
        elif is_remediation or is_inspect or is_run_command or is_playbook:
            score = 15
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "ready_to_execute":
        if is_inspect or is_playbook or is_run_command or is_continue:
            score = 0
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "ready_for_follow_up":
        if is_continue or is_remediation or is_run_command:
            score = 0
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "background_running":
        if is_background_inspect:
            score = 0
        elif is_pause or is_background_stop:
            score = 5
        elif is_review:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    elif status == "executed":
        if is_review:
            score = 0
        elif is_continue or is_run_command:
            score = 20
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90
    else:
        if is_continue:
            score = 10
        elif is_restart:
            score = 15
        elif is_remediation or is_dataset or is_gov_observe or is_inspect or is_playbook or is_run_command:
            score = 20
        elif is_review:
            score = 30
        elif is_knowledge:
            score = 80
        elif is_source:
            score = 90

    if score >= 50 and is_query_source:
        score = max(score, 90)
    elif score >= 50 and is_query_knowledge:
        score = max(score, 80)
    elif is_review:
        score = min(score, 30)
    elif is_run_command:
        score = min(score, 5 if status in {"prepared", "restart_available"} else 15)
    elif command_text:
        score = min(score, 25)
    return score, lowered


def prioritize_action_entries(
    entries: list[dict[str, Any]],
    *,
    execution_state: Optional[str],
    resume_status: Optional[str] = None,
    worknet_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    ordered = sorted(
        [
            (index, item)
            for index, item in enumerate(entries)
            if isinstance(item, dict) and str(item.get("label") or "").strip()
        ],
        key=lambda pair: (
            action_priority_key(
                execution_state,
                resume_status,
                label=pair[1].get("label"),
                command=str(pair[1].get("command") or "").strip() or None,
                worknet_key=worknet_key,
            ),
            pair[0],
        ),
    )
    return [dict(item) for _, item in ordered]


def prioritize_review_actions(
    worknet_key: str,
    status: str,
    user_actions: list[str],
    user_action_details: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    detail_by_label = {
        str(item.get("label") or "").strip(): dict(item)
        for item in user_action_details
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    }
    seed_entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for label in user_actions:
        text = str(label or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        entry = detail_by_label.get(text, {"label": text, "command": None})
        seed_entries.append(entry)
    for item in user_action_details:
        text = str(item.get("label") or "").strip() if isinstance(item, dict) else ""
        if not text or text in seen:
            continue
        seen.add(text)
        seed_entries.append(dict(item))
    prioritized = prioritize_action_entries(
        seed_entries,
        execution_state=status,
        resume_status=None,
        worknet_key=worknet_key,
    )
    reordered_actions = [str(item.get("label") or "").strip() for item in prioritized if str(item.get("label") or "").strip()]
    reordered_details = [item for item in prioritized if str(item.get("label") or "").strip() in detail_by_label]
    return reordered_actions, reordered_details


def humanize_worknet_switch_summary(profile: dict[str, Any], report: Optional[dict[str, Any]]) -> str:
    key = str(profile.get("key") or "")
    name = str(profile.get("name") or key)
    report = report or {}
    runnable = bool(report.get("runnable"))
    can_start_without_stake = report.get("canStartWithoutStake") is True

    canonical = canonical_worknet_switch_summary_text(
        profile,
        runnable=runnable,
        can_start_without_stake=can_start_without_stake,
    )
    if canonical:
        return canonical

    if key == "mine":
        if runnable:
            return f"{name} 当前可以直接切过去，而且默认就是无质押的数据工作流。"
        return f"{name} 还没准备好自动运行，先检查本地 runtime 和 dataset 入口。"
    if key == "predict":
        if runnable:
            return f"{name} 可以切过去观察市场，也可以直接挂静默循环；真实收益仍要等市场结算。"
        return f"{name} 现在更适合先观察市场 context，等 runtime 条件稳定后再自动运行。"
    if key == "gov":
        if runnable:
            return f"{name} 现在适合先切过去做公开观察；交易和投票类动作仍会先确认。"
        return f"{name} 已可发现，但当前更适合先看 markets 和 phase，再决定是否继续。"
    if key == "ardi":
        if runnable:
            return f"{name} 可以先切过去跑 preflight；后续 commit、reveal、inscribe 仍要跟官方下一步命令。"
        return f"{name} 还不适合直接自动运行，先补齐它要求的 gas 或 stake 条件。"
    if key == "kya":
        return f"{name} 更像一次性身份和委托工具，不会长期自动跑。"
    if key in {"tmr", "community"}:
        return f"{name} 已经被发现，但上游 skill 资料还不够厚，当前只建议查看档案，不建议自动执行。"
    if runnable and can_start_without_stake:
        return f"{name} 当前可以直接切过去，而且现在不用 stake 就能开始。"
    if runnable:
        return f"{name} 当前可以切过去。"
    reason = str(report.get("reason") or "").strip()
    if reason:
        return f"{name} 当前还不建议自动运行：{reason}"
    return f"{name} 已经被发现，但现在还没有足够条件安全自动运行。"


def review_runtime_safety_hint(worknet_key: str) -> Optional[str]:
    caution = canonical_worknet_caution_text(worknet_key)
    if caution:
        return caution
    return None


def humanize_phase_value(value: Optional[str]) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    mapping = {
        "Voting": "投票",
        "Trading": "交易",
        "Settlement": "结算",
        "Observe": "观察",
    }
    return mapping.get(text, text)


def summarize_worknet_review(
    worknet_key: str,
    latest_run: dict[str, Any],
) -> dict[str, list[str]]:
    executed_steps = latest_run.get("executedSteps", []) if isinstance(latest_run, dict) else []
    if not isinstance(executed_steps, list):
        return {}
    if worknet_key == "mine":
        start_step = find_executed_step(executed_steps, "start mine worker")
        start_payload = step_result_payload(start_step)
        if isinstance(start_payload, dict) and str(start_payload.get("state") or "") == "selection_required":
            return {
                "workDone": [
                    "Mine 已经准备好，但这轮停在 dataset 选择，还没真正开始采集。"
                ],
                "strategyChanges": [
                    "Mine 需要先选定 dataset，工作循环才能进入持续运行和产出阶段。"
                ],
            }
    if worknet_key == "gov":
        helper_step = find_executed_step(executed_steps, "gov phase-aware helper")
        helper_payload = step_result_payload(helper_step)
        phase = None
        if isinstance(helper_payload, dict):
            raw_phase = helper_payload.get("phase")
            if isinstance(raw_phase, str) and raw_phase.strip():
                phase = humanize_phase_value(raw_phase.strip())
        state_step = find_executed_step(executed_steps, "gov private state")
        state_payload = step_result_payload(state_step)
        no_power = (
            isinstance(state_payload, dict)
            and str(state_payload.get("error") or "") == "STATE_PRINCIPAL_NOT_IN_EPOCH"
        )
        if phase and no_power:
            return {
                "workDone": [
                    f"Gov 已读取本期公开市场，并确认当前处于{phase}阶段。"
                ],
                "failures": [
                    "这期你的 principal 还没有 AWP Power，所以签名投票和交易还不能做。"
                ],
                "strategyChanges": [
                    "Gov 先做公开观察，等 AWP Power 到位后再碰签名交易和投票。",
                    "所有投票、下单、stake 和其他不可逆动作都必须先进 confirmation queue，不能静默自动执行。",
                ],
            }
        if phase:
            return {
                "workDone": [
                    f"Gov 已确认当前处于{phase}阶段，并准备按这一阶段继续观察。"
                ],
                "strategyChanges": [
                    "先按当前阶段做公开观察，再决定要不要进入签名动作。",
                ],
            }
    return {}


def review_status_code(
    worknet_key: str,
    work_done: list[str],
    failures: list[str],
    strategy_changes: list[str],
) -> str:
    if worknet_key == "mine" and any("dataset" in item.lower() for item in work_done + strategy_changes):
        return "awaiting_dataset"
    if worknet_key == "gov" and any("awp power" in item.lower() for item in failures + strategy_changes):
        return "observe_only"
    if worknet_key == "predict" and any("重启" in item or "restart" in item.lower() for item in strategy_changes):
        return "restart_available"
    if failures and work_done:
        return "partial"
    if failures:
        return "blocked"
    if review_all_steps_prepared(work_done):
        return "prepared"
    if work_done:
        return "progressed"
    return "idle"


def review_status_display(status: Any) -> Optional[str]:
    mapping = {
        "idle": "暂无明确进展",
        "prepared": "只完成了准备阶段",
        "progressed": "已经推进了当前这一轮",
        "awaiting_dataset": "等待选择数据集",
        "observe_only": "当前只适合公开观察",
        "restart_available": "可以直接重启上一轮",
        "partial": "有进展但也有阻塞",
        "blocked": "当前被阻塞",
    }
    code = str(status or "").strip()
    if not code:
        return None
    return mapping.get(code, code)


def recovery_status_display(status: Any) -> Optional[str]:
    mapping = {
        "resume_available": "可以继续上一条工作路线",
        "restart_available": "可以从最近记录重启",
        "prefer_fresh_start": "更适合重新开始",
        "needs_confirmation": "有待确认动作",
        "follow_runtime_guidance": "已经有明确下一步",
        "background_running": "后台任务正在运行",
    }
    code = str(status or "").strip()
    if not code:
        return None
    return mapping.get(code, code)


def execution_state_display(status: Any) -> Optional[str]:
    code = str(status or "").strip()
    if not code:
        return None
    review_display = review_status_display(code)
    if review_display and review_display != code:
        return review_display
    mapping = {
        "setup_needed": "还在准备基础环境",
        "registration_needed": "还没完成注册",
        "registration_blocked": "注册路径暂时被挡住",
        "ready_to_choose_worknet": "可以开始选 WorkNet",
        "awaiting_confirmation": "等待确认动作",
        "ready_for_follow_up": "已经有明确下一步",
        "background_running": "后台任务正在运行",
        "resume_available": "可以恢复上一条工作路线",
        "knowledge_ready": "当前知识可直接参考",
        "knowledge_review_needed": "当前知识待复核",
        "knowledge_fresh": "当前知识目录已是最新",
        "stale_knowledge_pending": "当前有知识待重审",
        "source_ready": "当前来源可直接参考",
        "source_review_needed": "当前来源待复核",
        "source_missing": "当前来源还没进入本地目录",
        "review_required": "先复核知识再执行",
        "ready_to_execute": "可以直接执行",
        "observe_only": "当前先只适合观察",
        "needs_runtime_setup": "还要先补运行环境",
        "partial_ready": "只有部分环节已经就绪",
        "runtime_error": "运行环境当前报错",
        "network_blocked": "当前被网络环境挡住",
        "manual_review": "当前只适合人工检查",
        "executed": "当前这一轮已经执行完成",
    }
    return mapping.get(code, code)


def execution_state_payload(
    status: Any,
    *,
    headline: Optional[str] = None,
) -> dict[str, Optional[str]]:
    code = str(status or "").strip()
    if not code:
        return {
            "executionState": None,
            "executionStateDisplay": None,
            "executionHeadline": None,
        }
    default_headline_map = {
        "knowledge_ready": "当前知识资料可直接参考。",
        "knowledge_review_needed": "当前知识需要先复核再继续。",
        "knowledge_fresh": "当前知识目录已经是最新状态。",
        "stale_knowledge_pending": "当前有上游知识待重审，继续前先复核。",
        "source_ready": "当前来源资料可直接参考。",
        "source_review_needed": "当前来源发生了上游变化，继续前先复核。",
        "source_missing": "当前来源还没有进入本地百科目录。",
    }
    return {
        "executionState": code,
        "executionStateDisplay": execution_state_display(code),
        "executionHeadline": str(headline or default_headline_map.get(code) or "").strip() or None,
    }


def derive_execution_state(
    *,
    review: Any = None,
    recovery: Any = None,
    next_action: Any = None,
) -> dict[str, Any]:
    status = None
    headline = None
    if isinstance(review, dict):
        review_status = str(review.get("status") or "").strip()
        if review_status:
            status = review_status
            headline = str(review.get("headline") or "").strip() or None
    if status is None and isinstance(recovery, dict):
        latest_review_status = str(recovery.get("latestReviewStatus") or "").strip()
        if latest_review_status:
            status = latest_review_status
            headline = str(recovery.get("latestReviewHeadline") or "").strip() or None
    if status is None:
        action = str(next_action or "").strip()
        mapping = {
            "install_awp_skill_dependency": "setup_needed",
            "run_awp_skill_registration": "registration_needed",
            "register_agent": "registration_needed",
            "retry_registration_preflight": "registration_blocked",
            "scan_worknets": "ready_to_choose_worknet",
            "resume_pending_confirmations": "awaiting_confirmation",
            "resume_runtime_guidance": "ready_for_follow_up",
            "monitor_background_runs": "background_running",
            "resume_previous_run": "resume_available",
        }
        status = mapping.get(action)
    return {
        "executionState": status or None,
        "executionStateDisplay": execution_state_display(status) if status else None,
        "executionHeadline": headline,
    }


def derive_runtime_execution_state(
    response: Any,
    *,
    headline: Optional[str] = None,
    recovery: Any = None,
) -> dict[str, Any]:
    response = response if isinstance(response, dict) else {}
    recovery = recovery if isinstance(recovery, dict) else {}
    status = str(response.get("status") or "").strip()
    next_action = str(response.get("nextAction") or "").strip()
    queue = normalized_confirmation_queue(response.get("confirmationQueue", []))
    runtime_guidance = response.get("runtimeGuidance", {}) if isinstance(response.get("runtimeGuidance"), dict) else {}
    executed_steps = response.get("executedSteps", []) if isinstance(response.get("executedSteps"), list) else []
    step_statuses = {
        str(item.get("status") or "").strip()
        for item in executed_steps
        if isinstance(item, dict) and str(item.get("status") or "").strip()
    }
    execution_state = None
    if queue or status == "needs_confirmation" or next_action == "await_confirmation":
        execution_state = "awaiting_confirmation"
    elif status == "background_running" or next_action == "monitor_background_run":
        execution_state = "background_running"
    elif status == "needs_runtime_input" or next_action == "follow_runtime_guidance":
        execution_state = "ready_for_follow_up"
    elif status == "executed" or next_action == "review_epoch":
        execution_state = "executed"
    elif step_statuses and step_statuses.issubset({"planned", "available_manual"}):
        execution_state = "prepared"
    elif status == "planned" and (
        response.get("selectedWorknetKey")
        or response.get("selectedBackground")
        or response.get("playbookSource")
    ):
        execution_state = "prepared"
    elif status:
        execution_state = status
    selected_name = str(response.get("selectedWorknetName") or response.get("selectedWorknetKey") or "这条工作路径").strip()
    chosen_headline = str(headline or response.get("headline") or "").strip() or None
    if execution_state == "prepared":
        latest_review_headline = str(recovery.get("latestReviewHeadline") or "").strip()
        if latest_review_headline:
            chosen_headline = latest_review_headline
        elif selected_name:
            chosen_headline = f"{selected_name} 当前只完成了准备阶段，正式执行还没开始。"
    elif execution_state == "awaiting_confirmation":
        first_label = queue[0].get("label") if queue else None
        if isinstance(first_label, str) and first_label.strip():
            chosen_headline = f"继续前先确认“{first_label.strip()}”。"
        elif not chosen_headline:
            chosen_headline = "当前有待确认动作。"
    elif execution_state == "ready_for_follow_up":
        guidance_message = str(runtime_guidance.get("message") or "").strip()
        if guidance_message:
            chosen_headline = guidance_message
        elif selected_name:
            chosen_headline = f"{selected_name} 已经有明确下一步。"
    elif execution_state == "executed":
        if next_action == "review_epoch" and selected_name:
            chosen_headline = f"{selected_name} 这轮已经跑完，下一步先看复盘。"
        elif not chosen_headline:
            chosen_headline = "当前这一轮已经执行完成。"
    elif execution_state == "background_running":
        guidance_message = str(runtime_guidance.get("message") or "").strip()
        if guidance_message:
            chosen_headline = guidance_message
        elif not chosen_headline:
            chosen_headline = "后台任务仍在运行。"
    return {
        "executionState": execution_state or None,
        "executionStateDisplay": execution_state_display(execution_state) if execution_state else None,
        "executionHeadline": chosen_headline,
    }


def align_run_execution_user_message(
    user_message: Optional[str],
    *,
    execution_state: Any,
    execution_headline: Optional[str],
    primary_action: Optional[str],
    worknet_context_key: Optional[str],
    include_canonical_plain: bool = True,
    extra_parts: Optional[list[str]] = None,
) -> Optional[str]:
    state = str(execution_state or "").strip()
    base_message = str(user_message or "").strip()
    if state != "prepared":
        return base_message or None
    detail = str(execution_headline or "").strip()
    if not detail:
        return base_message or None
    parts: list[str] = []
    plain = canonical_worknet_plain_text(worknet_context_key) if include_canonical_plain else None
    if plain:
        parts.append(plain)
    parts.append(detail)
    action_label = str(primary_action or "").strip()
    if action_label:
        parts.append(f"如果你现在就要继续，先用“{action_label}”。")
    for item in extra_parts or []:
        text = str(item or "").strip()
        if text:
            parts.append(text)
    return join_product_sentences(parts) or base_message or None


def derive_playbook_execution_state(
    profile: dict[str, Any],
    *,
    inspection_status: Any,
    knowledge_caveat: Optional[str],
) -> dict[str, Any]:
    name = str(profile.get("name") or profile.get("key") or "当前 WorkNet").strip()
    status = str(inspection_status or "").strip()
    if knowledge_caveat:
        execution_state = "review_required"
        headline = knowledge_caveat
    elif status == "ready":
        execution_state = "ready_to_execute"
        headline = f"{name} 当前运行环境已就绪，可以直接按这份 playbook 执行。"
    elif status == "installed-needs-bootstrap":
        execution_state = "needs_runtime_setup"
        headline = f"{name} 的运行环境已经找到，但正式执行前还要先完成 bootstrap。"
    elif status == "partial":
        execution_state = "partial_ready"
        headline = f"{name} 只补齐了一部分运行条件，正式执行前还要继续补环境。"
    elif status == "runtime-error":
        execution_state = "runtime_error"
        headline = f"{name} 的运行环境当前报错，先修好运行时再继续。"
    elif status == "network-blocked":
        execution_state = "network_blocked"
        headline = f"{name} 的本地运行环境已经存在，但当前网络环境挡住了实时检查。"
    elif status in {"remote-profile-only", "empty-official-repo"}:
        execution_state = "manual_review"
        headline = f"{name} 当前还没有可安全自动执行的本地运行环境，先按文档做人工检查。"
    else:
        execution_state = "needs_runtime_setup"
        headline = f"{name} 当前还没有可直接执行的本地运行环境。"
    return {
        "executionState": execution_state,
        "executionStateDisplay": execution_state_display(execution_state),
        "executionHeadline": headline,
    }


def derive_capability_execution_state(report: Any) -> dict[str, Any]:
    report = report if isinstance(report, dict) else {}
    knowledge_context = report.get("knowledgeContext") if isinstance(report.get("knowledgeContext"), dict) else None
    knowledge_source_highlights = report.get("knowledgeSourceHighlights")
    caveat = capability_knowledge_caveat(knowledge_context, knowledge_source_highlights)
    name = str(report.get("name") or report.get("symbol") or report.get("worknetId") or "当前 WorkNet").strip()
    cli_status = str(report.get("cliStatus") or "").strip()
    runnable = bool(report.get("runnable"))
    automation = str(report.get("automationLevel") or "").strip()
    role = str(report.get("recommendedRole") or "").strip()
    worknet_key = (
        str(report.get("worknetKey") or "").strip().lower()
        or str((resolve_worknet(str(report.get("worknetId") or "")) or {}).get("key") or "").strip().lower()
        or str((resolve_worknet(str(report.get("name") or "")) or {}).get("key") or "").strip().lower()
        or str((resolve_worknet(str(report.get("symbol") or "")) or {}).get("key") or "").strip().lower()
    )

    if caveat:
        execution_state = "review_required"
        headline = caveat
    elif worknet_key == "gov" and cli_status == "ready":
        execution_state = "observe_only"
        headline = f"{name} 当前先适合看公开市场和阶段，不建议直接自动执行。"
    elif worknet_key == "ardi" and cli_status == "ready" and not runnable:
        execution_state = "blocked"
        headline = f"{name} 当前还缺手续费或资格条件，先补齐再继续。"
    elif role == "identity":
        execution_state = "manual_review"
        headline = f"{name} 更像一次性的身份工具，先按步骤检查身份、收款地址和签名边界。"
    elif role == "observer" or automation == "manual-only":
        execution_state = "manual_review"
        headline = f"{name} 当前只适合人工查看和判断，不建议直接自动执行。"
    elif cli_status == "ready" and runnable:
        execution_state = "ready_to_execute"
        headline = f"{name} 当前运行条件已就绪，可以直接进入执行。"
    elif cli_status == "installed-needs-bootstrap":
        execution_state = "needs_runtime_setup"
        headline = f"{name} 的本地运行环境已经找到，但正式执行前还要先补 bootstrap。"
    elif cli_status == "partial":
        execution_state = "partial_ready"
        headline = f"{name} 只补齐了一部分运行条件，正式执行前还要继续补环境。"
    elif cli_status == "runtime-error":
        execution_state = "runtime_error"
        headline = f"{name} 的运行环境当前报错，先修好运行时再继续。"
    elif cli_status == "network-blocked":
        execution_state = "network_blocked"
        headline = f"{name} 的本地运行环境已经存在，但当前网络环境挡住了实时检查。"
    elif cli_status in {"remote-profile-only", "empty-official-repo"}:
        execution_state = "manual_review"
        headline = f"{name} 当前还没有可安全自动执行的本地运行环境，先按公开资料人工检查。"
    elif runnable:
        execution_state = "prepared"
        headline = f"{name} 当前已经具备一部分执行条件，但还需要你先确认具体下一步。"
    else:
        execution_state = "needs_runtime_setup"
        headline = f"{name} 当前还不适合直接自动执行，先补运行环境或继续人工检查。"
    return {
        "executionState": execution_state,
        "executionStateDisplay": execution_state_display(execution_state),
        "executionHeadline": headline,
    }


def knowledge_topic_execution_state(
    *,
    label: str,
    affected: bool,
    capability_report: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if affected:
        return {
            "executionState": "review_required",
            "executionStateDisplay": execution_state_display("review_required"),
            "executionHeadline": f"{label} 当前有上游变更待复核，继续前先确认知识没有过期。",
        }
    if isinstance(capability_report, dict):
        return derive_capability_execution_state(capability_report)
    return {
        "executionState": None,
        "executionStateDisplay": None,
        "executionHeadline": None,
    }


def review_line_detail(text: Any) -> str:
    value = str(text or "").strip()
    if not value:
        return value
    for separator in ("：", ":"):
        if separator not in value:
            continue
        head, tail = value.split(separator, 1)
        if tail.strip() and len(head.strip()) <= 32:
            return tail.strip()
    return value


def review_all_steps_prepared(work_done: list[str]) -> bool:
    if not work_done:
        return False
    markers = ("还没真正执行", "还没真正启动")
    details = [review_line_detail(item) for item in work_done if str(item).strip()]
    return bool(details) and all(any(marker in detail for marker in markers) for detail in details)


def build_review_headline(
    worknet_key: str,
    work_done: list[str],
    failures: list[str],
    strategy_changes: list[str],
) -> Optional[str]:
    if worknet_key == "mine":
        if any(
            token in str(item)
            for item in work_done + strategy_changes
            for token in ("数据集选择阶段", "dataset 选择", "选定 dataset", "选一个数据集")
        ):
            return "Mine 这轮还没真正开跑，目前停在 dataset 选择。"
        if review_all_steps_prepared(work_done):
            return "Mine 当前只完成了准备阶段，正式采集还没开始。"
        if work_done:
            return "Mine 已完成当前一轮检查，下一步可以继续采集。"
    if worknet_key == "gov":
        if failures and any("awp power" in item.lower() for item in failures):
            return "Gov 这期先只能做公开观察，因为你还没有 AWP Power。"
        if review_all_steps_prepared(work_done):
            return "Gov 当前只完成了准备阶段，正式观察和签名动作还没开始。"
        if work_done:
            return "Gov 已确认当前阶段，下一步按这一阶段继续观察。"
    if worknet_key == "predict":
        if failures and any(
            token in item.lower()
            for item in failures
            for token in ("1000 awp", "资格", "stake", "没有合适市场", "上下文还不够稳定")
        ):
            return "Predict 这轮还没进入可稳定提交的状态，先把资格和市场条件理顺。"
        if review_all_steps_prepared(work_done):
            return "Predict 当前只完成了准备阶段，正式观察和提交还没开始。"
        if strategy_changes and any("重启" in item or "restart" in item.lower() for item in strategy_changes):
            return "Predict 当前没有在后台继续跑，但上一次 loop 记录还在，可以直接重启。"
        if work_done:
            return "Predict 最近一次 loop 已跑到新一轮检查。"
    if worknet_key == "ardi":
        if failures and any(
            token in item.lower()
            for item in failures
            for token in ("gas", "stake", "commit/reveal")
        ):
            return "Ardi 这轮还没进入提交承诺和揭示阶段，先把 Gas 和资格条件补齐。"
        if review_all_steps_prepared(work_done):
            return "Ardi 当前只完成了准备阶段，正式进入提交承诺和揭示前还没开始。"
        if work_done:
            return "Ardi 已完成当前一轮检查，下一步按官方命令继续。"
    if failures:
        return review_line_detail(failures[0])
    if work_done:
        return review_line_detail(work_done[0])
    return None


def build_daily_summary(
    worknet_key: str,
    headline: Optional[str],
    estimated_rewards: list[str],
    user_actions: list[str],
    *,
    reporter_note: Optional[str] = None,
) -> Optional[str]:
    def normalize_part(text: Any) -> str:
        value = strip_sentence_end(text)
        return re.sub(r"[\s。！？!?；;，,:：]+", "", value).lower()

    parts: list[str] = []
    seen: set[str] = set()

    def add_part(text: Any, *, max_chars: int, max_sentences: int = 1) -> None:
        preview = compact_preview_text(text, max_chars=max_chars, max_sentences=max_sentences)
        if not preview:
            return
        rendered = strip_sentence_end(preview)
        normalized = normalize_part(rendered)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        parts.append(rendered)

    if isinstance(headline, str) and headline.strip():
        add_part(headline, max_chars=120, max_sentences=1)
    else:
        plain = canonical_worknet_plain_text(worknet_key)
        if plain:
            add_part(plain, max_chars=120, max_sentences=1)
    if isinstance(reporter_note, str) and reporter_note.strip():
        add_part(reporter_note, max_chars=90, max_sentences=1)
    if estimated_rewards:
        add_part(estimated_rewards[0], max_chars=120, max_sentences=1)
    if user_actions:
        first_action = str(user_actions[0]).strip()
        if first_action:
            add_part(f"下一步：{first_action}", max_chars=100, max_sentences=1)
    if not parts:
        return None
    rendered: list[str] = []
    for part in parts:
        text = strip_sentence_end(part)
        if not text:
            continue
        if rendered:
            rendered.append(" " if rendered[-1].endswith("…") else "。 ")
        rendered.append(text)
    if not rendered:
        return None
    if rendered[-1].endswith("…"):
        return "".join(rendered)
    return "".join(rendered) + "。"


def reporter_reference_note(
    knowledge_context: Any,
    knowledge_reference_highlights: Any,
) -> Optional[str]:
    if not isinstance(knowledge_context, dict) or not isinstance(knowledge_reference_highlights, list):
        return None
    for item in knowledge_reference_highlights:
        if not isinstance(item, dict):
            continue
        ref_label = str(item.get("label") or item.get("key") or "").strip()
        if ref_label:
            return f"底层参考先看 {ref_label}。"
    return None


def knowledge_source_labels_text(
    knowledge_source_highlights: Any,
    *,
    affected_only: Optional[bool] = None,
    limit: int = 3,
) -> Optional[str]:
    if not isinstance(knowledge_source_highlights, list):
        return None
    labels: list[str] = []
    for item in knowledge_source_highlights:
        if not isinstance(item, dict):
            continue
        freshness = str(item.get("freshnessStatus") or "").strip().lower()
        if affected_only is True and freshness != "affected":
            continue
        if affected_only is False and freshness == "affected":
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label or label in labels:
            continue
        labels.append(label)
        if len(labels) >= limit:
            break
    if not labels:
        return None
    return "、".join(labels)


def reporter_source_note(knowledge_source_highlights: Any) -> Optional[str]:
    affected_items = [
        item
        for item in knowledge_source_highlights
        if isinstance(item, dict) and str(item.get("freshnessStatus") or "").strip().lower() == "affected"
    ] if isinstance(knowledge_source_highlights, list) else []
    stable_items = [
        item
        for item in knowledge_source_highlights
        if isinstance(item, dict) and str(item.get("freshnessStatus") or "").strip().lower() != "affected"
    ] if isinstance(knowledge_source_highlights, list) else []
    affected_labels = knowledge_source_labels_text(affected_items, affected_only=None, limit=3)
    stable_labels = knowledge_source_labels_text(stable_items, affected_only=None, limit=3)
    if affected_labels:
        first_label = str((affected_items[0].get("label") or affected_items[0].get("key") or "") if affected_items else "").strip()
        if first_label:
            return f"优先复核来源：{first_label}。"
        return f"优先复核来源：{affected_labels.split('、')[0]}。"
    if stable_labels:
        first_label = str((stable_items[0].get("label") or stable_items[0].get("key") or "") if stable_items else "").strip()
        if first_label:
            return f"相关来源先看 {first_label}。"
        return f"相关来源先看 {stable_labels.split('、')[0]}。"
    return None


def build_reporter_note(
    knowledge_context: Any,
    knowledge_reference_highlights: Any,
    knowledge_source_highlights: Any = None,
) -> Optional[str]:
    if not isinstance(knowledge_context, dict):
        return None
    label = str(knowledge_context.get("label") or knowledge_context.get("key") or "当前 WorkNet").strip()
    freshness = str(knowledge_context.get("freshnessStatus") or "").strip().lower()
    if freshness == "affected":
        note = f"{label} 当前有上游变更。"
    else:
        note = f"{label} 当前没有直接上游漂移。"
    source_note = reporter_source_note(knowledge_source_highlights)
    if source_note:
        note += f" {source_note}"
    reference_note = reporter_reference_note(knowledge_context, knowledge_reference_highlights)
    if reference_note:
        note += f" {reference_note}"
    return note


def runtime_payload_error_summary(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        suggestion = error.get("suggestion")
        if isinstance(suggestion, str) and suggestion.strip():
            return suggestion.strip()
        code = error.get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    if payload.get("ok") is False:
        if isinstance(error, dict):
            suggestion = error.get("suggestion")
            if isinstance(suggestion, str) and suggestion.strip():
                return suggestion.strip()
            code = error.get("code")
            if isinstance(code, str) and code.strip():
                return code.strip()
        message = runtime_message(payload)
        if message:
            return message
    status = str(payload.get("status") or "").lower()
    if status == "error":
        data = payload.get("data")
        if isinstance(data, dict):
            suggestion = data.get("suggestion")
            if isinstance(suggestion, str) and suggestion.strip():
                return suggestion.strip()
        message = runtime_message(payload)
        if message:
            return message
    if isinstance(error, str) and error.strip():
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        return error.strip()
    return None


def runtime_payload_has_blocker(payload: Any) -> bool:
    return runtime_payload_error_summary(payload) is not None


def strategy_changes_from_guidance(guidance: Any, *, worknet_key: str = "") -> list[str]:
    if not isinstance(guidance, dict):
        return []
    next_action = str(guidance.get("nextAction") or "")
    mapping = {
        "stake_required": "先解决 stake 资格，再继续自动循环。",
        "retry_stake_check": "先重试 stake 资格检查，确认运行时返回稳定结果后再继续。",
        "acquire_awp_power_or_observe_gov": "Gov 先做公开观察，等 AWP Power 到位后再碰签名交易和投票。",
        "fund_gas_and_or_satisfy_stake": "Ardi 先补 Gas 和资格路径，再进入提交承诺、揭示和铭刻节奏。",
        "fetch_context": "Predict 先拉市场上下文，再决定是否继续下单或观察。",
        "confirm_predict_submission": "Predict 已准备好推荐市场，但正式提交前要先确认方向、下单数量和推理说明。",
        "wait_for_predict_market": "Predict 当前没有可提交市场，先等待下一轮，再重新拉上下文。",
        "monitor_background_run": "工作循环已经在后台运行，接下来重点看日志和下一次复盘。",
    }
    message = mapping.get(next_action)
    changes: list[str] = [message] if message else []
    if worknet_key == "predict":
        if next_action == "confirm_predict_submission":
            changes.append("提交前先检查方向、下单数量和推理说明是否真的有差异化，不要为了出手而重复观点。")
        elif next_action == "wait_for_predict_market":
            changes.append("没有合适市场时宁可等下一轮，也不要为了开单而重复推理。")
        elif next_action in {"stake_required", "retry_stake_check"}:
            changes.append("Predict 的质押资格是增强路径，不是每次都要硬推到先质押再继续。")
    elif worknet_key == "gov":
        if next_action == "acquire_awp_power_or_observe_gov":
            changes.append("在 AWP Power 没到位前，先把精力放在公开市场、当前阶段和公开信号上。")
    elif worknet_key == "ardi":
        if next_action == "fund_gas_and_or_satisfy_stake":
            changes.append("Ardi 先把 Gas 和资格条件补齐，再严格按官方下一步命令推进，不要自造流程。")
    caution = review_runtime_safety_hint(worknet_key)
    if caution and next_action in {"confirm_predict_submission", "acquire_awp_power_or_observe_gov", "fund_gas_and_or_satisfy_stake"}:
        changes.append(caution)
    return [item for item in changes if isinstance(item, str) and item.strip()]


def normalized_follow_up_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        command = item.get("command")
        argv = item.get("argv")
        parsed_argv = [str(part) for part in argv] if isinstance(argv, list) and argv else None
        if parsed_argv is None and isinstance(command, str) and command.strip() and not command.strip().startswith(("http://", "https://", "Send ")):
            try:
                parsed_argv = shlex.split(command)
            except ValueError:
                parsed_argv = None
        normalized.append(
            {
                "label": label.strip(),
                "command": str(command).strip() if isinstance(command, str) and command.strip() else None,
                "argv": parsed_argv,
                "cwd": str(item.get("cwd")) if item.get("cwd") else None,
                "safeToAutoRun": bool(item.get("safeToAutoRun", False)),
                "requiresConfirmation": bool(item.get("requiresConfirmation", False)),
                "selectedByDefault": bool(item.get("selectedByDefault", False)),
                "longRunning": bool(item.get("longRunning", False)),
                "parameterSchema": [
                    spec for spec in item.get("parameterSchema", []) if isinstance(spec, dict)
                ] if isinstance(item.get("parameterSchema"), list) else [],
            }
        )
    return annotate_raw_follow_up_actions(normalized)


def normalized_confirmation_queue(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        argv = item.get("argv")
        normalized.append(
            {
                "label": label.strip(),
                "displayLabel": humanize_public_action_label(label.strip()),
                "command": render_argv([str(part) for part in argv]) if isinstance(argv, list) and argv else None,
                "argv": [str(part) for part in argv] if isinstance(argv, list) and argv else None,
                "cwd": str(item.get("cwd")) if item.get("cwd") else None,
                "category": item.get("category"),
                "executionPolicy": item.get("executionPolicy"),
                "status": item.get("status", "queued_for_confirmation"),
                "longRunning": bool(item.get("longRunning", False)),
                "parameterSchema": [
                    spec for spec in item.get("parameterSchema", []) if isinstance(spec, dict)
                ] if isinstance(item.get("parameterSchema"), list) else [],
            }
        )
    return annotate_raw_confirmation_queue(normalized)


def choose_default_confirmation(queue: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    return queue[0] if queue else None


def choose_default_background_process(active: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    return active[0] if active else None


def choose_default_follow_up_action(actions: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    candidates = [
        item
        for item in actions
        if item.get("safeToAutoRun") and not item.get("requiresConfirmation") and item.get("argv")
    ]
    if not candidates:
        return None
    for item in candidates:
        if item.get("selectedByDefault"):
            return item
    return candidates[0]


def execute_follow_up_action(
    latest_run: dict[str, Any],
    action: dict[str, Any],
    *,
    execute: bool,
    explicit_selection: bool = False,
    state: dict[str, Any],
) -> dict[str, Any]:
    step = {
        "label": action.get("label"),
        "cwd": action.get("cwd"),
        "argv": action.get("argv"),
        "category": "follow-up",
        "executionPolicy": "follow-up",
        "status": "planned" if execute else "available_manual",
        "parameterSchema": action.get("parameterSchema", []),
        "longRunning": bool(action.get("longRunning", False)),
    }
    runtime_guidance: Optional[dict[str, Any]] = None
    follow_up_actions: list[dict[str, Any]] = []
    if action.get("requiresConfirmation"):
        step["status"] = "queued_for_confirmation"
    elif not execute:
        return annotate_runtime_action_payloads({
            "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
            "status": "planned",
            "executedSteps": [step | {"status": "available_manual"}],
            "confirmationQueue": [],
            "runtimeGuidance": None,
            "followUpActions": [],
            "resumedFromState": True,
            "nextAction": "execute_when_ready",
            "progress": "[4/5] Work loop",
            "stateRoot": state["root"],
        })
    elif execute and (action.get("safeToAutoRun") or explicit_selection) and action.get("argv"):
        if action.get("longRunning"):
            launched = launch_background_command(
                [str(part) for part in action["argv"]],
                cwd=action.get("cwd"),
                state=state,
                label=str(action.get("label")),
            )
            step["status"] = "started_background"
            step["backgroundProcess"] = launched
            runtime_guidance = {
                "message": f"{action.get('label')} 已在后台启动。",
                "userActions": [],
                "actionMap": {},
                "nextCommand": None,
                "nextAction": "monitor_background_run",
                "state": None,
                "detail": launched.get("logPath"),
            }
            step["runtimeGuidance"] = runtime_guidance
        else:
            result = run_command([str(part) for part in action["argv"]], cwd=action.get("cwd"))
            step["status"] = "ok" if result.get("ok", False) else "failed"
            step["result"] = {
                "code": result.get("code"),
                "stdout": trim_output(parse_json_loose(result.get("stdout", ""))),
                "stderr": trim_output(result.get("stderr", "")),
            }
            playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
            worknet_key = str(playbook.get("worknetKey") or "").strip().lower()
            guidance = extract_runtime_guidance_from_payload(
                step["result"]["stdout"],
                worknet_key=worknet_key or None,
            )
            if guidance:
                step["runtimeGuidance"] = guidance
    executed_steps = [step]
    playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
    if runtime_guidance is None:
        runtime_guidance, follow_up_actions = synthesize_run_guidance(playbook, executed_steps)
    else:
        follow_up_actions = []
    run_record = annotate_runtime_action_payloads({
        "generatedAt": now_iso(),
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "execute": execute,
        "playbook": playbook,
        "executedSteps": executed_steps,
        "confirmationQueue": [step] if step.get("status") == "queued_for_confirmation" else [],
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "warnings": state["warnings"],
        "resumedFollowUp": True,
        "sourceFollowUpAction": action,
    })
    atomic_write_json(Path(state["runs"]) / "latest-run.json", run_record)
    atomic_write_json(
        Path(state["runs"]) / "pending-confirmations.json",
        run_record["confirmationQueue"],
    )
    append_jsonl(Path(state["runs"]) / "history.jsonl", run_record)
    return annotate_runtime_action_payloads({
        "mode": run_record["mode"],
        "status": (
            "needs_confirmation"
            if run_record["confirmationQueue"]
            else (
                "background_running"
                if isinstance(runtime_guidance, dict) and runtime_guidance.get("nextAction") == "monitor_background_run"
                else ("needs_runtime_input" if runtime_guidance and follow_up_actions else ("executed" if execute else "planned"))
            )
        ),
        "executedSteps": executed_steps,
        "confirmationQueue": run_record["confirmationQueue"],
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "resumedFromState": True,
        "nextAction": (
            "await_confirmation"
            if run_record["confirmationQueue"]
            else (
                runtime_guidance.get("nextAction")
                if isinstance(runtime_guidance, dict) and runtime_guidance.get("nextAction") == "monitor_background_run"
                else (
                    "follow_runtime_guidance"
                    if runtime_guidance and follow_up_actions
                    else ("review_epoch" if execute else "execute_when_ready")
                )
            )
        ),
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })


def continue_runtime_guidance_without_default(latest_run: dict[str, Any], *, state: dict[str, Any]) -> dict[str, Any]:
    follow_up_actions = normalized_follow_up_actions(latest_run.get("followUpActions", []))
    runtime_guidance = latest_run.get("runtimeGuidance", {}) if isinstance(latest_run, dict) else {}
    return annotate_runtime_action_payloads({
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "status": "needs_runtime_input" if follow_up_actions else "planned",
        "executedSteps": [],
        "confirmationQueue": [],
        "runtimeGuidance": runtime_guidance if isinstance(runtime_guidance, dict) else None,
        "followUpActions": follow_up_actions,
        "resumedFromState": True,
        "nextAction": "follow_runtime_guidance" if follow_up_actions else "execute_when_ready",
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })


def continue_pending_confirmations(
    latest_run: dict[str, Any],
    pending_queue: list[dict[str, Any]],
    *,
    state: dict[str, Any],
) -> dict[str, Any]:
    queue = normalized_confirmation_queue(pending_queue)
    return annotate_runtime_action_payloads({
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "status": "needs_confirmation",
        "executedSteps": [],
        "confirmationQueue": queue,
        "runtimeGuidance": None,
        "followUpActions": [],
        "resumedFromState": True,
        "nextAction": "await_confirmation",
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })


def continue_background_runs(
    latest_run: dict[str, Any],
    *,
    state: dict[str, Any],
    tail_lines: int = 40,
) -> dict[str, Any]:
    active = load_active_processes(state)
    inspected = [
        inspect_background_process(state, str(item.get("label")), tail_lines=tail_lines)
        for item in active
        if isinstance(item, dict)
    ]
    summary_message = f"{len(inspected)} 个后台任务仍在运行。"
    if len(inspected) == 1:
        info = inspected[0].get("summary", {})
        headline = info.get("headline") if isinstance(info, dict) else None
        if isinstance(headline, str) and headline.strip():
            summary_message = headline.strip()
    return annotate_runtime_action_payloads({
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "status": "background_running" if inspected else "planned",
        "executedSteps": [],
        "confirmationQueue": [],
        "runtimeGuidance": {
            "message": summary_message if inspected else "没有后台任务在运行。",
            "userActions": [str(item.get("label")) for item in inspected if item.get("label")],
            "actionMap": {},
            "nextCommand": None,
            "nextAction": "monitor_background_run" if inspected else "execute_when_ready",
            "state": None,
        },
        "followUpActions": [],
        "activeBackgroundProcesses": inspected,
        "resumedFromState": True,
        "nextAction": "monitor_background_run" if inspected else "execute_when_ready",
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })


def execute_confirmation_action(
    latest_run: dict[str, Any],
    pending_queue: list[dict[str, Any]],
    action: dict[str, Any],
    *,
    execute: bool,
    provided_inputs: dict[str, str],
    state: dict[str, Any],
) -> dict[str, Any]:
    queue = normalized_confirmation_queue(pending_queue)
    selected_label = str(action.get("label"))
    remaining_queue = [item for item in queue if str(item.get("label")) != selected_label] if execute else queue
    step = {
        "label": action.get("label"),
        "cwd": action.get("cwd"),
        "argv": action.get("argv"),
        "category": action.get("category", "confirmation"),
        "executionPolicy": "confirmation",
        "status": "awaiting_confirmation" if not execute else "queued_for_confirmation",
        "parameterSchema": action.get("parameterSchema", []),
    }
    runtime_guidance: Optional[dict[str, Any]] = None
    follow_up_actions: list[dict[str, Any]] = []
    parameter_schema = [
        spec for spec in action.get("parameterSchema", []) if isinstance(spec, dict)
    ] if isinstance(action.get("parameterSchema"), list) else []
    if not execute:
        return annotate_runtime_action_payloads({
            "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
            "status": "needs_confirmation",
            "executedSteps": [step],
            "confirmationQueue": queue,
            "selectedConfirmation": {
                "label": action.get("label"),
                "command": render_argv(action.get("argv", [])) if isinstance(action.get("argv"), list) else None,
                "requiredInputs": parameter_schema,
                "executeCommand": (
                    build_confirmation_execute_command(selected_label, parameter_schema)
                    if parameter_schema
                    else workstation_confirmation_command(selected_label, execute=True)
                ),
            },
            "runtimeGuidance": None,
            "followUpActions": [],
            "resumedFromState": True,
            "nextAction": "await_confirmation",
            "progress": "[4/5] Work loop",
            "stateRoot": state["root"],
        })
    if execute:
        argv = action.get("argv")
        if isinstance(argv, list) and argv:
            resolved_argv = [str(part) for part in argv]
            parameter_errors: list[str] = []
            if parameter_schema:
                maybe_resolved, parameter_errors = resolve_parameterized_argv(
                    resolved_argv,
                    parameter_schema,
                    provided_inputs,
                )
                if maybe_resolved is not None:
                    resolved_argv = maybe_resolved
            if parameter_errors:
                return annotate_runtime_action_payloads({
                    "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
                    "status": "needs_confirmation",
                    "executedSteps": [
                        {
                            **step,
                            "status": "missing_parameters",
                            "parameterErrors": parameter_errors,
                        }
                    ],
                    "confirmationQueue": queue,
                    "selectedConfirmation": {
                        "label": action.get("label"),
                        "command": render_argv(action.get("argv", [])) if isinstance(action.get("argv"), list) else None,
                        "requiredInputs": parameter_schema,
                        "executeCommand": build_confirmation_execute_command(selected_label, parameter_schema),
                    },
                    "runtimeGuidance": None,
                    "followUpActions": [],
                    "resumedFromState": True,
                    "nextAction": "await_confirmation",
                    "progress": "[4/5] Work loop",
                    "stateRoot": state["root"],
                })
            step["argv"] = resolved_argv
            result = run_command(resolved_argv, cwd=action.get("cwd"))
            step["status"] = "ok" if result.get("ok", False) else "failed"
            step["result"] = {
                "code": result.get("code"),
                "stdout": trim_output(parse_json_loose(result.get("stdout", ""))),
                "stderr": trim_output(result.get("stderr", "")),
            }
            playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
            worknet_key = str(playbook.get("worknetKey") or "").strip().lower()
            guidance = extract_runtime_guidance_from_payload(
                step["result"]["stdout"],
                worknet_key=worknet_key or None,
            )
            if guidance:
                step["runtimeGuidance"] = guidance
                runtime_guidance = guidance
        else:
            step["status"] = "missing_runtime_command"
    run_record = annotate_runtime_action_payloads({
        "generatedAt": now_iso(),
        "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
        "execute": execute,
        "playbook": latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {},
        "executedSteps": [step],
        "confirmationQueue": remaining_queue,
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "warnings": state["warnings"],
        "confirmedAction": action,
    })
    atomic_write_json(Path(state["runs"]) / "latest-run.json", run_record)
    atomic_write_json(
        Path(state["runs"]) / "pending-confirmations.json",
        remaining_queue,
    )
    append_jsonl(Path(state["runs"]) / "history.jsonl", run_record)
    return annotate_runtime_action_payloads({
        "mode": run_record["mode"],
        "status": (
            "needs_confirmation"
            if remaining_queue
            else ("executed" if execute else "needs_confirmation")
        ),
        "executedSteps": [step],
        "confirmationQueue": remaining_queue,
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "resumedFromState": True,
        "nextAction": (
            "await_confirmation"
            if remaining_queue
            else ("review_epoch" if execute else "await_confirmation")
        ),
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    })


def run_workstation(
    mode: str,
    worknet_identifier: Optional[str] = None,
    playbook_path: Optional[str] = None,
    follow_up_label: Optional[str] = None,
    confirm_label: Optional[str] = None,
    background_label: Optional[str] = None,
    stop_background_label: Optional[str] = None,
    pause: bool = False,
    tail_lines: int = 40,
    auto_advance: bool = False,
    provided_inputs: Optional[list[str]] = None,
    execute: bool = False,
) -> dict[str, Any]:
    state = state_context()
    preferences = ensure_user_preferences(state)
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    pending_queue = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    parsed_inputs = parse_input_assignments(provided_inputs)
    recovery_snapshot: Optional[dict[str, Any]] = None

    def finalize_run_response(response: dict[str, Any]) -> dict[str, Any]:
        briefing = build_run_response_briefing(
            response,
            preferences=preferences,
            recovery=recovery_snapshot,
        )
        return {
            **response,
            "headline": briefing.get("headline"),
            "userMessage": briefing.get("userMessage"),
            "resumeStatus": briefing.get("resumeStatus"),
            "resumeStatusDisplay": briefing.get("resumeStatusDisplay"),
            "executionState": briefing.get("executionState"),
            "executionStateDisplay": briefing.get("executionStateDisplay"),
            "executionHeadline": briefing.get("executionHeadline"),
            "knowledgeContext": briefing.get("knowledgeContext"),
            "knowledgeReferenceHighlights": briefing.get("knowledgeReferenceHighlights"),
            "knowledgeSourceHighlights": briefing.get("knowledgeSourceHighlights"),
            "primaryUserAction": briefing.get("primaryUserAction"),
            "primaryUserActionDisplay": briefing.get("primaryUserActionDisplay"),
            "primaryUserActionCommand": briefing.get("primaryUserActionCommand"),
            "userActionDetails": briefing.get("userActionDetails"),
            "recoveryDecision": humanize_public_recovery_decision(briefing.get("recoveryDecision")),
        }

    if not worknet_identifier and not playbook_path and isinstance(latest_run, dict):
        active = load_active_processes(state)
        if pause:
            selected = choose_default_background_process(active)
            if selected is None:
                raise ValueError("no active background task to pause")
            stopped = stop_background_process(state, str(selected.get("label")), execute=execute)
            return finalize_run_response(annotate_runtime_action_payloads({
                "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
                "status": stopped.get("status"),
                "executedSteps": [],
                "confirmationQueue": [],
                "runtimeGuidance": None,
                "followUpActions": [],
                "activeBackgroundProcesses": stopped.get("activeBackgroundProcesses", []),
                "selectedBackground": stopped.get("selectedBackground"),
                "resumedFromState": True,
                "nextAction": "monitor_background_run" if stopped.get("activeBackgroundProcesses") else "review_epoch",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }))
        if background_label:
            inspected = inspect_background_process(state, background_label, tail_lines=tail_lines)
            return finalize_run_response(annotate_runtime_action_payloads({
                "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
                "status": "background_running" if inspected.get("alive") else "planned",
                "executedSteps": [],
                "confirmationQueue": [],
                "runtimeGuidance": {
                    "message": f"{background_label} 仍在后台运行。" if inspected.get("alive") else f"{background_label} 已停止。",
                    "userActions": [],
                    "actionMap": {},
                    "nextCommand": None,
                    "nextAction": "monitor_background_run" if inspected.get("alive") else "execute_when_ready",
                    "state": None,
                    "detail": inspected.get("logPath"),
                },
                "followUpActions": [],
                "activeBackgroundProcesses": [inspected],
                "resumedFromState": True,
                "nextAction": "monitor_background_run" if inspected.get("alive") else "execute_when_ready",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }))
        if stop_background_label:
            stopped = stop_background_process(state, stop_background_label, execute=execute)
            return finalize_run_response(annotate_runtime_action_payloads({
                "mode": latest_run.get("mode") if isinstance(latest_run, dict) else "autopilot",
                "status": stopped.get("status"),
                "executedSteps": [],
                "confirmationQueue": [],
                "runtimeGuidance": None,
                "followUpActions": [],
                "activeBackgroundProcesses": stopped.get("activeBackgroundProcesses", []),
                "selectedBackground": stopped.get("selectedBackground"),
                "resumedFromState": True,
                "nextAction": "monitor_background_run" if stopped.get("activeBackgroundProcesses") else "review_epoch",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }))
        queue = normalized_confirmation_queue(pending_queue)
        if confirm_label:
            for item in queue:
                if str(item.get("label")) == confirm_label:
                    return finalize_run_response(execute_confirmation_action(
                        latest_run,
                        queue,
                        item,
                        execute=execute,
                        provided_inputs=parsed_inputs,
                        state=state,
                    ))
            raise ValueError(f"unknown confirmation label: {confirm_label}")
        if queue:
            return finalize_run_response(continue_pending_confirmations(latest_run, queue, state=state))
        follow_up_actions = normalized_follow_up_actions(latest_run.get("followUpActions", []))
        if follow_up_label:
            for item in follow_up_actions:
                if str(item.get("label")) == follow_up_label:
                    return finalize_run_response(execute_follow_up_action(
                        latest_run,
                        item,
                        execute=execute,
                        explicit_selection=True,
                        state=state,
                    ))
            source_follow_up = latest_run.get("sourceFollowUpAction")
            if isinstance(source_follow_up, dict) and str(source_follow_up.get("label")) == follow_up_label:
                fallback_actions = normalized_follow_up_actions([source_follow_up])
                if fallback_actions:
                    return finalize_run_response(execute_follow_up_action(
                        latest_run,
                        fallback_actions[0],
                        execute=execute,
                        explicit_selection=True,
                        state=state,
                    ))
            raise ValueError(f"unknown follow-up label: {follow_up_label}")
        if follow_up_actions:
            default_follow_up = choose_default_follow_up_action(follow_up_actions)
            if default_follow_up is not None:
                return finalize_run_response(execute_follow_up_action(
                    latest_run,
                    default_follow_up,
                    execute=execute,
                    explicit_selection=False,
                    state=state,
                ))
            return finalize_run_response(continue_runtime_guidance_without_default(latest_run, state=state))
        if load_active_processes(state):
            return finalize_run_response(continue_background_runs(latest_run, state=state, tail_lines=tail_lines))
    selected_worknet_identifier = worknet_identifier
    selection_warnings: list[str] = []
    redirected_to_preferred_worknet = False
    if not selected_worknet_identifier and not playbook_path:
        recovery = build_recovery_state(state)
        recovery_snapshot = recovery
        preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))
        if (
            isinstance(latest_run, dict)
            and latest_run
            and recovery.get("preferFreshStartOverResume")
            and preferred_profile is not None
            and str(preferred_profile.get("key")) != str(recovery.get("lastWorknetKey") or "")
        ):
            selected_worknet_identifier = str(preferred_profile["key"])
            redirected_to_preferred_worknet = True
            reason = humanize_recovery_stale_reason(recovery.get("staleLatestRunReason")) or "旧 run 已不适合继续恢复"
            selection_warnings.append(
                f"latest run was stale, so workstation switched to preferredWorknet={preferred_profile['key']}: {reason}"
            )
    playbook, warnings, playbook_source = load_playbook(playbook_path, selected_worknet_identifier)
    if redirected_to_preferred_worknet and playbook_source == "worknet":
        playbook_source = "preferred-worknet-over-stale-run"
    commands = playbook.get("commands", [])
    executed_steps: list[dict[str, Any]] = []
    confirmation_queue: list[dict[str, Any]] = []
    stop_execution_reason: Optional[str] = None
    primary_work_executed = False
    for command in commands:
        step = {
            "label": command.get("label"),
            "cwd": command.get("cwd"),
            "argv": command.get("argv"),
            "category": command.get("category"),
            "executionPolicy": command.get("executionPolicy"),
            "status": command_status_without_execution(command, execute=execute),
        }
        policy = str(command.get("executionPolicy", "manual"))
        if command.get("requires_confirmation"):
            confirmation_queue.append(step)
        elif not command.get("argv"):
            pass
        elif execute and policy not in {"probe", "setup", "primary-work"}:
            step["status"] = "available_manual"
            executed_steps.append(step)
            continue
        elif stop_execution_reason:
            step["status"] = "blocked_after_previous_step"
            step["reason"] = stop_execution_reason
        elif execute:
            if policy == "primary-work" and primary_work_executed:
                step["status"] = "skipped_after_primary_work"
                executed_steps.append(step)
                continue
            result = run_command(command["argv"], cwd=command.get("cwd"))
            step["status"] = "ok" if result["ok"] else "failed"
            step["result"] = {
                "code": result["code"],
                "stdout": trim_output(parse_json_loose(result["stdout"])),
                "stderr": trim_output(result["stderr"]),
            }
            worknet_key = str(playbook.get("worknetKey") or "").strip().lower()
            guidance = extract_runtime_guidance_from_payload(
                step["result"]["stdout"],
                worknet_key=worknet_key or None,
            )
            if guidance:
                step["runtimeGuidance"] = guidance
            if policy == "primary-work":
                primary_work_executed = True
                stop_execution_reason = "primary work step already executed; remaining control commands stay manual"
            elif policy == "setup" and result["ok"] is False:
                stop_execution_reason = f"{command.get('label')} failed"
        executed_steps.append(step)
    runtime_guidance, follow_up_actions = synthesize_run_guidance(playbook, executed_steps)
    run_record = annotate_runtime_action_payloads({
        "generatedAt": now_iso(),
        "mode": mode,
        "execute": execute,
        "playbook": playbook,
        "executedSteps": executed_steps,
        "confirmationQueue": confirmation_queue,
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "warnings": selection_warnings + warnings + state["warnings"],
    })
    latest_path = Path(state["runs"]) / "latest-run.json"
    atomic_write_json(latest_path, run_record)
    atomic_write_json(
        Path(state["runs"]) / "pending-confirmations.json",
        confirmation_queue,
    )
    append_jsonl(Path(state["runs"]) / "history.jsonl", run_record)
    if execute and auto_advance and not confirmation_queue and follow_up_actions:
        default_follow_up = choose_default_follow_up_action(normalized_follow_up_actions(follow_up_actions))
        if default_follow_up is not None:
            return finalize_run_response(execute_follow_up_action(
                run_record,
                default_follow_up,
                execute=True,
                explicit_selection=False,
                state=state,
            ))
    return finalize_run_response(annotate_runtime_action_payloads({
        "mode": mode,
        "status": (
            "needs_confirmation"
            if confirmation_queue
            else ("needs_runtime_input" if runtime_guidance and follow_up_actions else ("executed" if execute else "planned"))
        ),
        "executedSteps": executed_steps,
        "confirmationQueue": confirmation_queue,
        "runtimeGuidance": runtime_guidance,
        "followUpActions": follow_up_actions,
        "resumedFromState": playbook_source == "last-selected",
        "playbookSource": playbook_source,
        "selectedWorknetKey": playbook.get("worknetKey"),
        "selectedWorknetName": playbook.get("requiredSkill"),
        "warnings": selection_warnings + warnings + state["warnings"],
        "nextAction": (
            "await_confirmation"
            if confirmation_queue
            else (
                "follow_runtime_guidance"
                if runtime_guidance and follow_up_actions
                else ("review_epoch" if execute else "execute_when_ready")
            )
        ),
        "progress": "[4/5] Work loop",
        "stateRoot": state["root"],
    }))


def build_epoch_review() -> dict[str, Any]:
    state = state_context()
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    latest_run = load_json(Path(state["runs"]) / "latest-run.json", {})
    pending_queue = load_json(Path(state["runs"]) / "pending-confirmations.json", [])
    playbook = latest_run.get("playbook", {}) if isinstance(latest_run, dict) else {}
    worknet_key = str(playbook.get("worknetKey") or "")
    knowledge_context = knowledge_context_for_worknet(knowledge_catalog, worknet_key)
    knowledge_reference_highlights = knowledge_related_reference_highlights(
        knowledge_catalog,
        knowledge_context,
    )
    knowledge_source_highlights = knowledge_related_source_highlights(
        knowledge_catalog,
        knowledge_context,
    )
    background_observations = background_observations_from_run(latest_run, state=state)
    background_by_label = {
        str(item.get("label")): item
        for item in background_observations
        if isinstance(item, dict) and item.get("label")
    }
    work_done: list[str] = []
    failures: list[str] = []
    strategy_changes: list[str] = []
    user_actions: list[str] = []
    user_action_details: list[dict[str, Any]] = []
    estimated_rewards: list[str] = []
    processed_background_labels: set[str] = set()
    for step in latest_run.get("executedSteps", []):
        label = step.get("label") or "unnamed step"
        display_label = humanize_review_step_label(worknet_key, str(label))
        status = step.get("status")
        payload = step_result_payload(step) if isinstance(step, dict) else None
        message = runtime_message(payload)
        if status in {"planned", "ok"} and runtime_payload_has_blocker(payload):
            detail = humanize_review_failure(worknet_key, step, payload) or runtime_payload_error_summary(payload) or message or status
            failures.append(f"{display_label}: {detail}")
        elif status in {"planned", "ok"}:
            detail = (
                humanize_review_step(worknet_key, step, payload)
                or message
                or humanize_review_status_token(worknet_key, str(label), status)
                or str(status)
            )
            work_done.append(f"{display_label}: {detail}")
        elif status == "started_background":
            observation = background_by_label.get(str(label), {})
            processed_background_labels.add(str(label))
            summary = observation.get("summary", {}) if isinstance(observation, dict) else {}
            headline = summary.get("headline") if isinstance(summary, dict) else None
            log_path = observation.get("logPath") if isinstance(observation, dict) else None
            detail = "已在后台启动"
            if isinstance(headline, str) and headline.strip():
                qualifier = "最近状态" if observation.get("alive") else "上次观察到的状态"
                detail += f"; {qualifier}: {headline.strip()}"
            if log_path:
                detail += f" (log: {log_path})"
            work_done.append(f"{display_label}: {detail}")
            summary_state = str(summary.get("state") or "") if isinstance(summary, dict) else ""
            summary_detail = summary.get("detail") if isinstance(summary, dict) else None
            if summary_state == "llm_error":
                failures.append(f"{display_label}: {summary_detail or headline or '后台工作循环报告了 LLM 错误'}")
        elif status in {"available_manual", "skipped_after_primary_work", "blocked_after_previous_step"}:
            continue
        elif status in {"queued_for_confirmation", "missing_runtime_command", "failed", "missing_parameters"}:
            detail = (
                humanize_review_failure(worknet_key, step, payload)
                or message
                or step.get("reason")
                or step.get("result", {}).get("stderr")
                or humanize_review_status_token(worknet_key, str(label), status)
                or str(status)
            )
            if status == "missing_parameters" and isinstance(step.get("parameterErrors"), list):
                detail = "; ".join(str(item) for item in step.get("parameterErrors", []))
            failures.append(f"{display_label}: {detail}")
    confirmation_items = (
        pending_queue
        if isinstance(pending_queue, list) and pending_queue
        else latest_run.get("confirmationQueue", [])
    )
    has_confirmation_actions = bool(confirmation_items)
    for queued in confirmation_items:
        label = str(queued.get("label") or "").strip()
        if label:
            display = humanize_review_confirmation_label(worknet_key, label)
            append_unique_text(user_actions, display)
            append_unique_action_detail(
                user_action_details,
                label=display,
                description=humanize_review_action_description(
                    worknet_key,
                    label,
                    requires_confirmation=True,
                ),
                command=workstation_confirmation_command(label, execute=False),
            )
    runtime_guidance = latest_run.get("runtimeGuidance", {})
    follow_up_actions = latest_run.get("followUpActions", [])
    if isinstance(follow_up_actions, list) and follow_up_actions:
        for item in follow_up_actions:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            command = item.get("command")
            if label:
                display = humanize_review_action_label(worknet_key, str(label))
                append_unique_text(user_actions, display)
                append_unique_action_detail(
                    user_action_details,
                    label=display,
                    description=humanize_review_action_description(worknet_key, str(label)),
                    command=review_action_command(
                        worknet_key,
                        str(label),
                        command=str(command) if isinstance(command, str) else None,
                        safe_to_auto_run=bool(item.get("safeToAutoRun")),
                        requires_confirmation=bool(item.get("requiresConfirmation")),
                    ),
                )
    elif isinstance(runtime_guidance, dict):
        for label in runtime_guidance.get("userActions", []):
            command = runtime_guidance.get("actionMap", {}).get(label)
            display = humanize_review_action_label(worknet_key, str(label))
            append_unique_text(user_actions, display)
            append_unique_action_detail(
                user_action_details,
                label=display,
                description=humanize_review_action_description(worknet_key, str(label)),
                command=command if isinstance(command, str) else None,
            )
    summary_override = summarize_worknet_review(worknet_key, latest_run)
    if isinstance(summary_override.get("workDone"), list) and summary_override.get("workDone"):
        work_done = [str(item) for item in summary_override["workDone"] if str(item).strip()]
    if isinstance(summary_override.get("failures"), list) and summary_override.get("failures"):
        failures = [str(item) for item in summary_override["failures"] if str(item).strip()]
    if isinstance(summary_override.get("strategyChanges"), list):
        for item in summary_override.get("strategyChanges", []):
            append_unique_text(strategy_changes, str(item) if str(item).strip() else None)
    if isinstance(summary_override.get("userActions"), list):
        for item in summary_override.get("userActions", []):
            append_unique_text(user_actions, str(item) if str(item).strip() else None)
    estimated_rewards.extend(reward_hints_from_run(latest_run))
    append_unique_text(estimated_rewards, public_earnings_hint_for_worknet(state, worknet_key))
    active_background_count = sum(1 for item in background_observations if item.get("alive"))
    if active_background_count == 1:
        append_unique_text(user_actions, "暂停当前运行")
        append_unique_action_detail(
            user_action_details,
            label="暂停当前运行",
            description="停止当前唯一的后台工作循环。",
            command=workstation_pause_command(execute=True),
        )
    restart_source = latest_run.get("sourceFollowUpAction", {}) if isinstance(latest_run, dict) else {}
    restart_label = str(restart_source.get("label") or "")
    for observation in background_observations:
        if not isinstance(observation, dict):
            continue
        label = str(observation.get("label") or "")
        if not label:
            continue
        summary = observation.get("summary", {})
        headline = summary.get("headline") if isinstance(summary, dict) else None
        if label not in processed_background_labels:
            detail = headline.strip() if isinstance(headline, str) and headline.strip() else "后台任务已被工作站记录"
            log_path = observation.get("logPath")
            if log_path:
                detail += f" (log: {log_path})"
            work_done.append(f"{label}: {detail}")
        append_unique_text(
            strategy_changes,
            background_strategy_change_from_summary(
                summary if isinstance(summary, dict) else {},
                alive=bool(observation.get("alive")),
            ),
        )
        if observation.get("alive"):
            inspect_label = review_background_action_label(label, inspect=True)
            stop_label = review_background_action_label(label, stop=True)
            append_unique_text(user_actions, inspect_label)
            append_unique_text(user_actions, stop_label)
            append_unique_action_detail(
                user_action_details,
                label=inspect_label,
                description="查看这个后台任务的最近状态和日志。",
                command=workstation_background_command(label, tail_lines=80),
            )
            append_unique_action_detail(
                user_action_details,
                label=stop_label,
                description="停止这个后台任务。",
                command=workstation_background_command(label, stop=True, execute=False),
            )
        elif restart_label and restart_label == label:
            restart_display = review_background_action_label(label, restart=True)
            append_unique_text(user_actions, restart_display)
            append_unique_action_detail(
                user_action_details,
                label=restart_display,
                description="按上一次保存的参数重新启动这条后台工作路径。",
                command=workstation_follow_up_command(label, execute=True),
            )
    if not estimated_rewards:
        estimated_rewards.append("当前还没有可靠收益估计，等到有公开回执或收益样本后再补。")
    if failures:
        append_unique_text(strategy_changes, "先把运行时、资格和输入条件处理稳定，再考虑继续无人值守运行。")
        append_unique_text(strategy_changes, review_runtime_safety_hint(worknet_key))
    if has_confirmation_actions:
        append_unique_text(strategy_changes, "资金类和不可逆动作先留在确认队列里，确认前不要自动推进。")
        append_unique_text(strategy_changes, review_runtime_safety_hint(worknet_key))
    prepared_scene = (
        bool(worknet_key)
        and review_all_steps_prepared(work_done)
        and not failures
        and not has_confirmation_actions
        and not user_actions
    )
    if prepared_scene:
        worknet_name = str(playbook.get("requiredSkill") or worknet_key or "当前 WorkNet").strip()
        continue_label = f"继续 {worknet_name}"
        append_unique_text(user_actions, continue_label)
        append_unique_action_detail(
            user_action_details,
            label=continue_label,
            description="继续沿用上一次保存的这条工作路线。",
            command=run_worknet_command(worknet_key, execute=True, auto_advance=True),
        )
    if isinstance(knowledge_context, dict) and str(knowledge_context.get("freshnessStatus") or "") == "affected":
        label = str(knowledge_context.get("label") or worknet_key or "当前 WorkNet").strip()
        append_unique_text(strategy_changes, f"{label} 这条高层知识当前也有上游变更，继续自动运行前先复核官方来源。")
        append_unique_text(user_actions, f"查看 {label} 档案")
        append_unique_action_detail(
            user_action_details,
            label=f"查看 {label} 档案",
            description=knowledge_action_description(knowledge_context),
            command=knowledge_context.get("queryCommand"),
        )
        primary_command = str(knowledge_context.get("primaryCommand") or "").strip()
        query_command = str(knowledge_context.get("queryCommand") or "").strip()
        if primary_command and primary_command != query_command:
            append_unique_text(user_actions, f"重审 {label}")
            append_unique_action_detail(
                user_action_details,
                label=f"重审 {label}",
                description=knowledge_refresh_action_description(knowledge_context),
                command=primary_command,
            )
    for item in knowledge_source_highlights[:3]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        append_unique_text(user_actions, f"查看来源 {label}")
        append_unique_action_detail(
            user_action_details,
            label=f"查看来源 {label}",
            description=knowledge_source_action_description(item),
            command=item.get("queryCommand"),
        )
        primary_command = str(item.get("primaryCommand") or "").strip()
        query_command = str(item.get("queryCommand") or "").strip()
        if primary_command and primary_command != query_command:
            append_unique_text(user_actions, f"重读来源 {label}")
            append_unique_action_detail(
                user_action_details,
                label=f"重读来源 {label}",
                description=f"重新拉取 {label}，确认上游变化有没有影响这轮复盘结论。",
                command=primary_command,
            )
    for item in strategy_changes_from_guidance(runtime_guidance, worknet_key=worknet_key):
        if (
            item == "工作循环已经在后台运行，接下来重点看日志和下一次复盘。"
            and active_background_count == 0
        ):
            continue
        append_unique_text(strategy_changes, item)
    if isinstance(runtime_guidance, dict) and runtime_guidance.get("state") == "selection_required":
        append_unique_text(strategy_changes, "Mine 需要先选定 dataset，工作循环才能进入持续运行和产出阶段")
    status = review_status_code(worknet_key, work_done, failures, strategy_changes)
    user_actions, user_action_details = prioritize_review_actions(
        worknet_key,
        status,
        user_actions,
        user_action_details,
    )
    user_action_details = annotate_execution_actions(user_action_details)
    headline = build_review_headline(worknet_key, work_done, failures, strategy_changes)
    reporter_note = build_reporter_note(
        knowledge_context,
        knowledge_reference_highlights,
        knowledge_source_highlights,
    )
    daily_summary = build_daily_summary(
        worknet_key,
        headline,
        estimated_rewards,
        user_actions,
        reporter_note=reporter_note,
    )
    review = {
        "generatedAt": now_iso(),
        "worknetKey": worknet_key or None,
        "worknetName": playbook.get("requiredSkill") if isinstance(playbook, dict) else None,
        "status": status,
        "statusDisplay": review_status_display(status),
        "resumeStatus": None,
        "resumeStatusDisplay": None,
        "executionState": status,
        "executionStateDisplay": review_status_display(status),
        "executionHeadline": headline,
        "headline": headline,
        "dailySummary": daily_summary,
        "reporterNote": reporter_note,
        "knowledgeContext": compact_knowledge_context(knowledge_context),
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "primaryUserAction": user_actions[0] if user_actions else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "workDone": work_done,
        "estimatedRewards": estimated_rewards,
        "failures": failures,
        "strategyChanges": strategy_changes,
        "userActions": user_actions,
        "userActionDetails": user_action_details,
        "progress": "[5/5] Review",
        "stateRoot": state["root"],
    }
    atomic_write_json(Path(state["reviews"]) / "latest-review.json", review)
    return review


def build_workstation_status(
    *,
    query: Optional[str] = None,
    intent: Optional[str] = None,
    worknet_identifier: Optional[str] = None,
    source_identifier: Optional[str] = None,
) -> dict[str, Any]:
    state = state_context()
    preferences = ensure_user_preferences(state)
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    knowledge_overview = (
        knowledge_catalog.get("knowledgeOverview", {})
        if isinstance(knowledge_catalog.get("knowledgeOverview"), dict)
        else {}
    )
    knowledge_focus_topics = knowledge_focus_topics_payload(knowledge_catalog)
    knowledge_reference_highlights = knowledge_reference_highlights_payload(knowledge_catalog)
    knowledge_source_highlights = knowledge_source_highlights_payload(knowledge_catalog)
    topic_directory = knowledge_catalog.get("topicDirectory", []) if isinstance(knowledge_catalog.get("topicDirectory"), list) else []
    start_response = build_start_response()
    preflight = (
        start_response.get("_internal", {}).get("preflight", {})
        if isinstance(start_response.get("_internal"), dict)
        else {}
    )
    review = build_epoch_review()
    knowledge_review_queue = load_cached_knowledge_review_queue(state) or build_knowledge_review_queue(state=state)
    knowledge_review_queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
    resolved_intent = resolve_workstation_status_intent(query, explicit_intent=intent)
    target_profile = detect_worknet_from_text(query, explicit_identifier=worknet_identifier)
    target_source = detect_source_from_text(
        query,
        explicit_identifier=source_identifier,
        catalog=knowledge_catalog,
    )
    if (
        target_source is not None
        and resolved_intent == "status"
        and not (isinstance(intent, str) and intent.strip())
        and isinstance(source_identifier, str)
        and source_identifier.strip()
    ):
        resolved_intent = "research"
    recovery_decision = (
        preflight.get("recoveryDecision")
        if isinstance(preflight.get("recoveryDecision"), dict)
        else None
    )
    bundle = load_cached_capability_bundle(state)
    if target_profile or resolved_intent == "switch-worknet":
        bundle = bundle or build_capability_bundle()

    reports_by_key: dict[str, dict[str, Any]] = {}
    if isinstance(bundle, dict):
        for item in bundle.get("reports", []):
            if not isinstance(item, dict):
                continue
            profile = (
                resolve_worknet(str(item.get("worknetId") or ""))
                or resolve_worknet(str(item.get("name") or ""))
                or resolve_worknet(str(item.get("symbol") or ""))
            )
            if profile is not None:
                reports_by_key[profile["key"]] = item

    review_generated_at = str(review.get("generatedAt") or now_iso())
    current_worknet_key = str(review.get("worknetKey") or "").strip() or None
    current_worknet_name = str(review.get("worknetName") or "").strip() or None
    current_status = str(review.get("status") or preflight.get("nextAction") or "idle")
    current_headline = str(review.get("headline") or start_response.get("user_message") or "Workstation 状态可用。")
    current_answer = str(review.get("dailySummary") or start_response.get("user_message") or current_headline)

    knowledge_caveat = None
    if resolved_intent == "review-queue":
        knowledge_caveat = str(knowledge_review_queue_summary.get("headline") or "").strip() or None
    elif target_source is not None:
        knowledge_caveat = knowledge_review_queue_note_for_target(
            knowledge_review_queue,
            target_source.get("key"),
            target_label=humanize_knowledge_source_label(target_source.get("name") or target_source.get("key")),
        )
    elif target_profile is not None:
        knowledge_caveat = knowledge_review_queue_note_for_target(
            knowledge_review_queue,
            target_profile.get("key"),
            target_label=target_profile.get("name"),
        )
    elif current_worknet_key:
        knowledge_caveat = knowledge_review_queue_note_for_target(
            knowledge_review_queue,
            current_worknet_key,
            target_label=current_worknet_name,
        )

    user_actions: list[dict[str, Any]] = []
    action_map: dict[str, str] = {}

    headline = current_headline
    answer = current_answer
    status = current_status
    worknet_key = target_profile.get("key") if isinstance(target_profile, dict) else current_worknet_key
    worknet_name = target_profile.get("name") if isinstance(target_profile, dict) else current_worknet_name
    source_key = str(target_source.get("key") or "").strip() if isinstance(target_source, dict) else None
    source_name = (
        humanize_knowledge_source_label(target_source.get("name") or target_source.get("key"))
        if isinstance(target_source, dict)
        else None
    )
    source_record: Optional[dict[str, Any]] = None
    topic_knowledge_record: Optional[dict[str, Any]] = None
    target_worknet_display: Optional[dict[str, Any]] = None
    related_source_highlights: list[dict[str, Any]] = []
    source_topic_highlights: list[dict[str, Any]] = []
    source_fact_highlights: list[dict[str, Any]] = []
    source_worknet_highlights: list[dict[str, Any]] = []
    source_evidence_highlights: list[dict[str, Any]] = []
    research_action_groups: list[dict[str, Any]] = []
    research_current_labels: list[str] = []
    research_control_labels: list[str] = []
    research_source_labels: list[str] = []
    research_topic_labels: list[str] = []
    research_worknet_labels: list[str] = []
    research_reference_labels: list[str] = []

    if resolved_intent == "status":
        merge_payload_user_actions(user_actions, action_map, start_response)
        if isinstance(recovery_decision, dict):
            maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
        recovery_mode = str(preflight.get("nextAction") or "") in {
            "resume_previous_run",
            "resume_runtime_guidance",
            "resume_pending_confirmations",
            "monitor_background_runs",
        }
        if recovery_mode and isinstance(recovery_decision, dict):
            headline = str(recovery_decision.get("headline") or start_response.get("user_message") or current_headline)
            answer = str(recovery_decision.get("message") or start_response.get("user_message") or current_answer)
            status = str(recovery_decision.get("status") or preflight.get("nextAction") or current_status)
        else:
            headline = str(start_response.get("user_message") or current_headline)
            answer = str(review.get("dailySummary") or start_response.get("user_message") or current_answer)
            status = str(review.get("status") or preflight.get("nextAction") or current_status)
    elif resolved_intent == "continue":
        merge_payload_user_actions(user_actions, action_map, start_response)
        recovery = (
            preflight.get("recovery", {})
            if isinstance(preflight.get("recovery"), dict)
            else {}
        )
        preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))
        resume_briefing = build_resume_recovery_briefing(
            recovery,
            user_actions,
            worknet_name=worknet_name,
            preferred_profile=preferred_profile,
            context_message=None,
            action_map=action_map,
        )
        headline = str(resume_briefing.get("headline") or start_response.get("user_message") or current_headline)
        answer = str(resume_briefing.get("message") or start_response.get("user_message") or review.get("dailySummary") or current_answer)
        status = str(resume_briefing.get("status") or review.get("status") or preflight.get("nextAction") or current_status)
        if isinstance(resume_briefing.get("decision"), dict):
            recovery_decision = resume_briefing.get("decision")
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
    elif resolved_intent == "earnings":
        rewards = [str(item).strip() for item in review.get("estimatedRewards", []) if str(item).strip()]
        headline = "收益状态"
        if rewards:
            answer = f"按 {review_generated_at} 这次本地复盘，{rewards[0]}"
            if len(rewards) > 1:
                answer += " " + rewards[1]
            status = "estimated"
        else:
            answer = f"按 {review_generated_at} 这次本地复盘，还没有可用的收益估计。"
            status = "unavailable"
        append_user_action(
            user_actions,
            action_map,
            label="查看上次复盘",
            description="先看最近一次工作记录、收益样本和下一步动作。",
            command=review_epoch_command(),
        )
        merge_payload_user_actions(user_actions, action_map, start_response)
        if isinstance(recovery_decision, dict):
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision)
    elif resolved_intent == "failures":
        failures = [str(item).strip() for item in review.get("failures", []) if str(item).strip()]
        strategy_changes = [str(item).strip() for item in review.get("strategyChanges", []) if str(item).strip()]
        headline = "失败原因"
        if failures:
            answer = f"按 {review_generated_at} 这次本地复盘，主要失败点是 {failures[0]}"
            if len(failures) > 1:
                answer += f"；另外还有 {len(failures) - 1} 条失败记录。"
            status = "blocked" if str(review.get("status") or "") == "blocked" else "partial"
        else:
            answer = f"按 {review_generated_at} 这次本地复盘，没有记录到明确失败。"
            status = "clear"
        if strategy_changes:
            answer += f" 当前策略调整是：{strategy_changes[0]}"
        append_user_action(
            user_actions,
            action_map,
            label="查看上次复盘",
            description="展开看完整失败记录、策略调整和下一步动作。",
            command=review_epoch_command(),
        )
        merge_payload_user_actions(user_actions, action_map, start_response)
        if isinstance(recovery_decision, dict):
            merge_recovery_decision_actions(user_actions, action_map, recovery_decision)
    elif resolved_intent == "pause":
        active = [summarize_background_record(item, tail_lines=30) for item in load_active_processes(state)]
        if not active:
            headline = "暂停状态"
            answer = "当前没有后台任务在跑。"
            status = "idle"
            merge_payload_user_actions(user_actions, action_map, start_response)
            if isinstance(recovery_decision, dict):
                maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
        elif len(active) == 1:
            item = active[0]
            summary = item.get("summary", {}) if isinstance(item.get("summary"), dict) else {}
            background_headline = str(summary.get("headline") or "后台任务仍在运行。").strip()
            headline = "暂停当前运行"
            answer = f"当前有 1 个后台任务在跑：{background_headline}"
            status = "background_running"
            if isinstance(recovery_decision, dict) and str(recovery_decision.get("status") or "").strip() == "background_running":
                merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
            if not user_actions:
                append_user_action(
                    user_actions,
                    action_map,
                    label="暂停当前运行",
                    description="停止当前唯一的后台工作循环。",
                    command=workstation_pause_command(execute=True),
                )
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"查看 {item.get('label')}",
                    description="先看这个后台任务的最近状态和日志。",
                    command=workstation_background_command(str(item.get("label")), tail_lines=80),
                )
                if isinstance(recovery_decision, dict):
                    maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
        else:
            headline = "暂停当前运行"
            answer = f"当前有 {len(active)} 个后台任务在跑，先选定要停哪一个。"
            status = "background_running"
            if isinstance(recovery_decision, dict) and str(recovery_decision.get("status") or "").strip() == "background_running":
                merge_recovery_decision_actions(user_actions, action_map, recovery_decision, prefer_front=True)
            if not user_actions:
                for item in active[:3]:
                    label = str(item.get("label") or "").strip()
                    if not label:
                        continue
                    append_user_action(
                        user_actions,
                        action_map,
                        label=f"停止 {label}",
                        description="停止这个后台任务。",
                        command=workstation_background_command(label, stop=True, execute=False),
                    )
                    append_user_action(
                        user_actions,
                        action_map,
                        label=f"查看 {label}",
                        description="先看这个后台任务的最近状态和日志。",
                        command=workstation_background_command(label, tail_lines=80),
                    )
                if isinstance(recovery_decision, dict):
                    maybe_promote_recovery_decision(user_actions, action_map, recovery_decision)
    elif resolved_intent == "switch-worknet":
        bundle = bundle or build_capability_bundle()
        recommendation = recommend_worknet_actions(bundle, preferences=preferences)
        if target_profile is not None:
            target_key = str(target_profile.get("key"))
            target_name = str(target_profile.get("name"))
            target_report = reports_by_key.get(target_key, {})
            runnable = bool(target_report.get("runnable"))
            summary = humanize_worknet_switch_summary(target_profile, target_report)
            headline = f"切换到 {target_name}"
            if runnable:
                answer = summary
                status = "runnable"
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"开始 {target_name}",
                    description=(
                        canonical_worknet_switch_summary_text(
                            target_profile,
                            runnable=runnable,
                            can_start_without_stake=target_report.get("canStartWithoutStake") is True,
                        )
                        or "直接按这个 WorkNet 的默认节奏启动；若碰到资金动作仍会先进入确认队列。"
                    ),
                    command=run_worknet_command(target_key, execute=True, auto_advance=True),
                )
            else:
                answer = summary
                status = "discover_only"
            append_user_action(
                user_actions,
                action_map,
                label=f"把 {target_name} 设为默认 WorkNet",
                description="把这个 WorkNet 写回默认偏好，下次 generic 推荐会优先考虑它。",
                command=workstation_preferences_command(preferred_worknet=target_key),
            )
            append_user_action(
                user_actions,
                action_map,
                label=f"查看 {target_name} 档案",
                description="先看这个 WorkNet 的知识档案和当前限制。",
                command=query_knowledge_command(target_key),
            )
            append_user_action(
                user_actions,
                action_map,
                label=f"生成 {target_name} playbook",
                description="先生成这个 WorkNet 的执行计划，再决定是否启动。",
                command=build_playbook_command(target_key),
            )
        else:
            headline = "换一个 WorkNet"
            answer = str(recommendation.get("recommendation") or "先看当前可做的 WorkNet。")
            status = "switch_suggested"
            for item in recommendation.get("actions", []):
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                description = str(item.get("description") or "执行这个 WorkNet 建议动作。")
                command = recommendation.get("actionMap", {}).get(label)
                append_user_action(
                    user_actions,
                    action_map,
                    label=label,
                    description=description,
                    command=command if isinstance(command, str) else None,
                )
            preferred_profile = resolve_worknet(str(preferences.get("preferredWorknet") or ""))
            if preferred_profile is not None:
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"查看当前默认 {preferred_profile.get('name')}",
                    description="先看你当前保存的默认 WorkNet，再决定要不要改。",
                    command=query_knowledge_command(str(preferred_profile.get("key"))),
                )
            append_user_action(
                user_actions,
                action_map,
                label="查看 WorkNet 扫描",
                description="先看当前所有 WorkNet 的可运行性和风险。",
                command=scan_worknets_command(),
            )
    elif resolved_intent == "safety":
        active = load_active_processes(state)
        headline = "资金安全策略"
        answer = (
            "当前默认只自动跑非资金类工作；所有质押、投票、下单、转账和其他不可逆动作都要先确认。"
        )
        answer += (
            f" 当前 autopilot 模式是 {preferences.get('autopilotMode')}，"
            f"allowAssetActions={str(bool(preferences.get('allowAssetActions'))).lower()}。"
        )
        status = "non_financial_only" if str(preferences.get("autopilotMode")) == "non-financial-only" else "custom"
        append_user_action(
            user_actions,
            action_map,
            label="锁定为非资金模式",
            description="把默认自动模式写回为 non-financial-only，并明确关闭资产动作自动化。",
            command=workstation_preferences_command(
                allow_asset_actions=False,
                autopilot_mode="non-financial-only",
            ),
        )
        if active:
            append_user_action(
                user_actions,
                action_map,
                label="暂停当前运行",
                description="如果你想先完全停住自动流程，可以直接暂停当前后台任务。",
                command=workstation_pause_command(execute=True),
            )
        append_user_action(
            user_actions,
            action_map,
            label="查看预检",
            description="检查当前钱包、注册和保护边界。",
            command=workstation_preflight_command(full=True),
        )
        append_user_action(
            user_actions,
            action_map,
            label="查看上次复盘",
            description="确认最近一次运行有没有碰到需要人工确认的资金动作。",
            command=review_epoch_command(),
        )
    elif resolved_intent == "review-queue":
        review_queue_payload = build_knowledge_query_result("review-queue", catalog=knowledge_catalog)
        headline = str(review_queue_payload.get("headline") or "知识待重审队列")
        answer = str(review_queue_payload.get("summary") or knowledge_review_queue_summary.get("headline") or "当前没有待重审的知识条目。")
        status = str(review_queue_payload.get("status") or ("stale_knowledge_pending" if knowledge_review_queue_summary.get("hasPendingReviews") else "knowledge_fresh"))
        worknet_key = None
        worknet_name = None
        merge_payload_user_action_details(user_actions, action_map, review_queue_payload, limit=8)
        if isinstance(review_queue_payload.get("researchActionGroups"), list):
            research_action_groups = review_queue_payload.get("researchActionGroups", [])
        queue_primary_label = str(review_queue_payload.get("primaryUserAction") or knowledge_review_queue_summary.get("primaryActionLabel") or "").strip()
        if queue_primary_label:
            research_current_labels.append(queue_primary_label)
        queue_topic_actions = review_queue_payload.get("userActionDetails", []) if isinstance(review_queue_payload, dict) else []
        for item in queue_topic_actions:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label or label == queue_primary_label:
                continue
            if label.startswith("重读来源 ") or label.startswith("查看来源 "):
                research_source_labels.append(label)
            elif label.startswith("重审主题 ") or label.startswith("查看主题 ") or label.startswith("重审 "):
                research_topic_labels.append(label)
            elif label in {"刷新知识待重审队列", "查看知识待重审队列"}:
                research_control_labels.append(label)
        queue_refresh_label = str(knowledge_review_queue_summary.get("refreshActionLabel") or "").strip()
        if queue_refresh_label:
            research_control_labels.append(queue_refresh_label)
    elif resolved_intent == "research":
        status = "stale_knowledge_pending" if knowledge_review_queue_summary.get("hasPendingReviews") else "knowledge_ready"
        if target_source is not None:
            source_key = str(target_source.get("key") or "").strip() or None
            source_name = humanize_knowledge_source_label(target_source.get("name") or target_source.get("key")) or source_key
            if source_key:
                source_record = build_source_query_result(source_key, catalog=knowledge_catalog)
            if isinstance(source_record, dict):
                source_topic_highlights = source_record.get("topicHighlights", []) if isinstance(source_record.get("topicHighlights"), list) else []
                source_fact_highlights = source_record.get("factHighlights", []) if isinstance(source_record.get("factHighlights"), list) else []
                source_worknet_highlights = source_record.get("worknetHighlights", []) if isinstance(source_record.get("worknetHighlights"), list) else []
                source_evidence_highlights = source_record.get("evidenceHighlights", []) if isinstance(source_record.get("evidenceHighlights"), list) else []
            source_display = (
                source_record.get("sourceDisplay", {})
                if isinstance(source_record, dict) and isinstance(source_record.get("sourceDisplay"), dict)
                else {}
            )
            if isinstance(source_display, dict):
                source_name = str(source_display.get("nameDisplay") or source_name or source_key).strip() or source_name
            headline = str(source_record.get("headline") or (f"研究来源 {source_name}" if source_name else "研究来源"))
            answer = str(
                (
                    source_display.get("summaryPreview")
                    if isinstance(source_display, dict)
                    else None
                )
                or source_record.get("summaryPreview")
                or source_record.get("summary")
                or headline
            )
            drift = (
                source_record.get("drift", {})
                if isinstance(source_record, dict) and isinstance(source_record.get("drift"), dict)
                else {}
            )
            drift_status = str(drift.get("status") or "").strip()
            status = "source_review_needed" if drift_status and drift_status not in {"unchanged", "no-baseline"} else "source_ready"
            worknet_key = None
            worknet_name = None
            merge_payload_user_action_details(user_actions, action_map, source_record, limit=5)
            if isinstance(source_record, dict) and isinstance(source_record.get("researchActionGroups"), list):
                research_action_groups = source_record.get("researchActionGroups", [])
            if isinstance(source_record, dict):
                for index, item in enumerate(source_record.get("userActionDetails", [])):
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get("label") or "").strip()
                    if not label:
                        continue
                    if index == 0:
                        research_current_labels.append(label)
                    elif label in {"查看知识待重审队列", "刷新知识待重审队列"}:
                        research_control_labels.append(label)
                    elif label.startswith("查看主题 "):
                        research_topic_labels.append(label)
                    elif label.startswith("查看工作网 "):
                        research_worknet_labels.append(label)
        elif target_profile is not None:
            topic_entry = find_topic_directory_entry(
                topic_directory,
                key=str(target_profile.get("key") or ""),
                worknet_key=str(target_profile.get("key") or ""),
            )
            if isinstance(topic_entry, dict):
                label = str(topic_entry.get("label") or target_profile.get("name") or target_profile.get("key") or "目标主题").strip()
                headline = f"研究 {label}"
                status = "knowledge_review_needed" if str(topic_entry.get("freshnessStatus") or "") == "affected" else "knowledge_ready"
                worknet_key = target_profile.get("key")
                worknet_name = target_profile.get("name")
                topic_key_for_record = str(topic_entry.get("key") or target_profile.get("key") or "").strip()
                if topic_key_for_record:
                    topic_knowledge_record = build_knowledge_query_result(
                        topic_key_for_record,
                        catalog=knowledge_catalog,
                    )
                    if isinstance(topic_knowledge_record.get("worknetDisplay"), dict):
                        target_worknet_display = topic_knowledge_record.get("worknetDisplay")
                    answer = str(
                        topic_knowledge_record.get("summary")
                        or topic_entry.get("summary")
                        or topic_entry.get("headline")
                        or knowledge_overview.get("summary")
                        or headline
                    )
                    status = str(topic_knowledge_record.get("status") or status)
                    merge_payload_user_action_details(user_actions, action_map, topic_knowledge_record, limit=5)
                    if isinstance(topic_knowledge_record.get("researchActionGroups"), list):
                        research_action_groups = topic_knowledge_record.get("researchActionGroups", [])
                    if isinstance(topic_knowledge_record, dict):
                        for index, item in enumerate(topic_knowledge_record.get("userActionDetails", [])):
                            if not isinstance(item, dict):
                                continue
                            label = str(item.get("label") or "").strip()
                            if not label:
                                continue
                            if index == 0 or label.startswith("刷新 ") or label.startswith("重审 "):
                                research_current_labels.append(label)
                            elif label.startswith("查看来源 ") or label.startswith("重读来源 "):
                                research_source_labels.append(label)
                            else:
                                research_worknet_labels.append(label)
                else:
                    answer = str(topic_entry.get("summary") or topic_entry.get("headline") or knowledge_overview.get("summary") or headline)
                related_source_highlights = knowledge_related_source_highlights(
                    knowledge_catalog,
                    topic_entry,
                    limit=3,
                )
                for item in related_source_highlights[:2]:
                    if not isinstance(item, dict):
                        continue
                    source_label = str(item.get("label") or item.get("key") or "").strip()
                    append_user_action(
                        user_actions,
                        action_map,
                        label=f"查看来源 {source_label}",
                        description=knowledge_source_action_description(item),
                        command=item.get("queryCommand"),
                    )
                    research_source_labels.append(f"查看来源 {source_label}")
            else:
                headline = str(knowledge_overview.get("headline") or "研究 AWP 百科")
                answer = str(knowledge_overview.get("summary") or "当前本地百科已可直接使用。")
        else:
            headline = str(knowledge_overview.get("headline") or "研究 AWP 百科")
            answer = str(knowledge_overview.get("summary") or "当前本地百科已可直接使用。")
            worknet_key = None
            worknet_name = None
            if knowledge_review_queue_summary.get("hasPendingReviews"):
                append_user_action(
                    user_actions,
                    action_map,
                    label=knowledge_review_queue_summary.get("refreshActionLabel"),
                    description="重新刷新官方来源，再重建整份知识待重审队列。",
                    command=knowledge_review_queue_summary.get("refreshActionCommand"),
                )
                refresh_label = str(knowledge_review_queue_summary.get("refreshActionLabel") or "").strip()
                if refresh_label:
                    research_control_labels.append(refresh_label)
            for item in knowledge_focus_topics[:5]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or item.get("key") or "").strip()
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"查看 {label}",
                    description=knowledge_action_description(item),
                    command=item.get("queryCommand"),
                )
                research_topic_labels.append(f"查看 {label}")
            for item in knowledge_source_highlights[:3]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or item.get("key") or "").strip()
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"查看来源 {label}",
                    description=knowledge_source_action_description(item),
                    command=item.get("queryCommand"),
                )
                research_source_labels.append(f"查看来源 {label}")
            for item in knowledge_reference_highlights[:2]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or item.get("key") or "").strip()
                append_user_action(
                    user_actions,
                    action_map,
                    label=f"查看参考 {label}",
                    description="如果你要追底层规则、运行时约束或协议细节，就直接看这条参考条目。",
                    command=item.get("queryCommand"),
                )
                research_reference_labels.append(f"查看参考 {label}")
            append_user_action(
                user_actions,
                action_map,
                label="查看 WorkNet 扫描",
                description="回到当前所有 WorkNet 的可运行性、风险和推荐角色对比。",
                command=scan_worknets_command(),
            )
            research_worknet_labels.append("查看 WorkNet 扫描")

    if knowledge_review_queue_summary.get("hasPendingReviews"):
        append_user_action(
            user_actions,
            action_map,
            label=knowledge_review_queue_summary.get("primaryActionLabel"),
            description="查看最近哪些官方资料发生变化，以及哪些知识条目需要重审。",
            command=knowledge_review_queue_summary.get("primaryActionCommand"),
        )
        queue_label = str(knowledge_review_queue_summary.get("primaryActionLabel") or "").strip()
        if queue_label:
            if resolved_intent == "research" and target_source is None and target_profile is None:
                if queue_label not in research_control_labels:
                    research_control_labels.insert(0, queue_label)
            elif resolved_intent in {"research", "review-queue"} and queue_label not in research_control_labels and queue_label not in research_current_labels:
                research_control_labels.append(queue_label)

    resume_status = str(recovery_decision.get("status") or start_response.get("resumeStatus") or "").strip() or None
    runtime_execution_state = derive_execution_state(
        review=review,
        recovery=preflight.get("recovery"),
        next_action=preflight.get("nextAction"),
    )
    report_resume_status = resume_status
    report_execution_state = runtime_execution_state
    if resolved_intent == "research":
        report_resume_status = None
        if isinstance(source_record, dict):
            report_execution_state = {
                "executionState": source_record.get("executionState"),
                "executionStateDisplay": source_record.get("executionStateDisplay"),
                "executionHeadline": source_record.get("executionHeadline"),
            }
        elif isinstance(topic_knowledge_record, dict):
            report_execution_state = {
                "executionState": topic_knowledge_record.get("executionState"),
                "executionStateDisplay": topic_knowledge_record.get("executionStateDisplay"),
                "executionHeadline": topic_knowledge_record.get("executionHeadline"),
            }
        else:
            report_execution_state = execution_state_payload(status, headline=headline)
    elif resolved_intent == "review-queue":
        report_resume_status = None
        report_execution_state = execution_state_payload(status, headline=headline)
    action_priority_state = report_execution_state.get("executionState") or runtime_execution_state.get("executionState")
    action_priority_resume = report_resume_status
    if resolved_intent in {"switch-worknet", "pause"}:
        action_priority_state = status
        action_priority_resume = None
    if resolved_intent in {"status", "continue", "earnings", "failures", "research", "switch-worknet", "pause", "review-queue"}:
        user_actions = prioritize_ui_actions(
            user_actions,
            action_map,
            execution_state=action_priority_state,
            resume_status=action_priority_resume,
            worknet_key=worknet_key or current_worknet_key,
        )
    if resolved_intent == "research":
        if target_source is None and target_profile is None:
            ordered_research_labels = [
                *research_current_labels,
                *research_control_labels,
                *research_source_labels,
                *research_topic_labels,
                *research_worknet_labels,
                *research_reference_labels,
            ]
        else:
            ordered_research_labels = [
                *research_current_labels,
                *research_source_labels,
                *research_topic_labels,
                *research_worknet_labels,
                *research_control_labels,
                *research_reference_labels,
            ]
        user_actions = frontload_user_action_labels(user_actions, ordered_research_labels)
    elif resolved_intent == "review-queue":
        ordered_review_queue_labels = [
            *research_current_labels,
            *research_source_labels,
            *research_topic_labels,
            *research_worknet_labels,
            *research_control_labels,
        ]
        user_actions = frontload_user_action_labels(user_actions, ordered_review_queue_labels)
    if resolved_intent in {"status", "continue"}:
        answer = align_run_execution_user_message(
            answer,
            execution_state=runtime_execution_state.get("executionState"),
            execution_headline=runtime_execution_state.get("executionHeadline"),
            primary_action=user_actions[0]["label"] if user_actions else None,
            worknet_context_key=worknet_key or current_worknet_key,
            include_canonical_plain=False,
        ) or answer
    if resolved_intent == "research" and target_source is None and target_profile is None:
        user_actions = annotate_research_action_details(
            user_actions,
            current_labels=[],
            control_labels=[
                knowledge_review_queue_summary.get("primaryActionLabel"),
                knowledge_review_queue_summary.get("refreshActionLabel"),
            ],
            source_labels=[
                f"查看来源 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_source_highlights[:3]
                if isinstance(item, dict)
            ],
            topic_labels=[
                f"查看 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_focus_topics[:5]
                if isinstance(item, dict)
            ],
            worknet_labels=["查看 WorkNet 扫描"],
            reference_labels=[
                f"查看参考 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_reference_highlights[:2]
                if isinstance(item, dict)
            ],
            control_tier="overview",
            source_tier="overview",
            topic_tier="overview",
            worknet_tier="overview",
            reference_tier="overview",
        )
    elif resolved_intent == "research":
        user_actions = annotate_research_action_details(
            user_actions,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            current_tier="current",
            control_tier="queued",
            source_tier="related",
            topic_tier="related",
            worknet_tier="related",
            reference_tier="related",
        )
    elif resolved_intent == "review-queue":
        user_actions = annotate_research_action_details(
            user_actions,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="queued",
            worknet_tier="queued",
        )
    else:
        user_actions = annotate_execution_actions(user_actions)
    public_user_actions = humanize_public_action_entries(user_actions)
    public_preflight = dict(preflight)
    public_preflight["recoveryDecision"] = humanize_public_recovery_decision(preflight.get("recoveryDecision"))
    report = {
        "generatedAt": now_iso(),
        "query": query,
        "intent": resolved_intent,
        "progress": "[5/5] Workstation Status",
        "headline": headline,
        "answer": answer,
        "status": status,
        "resumeStatus": report_resume_status,
        "resumeStatusDisplay": recovery_status_display(report_resume_status) if report_resume_status else None,
        "executionState": report_execution_state.get("executionState"),
        "executionStateDisplay": report_execution_state.get("executionStateDisplay"),
        "executionHeadline": report_execution_state.get("executionHeadline"),
        "worknetKey": worknet_key,
        "worknetName": worknet_name,
        "sourceKey": source_key,
        "sourceName": source_name,
        "knowledgeCaveat": knowledge_caveat,
        "recoveryDecision": humanize_public_recovery_decision(recovery_decision),
        "knowledgeReviewQueueSummary": knowledge_review_queue_summary,
        "knowledgeOverview": knowledge_overview,
        "knowledgeFocusTopics": knowledge_focus_topics,
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "sourceTopicHighlights": source_topic_highlights,
        "sourceFactHighlights": source_fact_highlights,
        "sourceWorknetHighlights": source_worknet_highlights,
        "sourceEvidenceHighlights": source_evidence_highlights,
        "knowledgeRecord": topic_knowledge_record,
        "sourceRecord": source_record,
        "targetWorknetDisplay": target_worknet_display,
        "primaryUserAction": user_actions[0]["label"] if user_actions else None,
        "primaryUserActionDisplay": None,
        "primaryUserActionCommand": None,
        "userActions": public_user_actions,
        "userActionDetails": [],
        "latestReview": {
            "generatedAt": review.get("generatedAt"),
            "status": review.get("status"),
            "statusDisplay": review.get("statusDisplay"),
            "executionState": review.get("executionState"),
            "executionStateDisplay": review.get("executionStateDisplay"),
            "executionHeadline": review.get("executionHeadline"),
            "headline": review.get("headline"),
            "dailySummary": review.get("dailySummary"),
            "reporterNote": review.get("reporterNote"),
            "estimatedRewards": review.get("estimatedRewards"),
            "failures": review.get("failures"),
            "strategyChanges": review.get("strategyChanges"),
            "primaryUserAction": review.get("primaryUserAction"),
        },
        "_internal": {
            "action_map": action_map,
            "preflight": public_preflight,
            "start_response": start_response,
            "review": review,
            "targetWorknet": target_profile,
            "targetSource": target_source,
            "targetSourceRecord": source_record,
            "targetKnowledgeRecord": topic_knowledge_record,
            "relatedSourceHighlights": related_source_highlights,
            "stateRoot": state["root"],
        },
    }
    user_action_details = action_details_from_ui_actions(user_actions, action_map)
    if resolved_intent == "research" and target_source is None and target_profile is None:
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=[],
            control_labels=[
                knowledge_review_queue_summary.get("primaryActionLabel"),
                knowledge_review_queue_summary.get("refreshActionLabel"),
            ],
            source_labels=[
                f"查看来源 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_source_highlights[:3]
                if isinstance(item, dict)
            ],
            topic_labels=[
                f"查看 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_focus_topics[:5]
                if isinstance(item, dict)
            ],
            worknet_labels=["查看 WorkNet 扫描"],
            reference_labels=[
                f"查看参考 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_reference_highlights[:2]
                if isinstance(item, dict)
            ],
            control_tier="overview",
            source_tier="overview",
            topic_tier="overview",
            worknet_tier="overview",
            reference_tier="overview",
        )
    elif resolved_intent == "research":
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            current_tier="current",
            control_tier="queued",
            source_tier="related",
            topic_tier="related",
            worknet_tier="related",
            reference_tier="related",
        )
    elif resolved_intent == "review-queue":
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="queued",
            worknet_tier="queued",
        )
    else:
        user_action_details = annotate_execution_actions(user_action_details)
    if not research_action_groups and resolved_intent == "research" and target_source is None and target_profile is None:
        research_action_groups = build_research_action_groups(
            user_action_details,
            current_labels=[],
            control_labels=[
                knowledge_review_queue_summary.get("primaryActionLabel"),
                knowledge_review_queue_summary.get("refreshActionLabel"),
            ],
            source_labels=[
                f"查看来源 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_source_highlights[:3]
                if isinstance(item, dict)
            ],
            topic_labels=[
                f"查看 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_focus_topics[:5]
                if isinstance(item, dict)
            ],
            worknet_labels=["查看 WorkNet 扫描"],
            reference_labels=[
                f"查看参考 {str(item.get('label') or item.get('key') or '').strip()}"
                for item in knowledge_reference_highlights[:2]
                if isinstance(item, dict)
            ],
            control_first=True,
        )
    elif not research_action_groups and resolved_intent in {"research", "review-queue"}:
        research_action_groups = build_research_action_groups(
            user_action_details,
            current_labels=research_current_labels,
            control_labels=research_control_labels,
            source_labels=research_source_labels,
            topic_labels=research_topic_labels,
            worknet_labels=research_worknet_labels,
            reference_labels=research_reference_labels,
            control_first=False,
        )
    report["userActionDetails"] = user_action_details
    report["researchActionGroups"] = research_action_groups
    report["primaryUserActionDisplay"] = user_action_details[0]["displayLabel"] if user_action_details else None
    report["primaryUserActionCommand"] = user_action_details[0]["command"] if user_action_details else None
    atomic_write_json(Path(state["cache"]) / "workstation-status.json", report)
    return report


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


def build_coverage_audit(
    *,
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
    source_facts: Optional[dict[str, Any]] = None,
    source_evidence: Optional[dict[str, Any]] = None,
    topic_dossiers: Optional[dict[str, Any]] = None,
    glossary: Optional[dict[str, Any]] = None,
    skill_inspections: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    state = state or state_context()
    inventory = inventory or build_source_inventory(state=state)
    source_facts = source_facts or build_source_fact_catalog()
    source_evidence = source_evidence or build_source_evidence_catalog()
    topic_dossiers = topic_dossiers or build_topic_dossier_catalog()
    glossary = glossary or build_glossary_catalog()
    live_worknets = load_cached_live_worknets(state)
    source_drift = load_cached_source_drift(state)
    source_impact = load_cached_source_impact(state)
    knowledge_review_queue = load_cached_knowledge_review_queue(state)
    skill_inspections = skill_inspections or load_cached_skill_inspection_catalog(state)
    local_sources = {
        item["key"]: item for item in inventory.get("localSources", []) if isinstance(item, dict)
    }
    skill_registry = {
        item["key"]: item for item in skill_registry_from_inventory(inventory, state=state)
    }
    generated_root = REFERENCE_EXPORT_ROOT

    glossary_terms = {str(item["term"]).lower(): item for item in glossary.get("terms", [])}
    dossiers = {item["key"]: item for item in topic_dossiers.get("dossiers", [])}
    evidence_records = source_evidence.get("records", [])

    def generated_exists(filename: str) -> bool:
        return (generated_root / filename).exists()

    items: list[dict[str, Any]] = []
    for requirement in KNOWLEDGE_COVERAGE_REQUIREMENTS:
        key = requirement["key"]
        status = "missing"
        reasons: list[str] = []
        evidence_files: list[str] = []

        if key == "trigger-surface":
            status = "covered"
            reasons.append("SKILL metadata includes both English and Chinese trigger phrases.")
            evidence_files.extend(["SKILL.md", "agents/openai.yaml"])
        elif key == "protocol-encyclopedia":
            if all(name in dossiers for name in ("protocol-core", "staking", "dao")) and generated_exists("source-facts.json"):
                status = "covered"
                reasons.append("Protocol core, staking, DAO, facts, and evidence are all present locally.")
            else:
                status = "partial"
                reasons.append("Some protocol knowledge layers are still incomplete.")
            evidence_files.extend(["topic-dossiers.json", "source-facts.json", "source-evidence.json", "glossary.json"])
        elif key == "worknet-coverage":
            covered = all(name in dossiers for name in ("mine", "predict", "kya", "ardi", "gov", "tmr", "community"))
            if covered:
                status = "covered"
                reasons.append("All named WorkNets have local dossiers, including the thinner TMR and Community entries.")
            else:
                status = "partial"
                reasons.append("Some named WorkNet dossier coverage is missing.")
            evidence_files.extend(["topic-dossiers.json", "worknet-profiles.md"])
        elif key == "glossary-coverage":
            required_terms = {"rootnet", "worknet", "skilluri", "epoch", "clob", "staking"}
            if required_terms.issubset(set(glossary_terms.keys())):
                status = "covered"
                reasons.append("Required AWP terms are defined in the generated glossary.")
            else:
                status = "partial"
                reasons.append("Some required terms are still missing from the generated glossary.")
            evidence_files.extend(["glossary.json", "glossary.md"])
        elif key == "source-traceability":
            if generated_exists("source-evidence.json") and evidence_records:
                status = "covered"
                reasons.append("Derived claims map to official source keys, locators, evidence types, and stability labels.")
            else:
                status = "missing"
                reasons.append("No evidence record set is available.")
            evidence_files.extend(["source-evidence.json", "evidence-model.md"])
        elif key == "registration-flow":
            registration_plan = build_registration_plan(state=state)
            cached_preflight = load_json(Path(state["cache"]) / "preflight.json", {})
            cached_registration_plan = (
                cached_preflight.get("registrationPlan", {})
                if isinstance(cached_preflight, dict)
                else {}
            )
            coverage_plan = (
                cached_registration_plan
                if isinstance(cached_registration_plan, dict) and cached_registration_plan
                else registration_plan
            )
            command_labels = [
                item.get("label")
                for item in coverage_plan.get("commands", [])
                if isinstance(item, dict)
            ]
            official_preflight = coverage_plan.get("awpSkillPreflight", {}) if isinstance(coverage_plan, dict) else {}
            official_result = official_preflight.get("result", {}) if isinstance(official_preflight, dict) else {}
            official_state = official_result.get("state", {}) if isinstance(official_result, dict) else {}
            official_registered = official_state.get("registered") is True if isinstance(official_state, dict) else False
            official_next_action = str(official_result.get("nextAction") or "").strip() if isinstance(official_result, dict) else ""
            cached_registered = cached_preflight.get("registered") is True if isinstance(cached_preflight, dict) else False
            cached_official = cached_preflight.get("cachedOfficialPreflight", {}) if isinstance(cached_preflight, dict) else {}
            cached_official_result = cached_official.get("result", {}) if isinstance(cached_official, dict) else {}
            cached_official_state = cached_official_result.get("state", {}) if isinstance(cached_official_result, dict) else {}
            cached_official_registered = (
                cached_official_state.get("registered") is True
                if isinstance(cached_official_state, dict)
                else False
            )
            cached_official_next_action = (
                str(cached_official_result.get("nextAction") or "").strip()
                if isinstance(cached_official_result, dict)
                else ""
            )
            coverage_next_action = str(coverage_plan.get("nextAction") or "").strip() if isinstance(coverage_plan, dict) else ""
            coverage_official_next_action = (
                str(coverage_plan.get("officialNextAction") or "").strip()
                if isinstance(coverage_plan, dict)
                else ""
            )
            if coverage_next_action in {
                "run_awp_skill_registration",
                "registration_ready",
                "registration_already_confirmed",
            } or cached_registered or official_registered or cached_official_registered or coverage_official_next_action == "pick_worknet" or official_next_action == "pick_worknet" or cached_official_next_action == "pick_worknet":
                status = "covered"
                if coverage_next_action == "registration_already_confirmed" or cached_registered or official_registered or cached_official_registered or coverage_official_next_action == "pick_worknet" or official_next_action == "pick_worknet" or cached_official_next_action == "pick_worknet":
                    reasons.append("The workstation already recognizes that awp-skill registration is complete and still preserves the official onboarding command path.")
                else:
                    reasons.append("The workstation has a concrete awp-skill registration command path.")
            else:
                status = "partial"
                reasons.append("The workstation now probes runtime and emits install/register commands, but full registration execution still depends on awp-skill availability.")
            if command_labels:
                reasons.append("Available registration-plan commands: " + ", ".join(str(label) for label in command_labels if label))
            evidence_files.extend(["source-facts.json", "source-evidence.json", "skill-registry.json"])
        elif key == "live-rpc-scan":
            snapshot = load_json(Path(state["cache"]) / "capability-scan.json", {})
            if snapshot.get("sourceMode") in {"rpc", "live-cache"}:
                status = "covered"
                reasons.append("Capability scan has successfully used a live official data path.")
            else:
                status = "partial"
                reasons.append("RPC methods are documented and modeled, but current environment still falls back to catalog mode.")
            evidence_files.extend(["capability-catalog.json", "source-evidence.json"])
        elif key == "skill-inspector":
            inspections_payload = skill_inspections or build_skill_inspection_catalog(state=state, inventory=inventory)
            inspections = {
                item.get("skillKey"): item
                for item in inspections_payload.get("inspections", [])
                if isinstance(item, dict)
            }
            strong_keys = ("predict", "gov", "ardi")
            minimal_keys = ("tmr", "community")
            strong_ready = all(
                inspections.get(name, {}).get("runtimeName")
                and inspections.get(name, {}).get("inspectionCommands")
                for name in strong_keys
            )
            minimal_ready = all(
                inspections.get(name, {}).get("runtimeName")
                for name in minimal_keys
            )
            empty_repo_keys = [
                name
                for name in minimal_keys
                if inspections.get(name, {}).get("status") == "empty-official-repo"
            ]
            if strong_ready and minimal_ready:
                status = "covered"
                reasons.append("Predict, Gov, and Ardi expose runtime-specific install/inspection guidance.")
                if empty_repo_keys:
                    reasons.append(
                        "TMR/Community are still covered because inspector can prove when the official checkout is present but upstream only exposes license or metadata files: "
                        + ", ".join(empty_repo_keys)
                    )
                else:
                    reasons.append("TMR/Community expose remote runtime profiles.")
            else:
                status = "partial"
                reasons.append("Some official worknet skills still lack structured inspection guidance.")
            evidence_files.extend(["skill-inspections.json", "skill-registry.json"])
        elif key == "recovery-state":
            if (Path(state["runs"]) / "latest-run.json").exists() and (Path(state["runs"]) / "pending-confirmations.json").exists():
                status = "covered"
                reasons.append("Run state and confirmation queue files exist and are reused by preflight/review.")
            else:
                status = "partial"
                reasons.append("Recovery files are not all present yet.")
            evidence_files.extend(["runs/latest-run.json", "runs/pending-confirmations.json"])
        elif key == "live-canonical-quality":
            if live_worknets and isinstance(live_worknets.get("entries"), list):
                entries = live_worknets["entries"]
                unresolved = [
                    item
                    for item in entries
                    if isinstance(item, dict)
                    and item.get("resolutionConfidence", "low") == "low"
                ]
                if not unresolved:
                    status = "covered"
                    reasons.append("All cached live worknets resolved to canonical IDs with medium or high confidence.")
                else:
                    status = "partial"
                    reasons.append(f"{len(unresolved)} cached live worknet(s) still have low-confidence canonical resolution.")
                    reasons.append(
                        "Unresolved names: "
                        + ", ".join(str(item.get("name")) for item in unresolved[:5] if item.get("name"))
                    )
            else:
                status = "partial"
                reasons.append("No cached live worknet snapshot is available yet.")
            evidence_files.extend(["official-live-worknets.json", "capability-catalog.json"])
        elif key == "upstream-drift-watch":
            if source_drift and isinstance(source_drift.get("items"), list):
                status = "covered"
                summary = source_drift.get("summary", {}) if isinstance(source_drift, dict) else {}
                changed = int(summary.get("changedSources", 0) or 0)
                unreachable = int(summary.get("currentlyUnreachable", 0) or 0)
                reasons.append("Official source refresh now emits a structured drift report with per-source content and availability comparisons.")
                reasons.append(f"Current drift summary: {changed} changed source(s), {unreachable} currently unreachable source(s).")
                if source_impact and isinstance(source_impact.get("summary"), dict):
                    impact_summary = source_impact["summary"]
                    reasons.append(
                        "Knowledge impact routing is also available: "
                        f"{int(impact_summary.get('impactedTopics', 0) or 0)} topic(s), "
                        f"{int(impact_summary.get('impactedFacts', 0) or 0)} fact set(s), "
                        f"{int(impact_summary.get('impactedWorknets', 0) or 0)} worknet profile(s)."
                    )
                    if knowledge_review_queue and isinstance(knowledge_review_queue.get("summary"), dict):
                        queue_summary = knowledge_review_queue["summary"]
                        reasons.append(
                            "A knowledge review queue is available with "
                            f"{int(queue_summary.get('entries', 0) or 0)} actionable review item(s)."
                        )
                else:
                    status = "partial"
                    reasons.append("Source drift exists, but no impacted topic/fact/worknet routing has been generated yet.")
            elif generated_exists("source-snapshot.json"):
                status = "partial"
                reasons.append("Official sources can be snapshotted, but no structured drift comparison has been generated yet.")
            else:
                status = "missing"
                reasons.append("No official source snapshot exists yet.")
            evidence_files.extend(["source-snapshot.json", "source-drift.json", "source-impact.json", "knowledge-review-queue.json"])

        items.append(
            {
                "key": key,
                "title": requirement["title"],
                "intent": requirement["intent"],
                "status": status,
                "reasons": reasons,
                "evidenceFiles": evidence_files,
            }
        )

    covered_count = sum(1 for item in items if item["status"] == "covered")
    partial_count = sum(1 for item in items if item["status"] == "partial")
    missing_count = sum(1 for item in items if item["status"] == "missing")
    audit = {
        "generatedAt": now_iso(),
        "summary": {
            "covered": covered_count,
            "partial": partial_count,
            "missing": missing_count,
        },
        "items": items,
    }
    atomic_write_json(Path(state["cache"]) / "coverage-audit.json", audit)
    write_reference_export("coverage-audit.json", audit)
    return audit


def build_display_contract_audit(
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    mine_result = build_knowledge_query_result("mine", catalog=catalog)
    protocol_result = build_knowledge_query_result("protocol-core", catalog=catalog)
    awp_skill_result = build_source_query_result("awp-skill", catalog=catalog)
    mine_skill_result = build_source_query_result("mine-skill-raw", catalog=catalog)
    changed_sources_result = build_changed_sources_query_result(catalog=catalog)

    def first_item(items: Any) -> Optional[dict[str, Any]]:
        if not isinstance(items, list):
            return None
        for item in items:
            if isinstance(item, dict):
                return item
        return None

    def first_non_runtime_evidence(items: Any) -> Optional[dict[str, Any]]:
        if not isinstance(items, list):
            return None
        for item in items:
            if isinstance(item, dict) and item.get("evidenceType") != "runtime-inspection":
                return item
        return None

    def audit_item(
        key: str,
        title: str,
        payload: Any,
        fields: list[str],
        *,
        sample_ref: Optional[str] = None,
    ) -> dict[str, Any]:
        expected = list(fields)
        if not isinstance(payload, dict):
            reasons = ["No sample payload was available for this contract."]
            if sample_ref:
                reasons.append(f"Sample ref: {sample_ref}")
            return {
                "key": key,
                "title": title,
                "status": "missing",
                "expectedFields": expected,
                "actualFields": [],
                "missingFields": expected,
                "extraFields": [],
                "reasons": reasons,
                "sampleRef": sample_ref,
            }
        actual = list(payload.keys())
        missing_fields = [field for field in expected if field not in payload]
        extra_fields = [field for field in actual if field not in expected]
        status = "covered" if not missing_fields and not extra_fields else "partial"
        reasons = [f"Observed {len(actual)} field(s); expected fixed contract size is {len(expected)}."]
        if missing_fields:
            reasons.append("Missing fields: " + ", ".join(missing_fields[:10]))
        if extra_fields:
            reasons.append("Unexpected fields: " + ", ".join(extra_fields[:10]))
        if sample_ref:
            reasons.append(f"Sample ref: {sample_ref}")
        return {
            "key": key,
            "title": title,
            "status": status,
            "expectedFields": expected,
            "actualFields": actual,
            "missingFields": missing_fields,
            "extraFields": extra_fields,
            "reasons": reasons,
            "sampleRef": sample_ref,
        }

    items = [
        audit_item(
            "dossier-display",
            "Topic dossier display contract",
            mine_result.get("dossierDisplay"),
            DOSSIER_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('mine').dossierDisplay",
        ),
        audit_item(
            "source-fact-display",
            "Topic source-fact display contract",
            mine_result.get("sourceFactDisplay"),
            SOURCE_FACT_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('mine').sourceFactDisplay",
        ),
        audit_item(
            "worknet-display",
            "Topic worknet display contract",
            mine_result.get("worknetDisplay"),
            WORKNET_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('mine').worknetDisplay",
        ),
        audit_item(
            "source-record-display",
            "Source record display contract",
            awp_skill_result.get("sourceDisplay"),
            SOURCE_RECORD_DISPLAY_FIELDS,
            sample_ref="build_source_query_result('awp-skill').sourceDisplay",
        ),
        audit_item(
            "citation-display",
            "Citation display contract",
            first_item(protocol_result.get("citationsDisplay")),
            CITATION_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('protocol-core').citationsDisplay[0]",
        ),
        audit_item(
            "evidence-display",
            "Evidence display contract",
            first_non_runtime_evidence(protocol_result.get("evidenceDisplay")),
            RUNTIME_PROBE_EVIDENCE_FIELDS,
            sample_ref="build_knowledge_query_result('protocol-core').evidenceDisplay[non-runtime]",
        ),
        audit_item(
            "runtime-evidence-display",
            "Runtime evidence display contract",
            first_item(mine_skill_result.get("evidenceDisplay")),
            RUNTIME_PROBE_EVIDENCE_FIELDS,
            sample_ref="build_source_query_result('mine-skill-raw').evidenceDisplay[0]",
        ),
        audit_item(
            "drift-display",
            "Source drift display contract",
            awp_skill_result.get("driftDisplay"),
            DRIFT_DISPLAY_FIELDS,
            sample_ref="build_source_query_result('awp-skill').driftDisplay",
        ),
        audit_item(
            "changed-source-display",
            "Changed source list item contract",
            first_item(changed_sources_result.get("changedSourcesDisplay")),
            DRIFT_DISPLAY_FIELDS,
            sample_ref="build_changed_sources_query_result().changedSourcesDisplay[0]",
        ),
        audit_item(
            "source-impact-display",
            "Source impact display contract",
            awp_skill_result.get("impactDisplay"),
            SOURCE_IMPACT_DISPLAY_FIELDS,
            sample_ref="build_source_query_result('awp-skill').impactDisplay",
        ),
        audit_item(
            "source-impact-item-display",
            "Source impact item contract",
            first_item((awp_skill_result.get("impactDisplay") or {}).get("items")),
            SOURCE_IMPACT_ITEM_FIELDS,
            sample_ref="build_source_query_result('awp-skill').impactDisplay.items[0]",
        ),
        audit_item(
            "freshness-display",
            "Freshness display contract",
            protocol_result.get("freshnessDisplay"),
            FRESHNESS_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('protocol-core').freshnessDisplay",
        ),
        audit_item(
            "freshness-item-display",
            "Freshness item display contract",
            first_item((protocol_result.get("freshnessDisplay") or {}).get("items")),
            FRESHNESS_ITEM_FIELDS,
            sample_ref="build_knowledge_query_result('protocol-core').freshnessDisplay.items[0]",
        ),
    ]

    covered_count = sum(1 for item in items if item["status"] == "covered")
    partial_count = sum(1 for item in items if item["status"] == "partial")
    missing_count = sum(1 for item in items if item["status"] == "missing")
    return {
        "generatedAt": now_iso(),
        "summary": {
            "covered": covered_count,
            "partial": partial_count,
            "missing": missing_count,
        },
        "items": items,
    }


def build_glossary_query_result(
    term: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    catalog = catalog if isinstance(catalog, dict) else build_glossary_catalog()
    query = str(term or "").strip().lower()
    match = None
    for item in catalog.get("terms", []):
        candidates = [str(item.get("term", "")).lower()]
        candidates.extend(str(alias).lower() for alias in item.get("aliases", []))
        if query in candidates:
            match = item
            break
    normalized_match = normalize_glossary_query_match_payload(match) if isinstance(match, dict) else None
    normalized_match_display = normalize_glossary_item_payload(match) if isinstance(match, dict) else None
    return normalize_query_payload(
        {
            "query": query,
            "match": normalized_match,
            "matchDisplay": normalized_match_display,
        },
        GLOSSARY_QUERY_FIELDS,
    )


def build_query_contract_audit(
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    knowledge_result = build_knowledge_query_result("mine", catalog=catalog)
    review_queue_result = build_knowledge_query_result("review-queue", catalog=catalog)
    source_result = build_source_query_result("awp-skill", catalog=catalog)
    changed_result = build_changed_sources_query_result(catalog=catalog)
    glossary_result = build_glossary_query_result("rootnet")

    def first_item(items: Any) -> Optional[dict[str, Any]]:
        if not isinstance(items, list):
            return None
        for item in items:
            if isinstance(item, dict):
                return item
        return None

    def audit_item(
        key: str,
        title: str,
        payload: Any,
        fields: list[str],
        *,
        sample_ref: Optional[str] = None,
    ) -> dict[str, Any]:
        expected = list(fields)
        if not isinstance(payload, dict):
            reasons = ["No sample payload was available for this query contract."]
            if sample_ref:
                reasons.append(f"Sample ref: {sample_ref}")
            return {
                "key": key,
                "title": title,
                "status": "missing",
                "expectedFields": expected,
                "actualFields": [],
                "missingFields": expected,
                "extraFields": [],
                "reasons": reasons,
                "sampleRef": sample_ref,
            }
        actual = list(payload.keys())
        missing_fields = [field for field in expected if field not in payload]
        extra_fields = [field for field in actual if field not in expected]
        status = "covered" if not missing_fields and not extra_fields else "partial"
        reasons = [f"Observed {len(actual)} field(s); expected fixed contract size is {len(expected)}."]
        if missing_fields:
            reasons.append("Missing fields: " + ", ".join(missing_fields[:10]))
        if extra_fields:
            reasons.append("Unexpected fields: " + ", ".join(extra_fields[:10]))
        if sample_ref:
            reasons.append(f"Sample ref: {sample_ref}")
        return {
            "key": key,
            "title": title,
            "status": status,
            "expectedFields": expected,
            "actualFields": actual,
            "missingFields": missing_fields,
            "extraFields": extra_fields,
            "reasons": reasons,
            "sampleRef": sample_ref,
        }

    items = [
        audit_item(
            "knowledge-query",
            "Primary knowledge query contract",
            knowledge_result,
            KNOWLEDGE_QUERY_FIELDS,
            sample_ref="build_knowledge_query_result('mine')",
        ),
        audit_item(
            "knowledge-review-queue-query",
            "Review-queue knowledge query contract",
            review_queue_result,
            KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS,
            sample_ref="build_knowledge_query_result('review-queue')",
        ),
        audit_item(
            "source-query",
            "Source query contract",
            source_result,
            SOURCE_QUERY_FIELDS,
            sample_ref="build_source_query_result('awp-skill')",
        ),
        audit_item(
            "changed-sources-query",
            "Changed-sources query contract",
            changed_result,
            CHANGED_SOURCES_QUERY_FIELDS,
            sample_ref="build_changed_sources_query_result()",
        ),
        audit_item(
            "glossary-query",
            "Glossary query contract",
            glossary_result,
            GLOSSARY_QUERY_FIELDS,
            sample_ref="build_glossary_query_result('rootnet')",
        ),
        audit_item(
            "source-review-scope",
            "Source review-scope contract",
            source_result.get("reviewScope"),
            REVIEW_SCOPE_FIELDS,
            sample_ref="build_source_query_result('awp-skill').reviewScope",
        ),
        audit_item(
            "glossary-query-match",
            "Glossary match contract",
            glossary_result.get("match"),
            GLOSSARY_QUERY_MATCH_FIELDS,
            sample_ref="build_glossary_query_result('rootnet').match",
        ),
        audit_item(
            "glossary-query-match-display",
            "Glossary match display contract",
            glossary_result.get("matchDisplay"),
            GLOSSARY_ITEM_FIELDS,
            sample_ref="build_glossary_query_result('rootnet').matchDisplay",
        ),
    ]

    covered_count = sum(1 for item in items if item["status"] == "covered")
    partial_count = sum(1 for item in items if item["status"] == "partial")
    missing_count = sum(1 for item in items if item["status"] == "missing")
    return {
        "generatedAt": now_iso(),
        "summary": {
            "covered": covered_count,
            "partial": partial_count,
            "missing": missing_count,
        },
        "items": items,
    }


def build_public_contract_audit() -> dict[str, Any]:
    preflight = public_preflight_view(build_preflight_report())
    capability_bundle = build_capability_bundle()
    capability_reports = capability_bundle.get("reports", []) if isinstance(capability_bundle, dict) else []
    capability_public = public_capability_view(capability_reports[0]) if capability_reports and isinstance(capability_reports[0], dict) else None
    start_response = build_start_response()
    run_response = run_workstation(mode="autopilot", worknet_identifier="mine", execute=False)
    workstation_status_full = build_workstation_status(query="研究 Mine")
    workstation_status_public = public_workstation_status_view(workstation_status_full)
    playbook_public = public_playbook_view(build_work_playbook("mine"))
    review_public = public_review_view(build_epoch_review())

    def first_item(items: Any) -> Optional[dict[str, Any]]:
        if not isinstance(items, list):
            return None
        for item in items:
            if isinstance(item, dict):
                return item
        return None

    def audit_item(
        key: str,
        title: str,
        payload: Any,
        fields: list[str],
        *,
        sample_ref: Optional[str] = None,
    ) -> dict[str, Any]:
        expected = list(fields)
        if not isinstance(payload, dict):
            reasons = ["No sample payload was available for this public contract."]
            if sample_ref:
                reasons.append(f"Sample ref: {sample_ref}")
            return {
                "key": key,
                "title": title,
                "status": "missing",
                "expectedFields": expected,
                "actualFields": [],
                "missingFields": expected,
                "extraFields": [],
                "reasons": reasons,
                "sampleRef": sample_ref,
            }
        actual = list(payload.keys())
        missing_fields = [field for field in expected if field not in payload]
        extra_fields = [field for field in actual if field not in expected]
        status = "covered" if not missing_fields and not extra_fields else "partial"
        reasons = [f"Observed {len(actual)} field(s); expected fixed contract size is {len(expected)}."]
        if missing_fields:
            reasons.append("Missing fields: " + ", ".join(missing_fields[:10]))
        if extra_fields:
            reasons.append("Unexpected fields: " + ", ".join(extra_fields[:10]))
        if sample_ref:
            reasons.append(f"Sample ref: {sample_ref}")
        return {
            "key": key,
            "title": title,
            "status": status,
            "expectedFields": expected,
            "actualFields": actual,
            "missingFields": missing_fields,
            "extraFields": extra_fields,
            "reasons": reasons,
            "sampleRef": sample_ref,
        }

    items = [
        audit_item(
            "public-preflight",
            "Public preflight contract",
            preflight,
            PREFLIGHT_PUBLIC_FIELDS,
            sample_ref="public_preflight_view(build_preflight_report())",
        ),
        audit_item(
            "public-capability",
            "Public capability-report contract",
            capability_public,
            CAPABILITY_PUBLIC_FIELDS,
            sample_ref="public_capability_view(build_capability_bundle().reports[0])",
        ),
        audit_item(
            "public-playbook",
            "Public playbook contract",
            playbook_public,
            PLAYBOOK_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('mine'))",
        ),
        audit_item(
            "public-playbook-command",
            "Public playbook command-item contract",
            first_item(playbook_public.get("commands") if isinstance(playbook_public, dict) else None),
            PLAYBOOK_COMMAND_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('mine')).commands[0]",
        ),
        audit_item(
            "public-playbook-user-action-detail",
            "Public playbook user-action-detail contract",
            first_item(playbook_public.get("userActionDetails") if isinstance(playbook_public, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('mine')).userActionDetails[0]",
        ),
        audit_item(
            "public-review",
            "Public review contract",
            review_public,
            REVIEW_PUBLIC_FIELDS,
            sample_ref="public_review_view(build_epoch_review())",
        ),
        audit_item(
            "public-review-user-action-detail",
            "Public review user-action-detail contract",
            first_item(review_public.get("userActionDetails") if isinstance(review_public, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_review_view(build_epoch_review()).userActionDetails[0]",
        ),
        audit_item(
            "start-response",
            "Start-response contract",
            start_response,
            START_RESPONSE_FIELDS,
            sample_ref="build_start_response()",
        ),
        audit_item(
            "start-response-user-action",
            "Start-response user-action contract",
            first_item(start_response.get("user_actions") if isinstance(start_response, dict) else None),
            PUBLIC_ACTION_FIELDS,
            sample_ref="build_start_response().user_actions[0]",
        ),
        audit_item(
            "run-response",
            "Run-response contract",
            run_response,
            RUN_RESPONSE_FIELDS,
            sample_ref="run_workstation(mode='autopilot', worknet_identifier='mine', execute=False)",
        ),
        audit_item(
            "run-response-user-action-detail",
            "Run-response user-action-detail contract",
            first_item(run_response.get("userActionDetails") if isinstance(run_response, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="run_workstation(...).userActionDetails[0]",
        ),
        audit_item(
            "workstation-status-full",
            "Full workstation-status contract",
            workstation_status_full,
            WORKSTATION_STATUS_INTERNAL_FIELDS,
            sample_ref="build_workstation_status(query='研究 Mine')",
        ),
        audit_item(
            "workstation-status-public",
            "Public workstation-status contract",
            workstation_status_public,
            WORKSTATION_STATUS_PUBLIC_FIELDS,
            sample_ref="public_workstation_status_view(build_workstation_status(query='研究 Mine'))",
        ),
        audit_item(
            "workstation-status-user-action",
            "Public workstation-status user-action contract",
            first_item(workstation_status_public.get("userActions") if isinstance(workstation_status_public, dict) else None),
            PUBLIC_ACTION_FIELDS,
            sample_ref="public_workstation_status_view(...).userActions[0]",
        ),
        audit_item(
            "workstation-status-user-action-detail",
            "Public workstation-status user-action-detail contract",
            first_item(workstation_status_public.get("userActionDetails") if isinstance(workstation_status_public, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_workstation_status_view(...).userActionDetails[0]",
        ),
    ]

    covered_count = sum(1 for item in items if item["status"] == "covered")
    partial_count = sum(1 for item in items if item["status"] == "partial")
    missing_count = sum(1 for item in items if item["status"] == "missing")
    return {
        "generatedAt": now_iso(),
        "summary": {
            "covered": covered_count,
            "partial": partial_count,
            "missing": missing_count,
        },
        "items": items,
    }


def build_branch_contract_audit() -> dict[str, Any]:
    start_response = build_start_response()
    run_response = run_workstation(mode="autopilot", worknet_identifier="mine", execute=False)
    workstation_status = build_workstation_status(query="研究 Mine")

    synthetic_runtime_guidance = annotate_runtime_guidance_payload(
        {
            "message": "Wallet session expired; reinitialize first.",
            "state": "auth_required",
            "userActions": ["re-initialize", "check status"],
            "actionMap": {
                "re-initialize": "bash bootstrap.sh",
                "check status": "python3 scripts/run_tool.py agent-status",
            },
            "nextCommand": ["python3", "scripts/run_tool.py", "agent-status"],
        },
        worknet_key="mine",
    )

    synthetic_follow_up_items = annotate_raw_follow_up_actions([
        {
            "label": "继续当前运行",
            "description": "继续这条 runtime 建议动作。",
            "command": "python3 scripts/run-workstation.py --mode autopilot --execute",
            "argv": ["python3", "scripts/run-workstation.py", "--mode", "autopilot", "--execute"],
            "safeToAutoRun": True,
            "requiresConfirmation": False,
        }
    ])
    synthetic_follow_up = synthetic_follow_up_items[0] if synthetic_follow_up_items else None

    synthetic_confirmation_items = annotate_raw_confirmation_queue([
        {
            "label": "确认提交",
            "description": "确认并执行这个待确认动作。",
            "command": "python3 scripts/run-workstation.py --confirm-label 确认提交",
            "requiresConfirmation": True,
            "requiredInputs": [
                {"name": "amount", "prompt": "输入数量", "placeholder": "100"},
            ],
        }
    ])
    synthetic_confirmation = synthetic_confirmation_items[0] if synthetic_confirmation_items else None

    synthetic_selected_confirmation = annotate_selected_confirmation(
        {
            "label": "确认提交",
            "requiredInputs": [
                {"name": "amount", "prompt": "输入数量", "placeholder": "100"},
            ],
        }
    )

    synthetic_background = annotate_background_record(
        {
            "label": "mine-worker",
            "pid": 123,
            "cwd": "/tmp",
            "argv": ["python3", "worker.py"],
            "logPath": "/tmp/mine.log",
            "startedAt": "2026-05-22T00:00:00Z",
            "alive": False,
            "logTail": "tail",
            "summary": {"headline": "Mine 后台任务已停止。", "status": "stopped"},
        }
    )

    synthetic_recovery_decision = humanize_public_recovery_decision(
        {
            "decision": "resume_previous_run",
            "status": "restart_available",
            "headline": "继续上次运行",
            "message": "继续旧 run。",
            "lastWorknetName": "Mine",
            "preferredWorknetName": "Predict",
            "primaryActionLabel": "继续 Mine",
            "restartActionLabel": "重新启动 Mine",
            "switchActionLabel": "改按默认 Predict 开始",
            "staleReason": "old run stopped",
            "actions": [
                {
                    "label": "继续 Mine",
                    "description": "继续旧 run",
                    "command": "python3 scripts/run-workstation.py --mode autopilot --execute",
                },
                {
                    "label": "查看上次复盘",
                    "description": "看复盘",
                    "command": "python3 scripts/review-epoch.py",
                },
            ],
        }
    )

    parameter_schema_display = annotate_parameter_schema_items(
        [{"name": "amount", "prompt": "输入数量", "placeholder": "100"}]
    )
    synthetic_parameter_schema_item = parameter_schema_display[0] if parameter_schema_display else None
    synthetic_step = {
        "label": "gov private state",
        "status": "failed",
        "result": {
            "code": 1,
            "stdout": {
                "state": "blocked",
                "message": "[Errno -2] Name or service not known",
                "detail": "trace detail",
                "user_actions": ["check status", "re-initialize"],
                "_internal": {
                    "action_map": {
                        "check status": "python3 scripts/private/state.py",
                        "re-initialize": "bash bootstrap.sh",
                    },
                    "next_action": "follow_runtime_guidance",
                    "next_command": "python3 scripts/private/state.py",
                },
            },
            "stderr": "Traceback: boom",
        },
    }
    synthetic_result_display = build_executed_step_result_display("gov", synthetic_step)
    synthetic_stdout_display = (
        synthetic_result_display.get("stdoutDisplay")
        if isinstance(synthetic_result_display, dict)
        and isinstance(synthetic_result_display.get("stdoutDisplay"), dict)
        else None
    )
    synthetic_stdout_guidance = (
        synthetic_stdout_display.get("guidance")
        if isinstance(synthetic_stdout_display, dict)
        and isinstance(synthetic_stdout_display.get("guidance"), dict)
        else None
    )
    synthetic_probe = annotate_probe_result_display(
        {
            "label": "predict status",
            "code": 1,
            "text": "failed to fetch status: check coordinator connectivity",
            "result": {
                "state": "blocked",
                "message": "failed to fetch status: check coordinator connectivity",
                "detail": "failed to fetch status: check coordinator connectivity",
                "user_actions": ["check status", "re-initialize"],
                "_internal": {
                    "action_map": {
                        "check status": "python3 scripts/run_tool.py agent-status",
                        "re-initialize": "bash bootstrap.sh",
                    },
                    "next_action": "follow_runtime_guidance",
                    "next_command": "bash bootstrap.sh",
                },
            },
        },
        skill_key="predict",
    )
    synthetic_probe_result_display = (
        synthetic_probe.get("resultDisplay")
        if isinstance(synthetic_probe, dict)
        and isinstance(synthetic_probe.get("resultDisplay"), dict)
        else None
    )
    synthetic_probe_stdout_display = (
        synthetic_probe.get("stdoutDisplay")
        if isinstance(synthetic_probe, dict)
        and isinstance(synthetic_probe.get("stdoutDisplay"), dict)
        else None
    )
    synthetic_probe_runtime_guidance_display = (
        synthetic_probe.get("runtimeGuidanceDisplay")
        if isinstance(synthetic_probe, dict)
        and isinstance(synthetic_probe.get("runtimeGuidanceDisplay"), dict)
        else None
    )

    def first_item(items: Any) -> Optional[dict[str, Any]]:
        if not isinstance(items, list):
            return None
        for item in items:
            if isinstance(item, dict):
                return item
        return None

    def audit_item(
        key: str,
        title: str,
        payload: Any,
        fields: list[str],
        *,
        sample_ref: Optional[str] = None,
    ) -> dict[str, Any]:
        expected = list(fields)
        if not isinstance(payload, dict):
            reasons = ["No sample payload was available for this branch contract."]
            if sample_ref:
                reasons.append(f"Sample ref: {sample_ref}")
            return {
                "key": key,
                "title": title,
                "status": "missing",
                "expectedFields": expected,
                "actualFields": [],
                "missingFields": expected,
                "extraFields": [],
                "reasons": reasons,
                "sampleRef": sample_ref,
            }
        actual = list(payload.keys())
        missing_fields = [field for field in expected if field not in payload]
        extra_fields = [field for field in actual if field not in expected]
        status = "covered" if not missing_fields and not extra_fields else "partial"
        reasons = [f"Observed {len(actual)} field(s); expected fixed contract size is {len(expected)}."]
        if missing_fields:
            reasons.append("Missing fields: " + ", ".join(missing_fields[:10]))
        if extra_fields:
            reasons.append("Unexpected fields: " + ", ".join(extra_fields[:10]))
        if sample_ref:
            reasons.append(f"Sample ref: {sample_ref}")
        return {
            "key": key,
            "title": title,
            "status": status,
            "expectedFields": expected,
            "actualFields": actual,
            "missingFields": missing_fields,
            "extraFields": extra_fields,
            "reasons": reasons,
            "sampleRef": sample_ref,
        }

    items = [
        audit_item(
            "start-recovery-decision",
            "Start-response recovery-decision contract",
            start_response.get("recoveryDecision"),
            RECOVERY_DECISION_FIELDS,
            sample_ref="build_start_response().recoveryDecision",
        ),
        audit_item(
            "run-recovery-decision",
            "Run-response recovery-decision contract",
            run_response.get("recoveryDecision"),
            RECOVERY_DECISION_FIELDS,
            sample_ref="run_workstation(...).recoveryDecision",
        ),
        audit_item(
            "status-recovery-decision",
            "Workstation-status recovery-decision contract",
            workstation_status.get("recoveryDecision"),
            RECOVERY_DECISION_FIELDS,
            sample_ref="build_workstation_status(...).recoveryDecision",
        ),
        audit_item(
            "synthetic-recovery-decision",
            "Synthetic recovery-decision contract",
            synthetic_recovery_decision,
            RECOVERY_DECISION_FIELDS,
            sample_ref="humanize_public_recovery_decision({...})",
        ),
        audit_item(
            "synthetic-follow-up-action",
            "Synthetic follow-up action contract",
            synthetic_follow_up,
            FOLLOW_UP_ACTION_FIELDS,
            sample_ref="annotate_raw_follow_up_actions([...])[0]",
        ),
        audit_item(
            "synthetic-confirmation-queue-item",
            "Synthetic confirmation-queue item contract",
            synthetic_confirmation,
            CONFIRMATION_QUEUE_ITEM_FIELDS,
            sample_ref="annotate_raw_confirmation_queue([...])[0]",
        ),
        audit_item(
            "synthetic-selected-confirmation",
            "Synthetic selected-confirmation contract",
            synthetic_selected_confirmation,
            SELECTED_CONFIRMATION_FIELDS,
            sample_ref="annotate_selected_confirmation({...})",
        ),
        audit_item(
            "synthetic-background-record",
            "Synthetic background-record contract",
            synthetic_background,
            BACKGROUND_RECORD_FIELDS,
            sample_ref="annotate_background_record({...})",
        ),
        audit_item(
            "run-executed-step",
            "Run-response executed-step contract",
            first_item(run_response.get("executedSteps")),
            EXECUTED_STEP_FIELDS,
            sample_ref="run_workstation(...).executedSteps[0]",
        ),
        audit_item(
            "parameter-schema-item",
            "Parameter-schema display item contract",
            synthetic_parameter_schema_item,
            PARAMETER_SCHEMA_ITEM_FIELDS,
            sample_ref="annotate_parameter_schema_items([...])[0]",
        ),
        audit_item(
            "runtime-guidance",
            "Synthetic runtime-guidance contract",
            synthetic_runtime_guidance,
            RUNTIME_GUIDANCE_FIELDS,
            sample_ref="annotate_runtime_guidance_payload({...})",
        ),
        audit_item(
            "runtime-guidance-user-action-detail",
            "Synthetic runtime-guidance user-action-detail contract",
            first_item(synthetic_runtime_guidance.get("userActionDetails") if isinstance(synthetic_runtime_guidance, dict) else None),
            RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS,
            sample_ref="annotate_runtime_guidance_payload({...}).userActionDetails[0]",
        ),
        audit_item(
            "executed-step-result-display",
            "Synthetic executed-step result-display contract",
            synthetic_result_display,
            EXECUTED_STEP_RESULT_DISPLAY_FIELDS,
            sample_ref="build_executed_step_result_display('gov', synthetic_step)",
        ),
        audit_item(
            "executed-step-stdout-display",
            "Synthetic executed-step stdout-display contract",
            synthetic_stdout_display,
            EXECUTED_STEP_STDOUT_DISPLAY_FIELDS,
            sample_ref="build_executed_step_result_display(...).stdoutDisplay",
        ),
        audit_item(
            "executed-step-stdout-guidance",
            "Synthetic executed-step stdout guidance contract",
            synthetic_stdout_guidance,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="build_executed_step_result_display(...).stdoutDisplay.guidance",
        ),
        audit_item(
            "probe-result-display",
            "Synthetic probe result-display contract",
            synthetic_probe_result_display,
            EXECUTED_STEP_RESULT_DISPLAY_FIELDS,
            sample_ref="annotate_probe_result_display({...}).resultDisplay",
        ),
        audit_item(
            "probe-stdout-display",
            "Synthetic probe stdout-display contract",
            synthetic_probe_stdout_display,
            EXECUTED_STEP_STDOUT_DISPLAY_FIELDS,
            sample_ref="annotate_probe_result_display({...}).stdoutDisplay",
        ),
        audit_item(
            "probe-runtime-guidance-display",
            "Synthetic probe runtime-guidance-display contract",
            synthetic_probe_runtime_guidance_display,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="annotate_probe_result_display({...}).runtimeGuidanceDisplay",
        ),
    ]

    covered_count = sum(1 for item in items if item["status"] == "covered")
    partial_count = sum(1 for item in items if item["status"] == "partial")
    missing_count = sum(1 for item in items if item["status"] == "missing")
    return {
        "generatedAt": now_iso(),
        "summary": {
            "covered": covered_count,
            "partial": partial_count,
            "missing": missing_count,
        },
        "items": items,
    }


def build_topic_dossier_catalog() -> dict[str, Any]:
    state = state_context()
    source_map = {item["key"]: item for item in OFFICIAL_WEB_SOURCES}
    dossiers: list[dict[str, Any]] = []
    for item in DERIVED_TOPIC_DOSSIERS:
        dossier = dict(item)
        dossier["officialUrls"] = [
            source_map[key]["url"]
            for key in item.get("sourceKeys", [])
            if key in source_map
        ]
        dossiers.append(dossier)
    catalog = {
        "generatedAt": now_iso(),
        "dossiers": dossiers,
    }
    atomic_write_json(Path(state["cache"]) / "topic-dossiers.json", catalog)
    write_reference_export("topic-dossiers.json", catalog)
    return catalog


def build_knowledge_catalog(*, rebuild_derived: bool = False) -> dict[str, Any]:
    state = state_context()
    preferences = ensure_user_preferences(state)
    inventory = build_source_inventory()
    skill_registry = skill_registry_from_inventory(inventory, state=state)
    skill_inspections = build_skill_inspection_catalog(state=state, inventory=inventory)
    source_facts = build_source_fact_catalog()
    source_evidence = build_source_evidence_catalog()
    glossary = build_glossary_catalog()
    topic_dossiers = build_topic_dossier_catalog()
    coverage_audit = build_coverage_audit(
        state=state,
        inventory=inventory,
        source_facts=source_facts,
        source_evidence=source_evidence,
        topic_dossiers=topic_dossiers,
        glossary=glossary,
        skill_inspections=skill_inspections,
    )
    if rebuild_derived:
        source_drift = build_source_drift_report(state=state)
        source_impact = build_source_drift_impact_report(
            state=state,
            drift_report=source_drift,
            topic_dossiers=topic_dossiers,
            source_facts=source_facts,
            source_evidence=source_evidence,
        )
        topic_freshness = build_topic_freshness_catalog(
            state=state,
            source_impact=source_impact,
            topic_dossiers=topic_dossiers,
            source_facts=source_facts,
        )
        knowledge_review_queue = build_knowledge_review_queue(
            state=state,
            source_impact=source_impact,
            topic_freshness=topic_freshness,
            source_evidence=source_evidence,
        )
    else:
        source_drift = load_cached_source_drift(state) or build_source_drift_report(state=state)
        source_impact = load_cached_source_impact(state) or build_source_drift_impact_report(
            state=state,
            drift_report=source_drift,
            topic_dossiers=topic_dossiers,
            source_facts=source_facts,
            source_evidence=source_evidence,
        )
        topic_freshness = load_cached_topic_freshness(state) or build_topic_freshness_catalog(
            state=state,
            source_impact=source_impact,
            topic_dossiers=topic_dossiers,
            source_facts=source_facts,
        )
        knowledge_review_queue = load_cached_knowledge_review_queue(state) or build_knowledge_review_queue(
            state=state,
            source_impact=source_impact,
            topic_freshness=topic_freshness,
            source_evidence=source_evidence,
        )
    catalog = {
        "generatedAt": now_iso(),
        "schemaVersion": KNOWLEDGE_CATALOG_SCHEMA_VERSION,
        "protocolDefaults": {
            "stateRoot": state["root"],
            "rpcUrl": DEFAULT_RPC_URL,
            "allowlistedSkillPrefixes": list(OFFICIAL_SKILL_ALLOWLIST_PREFIXES),
        },
        "userPreferences": preferences,
        "safetyRules": SAFETY_RULES,
        "sources": inventory,
        "sourceDrift": source_drift,
        "sourceImpact": source_impact,
        "topicFreshness": topic_freshness,
        "knowledgeReviewQueue": knowledge_review_queue,
        "sourceFacts": source_facts["facts"],
        "sourceEvidence": source_evidence["records"],
        "glossary": glossary["terms"],
        "topicDossiers": topic_dossiers["dossiers"],
        "coverageAudit": coverage_audit,
        "skills": skill_registry,
        "skillInspections": skill_inspections["inspections"],
        "worknets": [
            {
                "key": item["key"],
                "worknetId": item["worknet_id"],
                "name": item["name"],
                "status": item["status"],
                "symbol": item["symbol"],
                "installUri": item.get("install_uri"),
                "sourceKeys": item.get("source_keys", []),
                "goal": item["goal"],
                "loop": item["loop"],
                "automationLevel": item["automation_level"],
                "riskLevel": item["risk_level"],
                "recommendedRole": item["recommended_role"],
            }
            for item in KNOWN_WORKNETS
        ],
    }
    topic_index = build_knowledge_topic_index(catalog)
    topic_directory = build_knowledge_topic_directory(topic_index)
    reference_index = build_knowledge_reference_index(topic_index)
    source_directory = build_knowledge_source_directory(catalog)
    catalog["knowledgeOverview"] = build_knowledge_overview(
        catalog,
        topic_index=topic_index,
        topic_directory=topic_directory,
        reference_index=reference_index,
        source_directory=source_directory,
    )
    catalog["topicIndex"] = topic_index
    catalog["topicDirectory"] = topic_directory
    catalog["referenceIndex"] = reference_index
    catalog["sourceDirectory"] = source_directory
    catalog = annotate_knowledge_catalog_runtime_summaries(catalog)
    atomic_write_json(Path(state["cache"]) / "knowledge-catalog.json", catalog)
    write_reference_export("knowledge-catalog.json", catalog)
    return catalog


def load_cached_knowledge_catalog(state: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    state = state or state_context()
    payload = load_json(Path(state["cache"]) / "knowledge-catalog.json", None)
    if not isinstance(payload, dict):
        return None
    if payload.get("schemaVersion") != KNOWLEDGE_CATALOG_SCHEMA_VERSION:
        return None
    required_sections = (
        "sourceDrift",
        "sourceImpact",
        "topicFreshness",
        "sourceFacts",
        "sourceEvidence",
        "topicDossiers",
        "knowledgeOverview",
        "topicIndex",
        "topicDirectory",
        "referenceIndex",
        "sourceDirectory",
    )
    if any(section not in payload for section in required_sections):
        return None
    return annotate_knowledge_catalog_runtime_summaries(payload)


KNOWLEDGE_QUEUE_PRIORITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}
KNOWLEDGE_PRIORITY_LABELS = {"critical": "最高", "high": "高", "medium": "中", "low": "低"}
KNOWLEDGE_QUEUE_KIND_ORDER = {"source": 0, "topic": 1, "fact": 2, "worknet": 3, "evidence": 4}
KNOWLEDGE_DIRECTORY_FACT_KEYS = {
    "staking-facts": "staking",
    "dao-facts": "dao",
    "testnet-facts": "benchmark-testnet",
    "blog-facts": "blog",
}
KNOWLEDGE_AUTOMATION_LABELS = {
    "full": "适合长期自动运行",
    "supervised": "适合有人盯关键节点时运行",
    "manual-only": "更适合手动观察",
    "partial": "只有部分环节适合自动化",
    "guided": "按步骤引导执行",
}
KNOWLEDGE_RISK_LABELS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
}
KNOWLEDGE_ROLE_LABELS = {
    "operator": "执行者",
    "strategist": "策略研究者",
    "governor": "治理操盘者",
    "observer": "观察者",
    "identity": "身份工具",
    "event-operator": "事件执行者",
}
KNOWLEDGE_WORKNET_STATUS_LABELS = {
    "active": "活跃",
    "public": "公开",
    "discoverable": "已发现",
    "service": "服务型",
}
KNOWLEDGE_SOURCE_KIND_LABELS = {
    "protocol": "协议入口",
    "directory": "目录页",
    "paper": "白皮书",
    "skill": "技能仓库",
    "skill-doc": "技能说明",
    "aip": "AIP 规范",
    "live-api": "实时接口",
    "worknet": "工作网页面",
    "protocol-surface": "协议页面",
    "worknet-surface": "工作网页面",
    "docs": "文档页面",
    "service": "服务页面",
}
KNOWLEDGE_DRIFT_STATUS_LABELS = {
    "content_changed": "内容已变更",
    "changed": "内容已变更",
    "unchanged": "未变化",
    "no-baseline": "缺少基线",
}
KNOWLEDGE_FRESHNESS_STATUS_LABELS = {
    "affected": "待复核",
    "stable": "可直接参考",
}
KNOWLEDGE_FRESHNESS_BUCKET_LABELS = {
    "topic": "主题",
    "fact": "事实",
    "worknet": "工作网",
}
KNOWLEDGE_TRUST_TIER_LABELS = {
    1: "一级官方",
    2: "二级参考",
    3: "低优先参考",
}
KNOWLEDGE_CHANGED_FIELD_LABELS = {
    "sha256": "内容哈希",
    "bytes": "字节大小",
    "status": "HTTP 状态",
    "ok": "抓取可用性",
}
KNOWLEDGE_QUEUE_KIND_LABELS = {
    "source": "来源",
    "topic": "主题",
    "fact": "事实",
    "worknet": "工作网",
    "evidence": "证据",
}


def humanize_knowledge_source_label(text: Any) -> str:
    raw = str(text or "").strip()
    if not raw:
        return raw
    return HUMANIZED_KNOWLEDGE_SOURCE_LABELS.get(raw, HUMANIZED_KNOWLEDGE_SOURCE_LABELS.get(raw.lower(), raw))


def humanize_knowledge_source_kind(kind: Any) -> Optional[str]:
    raw = str(kind or "").strip()
    if not raw:
        return None
    return KNOWLEDGE_SOURCE_KIND_LABELS.get(raw, raw)


def humanize_knowledge_trust_tier(tier: Any) -> Optional[str]:
    try:
        value = int(tier)
    except (TypeError, ValueError):
        return None
    return KNOWLEDGE_TRUST_TIER_LABELS.get(value, str(value))


def humanize_source_changed_field(field: Any) -> str:
    raw = str(field or "").strip()
    if not raw:
        return raw
    return KNOWLEDGE_CHANGED_FIELD_LABELS.get(raw, raw)


def normalized_knowledge_display_key(text: Any) -> str:
    normalized = str(text or "").strip().lower()
    if normalized.startswith("awp "):
        normalized = normalized[4:]
    if normalized.endswith(" worknet"):
        normalized = normalized[:-8]
    return " ".join(normalized.split())


def ranked_knowledge_review_queue_entries(queue: Any, limit: int = 5) -> list[dict[str, Any]]:
    entries = queue.get("entries", []) if isinstance(queue, dict) else []
    ranked: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        ranked.append((index, item))
    ranked.sort(
        key=lambda pair: (
            -KNOWLEDGE_QUEUE_PRIORITY_RANK.get(str(pair[1].get("priority") or "low"), 0),
            KNOWLEDGE_QUEUE_KIND_ORDER.get(str(pair[1].get("kind") or ""), 99),
            pair[0],
        )
    )
    return [item for _, item in ranked[:limit]]


def knowledge_review_queue_recommendation(
    entry: Any,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    entry = entry if isinstance(entry, dict) else {}
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    display_entries = knowledge_display_review_queue_entries([entry], catalog=catalog)
    rendered = display_entries[0] if display_entries else {}
    kind = str(rendered.get("recordKind") or rendered.get("kind") or entry.get("kind") or "").strip()
    label = str(rendered.get("labelDisplay") or rendered.get("label") or entry.get("label") or entry.get("key") or "").strip()
    action_prefix = {
        "source": "重读来源",
        "topic": "重审主题",
        "fact": "复核事实",
        "worknet": "复核 WorkNet 档案",
        "evidence": "复核证据",
    }.get(kind, "检查条目")
    reason = (
        knowledge_highlight_action_description(rendered, action="refresh")
        if isinstance(rendered, dict) and rendered
        else (humanize_knowledge_review_reason(str(entry.get("reason") or "").strip()) or "重新核对这个受影响条目。")
    )
    return {
        "label": f"{action_prefix} {label}",
        "kind": kind,
        "key": entry.get("key"),
        "priority": entry.get("priority"),
        "description": reason,
        "command": rendered.get("primaryCommand") if isinstance(rendered, dict) and rendered.get("primaryCommand") else entry.get("command"),
        "preview": rendered.get("preview") if isinstance(rendered, dict) else None,
        "recordKind": kind,
    }


def knowledge_review_queue_summary_text(summary: Any) -> str:
    summary = summary if isinstance(summary, dict) else {}
    if not summary.get("hasPendingReviews"):
        return "当前本地百科没有待重审条目。"
    text = str(summary.get("headline") or "").strip()
    highest_priority = str(summary.get("highestPriority") or "").strip()
    if highest_priority:
        text += f" 当前最高优先级是{KNOWLEDGE_PRIORITY_LABELS.get(highest_priority, highest_priority)}。"
    focus_sources = [
        humanize_knowledge_source_label(item)
        for item in summary.get("focusSources", [])
        if str(item).strip()
    ]
    focus_topics = [str(item).strip() for item in summary.get("focusTopics", []) if str(item).strip()]
    if focus_sources:
        text += f" 优先来源：{'、'.join(focus_sources[:3])}。"
    if focus_topics:
        text += f" 优先主题：{'、'.join(focus_topics[:3])}。"
    return text.strip()


def knowledge_first_non_empty(*values: object) -> Optional[str]:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def knowledge_freshness_status_display(status: Any) -> Optional[str]:
    return KNOWLEDGE_FRESHNESS_STATUS_LABELS.get(str(status or "").strip())


def knowledge_highlight_group_key(kind: Any) -> str:
    normalized = str(kind or "").strip().lower()
    return {
        "source": "sources",
        "topic": "topics",
        "worknet": "worknets",
        "reference": "references",
        "fact": "facts",
        "evidence": "evidence",
    }.get(normalized, "topics")


def build_knowledge_highlight_entry(
    *,
    kind: str,
    key: Any,
    label: Any,
    headline: Any = None,
    preview: Any = None,
    query_command: Any = None,
    primary_command: Any = None,
    freshness_status: Any = None,
    full_record_key: Any = None,
    research_group: Any = None,
    research_tier: Any = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    normalized_key = str(key or "").strip() or None
    normalized_label = str(label or normalized_key or "").strip() or None
    normalized_preview = compact_preview_text(preview, max_chars=140, max_sentences=2) if preview else None
    normalized_query_command = str(query_command or "").strip() or None
    normalized_primary_command = str(primary_command or "").strip() or None
    normalized_freshness_status = str(freshness_status or "").strip() or None
    record_key = str(full_record_key or normalized_key or "").strip() or None
    normalized_kind = str(kind or "").strip() or None
    normalized_research_group = str(research_group or knowledge_highlight_group_key(kind)).strip() or None
    normalized_research_tier = str(research_tier or "").strip() or None
    payload = {
        "recordKind": normalized_kind,
        "recordKey": record_key,
        "fullRecordKey": record_key,
        "key": normalized_key,
        "label": normalized_label,
        "headline": str(headline or "").strip() or None,
        "preview": normalized_preview,
        "command": normalized_query_command or normalized_primary_command,
        "queryCommand": normalized_query_command,
        "primaryCommand": normalized_primary_command,
        "freshnessStatus": normalized_freshness_status,
        "freshnessStatusDisplay": knowledge_freshness_status_display(normalized_freshness_status),
        "researchGroupKey": normalized_research_group,
        "researchGroupLabel": RESEARCH_HIGHLIGHT_GROUP_LABELS.get(normalized_research_group, normalized_research_group),
        "researchGroupRank": RESEARCH_HIGHLIGHT_GROUP_RANKS.get(normalized_research_group),
        "researchTier": normalized_research_tier,
        "researchTierLabel": RESEARCH_HIGHLIGHT_TIER_LABELS.get(normalized_research_tier, normalized_research_tier),
        "researchTierRank": RESEARCH_HIGHLIGHT_TIER_RANKS.get(normalized_research_tier),
    }
    if isinstance(extra, dict):
        payload.update(extra)
    return payload


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
]

SOURCE_FACT_DISPLAY_FIELDS = [
    "key",
    "topic",
    "summary",
    "facts",
    "sourceKeys",
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


def normalize_review_scope_payload(record: Any) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, REVIEW_SCOPE_FIELDS)


def normalize_query_payload(record: Any, fields: list[str]) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, fields)


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


def build_normalized_knowledge_highlight(
    *,
    kind: str,
    fields: Optional[list[str]] = None,
    key: Any,
    label: Any,
    headline: Any = None,
    preview: Any = None,
    query_command: Any = None,
    primary_command: Any = None,
    freshness_status: Any = None,
    full_record_key: Any = None,
    research_group: Any = None,
    research_tier: Any = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload = build_knowledge_highlight_entry(
        kind=kind,
        key=key,
        label=label,
        headline=headline,
        preview=preview,
        query_command=query_command,
        primary_command=primary_command,
        freshness_status=freshness_status,
        full_record_key=full_record_key,
        research_group=research_group,
        research_tier=research_tier,
        extra=extra,
    )
    normalized_fields = knowledge_highlight_fields(kind, fields)
    return normalize_knowledge_highlight_payload(payload, normalized_fields)


def humanize_knowledge_review_reason(reason: str) -> str:
    text = str(reason or "").strip()
    if not text:
        return text
    if text == "Re-read the affected upstream source and re-check the linked topic dossiers, facts, and runtime guidance.":
        return "重读受影响的上游来源，并重新核对关联主题、事实和运行时指引。"
    return text


def knowledge_display_topic_label(
    topic: str,
    *,
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
) -> str:
    return knowledge_first_non_empty(
        dossier.get("title") if isinstance(dossier, dict) else None,
        worknet.get("name") if isinstance(worknet, dict) else None,
        glossary_match.get("term") if isinstance(glossary_match, dict) else None,
        source_fact.get("topic") if isinstance(source_fact, dict) else None,
        topic,
    ) or topic


def knowledge_topic_worknet_context(
    topic: str,
    *,
    dossier: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    if not isinstance(worknet, dict) or not worknet.get("key"):
        return None
    worknet_key = str(worknet.get("key") or "").strip().lower()
    dossier_key = str(dossier.get("key") or "").strip().lower() if isinstance(dossier, dict) else ""
    if worknet_key == topic or (dossier_key and dossier_key == worknet_key):
        return worknet
    return None


def knowledge_resolved_topic_key(
    topic: str,
    *,
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
) -> str:
    return knowledge_first_non_empty(
        worknet.get("key") if isinstance(worknet, dict) else None,
        dossier.get("key") if isinstance(dossier, dict) else None,
        glossary_match.get("term") if isinstance(glossary_match, dict) else None,
        topic,
    ) or topic


def knowledge_topic_plain_language(
    *,
    narrative: Optional[dict[str, str]],
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
) -> Optional[str]:
    source_facts = source_fact.get("facts", []) if isinstance(source_fact, dict) else []
    return knowledge_first_non_empty(
        narrative.get("plain") if isinstance(narrative, dict) else None,
        glossary_match.get("plainLanguage") if isinstance(glossary_match, dict) else None,
        dossier.get("summary") if isinstance(dossier, dict) else None,
        source_facts[0] if isinstance(source_facts, list) and source_facts else None,
        glossary_match.get("definition") if isinstance(glossary_match, dict) else None,
        worknet.get("goal") if isinstance(worknet, dict) else None,
    )


def knowledge_freshness_affected_items(freshness: Any) -> list[dict[str, Any]]:
    if not isinstance(freshness, dict):
        return []
    items = freshness.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict) and item.get("status") == "affected"]


def knowledge_topic_headline(label: str, freshness: Any) -> str:
    if knowledge_freshness_affected_items(freshness):
        return f"{label} 当前有上游变更待复核。"
    return f"{label} 当前资料可直接参考。"


def knowledge_topic_summary(
    label: str,
    *,
    narrative: Optional[dict[str, str]],
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
    freshness: Any,
) -> str:
    parts: list[str] = []
    plain = knowledge_topic_plain_language(
        narrative=narrative,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet,
    )
    if plain:
        parts.append(plain)
    why_it_matters = knowledge_first_non_empty(
        narrative.get("why") if isinstance(narrative, dict) else None,
        glossary_match.get("whyItMatters") if isinstance(glossary_match, dict) else None,
        dossier.get("whyItExists") if isinstance(dossier, dict) else None,
    )
    if why_it_matters:
        parts.append(why_it_matters)
    if isinstance(worknet, dict) and worknet:
        automation = KNOWLEDGE_AUTOMATION_LABELS.get(str(worknet.get("automationLevel") or "").strip())
        risk = KNOWLEDGE_RISK_LABELS.get(str(worknet.get("riskLevel") or "").strip())
        loop_text = knowledge_first_non_empty(
            narrative.get("loop") if isinstance(narrative, dict) else None,
            (f"默认节奏是 {worknet.get('loop')}。" if knowledge_first_non_empty(worknet.get("loop")) else None),
        )
        posture = None
        if automation and risk:
            posture = f"这个 WorkNet 目前{automation}，整体属于{risk}。"
        elif automation:
            posture = f"这个 WorkNet 目前{automation}。"
        elif risk:
            posture = f"这个 WorkNet 当前属于{risk}。"
        parts.extend([item for item in (loop_text, posture) if item])
    affected = knowledge_freshness_affected_items(freshness)
    if affected:
        affected_labels: list[str] = []
        seen_labels: set[str] = set()
        source_names: list[str] = []
        seen_sources: set[str] = set()
        for item in affected:
            label_text = str(item.get("label") or item.get("key") or "").strip()
            normalized_label = normalized_knowledge_display_key(label_text)
            if label_text and normalized_label and normalized_label not in seen_labels:
                seen_labels.add(normalized_label)
                affected_labels.append(label_text)
            for impact in item.get("impactItems", []):
                if not isinstance(impact, dict):
                    continue
                source_name = humanize_knowledge_source_label(impact.get("sourceName") or impact.get("sourceKey"))
                normalized_source = normalized_knowledge_display_key(source_name)
                if source_name and normalized_source and normalized_source not in seen_sources:
                    seen_sources.add(normalized_source)
                    source_names.append(source_name)
        detail = f"当前这条知识要连同 {'、'.join(affected_labels[:3])} 一起复核。"
        if source_names:
            detail += f" 直接触发它的上游来源是 {'、'.join(source_names[:3])}。"
        parts.append(detail)
    else:
        parts.append("当前没有发现直接影响这条知识的上游变更。")
    caution = knowledge_first_non_empty(narrative.get("caution") if isinstance(narrative, dict) else None)
    if caution:
        parts.append(caution)
    return humanize_knowledge_display_text(" ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())) or ""


def knowledge_topic_citations(
    evidence_matches: list[dict[str, Any]],
    *,
    source_records: dict[str, dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in evidence_matches[:limit]:
        if not isinstance(item, dict):
            continue
        source_key = str(item.get("sourceKey") or "").strip()
        claim = str(item.get("claim") or "").strip()
        key = (source_key, claim)
        if not source_key or not claim or key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "sourceKey": source_key,
                "sourceName": item.get("sourceName"),
                "url": item.get("sourceUrl"),
                "locator": item.get("locator"),
                "claim": claim,
                "evidenceType": item.get("evidenceType"),
                "stability": item.get("stability"),
            }
        )
    if citations:
        return citations
    if isinstance(dossier, dict):
        for source_key in dossier.get("sourceKeys", [])[:limit]:
            source_record = source_records.get(str(source_key), {})
            citations.append(
                {
                    "sourceKey": source_key,
                    "sourceName": source_record.get("name"),
                    "url": source_record.get("url"),
                    "locator": None,
                    "claim": None,
                    "evidenceType": source_record.get("kind"),
                    "stability": None,
                }
            )
    return citations


KNOWLEDGE_EVIDENCE_TYPE_LABELS = {
    "normative-overview": "规范总览",
    "runtime-doc": "运行时说明",
    "runtime-inspection": "本地运行检查",
    "aip": "AIP",
    "skill-doc": "技能说明",
    "live-api": "实时接口",
    "protocol-surface": "协议页面",
    "skill-uri": "技能来源",
    "docs-surface": "文档页面",
}
KNOWLEDGE_STABILITY_LABELS = {
    "high": "高稳定",
    "medium": "中稳定",
    "low": "低稳定",
}
KNOWLEDGE_DOSSIER_DISPLAY_OVERRIDES: dict[str, dict[str, Any]] = {
    "protocol-core": {
        "summary": "AWP 是双层 agent 工作网络，RootNet 负责总控，WorkNet 负责具体任务执行。",
        "whyItExists": "它给 agent 一个可以长期找任务、拿收益和协作的总网络。",
        "operatorLoop": [
            "准备独立的 agent 工作钱包。",
            "在 RootNet 上完成注册或确认 agent 已就绪。",
            "扫描实时或缓存的 WorkNet 机会。",
            "选一条安全的工作路线，并把收益路由到已经确认过的收款地址。",
        ],
        "economics": [
            "AWP 是协议里的储备、质押和治理资产。",
            "各 WorkNet 会发行自己的工作代币，也可能同时分发 AWP。",
            "AWP Power 来自质押，会影响治理权和某些工作优先级。",
        ],
        "risks": [
            "收款地址配错会把收益发到错误地址。",
            "质押和分配会移动价值，必须先确认。",
            "上游 skill 变化不能直接改写工作站的默认行为。",
        ],
    },
    "awp-skill": {
        "summary": "awp-skill 是官方 RootNet 依赖层，负责注册、质押、分配、治理和协议实时读取。",
        "whyItExists": "它让工作站能把协议动作委托给官方运行层，而不是自己手拼合约调用。",
        "operatorLoop": [
            "安装 awp-skill 和 awp-wallet。",
            "初始化 agent 工作钱包，而且不向用户索要私密信息。",
            "用 awp-skill 处理 RootNet 注册和生命周期动作。",
        ],
        "economics": [
            "绑定关系、设置收款地址和 WorkNet 注册都支持免 gas 中继路径。",
        ],
        "risks": [
            "如果某个子 skill 一上来就要求私钥或助记词，要直接视为高风险。",
            "工作站应该把 awp-skill 当依赖层，而不是暴露给用户的产品主界面。",
        ],
    },
    "mine": {
        "summary": "Mine 是无需许可的数据工作网，重点是抓取、清洗、抽取并提交结构化网页数据。",
        "whyItExists": "它把 agent 的网页采集能力直接变成有代币结算的结构化数据生产。",
        "operatorLoop": [
            "发现网址和数据集入口。",
            "抓取原始网页。",
            "清洗成可处理文本。",
            "抽出符合结构的记录。",
            "提交结果并维持保活，直到结算。",
        ],
        "economics": [
            "$aMine 运行在 Base，上线后按 WorkNet 节奏排放。",
            "矿工通常不需要先质押，验证者需要。",
            "在启动阶段，Mine 也会和 $aMine 一起分发 AWP。",
        ],
        "risks": [
            "质量门槛会在结算前拒掉低质量提交。",
            "共享 IP 衰减会压缩吞吐。",
            "重复抓取和伪造数据会被系统惩罚。",
        ],
    },
    "predict": {
        "summary": "Predict 是推理型预测工作网，理由质量本身就是产品的一部分。",
        "whyItExists": "它让 agent 用方向判断和研究能力直接竞争收益。",
        "operatorLoop": [
            "读取市场上下文和候选时间窗。",
            "形成有原创性的方向判断。",
            "通过官方运行时提交预测或委托。",
            "跟踪结算结果和 alpha 质量。",
        ],
        "economics": [
            "Predict 用虚拟筹码启动，每四小时有一次筹码补给。",
            "排放拆成 owner、participation 和 alpha 三部分。",
            "流动性主要在 Base 上围绕 AWP 展开。",
        ],
        "risks": [
            "重复 reasoning 会直接触发质量门槛。",
            "市场窗口短，所以频率和 rate limit 管理很关键。",
            "本地官方运行时如果没就绪，就不能假装它已经可无人值守运行。",
        ],
    },
    "gov": {
        "summary": "GovNet 是每周结算的治理/交易型工作网，围绕市场、投票、筹码和结算运行。",
        "whyItExists": "它把对 WorkNet 价值和排放预期的判断变成可执行的 agent 行动。",
        "operatorLoop": [
            "列市场并观察当前阶段。",
            "读取当前主体状态和筹码余额。",
            "只在确认后才投票或下单。",
            "跟踪成交和结算结果。",
        ],
        "economics": [
            "筹码和 worknet share 共同表达每周价值判断。",
            "所有签名读写都会经由 EMG-SIG-V1 和 awp-wallet 确认当前主体身份。",
        ],
        "risks": [
            "阶段时间判断错了，整条计划就可能失效。",
            "部分端点可能存在文档和服务端漂移。",
            "所有签名写入都必须先进确认队列。",
        ],
    },
    "ardi": {
        "summary": "Ardi 是只允许 agent 执行的谜题工作网，围绕承诺、揭示和铭刻展开。",
        "whyItExists": "它把语言谜题推理转成链上铭刻游戏。",
        "operatorLoop": [
            "先跑 ardi-agent 预检。",
            "严格跟随 `_internal.next_command`。",
            "提交高置信答案承诺。",
            "到揭示阶段再揭示并铭刻。",
        ],
        "economics": [
            "需要 Base 手续费，以及 Ardi 质押或 KYA 委托路径。",
            "每日 ARDI 排放会累积到持有的 Ardinals，需要后续领取。",
        ],
        "risks": [
            "如果 auto-mine 已存在，就不该再手写 shell 循环顶上去。",
            "结算阶段和揭示窗口都很严格。",
            "保证金和手续费管理本身就是运行风险。",
        ],
    },
    "kya": {
        "summary": "KYA 是身份和委托质押服务层，负责身份验证、收款地址路由和社交/人工校验。",
        "whyItExists": "它补齐 agent 背后的身份或社交信任层，并打开委托质押路径。",
        "operatorLoop": [
            "检查现有身份验证状态。",
            "如果预检要求注册，就先交回 awp-skill 完成免 gas 注册。",
            "执行身份验证或 KYC 流程。",
            "只有确认后才设置收款地址或授予委托权限。",
        ],
        "economics": [
            "对某些路径来说，委托质押可以替代直接持有和质押 AWP。",
        ],
        "risks": [
            "magic-link 和交接 URL 在非 TTY 环境里必须明文输出。",
            "它是事件型服务，不应该被当成长期后台循环。",
        ],
    },
    "tmr": {
        "summary": "TMR 是已激活的官方 WorkNet，但当前公开操作说明仍然偏薄。",
        "whyItExists": "即使运行细节还不完整，工作站也应该先把它作为官方已发现 WorkNet 暴露出来。",
        "operatorLoop": [
            "先确认实时 WorkNet ID 和官方技能仓库地址。",
            "执行前先安装或检查官方 skill。",
            "在本地运行时核验前，先把任务语义当作未知。",
        ],
        "economics": [
            "当前公开实时查询显示它的最低质押提示是 0。",
        ],
        "risks": [
            "公开任务说明仍然稀薄。",
            "在本地 skill 没审过前，workstation 不该自动跑 TMR。",
        ],
    },
    "community": {
        "summary": "Community 是已激活的官方 WorkNet，但当前公开操作说明仍然偏薄。",
        "whyItExists": "它让工作站能在不假装理解完整任务闭环的前提下，仍把官方 Community 路径暴露出来。",
        "operatorLoop": [
            "先确认实时 WorkNet ID 和官方技能仓库地址。",
            "执行前先安装或检查官方 skill。",
            "在本地运行时说明补齐前，只按受监督的方式对待这条工作流。",
        ],
        "economics": [
            "当前公开实时查询显示它的最低质押提示是 0。",
        ],
        "risks": [
            "公开任务说明仍然稀薄。",
            "在本地 skill 没审过前，workstation 不该自动跑 Community。",
        ],
    },
    "staking": {
        "summary": "AWP 质押会把 AWP 锁成 veAWP，并进一步形成 AWP Power。",
        "whyItExists": "它把锁仓 AWP 变成治理权和资格权重。",
        "operatorLoop": [
            "先判断目标 WorkNet 是否真的需要质押。",
            "估算锁仓数量和时长。",
            "执行前单独确认质押动作。",
            "跟踪 veAWP 状态，以及它对下游资格的影响。",
        ],
        "economics": [
            "AWP Power 会随着数量和剩余锁仓时长一起变化。",
            "某些 WorkNet 会拿 AWP Power 做资格或优先级判断。",
        ],
        "risks": [
            "锁仓时长会影响流动性，不能被淡化成普通点击动作。",
            "质押永远是价值移动动作，必须先确认。",
        ],
    },
    "dao": {
        "summary": "DAO 是协议治理面，围绕提案、投票和 signal 行动展开，权重由 AWP Power 决定。",
        "whyItExists": "它让网络能通过 veAWP 投票去调整协议参数和资金方向。",
        "operatorLoop": [
            "读取当前提案和阶段。",
            "判断这是链上投票还是免 gas signal。",
            "所有需要签名的治理动作都单独确认。",
        ],
        "economics": [
            "公开页面显示提案门槛是 200K AWP。",
            "法定人数和时间窗口都是操作约束，不只是背景信息。",
        ],
        "risks": [
            "治理动作可能影响协议层面的价值流。",
            "即使不是市场操作，阶段时间也依然关键。",
        ],
    },
    "benchmark-testnet": {
        "summary": "Benchmark Testnet 是测试网上的任务工作网，适合提问、解题和做公开 benchmark。",
        "whyItExists": "它提供一个低风险的练手机会，方便 agent 上手工作流。",
        "operatorLoop": [
            "安装 awp-skill。",
            "让 agent 自动创建钱包并免 gas 注册。",
            "发现 Benchmark WorkNet 并开始提问或答题。",
        ],
        "economics": [
            "公开测试网代币是 $aBench。",
        ],
        "risks": [
            "测试网行为不能被误当成主网收益。",
        ],
    },
    "blog": {
        "summary": "官方博客是面向产品和上手的说明面，用更直白的话解释 WorkNet 和 onboarding。",
        "whyItExists": "它补足了规格文档之外的产品语气和 onboarding 叙事。",
        "operatorLoop": [
            "用博客把协议细节翻译成更容易理解的说明。",
            "当官方博客明显改变上手假设时，同步更新派生知识。",
        ],
        "economics": [
            "博客不会定义共识规则，但会影响产品默认引导语气。",
        ],
        "risks": [
            "编辑型文档通常比规范文档漂移得更快。",
        ],
    },
}
KNOWLEDGE_SOURCE_FACT_DISPLAY_OVERRIDES: dict[str, list[str]] = {
    "protocol-core": [
        "AWP 是去中心化的 agent 工作协议，由 RootNet 和任务型 WorkNet 共同组成。",
        "当前主网重点链路包括 Base、Ethereum、Arbitrum 和 BSC。",
        "公开协议入口主要是 `POST https://api.awp.sh/v2`、`wss://api.awp.sh/ws/live` 和 `GET https://api.awp.sh/api/health`。",
        "收款地址路由很关键，因为 agent 的收益会打到当前配置的收款地址。",
    ],
    "awp-skill-ops": [
        "官方 RootNet skill 是处理注册、质押、分配、治理和 WorkNet 管理的依赖层。",
        "官方安装路径是先装 awp-skill，再装 awp-wallet，并把 awp-wallet 放进 PATH。",
        "官方引导明确说过，初始化钱包时不该向用户索要密码、私钥或助记词。",
    ],
    "mine-aip": [
        "Mine 是首个 AWP 数据工作网，负责抓取、清洗并抽取结构化网页数据。",
        "Mine 跑在 Base 上，用 $aMine 结算，按日 UTC 周期运转。",
        "矿工通常不需要先质押，但验证者需要满足最低质押要求。",
        "标准流程是抓取、清洗、抽取、提交，然后参与结算和质量门槛判定。",
    ],
    "predict-aip": [
        "Predict 是 AI 原生预测工作网，预测结论和 reasoning 会一起进入市场。",
        "它使用虚拟筹码和四小时补给节奏，所以可以先不买代币就开始参与。",
        "Predict 按日 UTC 周期运行，奖励拆成 owner、participation 和 alpha 三部分。",
        "reasoning 本身属于产品质量的一部分，所以去重和频率控制非常关键。",
    ],
    "predict-skill-facts": [
        "截至 2026-05-20，官方实时接口把 Predict 映射到 Base 上的 `845300000003`，官方 skill 来源是 `https://github.com/awp-worknet/prediction-skill`。",
        "官方 Predict 运行时要求所有正式操作都通过 `predict-agent` 执行，而不是直接手调 API。",
        "官方说明显示它要求在 `845300000003` 上具备 `1000 AWP` 分配资格，或者走 KYA 委托质押路径。",
    ],
    "gov-skill-facts": [
        "GovNet 提供市场列表、下单、投票、筹码拆分/合并、订单簿观察和结算读取。",
        "公开读取不需要钱包，但所有签名读取和写入都会通过 awp-wallet 确认当前主体身份。",
        "官方文档同时给出 `api.gov.works` 下的 REST 和 WebSocket 入口。",
        "因为签名状态变更要走 EIP-712 和 awp-wallet，所以交易、投票和其他不可逆动作都必须先进确认队列。",
    ],
    "ardi-skill-facts": [
        "所有 Ardi 链上动作都必须通过 `ardi-agent` 执行，不能自己手写 calldata 或脚本顶上去。",
        "Ardi 有严格的运行上限，比如每个周期最多 5 次 commit，总铭刻上限 21,000。",
    ],
    "kya-skill-facts": [
        "KYA 更像一次性的身份和委托工具，不是长期后台守护进程。",
        "KYA 要求 agent 先完成 AWP 注册；如果还没注册，就先交给 awp-skill 完成免 gas 注册。",
        "KYA 的 magic-link 和交接 URL 在非 TTY 环境里必须明文输出，不能假设用户就在交互式浏览器里。",
        "默认配置会连接 kya.link、api.awp.sh 和 Base 主网 RPC 来确认注册状态。",
    ],
    "tmr": [
        "截至 2026-05-20，官方实时接口把 TMR 映射到 Base 上的 `845300000013`，对应的官方技能仓库地址是 `https://github.com/awp-worknet/tmr-skill`。",
        "由于公开操作说明仍然偏薄，工作站目前只把它当作已发现、但不适合无人值守自动运行的 WorkNet。",
    ],
    "community": [
        "截至 2026-05-20，官方实时接口把 Community 映射到 Base 上的 `845300000011`，对应的官方技能仓库地址是 `https://github.com/awp-worknet/com-skill`。",
        "因为公开操作说明仍然偏薄，工作站目前只把它当作已发现、但不适合无人值守自动运行的 WorkNet。",
    ],
    "staking-facts": [
        "锁定 AWP 会铸造 veAWP，并生成与数量和剩余锁仓时长相关的 AWP Power。",
        "AWP Power 会影响治理权重，也会影响某些 WorkNet 的资格或优先级。",
    ],
    "dao-facts": [
        "公开 DAO 页面当前显示 4% quorum、8 小时投票延迟、24 小时投票期，以及 200K AWP 提案门槛。",
    ],
    "testnet-facts": [
        "公开测试网代币是 `$aBench`。",
        "加入 Benchmark Testnet 的典型路径是安装 awp-skill，由它自动建钱包并免 gas 注册。",
        "测试网公开面包含空投检查、agent 活跃度检查和 benchmark 排行榜。",
    ],
    "blog-facts": [
        "官方博客会持续发布 onboarding 和 WorkNet 概念说明。",
        "当前公开文章序列覆盖了启动 WorkNet、什么是 AWP、如何快速让 agent 开始赚钱，以及什么是 WorkNet 等主题。",
    ],
}
KNOWLEDGE_EVIDENCE_DISPLAY_OVERRIDES: dict[str, dict[str, str]] = {
    "protocol-two-layer": {"claim": "AWP 采用双层结构：RootNet 做总协调，WorkNet 执行具体任务经济。", "rationale": "白皮书正式定义了 RootNet 和 WorkNet 的架构分工。"},
    "protocol-endpoints": {"claim": "官方 RootNet skill 把 `POST https://api.awp.sh/v2`、`wss://api.awp.sh/ws/live` 和 `GET https://api.awp.sh/api/health` 作为公开协议入口。", "rationale": "工作站应该直接沿用官方公开的协议入口，而不是自己编造端点。"},
    "awp-skill-install-sequence": {"claim": "官方上手顺序是先装 awp-skill，再装 awp-wallet，并确认 awp-wallet 在 PATH 中，最后初始化新的工作钱包。", "rationale": "这条顺序决定了工作站应该怎样解释上手流程。"},
    "awp-skill-gasless-ops": {"claim": "官方 RootNet skill 明确支持免 gas 的绑定、设置收款地址和 WorkNet 注册中继流程。", "rationale": "这些能力决定了工作站可以在不要求原生 gas 的前提下，先规划注册、绑定和收款地址动作。"},
    "mine-worknet-summary": {"claim": "Mine 是首个 AWP 数据工作网，负责无需许可的网页数据抓取、清洗和结构化抽取。", "rationale": "这是定义 Mine 工作本体的规范来源。"},
    "mine-emission-and-stake": {"claim": "Mine 运行在 Base 上，用 `$aMine` 结算，按日 UTC 周期运行；矿工通常不需要先质押，验证者需要。", "rationale": "这些信息决定 workstation 能不能把 Mine 推荐给新用户。"},
    "predict-worknet-summary": {"claim": "Predict 是 AI 原生预测工作网，预测结论和 reasoning 都会进入市场。", "rationale": "这解释了为什么 reasoning 质量本身就是运行维度。"},
    "predict-virtual-chips": {"claim": "Predict 使用虚拟筹码和周期性补给，所以可以先不买代币就开始参与。", "rationale": "这支撑了 workstation 优先推荐低门槛上手路径的默认策略。"},
    "predict-official-runtime": {"claim": "截至 2026-05-20，官方实时接口把 Predict 映射到 Base 上的 `845300000003`，官方 skill 要求通过 `predict-agent` 执行。", "rationale": "这条证据修正了“Predict 还没有明确官方运行时”的旧假设。"},
    "live-canonical-base-worknets": {"claim": "截至 2026-05-20，官方实时接口把 Base 上的 Mine、Predict、Gov、Community、KYA、TMR 和 Ardi 分别映射到 `845300000002`、`845300000003`、`845300000010`、`845300000011`、`845300000012`、`845300000013` 和 `845300000014`。", "rationale": "当列表、搜索和旧资料发生漂移时，工作站应该先以这份实时映射为准。"},
    "gov-public-vs-signed": {"claim": "GovNet 的公开读取不需要钱包，但所有签名读取和写入都会通过 awp-wallet 确认当前主体身份。", "rationale": "这就是工作站能先开放安全只读检查、却必须把签名动作放进确认队列的原因。"},
    "gov-auth-discipline": {"claim": "Gov skill 对域名不匹配、nonce 漂移和本地时间偏差这类错误有统一的重试和失败处理纪律。", "rationale": "工作站应该把这类情况当作运行状态，而不是让用户自己猜哪里出了问题。"},
    "ardi-agent-only": {"claim": "Ardi 要求所有链上动作都通过 `ardi-agent` 执行，并明确反对自己手写 loop 脚本替代官方路径。", "rationale": "这证明了 workstation 在 Ardi 上必须严格跟随官方 next-command 日志。"},
    "ardi-operational-caps": {"claim": "Ardi 有严格运行上限，比如每个周期最多 5 次 commit，总铭刻上限 21,000。", "rationale": "这些上限会直接影响自动化是否安全。"},
    "kya-registration-handoff": {"claim": "KYA 要求先完成 AWP 注册；如果 agent 还没注册，就先交给 awp-skill 做免 gas 注册再继续。", "rationale": "这就是工作站把 KYA 视作身份与委托服务工具、而不是注册替代品的原因。"},
    "kya-handoff-url-plain-text": {"claim": "KYA 的 magic-link 和交接流程在非 TTY 环境里必须输出明文 URL。", "rationale": "工作站在聊天界面翻译动作时，也必须保留这种行为。"},
    "staking-awp-power": {"claim": "锁定 AWP 会铸造 veAWP，并生成与数量和锁仓时长相关的 AWP Power。", "rationale": "这是对用户最重要的质押经济学摘要。"},
    "dao-public-params": {"claim": "公开 DAO 页面当前显示 4% quorum、8 小时投票延迟、24 小时投票期，以及 200K AWP 提案门槛。", "rationale": "这些公开参数会直接影响 workstation 对治理时机的解释。"},
    "testnet-gasless-start": {"claim": "公开 Benchmark Testnet 页面说明：awp-skill 会先自动建钱包并免 gas 注册，再去发现测试网 WorkNet。", "rationale": "这是官方公开的 agent-first onboarding 样例。"},
    "tmr-live-skill-uri": {"claim": "截至 2026-05-20，官方实时接口把 TMR 映射到 Base 上的 `845300000013`，对应的官方技能仓库地址是 `https://github.com/awp-worknet/tmr-skill`，但公开操作说明仍然偏薄。", "rationale": "这就是工作站只把 TMR 暴露为可发现、但不自动运行的根本原因。"},
    "community-live-skill-uri": {"claim": "截至 2026-05-20，官方实时接口把 Community 映射到 Base 上的 `845300000011`，对应的官方技能仓库地址是 `https://github.com/awp-worknet/com-skill`，但公开操作说明仍然偏薄。", "rationale": "这就是工作站只把 Community 暴露为可发现、但不自动运行的根本原因。"},
    "blog-operator-guides": {"claim": "官方博客属于文档面的一部分，目前持续提供 onboarding 和 WorkNet 概念说明。", "rationale": "它适合拿来补产品语气，但规范性低于 AIP 和官方 skill 文档。"},
}


def humanize_knowledge_locator(text: Any) -> Optional[str]:
    raw = str(text or "").strip()
    if not raw:
        return None
    lowered = raw.lower()
    if "scripts/preflight.py" in lowered:
        return "本地运行检查：检查 AWP RootNet 预检"
    if "scripts/query-status.py" in lowered:
        return "本地运行检查：查看 AWP RootNet 当前状态"
    if "scripts/query-worknet.py" in lowered:
        return "本地运行检查：查看 AWP RootNet WorkNet 信息"
    if "scripts/run_tool.py agent-control status" in lowered:
        return "本地运行检查：查看 Mine 控制状态"
    if "scripts/run_tool.py agent-status" in lowered:
        return "本地运行检查：查看 Mine 运行状态"
    if "scripts/run_tool.py doctor" in lowered:
        return "本地运行检查：运行 Mine 诊断"
    if "scripts/run_tool.py agent-start" in lowered:
        return "本地运行检查：开始 Mine 采集"
    if "bootstrap.sh" in lowered:
        return "本地运行检查：重新初始化 Mine 运行环境"
    mapping = {
        "whitepaper abstract and definitions": "白皮书摘要与定义部分",
        "README endpoint section": "README 端点说明部分",
        "README installation and quickstart": "README 安装与快速开始部分",
        "README gasless support table": "README 免 gas 支持表",
        "AIP-001 abstract and motivation": "AIP-001 摘要与动机部分",
        "AIP-001 terminology, token, and role sections": "AIP-001 术语、代币和角色部分",
        "AIP-002 abstract and worknet page summary": "AIP-002 摘要与 WorkNet 说明部分",
        "AIP-002 chip economy and participation design": "AIP-002 筹码经济与参与机制部分",
        "SKILL.md quick start, stake requirement, and install sections": "SKILL.md 快速开始、质押要求与安装部分",
        "worknets.get + worknets.getSkills live snapshots captured by workstation on 2026-05-20": "工作站在 2026-05-20 抓到的 `worknets.get` 与 `worknets.getSkills` 实时快照",
        "SKILL.md read vs signed section": "SKILL.md 公开读取与签名动作部分",
        "SKILL.md error handling discipline": "SKILL.md 错误处理纪律部分",
        "SKILL.md agent-only and auto-mine guidance": "SKILL.md agent-only 与 auto-mine 指引部分",
        "SKILL.md limits and constraints": "SKILL.md 限制与约束部分",
        "SKILL.md prerequisites and handoff text": "SKILL.md 前置条件与交接说明部分",
        "SKILL.md messaging and non-TTY guidance": "SKILL.md 消息与非 TTY 指引部分",
        "staking page main description": "staking 页面主说明",
        "DAO page governance summary line": "DAO 页面治理摘要行",
        "testnet join section": "testnet 加入说明部分",
        "official live skill URI returned by AWP plus repository landing page": "AWP 返回的官方 skill URI 与仓库入口页",
        "blog index visible article list": "博客索引页当前可见文章列表",
    }
    return mapping.get(raw, raw)


def humanize_runtime_probe_check_label(
    label: Any,
    *,
    command: Any = None,
    skill_key: Any = None,
) -> Optional[str]:
    command_text = str(command or "").strip()
    lowered_command = command_text.lower()
    text = str(label or "").strip()
    mapped = humanize_playbook_command_label(text)
    if mapped != text:
        return mapped
    label_prefix = text.lower().split(" ", 1)[0] if text else ""
    explicit_label_skill = ""
    if label_prefix in {"awp-skill", "awp-wallet"}:
        explicit_label_skill = label_prefix
    elif label_prefix and isinstance(resolve_worknet(label_prefix), dict):
        explicit_label_skill = label_prefix
    if not explicit_label_skill:
        if "scripts/preflight.py" in lowered_command or "scripts/query-status.py" in lowered_command or "scripts/query-worknet.py" in lowered_command:
            explicit_label_skill = "awp-skill"
    resolved_skill_key = (
        str(skill_key or "").strip().lower()
        or explicit_label_skill
        or runtime_guidance_worknet_key(
            None,
            labels=[text] if text else None,
            action_map={"_": lowered_command} if lowered_command else None,
        )
    )
    worknet_name = runtime_guidance_worknet_name(resolved_skill_key) if resolved_skill_key else "当前"
    lowered_text = text.lower()
    if lowered_text:
        if "query worknet" in lowered_text:
            return "查看 AWP RootNet WorkNet 信息" if resolved_skill_key == "awp-skill" else f"查看 {worknet_name} WorkNet 信息"
        if lowered_text.endswith(" preflight"):
            return "检查 AWP RootNet 预检" if resolved_skill_key == "awp-skill" else f"检查 {worknet_name} 预检"
        if lowered_text.endswith(" readiness"):
            return f"检查 {worknet_name} 就绪状态" if worknet_name != "当前" else "检查当前就绪状态"
        if lowered_text.endswith(" control status"):
            return f"查看 {worknet_name} 控制状态" if worknet_name != "当前" else "查看当前控制状态"
        if lowered_text.endswith(" agent status"):
            return f"查看 {worknet_name} 运行状态" if worknet_name != "当前" else "查看当前运行状态"
        if lowered_text.endswith(" status"):
            return f"查看 {worknet_name} 当前状态" if worknet_name != "当前" else "查看当前状态"
    resolved_skill_key = runtime_guidance_worknet_key(
        resolved_skill_key or None,
        labels=[text] if text else None,
        action_map={"_": lowered_command} if lowered_command else None,
    ) or resolved_skill_key
    if resolved_skill_key == "predict":
        if "predict-agent preflight" in lowered_command:
            return "重跑 Predict 预检"
        if "predict-agent status" in lowered_command:
            return "查看 Predict 运行状态"
        if "predict-agent stake" in lowered_command:
            return "检查 Predict 资格路径"
        if "predict-agent context" in lowered_command:
            return "拉取 Predict 上下文"
    if resolved_skill_key == "ardi":
        if "ardi-agent preflight" in lowered_command:
            return "重跑 Ardi 预检"
        if "ardi-agent status" in lowered_command:
            return "查看 Ardi 运行状态"
        if "ardi-agent gas" in lowered_command:
            return "检查 Ardi 手续费"
        if "ardi-agent stake" in lowered_command:
            return "检查 Ardi 资格路径"
    if resolved_skill_key == "gov":
        if "scripts/public/markets.py" in lowered_command:
            return "查看 Gov 公开市场"
        if "scripts/helpers/what-can-i-do.py" in lowered_command:
            return "查看 Gov 当前阶段"
        if "scripts/private/state.py" in lowered_command:
            return "查看 Gov 私有状态"
    if text:
        return (
            humanize_runtime_guidance_action_label(resolved_skill_key or None, text, command=command_text)
            or humanize_executed_step_label(text, category="inspect", execution_policy="probe")
            or text
        )
    if "scripts/preflight.py" in lowered_command:
        return "检查 AWP RootNet 预检"
    if "scripts/query-status.py" in lowered_command:
        return "查看 AWP RootNet 当前状态"
    if "scripts/query-worknet.py" in lowered_command:
        return "查看 AWP RootNet WorkNet 信息"
    if "scripts/run_tool.py agent-control status" in lowered_command:
        return "查看 Mine 控制状态"
    if "scripts/run_tool.py agent-status" in lowered_command:
        return "查看 Mine 运行状态"
    if "scripts/run_tool.py doctor" in lowered_command:
        return "运行 Mine 诊断"
    if "scripts/run_tool.py agent-start" in lowered_command:
        return "开始 Mine 采集"
    if "bootstrap.sh" in lowered_command:
        return "重新初始化 Mine 运行环境"
    return None


def humanize_runtime_probe_locator_display(
    label: Any,
    *,
    command: Any = None,
    skill_key: Any = None,
) -> Optional[str]:
    check_label = humanize_runtime_probe_check_label(
        label,
        command=command,
        skill_key=skill_key,
    )
    if check_label:
        return f"本地运行检查：{check_label}"
    command_text = str(command or "").strip()
    if command_text:
        generic = humanize_knowledge_locator(command_text)
        if generic and generic != command_text:
            return generic
    return "本地运行检查命令" if command_text else None


KNOWLEDGE_DISPLAY_TEXT_REPLACEMENTS: list[tuple[str, str]] = [
    ("live skill URI", "实时技能来源地址"),
    ("skill URI", "技能来源地址"),
    ("recipient routing", "收款地址路由"),
    ("recipient address", "收款地址"),
    ("reward recipient", "收益收款地址"),
    ("resolved recipient", "已解析的收款地址"),
    ("Set Recipient", "设置收款地址"),
    ("set recipient", "设置收款地址"),
    ("recipient", "收款地址"),
    ("principal state", "主体状态"),
    ("principal identity", "主体身份"),
    ("principal", "主体"),
    ("delegated staking", "委托质押"),
    ("grant delegate", "授予委托权限"),
    ("grant-delegate", "授予委托权限"),
    ("授予 delegate", "授予委托权限"),
    ("delegate", "委托权限"),
    ("attestation", "身份证明"),
    ("Workstation", "工作站"),
    ("workstation", "工作站"),
    ("Onboarding", "上手流程"),
    ("onboarding", "上手流程"),
    ("Handoff", "交接"),
    ("handoff", "交接"),
    ("runtime", "运行环境"),
    ("market context", "市场上下文"),
]


def humanize_knowledge_display_text(text: Any) -> Optional[str]:
    raw = str(text or "").strip()
    if not raw:
        return None
    rendered = raw
    for old, new in KNOWLEDGE_DISPLAY_TEXT_REPLACEMENTS:
        rendered = rendered.replace(old, new)
    rendered = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", rendered)
    rendered = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[，。；：！？、）】》])", "", rendered)
    rendered = re.sub(r"(?<=[（【《])\s+(?=[\u4e00-\u9fff])", "", rendered)
    rendered = rendered.replace("收款地址 地址", "收款地址")
    rendered = rendered.replace("收款地址  ", "收款地址 ")
    rendered = rendered.replace("  ", " ")
    return rendered


def humanize_knowledge_display_list(items: Any) -> list[str]:
    rendered: list[str] = []
    for item in items if isinstance(items, list) else []:
        text = humanize_knowledge_display_text(item)
        if text:
            rendered.append(text)
    return rendered


def knowledge_display_dossier(
    dossier: Any,
    *,
    summary: Optional[str] = None,
    why: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(dossier, dict):
        return None
    key = str(dossier.get("key") or "").strip().lower()
    override = KNOWLEDGE_DOSSIER_DISPLAY_OVERRIDES.get(key, {})
    return normalize_dossier_payload({
        "key": dossier.get("key"),
        "kind": dossier.get("kind"),
        "title": dossier.get("title"),
        "summary": humanize_knowledge_display_text(override.get("summary") or summary or dossier.get("summary")),
        "defaultEntrypoint": dossier.get("defaultEntrypoint"),
        "whyItExists": humanize_knowledge_display_text(override.get("whyItExists") or why or dossier.get("whyItExists")),
        "operatorLoop": humanize_knowledge_display_list(override.get("operatorLoop") or []),
        "economics": humanize_knowledge_display_list(override.get("economics") or []),
        "risks": humanize_knowledge_display_list(override.get("risks") or []),
        "sourceKeys": dossier.get("sourceKeys", []),
        "officialUrls": dossier.get("officialUrls", []),
    })


def knowledge_runtime_probe_summary_sentence(runtime_probe_display: Any) -> Optional[str]:
    if not isinstance(runtime_probe_display, dict):
        return None
    summary = str(runtime_probe_display.get("summary") or "").strip()
    if not summary:
        return None
    return humanize_knowledge_display_text(summary)


def knowledge_runtime_probe_count(runtime_probe_display: Any) -> int:
    try:
        return int(runtime_probe_display.get("itemCount", 0) or 0) if isinstance(runtime_probe_display, dict) else 0
    except (TypeError, ValueError):
        return 0


def knowledge_display_source_fact(
    source_fact: Any,
    *,
    summary: Optional[str] = None,
    runtime_probe_display: Any = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(source_fact, dict):
        return None
    key = str(source_fact.get("key") or "").strip().lower()
    override_facts = KNOWLEDGE_SOURCE_FACT_DISPLAY_OVERRIDES.get(key, [])
    runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
    summary_display = humanize_knowledge_display_text(summary)
    if runtime_summary:
        summary_display = join_product_sentences([summary_display, runtime_summary]) or runtime_summary
    return normalize_source_fact_payload({
        "key": source_fact.get("key"),
        "topic": source_fact.get("topic"),
        "summary": summary_display,
        "facts": humanize_knowledge_display_list(override_facts),
        "sourceKeys": source_fact.get("sourceKeys", []),
        "runtimeSummary": runtime_summary,
        "runtimeProbeCount": knowledge_runtime_probe_count(runtime_probe_display) or None,
    })


def knowledge_display_evidence(evidence_matches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    rendered: list[dict[str, Any]] = []
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for item in evidence_matches:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        claim = str(item.get("claim") or "").strip()
        source_key = str(item.get("sourceKey") or "").strip()
        override = KNOWLEDGE_EVIDENCE_DISPLAY_OVERRIDES.get(key, {})
        claim_display = humanize_knowledge_display_text(override.get("claim") or claim)
        preview_display = str(item.get("previewDisplay") or claim_display or "").strip() or None
        display_item = normalize_runtime_probe_payload({
            "key": key or None,
            "topicKey": item.get("topicKey"),
            "label": key or claim or None,
            "labelRaw": key or claim or None,
            "displayLabel": claim_display or key or None,
            "command": None,
            "commandRaw": None,
            "commandDisplay": None,
            "summary": preview_display,
            "summaryDisplay": preview_display,
            "summaryRaw": claim or None,
            "preview": preview_display,
            "claim": claim or None,
            "claimDisplay": claim_display,
            "claimRaw": claim or None,
            "previewDisplay": preview_display,
            "previewRaw": claim or None,
            "message": claim_display,
            "messageDisplay": claim_display,
            "messageRaw": claim or None,
            "textDisplay": claim_display,
            "textRaw": claim or None,
            "state": None,
            "stateDisplay": None,
            "userActions": None,
            "userActionsDisplay": None,
            "userActionsRaw": None,
            "nextCommand": None,
            "nextCommandDisplay": None,
            "nextCommandRaw": None,
            "detailDisplay": None,
            "detailRaw": None,
            "errorSummaryDisplay": None,
            "errorSummaryRaw": None,
            "status": None,
            "statusDisplay": None,
            "sourceKey": source_key or None,
            "sourceName": item.get("sourceName"),
            "sourceNameDisplay": humanize_knowledge_source_label(item.get("sourceName") or source_key) or None,
            "locator": item.get("locator"),
            "locatorDisplay": humanize_knowledge_locator(item.get("locator")),
            "resultDisplay": None,
            "runtimeGuidanceDisplay": None,
            "evidenceType": item.get("evidenceType"),
            "evidenceTypeDisplay": KNOWLEDGE_EVIDENCE_TYPE_LABELS.get(str(item.get("evidenceType") or "").strip()),
            "stability": item.get("stability"),
            "stabilityDisplay": KNOWLEDGE_STABILITY_LABELS.get(str(item.get("stability") or "").strip()),
            "rationale": item.get("rationale"),
            "rationaleDisplay": humanize_knowledge_display_text(override.get("rationale") or item.get("rationale")),
            "sourceUrl": item.get("sourceUrl"),
            "trustTier": item.get("trustTier"),
        }, RUNTIME_PROBE_EVIDENCE_FIELDS)
        rendered.append(display_item)
        if source_key and claim:
            index[(source_key, claim)] = display_item
    return rendered, index


def knowledge_display_citations(
    citations: list[dict[str, Any]],
    *,
    evidence_display_index: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for item in citations:
        if not isinstance(item, dict):
            continue
        source_key = str(item.get("sourceKey") or "").strip()
        claim = str(item.get("claim") or "").strip()
        match = evidence_display_index.get((source_key, claim), {})
        rendered.append(
            normalize_citation_payload({
                "sourceKey": source_key or None,
                "sourceName": item.get("sourceName"),
                "sourceNameDisplay": humanize_knowledge_source_label(item.get("sourceName") or source_key) or None,
                "url": item.get("url"),
                "locator": item.get("locator"),
                "locatorDisplay": humanize_knowledge_locator(item.get("locator")),
                "claim": item.get("claim"),
                "claimDisplay": match.get("claimDisplay") if isinstance(match, dict) else None,
                "evidenceType": item.get("evidenceType"),
                "evidenceTypeDisplay": KNOWLEDGE_EVIDENCE_TYPE_LABELS.get(str(item.get("evidenceType") or "").strip()),
                "stability": item.get("stability"),
                "stabilityDisplay": KNOWLEDGE_STABILITY_LABELS.get(str(item.get("stability") or "").strip()),
            })
        )
    return rendered


def knowledge_source_summary_display(source_record: Any) -> Optional[str]:
    if not isinstance(source_record, dict):
        return None
    kind = str(source_record.get("kind") or "").strip()
    worknet_key = str(source_record.get("worknetKey") or "").strip().lower()
    worknet_name = None
    if worknet_key:
        profile = resolve_worknet(worknet_key)
        if isinstance(profile, dict):
            worknet_name = str(profile.get("name") or "").strip() or None
    if kind == "protocol":
        return "这是 AWP 协议主入口来源，用来确认官网入口和高层协议说明。"
    if kind == "directory":
        return "这是官方目录页来源，用来确认公开列表、索引和当前可见条目。"
    if kind == "paper":
        return "这是白皮书规范来源，用来确认 RootNet、WorkNet、排放、质押和治理边界。"
    if kind == "skill":
        if worknet_name:
            return f"这是 {worknet_name} 的官方 skill 仓库来源，用来确认安装入口和上游仓库是否变化。"
        return "这是官方 skill 仓库来源，用来确认安装入口和上游仓库是否变化。"
    if kind == "skill-doc":
        if worknet_name:
            return f"这是 {worknet_name} 的官方 skill 说明原文，工作站用它核对命令、资格要求和运行约束。"
        return "这是官方 skill 说明原文，工作站用它核对命令、资格要求和运行约束。"
    if kind == "aip":
        if worknet_name:
            return f"这是 {worknet_name} 的 AIP 规范原文，用来确认这条 WorkNet 的规则和经济边界。"
        return "这是 AIP 规范原文，用来确认某条 WorkNet 的规则和经济边界。"
    if kind == "live-api":
        return "这是官方实时接口来源，用来确认当前 WorkNet ID、技能来源和在线状态。"
    if kind == "worknet":
        if worknet_name:
            return f"这是 {worknet_name} 的官方工作网页面，用来确认公开操作入口和高层玩法。"
        return "这是官方工作网页面，用来确认公开操作入口和高层玩法。"
    if kind == "protocol-surface":
        return "这是官方协议页面来源，用来确认当前公开参数和产品说明。"
    if kind == "worknet-surface":
        return "这是官方 WorkNet 页面来源，用来确认测试网或公开任务入口。"
    if kind == "docs":
        return "这是官方文档/博客来源，用来补足上手指引和概念说明。"
    if kind == "service":
        return "这是官方服务页面来源，用来确认身份验证或委托路径。"
    summary = str(source_record.get("summary") or "").strip()
    return summary or None


def knowledge_display_source_record(
    source_record: Any,
    *,
    drift_item: Any = None,
    impact_item: Any = None,
    runtime_probe_display: Any = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(source_record, dict):
        return None
    key = str(source_record.get("key") or "").strip()
    name_display = humanize_knowledge_source_label(source_record.get("name") or key) or None
    kind = str(source_record.get("kind") or "").strip()
    trust_tier = source_record.get("trustTier")
    drift_status = str(drift_item.get("status") or drift_item.get("driftStatus") or "").strip() if isinstance(drift_item, dict) else ""
    headline = (
        f"{name_display} 当前有上游变更待复核。"
        if drift_status and drift_status not in {"unchanged", "no-baseline"}
        else f"{name_display} 当前资料可直接参考。"
    ) if name_display else None
    impacted_topics = len(impact_item.get("impactedTopics", [])) if isinstance(impact_item, dict) and isinstance(impact_item.get("impactedTopics"), list) else 0
    impacted_facts = len(impact_item.get("impactedFacts", [])) if isinstance(impact_item, dict) and isinstance(impact_item.get("impactedFacts"), list) else 0
    impacted_worknets = len(impact_item.get("impactedWorknets", [])) if isinstance(impact_item, dict) and isinstance(impact_item.get("impactedWorknets"), list) else 0
    summary_display = knowledge_source_summary_display(source_record)
    if isinstance(impact_item, dict) and (impacted_topics or impacted_facts or impacted_worknets):
        summary_display = (
            f"{summary_display} 当前它直接牵动 {impacted_topics} 个主题、"
            f"{impacted_facts} 条事实和 {impacted_worknets} 个工作网。"
        ).strip()
    runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
    if runtime_summary:
        summary_display = join_product_sentences([summary_display, runtime_summary]) or runtime_summary
    summary_preview = knowledge_runtime_augmented_preview(
        summary_display or source_record.get("summary"),
        runtime_summary,
        headline=headline,
        max_chars=140,
        max_sentences=2,
    ) or compact_preview_text(
        summary_display or source_record.get("summary"),
        max_chars=140,
        max_sentences=2,
    )
    return normalize_source_record_payload({
        "key": source_record.get("key"),
        "name": source_record.get("name"),
        "nameDisplay": name_display,
        "url": source_record.get("url"),
        "kind": source_record.get("kind"),
        "kindDisplay": humanize_knowledge_source_kind(kind),
        "trustTier": trust_tier,
        "trustTierDisplay": humanize_knowledge_trust_tier(trust_tier),
        "worknetKey": source_record.get("worknetKey"),
        "headline": headline,
        "summary": source_record.get("summary"),
        "summaryDisplay": summary_display,
        "summaryPreview": summary_preview,
        "runtimeSummary": runtime_summary,
        "runtimeProbeCount": knowledge_runtime_probe_count(runtime_probe_display) or None,
    })


def knowledge_display_drift_item(
    drift_item: Any,
    *,
    source_record: Any = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(drift_item, dict):
        return None
    source_name = (
        (source_record.get("name") if isinstance(source_record, dict) else None)
        or drift_item.get("name")
        or drift_item.get("key")
    )
    changed_fields = [str(item).strip() for item in drift_item.get("changedFields", []) if str(item).strip()]
    return normalize_drift_payload({
        "key": drift_item.get("key"),
        "name": drift_item.get("name"),
        "nameDisplay": humanize_knowledge_source_label(source_name) or None,
        "status": drift_item.get("status"),
        "statusDisplay": KNOWLEDGE_DRIFT_STATUS_LABELS.get(str(drift_item.get("status") or "").strip()),
        "changedFields": changed_fields,
        "changedFieldsDisplay": [humanize_source_changed_field(item) for item in changed_fields],
        "note": drift_item.get("note"),
        "previous": drift_item.get("previous"),
        "current": drift_item.get("current"),
    })


def knowledge_display_changed_sources(
    changed_items: Any,
    *,
    source_records: Optional[dict[str, dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    source_records = source_records or {}
    for item in changed_items if isinstance(changed_items, list) else []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        rendered.append(
            knowledge_display_drift_item(
                item,
                source_record=source_records.get(key),
            )
            or {}
        )
    return [item for item in rendered if item]


def changed_source_highlight_entry(item: Any) -> Optional[dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    key = str(item.get("key") or "").strip()
    label = str(item.get("nameDisplay") or item.get("name") or key).strip()
    changed_fields = item.get("changedFieldsDisplay", []) if isinstance(item.get("changedFieldsDisplay"), list) else []
    preview = str(item.get("note") or "").strip()
    if not preview and changed_fields:
        preview = f"变化字段包括 {'、'.join(str(field).strip() for field in changed_fields if str(field).strip())}。"
    payload = build_normalized_knowledge_highlight(
        kind="source",
        fields=CHANGED_SOURCE_HIGHLIGHT_FIELDS,
        key=key,
        label=label,
        headline=item.get("headline") or (f"{label} 当前有上游变更待复核。" if label else None),
        preview=preview,
        query_command=query_source_command(key) if key else None,
        primary_command=query_source_command(key, rebuild=True) if key else None,
        freshness_status="affected",
        research_tier="queued",
        extra={
            "nameDisplay": item.get("nameDisplay"),
            "statusDisplay": item.get("statusDisplay"),
            "changedFieldsDisplay": changed_fields,
            "summary": compact_preview_text(preview, max_chars=140, max_sentences=2) if preview else None,
            "summaryPreview": compact_preview_text(preview, max_chars=140, max_sentences=2) if preview else None,
            "summaryFull": preview or None,
        },
    )
    return payload


def knowledge_skill_inspections_by_key(catalog: Any) -> dict[str, dict[str, Any]]:
    inspections = catalog.get("skillInspections", []) if isinstance(catalog, dict) else []
    return {
        str(item.get("skillKey") or "").strip().lower(): item
        for item in inspections
        if isinstance(item, dict) and str(item.get("skillKey") or "").strip()
    }


def knowledge_runtime_probe_display_from_catalog(
    catalog: Any,
    *,
    source_keys: Any = None,
    worknet_key: Optional[str] = None,
    capability_report: Any = None,
) -> Optional[dict[str, Any]]:
    if isinstance(capability_report, dict) and isinstance(capability_report.get("skillInspection"), dict):
        return knowledge_runtime_probe_display(
            capability_report.get("skillInspection"),
            skill_key=worknet_key,
        )
    inspections = knowledge_skill_inspections_by_key(catalog)
    normalized_worknet_key = str(worknet_key or "").strip().lower()
    if normalized_worknet_key and normalized_worknet_key in inspections:
        return knowledge_runtime_probe_display(
            inspections[normalized_worknet_key],
            skill_key=normalized_worknet_key,
        )
    source_records = knowledge_source_records_from_catalog(catalog)
    for source_key in source_keys if isinstance(source_keys, list) else []:
        normalized_source_key = str(source_key or "").strip().lower()
        if not normalized_source_key:
            continue
        if normalized_source_key in inspections:
            return knowledge_runtime_probe_display(
                inspections[normalized_source_key],
                skill_key=normalized_source_key,
            )
        source_record = source_records.get(normalized_source_key) or source_records.get(str(source_key or "").strip())
        source_worknet_key = str(source_record.get("worknetKey") or "").strip().lower() if isinstance(source_record, dict) else ""
        if source_worknet_key and source_worknet_key in inspections:
            return knowledge_runtime_probe_display(
                inspections[source_worknet_key],
                skill_key=source_worknet_key,
            )
    return None


def knowledge_runtime_probe_summary(
    probe_results: Any,
    *,
    label: str,
) -> Optional[str]:
    items = [item for item in probe_results if isinstance(item, dict)] if isinstance(probe_results, list) else []
    if not items:
        return None
    failed = [item for item in items if runtime_probe_effective_status(item) != "ok"]
    if failed:
        first = failed[0]
        detail = str(
            first.get("summaryDisplay")
            or first.get("resultSummary")
            or first.get("messageDisplay")
            or first.get("textDisplay")
            or ""
        ).strip()
        if detail:
            return f"{label} 当前有 {len(failed)} 条本地运行检查没通过。 例如：{detail}"
        return f"{label} 当前有 {len(failed)} 条本地运行检查没通过。"
    first = items[0]
    detail = str(
        first.get("summaryDisplay")
        or first.get("resultSummary")
        or first.get("messageDisplay")
        or first.get("textDisplay")
        or ""
    ).strip()
    if detail:
        return f"{label} 当前共有 {len(items)} 条本地运行检查记录。 最近一条：{detail}"
    return f"{label} 当前共有 {len(items)} 条本地运行检查记录。"


def knowledge_runtime_probe_summary_raw(
    probe_results: Any,
) -> Optional[str]:
    items = [item for item in probe_results if isinstance(item, dict)] if isinstance(probe_results, list) else []
    if not items:
        return None
    failed = [item for item in items if runtime_probe_effective_status(item) != "ok"]
    first = failed[0] if failed else items[0]
    return str(
        first.get("summaryRaw")
        or first.get("previewRaw")
        or first.get("messageRaw")
        or first.get("textRaw")
        or first.get("resultSummary")
        or first.get("text")
        or ""
    ).strip() or None


RUNTIME_PROBE_SHARED_FIELDS = [
    "label",
    "labelRaw",
    "displayLabel",
    "command",
    "commandRaw",
    "commandDisplay",
    "summary",
    "summaryDisplay",
    "summaryRaw",
    "preview",
    "previewDisplay",
    "previewRaw",
    "message",
    "messageDisplay",
    "messageRaw",
    "textDisplay",
    "textRaw",
    "state",
    "stateDisplay",
    "userActions",
    "userActionsDisplay",
    "userActionsRaw",
    "nextCommand",
    "nextCommandDisplay",
    "nextCommandRaw",
    "detailDisplay",
    "detailRaw",
    "errorSummaryDisplay",
    "errorSummaryRaw",
    "status",
    "statusDisplay",
    "locatorDisplay",
    "resultDisplay",
    "runtimeGuidanceDisplay",
]

RUNTIME_PROBE_TOP_LEVEL_FIELDS = [
    "skillKey",
    "status",
    "statusDisplay",
    "summary",
    "summaryDisplay",
    "summaryRaw",
    "preview",
    "previewDisplay",
    "previewRaw",
    "itemCount",
    "items",
    "highlights",
]

RUNTIME_PROBE_ITEM_FIELDS = [
    "key",
    *RUNTIME_PROBE_SHARED_FIELDS,
]

RUNTIME_PROBE_HIGHLIGHT_FIELDS = [
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
    *RUNTIME_PROBE_SHARED_FIELDS,
    "summaryPreview",
    "summaryFull",
    "probeLabel",
    "skillKey",
]

RUNTIME_PROBE_EVIDENCE_FIELDS = [
    "key",
    "topicKey",
    *RUNTIME_PROBE_SHARED_FIELDS,
    "claim",
    "claimDisplay",
    "claimRaw",
    "sourceKey",
    "sourceName",
    "sourceNameDisplay",
    "locator",
    "evidenceType",
    "evidenceTypeDisplay",
    "stability",
    "stabilityDisplay",
    "rationale",
    "rationaleDisplay",
    "sourceUrl",
    "trustTier",
]


def normalize_runtime_probe_payload(record: Any, fields: list[str]) -> dict[str, Any]:
    source = record if isinstance(record, dict) else {}
    return project_fields(source, fields)


def runtime_probe_contract_fields(item: Any) -> dict[str, Any]:
    return normalize_runtime_probe_payload(item, RUNTIME_PROBE_SHARED_FIELDS)


def build_runtime_probe_contract_item(
    *,
    key: Any,
    raw_label: Any,
    display_label: Any,
    command: Any,
    locator_display: Any,
    status: Any,
    status_display: Any,
    summary: Any,
    summary_raw: Any,
    preview: Any,
    preview_raw: Any,
    message: Any,
    message_raw: Any,
    state: Any,
    state_display: Any,
    user_actions: Any,
    user_actions_display: Any,
    user_actions_raw: Any,
    next_command: Any,
    next_command_display: Any,
    next_command_raw: Any,
    text_display: Any,
    text_raw: Any,
    detail_display: Any,
    detail_raw: Any,
    error_summary_display: Any,
    error_summary_raw: Any,
    result_display: Any,
    runtime_guidance_display: Any,
) -> dict[str, Any]:
    payload = {
        "key": key,
        "label": raw_label,
        "labelRaw": raw_label,
        "displayLabel": display_label,
        "command": command,
        "commandRaw": command,
        "commandDisplay": display_label,
        "locatorDisplay": locator_display,
        "status": status,
        "statusDisplay": status_display,
        "summary": summary,
        "summaryDisplay": summary,
        "summaryRaw": summary_raw,
        "preview": preview,
        "previewDisplay": preview,
        "previewRaw": preview_raw,
        "message": message,
        "messageDisplay": message,
        "messageRaw": message_raw,
        "state": state,
        "stateDisplay": state_display,
        "userActions": user_actions,
        "userActionsDisplay": user_actions_display,
        "userActionsRaw": user_actions_raw,
        "nextCommand": next_command,
        "nextCommandDisplay": next_command_display,
        "nextCommandRaw": next_command_raw,
        "textDisplay": text_display,
        "textRaw": text_raw,
        "detailDisplay": detail_display,
        "detailRaw": detail_raw,
        "errorSummaryDisplay": error_summary_display,
        "errorSummaryRaw": error_summary_raw,
        "resultDisplay": result_display,
        "runtimeGuidanceDisplay": runtime_guidance_display,
    }
    return normalize_runtime_probe_payload(payload, RUNTIME_PROBE_ITEM_FIELDS)


def runtime_probe_highlight_extra(
    item: Any,
    *,
    summary_full: Any,
    probe_label: Any,
    skill_key: Any,
) -> dict[str, Any]:
    payload = runtime_probe_contract_fields(item)
    payload.update(
        {
            "label": item.get("displayLabel") or item.get("label"),
            "command": item.get("command"),
            "summary": compact_preview_text(summary_full, max_chars=140, max_sentences=2) if summary_full else None,
            "summaryPreview": compact_preview_text(summary_full, max_chars=140, max_sentences=2) if summary_full else None,
            "summaryFull": summary_full,
            "probeLabel": probe_label,
            "skillKey": skill_key,
        }
    )
    return payload


def runtime_probe_claim_display(item: Any) -> Optional[str]:
    item = item if isinstance(item, dict) else {}
    label = str(item.get("displayLabel") or item.get("label") or "").strip()
    summary = str(item.get("summary") or item.get("messageDisplay") or item.get("textDisplay") or "").strip()
    preview_display = str(item.get("previewDisplay") or "").strip()
    if preview_display:
        return preview_display
    if summary:
        normalized_summary = strip_sentence_end(summary)
        normalized_label = strip_sentence_end(label)
        return summary if normalized_label and normalized_summary.startswith(normalized_label) else f"{label}：{summary}"
    if label:
        return f"{label} 当前{str(item.get('statusDisplay') or '').strip() or '有最新运行记录'}。"
    return None


def build_runtime_probe_highlight_entry(
    item: Any,
    *,
    probe_label: Any,
    skill_key: Any,
) -> dict[str, Any]:
    item = item if isinstance(item, dict) else {}
    label = str(item.get("displayLabel") or item.get("label") or "").strip()
    status = str(item.get("status") or "").strip()
    summary = str(item.get("summary") or "").strip() or None
    payload = build_knowledge_highlight_entry(
        kind="evidence",
        key=item.get("key"),
        label=label,
        headline=f"{label} 当前{humanize_executed_step_status_display(status) or status}。" if label else None,
        preview=summary,
        query_command=item.get("command"),
        primary_command=item.get("command"),
        freshness_status="affected" if status != "ok" else "stable",
        research_tier="related",
        extra=runtime_probe_highlight_extra(
            item,
            summary_full=summary,
            probe_label=probe_label,
            skill_key=skill_key,
        ),
    )
    return normalize_runtime_probe_payload(payload, RUNTIME_PROBE_HIGHLIGHT_FIELDS)


def build_runtime_probe_evidence_entry(
    item: Any,
    *,
    skill_key: str,
    source_name_display: str,
    topic_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    item = item if isinstance(item, dict) else {}
    label = str(item.get("displayLabel") or item.get("label") or "").strip()
    if not label:
        return None
    command = str(item.get("command") or "").strip() or None
    locator_display = humanize_runtime_probe_locator_display(
        label,
        command=command,
        skill_key=skill_key,
    ) or "本地运行检查命令"
    claim_display = runtime_probe_claim_display(item)
    if not claim_display:
        return None
    payload = {
        "key": item.get("key"),
        "topicKey": topic_key or None,
        **runtime_probe_contract_fields(item),
        "label": label,
        "command": command,
        "labelRaw": item.get("labelRaw") or item.get("label"),
        "claim": claim_display,
        "claimDisplay": humanize_knowledge_display_text(claim_display),
        "claimRaw": item.get("previewRaw") or item.get("summaryRaw") or item.get("messageRaw") or item.get("textRaw"),
        "sourceKey": skill_key or None,
        "sourceName": source_name_display,
        "sourceNameDisplay": source_name_display,
        "locator": command,
        "locatorDisplay": locator_display,
        "evidenceType": "runtime-inspection",
        "evidenceTypeDisplay": KNOWLEDGE_EVIDENCE_TYPE_LABELS.get("runtime-inspection"),
        "stability": "medium" if item.get("status") == "ok" else "low",
        "stabilityDisplay": KNOWLEDGE_STABILITY_LABELS.get("medium" if item.get("status") == "ok" else "low"),
        "rationale": "这是工作站本地运行检查留下的最新运行证据。",
        "rationaleDisplay": "这是工作站本地运行检查留下的最新运行证据。",
        "sourceUrl": None,
        "trustTier": None,
        "summaryDisplay": item.get("summaryDisplay") or item.get("summary"),
        "previewDisplay": str(item.get("previewDisplay") or "").strip() or humanize_knowledge_display_text(claim_display),
    }
    return normalize_runtime_probe_payload(payload, RUNTIME_PROBE_EVIDENCE_FIELDS)


def knowledge_runtime_probe_display(
    inspection: Any,
    *,
    skill_key: Any,
) -> Optional[dict[str, Any]]:
    if not isinstance(inspection, dict):
        return None
    normalized_skill_key = str(skill_key or inspection.get("skillKey") or "").strip().lower()
    probe_results = inspection.get("probeResults", []) if isinstance(inspection.get("probeResults"), list) else []
    label = runtime_guidance_worknet_name(normalized_skill_key)
    summary = knowledge_runtime_probe_summary(probe_results, label=label)
    summary_raw = knowledge_runtime_probe_summary_raw(probe_results)
    items: list[dict[str, Any]] = []
    highlights: list[dict[str, Any]] = []
    for probe in probe_results:
        if not isinstance(probe, dict):
            continue
        raw_label = str(probe.get("label") or "").strip()
        command = render_argv([str(part) for part in probe.get("argv", [])]) if isinstance(probe.get("argv"), list) and probe.get("argv") else None
        display_label = humanize_runtime_probe_check_label(
            raw_label,
            command=command,
            skill_key=normalized_skill_key,
        ) or humanize_executed_step_label(raw_label, category="inspect", execution_policy="probe") or raw_label
        locator_display = humanize_runtime_probe_locator_display(
            display_label or raw_label,
            command=command,
            skill_key=normalized_skill_key,
        )
        status = runtime_probe_effective_status(probe)
        status_summary = humanize_executed_step_status_display(status)
        result_summary = str(probe.get("resultSummary") or probe.get("messageDisplay") or probe.get("textDisplay") or "").strip() or None
        if not result_summary and display_label and status_summary:
            result_summary = f"{display_label}：当前{status_summary}。"
        result_display = probe.get("resultDisplay") if isinstance(probe.get("resultDisplay"), dict) else {}
        stdout_display = result_display.get("stdoutDisplay") if isinstance(result_display.get("stdoutDisplay"), dict) else {}
        runtime_guidance_display = probe.get("runtimeGuidanceDisplay") if isinstance(probe.get("runtimeGuidanceDisplay"), dict) else {}
        preview_display = str(probe.get("previewDisplay") or result_summary or "").strip() or None
        preview_raw = str(
            probe.get("previewRaw")
            or result_display.get("previewRaw")
            or stdout_display.get("previewRaw")
            or probe.get("textRaw")
            or probe.get("text")
            or ""
        ).strip() or None
        message_display = str(probe.get("messageDisplay") or result_summary or "").strip() or None
        message_raw = str(
            probe.get("messageRaw")
            or runtime_guidance_display.get("messageRaw")
            or stdout_display.get("messageRaw")
            or runtime_message(probe.get("result"))
            or ""
        ).strip() or None
        text_raw = str(probe.get("textRaw") or probe.get("text") or "").strip() or None
        summary_raw = str(
            probe.get("resultSummaryRaw")
            or result_display.get("summaryRaw")
            or text_raw
            or ""
        ).strip() or None
        payload = probe.get("result") if isinstance(probe.get("result"), dict) else {}
        state_raw = str(payload.get("state") or "").strip() if isinstance(payload, dict) else ""
        next_command_raw = None
        next_command = runtime_guidance_display.get("nextCommand")
        if isinstance(next_command, list) and next_command:
            next_command_raw = render_argv([str(part) for part in next_command])
        elif isinstance(next_command, str) and next_command.strip():
            next_command_raw = next_command.strip()
        user_actions_raw = [
            str(item).strip()
            for item in runtime_guidance_display.get("userActionsRaw", runtime_guidance_display.get("userActions", []))
            if isinstance(item, str) and str(item).strip()
        ] if isinstance(runtime_guidance_display.get("userActionsRaw", runtime_guidance_display.get("userActions", [])), list) else []
        item = build_runtime_probe_contract_item(
            key=f"{normalized_skill_key}:{safe_slug(raw_label) or 'probe'}" if normalized_skill_key else (safe_slug(raw_label) or raw_label),
            raw_label=raw_label or None,
            display_label=display_label or raw_label or None,
            command=command,
            locator_display=locator_display,
            status=status,
            status_display=status_summary,
            summary=result_summary,
            summary_raw=summary_raw,
            preview=preview_display,
            preview_raw=preview_raw,
            message=message_display,
            message_raw=message_raw,
            state=state_raw or None,
            state_display=probe.get("stateDisplay"),
            user_actions=runtime_guidance_display.get("userActionsDisplay") or probe.get("userActionsDisplay"),
            user_actions_display=runtime_guidance_display.get("userActionsDisplay") or probe.get("userActionsDisplay"),
            user_actions_raw=user_actions_raw or None,
            next_command=next_command_raw,
            next_command_display=runtime_guidance_display.get("nextCommandDisplay") or probe.get("nextCommandDisplay"),
            next_command_raw=runtime_guidance_display.get("nextCommandRaw") or next_command_raw,
            text_display=probe.get("textDisplay"),
            text_raw=text_raw,
            detail_display=stdout_display.get("detailDisplay"),
            detail_raw=stdout_display.get("detailRaw"),
            error_summary_display=stdout_display.get("errorSummaryDisplay"),
            error_summary_raw=stdout_display.get("errorSummaryRaw"),
            result_display=result_display or None,
            runtime_guidance_display=runtime_guidance_display or None,
        )
        items.append(item)
        highlights.append(
            build_runtime_probe_highlight_entry(
                item,
                probe_label=raw_label or None,
                skill_key=normalized_skill_key or None,
            )
        )
    payload = {
        "skillKey": normalized_skill_key or None,
        "status": inspection.get("status"),
        "statusDisplay": humanize_skill_inspection_status(str(inspection.get("status") or "").strip() or None),
        "summary": summary,
        "summaryDisplay": summary,
        "summaryRaw": summary_raw,
        "preview": summary,
        "previewDisplay": summary,
        "previewRaw": summary_raw,
        "itemCount": len(items),
        "items": items,
        "highlights": highlights,
    }
    return normalize_runtime_probe_payload(payload, RUNTIME_PROBE_TOP_LEVEL_FIELDS)


def knowledge_runtime_probe_evidence_entries(
    runtime_probe_display: Any,
    *,
    topic_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    if not isinstance(runtime_probe_display, dict):
        return []
    skill_key = str(runtime_probe_display.get("skillKey") or "").strip().lower()
    source_name = runtime_guidance_worknet_name(skill_key)
    source_name_display = (
        f"{source_name} 本地运行检查" if source_name and source_name != "当前" else "本地运行检查"
    )
    rendered: list[dict[str, Any]] = []
    for item in runtime_probe_display.get("items", [])[:3]:
        payload = build_runtime_probe_evidence_entry(
            item,
            skill_key=skill_key,
            source_name_display=source_name_display,
            topic_key=topic_key,
        )
        if payload:
            rendered.append(payload)
    return rendered


def knowledge_runtime_probe_display_for_topic(
    *,
    topic: str,
    catalog: Any,
    worknet_context: Any,
    capability_report: Any,
) -> Optional[dict[str, Any]]:
    inspections = knowledge_skill_inspections_by_key(catalog)
    worknet_key = str(worknet_context.get("key") or "").strip().lower() if isinstance(worknet_context, dict) else ""
    if isinstance(capability_report, dict) and isinstance(capability_report.get("skillInspection"), dict):
        return knowledge_runtime_probe_display(
            capability_report.get("skillInspection"),
            skill_key=worknet_key,
        )
    topic_key = str(topic or "").strip().lower()
    if topic_key and topic_key in inspections:
        return knowledge_runtime_probe_display(inspections[topic_key], skill_key=topic_key)
    if worknet_key and worknet_key in inspections:
        return knowledge_runtime_probe_display(inspections[worknet_key], skill_key=worknet_key)
    return None


def knowledge_runtime_probe_display_for_source(
    *,
    source_key: str,
    source_record: Any,
    catalog: Any,
    capability_report: Any = None,
) -> Optional[dict[str, Any]]:
    inspections = knowledge_skill_inspections_by_key(catalog)
    normalized_source_key = str(source_key or "").strip().lower()
    worknet_key = str(source_record.get("worknetKey") or "").strip().lower() if isinstance(source_record, dict) else ""
    if isinstance(capability_report, dict) and isinstance(capability_report.get("skillInspection"), dict):
        return knowledge_runtime_probe_display(
            capability_report.get("skillInspection"),
            skill_key=worknet_key or normalized_source_key,
        )
    if normalized_source_key and normalized_source_key in inspections:
        return knowledge_runtime_probe_display(inspections[normalized_source_key], skill_key=normalized_source_key)
    if worknet_key and worknet_key in inspections:
        return knowledge_runtime_probe_display(inspections[worknet_key], skill_key=worknet_key)
    return None


def knowledge_display_worknet(
    worknet: Any,
    *,
    capability_report: Any = None,
    runtime_probe_display: Any = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(worknet, dict):
        return None
    key = str(worknet.get("key") or "").strip().lower()
    narrative = canonical_topic_narrative(key, dossier_key=key, worknet_key=key)
    runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
    caution_display = humanize_knowledge_display_text((narrative or {}).get("caution"))
    if runtime_summary:
        caution_display = join_product_sentences([caution_display, runtime_summary]) or runtime_summary
    rendered = {
        "key": worknet.get("key"),
        "worknetId": worknet.get("worknetId"),
        "name": worknet.get("name"),
        "status": worknet.get("status"),
        "statusDisplay": KNOWLEDGE_WORKNET_STATUS_LABELS.get(str(worknet.get("status") or "").strip()),
        "symbol": worknet.get("symbol"),
        "installUri": worknet.get("installUri"),
        "sourceKeys": worknet.get("sourceKeys", []),
        "sourceKeysDisplay": [
            humanize_knowledge_source_label(item)
            for item in worknet.get("sourceKeys", [])
            if str(item).strip()
        ],
        "goal": worknet.get("goal"),
        "goalDisplay": humanize_knowledge_display_text((narrative or {}).get("plain") or worknet.get("goal")),
        "loop": worknet.get("loop"),
        "loopDisplay": humanize_knowledge_display_text((narrative or {}).get("loop") or worknet.get("loop")),
        "automationLevel": worknet.get("automationLevel"),
        "automationLevelDisplay": KNOWLEDGE_AUTOMATION_LABELS.get(str(worknet.get("automationLevel") or "").strip()),
        "riskLevel": worknet.get("riskLevel"),
        "riskLevelDisplay": KNOWLEDGE_RISK_LABELS.get(str(worknet.get("riskLevel") or "").strip()),
        "recommendedRole": worknet.get("recommendedRole"),
        "recommendedRoleDisplay": KNOWLEDGE_ROLE_LABELS.get(str(worknet.get("recommendedRole") or "").strip()),
        "cautionDisplay": caution_display,
        "runtimeSummary": runtime_summary,
        "runtimeProbeCount": knowledge_runtime_probe_count(runtime_probe_display) or None,
    }
    if isinstance(capability_report, dict):
        rendered["runnable"] = capability_report.get("runnable")
        rendered["canStartWithoutStake"] = capability_report.get("canStartWithoutStake")
        rendered["safeLongRun"] = capability_report.get("safeLongRun")
        rendered["cliStatus"] = capability_report.get("cliStatus")
        rendered["executionState"] = capability_report.get("executionState")
        rendered["executionStateDisplay"] = capability_report.get("executionStateDisplay")
        rendered["executionHeadline"] = capability_report.get("executionHeadline")
    return normalize_worknet_payload(rendered)


def knowledge_display_source_impact(
    source_impact: Any,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(source_impact, dict):
        return None
    items = source_impact.get("items", [])
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    topic_result_cache: dict[str, dict[str, Any]] = {}

    def topic_label(topic_key: Any) -> str:
        normalized = str(topic_key or "").strip()
        if not normalized:
            return normalized
        if normalized not in topic_result_cache:
            topic_result_cache[normalized] = build_knowledge_query_result(normalized, catalog=catalog)
        result = topic_result_cache[normalized]
        return str(result.get("resolvedTopicLabel") or normalized).strip()

    rendered_items: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        impacted_topics_display: list[str] = []
        for target in item.get("impactedTopics", []) if isinstance(item.get("impactedTopics"), list) else []:
            if isinstance(target, dict):
                label = str(target.get("title") or target.get("label") or target.get("key") or "").strip()
            else:
                label = ""
            if not label and target:
                label = topic_label(target)
            if label and label not in impacted_topics_display:
                impacted_topics_display.append(label)
        impacted_facts_display: list[str] = []
        for target in item.get("impactedFacts", []) if isinstance(item.get("impactedFacts"), list) else []:
            if isinstance(target, dict):
                label = str(target.get("topic") or target.get("title") or target.get("label") or target.get("key") or "").strip()
            else:
                label = ""
            if not label and target:
                label = topic_label(target)
            if label and label not in impacted_facts_display:
                impacted_facts_display.append(label)
        impacted_worknets_display: list[str] = []
        for target in item.get("impactedWorknets", []) if isinstance(item.get("impactedWorknets"), list) else []:
            profile = resolve_worknet(str(target or ""))
            label = str(profile.get("name") or target or "").strip() if isinstance(profile, dict) else str(target or "").strip()
            if label and label not in impacted_worknets_display:
                impacted_worknets_display.append(label)
        changed_fields = [str(field).strip() for field in item.get("changedFields", []) if str(field).strip()]
        review_commands = [
            str(command).strip()
            for command in item.get("reviewCommands", [])
            if str(command).strip()
        ] if isinstance(item.get("reviewCommands"), list) else []
        rendered_items.append(
            normalize_source_impact_item_payload({
                "sourceKey": item.get("sourceKey"),
                "sourceName": item.get("sourceName"),
                "sourceNameDisplay": humanize_knowledge_source_label(item.get("sourceName") or item.get("sourceKey")) or None,
                "priority": item.get("priority"),
                "priorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(str(item.get("priority") or "").strip()),
                "driftStatus": item.get("driftStatus"),
                "driftStatusDisplay": KNOWLEDGE_DRIFT_STATUS_LABELS.get(str(item.get("driftStatus") or "").strip()),
                "changedFields": changed_fields,
                "changedFieldsDisplay": [humanize_source_changed_field(field) for field in changed_fields],
                "note": item.get("note"),
                "impactedTopicsDisplay": impacted_topics_display,
                "impactedFactsDisplay": impacted_facts_display,
                "impactedWorknetsDisplay": impacted_worknets_display,
                "reviewHint": item.get("reviewHint"),
                "reviewCommands": review_commands,
            })
        )
    affected = bool(source_impact.get("affected"))
    if affected and rendered_items:
        summary = f"当前有 {len(rendered_items)} 个直接来源正在影响这条知识，继续前先复核。"
    else:
        summary = "当前没有发现直接影响这条知识的上游来源变更。"
    return normalize_source_impact_payload({
        "affected": affected,
        "summary": summary,
        "items": rendered_items,
    })


def knowledge_display_freshness(freshness: Any) -> Optional[dict[str, Any]]:
    if not isinstance(freshness, dict):
        return None
    items = freshness.get("items", [])
    rendered_items: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        impact_items = item.get("impactItems", [])
        changed_sources_display: list[str] = []
        for impact in impact_items if isinstance(impact_items, list) else []:
            if not isinstance(impact, dict):
                continue
            source_label = humanize_knowledge_source_label(impact.get("sourceName") or impact.get("sourceKey"))
            if source_label and source_label not in changed_sources_display:
                changed_sources_display.append(source_label)
        rendered_items.append(
            normalize_freshness_payload({
                "key": item.get("key"),
                "label": item.get("label"),
                "bucket": item.get("bucket"),
                "bucketDisplay": KNOWLEDGE_FRESHNESS_BUCKET_LABELS.get(str(item.get("bucket") or "").strip()),
                "status": item.get("status"),
                "statusDisplay": KNOWLEDGE_FRESHNESS_STATUS_LABELS.get(str(item.get("status") or "").strip()),
                "highestPriority": item.get("highestPriority"),
                "highestPriorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(str(item.get("highestPriority") or "").strip()),
                "changedSourceKeys": item.get("changedSourceKeys", []),
                "changedSourcesDisplay": changed_sources_display,
                "reviewHints": item.get("reviewHints", []),
            }, FRESHNESS_ITEM_FIELDS)
        )
    status = str(freshness.get("status") or "").strip()
    highest_priority = str(freshness.get("highestPriority") or "").strip()
    if status == "affected":
        summary = "这条知识当前受到上游变更影响，继续前应该先复核。"
    else:
        summary = "这条知识当前没有直接上游漂移，可以按现有资料继续参考。"
    return normalize_freshness_payload({
        "status": freshness.get("status"),
        "statusDisplay": KNOWLEDGE_FRESHNESS_STATUS_LABELS.get(status),
        "highestPriority": freshness.get("highestPriority"),
        "highestPriorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(highest_priority),
        "summary": summary,
        "items": rendered_items,
    }, FRESHNESS_DISPLAY_FIELDS)


def knowledge_display_review_queue_entries(
    entries: Any,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    evidence_records = {
        str(item.get("key")): item
        for item in catalog.get("sourceEvidence", [])
        if isinstance(item, dict) and item.get("key")
    }
    topic_result_cache: dict[str, dict[str, Any]] = {}
    rendered: list[dict[str, Any]] = []
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        key = str(item.get("key") or "").strip()
        label = str(item.get("label") or key).strip()
        label_display = label
        headline = None
        if kind == "source":
            label_display = humanize_knowledge_source_label(label)
        elif kind == "evidence":
            evidence_record = evidence_records.get(key)
            if isinstance(evidence_record, dict):
                evidence_display, _ = knowledge_display_evidence([evidence_record])
                if evidence_display:
                    label_display = str(evidence_display[0].get("claimDisplay") or evidence_display[0].get("claim") or label).strip()
        else:
            topic_lookup_key = key
            if topic_lookup_key:
                if topic_lookup_key not in topic_result_cache:
                    topic_result_cache[topic_lookup_key] = build_knowledge_query_result(topic_lookup_key, catalog=catalog)
                topic_result = topic_result_cache[topic_lookup_key]
                label_display = str(topic_result.get("resolvedTopicLabel") or label).strip()
                headline = str(topic_result.get("headline") or "").strip() or None
        preview = humanize_knowledge_review_reason(item.get("reason") or "")
        query_command = None
        primary_command = None
        if kind == "source" and key:
            query_command = query_source_command(key)
            primary_command = query_source_command(key, rebuild=True)
        elif kind in {"topic", "fact", "worknet"} and key:
            query_command = query_knowledge_command(key)
            primary_command = query_knowledge_command(key, rebuild=True)
        elif kind == "evidence":
            evidence_record = evidence_records.get(key)
            topic_key = str(evidence_record.get("topicKey") or "").strip() if isinstance(evidence_record, dict) else ""
            if topic_key:
                query_command = query_knowledge_command(topic_key)
                primary_command = query_knowledge_command(topic_key, rebuild=True)
        payload = build_normalized_knowledge_highlight(
            kind=kind or "entry",
            fields=REVIEW_QUEUE_HIGHLIGHT_FIELDS,
            key=key,
            label=label_display or label,
            headline=headline,
            preview=preview,
            query_command=query_command or item.get("command"),
            primary_command=primary_command or item.get("command"),
            freshness_status="affected",
            research_tier="queued",
            extra={
                "kind": kind,
                "kindDisplay": KNOWLEDGE_QUEUE_KIND_LABELS.get(kind, kind),
                "label": label,
                "labelDisplay": label_display,
                "priority": item.get("priority"),
                "priorityDisplay": KNOWLEDGE_PRIORITY_LABELS.get(str(item.get("priority") or "").strip()),
                "description": preview,
            },
        )
        rendered.append(
            payload
        )
    return rendered


def knowledge_topic_recommendations(
    topic: str,
    label: str,
    *,
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
    capability_report: Optional[dict[str, Any]],
    freshness: Any,
    impact_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label_text: Optional[str], description: str, command: Optional[str]) -> None:
        resolved_label = str(label_text or "").strip()
        resolved_command = str(command or "").strip()
        if not resolved_label or not resolved_command or resolved_label in seen:
            return
        seen.add(resolved_label)
        recommendations.append(
            {
                "label": resolved_label,
                "description": description,
                "command": resolved_command,
            }
        )

    affected = knowledge_freshness_affected_items(freshness)
    capability_state = knowledge_topic_execution_state(
        label=label,
        affected=affected,
        capability_report=capability_report if isinstance(capability_report, dict) else None,
    )
    if affected:
        add(
            f"重审 {label}",
            "重新拉取当前主题，确认上游变更有没有影响这条知识。",
            query_knowledge_command(topic, rebuild=True),
        )
        for item in impact_matches[:2]:
            source_key = str(item.get("sourceKey") or "").strip()
            source_name = humanize_knowledge_source_label(item.get("sourceName") or source_key)
            if source_key:
                add(
                    f"重读来源 {source_name}",
                    "先回到触发变更的官方来源，再决定本地知识要不要改。",
                    query_source_command(source_key, rebuild=True),
                )
    else:
        canonical_topic = knowledge_resolved_topic_key(
            topic,
            glossary_match=glossary_match,
            dossier=dossier,
            worknet=worknet,
        )
        add(
            f"刷新 {label}",
            "重新生成这条主题的本地百科条目，确认缓存仍然一致。",
            query_knowledge_command(canonical_topic, rebuild=True),
        )

    if isinstance(worknet, dict) and worknet.get("key"):
        worknet_key = str(worknet["key"])
        if not affected and isinstance(capability_report, dict):
            runnable = bool(capability_report.get("runnable"))
            cli_status = str(capability_report.get("cliStatus") or "").strip()
            automation = str(capability_report.get("automationLevel") or "").strip()
            role = str(capability_report.get("recommendedRole") or "").strip()
            can_start_without_stake = capability_report.get("canStartWithoutStake") is True
            if worknet_key == "predict" and runnable:
                add(
                    "启动 Predict 静默循环",
                    "先让 Predict 在后台持续观察市场、形成观点，不逐轮打断你。",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif worknet_key == "gov" and cli_status == "ready":
                add(
                    "查看 Gov 公开市场",
                    "先跑一轮 Gov 公共检查，只看公开市场、当前阶段和可做动作，不直接碰签名动作。",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif worknet_key == "ardi" and cli_status == "ready":
                add(
                    "重跑 Ardi 预检",
                    "先跑一轮 Ardi 预检，重新确认手续费、资格路径和下一步命令。",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif role == "identity" or worknet_key == "kya":
                add(
                    "检查 KYA 身份状态",
                    "先确认当前身份、收款地址和委托权限，再决定要不要继续绑定或签名。",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif role == "observer" or automation == "manual-only" or cli_status in {"remote-profile-only", "empty-official-repo"}:
                add(
                    "查看 WorkNet 扫描",
                    f"先看 {label} 当前为什么只建议观察、哪里还不适合自动执行。",
                    scan_worknets_command(),
                )
            elif worknet_key == "mine" and runnable and can_start_without_stake:
                add(
                    f"开始 {label}",
                    "这条是无质押的数据工作流，现在就可以直接开始第一轮。",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif runnable:
                add(
                    f"开始 {label}",
                    "如果你已经理解这条高层主题，现在就可以直接切过去开始。",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
        add(
            f"生成 {label} playbook",
            "把这条知识直接转成工作站可执行的 WorkPlaybook。",
            build_playbook_command(worknet_key),
        )
        add(
            "查看 WorkNet 扫描",
            "回到所有 WorkNet 的当前可运行性和风险对比。",
            scan_worknets_command(),
        )
    else:
        source_keys: list[str] = []
        for container in (dossier, source_fact, glossary_match):
            if not isinstance(container, dict):
                continue
            for source_key in container.get("sourceKeys", []):
                key = str(source_key).strip()
                if key and key not in source_keys:
                    source_keys.append(key)
        for source_key in source_keys[:2]:
            add(
                f"查看来源 {humanize_knowledge_source_label(source_key)}",
                "直接查看这条知识依赖的官方来源。",
                query_source_command(source_key),
            )

    worknet_key = str(worknet.get("key") or "").strip() if isinstance(worknet, dict) else None
    recommendations = prioritize_action_entries(
        recommendations,
        execution_state=capability_state.get("executionState") or ("review_required" if affected else "knowledge_ready"),
        resume_status=None,
        worknet_key=worknet_key or None,
    )
    return recommendations[:5]


def build_knowledge_query_result(
    topic: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    topic = str(topic or "").strip().lower()
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    topic_freshness_catalog = catalog.get("topicFreshness", {}) if isinstance(catalog.get("topicFreshness"), dict) else {}
    knowledge_review_queue = catalog.get("knowledgeReviewQueue", {}) if isinstance(catalog.get("knowledgeReviewQueue"), dict) else {}
    if not knowledge_review_queue:
        knowledge_review_queue = load_cached_knowledge_review_queue() or build_knowledge_review_queue()

    if topic in {"upstream-drift", "source-drift", "source-impact", "stale", "outdated", "review-queue", "knowledge-review-queue", "stale-queue"}:
        source_records: dict[str, dict[str, Any]] = {}
        sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
        for item in sources.get("officialWebSources", []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
        changed_sources = [
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
        impacts = [
            {
                "sourceKey": item.get("sourceKey"),
                "sourceName": item.get("sourceName"),
                "priority": item.get("priority"),
                "impactedTopics": [entry.get("key") for entry in item.get("impactedTopics", []) if isinstance(entry, dict)],
                "impactedFacts": [entry.get("key") for entry in item.get("impactedFacts", []) if isinstance(entry, dict)],
                "impactedWorknets": list(item.get("impactedWorknets", [])),
                "reviewHint": item.get("reviewHint"),
                "reviewCommands": item.get("reviewCommands"),
            }
            for item in source_impact.get("impacts", [])
            if isinstance(item, dict)
        ]
        review_queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
        focus_entries = ranked_knowledge_review_queue_entries(knowledge_review_queue, limit=6)
        status = "stale_knowledge_pending" if review_queue_summary.get("hasPendingReviews") else "knowledge_ready"
        recommendations = [
            knowledge_review_queue_recommendation(item)
            for item in focus_entries
        ]
        recommendations = prioritize_action_entries(
            recommendations,
            execution_state=status,
            resume_status=None,
            worknet_key=None,
        )
        changed_sources_display = knowledge_display_changed_sources(changed_sources, source_records=source_records)
        impacts_display = knowledge_display_source_impact(
            {"affected": bool(impacts), "items": impacts},
            catalog=catalog,
        )
        review_queue_top_entries_display = knowledge_display_review_queue_entries(
            focus_entries,
            catalog=catalog,
        )
        citations: list[dict[str, Any]] = []
        for item in changed_sources:
            source_key = str(item.get("key") or "").strip()
            source_record = source_records.get(source_key, {})
            citations.append(
                {
                    "sourceKey": source_key,
                    "sourceName": item.get("name"),
                    "url": source_record.get("url"),
                    "kind": source_record.get("kind"),
                    "status": item.get("status"),
                    "changedFields": item.get("changedFields", []),
                    "note": item.get("note"),
                }
            )
        primary_command = None
        if recommendations and isinstance(recommendations[0].get("command"), str) and recommendations[0].get("command"):
            primary_command = recommendations[0]["command"]
        elif isinstance(review_queue_summary.get("primaryActionCommand"), str) and review_queue_summary.get("primaryActionCommand"):
            primary_command = review_queue_summary["primaryActionCommand"]
        action_map = {
            str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
            for item in recommendations
            if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
        }
        user_action_details = action_details_from_ui_actions(recommendations, action_map)
        refresh_label = str(review_queue_summary.get("refreshActionLabel") or "").strip()
        refresh_command = str(review_queue_summary.get("refreshActionCommand") or "").strip()
        if refresh_label and refresh_command:
            append_unique_action_detail(
                user_action_details,
                label=refresh_label,
                description="重新刷新官方来源，再重建这份知识待重审队列。",
                command=refresh_command,
            )
        current_labels: list[str] = []
        source_labels: list[str] = []
        topic_labels: list[str] = []
        control_labels: list[str] = []
        for index, item in enumerate(user_action_details):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            if index == 0:
                current_labels.append(label)
            elif label.startswith("重读来源 ") or label.startswith("查看来源 "):
                source_labels.append(label)
            elif label.startswith("重审主题 ") or label.startswith("查看主题 ") or label.startswith("重审 "):
                topic_labels.append(label)
            elif label in {refresh_label, "查看知识待重审队列"}:
                control_labels.append(label)
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=[],
            reference_labels=[],
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="queued",
        )
        execution_payload = execution_state_payload(
            status,
            headline=str(review_queue_summary.get("headline") or "当前没有待重审的知识条目。"),
        )
        research_action_groups = build_research_action_groups(
            user_action_details,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=[],
            reference_labels=[],
            control_first=False,
        )
        recommendations = annotate_research_action_details(
            recommendations,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=[],
            reference_labels=[],
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="queued",
        )
        return normalize_query_payload({
            "topic": topic,
            "status": status,
            "progress": "[3/5] Knowledge Review Queue",
            "headline": str(review_queue_summary.get("headline") or "当前没有待重审的知识条目。"),
            "summary": knowledge_review_queue_summary_text(review_queue_summary),
            "executionState": execution_payload.get("executionState"),
            "executionStateDisplay": execution_payload.get("executionStateDisplay"),
            "executionHeadline": execution_payload.get("executionHeadline"),
            "primaryCommand": primary_command,
            "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
            "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
            "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
            "userActionDetails": user_action_details,
            "researchActionGroups": research_action_groups,
            "recommendations": recommendations,
            "citations": citations,
            "reviewQueueSummary": review_queue_summary,
            "reviewQueueTopEntries": focus_entries,
            "reviewQueueTopEntriesDisplay": review_queue_top_entries_display,
            "sourceDriftSummary": source_drift.get("summary"),
            "sourceImpactSummary": source_impact.get("summary"),
            "changedSources": changed_sources,
            "changedSourcesDisplay": changed_sources_display,
            "impacts": impacts,
            "impactsDisplay": impacts_display,
            "reviewQueue": source_impact.get("reviewQueue"),
            "knowledgeReviewQueue": knowledge_review_queue,
        }, KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS)

    dossiers = catalog.get("topicDossiers", []) if isinstance(catalog.get("topicDossiers"), list) else []
    source_facts = list(catalog.get("sourceFacts", []))
    source_evidence = list(catalog.get("sourceEvidence", []))
    glossary_terms = list(catalog.get("glossary", []))
    worknets = catalog.get("worknets", []) if isinstance(catalog.get("worknets"), list) else []

    dossier = next((item for item in dossiers if item.get("key") == topic), None)
    source_fact = next((item for item in source_facts if item.get("key") == topic), None)
    worknet = next((item for item in worknets if item.get("key") == topic), None)
    if source_fact is None:
        related_source_keys: set[str] = set()
        if isinstance(dossier, dict) and dossier.get("sourceKeys"):
            related_source_keys.update(dossier["sourceKeys"])
        if isinstance(worknet, dict) and worknet.get("sourceKeys"):
            related_source_keys.update(worknet["sourceKeys"])
        ranked: list[tuple[int, dict[str, Any]]] = []
        for item in source_facts:
            score = 0
            key = str(item.get("key", "")).strip().lower()
            fact_topic = str(item.get("topic", "")).strip().lower()
            keys = set(item.get("sourceKeys", []))
            if key == topic:
                score += 100
            if topic in key:
                score += 50
            if topic == fact_topic:
                score += 40
            if topic in fact_topic:
                score += 20
            score += 5 * len(related_source_keys.intersection(keys))
            if score > 0:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        source_fact = ranked[0][1] if ranked else None

    ranked_evidence: list[tuple[int, dict[str, Any]]] = []
    related_source_keys: set[str] = set()
    if isinstance(dossier, dict) and dossier.get("sourceKeys"):
        related_source_keys.update(dossier["sourceKeys"])
    if isinstance(worknet, dict) and worknet.get("sourceKeys"):
        related_source_keys.update(worknet["sourceKeys"])
    if isinstance(source_fact, dict) and source_fact.get("sourceKeys"):
        related_source_keys.update(source_fact["sourceKeys"])
    for item in source_evidence:
        score = 0
        if item.get("topicKey") == topic:
            score += 100
        source_key = item.get("sourceKey")
        item_source_keys = source_key if isinstance(source_key, list) else [source_key]
        overlap = related_source_keys.intersection(item_source_keys)
        score += 10 * len(overlap)
        if score > 0:
            ranked_evidence.append((score, item))
    ranked_evidence.sort(key=lambda pair: pair[0], reverse=True)
    evidence_matches = [item for _, item in ranked_evidence]

    glossary_match = next(
        (
            item
            for item in glossary_terms
            if topic == str(item.get("term", "")).strip().lower()
            or topic in {str(alias).strip().lower() for alias in item.get("aliases", [])}
        ),
        None,
    )

    if isinstance(glossary_match, dict):
        related_topics = [str(item).strip().lower() for item in glossary_match.get("relatedTopics", [])]
        if dossier is None:
            dossier = next((item for item in dossiers if item.get("key") in related_topics), dossier)
        if worknet is None:
            worknet = next((item for item in worknets if item.get("key") in related_topics), worknet)
        ranked_source_facts: list[tuple[int, dict[str, Any]]] = []
        for item in source_facts:
            score = 0
            key = str(item.get("key", "")).strip().lower()
            fact_topic = str(item.get("topic", "")).strip().lower()
            item_source_keys = {str(source_key).strip().lower() for source_key in item.get("sourceKeys", [])}
            if key in related_topics:
                score += 100
            score += 30 * sum(1 for rel in related_topics if rel in fact_topic)
            score += 5 * sum(1 for rel in related_topics if rel in item_source_keys)
            if score > 0:
                ranked_source_facts.append((score, item))
        ranked_source_facts.sort(key=lambda pair: pair[0], reverse=True)
        if ranked_source_facts:
            source_fact = ranked_source_facts[0][1]

    related_topic_keys = {topic}
    related_source_keys = set()
    if isinstance(glossary_match, dict):
        related_topic_keys.update(str(item).strip().lower() for item in glossary_match.get("relatedTopics", []))
        related_source_keys.update(glossary_match.get("sourceKeys", []))
    if isinstance(dossier, dict):
        related_topic_keys.add(str(dossier.get("key", "")).strip().lower())
        related_source_keys.update(dossier.get("sourceKeys", []))
    if isinstance(source_fact, dict):
        related_topic_keys.add(str(source_fact.get("key", "")).strip().lower())
        related_source_keys.update(source_fact.get("sourceKeys", []))
    if isinstance(worknet, dict):
        related_topic_keys.add(str(worknet.get("key", "")).strip().lower())
        related_source_keys.update(worknet.get("sourceKeys", []))

    impact_matches: list[dict[str, Any]] = []
    for item in source_impact.get("impacts", []):
        if not isinstance(item, dict):
            continue
        impacted_topics = {
            str(entry.get("key", "")).strip().lower()
            for entry in item.get("impactedTopics", [])
            if isinstance(entry, dict) and entry.get("key")
        }
        impacted_facts = {
            str(entry.get("key", "")).strip().lower()
            for entry in item.get("impactedFacts", [])
            if isinstance(entry, dict) and entry.get("key")
        }
        impacted_worknets = {
            str(entry).strip().lower()
            for entry in item.get("impactedWorknets", [])
            if str(entry).strip()
        }
        source_key = str(item.get("sourceKey", "")).strip()
        if (
            impacted_topics.intersection(related_topic_keys)
            or impacted_facts.intersection(related_topic_keys)
            or impacted_worknets.intersection(related_topic_keys)
            or source_key in related_source_keys
        ):
            impact_matches.append(
                {
                    "sourceKey": item.get("sourceKey"),
                    "sourceName": item.get("sourceName"),
                    "priority": item.get("priority"),
                    "driftStatus": item.get("driftStatus"),
                    "reviewHint": item.get("reviewHint"),
                    "reviewCommands": item.get("reviewCommands"),
                }
            )

    freshness_matches: list[dict[str, Any]] = []
    for bucket in ("topics", "facts", "worknets"):
        for item in topic_freshness_catalog.get(bucket, []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip().lower()
            if key in related_topic_keys:
                freshness_matches.append(item)
    freshness_status = "stable"
    highest_priority = "low"
    for item in freshness_matches:
        if item.get("status") == "affected":
            freshness_status = "affected"
        priority = str(item.get("highestPriority") or "low")
        if KNOWLEDGE_QUEUE_PRIORITY_RANK.get(priority, 0) > KNOWLEDGE_QUEUE_PRIORITY_RANK.get(highest_priority, 0):
            highest_priority = priority

    source_records: dict[str, dict[str, Any]] = {}
    sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item

    worknet_context = knowledge_topic_worknet_context(topic, dossier=dossier, worknet=worknet)
    narrative = canonical_topic_narrative(
        topic,
        dossier_key=str(dossier.get("key") or "") if isinstance(dossier, dict) else None,
        worknet_key=str(worknet_context.get("key") or "") if isinstance(worknet_context, dict) else None,
        glossary_term=str(glossary_match.get("term") or "") if isinstance(glossary_match, dict) else None,
    )
    label = knowledge_display_topic_label(
        topic,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
    )
    capability_reports = capability_reports_by_worknet_key()
    capability_report = None
    if isinstance(worknet_context, dict) and str(worknet_context.get("key") or "").strip():
        capability_report = capability_reports.get(str(worknet_context.get("key") or "").strip())
    freshness = {"status": freshness_status, "highestPriority": highest_priority, "items": freshness_matches}
    summary = knowledge_topic_summary(
        label,
        narrative=narrative,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
        freshness=freshness,
    )
    topic_execution_state = knowledge_topic_execution_state(
        label=label,
        affected=freshness_status == "affected",
        capability_report=capability_report if isinstance(capability_report, dict) else None,
    )
    recommendations = knowledge_topic_recommendations(
        topic,
        label,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
        capability_report=capability_report,
        freshness=freshness,
        impact_matches=impact_matches,
    )
    status = "knowledge_review_needed" if freshness_status == "affected" else "knowledge_ready"
    citations = knowledge_topic_citations(
        evidence_matches,
        source_records=source_records,
        dossier=dossier,
    )
    evidence_display, evidence_display_index = knowledge_display_evidence(evidence_matches)
    citations_display = knowledge_display_citations(
        citations,
        evidence_display_index=evidence_display_index,
    )
    runtime_probe_display = knowledge_runtime_probe_display_for_topic(
        topic=topic,
        catalog=catalog,
        worknet_context=worknet_context,
        capability_report=capability_report,
    )
    runtime_probe_evidence = knowledge_runtime_probe_evidence_entries(
        runtime_probe_display,
        topic_key=str(worknet_context.get("key") or topic).strip() if isinstance(worknet_context, dict) else str(topic).strip() or None,
    )
    evidence_display = [*runtime_probe_evidence, *evidence_display]
    primary_command = None
    if recommendations and isinstance(recommendations[0].get("command"), str) and recommendations[0].get("command"):
        primary_command = recommendations[0]["command"]
    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in recommendations
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    user_action_details = action_details_from_ui_actions(recommendations, action_map)
    current_action_labels: list[str] = []
    worknet_action_labels: list[str] = []
    for index, item in enumerate(user_action_details):
        if not isinstance(item, dict):
            continue
        label_text = str(item.get("label") or "").strip()
        if not label_text:
            continue
        if index == 0 or label_text.startswith("刷新 ") or label_text.startswith("重审 "):
            current_action_labels.append(label_text)
        else:
            worknet_action_labels.append(label_text)

    plain_language = knowledge_topic_plain_language(
        narrative=narrative,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
    )
    queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
    topic_directory = catalog.get("topicDirectory", []) if isinstance(catalog.get("topicDirectory"), list) else []
    current_context = find_topic_directory_entry(
        topic_directory,
        key=str(knowledge_resolved_topic_key(
            topic,
            glossary_match=glossary_match,
            dossier=dossier,
            worknet=worknet_context,
        ) or "").strip(),
        worknet_key=str(worknet_context.get("key") or "").strip() if isinstance(worknet_context, dict) else None,
    )
    if not isinstance(current_context, dict):
        current_context = {
            "key": knowledge_resolved_topic_key(
                topic,
                glossary_match=glossary_match,
                dossier=dossier,
                worknet=worknet_context,
            ),
            "label": label,
            "summary": summary,
            "summaryPreview": compact_preview_text(
                plain_language or summary,
                max_chars=140,
                max_sentences=2,
            ),
            "headline": knowledge_topic_headline(label, freshness),
            "queryCommand": query_knowledge_command(
                str(
                    knowledge_resolved_topic_key(
                        topic,
                        glossary_match=glossary_match,
                        dossier=dossier,
                        worknet=worknet_context,
                    )
                    or topic
                ).strip()
            ),
            "primaryCommand": primary_command,
            "freshnessStatus": freshness_status,
            "sourceKeys": list(related_source_keys),
            "worknetKey": worknet_context.get("key") if isinstance(worknet_context, dict) else None,
        }
    related_source_highlights = knowledge_related_source_highlights(
        catalog,
        current_context,
        limit=3,
    )
    related_reference_highlights = knowledge_related_reference_highlights(
        catalog,
        current_context,
        limit=2,
    )
    source_action_labels: list[str] = []
    for item in related_source_highlights[:2]:
        if not isinstance(item, dict):
            continue
        source_label = str(item.get("label") or item.get("key") or "").strip()
        command = str(item.get("queryCommand") or "").strip()
        if not source_label or not command:
            continue
        label_text = f"查看来源 {source_label}"
        source_action_labels.append(label_text)
        append_unique_action_detail(
            user_action_details,
            label=label_text,
            description=knowledge_source_action_description(item),
            command=command,
        )
    reference_action_labels: list[str] = []
    for item in related_reference_highlights[:2]:
        if not isinstance(item, dict):
            continue
        reference_label = str(item.get("label") or item.get("key") or "").strip()
        command = str(item.get("queryCommand") or "").strip()
        if not reference_label or not command:
            continue
        label_text = f"查看参考 {reference_label}"
        reference_action_labels.append(label_text)
        append_unique_action_detail(
            user_action_details,
            label=label_text,
            description="如果你要追底层规则、运行时约束或协议细节，就直接看这条参考条目。",
            command=command,
        )
    control_action_labels: list[str] = []
    queue_label = str(queue_summary.get("primaryActionLabel") or "").strip()
    queue_command = str(queue_summary.get("primaryActionCommand") or "").strip()
    if queue_summary.get("hasPendingReviews") and queue_label and queue_command:
        control_action_labels.append(queue_label)
        append_unique_action_detail(
            user_action_details,
            label=queue_label,
            description="查看最近哪些官方资料发生变化，以及哪些知识条目需要重审。",
            command=queue_command,
        )
    research_action_groups = build_research_action_groups(
        user_action_details,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=[],
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        control_first=False,
    )
    recommendations = annotate_research_action_details(
        recommendations,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=[],
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        current_tier="current",
        control_tier="queued",
        source_tier="related",
        worknet_tier="related",
        reference_tier="related",
    )
    user_action_details = annotate_research_action_details(
        user_action_details,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=[],
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        current_tier="current",
        control_tier="queued",
        source_tier="related",
        worknet_tier="related",
        reference_tier="related",
    )
    user_action_details = frontload_user_action_labels(
        user_action_details,
        [
            *current_action_labels,
            *source_action_labels,
            *worknet_action_labels,
            *control_action_labels,
            *reference_action_labels,
        ],
    )

    return normalize_query_payload({
        "topic": topic,
        "status": status,
        "resolvedTopicKey": knowledge_resolved_topic_key(
            topic,
            glossary_match=glossary_match,
            dossier=dossier,
            worknet=worknet_context,
        ),
        "resolvedTopicLabel": label,
        "progress": "[2/5] Knowledge Query",
        "headline": knowledge_topic_headline(label, freshness),
        "summary": summary,
        "plainLanguage": plain_language,
        "executionState": topic_execution_state.get("executionState"),
        "executionStateDisplay": topic_execution_state.get("executionStateDisplay"),
        "executionHeadline": topic_execution_state.get("executionHeadline"),
        "primaryCommand": primary_command,
        "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "userActionDetails": user_action_details,
        "researchActionGroups": research_action_groups,
        "recommendations": recommendations,
        "citations": citations,
        "citationsDisplay": citations_display,
        "glossary": glossary_match,
        "dossier": dossier,
        "dossierDisplay": knowledge_display_dossier(
            dossier,
            summary=summary,
            why=(narrative or {}).get("why") if isinstance(narrative, dict) else None,
        ),
        "sourceFact": source_fact,
        "sourceFactDisplay": knowledge_display_source_fact(
            source_fact,
            summary=summary,
            runtime_probe_display=runtime_probe_display,
        ),
        "evidence": evidence_matches,
        "evidenceDisplay": evidence_display,
        "worknet": worknet,
        "worknetDisplay": knowledge_display_worknet(
            worknet,
            capability_report=capability_report if isinstance(capability_report, dict) else None,
            runtime_probe_display=runtime_probe_display,
        ),
        "runtimeProbeDisplay": runtime_probe_display,
        "runtimeProbeHighlights": runtime_probe_display.get("highlights", []) if isinstance(runtime_probe_display, dict) else [],
        "sourceImpact": {
            "affected": bool(impact_matches),
            "items": impact_matches,
        },
        "sourceImpactDisplay": knowledge_display_source_impact({
            "affected": bool(impact_matches),
            "items": impact_matches,
        }, catalog=catalog),
        "freshness": freshness,
        "freshnessDisplay": knowledge_display_freshness(freshness),
        "relatedSourceHighlights": related_source_highlights,
        "relatedReferenceHighlights": related_reference_highlights,
    }, KNOWLEDGE_QUERY_FIELDS)


def knowledge_display_glossary_items(items: Any) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        rendered.append(
            normalize_glossary_item_payload({
                "term": item.get("term"),
                "aliases": item.get("aliases", []),
                "plainLanguage": item.get("plainLanguage"),
                "definition": item.get("definition"),
                "whyItMatters": item.get("whyItMatters"),
                "relatedTopics": item.get("relatedTopics", []),
            })
        )
    return rendered


def build_source_query_result(
    source_key: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    source_key = str(source_key or "").strip()
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    source_records: dict[str, dict[str, Any]] = {}
    sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
    capability_reports = capability_reports_by_worknet_key()
    source_record = source_records.get(source_key)
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
    facts = [item for item in catalog.get("sourceFacts", []) if source_key in item.get("sourceKeys", [])]
    evidence = [item for item in catalog.get("sourceEvidence", []) if item.get("sourceKey") == source_key]
    dossiers = [item for item in catalog.get("topicDossiers", []) if source_key in item.get("sourceKeys", [])]
    glossary = [item for item in catalog.get("glossary", []) if source_key in item.get("sourceKeys", [])]
    worknets = [item for item in catalog.get("worknets", []) if source_key in item.get("sourceKeys", [])]
    topic_cache: dict[str, dict[str, Any]] = {}

    def topic_result(topic_key: Any) -> Optional[dict[str, Any]]:
        normalized = str(topic_key or "").strip()
        if not normalized:
            return None
        if normalized not in topic_cache:
            topic_cache[normalized] = build_knowledge_query_result(normalized, catalog=catalog)
        return topic_cache[normalized]

    facts_display: list[dict[str, Any]] = []
    for item in facts:
        result = topic_result(item.get("key"))
        if isinstance(result, dict) and isinstance(result.get("sourceFactDisplay"), dict):
            facts_display.append(result["sourceFactDisplay"])
    dossiers_display: list[dict[str, Any]] = []
    for item in dossiers:
        result = topic_result(item.get("key"))
        if isinstance(result, dict) and isinstance(result.get("dossierDisplay"), dict):
            dossiers_display.append(result["dossierDisplay"])
    worknets_display: list[dict[str, Any]] = []
    for item in worknets:
        worknet_key = str(item.get("key") or "").strip()
        rendered = knowledge_display_worknet(
            item,
            capability_report=capability_reports.get(worknet_key) if worknet_key else None,
            runtime_probe_display=knowledge_runtime_probe_display(
                capability_reports.get(worknet_key, {}).get("skillInspection"),
                skill_key=worknet_key,
            ) if worknet_key and isinstance(capability_reports.get(worknet_key), dict) else None,
        )
        if isinstance(rendered, dict):
            worknets_display.append(rendered)
    evidence_display, evidence_display_index = knowledge_display_evidence(evidence)
    drift_display = knowledge_display_drift_item(
        drift_item,
        source_record=source_record,
    )
    impact_display = knowledge_display_source_impact(
        {"affected": bool(impact_item), "items": [impact_item] if isinstance(impact_item, dict) else []},
        catalog=catalog,
    )
    source_runtime_probe_display = knowledge_runtime_probe_display_for_source(
        source_key=source_key,
        source_record=source_record,
        catalog=catalog,
        capability_report=capability_reports.get(str(source_record.get("worknetKey") or "").strip()) if isinstance(source_record, dict) and str(source_record.get("worknetKey") or "").strip() else None,
    )
    runtime_probe_evidence = knowledge_runtime_probe_evidence_entries(
        source_runtime_probe_display,
        topic_key=str(source_record.get("worknetKey") or "").strip() if isinstance(source_record, dict) else None,
    )
    evidence_display = [*runtime_probe_evidence, *evidence_display]
    source_display = knowledge_display_source_record(
        source_record,
        drift_item=drift_item,
        impact_item=impact_item,
        runtime_probe_display=source_runtime_probe_display,
    )
    if isinstance(source_display, dict):
        source_display = dict(source_display)
        source_display["summaryPreview"] = compact_preview_text(
            source_display.get("summaryDisplay") or source_display.get("summary"),
            max_chars=140,
            max_sentences=2,
        )
    headline = None
    if isinstance(source_display, dict):
        headline = source_display.get("headline")
    if not headline:
        name_display = humanize_knowledge_source_label(source_key)
        headline = f"{name_display} 当前资料可直接参考。"
    summary_parts: list[str] = []
    if source_record is None:
        headline = f"当前还没有找到来源 {source_key}。"
        summary_parts.append("这条来源键还没进入本地百科目录，先检查来源键是否写对，或者先刷新总目录。")
    if isinstance(source_display, dict) and isinstance(source_display.get("summaryDisplay"), str):
        summary_parts.append(str(source_display["summaryDisplay"]).strip())
    if isinstance(drift_display, dict) and drift_display.get("statusDisplay"):
        changed_fields = drift_display.get("changedFieldsDisplay", [])
        drift_sentence = f"当前漂移状态是 {drift_display['statusDisplay']}。"
        if changed_fields:
            drift_sentence += f" 变化字段包括 {'、'.join(changed_fields)}。"
        if drift_display.get("note"):
            drift_sentence += f" {str(drift_display['note']).strip()}"
        summary_parts.append(drift_sentence.strip())
    if isinstance(impact_display, dict) and isinstance(impact_display.get("summary"), str):
        summary_parts.append(str(impact_display["summary"]).strip())
    if not summary_parts:
        summary_parts.append("当前没有发现这条来源的特别说明。")
    summary_text = " ".join(part for part in summary_parts if part).strip()
    summary_preview = (
        source_display.get("summaryPreview")
        if isinstance(source_display, dict)
        else None
    ) or compact_preview_text(summary_text, max_chars=160, max_sentences=2)
    recommendations: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    def add_recommendation(label: str, description: str, command: Optional[str]) -> None:
        resolved_label = str(label or "").strip()
        resolved_command = str(command or "").strip()
        if not resolved_label or not resolved_command or resolved_label in seen_labels:
            return
        seen_labels.add(resolved_label)
        recommendations.append(
            {
                "label": resolved_label,
                "description": description,
                "command": resolved_command,
            }
        )

    add_recommendation(
        f"重读来源 {humanize_knowledge_source_label(source_record.get('name') if isinstance(source_record, dict) else source_key)}",
        "重新拉取这条官方来源，确认上游变化有没有影响本地知识。",
        query_source_command(source_key, rebuild=True),
    )
    if isinstance(impact_item, dict):
        for topic in impact_item.get("impactedTopics", [])[:3]:
            topic_key = str(topic.get("key") if isinstance(topic, dict) else topic).strip()
            topic_label = str(topic.get("title") if isinstance(topic, dict) else "").strip()
            result = topic_result(topic_key)
            if isinstance(result, dict):
                topic_label = str(result.get("resolvedTopicLabel") or topic_label or topic_key).strip()
            add_recommendation(
                f"查看主题 {topic_label}",
                "直接看这条来源当前影响到的高层主题。",
                query_knowledge_command(topic_key),
            )
    add_recommendation(
        "查看知识待重审队列",
        "回到所有待重审来源、主题和事实的总队列。",
        query_knowledge_command("review-queue"),
    )
    review_needed = bool(
        source_record
        and (
            (
                isinstance(drift_display, dict)
                and str(drift_display.get("status") or "").strip()
                and str(drift_display.get("status") or "").strip() not in {"unchanged", "no-baseline"}
            )
            or (isinstance(impact_display, dict) and impact_display.get("affected"))
        )
    )
    status = "source_missing"
    if source_record is not None:
        status = "source_review_needed" if review_needed else "source_ready"
    execution_payload = execution_state_payload(status, headline=headline)
    recommendations = prioritize_action_entries(
        recommendations,
        execution_state=status,
        resume_status=None,
        worknet_key=str(source_record.get("worknetKey") or "").strip() if isinstance(source_record, dict) else None,
    )
    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in recommendations
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    user_action_details = action_details_from_ui_actions(recommendations, action_map)

    topic_highlights: list[dict[str, Any]] = []
    seen_topic_keys: set[str] = set()
    topic_candidates = []
    if isinstance(impact_item, dict) and isinstance(impact_item.get("impactedTopics"), list):
        topic_candidates.extend(impact_item.get("impactedTopics", []))
    topic_candidates.extend(dossiers)
    for item in topic_candidates:
        if isinstance(item, dict):
            topic_key = str(item.get("key") or "").strip()
        else:
            topic_key = str(item or "").strip()
        if not topic_key or topic_key in seen_topic_keys:
            continue
        seen_topic_keys.add(topic_key)
        result = topic_result(topic_key)
        if not isinstance(result, dict):
            continue
        freshness_display = result.get("freshnessDisplay", {}) if isinstance(result.get("freshnessDisplay"), dict) else {}
        topic_highlights.append(
            build_normalized_knowledge_highlight(
                kind="topic",
                key=str(result.get("resolvedTopicKey") or topic_key).strip(),
                label=str(result.get("resolvedTopicLabel") or topic_key).strip(),
                headline=result.get("headline"),
                preview=result.get("plainLanguage") or result.get("summary"),
                query_command=query_knowledge_command(str(result.get("resolvedTopicKey") or topic_key).strip()),
                primary_command=result.get("primaryCommand"),
                freshness_status=freshness_display.get("status"),
                research_tier="related",
                extra={
                    "summary": compact_preview_text(
                        result.get("plainLanguage") or result.get("summary"),
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "summaryPreview": compact_preview_text(
                        result.get("plainLanguage") or result.get("summary"),
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "summaryFull": result.get("summary"),
                    "status": freshness_display.get("status"),
                    "statusDisplay": freshness_display.get("statusDisplay"),
                },
            )
        )

    fact_highlights: list[dict[str, Any]] = []
    for item in facts_display:
        if not isinstance(item, dict):
            continue
        fact_key = str(item.get("key") or "").strip()
        fact_result = topic_result(fact_key) if fact_key else None
        fact_freshness_display = (
            fact_result.get("freshnessDisplay", {})
            if isinstance(fact_result, dict) and isinstance(fact_result.get("freshnessDisplay"), dict)
            else {}
        )
        fact_runtime_summary = str(item.get("runtimeSummary") or "").strip() or None
        if not fact_runtime_summary:
            source_keys = [str(value).strip() for value in item.get("sourceKeys", []) if str(value).strip()]
            if source_key in source_keys:
                fact_runtime_summary = knowledge_runtime_probe_summary_sentence(source_runtime_probe_display)
        fact_summary_full = join_product_sentences(
            [
                item.get("summary"),
                fact_runtime_summary,
            ]
        ) or item.get("summary")
        fact_preview_text = join_product_sentences(
            [
                compact_preview_text(
                    " ".join(str(entry).strip() for entry in item.get("facts", [])[:2] if str(entry).strip()),
                    max_chars=160,
                    max_sentences=2,
                ),
                fact_runtime_summary,
            ]
        ) or fact_summary_full
        fact_highlights.append(
            build_normalized_knowledge_highlight(
                kind="fact",
                key=fact_key,
                label=item.get("topic") or fact_key,
                headline=(fact_result or {}).get("headline") if isinstance(fact_result, dict) else None,
                preview=fact_preview_text,
                query_command=query_knowledge_command(fact_key) if fact_key else None,
                primary_command=(fact_result or {}).get("primaryCommand") if isinstance(fact_result, dict) else None,
                freshness_status=fact_freshness_display.get("status"),
                research_tier="related",
                extra={
                    "topic": item.get("topic"),
                    "summary": compact_preview_text(
                        fact_summary_full,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "summaryPreview": compact_preview_text(
                        fact_summary_full,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "summaryFull": fact_summary_full,
                    "factsPreview": fact_preview_text,
                    "factCount": len(item.get("facts", [])) if isinstance(item.get("facts"), list) else 0,
                    "runtimeSummary": fact_runtime_summary,
                    "runtimeProbeCount": item.get("runtimeProbeCount") or (knowledge_runtime_probe_count(source_runtime_probe_display) or None),
                },
            )
        )

    worknet_highlights: list[dict[str, Any]] = []
    for item in worknets_display:
        if not isinstance(item, dict):
            continue
        worknet_key = str(item.get("key") or "").strip()
        worknet_result = topic_result(worknet_key) if worknet_key else None
        worknet_freshness_display = (
            worknet_result.get("freshnessDisplay", {})
            if isinstance(worknet_result, dict) and isinstance(worknet_result.get("freshnessDisplay"), dict)
            else {}
        )
        worknet_preview_text = join_product_sentences(
            [
                item.get("goalDisplay") or item.get("goal"),
                item.get("runtimeSummary"),
            ]
        ) or item.get("goalDisplay") or item.get("goal")
        worknet_highlights.append(
            build_normalized_knowledge_highlight(
                kind="worknet",
                key=worknet_key,
                label=item.get("name") or worknet_key,
                headline=(worknet_result or {}).get("headline") if isinstance(worknet_result, dict) else None,
                preview=worknet_preview_text,
                query_command=query_knowledge_command(worknet_key) if worknet_key else None,
                primary_command=(worknet_result or {}).get("primaryCommand") if isinstance(worknet_result, dict) else None,
                freshness_status=worknet_freshness_display.get("status"),
                research_tier="related",
                extra={
                    "name": item.get("name"),
                    "goal": compact_preview_text(
                        worknet_preview_text,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "goalPreview": compact_preview_text(
                        worknet_preview_text,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "goalFull": worknet_preview_text,
                    "cautionPreview": compact_preview_text(
                        item.get("cautionDisplay"),
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "statusDisplay": item.get("statusDisplay"),
                    "riskLevelDisplay": item.get("riskLevelDisplay"),
                    "recommendedRoleDisplay": item.get("recommendedRoleDisplay"),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
        )

    evidence_highlights: list[dict[str, Any]] = []
    for item in evidence_display[:5]:
        if not isinstance(item, dict):
            continue
        evidence_topic_key = str(item.get("topicKey") or "").strip()
        evidence_preview = str(item.get("previewDisplay") or item.get("claimDisplay") or "").strip()
        evidence_highlights.append(
            build_normalized_knowledge_highlight(
                kind="evidence",
                key=item.get("key"),
                label=item.get("label") or item.get("sourceNameDisplay") or item.get("key"),
                headline=None,
                preview=evidence_preview,
                query_command=query_knowledge_command(evidence_topic_key) if evidence_topic_key else None,
                primary_command=None,
                freshness_status="affected" if review_needed else "stable",
                research_tier="related",
                extra={
                    "claim": compact_preview_text(
                        evidence_preview,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "claimPreview": compact_preview_text(
                        evidence_preview,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "claimFull": item.get("claimDisplay"),
                    "claimDisplay": item.get("claimDisplay"),
                    "previewDisplay": item.get("previewDisplay"),
                    "locatorDisplay": item.get("locatorDisplay"),
                    "commandDisplay": item.get("commandDisplay"),
                    "stabilityDisplay": item.get("stabilityDisplay"),
                    "topicKey": evidence_topic_key or None,
                },
            )
        )
    for item in worknet_highlights[:2]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        command = str(item.get("queryCommand") or "").strip()
        if not label or not command:
            continue
        append_unique_action_detail(
            user_action_details,
            label=f"查看工作网 {label}",
            description=knowledge_action_description(item),
            command=command,
        )

    current_labels: list[str] = []
    topic_labels: list[str] = []
    worknet_labels: list[str] = []
    control_labels: list[str] = []
    for index, item in enumerate(user_action_details):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        if index == 0:
            current_labels.append(label)
        elif label.startswith("查看主题 "):
            topic_labels.append(label)
        elif label.startswith("查看工作网 "):
            worknet_labels.append(label)
        elif label in {"查看知识待重审队列", "刷新知识待重审队列"}:
            control_labels.append(label)
    user_action_details = annotate_research_action_details(
        user_action_details,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=[],
        topic_labels=topic_labels,
        worknet_labels=worknet_labels,
        reference_labels=[],
        current_tier="current",
        control_tier="queued",
        topic_tier="related",
        worknet_tier="related",
    )

    research_action_groups = build_research_action_groups(
        user_action_details,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=[],
        topic_labels=topic_labels,
        worknet_labels=worknet_labels,
        reference_labels=[],
        control_first=False,
    )
    recommendations = annotate_research_action_details(
        recommendations,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=[],
        topic_labels=topic_labels,
        worknet_labels=worknet_labels,
        reference_labels=[],
        current_tier="current",
        control_tier="queued",
        topic_tier="related",
        worknet_tier="related",
    )
    user_action_details = frontload_user_action_labels(
        user_action_details,
        [
            *current_labels,
            *topic_labels,
            *worknet_labels,
            *control_labels,
        ],
    )

    citations_display = knowledge_display_citations(
        [
            {
                "sourceKey": source_key,
                "sourceName": source_record.get("name") if isinstance(source_record, dict) else source_key,
                "url": source_record.get("url") if isinstance(source_record, dict) else None,
                "locator": None,
                "claim": None,
                "evidenceType": source_record.get("kind") if isinstance(source_record, dict) else None,
                "stability": None,
            }
        ],
        evidence_display_index=evidence_display_index,
    )
    return normalize_query_payload({
        "sourceKey": source_key,
        "sourceName": source_record.get("name") if isinstance(source_record, dict) else None,
        "sourceNameDisplay": source_display.get("nameDisplay") if isinstance(source_display, dict) else None,
        "status": status,
        "progress": "[1/5] Source Query",
        "headline": headline,
        "summary": summary_text,
        "summaryPreview": summary_preview,
        "summaryDisplay": source_display.get("summaryDisplay") if isinstance(source_display, dict) else None,
        "executionState": execution_payload.get("executionState"),
        "executionStateDisplay": execution_payload.get("executionStateDisplay"),
        "executionHeadline": execution_payload.get("executionHeadline"),
        "primaryCommand": query_source_command(source_key, rebuild=True),
        "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "userActionDetails": user_action_details,
        "researchActionGroups": research_action_groups,
        "recommendations": recommendations,
        "reviewScope": normalize_review_scope_payload({
            "topicCount": len(topic_highlights),
            "factCount": len(fact_highlights),
            "worknetCount": len(worknet_highlights),
            "evidenceCount": len(evidence_highlights),
        }),
        "topicHighlights": topic_highlights,
        "factHighlights": fact_highlights,
        "worknetHighlights": worknet_highlights,
        "evidenceHighlights": evidence_highlights,
        "source": source_record,
        "sourceDisplay": source_display,
        "drift": drift_item,
        "driftDisplay": drift_display,
        "impact": impact_item,
        "impactDisplay": impact_display,
        "facts": facts,
        "factsDisplay": facts_display,
        "evidence": evidence,
        "evidenceDisplay": evidence_display,
        "dossiers": dossiers,
        "dossiersDisplay": dossiers_display,
        "glossary": glossary,
        "glossaryDisplay": knowledge_display_glossary_items(glossary),
        "worknets": worknets,
        "worknetsDisplay": worknets_display,
        "runtimeProbeDisplay": source_runtime_probe_display,
        "runtimeProbeHighlights": source_runtime_probe_display.get("highlights", []) if isinstance(source_runtime_probe_display, dict) else [],
        "citationsDisplay": citations_display,
    }, SOURCE_QUERY_FIELDS)


def build_changed_sources_query_result(
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    knowledge_review_queue = catalog.get("knowledgeReviewQueue", {}) if isinstance(catalog.get("knowledgeReviewQueue"), dict) else {}
    if not knowledge_review_queue:
        knowledge_review_queue = load_cached_knowledge_review_queue() or build_knowledge_review_queue()
    source_records: dict[str, dict[str, Any]] = {}
    sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
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
            "changedFields": item.get("changedFields", []),
            "note": item.get("note"),
            "impactedTopics": [entry.get("key") for entry in item.get("impactedTopics", []) if isinstance(entry, dict)],
            "impactedFacts": [entry.get("key") for entry in item.get("impactedFacts", []) if isinstance(entry, dict)],
            "impactedWorknets": list(item.get("impactedWorknets", [])),
            "reviewHint": item.get("reviewHint"),
            "reviewCommands": item.get("reviewCommands"),
        }
        for item in source_impact.get("impacts", [])
        if isinstance(item, dict)
    ]
    queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
    top_entries = ranked_knowledge_review_queue_entries(knowledge_review_queue, limit=8)
    recommendations: list[dict[str, Any]] = []
    if isinstance(queue_summary.get("primaryActionLabel"), str) and isinstance(queue_summary.get("primaryActionCommand"), str):
        recommendations.append(
            {
                "label": str(queue_summary["primaryActionLabel"]).strip(),
                "description": "先看当前所有待重审来源、主题和事实的总队列。",
                "command": str(queue_summary["primaryActionCommand"]).strip(),
            }
        )
    if isinstance(queue_summary.get("refreshActionLabel"), str) and isinstance(queue_summary.get("refreshActionCommand"), str):
        recommendations.append(
            {
                "label": str(queue_summary["refreshActionLabel"]).strip(),
                "description": "重新刷新官方来源，再重建这份待重审队列。",
                "command": str(queue_summary["refreshActionCommand"]).strip(),
            }
        )
    for item in changed_items[:3]:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        label = humanize_knowledge_source_label(item.get("name") or key)
        if not key or not label:
            continue
        recommendations.append(
            {
                "label": f"查看来源 {label}",
                "description": "直接打开这条刚发生变化的来源档案。",
                "command": query_source_command(key),
            }
        )
    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in recommendations
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    user_action_details = action_details_from_ui_actions(recommendations, action_map)
    current_labels: list[str] = []
    source_labels: list[str] = []
    control_labels: list[str] = []
    for index, item in enumerate(user_action_details):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        if index == 0:
            current_labels.append(label)
        elif label.startswith("查看来源 "):
            source_labels.append(label)
        elif label in {
            str(queue_summary.get("refreshActionLabel") or "").strip(),
            str(queue_summary.get("primaryActionLabel") or "").strip(),
        }:
            control_labels.append(label)
    user_action_details = annotate_research_action_details(
        user_action_details,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=source_labels,
        topic_labels=[],
        worknet_labels=[],
        reference_labels=[],
        current_tier="current",
        control_tier="queued",
        source_tier="queued",
    )
    changed_source_highlights = [
        highlight
        for highlight in (
            changed_source_highlight_entry(item)
            for item in knowledge_display_changed_sources(changed_items, source_records=source_records)
        )
        if isinstance(highlight, dict)
    ]
    status = "source_review_needed" if changed_items else "source_ready"
    execution_payload = execution_state_payload(
        status,
        headline=str(queue_summary.get("headline") or "当前没有待重审的来源。"),
    )
    research_action_groups = build_research_action_groups(
        user_action_details,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=source_labels,
        topic_labels=[],
        worknet_labels=[],
        reference_labels=[],
        control_first=False,
    )
    recommendations = annotate_research_action_details(
        recommendations,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=source_labels,
        topic_labels=[],
        worknet_labels=[],
        reference_labels=[],
        current_tier="current",
        control_tier="queued",
        source_tier="queued",
    )
    user_action_details = frontload_user_action_labels(
        user_action_details,
        [
            *current_labels,
            *source_labels,
            *control_labels,
        ],
    )
    return normalize_query_payload({
        "query": "changed",
        "status": status,
        "progress": "[2/5] Source Drift",
        "headline": str(queue_summary.get("headline") or "当前没有待重审的来源。"),
        "summary": knowledge_review_queue_summary_text(queue_summary),
        "executionState": execution_payload.get("executionState"),
        "executionStateDisplay": execution_payload.get("executionStateDisplay"),
        "executionHeadline": execution_payload.get("executionHeadline"),
        "primaryCommand": queue_summary.get("primaryActionCommand"),
        "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "userActionDetails": user_action_details,
        "researchActionGroups": research_action_groups,
        "recommendations": recommendations,
        "sourceDriftSummary": source_drift.get("summary"),
        "sourceImpactSummary": source_impact.get("summary"),
        "changedSources": changed_items,
        "changedSourcesDisplay": knowledge_display_changed_sources(changed_items, source_records=source_records),
        "changedSourceHighlights": changed_source_highlights,
        "impacts": impacted,
        "impactsDisplay": knowledge_display_source_impact(
            {"affected": bool(impacted), "items": impacted},
            catalog=catalog,
        ),
        "reviewQueue": source_impact.get("reviewQueue"),
        "knowledgeReviewQueueSummary": queue_summary,
        "reviewQueueTopEntriesDisplay": knowledge_display_review_queue_entries(top_entries, catalog=catalog),
    }, CHANGED_SOURCES_QUERY_FIELDS)


def knowledge_catalog_topic_keys(catalog: Any) -> list[str]:
    if not isinstance(catalog, dict):
        return []
    ordered_keys: list[str] = []
    seen: set[str] = set()
    for bucket in ("topicDossiers", "sourceFacts", "worknets"):
        items = catalog.get(bucket, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            ordered_keys.append(key)
    return ordered_keys


def knowledge_index_surface_level(item: Any) -> str:
    if not isinstance(item, dict):
        return "reference"
    if str(item.get("kind") or "").strip() != "fact":
        return "topic"
    raw_key = str(item.get("rawKey") or item.get("key") or "").strip().lower()
    return "topic" if raw_key in KNOWLEDGE_DIRECTORY_FACT_KEYS else "reference"


def knowledge_directory_key_for_item(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    raw_key = str(item.get("rawKey") or item.get("key") or "").strip().lower()
    mapped = KNOWLEDGE_DIRECTORY_FACT_KEYS.get(raw_key)
    if mapped:
        return mapped
    canonical = str(item.get("canonicalTopicKey") or item.get("key") or "").strip().lower()
    return canonical


def build_knowledge_topic_index(catalog: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    capability_reports = capability_reports_by_worknet_key(bundle=load_cached_capability_bundle(state_context()))
    index: list[dict[str, Any]] = []
    for topic_key in knowledge_catalog_topic_keys(catalog):
        result = build_knowledge_query_result(topic_key, catalog=catalog)
        dossier = result.get("dossier") if isinstance(result.get("dossier"), dict) else {}
        source_fact = result.get("sourceFact") if isinstance(result.get("sourceFact"), dict) else {}
        worknet = result.get("worknet") if isinstance(result.get("worknet"), dict) else {}
        glossary = result.get("glossary") if isinstance(result.get("glossary"), dict) else {}
        freshness = result.get("freshness") if isinstance(result.get("freshness"), dict) else {}
        source_impact = result.get("sourceImpact") if isinstance(result.get("sourceImpact"), dict) else {}
        affected_source_keys: list[str] = []
        for item in source_impact.get("items", []):
            if not isinstance(item, dict):
                continue
            source_key = str(item.get("sourceKey") or "").strip()
            if source_key and source_key not in affected_source_keys:
                affected_source_keys.append(source_key)
        source_keys: list[str] = []
        for container in (dossier, source_fact, glossary, worknet):
            if not isinstance(container, dict):
                continue
            for source_key in container.get("sourceKeys", []):
                key = str(source_key).strip()
                if key and key not in source_keys:
                    source_keys.append(key)
        worknet_key = str(worknet.get("key") or "").strip()
        runtime_probe_display = (
            result.get("runtimeProbeDisplay")
            if isinstance(result.get("runtimeProbeDisplay"), dict)
            else knowledge_runtime_probe_display_from_catalog(
                catalog,
                source_keys=source_keys,
                worknet_key=worknet_key or None,
                capability_report=capability_reports.get(worknet_key) if worknet_key else None,
            )
        )
        runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
        summary_text = join_product_sentences(
            [
                result.get("summary"),
                runtime_summary,
            ]
        ) or result.get("summary")
        kind = knowledge_first_non_empty(
            dossier.get("kind"),
            ("worknet" if worknet else None),
            ("glossary" if glossary else None),
            ("fact" if source_fact else None),
            "topic",
        )
        index.append(
            {
                "key": result.get("resolvedTopicKey") or topic_key,
                "rawKey": topic_key,
                "canonicalTopicKey": result.get("resolvedTopicKey") or topic_key,
                "label": result.get("resolvedTopicLabel") or topic_key,
                "kind": kind,
                "headline": result.get("headline"),
                "summary": summary_text,
                "summaryPreview": knowledge_runtime_augmented_preview(
                    result.get("plainLanguage") or result.get("summary") or summary_text,
                    runtime_summary,
                    headline=result.get("headline"),
                    max_chars=140,
                    max_sentences=2,
                ),
                "plainLanguage": result.get("plainLanguage"),
                "runtimeSummary": runtime_summary,
                "runtimeProbeCount": knowledge_runtime_probe_count(runtime_probe_display) or None,
                "queryCommand": query_knowledge_command(topic_key),
                "primaryCommand": result.get("primaryCommand"),
                "freshnessStatus": freshness.get("status"),
                "highestPriority": freshness.get("highestPriority"),
                "affectedSourceKeys": affected_source_keys,
                "sourceKeys": source_keys,
                "officialUrls": dossier.get("officialUrls", []),
                "aliases": glossary.get("aliases", []),
                "worknetKey": worknet.get("key"),
                "worknetName": worknet.get("name"),
                "automationLevel": worknet.get("automationLevel"),
                "riskLevel": worknet.get("riskLevel"),
                "recommendedRole": worknet.get("recommendedRole"),
                "surfaceLevel": "topic" if str(kind) != "fact" else ("topic" if topic_key in KNOWLEDGE_DIRECTORY_FACT_KEYS else "reference"),
                "recommendations": [
                    {
                        "label": item.get("label"),
                        "command": item.get("command"),
                    }
                    for item in result.get("recommendations", [])[:3]
                    if isinstance(item, dict)
                ],
                "citations": result.get("citations", [])[:3] if isinstance(result.get("citations"), list) else [],
            }
        )
    return index


def build_knowledge_topic_directory(topic_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    directory: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in topic_index:
        if not isinstance(item, dict):
            continue
        if knowledge_index_surface_level(item) != "topic":
            continue
        directory_key = knowledge_directory_key_for_item(item)
        if not directory_key or directory_key in seen:
            continue
        seen.add(directory_key)
        normalized = dict(item)
        normalized["key"] = directory_key
        normalized["surfaceLevel"] = "topic"
        directory.append(normalized)
    return directory


def build_knowledge_reference_index(topic_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for item in topic_index:
        if not isinstance(item, dict):
            continue
        if knowledge_index_surface_level(item) != "reference":
            continue
        normalized = dict(item)
        normalized["surfaceLevel"] = "reference"
        references.append(normalized)
    return references


def knowledge_source_directory_sort_key(item: Any) -> tuple[int, int, int, int, str]:
    item = item if isinstance(item, dict) else {}
    freshness = str(item.get("freshnessStatus") or "").strip().lower()
    freshness_rank = {"affected": 0, "stable": 1, "unknown": 2}
    priority_rank = KNOWLEDGE_QUEUE_PRIORITY_RANK.get(str(item.get("highestPriority") or "low").strip().lower(), 0)
    core_source_rank = {
        "awp-skill": 0,
        "awp-live-query": 1,
        "awp-whitepaper": 2,
        "awp-home": 3,
        "awp-worknets": 4,
        "awp-aip": 5,
        "awp-blog": 6,
    }
    key = str(item.get("key") or "").strip()
    label = str(item.get("label") or key).strip().lower()
    return (
        freshness_rank.get(freshness, 3),
        -priority_rank,
        core_source_rank.get(key, 99),
        0 if str(item.get("worknetKey") or "").strip() else 1,
        label,
    )


def build_knowledge_source_directory(catalog: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    source_records = knowledge_source_records_from_catalog(catalog)
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    drift_by_source = {
        str(item.get("key") or "").strip(): item
        for item in source_drift.get("items", [])
        if isinstance(item, dict) and str(item.get("key") or "").strip()
    }
    impact_by_source = {
        str(item.get("sourceKey") or "").strip(): item
        for item in source_impact.get("impacts", [])
        if isinstance(item, dict) and str(item.get("sourceKey") or "").strip()
    }
    directory: list[dict[str, Any]] = []
    for source_key, source_record in source_records.items():
        drift_item = drift_by_source.get(source_key)
        impact_item = impact_by_source.get(source_key)
        runtime_probe_display = knowledge_runtime_probe_display_from_catalog(
            catalog,
            source_keys=[source_key],
            worknet_key=str(source_record.get("worknetKey") or "").strip() if isinstance(source_record, dict) else None,
        )
        source_display = knowledge_display_source_record(
            source_record,
            drift_item=drift_item,
            impact_item=impact_item,
            runtime_probe_display=runtime_probe_display,
        )
        drift_display = knowledge_display_drift_item(
            drift_item,
            source_record=source_record,
        )
        impact_display = knowledge_display_source_impact(
            {"affected": bool(impact_item), "items": [impact_item] if isinstance(impact_item, dict) else []},
            catalog=catalog,
        )
        summary_parts: list[str] = []
        display_summary = str(source_display.get("summaryDisplay") or "").strip() if isinstance(source_display, dict) else ""
        if display_summary:
            summary_parts.append(display_summary)
        impact_summary = str(impact_display.get("summary") or "").strip() if isinstance(impact_display, dict) else ""
        if impact_summary and impact_summary not in summary_parts:
            summary_parts.append(impact_summary)
        drift_note = str(drift_display.get("note") or "").strip() if isinstance(drift_display, dict) else ""
        if drift_note and drift_note not in summary_parts:
            summary_parts.append(drift_note)
        drift_status = str((drift_item or {}).get("status") or "").strip()
        if impact_item or drift_status not in {"", "unchanged"}:
            freshness_status = "affected" if drift_status != "no-baseline" else "unknown"
        else:
            freshness_status = "stable"
        highest_priority = str((impact_item or {}).get("priority") or "low").strip() or "low"
        directory.append(
            {
                "key": source_key,
                "label": str(source_display.get("nameDisplay") or humanize_knowledge_source_label(source_record.get("name") or source_key)).strip(),
                "name": source_record.get("name"),
                "headline": source_display.get("headline") if isinstance(source_display, dict) else None,
                "summary": " ".join(part for part in summary_parts if part).strip(),
                "summaryPreview": knowledge_runtime_augmented_preview(
                    (
                        source_display.get("summaryDisplay")
                        if isinstance(source_display, dict)
                        else " ".join(part for part in summary_parts if part).strip()
                    ),
                    source_display.get("runtimeSummary") if isinstance(source_display, dict) else None,
                    headline=source_display.get("headline") if isinstance(source_display, dict) else None,
                    max_chars=140,
                    max_sentences=2,
                )
                or (
                    source_display.get("summaryPreview")
                    if isinstance(source_display, dict)
                    else None
                )
                or compact_preview_text(
                    " ".join(part for part in summary_parts if part).strip(),
                    max_chars=140,
                    max_sentences=2,
                ),
                "queryCommand": query_source_command(source_key),
                "primaryCommand": query_source_command(source_key, rebuild=True),
                "url": source_record.get("url") if isinstance(source_record, dict) else None,
                "kind": source_record.get("kind") if isinstance(source_record, dict) else None,
                "kindDisplay": source_display.get("kindDisplay") if isinstance(source_display, dict) else None,
                "trustTier": source_record.get("trustTier") if isinstance(source_record, dict) else None,
                "trustTierDisplay": source_display.get("trustTierDisplay") if isinstance(source_display, dict) else None,
                "worknetKey": source_record.get("worknetKey") if isinstance(source_record, dict) else None,
                "freshnessStatus": freshness_status,
                "highestPriority": highest_priority,
                "runtimeSummary": source_display.get("runtimeSummary") if isinstance(source_display, dict) else None,
                "runtimeProbeCount": source_display.get("runtimeProbeCount") if isinstance(source_display, dict) else None,
                "driftStatus": drift_status or None,
                "driftStatusDisplay": drift_display.get("statusDisplay") if isinstance(drift_display, dict) else None,
                "changedFieldsDisplay": drift_display.get("changedFieldsDisplay", []) if isinstance(drift_display, dict) else [],
                "impactedTopicsDisplay": impact_display.get("items", [{}])[0].get("impactedTopicsDisplay", []) if isinstance(impact_display, dict) and impact_display.get("items") else [],
                "impactedWorknetsDisplay": impact_display.get("items", [{}])[0].get("impactedWorknetsDisplay", []) if isinstance(impact_display, dict) and impact_display.get("items") else [],
                "reviewHint": impact_display.get("items", [{}])[0].get("reviewHint") if isinstance(impact_display, dict) and impact_display.get("items") else None,
            }
        )
    directory.sort(key=knowledge_source_directory_sort_key)
    return directory


def apply_runtime_summary_to_knowledge_entry(
    entry: dict[str, Any],
    *,
    runtime_probe_display: Any,
) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return entry
    runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
    if not runtime_summary:
        return entry
    normalized = dict(entry)
    normalized["runtimeSummary"] = runtime_summary
    normalized["runtimeProbeCount"] = knowledge_runtime_probe_count(runtime_probe_display) or None
    summary_text = str(normalized.get("summary") or "").strip()
    if runtime_summary not in summary_text:
        summary_text = join_product_sentences([summary_text, runtime_summary]) or runtime_summary
    normalized["summary"] = summary_text or normalized.get("summary")
    normalized["summaryPreview"] = knowledge_runtime_augmented_preview(
        normalized.get("summaryPreview") or normalized.get("plainLanguage") or summary_text,
        runtime_summary,
        headline=normalized.get("headline"),
        max_chars=140,
        max_sentences=2,
    ) if summary_text else normalized.get("summaryPreview")
    return normalized


def annotate_knowledge_catalog_runtime_summaries(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    capability_reports = capability_reports_by_worknet_key(
        bundle=load_cached_capability_bundle(state_context()),
    )
    source_directory = normalized.get("sourceDirectory")
    if isinstance(source_directory, list):
        updated_sources: list[dict[str, Any]] = []
        for item in source_directory:
            if not isinstance(item, dict):
                continue
            runtime_probe_display = knowledge_runtime_probe_display_from_catalog(
                normalized,
                source_keys=[item.get("key")],
                worknet_key=str(item.get("worknetKey") or "").strip() or None,
                capability_report=capability_reports.get(str(item.get("worknetKey") or "").strip()) if str(item.get("worknetKey") or "").strip() else None,
            )
            updated_sources.append(
                apply_runtime_summary_to_knowledge_entry(
                    item,
                    runtime_probe_display=runtime_probe_display,
                )
            )
        normalized["sourceDirectory"] = updated_sources
    reference_index = normalized.get("referenceIndex")
    if isinstance(reference_index, list):
        updated_references: list[dict[str, Any]] = []
        for item in reference_index:
            if not isinstance(item, dict):
                continue
            runtime_probe_display = knowledge_runtime_probe_display_from_catalog(
                normalized,
                source_keys=item.get("sourceKeys"),
                worknet_key=str(item.get("worknetKey") or "").strip() or None,
                capability_report=capability_reports.get(str(item.get("worknetKey") or "").strip()) if str(item.get("worknetKey") or "").strip() else None,
            )
            updated_references.append(
                apply_runtime_summary_to_knowledge_entry(
                    item,
                    runtime_probe_display=runtime_probe_display,
                )
            )
        normalized["referenceIndex"] = updated_references
    return normalized


def build_knowledge_overview(
    catalog: Optional[dict[str, Any]] = None,
    *,
    topic_index: Optional[list[dict[str, Any]]] = None,
    topic_directory: Optional[list[dict[str, Any]]] = None,
    reference_index: Optional[list[dict[str, Any]]] = None,
    source_directory: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    topic_index = topic_index if isinstance(topic_index, list) else build_knowledge_topic_index(catalog)
    topic_directory = topic_directory if isinstance(topic_directory, list) else build_knowledge_topic_directory(topic_index)
    reference_index = reference_index if isinstance(reference_index, list) else build_knowledge_reference_index(topic_index)
    source_directory = source_directory if isinstance(source_directory, list) else build_knowledge_source_directory(catalog)
    queue = catalog.get("knowledgeReviewQueue", {}) if isinstance(catalog.get("knowledgeReviewQueue"), dict) else {}
    queue_summary = summarize_knowledge_review_queue(queue)
    affected_topics = [item for item in topic_directory if isinstance(item, dict) and item.get("freshnessStatus") == "affected"]
    stable_topics = [item for item in topic_directory if isinstance(item, dict) and item.get("freshnessStatus") != "affected"]
    worknet_topics = [item for item in topic_directory if isinstance(item, dict) and item.get("worknetKey")]
    affected_sources = [item for item in source_directory if isinstance(item, dict) and item.get("freshnessStatus") == "affected"]
    focus_topics = topic_directory[:6]
    summary = (
        f"当前本地百科收录 {len(topic_directory)} 个高层主题、"
        f"{len(worknet_topics)} 个 WorkNet 条目、"
        f"{len(catalog.get('glossary', [])) if isinstance(catalog.get('glossary'), list) else 0} 个术语，"
        f"以及 {len(reference_index)} 条底层事实参考。"
    )
    queue_text = knowledge_review_queue_summary_text(queue_summary)
    if queue_summary.get("hasPendingReviews"):
        summary = f"{summary} {queue_text}"
    else:
        summary += " 当前没有待重审的知识条目。"
    headline = (
        str(queue_summary.get("headline") or "AWP 本地百科当前可直接使用。")
        if queue_summary.get("hasPendingReviews")
        else "AWP 本地百科当前可直接使用。"
    )
    primary_action_label = None
    primary_action_command = None
    if isinstance(queue_summary.get("primaryActionLabel"), str) and queue_summary.get("primaryActionLabel"):
        primary_action_label = queue_summary["primaryActionLabel"]
        primary_action_command = queue_summary.get("primaryActionCommand")
    elif focus_topics:
        primary_action_label = f"查看 {focus_topics[0].get('label')}"
        primary_action_command = focus_topics[0].get("queryCommand")
    return {
        "generatedAt": catalog.get("generatedAt") or now_iso(),
        "headline": headline,
        "summary": summary,
        "topicCount": len(topic_directory),
        "rawTopicIndexCount": len(topic_index),
        "referenceEntryCount": len(reference_index),
        "sourceDirectoryCount": len(source_directory),
        "affectedSourceDirectoryCount": len(affected_sources),
        "stableTopicCount": len(stable_topics),
        "affectedTopicCount": len(affected_topics),
        "worknetTopicCount": len(worknet_topics),
        "glossaryTermCount": len(catalog.get("glossary", [])) if isinstance(catalog.get("glossary"), list) else 0,
        "officialSourceCount": len(catalog.get("sources", {}).get("officialWebSources", [])) if isinstance(catalog.get("sources"), dict) else 0,
        "pendingReviewCount": int(queue_summary.get("pendingReviewCount", 0) or 0),
        "changedSourceCount": int(queue_summary.get("changedSourceCount", 0) or 0),
        "highestPriority": queue_summary.get("highestPriority"),
        "knowledgeReviewQueueSummary": queue_summary,
        "primaryActionLabel": primary_action_label,
        "primaryActionCommand": primary_action_command,
        "focusTopics": [
            build_normalized_knowledge_highlight(
                kind="topic",
                key=item.get("key"),
                label=item.get("label"),
                headline=item.get("headline"),
                preview=knowledge_runtime_augmented_preview(
                    item.get("summaryPreview") or item.get("summary"),
                    item.get("runtimeSummary"),
                    headline=item.get("headline"),
                ),
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="overview",
                extra={
                    "summary": knowledge_runtime_augmented_preview(
                        item.get("summaryPreview") or item.get("summary"),
                        item.get("runtimeSummary"),
                        headline=item.get("headline"),
                    ),
                    "summaryPreview": knowledge_runtime_augmented_preview(
                        item.get("summaryPreview") or item.get("summary"),
                        item.get("runtimeSummary"),
                        headline=item.get("headline"),
                    ),
                    "summaryFull": knowledge_runtime_augmented_summary(
                        item.get("summary"),
                        item.get("runtimeSummary"),
                    ) or item.get("summary"),
                    "affectedSourceKeys": item.get("affectedSourceKeys", []),
                    "worknetKey": item.get("worknetKey"),
                    "worknetName": item.get("worknetName"),
                    "automationLevel": item.get("automationLevel"),
                    "riskLevel": item.get("riskLevel"),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                    "status": item.get("freshnessStatus"),
                    "statusDisplay": knowledge_freshness_status_display(item.get("freshnessStatus")),
                },
            )
            for item in focus_topics
            if isinstance(item, dict)
        ],
        "affectedTopics": [
            normalize_affected_topic_payload({
                "key": item.get("key"),
                "label": item.get("label"),
                "headline": item.get("headline"),
                "primaryCommand": item.get("primaryCommand"),
                "affectedSourceKeys": item.get("affectedSourceKeys", []),
            })
            for item in affected_topics[:6]
            if isinstance(item, dict)
        ],
        "referenceHighlights": [
            build_normalized_knowledge_highlight(
                kind="reference",
                key=item.get("key"),
                label=item.get("label"),
                headline=item.get("headline"),
                preview=knowledge_runtime_augmented_preview(
                    item.get("summaryPreview") or item.get("summary"),
                    item.get("runtimeSummary"),
                    headline=item.get("headline"),
                ),
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="overview",
                extra={
                    "summaryPreview": knowledge_runtime_augmented_preview(
                        item.get("summaryPreview") or item.get("summary"),
                        item.get("runtimeSummary"),
                        headline=item.get("headline"),
                    ),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
            for item in reference_index[:6]
            if isinstance(item, dict)
        ],
        "sourceHighlights": [
            build_normalized_knowledge_highlight(
                kind="source",
                key=item.get("key"),
                label=item.get("label"),
                headline=item.get("headline"),
                preview=knowledge_runtime_augmented_preview(
                    item.get("summaryPreview") or item.get("summary"),
                    item.get("runtimeSummary"),
                    headline=item.get("headline"),
                ),
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="overview",
                extra={
                    "summaryPreview": knowledge_runtime_augmented_preview(
                        item.get("summaryPreview") or item.get("summary"),
                        item.get("runtimeSummary"),
                        headline=item.get("headline"),
                    ),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
            for item in source_directory[:6]
            if isinstance(item, dict)
        ],
    }


def capability_reports_by_worknet_key(
    *,
    state: Optional[dict[str, Any]] = None,
    bundle: Optional[dict[str, Any]] = None,
) -> dict[str, dict[str, Any]]:
    state = state or state_context()
    bundle = bundle if isinstance(bundle, dict) else load_cached_capability_bundle(state)
    if not isinstance(bundle, dict):
        return {}
    reports: dict[str, dict[str, Any]] = {}
    for item in bundle.get("reports", []):
        if not isinstance(item, dict):
            continue
        profile = (
            resolve_worknet(str(item.get("worknetId") or ""))
            or resolve_worknet(str(item.get("name") or ""))
            or resolve_worknet(str(item.get("symbol") or ""))
        )
        if isinstance(profile, dict) and str(profile.get("key") or "").strip():
            reports[str(profile["key"]).strip()] = item
    return reports


def load_or_build_knowledge_catalog(state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    state = state or state_context()
    return load_cached_knowledge_catalog(state) or build_knowledge_catalog()


def knowledge_focus_topics_payload(catalog: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    topic_directory = catalog.get("topicDirectory", []) if isinstance(catalog, dict) else []
    topics: list[dict[str, Any]] = []
    for item in topic_directory:
        if not isinstance(item, dict):
            continue
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        payload = build_normalized_knowledge_highlight(
            kind="topic",
            key=item.get("key"),
            label=item.get("label"),
            headline=item.get("headline"),
            preview=preview_text,
            query_command=item.get("queryCommand"),
            primary_command=item.get("primaryCommand"),
            freshness_status=item.get("freshnessStatus"),
            research_tier="overview",
            extra={
                "summary": preview_text,
                "summaryPreview": preview_text,
                "summaryFull": summary_text or item.get("summary"),
                "worknetKey": item.get("worknetKey"),
                "worknetName": item.get("worknetName"),
                "automationLevel": item.get("automationLevel"),
                "riskLevel": item.get("riskLevel"),
                "runtimeSummary": item.get("runtimeSummary"),
                "runtimeProbeCount": item.get("runtimeProbeCount"),
                "status": item.get("freshnessStatus"),
                "statusDisplay": knowledge_freshness_status_display(item.get("freshnessStatus")),
            },
        )
        topics.append(payload)
        if len(topics) >= limit:
            break
    return topics


def knowledge_reference_highlights_payload(catalog: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    reference_index = catalog.get("referenceIndex", []) if isinstance(catalog, dict) else []
    references: list[dict[str, Any]] = []
    for item in reference_index:
        if not isinstance(item, dict):
            continue
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        payload = build_normalized_knowledge_highlight(
            kind="reference",
            key=item.get("key"),
            label=item.get("label"),
            headline=item.get("headline"),
            preview=preview_text,
            query_command=item.get("queryCommand"),
            primary_command=item.get("primaryCommand"),
            freshness_status=item.get("freshnessStatus"),
            research_tier="overview",
            extra={
                "summary": preview_text,
                "summaryPreview": preview_text,
                "summaryFull": summary_text or item.get("summary"),
                "runtimeSummary": item.get("runtimeSummary"),
                "runtimeProbeCount": item.get("runtimeProbeCount"),
            },
        )
        references.append(payload)
        if len(references) >= limit:
            break
    return references


def knowledge_source_highlights_payload(catalog: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    source_directory = catalog.get("sourceDirectory", []) if isinstance(catalog, dict) else []
    highlights: list[dict[str, Any]] = []
    for item in source_directory:
        if not isinstance(item, dict):
            continue
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        payload = build_normalized_knowledge_highlight(
            kind="source",
            key=item.get("key"),
            label=item.get("label"),
            headline=item.get("headline"),
            preview=preview_text,
            query_command=item.get("queryCommand"),
            primary_command=item.get("primaryCommand"),
            freshness_status=item.get("freshnessStatus"),
            research_tier="overview",
            extra={
                "summary": preview_text,
                "summaryPreview": preview_text,
                "summaryFull": summary_text or item.get("summary"),
                "highestPriority": item.get("highestPriority"),
                "worknetKey": item.get("worknetKey"),
                "kindDisplay": item.get("kindDisplay"),
                "runtimeSummary": item.get("runtimeSummary"),
                "runtimeProbeCount": item.get("runtimeProbeCount"),
            },
        )
        highlights.append(payload)
        if len(highlights) >= limit:
            break
    return highlights


def find_topic_directory_entry(
    topic_directory: Any,
    *,
    key: Optional[str] = None,
    worknet_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(topic_directory, list):
        return None
    normalized_key = str(key or "").strip().lower()
    normalized_worknet_key = str(worknet_key or "").strip().lower()
    for item in topic_directory:
        if not isinstance(item, dict):
            continue
        item_key = str(item.get("key") or "").strip().lower()
        item_worknet_key = str(item.get("worknetKey") or "").strip().lower()
        if normalized_key and item_key == normalized_key:
            return item
        if normalized_worknet_key and item_worknet_key == normalized_worknet_key:
            return item
    return None


def knowledge_action_description(item: Any) -> str:
    return knowledge_highlight_action_description(item, action="view")


def knowledge_source_action_description(item: Any) -> str:
    return knowledge_highlight_action_description(item, action="source-view")


def knowledge_refresh_action_description(item: Any) -> str:
    return knowledge_highlight_action_description(item, action="refresh")


def knowledge_highlight_preview_text(item: Any) -> str:
    item = item if isinstance(item, dict) else {}
    return strip_sentence_end(
        item.get("preview")
        or item.get("summaryPreview")
        or item.get("summary")
        or item.get("headline")
        or item.get("label")
    )


def knowledge_runtime_augmented_summary(
    summary: Any,
    runtime_summary: Any,
) -> Optional[str]:
    summary_text = str(summary or "").strip()
    runtime_text = str(runtime_summary or "").strip()
    if runtime_text:
        runtime_core = strip_sentence_end(runtime_text)
        duplicate_pattern = re.compile(
            rf"(?:{re.escape(runtime_core)}(?:[。.!?！？]?\s*)){{2,}}"
        )
        summary_text = duplicate_pattern.sub(runtime_core, summary_text).strip()
    if runtime_text:
        normalized_summary = strip_sentence_end(summary_text)
        normalized_runtime = strip_sentence_end(runtime_text)
        if normalized_runtime and normalized_runtime in normalized_summary:
            return summary_text
    if runtime_text and runtime_text in summary_text:
        return summary_text
    text = join_product_sentences(
        [
            summary_text,
            runtime_text,
        ]
    )
    return text or summary_text or None


def knowledge_runtime_augmented_preview(
    summary: Any,
    runtime_summary: Any,
    *,
    headline: Any = None,
    max_chars: int = 140,
    max_sentences: int = 2,
) -> Optional[str]:
    summary_text = str(summary or "").strip()
    runtime_text = str(runtime_summary or "").strip()
    headline_text = str(headline or "").strip()
    if not runtime_text:
        return compact_preview_text(summary_text or headline_text, max_chars=max_chars, max_sentences=max_sentences) if (summary_text or headline_text) else None
    summary_text = knowledge_runtime_augmented_summary(summary_text, runtime_text) or summary_text
    normalized_summary = strip_sentence_end(summary_text)
    normalized_runtime = strip_sentence_end(runtime_text)
    base_text = summary_text
    if normalized_runtime and normalized_runtime in normalized_summary:
        base_text = re.sub(
            rf"(?:[。.!?！？]\s*)?{re.escape(normalized_runtime)}(?:[。.!?！？]\s*)?",
            " ",
            summary_text,
            count=1,
        )
        base_text = re.sub(r"\s+", " ", base_text).strip()
    if not base_text and headline_text and strip_sentence_end(headline_text) != normalized_runtime:
        base_text = headline_text
    if len(runtime_text) >= max_chars - 12:
        return compact_preview_text(runtime_text, max_chars=max_chars, max_sentences=1)
    reserve = min(max(len(normalized_runtime) + 4, 48), max_chars - 18) if normalized_runtime else 48
    base_max_chars = max(18, min(72, max_chars - reserve))
    base_preview = None
    for candidate in preview_candidate_fragments(base_text):
        candidate_preview = compact_preview_text(candidate, max_chars=base_max_chars, max_sentences=1)
        if not isinstance(candidate_preview, str):
            continue
        candidate_preview = candidate_preview.rstrip("… ")
        if candidate_preview.endswith(("这条", "这个", "当前", "这些", "那些", "该条", "该项")):
            boundary = max(
                candidate_preview.rfind("，"),
                candidate_preview.rfind("、"),
                candidate_preview.rfind("："),
                candidate_preview.rfind(" "),
            )
            if boundary > 0:
                candidate_preview = candidate_preview[:boundary].rstrip("，、： ")
        combined_candidate = join_product_sentences([candidate_preview, runtime_text])
        if len(combined_candidate) <= max_chars:
            base_preview = candidate_preview
            if "…" not in candidate_preview:
                break
    if not base_preview and headline_text and strip_sentence_end(headline_text) != normalized_runtime:
        base_preview = compact_preview_text(headline_text, max_chars=base_max_chars, max_sentences=1)
        if isinstance(base_preview, str):
            base_preview = base_preview.rstrip("… ")
    combined = join_product_sentences([base_preview or base_text, runtime_text]) if (base_preview or base_text) else runtime_text
    preview = compact_preview_text(combined, max_chars=max_chars, max_sentences=max_sentences) if combined else None
    if normalized_runtime and isinstance(preview, str) and normalized_runtime not in strip_sentence_end(preview):
        runtime_only = compact_preview_text(runtime_text, max_chars=max_chars, max_sentences=1)
        if runtime_only:
            return runtime_only
    return preview


def knowledge_highlight_action_description(item: Any, *, action: str = "view") -> str:
    item = item if isinstance(item, dict) else {}
    record_kind = str(item.get("recordKind") or item.get("kind") or "").strip().lower()
    label = str(item.get("labelDisplay") or item.get("label") or item.get("key") or "这条条目").strip()
    preview = knowledge_highlight_preview_text(item) or label
    freshness = str(item.get("freshnessStatus") or "").strip().lower()

    if action == "refresh":
        if freshness == "affected":
            return f"如果你怀疑上游刚变了，就重新核对 {label} 这条本地知识条目。"
        return f"重新生成 {label} 这条本地知识条目，确认缓存和上游资料仍然一致。"

    if record_kind == "source" or action == "source-view":
        if freshness == "affected":
            return f"直接看 {label} 最近变了什么、影响了哪些主题和工作网。"
        return f"{preview}。 直接看这条来源的档案、漂移状态和受影响范围。"

    if record_kind == "reference":
        return f"{preview}。 直接看这条底层参考、规则边界和运行时约束。"
    if record_kind == "fact":
        return f"{preview}。 直接看这条事实记录和对应证据。"
    if record_kind == "worknet":
        return f"{preview}。 直接看这条 WorkNet 的高层说明、风险和下一步建议。"
    if record_kind == "evidence":
        return f"{preview}。 直接看这条证据 claim、定位和稳定性。"
    return f"{preview}。 直接看这条高层主题的百科摘要、证据和下一步建议。"


def knowledge_context_for_worknet(catalog: Any, worknet_key: Optional[str]) -> Optional[dict[str, Any]]:
    key = str(worknet_key or "").strip().lower()
    if not key or not isinstance(catalog, dict):
        return None
    topic_directory = catalog.get("topicDirectory", [])
    return find_topic_directory_entry(topic_directory, key=key, worknet_key=key)


def knowledge_related_reference_highlights(
    catalog: Any,
    knowledge_context: Any,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not isinstance(catalog, dict) or not isinstance(knowledge_context, dict):
        return []
    topic_source_keys = {
        str(item).strip()
        for item in knowledge_context.get("sourceKeys", [])
        if str(item).strip()
    }
    topic_label = str(knowledge_context.get("label") or "").strip().lower()
    topic_key = str(knowledge_context.get("key") or "").strip().lower()
    references = catalog.get("referenceIndex", [])
    ranked: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    for item in references:
        if not isinstance(item, dict):
            continue
        item_label = str(item.get("label") or "").strip().lower()
        item_key = str(item.get("key") or "").strip().lower()
        item_source_keys = {
            str(source_key).strip()
            for source_key in item.get("sourceKeys", [])
            if str(source_key).strip()
        }
        overlap = len(topic_source_keys.intersection(item_source_keys))
        same_label = 1 if topic_label and item_label == topic_label else 0
        key_hint = 1 if topic_key and topic_key in item_key else 0
        score = same_label + key_hint + overlap
        if score <= 0:
            continue
        ranked.append(((-score, -overlap, item_key), item))
    ranked.sort(key=lambda pair: pair[0])
    highlights: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, item in ranked:
        key = str(item.get("key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        highlights.append(
            build_normalized_knowledge_highlight(
                kind="reference",
                key=key,
                label=item.get("label"),
                headline=item.get("headline"),
                preview=preview_text,
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="related",
                extra={
                    "summary": preview_text,
                    "summaryPreview": preview_text,
                    "summaryFull": summary_text or item.get("summary"),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
        )
        if len(highlights) >= limit:
            break
    return highlights


def knowledge_related_source_highlights(
    catalog: Any,
    knowledge_context: Any,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not isinstance(catalog, dict) or not isinstance(knowledge_context, dict):
        return []
    topic_source_keys = {
        str(item).strip()
        for item in knowledge_context.get("sourceKeys", [])
        if str(item).strip()
    }
    worknet_key = str(knowledge_context.get("worknetKey") or "").strip().lower()
    source_directory = catalog.get("sourceDirectory", [])
    ranked: list[dict[str, Any]] = []
    for item in source_directory:
        if not isinstance(item, dict):
            continue
        item_key = str(item.get("key") or "").strip()
        item_worknet_key = str(item.get("worknetKey") or "").strip().lower()
        if item_key not in topic_source_keys and (not worknet_key or item_worknet_key != worknet_key):
            continue
        ranked.append(item)
    ranked.sort(key=knowledge_source_directory_sort_key)
    highlights: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in ranked:
        key = str(item.get("key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        preview_text = knowledge_runtime_augmented_preview(
            item.get("summaryPreview") or item.get("summary"),
            item.get("runtimeSummary"),
            headline=item.get("headline"),
        )
        summary_text = knowledge_runtime_augmented_summary(
            item.get("summary"),
            item.get("runtimeSummary"),
        )
        highlights.append(
            build_normalized_knowledge_highlight(
                kind="source",
                key=key,
                label=item.get("label"),
                headline=item.get("headline"),
                preview=preview_text,
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="related",
                extra={
                    "summary": preview_text,
                    "summaryPreview": preview_text,
                    "summaryFull": summary_text or item.get("summary"),
                    "highestPriority": item.get("highestPriority"),
                    "worknetKey": item.get("worknetKey"),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
        )
        if len(highlights) >= limit:
            break
    return highlights


def compact_knowledge_context(item: Any) -> Optional[dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    payload = build_normalized_knowledge_highlight(
        kind="topic",
        key=item.get("key"),
        label=item.get("label"),
        headline=item.get("headline"),
        preview=item.get("summaryPreview") or item.get("summary"),
        query_command=item.get("queryCommand"),
        primary_command=item.get("primaryCommand"),
        freshness_status=item.get("freshnessStatus"),
        research_tier="current",
        extra={
            "summary": item.get("summaryPreview") or item.get("summary"),
            "summaryPreview": item.get("summaryPreview"),
            "summaryFull": item.get("summary"),
            "affectedSourceKeys": item.get("affectedSourceKeys", []),
            "worknetKey": item.get("worknetKey"),
            "worknetName": item.get("worknetName"),
            "automationLevel": item.get("automationLevel"),
            "riskLevel": item.get("riskLevel"),
            "runtimeSummary": item.get("runtimeSummary"),
            "runtimeProbeCount": item.get("runtimeProbeCount"),
            "status": item.get("freshnessStatus"),
            "statusDisplay": knowledge_freshness_status_display(item.get("freshnessStatus")),
        },
    )
    return payload


def capability_knowledge_caveat(
    knowledge_context: Any,
    knowledge_source_highlights: Any = None,
) -> Optional[str]:
    if not isinstance(knowledge_context, dict):
        return None
    if str(knowledge_context.get("freshnessStatus") or "") != "affected":
        return None
    label = str(knowledge_context.get("label") or knowledge_context.get("key") or "当前 WorkNet").strip()
    source_labels = knowledge_source_labels_text(
        knowledge_source_highlights,
        affected_only=True,
        limit=3,
    )
    if source_labels:
        return f"{label} 这条高层知识当前也有上游变更，继续前先复核 {source_labels}。"
    return f"{label} 这条高层知识当前也有上游变更，继续前先复核官方来源。"


def attach_knowledge_to_capability_reports(
    reports: list[dict[str, Any]],
    *,
    catalog: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    catalog = catalog if isinstance(catalog, dict) else load_or_build_knowledge_catalog()
    enriched: list[dict[str, Any]] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        normalized = dict(report)
        profile = (
            resolve_worknet(str(report.get("worknetId") or ""))
            or resolve_worknet(str(report.get("name") or ""))
            or resolve_worknet(str(report.get("symbol") or ""))
        )
        worknet_key = str(profile.get("key") or "") if isinstance(profile, dict) else ""
        knowledge_context = compact_knowledge_context(
            knowledge_context_for_worknet(catalog, worknet_key)
        )
        reference_highlights = knowledge_related_reference_highlights(
            catalog,
            knowledge_context,
        ) if isinstance(knowledge_context, dict) else []
        source_highlights = knowledge_related_source_highlights(
            catalog,
            knowledge_context,
        ) if isinstance(knowledge_context, dict) else []
        normalized["knowledgeContext"] = knowledge_context
        normalized["knowledgeReferenceHighlights"] = reference_highlights
        normalized["knowledgeSourceHighlights"] = source_highlights
        caveat = capability_knowledge_caveat(knowledge_context, source_highlights)
        reason = str(normalized.get("reason") or "").strip()
        if caveat and caveat not in reason:
            normalized["reason"] = f"{reason} 百科补充：{caveat}".strip() if reason else caveat
        enriched.append(normalized)
    return enriched
