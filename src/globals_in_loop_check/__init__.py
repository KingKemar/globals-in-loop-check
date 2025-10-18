"""globals-in-loop-check package."""
from .checker import (
    GlobalUsageChecker,
    Violation,
    analyze_file,
    find_globals,
    load_gitignore,
    scan_paths,
)

__all__ = [
    "GlobalUsageChecker",
    "Violation",
    "analyze_file",
    "find_globals",
    "load_gitignore",
    "scan_paths",
]
