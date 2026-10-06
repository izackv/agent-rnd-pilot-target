"""AGE-33: the whole suite must be collectable in one `pytest` invocation.

`tests/integration/test_export.py` and `tests/e2e/test_export.py` share a basename. That is fine
*given* that every test directory is a package: pytest then imports them as
`tests.integration.test_export` and `tests.e2e.test_export`, which cannot collide. Without the
`__init__.py` markers pytest falls back to inserting each file's directory on `sys.path` and
importing it as the bare module `test_export` — and two files cannot both be that module, so
`uv run pytest` dies with `import file mismatch` before running a single assertion.

The three required CI jobs invoke `tests/unit`, `tests/integration` and `tests/e2e` separately, so
no CI process ever imports the two colliding modules together. This test is what makes the
invariant visible to the `unit` job: it fails on the broken layout for the same reason the
full-suite run does, without needing a full-suite invocation to notice.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"


def _test_module_dirs() -> list[Path]:
    """Every directory under `tests/` (inclusive) that holds at least one `test_*.py`."""
    dirs = {path.parent for path in TESTS_ROOT.rglob("test_*.py")}
    return sorted(d for d in dirs if "__pycache__" not in d.parts)


def test_every_test_directory_is_a_package():
    """Each directory pytest imports test modules from carries an `__init__.py`.

    `tests/__init__.py` has existed since the scaffold; its subdirectories were the inconsistency.
    """
    missing = [
        str(d.relative_to(REPO_ROOT))
        for d in _test_module_dirs()
        if not (d / "__init__.py").is_file()
    ]
    assert not missing, (
        "these test directories hold test modules but are not packages, so pytest imports their "
        f"modules by bare basename and duplicate names collide: {missing}"
    )


def test_duplicate_test_basenames_are_disambiguated_by_packages():
    """Guards the other half: a shared basename is only safe while the packages above hold.

    This does not forbid duplicate basenames — `test_export.py` is deliberately reused, because
    renaming either copy would force the `docs/api.md` journey rows (J-02/J-03/J-04) to change.
    It asserts that every directory a duplicate lives in is importable as a package, which is the
    condition that makes the duplication harmless.
    """
    by_basename: defaultdict[str, list[Path]] = defaultdict(list)
    for path in TESTS_ROOT.rglob("test_*.py"):
        if "__pycache__" in path.parts:
            continue
        by_basename[path.name].append(path)

    for basename, paths in sorted(by_basename.items()):
        if len(paths) < 2:
            continue
        for path in paths:
            # Walk `tests/` down to the file's own directory; every step must be a package.
            package = TESTS_ROOT
            chain = [package]
            for part in path.parent.relative_to(TESTS_ROOT).parts:
                package = package / part
                chain.append(package)

            for package in chain:
                assert (package / "__init__.py").is_file(), (
                    f"{basename} is duplicated across "
                    f"{[str(p.relative_to(REPO_ROOT)) for p in paths]} but "
                    f"{package.relative_to(REPO_ROOT)} is not a package"
                )
