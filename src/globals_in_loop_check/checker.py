"""Core logic for detecting global variable usage inside loops."""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Set

__all__ = [
    "Violation",
    "load_gitignore",
    "GlobalUsageChecker",
    "find_globals",
    "analyze_file",
    "scan_paths",
]


@dataclass(frozen=True)
class Violation:
    """Representation of a global usage violation."""

    path: Path
    line: int
    variable: str

    def format(self) -> str:
        """Return the violation as a flake8-style message."""
        path = self.path.as_posix()
        return (
            f"{path}:{self.line}:1: G001 "
            f"global variable '{self.variable}' used inside a loop"
        )


def load_gitignore(root_dir: Path) -> Set[str]:
    """Parse the .gitignore file in *root_dir* and return ignored paths.

    The parser is intentionally lightweight and only supports pattern forms used
    in this repository (plain names and directory suffixes). It is sufficient for
    excluding common directories such as ``__pycache__`` or ``.venv`` when
    walking the tree.
    """

    gitignore_path = Path(root_dir) / ".gitignore"
    ignored: Set[str] = set()
    if gitignore_path.exists():
        for line in gitignore_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ignored.add(line.rstrip("/"))
    return ignored


class GlobalUsageChecker(ast.NodeVisitor):
    """``ast.NodeVisitor`` collecting global usage in loops and comprehensions."""

    def __init__(self, globals_defined: Iterable[str]):
        self.globals_defined = set(globals_defined)
        self.violations: List[tuple[str, int]] = []

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        self._check_loop_body(node)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        self._check_loop_body(node)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:  # noqa: N802
        self._check_comp(node)
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:  # noqa: N802
        self._check_comp(node)
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:  # noqa: N802
        self._check_comp(node)
        self.generic_visit(node)

    def _check_loop_body(self, loop_node: ast.AST) -> None:
        for child in ast.walk(loop_node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                if child.id in self.globals_defined:
                    self.violations.append((child.id, child.lineno))

    def _check_comp(self, comp_node: ast.AST) -> None:
        for child in ast.walk(comp_node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                if child.id in self.globals_defined:
                    self.violations.append((child.id, child.lineno))


def find_globals(tree: ast.AST) -> List[str]:
    """Return a list of module-level variable names assigned in *tree*."""

    globals_: List[str] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    globals_.append(target.id)
    return globals_


def analyze_file(file_path: Path | str) -> List[Violation]:
    """Analyse a python file and return any detected violations."""

    path = Path(file_path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    globals_ = find_globals(tree)
    checker = GlobalUsageChecker(globals_)
    checker.visit(tree)
    return [Violation(path=path, line=line, variable=var) for var, line in checker.violations]


def scan_paths(
    paths: Sequence[Path | str] | None = None,
    *,
    respect_gitignore: bool = True,
) -> List[Violation]:
    """Scan the provided paths (files or directories) for violations."""

    if not paths:
        paths = [Path(".")]

    violations: List[Violation] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            violations.extend(_scan_directory(path, respect_gitignore=respect_gitignore))
        elif path.is_file() and path.suffix == ".py":
            violations.extend(analyze_file(path))
    return violations


def _scan_directory(directory: Path, *, respect_gitignore: bool) -> List[Violation]:
    ignored: Set[str] = load_gitignore(directory) if respect_gitignore else set()
    violations: List[Violation] = []

    for root, dirs, files in os.walk(directory):
        rel_root = os.path.relpath(root, directory)
        if rel_root == ".":
            rel_root = ""

        dirs[:] = [
            d
            for d in dirs
            if not _is_ignored(os.path.join(rel_root, d), ignored)
        ]
        for file_name in files:
            if not file_name.endswith(".py"):
                continue
            rel_path = os.path.join(rel_root, file_name)
            if _is_ignored(rel_path, ignored):
                continue
            file_path = Path(root, file_name)
            violations.extend(analyze_file(file_path))
    return violations


def _is_ignored(relative_path: str, ignored: Set[str]) -> bool:
    relative_path = relative_path.lstrip("./")
    return any(
        relative_path == pattern
        or relative_path.startswith(f"{pattern}/")
        for pattern in ignored
    )
