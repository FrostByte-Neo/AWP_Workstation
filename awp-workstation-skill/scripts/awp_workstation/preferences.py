"""User preference persistence and updates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from awp_workstation.knowledge_data import load_default_user_preferences
from awp_workstation.state import state_context
from awp_workstation.storage import atomic_write_json, load_json
from awp_workstation.utils import now_iso
from awp_workstation.worknets import load_worknet_profiles


DEFAULT_USER_PREFERENCES: dict[str, Any] = load_default_user_preferences()
KNOWN_WORKNETS: list[dict[str, Any]] = load_worknet_profiles()


def resolve_preference_worknet(identifier: str) -> Optional[dict[str, Any]]:
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


def load_user_preferences(state: dict[str, Any]) -> dict[str, Any]:
    path = Path(state["user"]) / "preferences.json"
    current = load_json(path, {})
    merged = dict(DEFAULT_USER_PREFERENCES)
    if isinstance(current, dict):
        merged.update(current)
    return merged


def ensure_user_preferences(state: dict[str, Any]) -> dict[str, Any]:
    path = Path(state["user"]) / "preferences.json"
    merged = load_user_preferences(state)
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
        profile = resolve_preference_worknet(preferred_worknet)
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
        profile = resolve_preference_worknet(preferred_worknet)
        if profile is not None:
            message_parts.append(f"Preferred WorkNet set to {profile['name']}.")
    if allow_asset_actions is False or str(autopilot_mode or "") == "non-financial-only":
        message_parts.append("Autopilot remains limited to non-financial actions.")
    if allow_asset_actions is True:
        message_parts.append("Asset actions are allowed only when an explicit confirmation gate is present.")
    if not message_parts:
        message_parts.append("Workstation preferences updated." if applied_changes else "Workstation preferences unchanged.")

    return {
        "generatedAt": now_iso(),
        "message": " ".join(message_parts),
        "appliedChanges": applied_changes,
        "userPreferences": updated,
        "stateRoot": state["root"],
    }
