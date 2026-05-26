"""JSON-RPC helpers for AWP protocol calls."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from awp_workstation.runtime import DEFAULT_FETCH_USER_AGENT, parse_json_loose


DEFAULT_RPC_URL = os.environ.get("AWP_RPC_URL", "https://api.awp.sh/v2")


def rpc_call(method: str, params: Any = None, timeout: int = 15) -> dict[str, Any]:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {} if params is None else params,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        DEFAULT_RPC_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_FETCH_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            body_text = exc.read().decode("utf-8")
        except OSError:
            body_text = str(exc)
        return {"ok": False, "error": f"http {exc.code}", "body": parse_json_loose(body_text)}
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "error": str(exc), "body": None}
    payload = parse_json_loose(raw)
    if isinstance(payload, dict) and payload.get("error"):
        return {"ok": False, "error": payload["error"], "body": payload}
    return {"ok": True, "error": None, "body": payload}


def rpc_try_many(method: str, params_options: list[Any]) -> dict[str, Any]:
    errors: list[str] = []
    for params in params_options:
        response = rpc_call(method, params=params)
        if response.get("ok"):
            return response
        error = response.get("error")
        if error:
            errors.append(str(error))
    return {"ok": False, "error": "; ".join(errors) if errors else "no successful call", "body": None}


def rpc_result_body(payload: Any) -> Any:
    if isinstance(payload, dict) and "result" in payload:
        return payload["result"]
    return payload
