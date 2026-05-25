"""Notification adapter envelopes and delivery helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from email.message import EmailMessage
from typing import Any, Optional


SUPPORTED_NOTIFICATION_ADAPTER_KEYS = [
    "codex-heartbeat",
    "cron",
    "desktop",
    "telegram-webhook",
    "discord-webhook",
    "email",
]


def _render_monitor_message(report: dict[str, Any]) -> tuple[str, str]:
    headline = str(report.get("headline") or "Workstation update").strip() or "Workstation update"
    body = str(report.get("message") or report.get("reason") or headline).strip() or headline
    return headline, body


def build_notification_delivery_payload(
    report: Any,
    *,
    adapter_key: str,
    webhook_url: Optional[str] = None,
    email_to: Optional[str] = None,
) -> dict[str, Any]:
    payload = report if isinstance(report, dict) else {}
    headline, body = _render_monitor_message(payload)
    digest = str(payload.get("digest") or "").strip() or None
    base = {
        "adapter": adapter_key,
        "headline": headline,
        "message": body,
        "digest": digest,
        "reminderType": payload.get("reminderType"),
        "status": payload.get("status"),
        "worknetKey": payload.get("worknetKey"),
        "worknetName": payload.get("worknetName"),
        "currentTask": payload.get("currentTask"),
        "nextCheckAt": payload.get("nextCheckAt"),
    }
    if adapter_key == "codex-heartbeat":
        return {
            **base,
            "delivery": {
                "kind": "heartbeat",
                "payload": {
                    "headline": headline,
                    "message": body,
                    "digest": digest,
                    "reminderType": payload.get("reminderType"),
                    "nextCheckAt": payload.get("nextCheckAt"),
                },
            },
        }
    if adapter_key == "cron":
        return {
            **base,
            "delivery": {
                "kind": "cron",
                "payload": {
                    "summary": headline,
                    "detail": body,
                },
            },
        }
    if adapter_key == "desktop":
        return {
            **base,
            "delivery": {
                "kind": "desktop",
                "command": ["notify-send", headline, body],
                "available": bool(shutil.which("notify-send")),
            },
        }
    if adapter_key == "telegram-webhook":
        return {
            **base,
            "delivery": {
                "kind": "webhook",
                "platform": "telegram",
                "url": webhook_url,
                "json": {"text": f"{headline}\n{body}"},
            },
        }
    if adapter_key == "discord-webhook":
        return {
            **base,
            "delivery": {
                "kind": "webhook",
                "platform": "discord",
                "url": webhook_url,
                "json": {"content": f"**{headline}**\n{body}"},
            },
        }
    if adapter_key == "email":
        return {
            **base,
            "delivery": {
                "kind": "email",
                "to": email_to,
                "subject": headline,
                "body": body,
                "available": bool(shutil.which("sendmail")),
            },
        }
    raise ValueError(f"unsupported adapter: {adapter_key}")


def dispatch_monitor_notification_payload(
    report: Any,
    *,
    adapter_key: str,
    webhook_url: Optional[str] = None,
    email_to: Optional[str] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    payload = build_notification_delivery_payload(
        report,
        adapter_key=adapter_key,
        webhook_url=webhook_url,
        email_to=email_to,
    )
    delivery = payload.get("delivery", {}) if isinstance(payload.get("delivery"), dict) else {}
    if dry_run:
        return {
            **payload,
            "deliveryStatus": "dry_run",
        }
    kind = str(delivery.get("kind") or "").strip()
    if kind in {"heartbeat", "cron"}:
        return {
            **payload,
            "deliveryStatus": "emitted",
        }
    if kind == "desktop":
        command = delivery.get("command")
        if not isinstance(command, list) or not shutil.which("notify-send"):
            return {
                **payload,
                "deliveryStatus": "unavailable",
                "reason": "notify-send is not available",
            }
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return {
            **payload,
            "deliveryStatus": "emitted" if result.returncode == 0 else "failed",
            "result": {
                "code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        }
    if kind == "webhook":
        url = str(delivery.get("url") or "").strip()
        if not url:
            return {
                **payload,
                "deliveryStatus": "unavailable",
                "reason": "webhook url is required",
            }
        request = urllib.request.Request(
            url,
            data=json.dumps(delivery.get("json", {}), ensure_ascii=True).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read().decode("utf-8", errors="replace")
                return {
                    **payload,
                    "deliveryStatus": "emitted",
                    "result": {
                        "code": response.status,
                        "body": body,
                    },
                }
        except urllib.error.URLError as exc:
            return {
                **payload,
                "deliveryStatus": "failed",
                "reason": str(exc),
            }
    if kind == "email":
        recipient = str(delivery.get("to") or "").strip()
        if not recipient:
            return {
                **payload,
                "deliveryStatus": "unavailable",
                "reason": "email recipient is required",
            }
        sendmail = shutil.which("sendmail")
        if not sendmail:
            return {
                **payload,
                "deliveryStatus": "unavailable",
                "reason": "sendmail is not available",
            }
        message = EmailMessage()
        message["To"] = recipient
        message["Subject"] = str(delivery.get("subject") or "Workstation update")
        message["From"] = "awp-workstation@localhost"
        message.set_content(str(delivery.get("body") or ""))
        result = subprocess.run(
            [sendmail, "-t", "-oi"],
            input=message.as_string(),
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            **payload,
            "deliveryStatus": "emitted" if result.returncode == 0 else "failed",
            "result": {
                "code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        }
    return {
        **payload,
        "deliveryStatus": "unsupported",
    }
