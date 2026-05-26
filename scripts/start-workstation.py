#!/usr/bin/env python3
"""Agent-facing entry point for the awp start flow."""

from awp_workstation_lib import build_start_response, print_json


def main() -> None:
    print_json(build_start_response())


if __name__ == "__main__":
    main()
