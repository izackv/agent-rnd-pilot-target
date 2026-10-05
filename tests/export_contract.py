"""The CSV export's wire contract as test constants. One edit here re-points every assertion.

Pinned to contract v1.1 (AGE-4) and test plan v1.1 §0 (AGE-5). Each name below that cites a
decision is still open on the board's consolidated card; if the board answers differently, change
it here and nowhere else. A test that hardcodes `b"id,title,owner,rows"` instead of importing
`HEADER` is a review defect, because it hides which assertions a reopened decision invalidates.

Constants only: no tests, and no import from `app`. This module lives at `tests/` level rather
than under `tests/unit/` because `tests/unit/` has no `__init__.py`, so constants placed there
could not be imported by the integration and e2e suites.
"""

HEADER = b"id,title,owner,rows"  # [D-1]
EOL = b"\r\n"  # [D-8]
GUARD = "'"  # [D-4]
RISKY_PREFIX = ("=", "+", "-", "@", "\t", "\r")  # not decision-dependent (brief §6, contract §9)
BOM = b"\xef\xbb\xbf"  # [D-3] — downloaded file only; never on the wire
FILENAME_RE = r'^attachment; filename="reports-(\d{4}-\d{2}-\d{2})\.csv"$'  # [D-2]
WHITESPACE_PRESERVED = True  # [QA-D-A]

# Today's seed data, both roles (test plan §3.2). No seed report triggers the guard or any
# quoting, which is exactly why the cell-safety fixtures exist.
VIEWER_BODY = (
    b"id,title,owner,rows\r\n"
    b"1,Monthly usage,ops,1200\r\n"
    b"2,Error budget,sre,48\r\n"
    b"4,Signup funnel,growth,5200\r\n"
)  # len == 99

ADMIN_BODY = (
    b"id,title,owner,rows\r\n"
    b"1,Monthly usage,ops,1200\r\n"
    b"2,Error budget,sre,48\r\n"
    b"3,Payroll summary,finance,310\r\n"
    b"4,Signup funnel,growth,5200\r\n"
)  # len == 130

EMPTY_BODY = b"id,title,owner,rows\r\n"  # len == 21   [D-7]
