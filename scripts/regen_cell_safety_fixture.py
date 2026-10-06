#!/usr/bin/env python3
"""Regenerate the committed cell-safety fixtures from the serializer (test plan §5.4).

The fixtures are the artifact the manual four-spreadsheet sign-off (AGE-19) is performed against.
They are generated here and asserted byte-equal in `tests/unit/test_export_csv.py`, so they cannot
drift from the §3.3 expectations without CI failing.

Run after any intentional change to the guard or the serializer, then re-open the sign-off: a new
fixture invalidates the previous sign-off, because that sign-off named the old commit's bytes.

    uv run python scripts/regen_cell_safety_fixture.py
"""

from __future__ import annotations

import sys

from app.export import render_reports_csv
from tests.export_contract import BOM
from tests.unit.test_export_csv import (
    CELL_SAFETY_CSV,
    CELL_SAFETY_DOWNLOAD_CSV,
    CELL_SAFETY_FIXTURES,
)


def main() -> int:
    body = render_reports_csv([report for _, report, _ in CELL_SAFETY_FIXTURES])
    CELL_SAFETY_CSV.parent.mkdir(parents=True, exist_ok=True)
    CELL_SAFETY_CSV.write_bytes(body)
    CELL_SAFETY_DOWNLOAD_CSV.write_bytes(BOM + body)
    print(f"{CELL_SAFETY_CSV}: {len(body)} bytes, {len(CELL_SAFETY_FIXTURES)} records")
    print(f"{CELL_SAFETY_DOWNLOAD_CSV}: {len(BOM) + len(body)} bytes (BOM-prefixed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
