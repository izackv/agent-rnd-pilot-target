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

#: Journey rows `docs/api.md` must carry, and the test file each one names. J-02 and J-03 are the
#: two browser export journeys and belong to the UI issue, which owns the export control; they
#: join this tuple in the same commit as `tests/e2e/test_export.py`, and until then the
#: "no dangling row" assertion below still covers them if that issue lands its rows first.
REQUIRED_JOURNEYS = [
    ("J-01", "tests/e2e/test_journey.py"),
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
    """AC-17: every required journey row is present with the test file it names, and — the other
    direction — no journey row names a file that does not exist on disk."""
    documented = dict(JOURNEY_ROW.findall(api_md))
    assert documented, "no journey rows found in docs/api.md"

    for journey_id, test_path in REQUIRED_JOURNEYS:
        assert journey_id in documented, f"{journey_id} is missing from docs/api.md"
        assert documented[journey_id] == test_path

    for journey_id, test_path in documented.items():
        assert (REPO_ROOT / test_path).exists(), f"{journey_id} names a missing file: {test_path}"
