"""The export route over HTTP: `GET /api/reports.csv` (contract v1.1 §2, §3, §6, §7, §8).

Accepted journey J-04. Test plan v1.1 §1 and §2 are the normative coverage list; the contract is
normative for the wire shape. Expected bytes and header values come from `tests/export_contract`,
never hardcoded here, so one edit re-points every assertion if the board reopens a decision.

Two rules this file holds to, both from test plan §3.3:

* **Record counts come from `csv.reader`, never from splitting bytes on the terminator.** An
  embedded CRLF inside a quoted field is indistinguishable from a record separator by splitting,
  so `content.count(EOL)` is not a record count.
* **Permission is asserted as parity, not as identity-proofing.** `X-Role` is self-asserted and
  the brief puts authentication out of scope, so the guarantee under test is that the export's
  report set equals `GET /api/reports`'s set for the same headers — the export is never a wider
  door than the JSON endpoint beside it (contract Invariant P, test plan §2).
"""

from __future__ import annotations

import csv
import io
import re
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app import data
from app.data import Report
from app.main import app
from tests.export_contract import (
    ADMIN_BODY,
    BOM,
    EMPTY_BODY,
    FILENAME_RE,
    HEADER,
    VIEWER_BODY,
)

client = TestClient(app)

EXPORT = "/api/reports.csv"

#: Every `X-Role` spelling of test plan §2.1 P-1..P-6 plus P-15. Exactly `admin` selects the admin
#: role; every other value — absent, empty, cased differently, padded, invented — is a viewer.
#: `None` means the header is not sent at all.
ROLE_SPELLINGS = [None, "", "viewer", "admin", "Admin", "ADMIN", "root", " admin", "admin "]

#: Test plan §2.1 P-7..P-10: a role in the URL, a guessed id, a request for restricted rows. None
#: may influence the body (contract Invariant Q).
WIDENING_QUERY_STRINGS = [
    "role=admin",
    "x_role=admin",
    "X-Role=admin",
    "id=3",
    "report_id=3",
    "ids=1,2,3,4",
    "restricted=true",
    "include_restricted=1",
    "all=true",
]


def _headers(x_role: str | None) -> dict[str, str]:
    return {} if x_role is None else {"X-Role": x_role}


def _records(content: bytes) -> list[list[str]]:
    """Parse the body with `csv.reader` — the only honest way to count records (§3.3, trap 3)."""
    return list(csv.reader(io.StringIO(content.decode("utf-8"), newline="")))


def _ids(content: bytes) -> list[str]:
    return [record[0] for record in _records(content)[1:]]


# --- Exact bodies per role (AC-2, AC-3b, AC-5) ------------------------------------------------


def test_export_viewer_default_is_exact_bytes():
    """AC-2, AC-5: no `X-Role` at all yields the viewer file, byte for byte."""
    r = client.get(EXPORT)
    assert r.status_code == 200
    assert r.content == VIEWER_BODY
    assert len(r.content) == 99
    assert r.headers["content-length"] == str(len(VIEWER_BODY))


def test_export_admin_is_exact_bytes():
    """AC-3b: `X-Role: admin` yields the four-report file, byte for byte."""
    r = client.get(EXPORT, headers={"X-Role": "admin"})
    assert r.status_code == 200
    assert r.content == ADMIN_BODY
    assert len(r.content) == 130
    assert b"3,Payroll summary,finance,310" in r.content


def test_viewer_export_never_contains_payroll_summary():
    """AC-2, P-1: the restricted report is absent as a title *and* as an id field."""
    r = client.get(EXPORT)
    assert b"Payroll summary" not in r.content
    assert b"restricted" not in r.content
    assert "3" not in _ids(r.content)


# --- The four response headers (AC-22, AC-23, AC-7/P-13) -------------------------------------


def test_export_content_type_is_text_csv_utf8():
    """AC-22. Starlette appends `; charset=utf-8` for `text/*` media types."""
    assert client.get(EXPORT).headers["content-type"] == "text/csv; charset=utf-8"


def test_export_content_disposition_is_a_dated_attachment():
    """AC-23 [D-2]. The date is captured either side of the request rather than computed once:
    the filename is built from `datetime.now(UTC)`, so a single computed date fails if the
    request crosses midnight UTC (test plan §5.5)."""
    before = datetime.now(UTC).date()
    r = client.get(EXPORT)
    after = datetime.now(UTC).date()
    match = re.match(FILENAME_RE, r.headers["content-disposition"])
    assert match, r.headers["content-disposition"]
    assert date.fromisoformat(match.group(1)) in {before, after}


def test_export_sets_vary_x_role_and_cache_control_no_store():
    """AC-7, P-13. Not a performance nit: the body varies on a *request header*, so a cache keyed
    on the URL alone could hand an admin's file to a viewer even with a correct handler (R-1)."""
    r = client.get(EXPORT)
    assert r.headers["vary"] == "X-Role"
    assert r.headers["cache-control"] == "no-store"


def test_export_body_has_no_bom_on_the_wire():
    """AC-13 [D-3]. The server never emits a BOM; the UI prepends one to the downloaded Blob, so
    the two artifacts differ by exactly these three bytes and e2e asserts the other half."""
    r = client.get(EXPORT)
    assert not r.content.startswith(BOM)
    assert r.content[: len(HEADER)] == HEADER


# --- Parity with the JSON endpoint (AC-4, AC-6, AC-7) ----------------------------------------


@pytest.mark.parametrize("x_role", ROLE_SPELLINGS, ids=lambda v: repr(v))
def test_export_id_sequence_matches_json_api_for_every_role_value(x_role: str | None):
    """AC-4, AC-6, AC-7 parity, P-18. For every role spelling the export's id sequence equals
    `GET /api/reports`'s id list for identical headers — the export is never a wider door."""
    headers = _headers(x_role)
    csv_response = client.get(EXPORT, headers=headers)
    json_response = client.get("/api/reports", headers=headers)
    assert csv_response.status_code == json_response.status_code == 200
    assert _ids(csv_response.content) == [str(item["id"]) for item in json_response.json()]


def test_export_duplicate_x_role_header_first_value_wins():
    """AC-6, P-11, P-16. Starlette's `Headers.get` returns the first occurrence, and the export
    inherits that from `_role` rather than parsing the header itself — so it agrees with the JSON
    endpoint on exactly the awkward requests a second parser would get wrong."""
    admin_first = [("X-Role", "admin"), ("X-Role", "viewer")]
    viewer_first = [("X-Role", "viewer"), ("X-Role", "admin")]

    assert _ids(client.get(EXPORT, headers=admin_first).content) == ["1", "2", "3", "4"]
    assert _ids(client.get(EXPORT, headers=viewer_first).content) == ["1", "2", "4"]

    for headers in (admin_first, viewer_first):
        csv_ids = _ids(client.get(EXPORT, headers=headers).content)
        json_ids = [str(item["id"]) for item in client.get("/api/reports", headers=headers).json()]
        assert csv_ids == json_ids


@pytest.mark.parametrize("query", WIDENING_QUERY_STRINGS)
def test_export_ignores_every_query_parameter(query: str):
    """AC-7, P-7..P-9 (contract Invariant Q). The assertion is byte-identity with the no-query
    viewer body rather than "does not contain report 3": byte-identity also catches a parameter
    that changes the order, the column set or the encoding."""
    assert client.get(f"{EXPORT}?{query}").content == VIEWER_BODY


def test_export_query_parameter_cannot_override_a_viewer_header():
    """P-10: `?role=admin` sent *with* `X-Role: viewer` is still the viewer file."""
    r = client.get(f"{EXPORT}?role=admin", headers={"X-Role": "viewer"})
    assert r.content == VIEWER_BODY


# --- Methods, slash, casing, and the paths that do not exist (AC-27, P-12) --------------------


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_export_unsupported_methods_are_405_with_allow_get(method: str):
    """AC-27. The JSON body is asserted here but not for `HEAD` — see the next test."""
    r = client.request(method, EXPORT)
    assert r.status_code == 405
    assert r.headers["allow"] == "GET"
    assert r.json() == {"detail": "Method Not Allowed"}


def test_export_head_is_405_with_allow_get_and_no_body():
    """AC-27, errata S-6 / test plan §8.2 C-1. Contract §7 lists the JSON body for `HEAD` too,
    but HTTP strips a `HEAD` response body, so only the status and `Allow` are assertable. This
    matches the existing surface: `HEAD /api/reports` already `405`s today."""
    r = client.head(EXPORT)
    assert r.status_code == 405
    assert r.headers["allow"] == "GET"
    assert r.content == b""


def test_export_trailing_slash_redirects_to_the_canonical_path():
    """AC-27. Starlette `redirect_slashes`; clients that follow redirects see no difference."""
    r = client.get(EXPORT + "/", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"].endswith(EXPORT)


def test_export_path_is_case_sensitive():
    """AC-27: `/api/reports.CSV` is not the export route."""
    assert client.get("/api/reports.CSV").status_code == 404


def test_there_is_no_per_report_csv_route():
    """P-12: no route names a single report's CSV, so there is no id for a viewer to guess.

    Correction to test plan §2.1 P-12, which predicted `404` for both paths. Verified at
    `c7816bc`: `/api/reports/3.csv` is **422** `int_parsing` — it reaches
    `GET /api/reports/{report_id}` and fails path validation — while `/api/reports.csv/3` is
    `404`. Neither leaks report content, which is the property P-12 exists to assert, so the
    status is corrected rather than the requirement. Asserted for both roles because a `422`
    raised before the handler cannot depend on the role.
    """
    for headers in ({}, {"X-Role": "admin"}):
        nested = client.get("/api/reports/3.csv", headers=headers)
        assert nested.status_code == 422
        assert b"Payroll summary" not in nested.content

        suffixed = client.get("/api/reports.csv/3", headers=headers)
        assert suffixed.status_code == 404
        assert b"Payroll summary" not in suffixed.content


# --- Report sets the seed data cannot reach (AC-16, AC-21) ------------------------------------


def test_export_empty_permitted_set_is_header_row_only(monkeypatch: pytest.MonkeyPatch):
    """AC-16 [D-7]. Emptied at `data._REPORTS` rather than by replacing `list_reports`, so the
    real filter still runs and the response goes through the one code path the non-empty case
    uses. A file is still downloaded: `Content-Disposition` is present and the body is valid CSV
    with zero data rows, not a zero-byte file."""
    monkeypatch.setattr(data, "_REPORTS", [])
    r = client.get(EXPORT)
    assert r.status_code == 200
    assert r.content == EMPTY_BODY
    assert len(r.content) == 21
    assert r.headers["content-length"] == "21"
    assert r.headers["content-disposition"].startswith("attachment;")
    assert _records(r.content) == [["id", "title", "owner", "rows"]]


def test_a_newly_restricted_report_is_excluded_from_a_viewer_export(
    monkeypatch: pytest.MonkeyPatch,
):
    """AC-21, P-14: the brief's "a future report flagged `restricted` inherits this
    automatically". A fifth restricted report is injected into the data layer and the export
    changes correctly with **zero** export-side changes, because the export never mentions
    `restricted` — it reuses `data.list_reports(role)` (contract Invariant P)."""
    injected = Report(5, "Secret plan", "exec", 7, restricted=True)
    monkeypatch.setattr(data, "_REPORTS", [*data._REPORTS, injected])

    viewer = client.get(EXPORT)
    admin = client.get(EXPORT, headers={"X-Role": "admin"})

    assert _ids(viewer.content) == ["1", "2", "4"]
    assert b"Secret plan" not in viewer.content
    assert viewer.content == VIEWER_BODY

    assert _ids(admin.content) == ["1", "2", "3", "4", "5"]
    assert b"Secret plan" in admin.content
