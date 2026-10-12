"""Positive Country Records browser evidence from ONE real Saved Tournament Run.

This helper reuses the existing real 64-player / 3-match Chromium + production
FastAPI + SQLite acceptance. No fake API data, generated fixtures or new Run writes.
"""
from __future__ import annotations

from urllib.parse import quote

from playwright.sync_api import expect


def verify_country_saved_records(
    page, run_url: str, artifacts, port: int, source: dict,
    *, prefix: str = "", expected: dict | None = None,
) -> dict:
    base, run_id = run_url.split("/admin/runs/", 1)
    api = f"http://127.0.0.1:{port}"
    branch_id, head_id = source["branch_id"], source["saved_revision_id"]
    event_id = source["event_id"]
    enc = lambda value: quote(str(value), safe="")

    def get(path: str, status: int = 200):
        response = page.request.get(api + path, timeout=40000)
        assert response.status == status, (path, response.status, response.text()[:1700])
        return response.json() if status == 200 else None

    branch = get("/run-branches/" + enc(branch_id))
    assert branch["saved_head_revision_id"] == head_id, "World read must use immutable source HEAD"
    official = get("/viewer/runs/" + enc(run_id) + "/tournaments/" + enc(event_id) + "/result")
    assert official["viewer_branch_id"] == branch_id
    participants = sorted({
        pid for match in official["matches"]
        for pid in (match["winner_player_id"], match["loser_player_id"]) if pid is not None
    })
    assert len(participants) == 4, participants
    identities = get(
        "/admin/runs/" + enc(run_id) + "/branches/" + enc(branch_id) +
        "/home-player-identities?player_ids=" + enc(",".join(participants))
    )
    assert identities["status"] == "ready" and not identities["unresolved_ids"], identities
    nationality = {p["player_id"]: p["country_code"] for p in identities["players"]}
    assert set(nationality) == set(participants)

    # Select the real finalist's nationality: finalist won the semi and lost
    # the final. A chosen country must exist in the immutable copied World.
    code = nationality[official["finalist_player_id"]]
    saved_world = get("/admin/runs/" + enc(run_id) + "/branches/" + enc(branch_id) + "/packages")
    countries = {
        entity["payload"]["code"]
        for entity in (saved_world["state"] or {})["entities"]
        if entity["entity_kind"] == "world.country.v1"
    }
    assert code in countries, (code, countries)

    base_scope = ("/admin/runs/" + enc(run_id) + "/branches/" + enc(branch_id))
    record_route = base_scope + "/country-match-records/" + enc(code)
    title_route = base_scope + "/country-records/" + enc(code)
    matches = get(record_route + "?revision_id=" + enc(head_id) + "&offset=0&limit=25")
    titles = get(title_route + "?revision_id=" + enc(head_id))
    assert matches["saved_revision_id"] == titles["saved_revision_id"] == head_id
    assert matches["source"] == titles["source"] == "reachable_saved_revision"
    assert matches["branch_id"] == titles["branch_id"] == branch_id
    assert matches["country_code"] == titles["country_code"] == code
    assert matches["revision_branch_id"] == titles["revision_branch_id"] == branch_id
    assert matches["published_event_count"] == titles["published_result_count"] == 1
    assert matches["calendar_status"] == titles["calendar_status"] == "ready"

    actual = {
        (event_id, match["match_id"]): match
        for match in official["matches"] if match["loser_player_id"] is not None
    }
    assert len(actual) == 3, "Expected actual semi-finals and final, not BYEs"
    relevant = {
        (event_id, m["match_id"]): m for m in actual.values()
        if code in (nationality[m["winner_player_id"]], nationality[m["loser_player_id"]])
    }
    saved_rows = {(m["event_id"], m["match_id"]): m for m in matches["matches"]}
    assert len(saved_rows) == len(relevant) == matches["country_match_count"] == matches["filtered_match_count"]
    assert not matches["has_more"]
    for key, match in relevant.items():
        saved = saved_rows[key]
        assert saved["winner_player_id"] == match["winner_player_id"]
        assert saved["loser_player_id"] == match["loser_player_id"]
        assert saved["scoreline"] == match["scoreline"]
        assert saved["winner_country"] == nationality[match["winner_player_id"]]
        assert saved["loser_country"] == nationality[match["loser_player_id"]]
        assert saved["completion"] == "played"
    wins = sum(nationality[m["winner_player_id"]] == code for m in relevant.values())
    losses = sum(nationality[m["loser_player_id"]] == code for m in relevant.values())
    assert matches["country_played_wins"] == wins >= 1, matches
    assert matches["country_played_losses"] == losses >= 1, matches
    assert matches["country_walkover_wins"] == matches["country_walkover_losses"] == 0
    assert matches["total_played_matches"] == 3 and matches["total_walkovers"] == 0
    assert matches["available_seasons"] == [0]
    assert titles["country_titles"] == int(nationality[official["champion_player_id"]] == code)
    assert titles["country_finalists"] == 1

    # Server filtering must run on all verified rows BEFORE paging.
    def filtered(**kw):
        args = {"revision_id": head_id, "offset": 0, "limit": 25, **kw}
        query = "&".join(enc(k) + "=" + enc(v) for k, v in args.items())
        return get(record_route + "?" + query)

    win_data = filtered(season_index=0, result_kind="played", outcome="win")
    loss_data = filtered(season_index=0, result_kind="played", outcome="loss")
    no_next_season = filtered(season_index=1)
    no_walkovers = filtered(result_kind="walkover")
    assert win_data["filtered_match_count"] == wins
    assert loss_data["filtered_match_count"] == losses
    assert no_next_season["filtered_match_count"] == 0 and not no_next_season["matches"]
    assert no_walkovers["filtered_match_count"] == 0 and not no_walkovers["matches"]
    assert all(m["winner_country"] == code for m in win_data["matches"])
    assert all(m["loser_country"] == code for m in loss_data["matches"])
    assert all(m["season"] == "2000/2001" for m in win_data["matches"])
    get(record_route + "?revision_id=" + enc(head_id) + "&season_index=50", 422)
    get(record_route + "?revision_id=" + enc(head_id) + "&result_kind=bye", 422)
    get(record_route + "?revision_id=" + enc(head_id) + "&outcome=draw", 422)
    get(record_route + "?revision_id=no-such-revision", 404)

    # Use the repository's REAL saved pre-tournament World revision, never a
    # synthetic snapshot or fake older result. Check immutable results there.
    history_root = (
        "/run-containers/" + enc(run_id) + "/branches/" + enc(branch_id) +
        "/saved-revisions"
    )
    history = get(history_root + "?limit=200")
    assert history["saved_head_revision_id"] == head_id
    historical_id = None
    for item in history["saved_revisions"]:
        candidate = item["revision_id"]
        if candidate == head_id:
            continue
        details = get(history_root + "/" + enc(candidate))
        component = details["payload"].get("content", {}).get("run_package_state")
        if not isinstance(component, dict):
            continue
        entities = component.get("state", {}).get("entities", [])
        if not any(e.get("entity_kind") == "world.country.v1" and
                   e.get("payload", {}).get("code") == code for e in entities):
            continue
        candidate_records = get(record_route + "?revision_id=" + enc(candidate))
        if candidate_records["published_event_count"] == 0:
            historical_id = candidate
            assert candidate_records["country_match_count"] == 0
            assert candidate_records["matches"] == []
            assert get(title_route + "?revision_id=" + enc(candidate))["country_titles"] == 0
            break
    assert historical_id, "Need a real pre-tournament Saved World ancestor"

    # Open the actual Admin country route, NOT just the API response.
    path = run_url + "/world/countries/" + enc(code) + "?tab=records&year=2000"
    page.goto(path)
    branch_control = page.get_by_role("combobox", name="Admin active Branch")
    expect(branch_control).to_be_visible()
    if branch_control.input_value() != branch_id:
        branch_control.select_option(branch_id)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    country = page.get_by_role("region", name="Run World country detail")
    expect(country).to_be_visible()
    assert code in country.inner_text()
    summary = page.get_by_label("Country published records")
    expect(summary.get_by_label("Country verified record totals")).to_be_visible()
    match_panel = page.get_by_label("Country saved match records")
    table = match_panel.get_by_role("table", name="Country canonical saved matches")
    expect(table.locator("tbody tr")).to_have_count(len(relevant))
    for item in saved_rows.values():
        assert item["scoreline"] in table.inner_text()
        assert item["event_name"] in table.inner_text()
    assert head_id in match_panel.inner_text()

    season = match_panel.get_by_role("combobox", name="Country match season")
    season.select_option("0")
    expect(table.locator("tbody tr")).to_have_count(len(relevant))
    result_kind = match_panel.get_by_role("combobox", name="Country match completion")
    outcome = match_panel.get_by_role("combobox", name="Country match outcome")
    outcome.select_option("win")
    expect(table.locator("tbody tr")).to_have_count(wins)
    outcome.select_option("loss")
    expect(table.locator("tbody tr")).to_have_count(losses)
    outcome.select_option("all")
    result_kind.select_option("walkover")
    expect(match_panel.get_by_text("No saved matches match these filters in the selected revision.")).to_be_visible()
    result_kind.select_option("played")
    expect(table.locator("tbody tr")).to_have_count(len(relevant))
    expect(match_panel.get_by_role("button", name="Next →")).to_be_disabled()
    page.screenshot(path=str(artifacts / f"{prefix}09-country-published-matches.png"), full_page=True)

    # A selected historical World revision must show empty VERIFIABLE records,
    # without borrowing the current saved results or player-profile links.
    page.goto(path + "&revision=" + enc(historical_id))
    old_panel = page.get_by_label("Country saved match records")
    expect(old_panel.get_by_text("No saved matches match these filters in the selected revision.")).to_be_visible()
    assert historical_id in old_panel.inner_text()
    expect(old_panel.get_by_role("table", name="Country canonical saved matches")).to_have_count(0)
    assert old_panel.get_by_role("link").count() == 0, "Historical matches must not link to present profiles"
    assert get("/run-branches/" + enc(branch_id))["saved_head_revision_id"] == head_id
    page.screenshot(path=str(artifacts / f"{prefix}10-country-historical-before-results.png"), full_page=True)

    proof = {
        "run_id": run_id, "branch_id": branch_id, "saved_revision_id": head_id,
        "country_code": code, "historical_revision_id": historical_id,
        "country_played_wins": wins, "country_played_losses": losses,
        "published_event_count": matches["published_event_count"],
        "match_scorelines": sorted((m["match_id"], m["scoreline"]) for m in saved_rows.values()),
        "historical_results_empty": True,
        "saved_head_unchanged": True,
    }
    if expected is not None:
        assert proof == expected, ("Country Saved evidence changed after restart", proof, expected)
    return proof
