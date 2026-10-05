"""CSV serialization for the reports export (contract v1.1 §4 and §5).

Pure functions only: no framework import, no global mutable state, no I/O. The route in
`app.main` supplies the already-filtered report list, so this module never sees a role and never
decides visibility — see contract §6, Invariant P.
"""

from __future__ import annotations

import csv
import io

from app.data import Report

#: Exact column set and order [D-1]. Spelled out rather than derived from the dataclass: a field
#: added to `Report` later must not reach the export without a contract revision (contract §4).
COLUMNS = ("id", "title", "owner", "rows")

#: Record terminator [D-8]. Applies only *between* records; an embedded CR or LF inside a field is
#: written through verbatim by `csv.writer` and must not be normalized (contract §4 point 1).
EOL = "\r\n"

#: Marker prepended to a text field a spreadsheet would otherwise evaluate [D-4].
GUARD = "'"

#: Leading characters that make a text field evaluable. Not decision-dependent (contract §9).
RISKY_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe(value: str) -> str:
    """Prefix a text field whose first character would make a spreadsheet evaluate it.

    Only the first character is examined, so `a=b` and ` =notfirst` are returned unchanged. An
    empty string starts with nothing and is returned unchanged. Applied *before* the CSV writer,
    so quoting and quote-doubling then apply to the guarded string (contract §5).
    """
    return GUARD + value if value.startswith(RISKY_PREFIXES) else value


def render_reports_csv(reports: list[Report]) -> bytes:
    """Render reports as a UTF-8 CSV document with no BOM (contract §3, §4).

    A header row is always present, so an empty list yields the header row alone. Records are
    emitted in `id` ascending order, which is the documented guarantee [D-9] and independent of
    the order the caller happens to pass. Numeric fields (`id`, `rows`) are never guarded.
    """
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator=EOL)
    writer.writerow(COLUMNS)
    for report in sorted(reports, key=lambda item: item.id):
        writer.writerow([report.id, _safe(report.title), _safe(report.owner), report.rows])
    return buf.getvalue().encode("utf-8")
