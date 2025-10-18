# globals-in-loop-check

`globals-in-loop-check` detects usage of global variables inside loops or comprehensions.
Accessing globals within hot loops slows execution because each iteration performs a global lookup.

## Installation

Install locally in editable mode:

```
pip install -e .
```

Or install directly from GitHub:

```
pip install git+https://github.com/<org>/<repo>.git
```

## Usage

Run the checker on one or more files or directories:

```
globals-in-loop-check src/ my_module.py
```

Key options:

- `--short` – emit a compact report, useful for CI environments.
- `--no-gitignore` – analyze files even if they are listed in `.gitignore`.
- `--help` – show the full command-line reference.

## Integration with pre-commit

Add the hook definition to your repository:

```yaml
repos:
  - repo: https://github.com/<org>/<repo>.git
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
