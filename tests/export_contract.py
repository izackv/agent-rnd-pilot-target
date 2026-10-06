"""The CSV export's wire contract as test constants. One edit here re-points every assertion.

Pinned to contract v1.1 (AGE-4) and test plan v1.1 §0 (AGE-5). Every decision cited below was
ratified as recommended by the owner on card `4078654f` (2026-10-06); none is still open. Should
one ever be reopened and answered differently, change it here and nowhere else. A test that
hardcodes `b"id,title,owner,rows"` instead of importing `HEADER` is a review defect, because it
hides which assertions a reopened decision invalidates.

Constants only: no tests, and no import from `app`. This module lives at `tests/` level rather
than under `tests/unit/` because `tests/unit/` has no `__init__.py`, so constants placed there
could not be imported by the integration and e2e suites.
"""

HEADER = b"id,title,owner,rows"  # [D-1]
EOL = b"\r\n"  # [D-8]
GUARD = "'"  # [D-4]
RISKY_PREFIX = ("=", "+", "-", "@", "\t", "\r")  # not decision-dependent (brief §6, contract §9)

#: Leading characters contract §5 requires to pass through *unguarded*. Disjoint from
#: RISKY_PREFIX, and asserted to be so, so that a character added to the guard alphabet fails a
#: test instead of silently widening it (AGE-20). `" "` is also pinned by WHITESPACE_PRESERVED.
SAFE_PREFIX = ("#", "\n", " ", "a", "0", ".", '"')
BOM = b"\xef\xbb\xbf"  # [D-3] — downloaded file only; never on the wire
FILENAME_RE = r'^attachment; filename="reports-(\d{4}-\d{2}-\d{2})\.csv"$'  # [D-2]
WHITESPACE_PRESERVED = True  # [QA-D-A]

#: The one string the UI may write to `#status` when an export fails, fixed by settlement S-4
#: (D-13). Declared in `app/static/app.js` as `EXPORT_FAILED`; pinned here so a copy change is a
#: one-line edit rather than a retyped literal in every failure test. Deliberately *not* read out
#: of the page at runtime: a test that asked the app for its own copy would pass for any copy and
#: so could not hold the UI to S-4.
EXPORT_FAILED = "Export failed. Please try again."  # [S-4]

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
