# globals-in-loop-check

`globals-in-loop-check` detects problematic/global usage patterns in Python code.
It focuses on performance and encapsulation best‑practices around module‑level variables.

## Why this library exists

Accessing **global variables** inside loops or functions is **slower** than accessing locals.  
This is a well-documented behavior in Python’s design and can cause measurable slowdowns in tight loops or performance-critical code.

here are two instances where this behaviour is illustrated

### 🔹 [Optimize Python Code: Local vs Global Variables (CyCoderX, 2024)](https://python.plainenglish.io/optimize-python-code-local-vs-global-variables-5ec0722d7d4d)

Shows that copying a global variable into a local before entering a loop can improve performance by **~12%** for just 1,000 iterations.

```python
global_var = 10

def func():
    ans = 0
    local_var = global_var  # copy to local scope
    for i in range(1000):
        ans += local_var * i
    return ans
```
### 🔹 [Python Patterns – An Optimization Anecdote (python.org, Guido van Rossum)](https://www.python.org/doc/essays/list2str/#:~:text=,an%20explicit%20for%20loop%2C%20but)

An early essay demonstrating why local lookups are much faster than global or built-in ones:

“Local variable lookups are much faster than global or built-in variable lookups:
the compiler optimizes function bodies so that local variables use simple array indexing instead of dictionary lookups.”

## Installation

Install locally in editable mode:

```
pip install -e .
```

Or install directly from GitHub:

```
pip install git+https://github.com/KingKemar/globals-in-loop-check
```

## Usage

Run the checker on one or more files or directories:

```
globals-in-loop-check src/ my_module.py
```

Key options:

- `--short` – emit a compact report, useful for CI environments.
- `--no-gitignore` - analyze files even if they are listed in `.gitignore`.
- `--help` - show the full command-line reference.

## Rules

The tool currently reports these checks as flake8‑style messages:

- G001 — Global used inside a loop/comprehension
  - Example: `path/to/file.py:10:1: G001 global variable 'X' used inside a loop`
  - Rationale: each iteration performs a global lookup; cache into a local before the loop.
- G002 — Global should be encapsulated in a class
  - Trigger: a module‑level variable is only ever referenced inside methods of a single class.
  - Example: `path/to/file.py:3:1: G002 module-level variable 'CFG' is only used inside class 'Service'; consider encapsulating it as a class/instance attribute`
  - Rationale: improves modularity and control over access/modification.

## Integration with pre-commit

Add the hook definition to your repository:

```yaml
repos:
  - repo: https://github.com/KingKemar/globals-in-loop-check.git
    rev: <tag-or-commit>
    hooks:
      - id: globals-in-loop-check
```

If publishing your own mirror of the hook, include a `.pre-commit-hooks.yaml` file containing:

```yaml
- id: globals-in-loop-check
  name: globals-in-loop-check
  entry: globals-in-loop-check
  language: python
  types: [python]
```

## Running tests

Tests use `pytest`:

```
pytest
```

## Notes

- The CLI prints a short remediation hint for G001 by default (omit with `--short`).
- Directories like `.venv/` and third‑party trees `site-packages/` or `dist-packages/` are skipped.
