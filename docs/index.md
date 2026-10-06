# pilot-target

A deliberately small reports web app. It exists so that an agent team can be evaluated on a
realistic delivery loop: plan → small tickets → PRs → protected merge → release to a real host.

- Browser UI at `/` lists reports visible to the selected role and exports them as CSV.
- JSON API under `/api` (see `api.md`).
- Health endpoint `/healthz`.

## Exporting reports

The reports page has an **Export CSV** button, available to both roles. It downloads the reports you
can currently see — one row per report, carrying the same `id`, `title`, `owner` and `rows` values as
the table — and nothing more. A viewer's file contains the viewer's reports and stops there: no
placeholder row, no withheld count, and no hint that a restricted report exists. Switching the role
selector to `admin` and exporting again gives the admin's larger set.

The downloaded file is named `reports-YYYY-MM-DD.csv`, dated in UTC, and opens as a table in Excel,
Numbers, LibreOffice Calc or Google Sheets. It is UTF-8 **with** a byte-order mark, so a double-click
into Excel decodes accented characters correctly. The API response body for the same data carries
**no** BOM, which is what a script or `pandas` wants; the two differ by exactly those three leading
bytes and are otherwise identical.

The same export is available to API clients as `GET /api/reports.csv` — see `api.md` for the response
headers, the CSV shape and how cells are kept safe for spreadsheets.

The export covers the report **list** only. `rows` is a count, and the application holds no row-level
data to export. There is no filtering, sorting, column selection or date range on the export, no
format other than CSV, and no per-report export.

## Run locally

```
uv sync
uv run uvicorn app.main:app --reload
```

## Tests

```
uv run ruff check .
uv run pytest tests/unit tests/integration
uv run playwright install chromium && uv run pytest tests/e2e
```

## Documentation policy

Any change under `app/` must touch `docs/` in the same PR, or the PR description must contain
the line `docs-impact: none` with a one-line reason. The `docs` CI check enforces this.
