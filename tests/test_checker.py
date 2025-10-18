import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from globals_in_loop_check import GlobalUsageChecker, analyze_file, find_globals, scan_paths


def run_checker_on_code(code, globals_defined):
    tree = ast.parse(code)
    checker = GlobalUsageChecker(globals_defined)
    checker.visit(tree)
    return checker.violations


def test_for_loop_detects_global_usage():
    code = """
GLOBAL = 10
def func():
    for i in range(5):
        print(GLOBAL)
"""
    violations = run_checker_on_code(code, ["GLOBAL"])
    assert len(violations) == 1
    assert violations[0][0] == "GLOBAL"


def test_for_loop_no_violation_with_local_copy():
    code = """
GLOBAL = 10
def func():
    g = GLOBAL
    for i in range(5):
        print(g)
"""
    violations = run_checker_on_code(code, ["GLOBAL"])
    assert violations == []


def test_while_loop_detects_global_usage():
    code = """
GLOBAL = True
def func():
    while GLOBAL:
        break
"""
    violations = run_checker_on_code(code, ["GLOBAL"])
    assert len(violations) == 1


def test_list_comprehension_detects_global_usage():
    code = """
GLOBAL = 3
def func():
    return [x * GLOBAL for x in range(5)]
"""
    violations = run_checker_on_code(code, ["GLOBAL"])
    assert len(violations) == 1


def test_set_comprehension_detects_global_usage():
    code = """
GLOBAL = 3
def func():
    return {x * GLOBAL for x in range(5)}
"""
    violations = run_checker_on_code(code, ["GLOBAL"])
    assert len(violations) == 1


def test_dict_comprehension_detects_global_usage():
    code = """
GLOBAL = 3
def func():
    return {x: GLOBAL for x in range(5)}
"""
    violations = run_checker_on_code(code, ["GLOBAL"])
    assert len(violations) == 1


def test_no_violation_when_no_global_used():
    code = """
GLOBAL = 3
def func():
    for i in range(3):
        print(i)
"""
    violations = run_checker_on_code(code, ["GLOBAL"])
    assert violations == []


def test_find_globals_detects_assignments():
    tree = ast.parse("A = 1\nB = 2\n")
    globals_found = find_globals(tree)
    assert set(globals_found) == {"A", "B"}


def test_analyze_file(tmp_path):
    code = """
GLOBAL = 10
def func():
    for i in range(2):
        print(GLOBAL)
"""
    f = tmp_path / "sample.py"
    f.write_text(code)
    violations = analyze_file(f)
    assert len(violations) == 1
    assert violations[0].variable == "GLOBAL"


def test_scan_paths_handles_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = """
GLOBAL = 10
def func():
    for i in range(2):
        print(GLOBAL)
"""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    target = pkg / "sample.py"
    target.write_text(code)

    violations = scan_paths([pkg])
    assert len(violations) == 1
    assert violations[0].path == target


def test_scan_paths_ignores_non_python_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "pkg"
    folder.mkdir()
    (folder / "readme.txt").write_text("GLOBAL = 1\n")

    violations = scan_paths([folder])
    assert violations == []


def test_scan_paths_accepts_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = """
GLOBAL = 10
def func():
    for i in range(2):
        print(GLOBAL)
"""
    file_path = tmp_path / "file.py"
    file_path.write_text(code)

    violations = scan_paths([file_path])
    assert len(violations) == 1
    assert violations[0].path == file_path


def test_scan_paths_skips_virtual_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    venv_dir = project / ".venv" / "lib" / "python3.11" / "site-packages" / "pkg"
    venv_dir.mkdir(parents=True)
    (venv_dir / "__init__.py").write_text(
        "GLOBAL = 1\n"
        "def func():\n"
        "    for i in range(3):\n"
        "        print(GLOBAL)\n"
    )

    violations = scan_paths([project])
    assert violations == []


def test_scan_paths_skips_site_packages_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "workspace"
    project.mkdir()

    app = project / "app.py"
    app.write_text(
        "GLOBAL = 1\n"
        "def func():\n"
        "    for i in range(3):\n"
        "        print(GLOBAL)\n"
    )

    site_packages = project / "deps" / "site-packages" / "pkg"
    site_packages.mkdir(parents=True)
    (site_packages / "__init__.py").write_text(
        "GLOBAL = 2\n"
        "def third_party():\n"
        "    for i in range(2):\n"
        "        print(GLOBAL)\n"
    )

    violations = scan_paths([project])
    assert len(violations) == 1
    assert violations[0].path == app
