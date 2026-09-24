from pathlib import Path


def build_generation_prompt(class_file: Path, project_dir: Path) -> str:
    module_stem = class_file.stem
    target_source = class_file.read_text()

    sibling_blocks = []
    for f in sorted(project_dir.glob("*.py")):
        if f.resolve() == class_file.resolve():
            continue
        if f.name == "__init__.py":
            continue  # just re-export aliases, no real logic to show
        sibling_blocks.append(f"# --- {f.name} ---\n{f.read_text()}")
    context_block = "\n\n".join(sibling_blocks)

    return f"""You are an expert Python test engineer specializing in pytest.

Your task: write a pytest test suite for the target module below, maximizing
line coverage, branch coverage, and resistance to mutation testing (cosmic-ray).

## Target module: {module_stem}.py
```python
{target_source}
```

## Other files in the same project (context only — types/classes the target module depends on; do not write tests for these, only for {module_stem}.py)
```python
{context_block}
```

## Requirements
1. Import the code under test with: `from {module_stem} import <ClassName>`
   (and any other names you need, from the same module). Do not use
   package-qualified imports (e.g. `from blackjack.dealer import ...`) —
   only the flat form above is guaranteed to work.
2. Cover both branches of every `if`/`else` and both the taken and skipped
   path of every loop — branch coverage is graded separately from line
   coverage, so a test that only ever hits one side of a condition is
   insufficient.
3. Include boundary-value and equivalence-partition test cases (e.g. empty
   inputs, single-element inputs, minimum/maximum valid values, one-past-
   boundary invalid values) — not just one "happy path" call per method.
4. For any class that takes an `np_random`-style parameter, pass a real
   `numpy.random.RandomState(<fixed integer seed>)`, not a mock. Do not
   mock or stub any logic that belongs to the code under test — assertions
   must check real computed behavior, not a faked return value.
5. Write plain pytest-style test functions (`def test_...():`), not
   `unittest.TestCase` classes.
6. Do not add any `sys.path` manipulation, import hacks, or environment
   setup — the import in point 1 is guaranteed to already work.
7. Test the code's *actual* behavior, not the behavior its names or
   docstrings suggest. The code may contain bugs (e.g. an operator that
   raises `TypeError`, an off-by-one). Trace the code by hand before writing
   each assertion; if a call raises for some input, assert that with
   `pytest.raises(<ExceptionType>)`, and still reach every other branch
   with inputs that avoid the failing path. Never write a test that
   assumes the code is correct when it isn't.
8. If such a bug makes code *downstream* of it unreachable (e.g. a helper
   that always raises, so the logic after it never runs), still cover that
   downstream code: keep one test asserting the bug's real behavior, and in
   separate tests use pytest's `monkeypatch` to replace *only that one
   broken helper* with a minimal correct stand-in, so every other line of
   the real code executes and its results can be asserted precisely.
   The stand-in must return realistic, non-empty values (what the helper
   was evidently meant to compute) -- a stub returning `[]`/`None` just
   skips the downstream code again and defeats the purpose.

## Output format
Respond with exactly one fenced Python code block and nothing else — no
explanation before or after it.
```python
# your test file content here
```
"""


def build_fix_prompt(pytest_output: str) -> str:
    return f"""The test file you generated failed when run with pytest. Here is
the captured output (stdout + stderr):

```
{pytest_output}
```

Fix the test file so that it passes. If the failure shows the code under
test behaves differently from what the test expected (including raising an
exception), the code is the ground truth: change the test's expectation to
match the actual behavior (use `pytest.raises` for exceptions) instead of
dropping the test. Keep following the same rules as
before: flat import from the module filename, a real
`numpy.random.RandomState(<seed>)` instead of mocks for any `np_random`
parameter, coverage of both branches of every conditional, and boundary/
equivalence-partition cases.

Respond with exactly one fenced Python code block containing the
corrected, complete test file — nothing else."""


if __name__ == "__main__":
    class_file = Path("Public_Proyects/blackjack/dealer.py")
    project_dir = class_file.parent
    print(build_generation_prompt(class_file, project_dir))
