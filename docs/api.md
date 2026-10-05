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
