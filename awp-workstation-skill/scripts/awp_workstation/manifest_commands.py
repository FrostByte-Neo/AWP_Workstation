"""Runtime manifest command construction helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from awp_workstation.manifests import load_runtime_manifests
from awp_workstation.utils import safe_slug


OFFICIAL_REMOTE_SKILL_MANIFESTS: dict[str, dict[str, Any]] = load_runtime_manifests()


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
    cwd = str(updated.get("cwd") or "")
    if skill_root is not None and cwd.startswith("/root/.nanobot/workspace/"):
        updated["cwd"] = str(skill_root)
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
