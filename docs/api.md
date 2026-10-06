# API

Role is supplied by the `X-Role` header (`viewer` default, `admin`). This is trial-grade
authentication, chosen so permission paths can be tested without an identity provider.

| Method | Path | Behavior |
|---|---|---|
| GET | `/healthz` | `{"status": "ok", "version": ...}` |
| GET | `/api/reports` | Reports visible to the role. Restricted reports are admin-only. |
| GET | `/api/reports.csv` | The role's visible reports as CSV (`text/csv; charset=utf-8`, attachment). |
| GET | `/api/reports/{id}` | One report, or 404 if missing or not visible to the role. |

## CSV export

`GET /api/reports.csv` is the CSV representation of the collection `GET /api/reports` serves. It is
one route: the Export CSV button on the reports page and an API client both call it. For the
user-facing description of the same feature, see [Exporting reports](index.md#exporting-reports).

### Response

| Aspect | Value |
|---|---|
| Status | `200` for every request. Permission is expressed as content, never as a gate: there is no `401` and no `403` on any input. |
| `Content-Type` | `text/csv; charset=utf-8` |
| `Content-Disposition` | `attachment; filename="reports-<UTC YYYY-MM-DD>.csv"` |
| `Vary` | `X-Role` |
| `Cache-Control` | `no-store` |
| Body | UTF-8, **no BOM**. `CRLF` between records, including after the last one. |

`Vary` and `Cache-Control` are part of the permission rule rather than a performance nit: the body
varies on a *request header*, so a cache keyed on the URL alone could serve an admin's file to a
viewer even with a correct handler.

Any other method on the path returns `405` with `Allow: GET`. That includes `HEAD`, because FastAPI
does not add `HEAD` to a `GET` route — `HEAD /api/reports` already behaves this way, so the export is
consistent with the existing surface rather than special-cased. Paths are case-sensitive, so
`/api/reports.CSV` is `404`; a trailing slash redirects with `307`.

### Body

The header row `id,title,owner,rows` is always present, and the column set is identical for both
roles. An empty permitted set yields that row alone — a valid CSV with no data rows, not a
zero-byte file. Records follow one per report in `id` ascending order, which is a guarantee of this
endpoint and not a side effect of the page's ordering.

The CSV column set is a deliberate **subset** of the JSON field set: the JSON carries `restricted`,
the CSV does not. It is an internal access flag with no user value, and a role-varying column set
would force two file shapes through the UI, the docs and every test. Omitting it is not a leak fix —
`GET /api/reports` already reports `"restricted": false` to viewers. Do not "fix" the difference.

The reports in the body are exactly `data.list_reports(role)` for the role resolved from `X-Role` —
the same call `GET /api/reports` makes — so the export can never be a wider door than the JSON
endpoint beside it, and a report flagged `restricted` later is excluded with no further export work.
`X-Role` is reused unchanged: exactly `admin` selects the admin role and every other value (absent,
empty, `Admin`, `root`) selects `viewer`, so an unrecognized role yields the viewer file and never a
`400`. No query parameter, cookie or request body influences which reports appear; a query string is
ignored, not rejected.

### Cell safety

A text field (`title`, `owner`) whose **first** character is `=`, `+`, `-`, `@`, TAB or CR is emitted
with a single `'` prepended, so a spreadsheet reads it as text instead of evaluating it. Only the
first character is examined: `a=b` is untouched. Numeric fields (`id`, `rows`) are never guarded,
which is what keeps `1200` a number the user can total and sort.

Quoting is the Python `csv` default `QUOTE_MINIMAL`: a field is quoted only when it contains `,`,
`"`, CR or LF, and an embedded `"` is doubled inside the quoted field. An embedded CR or LF is
written through **verbatim** and is deliberately not normalized to `CRLF`; do not normalize it. None
of the application's seed values triggers the guard or any quoting today, so both roles' files are
plain. `tests/unit/test_export_csv.py` covers the awkward values with fixtures.

### Browser download

The Export CSV button calls this route with `fetch` and the role selector's current value in
`X-Role`, then builds the download from the response Blob. It is deliberately not an
`<a href="/api/reports.csv" download>`: a browser attaches no custom header to a navigation, so an
anchor would download the viewer file even for an admin. The role is never placed in the URL.

The browser prepends a UTF-8 BOM when it constructs the Blob, so the downloaded file and the API
response differ by exactly the leading `EF BB BF` and nothing else. The file name comes from the
response's `Content-Disposition`. The control is present and enabled for both roles. When the
request fails, the page reports it in the status line and downloads nothing.

A failure message does not outlive the failure: a later export that succeeds puts the status line
back to the report count it showed before the click, so the page never claims the export failed
while handing the user their file. On a click that succeeds first time the line is unchanged, and
the restore is not an announcement — whether a successful export should announce itself to assistive
technology is still open.

## Accepted user journeys

| ID | Journey | Test |
|---|---|---|
| J-01 | Viewer opens the reports page and sees permitted reports; admin sees the restricted one too | `tests/e2e/test_journey.py` |
| J-02 | A viewer clicks Export on the reports page and their browser downloads a CSV file containing the three reports they can see, and not the restricted one | `tests/e2e/test_export.py::test_j02_viewer_downloads_permitted_reports` |
| J-03 | An admin switches the role selector to `admin`, clicks Export, and the downloaded file contains all four reports including "Payroll summary" | `tests/e2e/test_export.py::test_j03_admin_download_contains_the_restricted_report` |
| J-04 | A client exports the permitted reports as CSV through the API; with no role header it receives the viewer file, with `X-Role: admin` all four reports, and no query parameter can widen either | `tests/integration/test_export.py` |

`tests/unit/test_docs_traceability.py` asserts the rows in this table rather than leaving them to a
reviewer's eye: CI's `docs` job only checks that *some* file under `docs/` changed when `app/`
changed, never what it says. It also checks the other direction — that no row names a test file or
test function missing from the tree — so a journey row cannot rot into a reference to a renamed test.
