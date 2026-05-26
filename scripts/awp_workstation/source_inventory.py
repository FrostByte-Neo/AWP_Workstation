"""Source inventory helpers for official and local workstation sources."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any, Optional

from awp_workstation.knowledge_data import load_official_web_sources
from awp_workstation.skill_inventory import discover_local_sources
from awp_workstation.utils import now_iso, repository_is_effectively_empty, safe_slug
from awp_workstation.worknets import load_worknet_profiles


OFFICIAL_WEB_SOURCES: list[dict[str, Any]] = load_official_web_sources()
KNOWN_WORKNETS: list[dict[str, Any]] = load_worknet_profiles()


def source_filename(source: dict[str, Any]) -> str:
    parsed = urllib.parse.urlparse(str(source["url"]))
    path = parsed.path or ""
    suffix = Path(path).suffix.lower()
    if not suffix:
        suffix = ".txt" if source.get("kind") in {"skill-doc", "aip"} else ".bin"
    return f"{safe_slug(str(source['key']))}{suffix}"


def build_source_inventory(state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    local_sources = discover_local_sources()
    local_by_key = {item["key"]: item for item in local_sources}
    missing = [item["key"] for item in local_sources if not item.get("available")]
    managed_root = Path(state["skills"]) / "checkouts" if isinstance(state, dict) else Path()
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
