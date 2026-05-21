#!/usr/bin/env python3
"""Build a workstation playbook for one worknet."""

import argparse

from awp_workstation_lib import build_work_playbook, print_json, public_playbook_view


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worknet", required=True, help="Worknet key, alias, or ID.")
    parser.add_argument("--full", action="store_true", help="Emit the full internal playbook record.")
    args = parser.parse_args()
    playbook = build_work_playbook(args.worknet)
    print_json(playbook if args.full else public_playbook_view(playbook))


if __name__ == "__main__":
    main()
