#!/usr/bin/env python3
"""Inspect one workstation skill or dependency runtime."""

from __future__ import annotations

import argparse

from awp_workstation_lib import inspect_skill_runtime, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-key", required=True, help="Skill key such as awp-skill, gov, ardi, mine, or kya.")
    args = parser.parse_args()
    print_json(inspect_skill_runtime(args.skill_key))


if __name__ == "__main__":
    main()
