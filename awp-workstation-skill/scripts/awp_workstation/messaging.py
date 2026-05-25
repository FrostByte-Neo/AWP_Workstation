"""Plain-language workstation message helpers."""

from __future__ import annotations

from typing import Any, Optional

from awp_workstation.narratives import canonical_topic_narrative, canonical_worknet_plain_text
from awp_workstation.text import strip_sentence_end


def build_preflight_plain_language_summary(
    next_action: str,
    *,
    knowledge_review_queue_summary: Optional[dict[str, Any]] = None,
    include_queue_note: bool = True,
) -> str:
    next_action = str(next_action or "").strip()
    protocol_intro = (
        (canonical_topic_narrative("protocol-core") or {}).get("plain")
        or "AWP is a network that helps agents find work, coordinate execution, and earn rewards."
    )
    message = (
        f"{protocol_intro} The workstation first checks the agent work wallet, registration state, and runnable WorkNets, "
        "and it requires confirmation before staking, voting, ordering, or other value-moving actions. It never asks for a private key."
    )
    if next_action == "install_awp_skill_dependency":
        message += " The official RootNet dependency is missing, so the next step is to install awp-skill."
    elif next_action in {"run_awp_skill_registration", "register_agent"}:
        message += " The next step is to continue official gasless registration."
    elif next_action == "retry_registration_preflight":
        message += " The registration runtime is present, but the AWP API is currently unreachable, so registration submission should wait."
    elif next_action == "install_or_setup_wallet":
        message += " Prepare the agent work wallet before registration and WorkNet selection."
    elif next_action == "prepare_registration_runtime":
        message += " The wallet is mostly ready, but the registration runtime still needs setup."
    elif next_action == "scan_worknets":
        message += " Wallet and registration checks passed; the next step is to choose a suitable WorkNet."
    elif next_action == "resume_previous_run":
        message += " A previous work record is available and can be resumed."
    elif next_action == "resume_runtime_guidance":
        message += " The previous run left explicit runtime guidance, so no WorkNet reselection is needed."
    elif next_action == "resume_pending_confirmations":
        message += " Handle pending confirmations before continuing work."
    elif next_action == "monitor_background_runs":
        message += " Background work is already running, so inspect status before starting another route."
    if include_queue_note and isinstance(knowledge_review_queue_summary, dict) and knowledge_review_queue_summary.get("hasPendingReviews"):
        pending = int(knowledge_review_queue_summary.get("pendingReviewCount", 0) or 0)
        message += f" {pending} knowledge items need review because upstream sources changed recently."
    return message.strip()


def prepend_canonical_worknet_plain(message: Optional[str], worknet_key: Optional[str]) -> Optional[str]:
    body = str(message or "").strip()
    plain = canonical_worknet_plain_text(worknet_key)
    if not plain:
        return body or None
    if not body:
        return plain
    if body.startswith(plain):
        return body
    return f"{plain} {body}".strip()


def append_runtime_maturity_note(base: Optional[str], note: Optional[str]) -> Optional[str]:
    body = str(base or "").strip()
    extra = str(note or "").strip()
    if not body:
        return extra or None
    if not extra or extra in body:
        return body
    return f"{strip_sentence_end(body)}. {extra}".strip()
