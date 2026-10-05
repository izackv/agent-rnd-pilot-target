from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_reports_viewer_default():
    r = client.get("/api/reports")
    assert r.status_code == 200
    assert [x["id"] for x in r.json()] == [1, 2, 4]


def test_reports_admin_header():
    r = client.get("/api/reports", headers={"X-Role": "admin"})
    assert [x["id"] for x in r.json()] == [1, 2, 3, 4]


def test_restricted_report_404_for_viewer():
    assert client.get("/api/reports/3").status_code == 404
    assert client.get("/api/reports/3", headers={"X-Role": "admin"}).status_code == 200


def test_index_renders():
    r = client.get("/")
    assert r.status_code == 200 and "<table" in r.text


def test_existing_endpoints_are_byte_unchanged_by_the_export():
    """Contract §10: the export is additive. The five tests above are the regression floor for
    the owner's non-negotiable 3 ("permissions must keep working exactly as today"); this one
    pins the full response payloads rather than just the id lists, so a change to a field name,
    a field's value or a status code cannot slip through while the id assertions still pass.

    Every literal below was captured at baseline `8499df9`, before `GET /api/reports.csv`
    existed. Note `"restricted": false` reaching a viewer: that is errata E-2 / test plan §8.2
    C-2 — omitting `restricted` from the CSV is not a leak fix, because the JSON endpoint has
    always disclosed the flag. Do not "fix" either side on the strength of the brief's rationale.
    """
    viewer_payload = [
        {"id": 1, "title": "Monthly usage", "owner": "ops", "rows": 1200, "restricted": False},
        {"id": 2, "title": "Error budget", "owner": "sre", "rows": 48, "restricted": False},
        {"id": 4, "title": "Signup funnel", "owner": "growth", "rows": 5200, "restricted": False},
    ]
    restricted_payload = {
        "id": 3,
        "title": "Payroll summary",
        "owner": "finance",
        "rows": 310,
        "restricted": True,
    }

    reports = client.get("/api/reports")
    assert reports.status_code == 200
    assert reports.headers["content-type"] == "application/json"
    assert reports.json() == viewer_payload

    admin_reports = client.get("/api/reports", headers={"X-Role": "admin"})
    assert admin_reports.status_code == 200
    assert admin_reports.json() == [
        viewer_payload[0],
        viewer_payload[1],
        restricted_payload,
        viewer_payload[2],
    ]

    denied = client.get("/api/reports/3")
    assert denied.status_code == 404
    assert denied.json() == {"detail": "report not found"}

    allowed = client.get("/api/reports/3", headers={"X-Role": "admin"})
    assert allowed.status_code == 200
    assert allowed.json() == restricted_payload

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": "0.1.0"}
