"""AC-17: the export is documented, asserted rather than eyeballed (test plan v1.1 §1, §5.1).

CI's `docs` job runs `scripts/docs_check.py`, which only checks that *some* file under `docs/`
changed when `app/` changed. It cannot see whether the export was documented, or whether a journey
row points at a test file that exists. These two tests close that gap, so a journey row can never
rot into a reference to a deleted test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
API_MD = REPO_ROOT / "docs" / "api.md"

#: Journey rows `docs/api.md` must carry, and the test target each one names. Three export rows,
#: per settlement S-5 (test plan §4 over contract §10's two): J-03 earns its own id because the
#: admin browser path is the only journey that fails for an anchor-based control.
REQUIRED_JOURNEYS = [
    ("J-01", "tests/e2e/test_journey.py"),
    ("J-02", "tests/e2e/test_export.py::test_j02_viewer_downloads_permitted_reports"),
    ("J-03", "tests/e2e/test_export.py::test_j03_admin_download_contains_the_restricted_report"),
    ("J-04", "tests/integration/test_export.py"),
]

#: Matches a journey table row and captures its id and the first backtick-quoted path in it.
JOURNEY_ROW = re.compile(r"^\|\s*(J-\d+)\s*\|.*?\|\s*`([^`]+)`\s*\|\s*$", re.MULTILINE)


@pytest.fixture(scope="module")
def api_md() -> str:
    return API_MD.read_text(encoding="utf-8")


def test_api_md_documents_the_export_route(api_md: str):
    """AC-17, contract §10: the route row, its media type and the `attachment` disposition."""
    route_rows = [
        line
        for line in api_md.splitlines()
        if line.startswith("|") and "`/api/reports.csv`" in line
    ]
    assert len(route_rows) == 1, route_rows
    row = route_rows[0]
    assert "GET" in row
    assert "text/csv; charset=utf-8" in row
    assert "attachment" in row

    # Contract §10's extra line: the CSV column set is a deliberate subset of the JSON field set,
    # documented so nobody later "fixes" the difference by adding `restricted` to the export.
    assert "subset" in api_md
    assert "`id,title,owner,rows`" in api_md


def test_api_md_lists_the_new_journeys_with_their_test_files(api_md: str):
    """AC-17: every required journey row is present naming the test it names, and — the other
    direction — no journey row points at a test that does not exist.

    A row may name a file (`tests/integration/test_export.py`) or a specific test within one
    (`...::test_j02_...`). Both halves of a `::` target are checked: the file must exist on disk
    **and** the named function must be defined in it. Checking only the file would let a row rot
    into a reference to a renamed test while still passing.
    """
    documented = dict(JOURNEY_ROW.findall(api_md))
    assert documented, "no journey rows found in docs/api.md"

    for journey_id, target in REQUIRED_JOURNEYS:
        assert journey_id in documented, f"{journey_id} is missing from docs/api.md"
        assert documented[journey_id] == target

    for journey_id, target in documented.items():
        path, _, test_name = target.partition("::")
        source = REPO_ROOT / path
        assert source.exists(), f"{journey_id} names a missing file: {path}"
        if test_name:
            defined = re.search(rf"^def {re.escape(test_name)}\(", source.read_text(), re.M)
            assert defined, f"{journey_id} names {test_name}, which is not defined in {path}"
