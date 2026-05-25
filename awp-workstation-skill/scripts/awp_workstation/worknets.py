"""WorkNet profile loading."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Optional

from awp_workstation.utils import normalize_worknet_token


DATA_ROOT = Path(__file__).resolve().parent / "data"
WORKNET_PROFILES_PATH = DATA_ROOT / "worknets.json"


def load_worknet_profiles(path: Path = WORKNET_PROFILES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"worknet profile data must be a list: {path}")
    profiles: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"worknet profile at index {index} is not an object")
        key = str(item.get("key") or "").strip()
        if not key:
            raise ValueError(f"worknet profile at index {index} is missing key")
        profiles.append(copy.deepcopy(item))
    return profiles


KNOWN_WORKNETS: list[dict[str, Any]] = load_worknet_profiles()


def resolve_worknet(identifier: str) -> Optional[dict[str, Any]]:
    text = identifier.strip().lower()
    for item in KNOWN_WORKNETS:
        if text == item["key"]:
            return copy.deepcopy(item)
        if text == str(item["worknet_id"]).lower():
            return copy.deepcopy(item)
        if text == item["name"].lower():
            return copy.deepcopy(item)
        if text in {alias.lower() for alias in item.get("aliases", [])}:
            return copy.deepcopy(item)
    return None


def worknet_candidate_matches_text(
    candidate_text: str,
    query_text: str,
    *,
    normalized_candidate: Optional[str] = None,
    normalized_query: Optional[str] = None,
) -> bool:
    candidate = str(candidate_text or "").strip().lower()
    query = str(query_text or "").strip().lower()
    if not candidate or not query:
        return False
    normalized_candidate = normalize_worknet_token(candidate) if normalized_candidate is None else normalized_candidate
    normalized_query = normalize_worknet_token(query) if normalized_query is None else normalized_query
    if normalized_candidate and normalized_candidate == normalized_query:
        return True
    if candidate.isdigit() and len(candidate) >= 3:
        return re.search(rf"(?<![0-9]){re.escape(candidate)}(?![0-9])", query) is not None
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(candidate)}(?![A-Za-z0-9])", query) is not None


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
            if worknet_candidate_matches_text(
                candidate_text,
                text,
                normalized_candidate=normalized_candidate,
                normalized_query=normalized_query,
            ):
                return copy.deepcopy(profile)
    return None


def recommend_worknet_actions_payload(
    bundle: dict[str, Any],
    *,
    preferences: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("worknet recommendation dependencies are required")
    build_playbook_command = dependencies["build_playbook_command"]
    humanize_worknet_switch_summary = dependencies["humanize_worknet_switch_summary"]
    query_knowledge_command = dependencies["query_knowledge_command"]
    resolve_worknet = dependencies["resolve_worknet"]
    run_worknet_command = dependencies["run_worknet_command"]

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

    recommendation = "Complete preflight first, then choose which WorkNet to run."
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
            return "Let Predict observe markets and form views in the background without interrupting every round."
        summary = humanize_worknet_switch_summary(profile, report)
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip()
        return f"Continue with the default rhythm for {profile.get('name') or profile.get('key') or 'this WorkNet'}."

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
                else "Mine remains the safer no-stake fallback."
            )
            recommendation = f"{preferred_name} is saved as the default WorkNet. {preferred_summary} If you want the safer no-stake route now, {mine_summary}"
        else:
            recommendation = f"{preferred_name} is saved as the default WorkNet. {describe_worknet_action(preferred_profile, preferred)}"
        label = f"Run only {preferred_name}"
        actions.append(
            {
                "label": label,
                "description": describe_worknet_action(
                    preferred_profile,
                    preferred,
                    fallback="Start the saved default WorkNet first.",
                ),
            }
        )
        action_map[label] = build_playbook_command(str(preferred_profile["key"]))
        if preferred_profile["key"] == "predict":
            actions.append(
                {
                    "label": "Start Predict quiet loop",
                    "description": describe_worknet_action(
                        preferred_profile,
                        preferred,
                        background=True,
                        fallback="Let Predict run in the background without interrupting every round.",
                    ),
                }
            )
            action_map["Start Predict quiet loop"] = run_worknet_command("predict", execute=True, auto_advance=True)
        if mine and mine.get("runnable"):
            actions.append(
                {
                    "label": "Switch back to Mine only",
                    "description": describe_worknet_action(
                        mine_profile or resolve_worknet("mine") or {"key": "mine", "name": "Mine WorkNet"},
                        mine,
                        fallback="Switch back to Mine if you want the safer no-stake data workflow.",
                    ),
                }
            )
            action_map["Switch back to Mine only"] = build_playbook_command("mine")
    elif mine and mine.get("runnable"):
        predict_ready = bool(predictable and predictable.get("runnable"))
        mine_summary = describe_worknet_action(
            mine_profile or resolve_worknet("mine") or {"key": "mine", "name": "Mine WorkNet"},
            mine,
            fallback="             Mine          ",
        )
        if predict_ready:
            predict_summary = describe_worknet_action(
                predict_profile or resolve_worknet("predict") or {"key": "predict", "name": "Predict WorkNet"},
            predictable,
            background=True,
            fallback="Also keep Predict running as a quiet background loop.",
        )
            recommendation = f"Start with Mine. {mine_summary} Also, {predict_summary}"
        else:
            recommendation = f"Start with Mine. {mine_summary} Predict is safer as observation for the next 24 hours."
        actions.append(
            {
                "label": "Run Mine only",
                "description": describe_worknet_action(
                    mine_profile or resolve_worknet("mine") or {"key": "mine", "name": "Mine WorkNet"},
                    mine,
                    fallback="Start with the no-stake data workflow.",
                ),
            }
        )
        action_map["Run Mine only"] = build_playbook_command("mine")
        if predict_ready:
            actions.append(
                {
                    "label": "Start Predict quiet loop",
                    "description": describe_worknet_action(
                        predict_profile or resolve_worknet("predict") or {"key": "predict", "name": "Predict WorkNet"},
                        predictable,
                        background=True,
                        fallback="Let Predict run in the background without interrupting every round.",
                    ),
                }
            )
            action_map["Start Predict quiet loop"] = run_worknet_command("predict", execute=True, auto_advance=True)
    elif no_stake:
        first = no_stake[0]
        first_profile = resolve_worknet(str(first.get("worknetId") or first.get("name") or ""))
        recommendation = f"Start with {first.get('name')}. {describe_worknet_action(first_profile or {'key': first.get('name'), 'name': first.get('name')}, first, fallback='It does not currently require stake.')}"
        label = f"Run only {first.get('name')}"
        actions.append(
            {
                "label": label,
                "description": describe_worknet_action(
                    first_profile or {"key": first.get("name"), "name": first.get("name")},
                    first,
                    fallback="Start with the easiest currently runnable workflow.",
                ),
            }
        )
        action_map[label] = build_playbook_command(str(first.get("worknetId")))
    elif mine and str(mine.get("cliStatus")) == "runtime-error":
        recommendation = "Fix the Mine runtime first, then decide whether to switch to another WorkNet that needs an official runtime install."
        actions.append(
            {
                "label": "Inspect Mine runtime",
                "description": "Check why the local Mine runtime did not pass self-test.",
            }
        )
        action_map["Inspect Mine runtime"] = "python3 scripts/inspect-skill.py --skill-key mine"
        remediation_commands = mine.get("skillInspection", {}).get("remediationCommands", [])
        if isinstance(remediation_commands, list) and remediation_commands:
            command = remediation_commands[0]
            label = "Repair Mine runtime"
            actions.insert(
                0,
                {
                    "label": label,
                    "description": "Apply the detected environment fix for the local Mine runtime first.",
                },
            )
            action_map[label] = " ".join(str(item) for item in command.get("argv", []))

    if predictable and not predictable.get("runnable"):
        actions.append(
            {
                "label": "Observe Predict",
                "description": describe_worknet_action(
                    predict_profile or resolve_worknet("predict") or {"key": "predict", "name": "Predict WorkNet"},
                    predictable,
                    fallback="Collect prediction market context first, then wait for official runtime conditions to be clear.",
                ),
            }
        )
        action_map["Observe Predict"] = query_knowledge_command("predict")

    if not actions:
        actions.append(
            {
                "label": "View WorkNet dossiers",
                "description": "Understand each WorkNet's requirements and risks before choosing one.",
            }
        )
        action_map["View WorkNet dossiers"] = "python3 scripts/query-knowledge.py --topic protocol-core"

    return {
        "recommendation": recommendation,
        "actions": actions,
        "actionMap": action_map,
        "runnableCount": len(all_runnable),
        "earningRunnableCount": len(earning_runnable),
        "supportRunnableCount": max(0, len(all_runnable) - len(earning_runnable)),
        "noStakeRunnableCount": len(no_stake),
    }
