"""Create and configure a fresh ATP Run via the browser and a real API."""

import argparse
from contextlib import suppress
import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from playwright.sync_api import Error, expect, sync_playwright


def configure_atp_run(page, base_url, api_url):
    page.goto(base_url + "/admin/runs/new")
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    page.get_by_label("Unique Run name").fill("Browser ATP W52 acceptance")
    page.get_by_label("Set up a Run from ATP packages").check()
    page.get_by_label("Start year", exact=True).fill("2025")
    page.get_by_label("Number of seasons", exact=True).fill("3")
    page.get_by_role("button", name="Review calendar", exact=True).click()

    with page.expect_response(
        lambda response: urlsplit(response.url).path == "/run-containers"
        and response.request.method == "POST"
    ) as creation:
        page.get_by_role("button", name="Create Run and continue to ATP packages").click()
    assert creation.value.ok, creation.value.status
    run = creation.value.json()
    assert run["metadata_json"]["run_calendar"] == {
        "schema_version": "run_calendar.v1",
        "weeks_per_year": 52,
        "season_start_year_week": 1,
        "start_year": 2025,
        "season_count": 3,
    }
    run_id, branch_id = run["run_id"], run["viewer_branch_id"]
    target = urlencode({"run": run_id, "branch": branch_id})
    draft_url = f"{api_url}/run-containers/{run_id}/branches/{branch_id}/working-draft"
    admin_url = f"{api_url}/admin/runs/{run_id}/branches/{branch_id}"

    def read(url):
        response = page.request.get(url)
        expect(response).to_be_ok()
        return response.json()

    def check_target(path):
        expect(page).to_have_url(f"{base_url}{path}?{target}")
        for field, identity in (("Target Run", run_id), ("Target Branch", branch_id)):
            selector = page.get_by_role("combobox", name=field, exact=True)
            expect(selector).to_have_value(identity)
            expect(selector).to_be_disabled()

    def confirm_and_save(approval, success, previous_head):
        page.get_by_label(approval, exact=True).check()
        page.get_by_role("button", name="Confirm into Working Draft", exact=True).click()
        save = page.get_by_role("button", name="Save revision", exact=True)
        expect(save).to_be_enabled()
        staged = read(draft_url)
        assert staged["status"] == "dirty"
        assert staged["base_saved_revision_id"] == previous_head

        save.click()
        expect(page.get_by_role("status").filter(has_text=success)).to_be_visible()
        saved = read(draft_url)
        assert saved["status"] == "clean"
        assert saved["base_saved_revision_id"] != previous_head
        return saved["base_saved_revision_id"]

    check_target("/admin/packages/world/atp_earth/apply")
    initial_draft = read(draft_url)
    assert initial_draft["status"] == "clean"
    next_package = page.get_by_role("link", name="Continue to the historical ATP calendar")
    expect(next_package).to_have_count(0)

    page.get_by_role("button", name="Select all valid", exact=True).click()
    world_head = confirm_and_save(
        "I reviewed the exact selection, changes and target Branch.",
        "New Saved Revision saved.",
        initial_draft["base_saved_revision_id"],
    )
    next_package.click()
    check_target("/admin/packages/atp-tour-calendar-reference")
    tour_head = confirm_and_save(
        "I reviewed the changes and confirm the displayed packages.",
        "A new Saved Revision has been saved.",
        world_head,
    )

    page.reload()
    check_target("/admin/packages/atp-tour-calendar-reference")
    page.get_by_label("ATP season for this Run", exact=True).select_option("2025")
    page.get_by_role("button", name="Preview weeks from the Saved ATP Package").click()
    saved_calendar = page.locator("section.package-apply-step").filter(
        has=page.get_by_role("heading", name="ATP calendar in Run weeks (W52)", exact=True),
    ).filter(has=page.get_by_label("ATP season for this Run", exact=True))
    dallas = saved_calendar.locator("tbody").get_by_role("row").filter(has_text="Dallas")
    expect(dallas).to_contain_text("2025-02-03")
    expect(dallas).to_contain_text("2025/W06 (S1/W06)")

    catalog = read(admin_url + "/calendar-tour/atp-source-editions")
    assert (catalog["run_id"], catalog["branch_id"], catalog["saved_head_revision_id"]) == (
        run_id, branch_id, tour_head,
    )
    profile = next(
        edition for edition in catalog["entries"]
        if edition["profile"]["occurrence_id"] == "atp_2025_dallas"
    )
    assert profile["qualification_calendar_projection"]["run_weeks"] == [
        {"season_index": 0, "season_week": 5},
    ]
    assert [week["season_week"] for week in profile["calendar_projection"]["run_weeks"]] == [6]
    assert read(draft_url)["base_saved_revision_id"] == tour_head


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--api-url", default="http://127.0.0.1:8001")
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=120_000)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("CHROME_BIN") or None,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            page = browser.new_page()
            page.set_default_timeout(120_000)
            try:
                configure_atp_run(page, args.base_url.rstrip("/"), args.api_url.rstrip("/"))
            except Exception:
                with suppress(Error):
                    page.screenshot(path=args.artifacts / "atp-w52-run-setup-failure.png", timeout=5_000)
                raise
            page.screenshot(path=args.artifacts / "atp-w52-run-setup.png")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
