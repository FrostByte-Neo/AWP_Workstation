#!/usr/bin/env python3
"""Emit an epoch-style review from workstation state."""

import argparse

from awp_workstation_lib import build_epoch_review, print_json, public_review_view


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Emit the full internal review record.")
    args = parser.parse_args()
    review = build_epoch_review()
    print_json(review if args.full else public_review_view(review))


if __name__ == "__main__":
    main()
