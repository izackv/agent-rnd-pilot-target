"""Accepted user journey J-01: a viewer opens the reports page and sees only permitted reports;
switching to admin reveals the restricted one."""

from playwright.sync_api import Page, expect


def test_j01_reports_journey(page: Page, base_url: str):
    page.goto(base_url + "/")
    expect(page.get_by_role("heading", name="Reports")).to_be_visible()
    expect(page.locator("#reports tbody tr")).to_have_count(3)
    expect(page.locator("#status")).to_have_text("3 reports")
    page.get_by_label("role").select_option("admin")
    expect(page.locator("#reports tbody tr")).to_have_count(4)
    expect(page.locator("#reports tbody tr[data-id='3']")).to_contain_text("Payroll summary")
