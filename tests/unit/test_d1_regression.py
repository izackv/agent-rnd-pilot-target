"""Regression test for defect D-1: a viewer must not be able to fetch a restricted report by id."""

from app import data


def test_d1_viewer_cannot_fetch_restricted_by_id():
    assert data.get_report(3, data.ROLE_VIEWER) is None
