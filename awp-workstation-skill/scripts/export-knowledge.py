#!/usr/bin/env python3
"""Export workstation-owned AWP knowledge as JSON."""

from awp_workstation_lib import build_knowledge_catalog, print_json


def main() -> None:
    print_json(build_knowledge_catalog())


if __name__ == "__main__":
    main()
