"""General workstation utility helpers."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from awp_workstation.i18n import sanitize_public_payload


WORKNET_ID_BASE = 100_000_000
CHAIN_ALIAS_TO_ID = {
    "ethereum": 1,
    "bsc": 56,
    "base": 8453,
    "arbitrum": 42161,
    "optimism": 10,
    "polygon": 137,
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
    print(json.dumps(sanitize_public_payload(payload), ensure_ascii=True, indent=2))


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


def normalize_worknet_token(text: str) -> str:
    value = text.strip().lower().replace("-", " ").replace("_", " ")
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
