"""Canonical topic and WorkNet narrative helpers."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.knowledge_data import load_topic_narratives


CANONICAL_TOPIC_NARRATIVES: dict[str, dict[str, str]] = load_topic_narratives()


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
            return f"{plain} This path can start directly now and is the default no-stake long-running data workflow."
        return f"{plain} The local runtime is not ready yet; fix Mine runtime setup and dataset access first."
    if key == "predict":
        if runnable:
            return f"{plain} It can observe markets now, or run a quiet loop if the user accepts the higher risk."
        return f"{plain} Observation is safer until runtime and qualification conditions are stable."
    if key == "gov":
        if runnable:
            return f"{plain} Public observation is appropriate now; trades and votes still require confirmation."
        return f"{plain} Start with public markets and the current phase instead of direct automation."
    if key == "ardi":
        if runnable:
            return f"{plain} Preflight can run now, but commit, reveal, and inscribe must follow official next-command guidance."
        return f"{plain} Fund gas or complete the qualification path before continuing."
    if key == "kya":
        return plain or f"{name} is a one-off identity and delegation utility rather than a long-running loop."
    if key in {"tmr", "community"}:
        return f"{plain} Observation and documentation are recommended; automatic execution is not."
    if plain and runnable and can_start_without_stake is True:
        return f"{plain} It can start directly now without stake."
    if plain and runnable:
        return f"{plain} It is ready to continue."
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
            return f"{plain} It can be selected now and is the default no-stake data workflow."
        return f"{plain} It is not ready for automatic execution yet; inspect runtime setup and dataset access first."
    if key == "predict":
        if runnable:
            return f"{plain} It can be selected for market observation or a quiet loop; real rewards still depend on settlement."
        return f"{plain} It is safer to observe market context until runtime conditions are stable."
    if key == "gov":
        if runnable:
            return f"{plain} It is appropriate for public observation now; trades and votes still require confirmation."
        return f"{plain} It is discoverable, but start with public markets and phase inspection before continuing."
    if key == "ardi":
        if runnable:
            return f"{plain} Preflight can run after switching, but commit, reveal, and inscribe must follow official next-command guidance."
        return f"{plain} It is not ready for automatic execution until gas or qualification gaps are fixed."
    if key == "kya":
        return plain or f"{name} is a one-off identity and delegation utility rather than a long-running loop."
    if key in {"tmr", "community"}:
        return f"{plain} View its dossier rather than starting automation."
    if plain and runnable and can_start_without_stake is True:
        return f"{plain} It can be selected now without stake."
    if plain and runnable:
        return f"{plain} It can be selected now."
    if plain:
        return f"{plain} Automatic execution is not recommended yet."
    return None


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
