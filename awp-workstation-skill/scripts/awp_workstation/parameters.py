"""Parameterized command and confirmation argv helpers."""

from __future__ import annotations

import re
from typing import Any, Optional

from awp_workstation.commands import render_argv


PLACEHOLDER_TOKEN_RE = re.compile(r"^<([^>]+)>$")


def placeholder_spec(token: str, *, param_name: Optional[str]) -> Optional[dict[str, Any]]:
    match = PLACEHOLDER_TOKEN_RE.match(token)
    if not match:
        return None
    raw = match.group(1).strip()
    if not raw:
        return None
    choices = [part.strip() for part in raw.split("|") if part.strip()]
    name = (param_name or raw).strip().lower().replace(" ", "_").replace("-", "_")
    spec = {
        "name": name,
        "placeholder": token,
        "prompt": raw,
    }
    if len(choices) > 1:
        spec["choices"] = choices
    return spec


def extract_command_parameter_schema(argv: list[str]) -> list[dict[str, Any]]:
    schema: list[dict[str, Any]] = []
    last_flag: Optional[str] = None
    for item in argv:
        text = str(item)
        if text.startswith("--"):
            last_flag = text[2:].replace("-", "_")
            continue
        spec = placeholder_spec(text, param_name=last_flag)
        if spec is not None:
            schema.append(spec)
            last_flag = None
        elif text and not text.startswith("-"):
            last_flag = None
    return schema


def parse_input_assignments(values: Optional[list[str]]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values or []:
        if "=" not in str(item):
            continue
        key, value = str(item).split("=", 1)
        key = key.strip().lower().replace("-", "_")
        if key:
            parsed[key] = value
    return parsed


def build_confirmation_execute_command(label: str, parameter_schema: list[dict[str, Any]]) -> str:
    argv = [
        "python3",
        "scripts/run-workstation.py",
        "--mode",
        "autopilot",
        "--confirm-label",
        label,
    ]
    for spec in parameter_schema:
        name = str(spec.get("name") or "value")
        prompt = str(spec.get("prompt") or "value")
        argv.extend(["--input", f"{name}={prompt}"])
    argv.append("--execute")
    return render_argv(argv)


def resolve_parameterized_argv(
    argv: list[str],
    parameter_schema: list[dict[str, Any]],
    provided_inputs: dict[str, str],
) -> tuple[Optional[list[str]], list[str]]:
    required_names = [str(spec.get("name")) for spec in parameter_schema if spec.get("name")]
    missing = [name for name in required_names if name not in provided_inputs]
    if missing:
        return None, [f"missing input: {name}" for name in missing]
    placeholder_to_value: dict[str, str] = {}
    errors: list[str] = []
    for spec in parameter_schema:
        name = str(spec.get("name") or "")
        placeholder = str(spec.get("placeholder") or "")
        if not name or not placeholder:
            continue
        value = provided_inputs.get(name, "")
        choices = spec.get("choices")
        if isinstance(choices, list) and choices and value not in [str(choice) for choice in choices]:
            errors.append(f"invalid value for {name}: {value}")
            continue
        placeholder_to_value[placeholder] = value
    if errors:
        return None, errors
    resolved: list[str] = []
    for item in argv:
        text = str(item)
        resolved.append(placeholder_to_value.get(text, text))
    return resolved, []
