"""Reference export write helpers."""

from __future__ import annotations

from typing import Any

from awp_workstation.state import REFERENCE_EXPORT_ROOT
from awp_workstation.storage import atomic_write_json


def write_reference_export(filename: str, payload: Any) -> str:
    REFERENCE_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REFERENCE_EXPORT_ROOT / filename
    atomic_write_json(path, payload)
    return str(path)
