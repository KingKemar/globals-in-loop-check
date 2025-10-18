"""Core logic for detecting global variable usage inside loops."""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

__all__ = [
    "Violation",
    "load_gitignore",
    "GlobalUsageChecker",
    "find_globals",
    "analyze_file",
    "scan_paths",
]

DEFAULT_IGNORED_NAMES: Set[str] = {".venv", "venv"}
THIRD_PARTY_MARKERS: Set[str] = {"site-packages", "dist-packages"}


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

    project_root = _discover_project_root(Path.cwd().resolve())
    ignored_patterns = _build_ignored_patterns(project_root, respect_gitignore)

    violations: List[Violation] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue

        resolved_path = path.resolve()
        if not _is_within_project(resolved_path, project_root):
            continue
        if _path_has_third_party_marker(resolved_path):
            continue

        if resolved_path.is_dir():
            if _is_ignored(resolved_path.name, ignored_patterns):
                continue
            violations.extend(
                _scan_directory(
                    resolved_path,
                    project_root=project_root,
                    ignored=ignored_patterns,
                    respect_gitignore=respect_gitignore,
                )
            )
        elif resolved_path.is_file() and resolved_path.suffix == ".py":
            rel_path = os.path.relpath(resolved_path, project_root)
            if not _is_ignored(rel_path, ignored_patterns):
                violations.extend(analyze_file(resolved_path))
    return violations


def _scan_directory(
    directory: Path,
    *,
    project_root: Path,
    ignored: Set[str],
    respect_gitignore: bool,
) -> List[Violation]:
    project_root = project_root.resolve()
    directory = directory.resolve()
    violations: List[Violation] = []
    gitignore_cache: Dict[Path, Set[str]] = {}

    for root, dirs, files in os.walk(directory):
        root_path = Path(root).resolve()
        if not _is_within_project(root_path, project_root):
            dirs[:] = []
            continue
        if _path_has_third_party_marker(root_path):
            dirs[:] = []
            continue

        effective_ignored = ignored
        if respect_gitignore:
            additional = gitignore_cache.get(root_path)
            if additional is None:
                additional = load_gitignore(root_path)
                gitignore_cache[root_path] = additional
            if additional:
                effective_ignored = ignored | additional

        rel_root = os.path.relpath(root_path, project_root)
        if rel_root == ".":
            rel_root = ""

        dirs[:] = [
            d
            for d in dirs
            if not _is_ignored_dir(d, rel_root, root_path, project_root, effective_ignored)
        ]
        for file_name in files:
            if not file_name.endswith(".py"):
                continue
            file_path = root_path / file_name
            rel_path = os.path.join(rel_root, file_name) if rel_root else file_name
            if (
                _path_has_third_party_marker(file_path)
                or not _is_within_project(file_path, project_root)
                or _is_ignored(rel_path, effective_ignored)
            ):
                continue
            violations.extend(analyze_file(file_path))
    return violations


def _is_ignored(relative_path: str, ignored: Set[str]) -> bool:
    if not ignored:
        return False

    normalized = relative_path.strip().strip(os.sep)
    normalized = normalized.replace("\\", "/")
    parts = normalized.split("/") if normalized else []

    for pattern in ignored:
        pattern_normalized = pattern.strip().strip(os.sep).replace("\\", "/")
        if not pattern_normalized:
            continue
        if normalized == pattern_normalized:
            return True
        if normalized.startswith(f"{pattern_normalized}/"):
            return True
        if pattern_normalized in parts:
            return True
    return False


def _is_ignored_dir(
    entry: str,
    rel_root: str,
    current_root: Path,
    project_root: Path,
    ignored: Set[str],
) -> bool:
    dir_path = current_root / entry
    rel_path = os.path.join(rel_root, entry) if rel_root else entry
    return (
        _path_has_third_party_marker(dir_path)
        or not _is_within_project(dir_path, project_root)
        or _is_ignored(rel_path, ignored)
    )


def _is_within_project(path: Path, project_root: Path) -> bool:
    try:
        path.resolve().relative_to(project_root)
    except ValueError:
        return False
    return True


def _path_has_third_party_marker(path: Path) -> bool:
    parts = set(path.resolve().parts)
    return any(marker in parts for marker in THIRD_PARTY_MARKERS)


def _discover_project_root(start: Path) -> Path:
    current = start
    markers = {".git", "pyproject.toml", "setup.cfg", "setup.py"}
    while True:
        if any((current / marker).exists() for marker in markers):
            return current
        parent = current.parent
        if parent == current:
            return start
        current = parent


def _build_ignored_patterns(project_root: Path, respect_gitignore: bool) -> Set[str]:
    ignored = set(DEFAULT_IGNORED_NAMES)
    if respect_gitignore:
        ignored.update(load_gitignore(project_root))
    return ignored
