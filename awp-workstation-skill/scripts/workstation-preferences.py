#!/usr/bin/env python3
"""Read or update workstation user preferences in JSON."""

import argparse

from awp_workstation_lib import (
    ensure_user_preferences,
    now_iso,
    print_json,
    public_workstation_preferences_view,
    state_context,
    update_user_preferences,
)


def parse_bool_flag(raw: str) -> bool:
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {raw}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preferred-worknet", help="Save one default worknet key, alias, or ID.")
    parser.add_argument("--allow-asset-actions", type=parse_bool_flag, help="Whether asset actions may be auto-enabled by default.")
    parser.add_argument("--autopilot-mode", help="Save the default autopilot mode label.")
    parser.add_argument("--allow-third-party-skills", type=parse_bool_flag, help="Whether third-party skills may be considered by default.")
    parser.add_argument("--observe-before-predict-hours", type=int, help="Default observation window for Predict before active running.")
    parser.add_argument("--notification-cooldown-minutes", type=int, help="Minimum minutes before repeating the same reminder digest.")
    parser.add_argument("--quiet-hours-start", help="Quiet hours start in HH:MM local time.")
    parser.add_argument("--quiet-hours-end", help="Quiet hours end in HH:MM local time.")
    parser.add_argument("--remind-on-earnings-change", type=parse_bool_flag, help="Whether earnings changes should trigger reminders.")
    parser.add_argument("--remind-on-failure", type=parse_bool_flag, help="Whether failures should trigger reminders.")
    parser.add_argument("--remind-on-stall", type=parse_bool_flag, help="Whether long-running attention states should re-remind.")
    parser.add_argument(
        "--background-auto-recovery",
        choices=["manual", "pause", "restart"],
        help="Default background recovery policy when a runtime stalls or exits.",
    )
    parser.add_argument("--risk-profile", help="Save the workstation risk profile label.")
    parser.add_argument("--full", action="store_true", help="Emit the full internal preference update record.")
    args = parser.parse_args()

    has_updates = any(
        value is not None
        for value in (
            args.preferred_worknet,
            args.allow_asset_actions,
            args.autopilot_mode,
            args.allow_third_party_skills,
            args.observe_before_predict_hours,
            args.notification_cooldown_minutes,
            args.quiet_hours_start,
            args.quiet_hours_end,
            args.remind_on_earnings_change,
            args.remind_on_failure,
            args.remind_on_stall,
            args.background_auto_recovery,
            args.risk_profile,
        )
    )

    if has_updates:
        report = update_user_preferences(
            preferred_worknet=args.preferred_worknet,
            allow_asset_actions=args.allow_asset_actions,
            autopilot_mode=args.autopilot_mode,
            allow_third_party_skills=args.allow_third_party_skills,
            observe_before_predict_hours=args.observe_before_predict_hours,
            notification_cooldown_minutes=args.notification_cooldown_minutes,
            quiet_hours_start=args.quiet_hours_start,
            quiet_hours_end=args.quiet_hours_end,
            remind_on_earnings_change=args.remind_on_earnings_change,
            remind_on_failure=args.remind_on_failure,
            remind_on_stall=args.remind_on_stall,
            background_auto_recovery=args.background_auto_recovery,
            risk_profile=args.risk_profile,
        )
    else:
        state = state_context()
        preferences = ensure_user_preferences(state)
        report = {
            "generatedAt": now_iso(),
            "message": "Current Workstation preferences.",
            "appliedChanges": [],
            "userPreferences": preferences,
            "stateRoot": state["root"],
        }

    print_json(report if args.full else public_workstation_preferences_view(report))


if __name__ == "__main__":
    main()
