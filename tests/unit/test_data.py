from app import data


def test_viewer_cannot_see_restricted():
    ids = [r.id for r in data.list_reports(data.ROLE_VIEWER)]
    assert 3 not in ids and len(ids) == 3


def test_admin_sees_all():
    assert len(data.list_reports(data.ROLE_ADMIN)) == 4


def test_get_report_respects_role():
    assert data.get_report(3, data.ROLE_VIEWER) is None
    assert data.get_report(3, data.ROLE_ADMIN) is not None
