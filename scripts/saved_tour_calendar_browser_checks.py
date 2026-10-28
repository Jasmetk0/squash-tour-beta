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
    # The same saved snapshot also carries the canonical accepted entrant field
    # and the original/effective first-round draw, never the live Viewer HEAD.
    field = result["entry_field"]
    draw = result["draw"]
    assert field is not None and draw is not None, result
    for item in (field, draw):
        assert item["product_run_id"] == run_id
        assert item["viewer_branch_id"] == branch_id
        assert item["event_id"] == event_id
    assert field["direct_main_player_ids"], field
    assert draw["main"]["slots"] and draw["main"]["bracket_size"] == len(draw["main"]["slots"])
    assert any(slot["player_id"] == source["player_id"] for slot in draw["main"]["slots"])
    saved_schedule = result["match_schedule"]
    assert saved_schedule is not None, ("Canonical real Match Day schedule missing", result)
    assert saved_schedule["source"] == "saved_week_simulation_schedule.v2"
    assert saved_schedule["run_id"] == run_id
    assert saved_schedule["revision_branch_id"] == branch_id
    assert saved_schedule["season_index"] == 0
    assert saved_schedule["season_week"] == edition["season_week"]
    assert saved_schedule["event_id"] == event_id
    assert saved_schedule["slots"] and all(
        slot["global_slot_ordinal"] > 0 and slot["match_day_ordinal"] > 0
        and slot["match_order"] > 0 and slot["round_number"] > 0
        for slot in saved_schedule["slots"]
    )
    match_ids = {m["match_id"] for m in result["published_result"]["matches"]}
    assert source["match_id"] in match_ids
    assert any(slot["match_id"] == source["match_id"] for slot in saved_schedule["slots"])
    assert all(slot["match_id"] is None or slot["match_id"] in match_ids
               for slot in saved_schedule["slots"])
    # The historical Edition match endpoint is NOT the current player HEAD.
    # It must read exactly this Saved Revision and a real archived rally log.
    match_path = (scope + "/tour/editions/" + enc(event_id)
                  + "/matches/" + enc(source["match_id"]))
    match_query = params + "&offset=0&limit=25"
    archived = get(match_path + match_query)
    assert archived["schema_version"] == "run_saved_tour_match_detail.v1"
    assert archived["source"] == "reachable_saved_revision"
    assert archived["branch_id"] == archived["revision_branch_id"] == branch_id
    assert archived["saved_revision_id"] == revision_id
    assert archived["match"]["match_id"] == source["match_id"]
    assert archived["match"]["scoreline"] == source["scoreline"]
    assert archived["replay_status"] == "available", ("Rally archive missing", archived)
    assert archived["total_rallies"] > 25 and archived["has_more"]
    assert len(archived["rallies"]) == 25
    later_rallies = get(match_path + params + "&offset=25&limit=25")
    assert later_rallies["rallies"][0]["rally_index"] == 26
    assert later_rallies["saved_revision_id"] == revision_id
    get(match_path.replace("/branches/" + enc(branch_id) + "/",
                           "/branches/foreign-branch/") + params, status=404)
    get(match_path + "?revision_id=not-reachable&season_index=0", status=404)
    get(scope + "/tour/editions/" + enc(event_id)
        + "/matches/foreign-match" + params, status=404)
    get(match_path + "?revision_id=" + enc(revision_id) + "&season_index=2", status=404)



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
    # Click the exact match rather than using the present-time player profile.
    played_link = page.locator(
        'a[href*="/matches/' + enc(source["match_id"]) + '"]'
    ).first
    expect(played_link).to_be_visible()
    played_link.click()
    expect(page.get_by_role("heading", name="Historical match detail")).to_be_visible()
    expect(page.get_by_text("Archived rallies:", exact=False)).to_be_visible()
    expect(page.get_by_text("Rally 1/", exact=False)).to_be_visible()
    page.get_by_role("button", name="Next rally →").click()
    expect(page.get_by_text("Rally 2/", exact=False)).to_be_visible()
    for _ in range(24):
        page.get_by_role("button", name="Next rally →").click()
    expect(page.get_by_text("Rally 26/", exact=False)).to_be_visible()
    assert "revision=" + enc(revision_id) in page.url
    page.screenshot(path=str(artifacts / f"{prefix}saved-tour-match-replay.png"), full_page=True)
    page.get_by_role("link", name="Back to Edition results").click()
    expect(page.get_by_role("heading", name=edition["event_name"])).to_be_visible()
    assert source["scoreline"] in page.locator("#saved-results-main").inner_text()
    page.get_by_role("button", name="Schedule & matches").click()
    expect(page.get_by_text("Authentic Saved Week Simulation Schedule v2.", exact=False)).to_be_visible()
    expect(page.get_by_role("table", name="Saved Match Day order").first).to_be_visible()
    assert source["scoreline"] in page.locator("#saved-schedule-main").inner_text()
    page.get_by_role("button", name="Draw / groups").click()
    expect(page.get_by_role("table", name="Saved draw main")).to_be_visible()
    assert source["player_id"] in page.get_by_role("table", name="Saved draw main").inner_text()
    page.get_by_role("button", name="Qualification").click()
    expect(page.get_by_text("No evidenced matches available.")).to_be_visible()
    page.get_by_role("button", name="Main").click()
    assert source["scoreline"] in page.locator("main").inner_text()
    page.get_by_role("button", name="Entries & participants").click()
    expect(page.get_by_text("Authentic saved Entry Field, version:", exact=False)).to_be_visible()
    expect(page.get_by_text("Direct Main entrants", exact=False)).to_be_visible()
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

    # Read-only result discovery and rally navigation use the very same genuine
    # SQLite-backed tournament, match and persisted rally pages. No route mocks.
    # The published-only list link must preserve this immutable historical scope.
    direct_result = page.get_by_role("link", name="View results").first
    expect(direct_result).to_be_visible()
    direct_href = direct_result.get_attribute("href") or ""
    assert "/tour/calendar/" + enc(event_id) in direct_href, direct_href
    assert all(token in direct_href for token in (
        "branch=" + enc(branch_id), "revision=" + enc(revision_id),
        "season=0", "tab=results", "country=" + enc(edition["host_country"])
    )), direct_href
    direct_result.click()
    expect(page.get_by_role("heading", name=edition["event_name"])).to_be_visible()
    expect(page.get_by_role("button", name="Results")).to_have_attribute(
        "aria-current", "page"
    )
    assert source["scoreline"] in page.locator("#saved-results-main").inner_text()
    direct_match = page.locator(
        'a[href*="/matches/' + enc(source["match_id"]) + '"]'
    ).first
    expect(direct_match).to_be_visible()
    direct_match.click()
    expect(page.get_by_role("heading", name="Historical match detail")).to_be_visible()
    expect(page.get_by_text("Rally 1/", exact=False)).to_be_visible()
    # First/last and a typed jump are genuine archive reads, never simulation.
    page.get_by_role("button", name="Last rally").click()
    expect(page.get_by_text(
        "Rally " + str(archived["total_rallies"]) + "/", exact=False
    )).to_be_visible()
    assert "revision=" + enc(revision_id) in page.url
    assert "rally=" + str(archived["total_rallies"]) in page.url, page.url
    # Refresh the actual browser URL: the same historical rally must survive.
    page.reload()
    expect(page.get_by_text(
        "Rally " + str(archived["total_rallies"]) + "/", exact=False
    )).to_be_visible()
    rally_input = page.get_by_role("spinbutton", name="Archived rally number")
    rally_input.fill(str(archived["total_rallies"] + 1))
    expect(page.get_by_role("button", name="Jump to rally")).to_be_disabled()
    rally_input.fill("26")
    page.get_by_role("button", name="Jump to rally").click()
    expect(page.get_by_text("Rally 26/", exact=False)).to_be_visible()
    assert "rally=26" in page.url, page.url
    page.get_by_role("button", name="First rally").click()
    expect(page.get_by_text("Rally 1/", exact=False)).to_be_visible()
    assert "rally=" not in page.url, page.url
    # Lookup goes to published final placements in the same Saved Revision.
    # It must not silently constrain history to this event's host country/week.
    final_evidence = page.get_by_role(
        "link", name="Find published finals for " + source["player_id"]
    )
    expect(final_evidence).to_be_visible()
    final_evidence.click()
    expect(page.get_by_role("table", name="Saved Tour edition list")).to_be_visible()
    expect(page.get_by_role("link", name=edition["event_name"])).to_be_visible()
    expect(page.get_by_role(
        "searchbox", name="Search champion or finalist player ID"
    )).to_have_value(source["player_id"])
    for token in ("branch=" + enc(branch_id), "revision=" + enc(revision_id),
                  "season=0", "view=list", "publication=published",
                  "playerId=" + enc(source["player_id"])):
        assert token in page.url, (token, page.url)
    assert "country=" not in page.url and "week=" not in page.url, page.url
    page.get_by_text("Published final finishes in displayed editions").click()
    tally = page.get_by_role("table", name="Published final outcome tally")
    expect(tally.get_by_role(
        "link", name="Filter published results for player " + source["player_id"]
    )).to_be_visible()
    # A role filter can narrow to documented winners without a new sporting run.
    page.get_by_role("combobox", name="Player outcome role").select_option("champion")
    expect(page.get_by_role("link", name=edition["event_name"])).to_be_visible()
    page.screenshot(
        path=str(artifacts / f"{prefix}saved-tour-published-final-lookup.png"),
        full_page=True,
    )
    page.goto(base + route)

    # New production Country -> immutable Edition -> real archived Match -> Country
    # navigation, using the SAME SQLite-backed Run, not a mocked browser API.
    # This disposable test Cup has a host in its copied FAX World (GER).
    assert edition["host_country"] == "GER", edition
    country_path = (f"/admin/runs/{enc(run_id)}/world/countries/{enc(edition['host_country'])}"
                    "?tab=tournaments&year=2020&q=retain-me")
    page.goto(base + country_path)
    country_panel = page.get_by_role("region", name="Run World country detail")
    expect(country_panel).to_be_visible()
    editions_table = country_panel.get_by_role(
        "table", name="Country tournament editions 2000/2001")
    expect(editions_table.get_by_role("link", name=edition["event_name"])).to_be_visible()
    editions_table.get_by_role("link", name=edition["event_name"]).click()
    expect(page.get_by_role("heading", name=edition["event_name"])).to_be_visible()
    assert "branch=" + enc(branch_id) in page.url
    assert "revision=" + enc(revision_id) in page.url
    assert "season=0" in page.url
    page.get_by_role("button", name="Results").click()
    exact_match = page.locator('a[href*="/matches/' + enc(source["match_id"]) + '"]').first
    expect(exact_match).to_be_visible()
    exact_match.click()
    expect(page.get_by_role("heading", name="Historical match detail")).to_be_visible()
    expect(page.get_by_text("Archived rallies:", exact=False)).to_be_visible()
    page.get_by_role("link", name="Back to Edition results").click()
    expect(page.get_by_role("heading", name=edition["event_name"])).to_be_visible()
    page.get_by_role("link", name="Back to country tournaments").click()
    expect(country_panel.get_by_role(
        "table", name="Country tournament editions 2000/2001")).to_be_visible()
    assert "tab=tournaments" in page.url and "year=2020" in page.url
    assert "q=retain-me" in page.url
    assert "#country-edition-0-" in page.url
    page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
    expect(country_panel.get_by_role(
        "link", name=edition["event_name"])).to_be_visible()
    page.screenshot(path=str(artifacts / f"{prefix}country-edition-match-return.png"),
                    full_page=True)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    page.goto(base + route)

    # A historical earlier Saved Revision must not inherit a later result.
    history = get(f"/run-containers/{enc(run_id)}/branches/{enc(branch_id)}/saved-revisions")
    older = [r["revision_id"] for r in history["saved_revisions"]
             if r["revision_id"] != revision_id]
    if older:
        oldest = older[0]
        old = get(scope + "/tour/calendar?revision_id=" + enc(oldest) + "&season_index=0")
        assert old["saved_revision_id"] == oldest
        assert not any(e["event_id"] == event_id and e["result_published"] for e in old["editions"])
        # The older immutable snapshot cannot expose a newer champion through
        # a calendar's published-finals lookup, even if deep-linked by player ID.
        prior_route = (f"/admin/runs/{enc(run_id)}/tour/calendar"
                       f"?branch={enc(branch_id)}&revision={enc(oldest)}&season=0"
                       f"&view=list&publication=published&playerId={enc(source['player_id'])}")
        page.goto(base + prior_route)
        expect(page.get_by_role("heading", name="Saved season calendar")).to_be_visible()
        assert "revision=" + enc(oldest) in page.url
        expect(page.get_by_role(
            "link", name=edition["event_name"]
        )).to_have_count(0)
        page.goto(base + route)
    page.screenshot(path=str(artifacts / f"{prefix}saved-tour-calendar.png"), full_page=True)
    proof = {
        "run_id": run_id, "branch_id": branch_id, "saved_revision_id": revision_id,
        "event_id": event_id, "published_matches": len(result["published_result"]["matches"]),
        "season_index": 0, "week_count": 61, "older_saved_revision_without_result": bool(older),
        "filters_and_return": True, "six_tabs": True,
        "real_saved_match_day_slot_count": len(saved_schedule["slots"]),
        "real_saved_match_day_fingerprint": saved_schedule["week_schedule_fingerprint"],
        "replay_total_rallies": archived["total_rallies"],
        "historical_match_replay_revision": archived["saved_revision_id"],
    }
    if expected is not None:
        assert proof == expected, (proof, expected)
    return proof
