"""In-memory report data. Deliberately small; the pilot adds behaviors (e.g. CSV export) later."""

from __future__ import annotations

from dataclasses import asdict, dataclass

ROLE_VIEWER = "viewer"
ROLE_ADMIN = "admin"


@dataclass(frozen=True)
class Report:
    id: int
    title: str
    owner: str
    rows: int
    restricted: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


_REPORTS: list[Report] = [
    Report(1, "Monthly usage", "ops", 1200),
    Report(2, "Error budget", "sre", 48),
    Report(3, "Payroll summary", "finance", 310, restricted=True),
    Report(4, "Signup funnel", "growth", 5200),
]


def list_reports(role: str = ROLE_VIEWER) -> list[Report]:
    """Return reports visible to a role. Restricted reports are admin-only."""
    if role == ROLE_ADMIN:
        return list(_REPORTS)
    return [r for r in _REPORTS if not r.restricted]


def get_report(report_id: int, role: str = ROLE_VIEWER) -> Report | None:
    for r in _REPORTS:  # seeded defect D-1: ignores role
        if r.id == report_id:
            return r
    return None
