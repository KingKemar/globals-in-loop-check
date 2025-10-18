"""Command line interface for globals-in-loop-check."""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .checker import Violation, scan_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Detect usage of module-level global variables inside loops and "
            "comprehensions."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to scan (defaults to current directory).",
    )
    parser.add_argument(
        "--short",
        action="store_true",
        help="Only print violations without the remediation hint.",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Do not consult .gitignore files when walking directories.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    violations = scan_paths(args.paths, respect_gitignore=not args.no_gitignore)

    if violations:
        for violation in sorted(
            violations, key=lambda v: (str(v.path), v.line, v.variable)
        ):
            _print_violation(violation)

        if not args.short:
            print("\nHint: cache the global variable in a local variable before the loop.")
        return 1
    return 0


def _print_violation(violation: Violation) -> None:
    print(violation.format())


if __name__ == "__main__":
    sys.exit(main())
