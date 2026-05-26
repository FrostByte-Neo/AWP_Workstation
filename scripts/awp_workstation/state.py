"""State root discovery and workstation state bootstrap helpers."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from awp_workstation.storage import atomic_write_json, load_json
from awp_workstation.utils import now_iso


SKILL_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_EXPORT_ROOT = SKILL_ROOT / "references" / "generated"
STATE_ENV_VAR = "AWP_WORKSTATION_HOME"
DEFAULT_STATE_ROOT = Path.home() / ".awp-workstation"
DEFAULT_FALLBACK_STATE_ROOT = Path("/tmp/awp-workstation")
VERIFICATION_STATE_SEED_FILES = {
    "knowledge-catalog.json": ("cache", "knowledge-catalog.json"),
    "capability-catalog.json": ("cache", "capability-scan.json"),
    "official-live-worknets.json": ("cache", "official-live-worknets.json"),
    "skill-inspections.json": ("cache", "skill-inspections.json"),
    "concept-catalog.json": ("cache", "concept-catalog.json"),
    "source-drift.json": ("cache", "source-drift.json"),
    "source-impact.json": ("cache", "source-impact.json"),
    "source-snapshot.json": ("cache", "source-snapshot.json"),
    "knowledge-review-queue.json": ("cache", "knowledge-review-queue.json"),
    "topic-freshness.json": ("cache", "topic-freshness.json"),
    "source-facts.json": ("cache", "source-facts.json"),
    "source-evidence.json": ("cache", "source-evidence.json"),
    "topic-dossiers.json": ("cache", "topic-dossiers.json"),
    "glossary.json": ("cache", "glossary.json"),
    "skill-registry.json": ("skills", "install-status.json"),
}


def looks_like_state_root(root: Path) -> bool:
    markers = [
        root / "skills" / "install-status.json",
        root / "cache" / "preflight.json",
        root / "cache" / "workstation-monitor.json",
        root / "cache" / "workstation-state.json",
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

    workspace_root = SKILL_ROOT
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
        "cache/workstation-monitor.json",
        "cache/workstation-state.json",
        "playbooks/last-selected.json",
    ):
        rewrite_json_state_paths(target_root / rel, source_root, target_root_str)
    playbooks_root = target_root / "playbooks"
    if playbooks_root.exists():
        for item in playbooks_root.glob("*.json"):
            rewrite_json_state_paths(item, source_root, target_root_str)
    rewrite_jsonl_state_paths(target_root / "runs" / "history.jsonl", source_root, target_root_str)
    rewrite_jsonl_state_paths(target_root / "runs" / "timeline.jsonl", source_root, target_root_str)


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
        "cache/workstation-status.json",
        "cache/workstation-monitor.json",
        "cache/workstation-state.json",
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
    warnings: list[str] = []

    def build_layout(root: Path) -> dict[str, Any]:
        root.mkdir(parents=True, exist_ok=True)
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
        # Probe write access up front so later bootstrap/repair logic does not
        # fail deep inside atomic JSON writes on read-only homes or containers.
        with tempfile.NamedTemporaryFile(dir=layout["runs"], delete=True):
            pass
        return layout

    try:
        layout = build_layout(preferred)
        root = preferred
    except OSError:
        root = DEFAULT_FALLBACK_STATE_ROOT
        layout = build_layout(root)
        warnings.append(
            f"state root {preferred} was not fully writable; using fallback {root}"
        )

    try:
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
    except OSError:
        if root != DEFAULT_FALLBACK_STATE_ROOT:
            warnings.append(
                f"state root {root} could not complete bootstrap/repair writes; using fallback {DEFAULT_FALLBACK_STATE_ROOT}"
            )
            root = DEFAULT_FALLBACK_STATE_ROOT
            layout = build_layout(root)
            layout["bootstrap"] = None
        else:
            raise

    layout["warnings"] = warnings
    layout["preferredRoot"] = str(preferred)
    layout["root"] = str(root)
    return layout


def seed_verification_state_from_reference_exports(
    state: Optional[dict[str, Any]] = None,
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    state = state or state_context()
    seeded: list[dict[str, Any]] = []
    for source_name, (bucket, target_name) in VERIFICATION_STATE_SEED_FILES.items():
        source = REFERENCE_EXPORT_ROOT / source_name
        if not source.exists():
            continue
        target_root = Path(str(state.get(bucket) or ""))
        if not str(target_root):
            continue
        target_root.mkdir(parents=True, exist_ok=True)
        target = target_root / target_name
        if target.exists() and not overwrite:
            continue
        shutil.copy2(source, target)
        seeded.append(
            {
                "source": str(source.relative_to(SKILL_ROOT)),
                "target": str(target),
            }
        )
    return {
        "generatedAt": now_iso(),
        "seeded": seeded,
        "overwrite": overwrite,
    }
