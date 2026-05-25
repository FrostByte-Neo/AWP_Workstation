"""Skill source inventory and installation-state helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from awp_workstation.knowledge_data import load_core_dependency_skills, load_local_source_candidates
from awp_workstation.state import DEFAULT_FALLBACK_STATE_ROOT, state_context
from awp_workstation.utils import safe_slug
from awp_workstation.worknets import load_worknet_profiles


OFFICIAL_SKILL_ALLOWLIST_PREFIXES = ("https://github.com/awp-worknet/",)
CORE_DEPENDENCY_SKILLS: list[dict[str, Any]] = load_core_dependency_skills()
LOCAL_SOURCE_CANDIDATES: list[dict[str, Any]] = load_local_source_candidates()
KNOWN_WORKNETS: list[dict[str, Any]] = load_worknet_profiles()


def looks_official_skill_uri(uri: Optional[str]) -> bool:
    if not uri:
        return False
    return uri.startswith(OFFICIAL_SKILL_ALLOWLIST_PREFIXES) or "github.com/awp-core/awp-skill" in uri


def discover_local_sources() -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    allow_legacy = os.environ.get("AWP_WORKSTATION_ALLOW_LEGACY_LOCAL_SOURCES") == "1"
    for candidate in LOCAL_SOURCE_CANDIDATES:
        root = Path(candidate["path"])
        record = dict(candidate)
        is_legacy_nanobot_path = str(root).startswith("/root/.nanobot/workspace/")
        record["available"] = root.exists() and (allow_legacy or not is_legacy_nanobot_path)
        if root.exists() and is_legacy_nanobot_path and not allow_legacy:
            record["warning"] = (
                "legacy nanobot workspace path ignored; set "
                "AWP_WORKSTATION_ALLOW_LEGACY_LOCAL_SOURCES=1 to opt in"
            )
        record["path"] = str(root)
        important = []
        if record["available"]:
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
    inventory = inventory or {"localSources": discover_local_sources()}
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


def build_skill_sync_command_payload(
    skill_record: dict[str, Any],
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("build skill sync command dependencies are required")
    SKILL_ROOT = dependencies["SKILL_ROOT"]
    looks_official_skill_uri = dependencies["looks_official_skill_uri"]

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


def build_skill_inspect_command_payload(
    skill_key: str,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build skill inspect command dependencies are required")
    SKILL_ROOT = dependencies["SKILL_ROOT"]

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


def inspect_skill_runtime_payload(
    skill_key: str,
    *,
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("inspect skill runtime dependencies are required")
    annotate_probe_results_display = dependencies["annotate_probe_results_display"]
    build_manifest_commands = dependencies["build_manifest_commands"]
    build_source_inventory = dependencies["build_source_inventory"]
    command_exists = dependencies["command_exists"]
    command_probe_available = dependencies["command_probe_available"]
    derive_runtime_remediation = dependencies["derive_runtime_remediation"]
    extract_command_hints_from_skill_md = dependencies["extract_command_hints_from_skill_md"]
    official_remote_manifest = dependencies["official_remote_manifest"]
    planned_skill_root = dependencies["planned_skill_root"]
    probe_failures_are_expected_state = dependencies["probe_failures_are_expected_state"]
    probe_failures_are_network_only = dependencies["probe_failures_are_network_only"]
    repository_file_is_metadata = dependencies["repository_file_is_metadata"]
    repository_files = dependencies["repository_files"]
    repository_is_effectively_empty = dependencies["repository_is_effectively_empty"]
    resolve_skill_root = dependencies["resolve_skill_root"]
    run_inspection_probe = dependencies["run_inspection_probe"]
    state_context = dependencies["state_context"]

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


def build_skill_inspection_catalog_payload(
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build skill inspection catalog dependencies are required")
    KNOWN_WORKNETS = dependencies["KNOWN_WORKNETS"]
    annotate_skill_inspection_catalog_payload = dependencies["annotate_skill_inspection_catalog_payload"]
    atomic_write_json = dependencies["atomic_write_json"]
    build_source_inventory = dependencies["build_source_inventory"]
    inspect_skill_runtime = dependencies["inspect_skill_runtime"]
    now_iso = dependencies["now_iso"]
    state_context = dependencies["state_context"]
    write_reference_export = dependencies["write_reference_export"]

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


def load_cached_skill_inspection_catalog_payload(
    state: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("load cached skill inspection catalog dependencies are required")
    annotate_skill_inspection_catalog_payload = dependencies["annotate_skill_inspection_catalog_payload"]
    load_json = dependencies["load_json"]
    state_context = dependencies["state_context"]

    state = state or state_context()
    payload = load_json(Path(state["cache"]) / "skill-inspections.json", None)
    if not isinstance(payload, dict):
        return None
    inspections = payload.get("inspections")
    if not isinstance(inspections, list):
        return None
    return annotate_skill_inspection_catalog_payload(payload)
