# API

Role is supplied by the `X-Role` header (`viewer` default, `admin`). This is trial-grade
authentication, chosen so permission paths can be tested without an identity provider.

| Method | Path | Behavior |
|---|---|---|
| GET | `/healthz` | `{"status": "ok", "version": ...}` |
| GET | `/api/reports` | Reports visible to the role. Restricted reports are admin-only. |
| GET | `/api/reports.csv` | The role's visible reports as CSV (`text/csv; charset=utf-8`, attachment). |
| GET | `/api/reports/{id}` | One report, or 404 if missing or not visible to the role. |

The CSV column set (`id,title,owner,rows`) is a deliberate **subset** of the JSON field set: the
JSON carries `restricted`, the CSV does not. It is an internal access flag with no user value, and
a role-varying column set would force two file shapes through the UI, the docs and every test.
Omitting it is not a leak fix — `GET /api/reports` already reports `"restricted": false` to
viewers. Do not "fix" the difference.

## Accepted user journeys

| ID | Journey | Test |
|---|---|---|
| J-01 | Viewer opens the reports page and sees permitted reports; admin sees the restricted one too | `tests/e2e/test_journey.py` |
| J-02 | A viewer clicks Export on the reports page and their browser downloads a CSV file containing the three reports they can see, and not the restricted one | `tests/e2e/test_export.py::test_j02_viewer_downloads_permitted_reports` |
| J-03 | An admin switches the role selector to `admin`, clicks Export, and the downloaded file contains all four reports including "Payroll summary" | `tests/e2e/test_export.py::test_j03_admin_download_contains_the_restricted_report` |

The export control uses `fetch` with the `X-Role` header and builds the download from the response
Blob. It is deliberately not an `<a href="/api/reports.csv" download>`: a browser attaches no custom
header to a navigation, so an anchor would download the viewer file even for an admin. The role is
never placed in the URL. The downloaded file is prefixed with a UTF-8 BOM in the browser; the API
bytes carry none, so the two differ by exactly the leading `EF BB BF`.
