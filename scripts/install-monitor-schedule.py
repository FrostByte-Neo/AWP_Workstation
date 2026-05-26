#!/usr/bin/env python3
"""Render monitor scheduling templates for cron or systemd."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "deploy"


def render_template(path: Path, replacements: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def adapter_args(adapter: str, *, webhook_url: str | None, email_to: str | None) -> str:
    parts = [f"--emit-adapter {adapter}", "--record-delivery"]
    if webhook_url:
        parts.append(f"--webhook-url {json.dumps(webhook_url)}")
    if email_to:
        parts.append(f"--email-to {json.dumps(email_to)}")
    return " ".join(parts)


def write_or_print(target: Path, content: str, *, print_only: bool) -> None:
    if print_only:
        print(f"--- {target.name} ---")
        print(content.rstrip())
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["cron", "systemd"], required=True, help="Which scheduler template set to render.")
    parser.add_argument("--target-dir", required=True, help="Directory where rendered files should be written.")
    parser.add_argument("--state-root", help="State root to embed in the rendered templates.")
    parser.add_argument("--python-bin", default=sys.executable, help="Python interpreter to embed in the rendered templates.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root to embed in the rendered templates.")
    parser.add_argument(
        "--adapter",
        choices=["codex-heartbeat", "cron", "desktop", "telegram-webhook", "discord-webhook", "email"],
        default="codex-heartbeat",
        help="Notification adapter to embed in the rendered command.",
    )
    parser.add_argument("--webhook-url", help="Optional webhook URL for webhook adapters.")
    parser.add_argument("--email-to", help="Optional email recipient for email adapter.")
    parser.add_argument("--print-only", action="store_true", help="Print rendered files instead of writing them.")
    args = parser.parse_args()

    state_root = args.state_root or str(Path.home() / ".awp-workstation")
    monitor_args = adapter_args(
        args.adapter,
        webhook_url=args.webhook_url,
        email_to=args.email_to,
    )
    replacements = {
        "__REPO_ROOT__": str(Path(args.repo_root).resolve()),
        "__PYTHON__": str(Path(args.python_bin).resolve()),
        "__STATE_ROOT__": state_root,
        "--emit-adapter codex-heartbeat --record-delivery": monitor_args,
    }

    target_dir = Path(args.target_dir)
    rendered: list[dict[str, str]] = []
    if args.mode == "cron":
        template = TEMPLATE_ROOT / "cron" / "awp-workstation-monitor.cron"
        target = target_dir / template.name
        content = render_template(template, replacements)
        write_or_print(target, content, print_only=args.print_only)
        rendered.append({"template": str(template), "target": str(target)})
    else:
        for name in ("awp-workstation-monitor.service", "awp-workstation-monitor.timer"):
            template = TEMPLATE_ROOT / "systemd" / name
            target = target_dir / name
            content = render_template(template, replacements)
            write_or_print(target, content, print_only=args.print_only)
            rendered.append({"template": str(template), "target": str(target)})

    payload = {
        "ok": True,
        "mode": args.mode,
        "targetDir": str(target_dir),
        "stateRoot": state_root,
        "pythonBin": str(Path(args.python_bin).resolve()),
        "repoRoot": str(Path(args.repo_root).resolve()),
        "adapter": args.adapter,
        "printOnly": bool(args.print_only),
        "rendered": rendered,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
