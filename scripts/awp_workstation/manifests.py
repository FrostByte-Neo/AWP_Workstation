"""Official skill/runtime manifest loading."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


DATA_ROOT = Path(__file__).resolve().parent / "data"
RUNTIME_MANIFESTS_PATH = DATA_ROOT / "runtime-manifests.json"


def load_runtime_manifests(path: Path = RUNTIME_MANIFESTS_PATH) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"runtime manifest data must be an object: {path}")
    manifests: dict[str, dict[str, Any]] = {}
    for key, item in payload.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("runtime manifest key must be a non-empty string")
        if not isinstance(item, dict):
            raise ValueError(f"runtime manifest for {key} is not an object")
        manifests[key.strip()] = copy.deepcopy(item)
    return manifests
