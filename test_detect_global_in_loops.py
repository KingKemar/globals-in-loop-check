import ast
from detect_global_in_loops import GlobalUsageChecker, find_globals, analyze_file


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
    violations = analyze_file(str(f))
    assert len(violations) == 1
    assert violations[0][0] == "GLOBAL"
