"""Real Chromium acceptance of native calendar MatchEngine -> manual Save/replay.

Called from the existing Pre-alpha Shell browser, using its already-committed
population, original signed Saved revision and real disposable FastAPI/SQLite.
Never inject simulated UI responses or directly re-sign Saved payloads.
"""
from __future__ import annotations

from urllib.parse import quote

from playwright.sync_api import expect


def exercise_calendar_match(
    page, *,
    base_url: str,
    api_url: str,
    artifacts,
    run_id: str,
    original_branch_id: str,
    population_revision_id: str,
    original_clock: dict,
) -> dict:
    def enc(value: str) -> str:
        return quote(value, safe="")

    def api(method: str, path: str, payload=None, expected: int = 200):
        options = {"method": method, "timeout": 120000}
        if payload is not None:
            options["data"] = payload
        response = page.request.fetch(api_url + path, **options)
        assert response.status == expected, (
            method, path, response.status, response.text()[:1800]
        )
        return response.json()

    # The original Branch has later verified Health and a longer W52 horizon.
    # Fork specifically from the earlier, immutable, Saved population to make
    # one independently owned exhibition; the source Branch is not changed.
    source_branches = api("GET", "/run-branches?run_id=" + enc(run_id))
    original = next(
        b for b in source_branches["run_branches"]
        if b["branch_id"] == original_branch_id
    )
    original_head = original["saved_head_revision_id"]
    fork = api(
        "POST", "/run-containers/" + enc(run_id) + "/branches",
        {
            "source_branch_id": original_branch_id,
            "source_saved_revision_id": population_revision_id,
            "display_name": "Native Calendar Match Alternative",
        }, expected=201
    )
    branch_id = fork["branch_id"]
    assert branch_id != original_branch_id
    root = "/admin/runs/" + enc(run_id) + "/branches/" + enc(branch_id)
    match_root = root + "/authoritative-simulation/calendar-standalone-match"
    initial = api("GET", match_root)
    assert initial["match"] is None and not initial["saved"]
    assert initial["run_calendar"]["weeks_per_year"] == original_clock["weeks_per_year"]
    assert initial["run_calendar"]["season_count"] > original_clock["season_count"]
    assert len(initial["player_ids"]) >= 2
    assert initial["saved_head_revision_id"] == fork["saved_head_revision_id"]
    assert initial["initial_world_fingerprint"]

    page.goto(base_url + "/admin/runs/" + enc(run_id) + "/simulate")
    selector = page.get_by_role("combobox", name="Admin active Branch")
    expect(selector).to_be_visible()
    selector.select_option(branch_id)
    expect(page.get_by_role(
        "heading", name="First real Run-calendar match", exact=True
    )).to_be_visible()
    region = page.get_by_role("region", name="Calendar native standalone match")
    # The current implementation renders this semantic section as a section,
    # so locator('[aria-label]') avoids assuming role=mapped region for a bare tag.
    if region.count() == 0:
        region = page.locator('section[aria-label="Calendar native standalone match"]')
    expect(region).to_be_visible()
    play = region.get_by_role("button", name="Play match")
    expect(play).to_be_disabled()
    players = region.get_by_role("combobox")
    expect(players).to_have_count(2)
    selected_a = players.nth(0).input_value()
    selected_b = players.nth(1).input_value()
    assert selected_a != selected_b and {selected_a, selected_b}.issubset(initial["player_ids"])
    region.get_by_label("Audit reason").fill("Chromium verified real BO5 exhibition")
    region.get_by_label("Confirm actual match execution.").check()
    expect(play).to_be_enabled()
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith("/calendar-standalone-match/simulate")
    ) as played_response:
        play.click()
    played_http = played_response.value
    assert played_http.status == 201, played_http.text()[:1200]
    played = played_http.json()
    assert played["match"]["result"]["winner_player_id"] in {selected_a, selected_b}
    assert played["match"]["source_initial_world_fingerprint"] == initial["initial_world_fingerprint"]
    assert len(played["match"]["result"]["rally_log"]["events"]) > 20
    expect(region.get_by_text("Unsaved result", exact=False)).to_be_visible()

    with page.expect_response(
        lambda r: r.request.method == "GET"
        and r.url.endswith("/calendar-opening-exhibition/replay")
    ) as replay_response:
        region.get_by_role("button", name="Verify exact replay").click()
    assert replay_response.value.status == 200, replay_response.value.text()[:1200]
    result = replay_response.value.json()
    assert result["exact_replay"]
    assert result["result"] == played["match"]["result"]
    expect(region.get_by_text("Verified replay", exact=False)).to_be_visible()
    expect(region.get_by_role("button", name="Save revision")).to_have_count(0)
    region.get_by_role("button", name="Review manual Save").click()
    save = region.get_by_role("button", name="Save revision")
    expect(save).to_be_disabled()
    region.get_by_label("Confirm new Saved Revision.").check()
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith("/calendar-standalone-match/save")
    ) as saved_response:
        save.click()
    assert saved_response.value.status == 201, saved_response.value.text()[:1200]
    saved = saved_response.value.json()
    new_revision = saved["saved_revision"]["revision_id"]
    assert new_revision != initial["saved_head_revision_id"]
    assert api("GET", match_root)["saved"] is True
    after_source = api("GET", "/run-branches?run_id=" + enc(run_id))
    assert next(
        b for b in after_source["run_branches"]
        if b["branch_id"] == original_branch_id
    )["saved_head_revision_id"] == original_head
    old_population = api(
        "GET", "/run-containers/" + enc(run_id) + "/branches/"
        + enc(original_branch_id) + "/saved-revisions/" + enc(population_revision_id)
    )
    assert old_population["revision_id"] == population_revision_id
    assert "calendar_standalone_match" not in old_population["payload"]["content"]

    page.reload()
    expect(page.get_by_role(
        "heading", name="First real Run-calendar match", exact=True
    )).to_be_visible()
    region = page.locator('section[aria-label="Calendar native standalone match"]')
    expect(region.get_by_text("Status: Saved", exact=False)).to_be_visible()
    assert api("GET", match_root)["match_fingerprint"] == played["fingerprint"]
    assert api("GET", match_root + "/calendar-opening-exhibition/replay")["exact_replay"]
    page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
    expect(page.get_by_role(
        "heading", name="První skutečný zápas podle Run kalendáře"
    )).to_be_visible()
    expect(region.get_by_role("button", name="Ověřit přesný replay")).to_be_visible()
    page.screenshot(path=str(artifacts / "16-calendar-native-real-match-saved.png"), full_page=True)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    return {
        "actual_match_engine": True,
        "manual_save": True,
        "cold_browser_reload": True,
        "deterministic_replay": True,
        "cs_en_browser": True,
        "original_branch_head_intact": True,
        "forked_from_population_revision": population_revision_id,
        "new_saved_revision": new_revision,
        "run_id": run_id,
        "branch_id": branch_id,
        "weeks_per_year": original_clock["weeks_per_year"],
        "season_count": initial["run_calendar"]["season_count"],
        "rally_count": result["rally_count"],
    }
