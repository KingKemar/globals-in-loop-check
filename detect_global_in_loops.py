import ast
import sys
import os
from pathlib import Path


def load_gitignore(root_dir):
    gitignore_path = Path(root_dir) / ".gitignore"
    ignored = set()
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                ignored.add(line.rstrip("/"))
    return ignored


class GlobalUsageChecker(ast.NodeVisitor):
    def __init__(self, globals_defined):
        self.globals_defined = set(globals_defined)
        self.violations = []

    def visit_For(self, node):
        self._check_loop_body(node)
        self.generic_visit(node)

    def visit_While(self, node):
        self._check_loop_body(node)
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self._check_comp(node)
        self.generic_visit(node)

    def visit_SetComp(self, node):
        self._check_comp(node)
        self.generic_visit(node)

    def visit_DictComp(self, node):
        self._check_comp(node)
        self.generic_visit(node)

    def _check_loop_body(self, loop_node):
        for child in ast.walk(loop_node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                if child.id in self.globals_defined:
                    self.violations.append((child.id, child.lineno))

    def _check_comp(self, comp_node):
        for child in ast.walk(comp_node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                if child.id in self.globals_defined:
                    self.violations.append((child.id, child.lineno))


def find_globals(tree):
    globals_ = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    globals_.append(target.id)
    return globals_


def analyze_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    globals_ = find_globals(tree)
    checker = GlobalUsageChecker(globals_)
    checker.visit(tree)
    return checker.violations


def scan_directory(directory, short_mode=False):
    ignored = load_gitignore(directory)
    total_violations = 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if os.path.relpath(os.path.join(root, d), directory) not in ignored]
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), directory)
            if any(rel_path.startswith(ig) for ig in ignored):
                continue
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                violations = analyze_file(file_path)
                for var, line in violations:
                    print(f"{file_path}:{line}:1: G001 global variable '{var}' used inside a loop")
                total_violations += len(violations)

    if total_violations > 0 and not short_mode:
        print("\nHint: cache the global variable in a local variable before the loop.")

    if total_violations > 0:
        sys.exit(1)


if __name__ == "__main__":
    short_mode = "--short" in sys.argv
    path_args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    path = path_args[0] if path_args else "."
    scan_directory(path, short_mode=short_mode)
