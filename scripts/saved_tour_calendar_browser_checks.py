"""Actual Run Saved Calendar -> Edition Chromium journey, backed by production API/SQLite.

Invoked during the existing 64-player/three-match Save-and-restart acceptance.
No fake route responses, browser mocks, generated sport outcomes or draft fallback.
"""
from __future__ import annotations

from urllib.parse import quote

from playwright.sync_api import expect


def verify_saved_tour_calendar(page, run_url: str, artifacts, port: int, source: dict, *, prefix: str = "", expected: dict | None = None) -> dict:
    base, run_id = run_url.split("/admin/runs/", 1)
    api = f"http://127.0.0.1:{port}"
    branch_id, revision_id, event_id = (
        source["branch_id"], source["saved_revision_id"], source["event_id"]
    )
    enc = lambda text: quote(str(text), safe="")
    scope = f"/admin/runs/{enc(run_id)}/branches/{enc(branch_id)}"
    params = f"?revision_id={enc(revision_id)}&season_index=0"

    def get(url, status=200):
        response = page.request.get(api + url, timeout=40000)
        assert response.status == status, (url, response.status, response.text()[:1500])
        return response.json() if status == 200 else None

    branch = get("/run-branches/" + enc(branch_id))
    assert branch["saved_head_revision_id"] == revision_id, branch
    calendar = get(scope + "/tour/calendar" + params)
    assert calendar["source"] == "reachable_saved_revision"
    assert calendar["branch_id"] == calendar["revision_branch_id"] == branch_id
    assert calendar["saved_revision_id"] == revision_id
    assert calendar["week_count"] == 61 and calendar["season_index"] == 0
    editions = [e for e in calendar["editions"] if e["event_id"] == event_id]
    assert len(editions) == 1, calendar
    edition = editions[0]
    assert edition["result_published"] is True, edition
    assert edition["season_week"] == 1

    result = get(scope + "/tour/editions/" + enc(event_id) + params)
    assert result["edition"] == edition and result["lifecycle_status"] == "unavailable"
    assert result["published_result"]["champion_player_id"] == source["player_id"]
    assert any(m["match_id"] == source["match_id"] and m["scoreline"] == source["scoreline"]
               for m in result["published_result"]["matches"])
    get(scope + "/tour/calendar?revision_id=foreign&season_index=0", status=404)
    get(scope + "/tour/editions/" + enc(event_id) + "?revision_id=" + enc(revision_id)
        + "&season_index=2", status=404)
    get(scope + "/tour/calendar?revision_id=" + enc(revision_id) + "&season_index=50", status=422)

    # Open the exact immutable snapshot in the *real* application and verify
    # the 61-week grid, a list view and the back-link's preserved filters.
    route = (f"/admin/runs/{enc(run_id)}/tour/calendar"
             f"?branch={enc(branch_id)}&revision={enc(revision_id)}&season=0")
    page.goto(base + route)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    expect(page.get_by_role("heading", name="Saved season calendar")).to_be_visible()
    expect(page.get_by_label("Saved Tour 61 season weeks").get_by_role("heading", name="Week 61")).to_be_visible()
    expect(page.get_by_role("link", name=edition["event_name"])).to_be_visible()
    page.get_by_role("combobox", name="Saved Tour view").select_option("list")
    page.get_by_role("combobox", name="Saved Tour filter country").select_option(edition["host_country"])
    page.get_by_role("link", name=edition["event_name"]).click()
    expect(page.get_by_role("heading", name=edition["event_name"])).to_be_visible()
    assert "revision=" + enc(revision_id) in page.url
    expect(page.get_by_role("navigation", name="Edition sections").get_by_role("button")).to_have_count(6)
    page.get_by_role("button", name="Results").click()
    assert source["scoreline"] in page.locator("#saved-results-main").inner_text()
    page.get_by_role("button", name="Schedule & matches").click()
    assert source["scoreline"] in page.locator("#saved-schedule-main").inner_text()
    page.get_by_role("button", name="Draw / groups").click()
    page.get_by_role("button", name="Qualification").click()
    expect(page.get_by_text("No evidenced matches available.")).to_be_visible()
    page.get_by_role("button", name="Main").click()
    assert source["scoreline"] in page.locator("main").inner_text()
    page.get_by_role("button", name="Entries & participants").click()
    expect(page.get_by_text(source["player_id"], exact=False).first).to_be_visible()
    page.get_by_role("button", name="Settings").click()
    expect(page.get_by_text("Saved Edition parameters", exact=False)).to_be_visible()
    page.get_by_role("button", name="Overview").click()
    expect(page.get_by_text("Authoritative lifecycle status: unavailable.", exact=False)).to_be_visible()
    page.screenshot(path=str(artifacts / f"{prefix}saved-tour-edition.png"), full_page=True)
    page.get_by_role("link", name="Back to calendar").click()
    expect(page.get_by_role("table", name="Saved Tour edition list")).to_be_visible()
    assert "country=" + enc(edition["host_country"]) in page.url
    assert "revision=" + enc(revision_id) in page.url

    # A historical earlier Saved Revision must not inherit a later result.
    history = get(f"/run-containers/{enc(run_id)}/branches/{enc(branch_id)}/saved-revisions")
    older = [r["revision_id"] for r in history["saved_revisions"]
             if r["revision_id"] != revision_id]
    if older:
        oldest = older[0]
        old = get(scope + "/tour/calendar?revision_id=" + enc(oldest) + "&season_index=0")
        assert old["saved_revision_id"] == oldest
        assert not any(e["event_id"] == event_id and e["result_published"] for e in old["editions"])
    page.screenshot(path=str(artifacts / f"{prefix}saved-tour-calendar.png"), full_page=True)
    proof = {
        "run_id": run_id, "branch_id": branch_id, "saved_revision_id": revision_id,
        "event_id": event_id, "published_matches": len(result["published_result"]["matches"]),
        "season_index": 0, "week_count": 61, "older_saved_revision_without_result": bool(older),
        "filters_and_return": True, "six_tabs": True,
    }
    if expected is not None:
        assert proof == expected, (proof, expected)
    return proof
