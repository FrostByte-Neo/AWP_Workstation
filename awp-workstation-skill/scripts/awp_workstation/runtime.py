"""Runtime command, HTTP, and output helpers for the workstation."""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any, Optional


DEFAULT_FETCH_USER_AGENT = "awp-workstation-skill/0.1.0"


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def parse_json_loose(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def run_command(
    argv: list[str], cwd: Optional[str] = None, timeout: int = 120
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "code": 127, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "code": 124,
            "stdout": "",
            "stderr": f"timed out after {timeout}s",
        }
    return {
        "ok": result.returncode == 0,
        "code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def trim_output(
    value: Any,
    limit: int = 800,
    *,
    max_items: int = 5,
    max_keys: int = 24,
    max_depth: int = 5,
    _depth: int = 0,
) -> Any:
    if isinstance(value, str):
        if len(value) > limit:
            return value[:limit] + "...(truncated)"
        return value
    if isinstance(value, list):
        if _depth >= max_depth:
            return [f"...({len(value)} items truncated at depth {max_depth})"] if value else []
        trimmed = [
            trim_output(
                item,
                limit=limit,
                max_items=max_items,
                max_keys=max_keys,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            trimmed.append(f"...({len(value) - max_items} more items truncated)")
        return trimmed
    if isinstance(value, dict):
        if _depth >= max_depth:
            return {"_truncated": f"{len(value)} keys hidden at depth {max_depth}"}
        items = list(value.items())
        trimmed: dict[str, Any] = {}
        for key, item in items[:max_keys]:
            trimmed[str(key)] = trim_output(
                item,
                limit=limit,
                max_items=max_items,
                max_keys=max_keys,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
        if len(items) > max_keys:
            trimmed["_truncatedKeys"] = len(items) - max_keys
        return trimmed
    return value


def command_help_probe(argv: list[str], timeout: int = 20) -> dict[str, Any]:
    result = run_command(argv, timeout=timeout)
    combined = "\n".join(part for part in [result.get("stdout", ""), result.get("stderr", "")] if part)
    return {
        "ok": result.get("ok", False),
        "code": result.get("code"),
        "text": trim_output(combined, limit=1200),
    }


def fetch_url(url: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": DEFAULT_FETCH_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            headers = dict(response.headers.items())
            content_type = response.headers.get_content_type()
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        body = b""
        headers = dict(exc.headers.items()) if exc.headers else {}
        content_type = headers.get("Content-Type", "")
        return {
            "ok": False,
            "status": exc.code,
            "headers": headers,
            "contentType": content_type,
            "body": body,
            "error": f"http {exc.code}",
        }
    except (urllib.error.URLError, OSError) as exc:
        return {
            "ok": False,
            "status": None,
            "headers": {},
            "contentType": "",
            "body": b"",
            "error": str(exc),
        }
    return {
        "ok": True,
        "status": status,
        "headers": headers,
        "contentType": content_type,
        "body": body,
        "error": None,
    }
