"""The CSV serializer and the cell-safety guard as pure functions (test plan v1.1 §3).

Every expected byte string here is pinned against contract v1.1 §4/§5. Decision-dependent values
come from `tests/export_contract.py`, never hardcoded, so one edit there re-points every
assertion if the board answers a decision differently.
"""

from __future__ import annotations

import csv
import inspect
import io
import re
from dataclasses import fields

import pytest

from app import data
from app import export as export_module
from app.data import Report
from app.export import COLUMNS, render_reports_csv
from app.export import _safe as safe
from tests.export_contract import (
    ADMIN_BODY,
    EMPTY_BODY,
    EOL,
    GUARD,
    HEADER,
    RISKY_PREFIX,
    SAFE_PREFIX,
    VIEWER_BODY,
    WHITESPACE_PRESERVED,
)

TAB = "\t"
CR = "\r"
LF = "\n"

# Test plan §3.3, the twelve cell-safety fixtures. Each `expected` is the record bytes only; the
# whole-body expectation is HEADER + EOL + expected.
CELL_SAFETY_FIXTURES = [
    ("comma", Report(9, "=SUM(A1:A9)", "a,b", 7), b'9,\'=SUM(A1:A9),"a,b",7\r\n'),
    (
        "dquote",
        Report(10, 'He said "hi"', f"line1{LF}line2", 0),
        b'10,"He said ""hi""","line1\nline2",0\r\n',
    ),
    (
        "tab_and_negative",
        Report(11, f"{TAB}Tabbed", "-finance", -5),
        b"11,'\tTabbed,'-finance,-5\r\n",
    ),
    ("empty_and_at", Report(12, "", "@ops", 0), b"12,,'@ops,0\r\n"),
    (
        "non_ascii_and_spaces",
        Report(13, "Café ☕ naïve", " lead ", 3),
        b"13,Caf\xc3\xa9 \xe2\x98\x95 na\xc3\xafve, lead ,3\r\n",
    ),
    ("leading_plus", Report(14, "+1", "ops", 1), b"14,'+1,ops,1\r\n"),
    ("leading_cr", Report(15, f"{CR}CR", "ops", 1), b'15,"\'\rCR",ops,1\r\n'),
    ("equals_not_first", Report(16, "a=b", "ops", 1), b"16,a=b,ops,1\r\n"),
    ("space_then_equals", Report(17, " =notfirst", "ops", 1), b"17, =notfirst,ops,1\r\n"),
    ("already_apostrophed", Report(18, "already'quoted", "ops", 1), b"18,already'quoted,ops,1\r\n"),
    ("guard_then_quote", Report(19, "=a,b", "ops", 1), b'19,"\'=a,b",ops,1\r\n'),
    ("astral_emoji", Report(20, "spark 🙂", "ops", 1), b"20,spark \xf0\x9f\x99\x82,ops,1\r\n"),
]

# Test plan §3.3, fixture 21 — kept out of the twelve because its only job is to pin the trap that
# a record count must never be computed by splitting bytes on the terminator.
FIXTURE_21 = Report(21, f"line1{CR}{LF}line2", "ops", 1)
FIXTURE_21_RECORD = b'21,"line1\r\nline2",ops,1\r\n'

_IDS = [name for name, _, _ in CELL_SAFETY_FIXTURES]
_CASES = [(report, expected) for _, report, expected in CELL_SAFETY_FIXTURES]


def _records(body: bytes) -> list[list[str]]:
    """Parse records the way a conformant CSV consumer does — never by splitting on EOL."""
    return list(csv.reader(io.StringIO(body.decode("utf-8"), newline="")))


def _unguard(field: str) -> str:
    """Strip at most one leading GUARD, which is the whole of the protection's reversibility."""
    return field[1:] if field.startswith(GUARD) else field


# --- the column set (R-2) -------------------------------------------------------------------


def test_columns_is_an_explicit_tuple_pinned_to_the_contract():
    assert COLUMNS == ("id", "title", "owner", "rows")


def test_header_row_is_exactly_the_four_columns():
    output = render_reports_csv(data.list_reports(data.ROLE_VIEWER))
    assert _records(output)[0] == list(COLUMNS)
    assert output.startswith(HEADER + EOL)
    assert output.count(HEADER) == 1


def test_the_column_set_is_a_strict_subset_of_the_report_dataclass():
    """A field on `Report` that is not a column must stay out of the export (contract §4).

    This is the assertion that fails if someone later swaps the explicit tuple for `asdict`, or
    adds a dataclass field expecting the export to pick it up for free.
    """
    declared = {f.name for f in fields(Report)}
    assert set(COLUMNS) < declared
    assert declared - set(COLUMNS)


# --- today's seed data ----------------------------------------------------------------------


def test_viewer_seed_body_is_exact_bytes():
    output = render_reports_csv(data.list_reports(data.ROLE_VIEWER))
    assert output == VIEWER_BODY
    assert len(output) == 99


def test_admin_seed_body_is_exact_bytes():
    output = render_reports_csv(data.list_reports(data.ROLE_ADMIN))
    assert output == ADMIN_BODY
    assert len(output) == 130


def test_admin_body_minus_the_restricted_record_equals_the_viewer_body():
    """Pins the two expectations to each other so they cannot drift apart (test plan §3.2)."""
    assert ADMIN_BODY.replace(b"3,Payroll summary,finance,310" + EOL, b"") == VIEWER_BODY


def test_empty_report_list_is_header_row_only():
    output = render_reports_csv([])
    assert output == HEADER + EOL == EMPTY_BODY
    assert len(output) == 21


# --- cell safety: exact bytes ---------------------------------------------------------------


@pytest.mark.parametrize(("report", "expected"), _CASES, ids=_IDS)
def test_cell_safety_fixture_bytes(report: Report, expected: bytes):
    assert render_reports_csv([report]) == HEADER + EOL + expected


def test_embedded_crlf_in_a_field_is_written_through_verbatim():
    output = render_reports_csv([FIXTURE_21])
    assert output == HEADER + EOL + FIXTURE_21_RECORD
    # The trap: splitting on EOL sees three pieces in a two-record file.
    assert len(output.split(EOL)) - 1 == 3
    assert len(_records(output)) == 2


def test_embedded_newline_is_written_through_as_bare_lf():
    report = Report(10, 'He said "hi"', f"line1{LF}line2", 0)
    output = render_reports_csv([report])
    assert b'"line1\nline2"' in output
    assert b"line1\r\nline2" not in output
    assert output.count(EOL) == 1 + 1


def test_non_ascii_round_trips_codepoint_for_codepoint():
    reports = [Report(13, "Café ☕ naïve", " lead ", 3), Report(20, "spark 🙂", "ops", 1)]
    output = render_reports_csv(reports)
    assert b"13,Caf\xc3\xa9 \xe2\x98\x95 na\xc3\xafve, lead ,3\r\n" in output
    assert b"20,spark \xf0\x9f\x99\x82,ops,1\r\n" in output
    recovered = _records(output)[1:]
    assert [row[1] for row in recovered] == ["Café ☕ naïve", "spark 🙂"]


def test_surrounding_whitespace_is_preserved_unquoted():
    assert WHITESPACE_PRESERVED  # [QA-D-A] — flip this constant and this test inverts
    output = render_reports_csv([Report(13, "Café ☕ naïve", " lead ", 3)])
    assert b", lead ,3" in output
    assert b'" lead "' not in output
    assert _records(output)[1][2] == " lead "


def test_empty_field_is_an_empty_unquoted_field():
    output = render_reports_csv([Report(12, "", "@ops", 0)])
    assert output == HEADER + EOL + b"12,,'@ops,0\r\n"
    assert b'""' not in output
    assert _records(output)[1][1] == ""


# --- cell safety: the guard as a function ---------------------------------------------------


@pytest.mark.parametrize("char", list(RISKY_PREFIX))
def test_guard_prefixes_every_risky_leading_character(char: str):
    assert safe(char + "x") == GUARD + char + "x"
    output = render_reports_csv([Report(1, char + "x", char + "y", 1)])
    for field in _records(output)[1][1:3]:
        assert field.startswith(GUARD)
        assert field[0] not in RISKY_PREFIX


def test_the_guard_alphabet_is_exactly_the_contract_list():
    """Equality, not membership — a character *added* to `RISKY_PREFIXES` must fail too.

    Every other guard assertion iterates *over* `RISKY_PREFIX`, which catches a character removed
    from the guard alphabet and is blind to one added to it. Contract §5's list is normative, so
    pin it in both directions here and keep the negative fixtures honestly non-risky.
    """
    assert set(export_module.RISKY_PREFIXES) == set(RISKY_PREFIX)
    assert set(SAFE_PREFIX).isdisjoint(RISKY_PREFIX)


@pytest.mark.parametrize("char", list(SAFE_PREFIX))
def test_a_non_risky_leading_character_is_never_guarded(char: str):
    """The negative direction of the guard: a plausible-looking prefix stays untouched.

    `" "` is deliberately in this set: WHITESPACE_PRESERVED [QA-D-A] makes a leading space both a
    non-risky prefix and a pinned decision. `\\n` is here and `\\r` is not — only CR is risky.
    """
    assert safe(char + "x") == char + "x"
    output = render_reports_csv([Report(1, char + "x", char + "y", 1)])
    for field, expected in zip(_records(output)[1][1:3], (char + "x", char + "y"), strict=True):
        assert field == expected
        assert not field.startswith(GUARD)


def test_guard_examines_only_the_first_character():
    assert safe("a=b") == "a=b"
    assert safe(" =notfirst") == " =notfirst"
    assert safe("") == ""
    assert safe("already'quoted") == "already'quoted"


def test_guard_is_mechanically_reversible():
    """AC-14: stripping at most one leading GUARD recovers the source value exactly."""
    for _, report, _ in CELL_SAFETY_FIXTURES:
        record = _records(render_reports_csv([report]))[1]
        assert len(record) == len(COLUMNS)
        assert record[0] == str(report.id)
        assert not record[0].startswith(GUARD)
        assert _unguard(record[1]) == report.title
        assert _unguard(record[2]) == report.owner


@pytest.mark.parametrize("rows", [1200, 0, -5])
def test_numeric_fields_are_never_guarded_or_quoted(rows: int):
    """A blanket sanitizer passes every title-focused test and still breaks SUM (R-3, AC-18)."""
    output = render_reports_csv([Report(-7, "t", "o", rows)])
    record = _records(output)[1]
    for field in (record[0], record[3]):
        assert re.fullmatch(r"-?[0-9]+", field)
        assert GUARD not in field
    assert record[0] == "-7" and record[3] == str(rows)
    assert b'"' not in output
    assert f",{rows}\r\n".encode() in output


# --- structure, ordering and terminators ----------------------------------------------------


def test_every_fixture_round_trips_through_csv_reader():
    for _, report, _ in CELL_SAFETY_FIXTURES:
        records = _records(render_reports_csv([report]))
        assert len(records) == 2
        assert len(records[1]) == 4
        assert records[1] == [
            str(report.id),
            safe(report.title),
            safe(report.owner),
            str(report.rows),
        ]


def test_every_record_has_four_fields_for_every_fixture():
    reports = [report for _, report, _ in CELL_SAFETY_FIXTURES] + [FIXTURE_21]
    records = _records(render_reports_csv(reports))
    assert len(records) == 1 + len(reports)
    assert all(len(record) == 4 for record in records)


def test_records_are_in_id_ascending_order_whatever_the_input_order():
    by_id = {r.id: r for r in data.list_reports(data.ROLE_ADMIN)}
    shuffled = [by_id[4], by_id[1], by_id[3], by_id[2]]
    output = render_reports_csv(shuffled)
    assert [record[0] for record in _records(output)[1:]] == ["1", "2", "3", "4"]
    assert output == ADMIN_BODY


def test_every_record_ends_with_crlf_including_the_last():
    reports = [report for _, report, _ in CELL_SAFETY_FIXTURES] + [FIXTURE_21]
    output = render_reports_csv(reports)
    assert output.endswith(EOL)
    # A writer whose stream also translates newlines emits CR CR LF: parseable, round-trippable
    # and malformed. Only a byte assertion catches it.
    assert b"\r\r\n" not in output
    assert len(_records(output)) == 1 + len(reports)


def test_serializer_emits_no_bom():
    """The BOM belongs to the downloaded file only; the server has no BOM code path (§4, D-3)."""
    for reports in ([], data.list_reports(data.ROLE_VIEWER), data.list_reports(data.ROLE_ADMIN)):
        assert render_reports_csv(reports).startswith(HEADER)


# --- the permission flag must not reach the export ------------------------------------------


def test_restricted_is_neither_a_column_nor_a_value_in_the_body():
    output = render_reports_csv(data.list_reports(data.ROLE_ADMIN))
    assert b"restricted" not in output
    records = _records(output)
    assert b"restricted" not in HEADER
    for record in records[1:]:
        assert not {f.lower() for f in record} & {"true", "false"}


def test_export_module_never_mentions_restricted():
    """Structural guarantee of contract §6: the export never names the visibility flag at all."""
    assert "restricted" not in inspect.getsource(export_module)
