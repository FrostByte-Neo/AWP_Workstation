#!/usr/bin/env python3
"""Query the workstation glossary by term or alias."""

from __future__ import annotations

import argparse

from awp_workstation_lib import build_glossary_query_result, print_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--term", required=True, help="Glossary term or alias.")
    args = parser.parse_args()
    print_json(build_glossary_query_result(args.term))


if __name__ == "__main__":
    main()
