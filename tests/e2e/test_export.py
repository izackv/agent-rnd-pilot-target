"""Accepted user journeys J-02 and J-03: exporting the reports page to CSV in a real browser.

Test plan v1.1 §1, §2.2 and §5.3. These assert the user's **artifact** — a file, with a name, in an
encoding, containing exactly these reports — rather than that a button was clicked.

Why this file is the one that matters, and the one thing nothing below it can see: the contract
(§1) requires the control to use `fetch` with an `X-Role` header rather than an
`<a href="/api/reports.csv" download>`, because a browser attaches no custom header to a
navigation. An anchor-based control satisfies AC-1, AC-2, AC-5, AC-6 and **every** test in
`tests/integration/test_export.py` — those set the header themselves — while silently shipping the
*viewer* file to admins. `test_j03_admin_download_contains_the_restricted_report` is the only
assertion in the whole suite that fails for it (AC-28, test plan §2.2 P-17).

Mechanics this file depends on (§5.3):

* the `base_url` fixture from `conftest.py`, which boots uvicorn on a free port — never a hard-coded
  port;
* `page.expect_download()` as a context manager around the click; the download is only available
  inside or after that block;
* reading the download as **bytes** from `download.path()`. `open()` with the platform default
  encoding is not an encoding test and would defeat AC-13;
* selecting the control by **`id`** (settlement S-2), never by its label — the button copy is the
  Tech Lead's to change, and a rename must not turn AC-15 or AC-28 red.
"""

from __future__ import annotations

import csv
import io
import pathlib
import re

import pytest
from playwright.sync_api import Page, expect

from tests.export_contract import BOM, EXPORT_FAILED, HEADER

EXPORT = "#export"
FILENAME_RE = re.compile(r"reports-\d{4}-\d{2}-\d{2}\.csv")

#: Proxies `window.fetch` so that `/api/reports.csv` resolves with real headers and a real status,
#: and only the **body read** rejects — a connection dropped after the response line, which is the
#: one failure the `fetch` call's own `try` cannot see. Everything the control reads off the
#: response (`ok`, `headers`) is delegated to the genuine `Response`, so the test exercises the
#: real success path right up to `text()`.
#:
#: Deliberately touches nothing but `window.fetch`: no `HTMLAnchorElement.prototype.click` or
#: `URL.revokeObjectURL` patches. Those observe DOM mechanics rather than user-visible outcomes,
#: and on Chromium — the only engine in test plan v1.1 §7 — neither is observable in behavior.
_REJECT_BODY_READ = """
(() => {
  const realFetch = window.fetch;
  window.fetch = async (...args) => {
    const response = await realFetch(...args);
    const url = typeof args[0] === "string" ? args[0] : args[0].url;
    if (!url.includes("reports.csv")) return response;
    return new Proxy(response, {
      get(target, prop) {
        if (prop === "text") {
          return () => Promise.reject(new TypeError("body read failed"));
        }
        const value = Reflect.get(target, prop);
        return typeof value === "function" ? value.bind(target) : value;
      },
    });
  };
})();
"""


def _download_bytes(page: Page) -> tuple[bytes, str]:
    """Click the export control and return the downloaded bytes and its suggested filename."""
    with page.expect_download() as download_info:
        page.locator(EXPORT).click()
    download = download_info.value
    return pathlib.Path(download.path()).read_bytes(), download.suggested_filename


def _records(raw: bytes) -> list[list[str]]:
    """Parse the downloaded file. `utf-8-sig` consumes the BOM the UI prepended (contract §4)."""
    return list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))


def _open_reports(page: Page, base_url: str, role: str = "viewer") -> None:
    page.goto(base_url + "/")
    expect(page.locator("#reports tbody tr")).to_have_count(3)
    if role != "viewer":
        page.get_by_label("role").select_option(role)
        expect(page.locator("#reports tbody tr")).to_have_count(4)


def test_j02_viewer_downloads_permitted_reports(page: Page, base_url: str):
    """J-02, AC-1, AC-2, AC-23: a viewer gets a *download*, not a rendered page, and the file holds
    exactly the three reports they can see."""
    _open_reports(page, base_url)
    url_before = page.url

    raw, filename = _download_bytes(page)
    records = _records(raw)

    assert records[0] == ["id", "title", "owner", "rows"]
    assert [record[0] for record in records[1:]] == ["1", "2", "4"]
    assert b"Payroll summary" not in raw
    assert FILENAME_RE.fullmatch(filename), filename
    assert page.url == url_before  # a download, not a navigation


def test_j03_admin_download_contains_the_restricted_report(page: Page, base_url: str):
    """J-03, AC-3a, AC-28, test plan §2.2 P-17 — **the most important test in this plan.**

    With the selector on `admin` the downloaded bytes must contain all four reports. An
    anchor-based control passes everything else and fails exactly here, because it cannot carry
    `X-Role` and so hands the admin the viewer's three-record file.
    """
    _open_reports(page, base_url, role="admin")

    raw, filename = _download_bytes(page)
    records = _records(raw)

    assert [record[0] for record in records[1:]] == ["1", "2", "3", "4"]
    assert records[3] == ["3", "Payroll summary", "finance", "310"]
    assert b"Payroll summary" in raw
    assert FILENAME_RE.fullmatch(filename), filename


def test_export_control_is_visible_and_enabled_for_both_roles(page: Page, base_url: str):
    """AC-15 (brief): the control is present and enabled for *both* roles. It is a copy of data the
    user can already see, so there is no role for which exporting is withheld.

    Selected by `id` per S-2, so renaming the button copy cannot fail this test.
    """
    _open_reports(page, base_url)
    for role in ("viewer", "admin"):
        page.get_by_label("role").select_option(role)
        expect(page.locator(EXPORT)).to_be_visible()
        expect(page.locator(EXPORT)).to_be_enabled()


def test_downloaded_file_starts_with_a_utf8_bom(page: Page, base_url: str):
    """AC-13 [D-3]. The server emits no BOM and the UI prepends one, so the downloaded file and the
    API body differ by **exactly** the three bytes `EF BB BF`.

    Both halves are asserted: the BOM is present *and* `raw[3:]` equals the API body for the same
    role. A test asserting the two paths are byte-identical would be wrong, and one asserting only
    the BOM would not notice the UI corrupting the body on the way through the Blob.
    """
    _open_reports(page, base_url)
    raw, _ = _download_bytes(page)

    assert raw.startswith(BOM)
    assert raw[3 : 3 + len(HEADER)] == HEADER

    api_body = page.request.get(base_url + "/api/reports.csv", headers={"X-Role": "viewer"}).body()
    assert not api_body.startswith(BOM)
    assert raw[3:] == api_body


def test_download_matches_the_rendered_table(page: Page, base_url: str):
    """AC-4, the page -> file chain: the file agrees with what the role can actually see on screen.

    Asserted for both roles, because the table and the export are two independent reads of
    `data.list_reports(role)` and a role-dependent divergence is exactly the defect worth catching.
    """
    _open_reports(page, base_url)

    for role in ("viewer", "admin"):
        page.get_by_label("role").select_option(role)
        expect(page.locator("#reports tbody tr")).to_have_count(3 if role == "viewer" else 4)

        rendered = [
            [cell.inner_text().strip() for cell in row.locator("td").all()]
            for row in page.locator("#reports tbody tr").all()
        ]
        raw, _ = _download_bytes(page)
        assert _records(raw)[1:] == rendered, role


def test_page_state_is_unchanged_after_export(page: Page, base_url: str):
    """AC-1, negative half, and R-4. The export must not perturb the page it was invoked from.

    `#status` is the sharp edge: `tests/e2e/test_journey.py:11` asserts it reads exactly
    `"3 reports"` on load, so the control may write there **only** on a click that fails. A
    successful export leaves it alone, and this test is what holds the UI to that.
    """
    _open_reports(page, base_url)
    rows_before = page.locator("#reports tbody tr").count()
    status_before = page.locator("#status").inner_text()
    url_before = page.url
    assert status_before == "3 reports"

    _download_bytes(page)

    assert page.locator("#reports tbody tr").count() == rows_before
    assert page.locator("#status").inner_text() == status_before
    assert page.url == url_before


def test_export_request_carries_the_role_in_a_header_not_the_url(page: Page, base_url: str):
    """Contract §1, normative point 2: the role travels in `X-Role` and is **never** placed in the
    URL. A role in the query string would be a second permission door and would make a
    permitted-set-widening link shareable.

    Pinned by capturing the real request rather than inferred from the downloaded bytes, which
    would look identical either way for a viewer.
    """
    _open_reports(page, base_url, role="admin")

    with page.expect_request(lambda request: "reports.csv" in request.url) as request_info:
        with page.expect_download():
            page.locator(EXPORT).click()
    request = request_info.value

    assert request.method == "GET"
    assert request.url.endswith("/api/reports.csv"), request.url
    assert "?" not in request.url
    assert request.headers.get("x-role") == "admin"


@pytest.mark.parametrize("role", ["viewer", "admin"])
def test_download_filename_comes_from_the_response_header(page: Page, base_url: str, role: str):
    """AC-23 [D-2]. The name is the server's `Content-Disposition` value, not a client-side guess:
    the UI's `"reports.csv"` literal is a fallback for an absent header only.

    The date is read out of the response rather than computed in the test, so this cannot fail if
    the run crosses midnight UTC (test plan §5.5).
    """
    _open_reports(page, base_url, role=role)
    disposition = page.request.get(base_url + "/api/reports.csv", headers={"X-Role": role}).headers[
        "content-disposition"
    ]
    expected = re.fullmatch(r'attachment; filename="(.+)"', disposition)
    assert expected, disposition

    _, filename = _download_bytes(page)
    assert filename == expected.group(1)
    assert FILENAME_RE.fullmatch(filename), filename


def test_a_failed_body_read_surfaces_the_failure_copy(page: Page, base_url: str):
    """Contract §7 UI row and settlement S-4: a body read that fails *after* the response headers
    arrived must surface in `#status`, download nothing, and raise nothing at the page.

    This is the one export failure the response-status check cannot catch. `res.ok` is true, the
    headers are real, and the rejection comes from `res.text()` — so if the body read sits outside
    the control's `try`, the click is **inert**: no file, no message, and an unhandled rejection.
    That exact triple was observed on `main@8b3ea8f`, before AGE-27 moved the read inside the guard.

    All three assertions are user-visible, which is why this is worth standing coverage rather than
    a one-off diagnostic:

    * `#status` carries the S-4 copy, imported from `tests/export_contract.py` so that a copy change
      is one edit and cannot be silently diverged from here;
    * **no** download fires — the contract forbids handing the user a file built from a failed read,
      and a zero-byte or truncated `reports-*.csv` would be worse than an error message;
    * nothing reaches `pageerror`. An unhandled rejection is not merely untidy: it is the signal
      that the failure was never handled at all, and it is invisible to a status assertion alone.
    """
    page_errors: list[str] = []
    downloads: list[object] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    # Both handlers are lambdas, not bound builtins: Playwright annotates the handler object, and
    # `downloads.append` is a `builtin_function_or_method`, which rejects attributes.
    page.on("download", lambda download: downloads.append(download))

    # Must precede the navigation in `_open_reports`: an init script only applies to documents
    # loaded after it is registered.
    page.add_init_script(_REJECT_BODY_READ)
    _open_reports(page, base_url)
    rows_before = page.locator("#reports tbody tr").count()
    assert page.locator("#status").inner_text() == "3 reports"  # the proxy spares /api/reports

    page.locator(EXPORT).click()

    # `to_have_text` is exact and auto-waiting, so it is also the synchronisation point for the two
    # negative assertions below: a download or a page error on this click would have to land before
    # the status settles.
    expect(page.locator("#status")).to_have_text(EXPORT_FAILED)
    assert downloads == []
    assert page_errors == []

    # The failed export leaves the table it was invoked from alone (R-4).
    assert page.locator("#reports tbody tr").count() == rows_before
