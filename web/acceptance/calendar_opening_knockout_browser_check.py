"""Real Chromium four-player W52 opening-week MatchEngine and immutable Save.

Uses the same disposable FastAPI/SQLite shell as the existing exhibition
acceptance, then extends the Run with all Saved sporting Branches intact.
"""
from __future__ import annotations

import json
from urllib.parse import quote

from playwright.sync_api import expect


def exercise_calendar_knockout(page, *, base_url, api_url, artifacts,
                               run_id, original_branch_id,
                               population_revision_id, original_clock) -> dict:
    def enc(value):
        return quote(value, safe="")

    def api(method, path, payload=None, expected=200):
        params = {"method": method, "timeout": 120000}
        if payload is not None:
            params["data"] = payload
        r = page.request.fetch(api_url + path, **params)
        assert r.status == expected, (path, r.status, r.text()[:1600])
        return r.json()

    before = api("GET", "/run-branches?run_id=" + enc(run_id))
    original = next(b for b in before["run_branches"]
                    if b["branch_id"] == original_branch_id)
    head_before = original["saved_head_revision_id"]
    fork = api("POST", "/run-containers/" + enc(run_id) + "/branches", {
        "source_branch_id": original_branch_id,
        "source_saved_revision_id": population_revision_id,
        "display_name": "Native Calendar Four Player Knockout",
    }, expected=201)
    branch_id = fork["branch_id"]
    root = ("/admin/runs/" + enc(run_id) + "/branches/"
            + enc(branch_id) + "/authoritative-simulation/calendar-opening-knockout")
    initial = api("GET", root)
    assert initial["knockout"] is None and initial["saved"] is False
    assert initial["run_calendar"]["weeks_per_year"] == original_clock["weeks_per_year"]
    assert len(initial["player_ids"]) >= 4

    page.goto(base_url + "/admin/runs/" + enc(run_id) + "/simulate")
    selector = page.get_by_role("combobox", name="Admin active Branch")
    expect(selector).to_be_visible()
    selector.select_option(branch_id)
    panel = page.locator('section[aria-label="Calendar native four-player knockout"]')
    expect(panel).to_be_visible()
    expect(page.get_by_role("heading", name="Real four-player Run-calendar knockout")).to_be_visible()
    play = panel.get_by_role("button", name="Play knockout")
    expect(play).to_be_disabled()
    entrants = panel.get_by_role("combobox")
    expect(entrants).to_have_count(4)
    ids = [entrants.nth(i).input_value() for i in range(4)]
    assert len(set(ids)) == 4 and set(ids).issubset(initial["player_ids"])
    panel.get_by_label("Audit reason").fill("Chromium real semifinals and winner-fed final")
    panel.get_by_label("Confirm playing all three matches.").check()
    expect(play).to_be_enabled()
    with page.expect_response(lambda r:
            r.request.method == "POST" and r.url.endswith("/calendar-opening-knockout/simulate")) as response:
        play.click()
    assert response.value.status == 201, response.value.text()[:1200]
    played = response.value.json()
    assert played['knockout']['schema_version'] == 'calendar_opening_knockout.v2'
    sporting = played['knockout']['sporting']
    assert len(sporting['effects']) == 6
    after_semis = {p['player_id']: p for p in sporting['after_semifinals']}
    expect(panel.get_by_role('table', name='Knockout player state table')).to_be_visible()
    expect(panel.get_by_role('table', name='Knockout player state table').get_by_role('row')).to_have_count(13)
    matches = played["knockout"]["matches"]
    for ctx in (matches[2]['input_context']['player_a'], matches[2]['input_context']['player_b']):
        pid = ctx['player']['player_id']
        assert after_semis[pid]['long_term_fatigue'] > 0
        assert ctx['fatigue_modifier'] == round(-after_semis[pid]['long_term_fatigue'] / 300, 6)
    assert len(matches) == 3 and [m["slot"] for m in matches] == [1, 1, 2]
    assert matches[2]["result"]["player_a_id"] == matches[0]["result"]["winner_player_id"]
    assert matches[2]["result"]["player_b_id"] == matches[1]["result"]["winner_player_id"]
    expect(panel.get_by_text("Unsaved", exact=False)).to_be_visible()

    with page.expect_response(lambda r:
            r.request.method == "GET" and r.url.endswith("/calendar-opening-knockout/replay")) as response:
        panel.get_by_role("button", name="Verify all match replays").click()
    assert response.value.status == 200, response.value.text()[:1200]
    assert response.value.json()["exact_replay"]
    expect(panel.get_by_text("Verified", exact=False)).to_be_visible()
    panel.get_by_role("button", name="Review Save").click()
    save = panel.get_by_role("button", name="Save knockout")
    expect(save).to_be_disabled()
    panel.get_by_label("Confirm new immutable Saved Revision.").check()
    with page.expect_response(lambda r:
            r.request.method == "POST" and r.url.endswith("/calendar-opening-knockout/save")) as response:
        save.click()
    assert response.value.status == 201, response.value.text()[:1200]
    revision = response.value.json()["saved_revision"]["revision_id"]
    assert revision != initial["saved_head_revision_id"]
    assert api("GET", root)["saved"] is True
    assert api("GET", root)['knockout']['sporting'] == sporting

    page.reload()
    selector = page.get_by_role("combobox", name="Admin active Branch")
    expect(selector).to_be_visible()
    selector.select_option(branch_id)
    panel = page.locator('section[aria-label="Calendar native four-player knockout"]')
    expect(panel.get_by_text("Status: Saved", exact=False)).to_be_visible()
    expect(panel.get_by_role('table', name='Knockout player state table')).to_be_visible()
    assert api("GET", root + "/calendar-opening-knockout/replay")["exact_replay"]
    page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
    expect(page.get_by_role(
        "heading", name="Skutečný čtyřčlenný pavouk podle Run kalendáře"
    )).to_be_visible()
    expect(panel.get_by_role("button", name="Ověřit replay všech zápasů")).to_be_visible()
    expect(panel.get_by_role('columnheader', name='Dlouhodobá únava', exact=True)).to_be_visible()
    page.screenshot(path=str(artifacts / "17-calendar-real-knockout-saved.png"), full_page=True)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    # A second, separately confirmed sporting Save attaches prepared point
    # evidence to the exact earlier Signed bracket; no fabricated winners.
    awards = panel.locator('section[aria-label="Calendar knockout award preparation"]')
    expect(awards).to_be_visible()
    awards.get_by_label("Point policy audit reason").fill(
        "Explicit operator-reviewed policy for Saved MatchEngine scores"
    )
    with page.expect_response(lambda r:
            r.request.method == "POST" and r.url.endswith(
                "/calendar-opening-knockout/awards/review"
            )) as review_response:
        awards.get_by_role("button", name="Review prepared point awards").click()
    assert review_response.value.status == 200, review_response.value.text()[:1200]
    reviewed = review_response.value.json()
    assert reviewed["publication_status"] == "prepared_not_official"
    assert sorted(a["main_points"] for a in reviewed["awards"]) == [30, 30, 60, 100]
    awards.get_by_label("Confirm preparing points without Official publication.").check()
    with page.expect_response(lambda r:
            r.request.method == "POST" and r.url.endswith(
                "/calendar-opening-knockout/awards/apply"
            )) as apply_response:
        awards.get_by_role("button", name="Apply prepared awards").click()
    assert apply_response.value.status == 201, apply_response.value.text()[:1200]
    prepared = apply_response.value.json()
    assert prepared["prepared"]["knockout"] == played["knockout"]
    # Confirm completion of the UI's own Signed-HEAD inspection before
    # issuing another API request. Concurrent heavyweight 1000-player
    # inspections are not an acceptance requirement for this operation.
    expect(panel.get_by_text("Prepared points (not Official)")).to_be_visible(
        timeout=120000
    )
    expect(panel.get_by_text("Status: Unsaved", exact=False)).to_be_visible()
    now = api("GET", root)
    assert now["saved"] is False
    assert now["prepared_points"]["publication_status"] == "prepared_not_official"
    assert now["knockout_fingerprint"] == prepared["fingerprint"]
    panel.get_by_role("button", name="Review Save").click()
    panel.get_by_label("Confirm new immutable Saved Revision.").check()
    with page.expect_response(lambda r:
            r.request.method == "POST" and r.url.endswith(
                "/calendar-opening-knockout/save"
            )) as second_save:
        panel.get_by_role("button", name="Save knockout").click()
    assert second_save.value.status == 201, second_save.value.text()[:1200]
    scored_revision = second_save.value.json()["saved_revision"]["revision_id"]
    assert scored_revision != revision
    assert api("GET", root)["saved"] is True
    assert api("GET", root)['knockout']['sporting'] == sporting
    assert api("GET", root + "/calendar-opening-knockout/replay")["exact_replay"]
    page.reload()
    selector = page.get_by_role("combobox", name="Admin active Branch")
    expect(selector).to_be_visible()
    selector.select_option(branch_id)
    panel = page.locator('section[aria-label="Calendar native four-player knockout"]')
    expect(panel.get_by_text("Prepared points (not Official)")).to_be_visible()
    rankings = panel.locator('section[aria-label="Signed calendar knockout as-of standings"]')
    expect(rankings).to_be_visible()
    expect(rankings.get_by_role("table", name="Signed tournament standings table")).to_be_visible(
        timeout=120000
    )
    table = rankings.get_by_role("table", name="Signed tournament standings table")
    expect(table.locator("tbody tr")).to_have_count(4)
    points = [int(table.locator("tbody tr").nth(i).locator("td").nth(3).inner_text())
              for i in range(4)]
    assert points == [100, 60, 30, 30], points
    # W52 point validity: Week 2 of Season 2 is the first expired week.
    rankings.get_by_role("button", name="View first expired week").click()
    source_context = "|".join((run_id, branch_id, scored_revision))
    saved_period = page.evaluate(
        "(scope) => window.sessionStorage.getItem('squash-calendar-asof:' + scope)",
        source_context,
    )
    assert saved_period is not None and json.loads(saved_period) == {
        "season": 1, "week": 2,
    }, "as-of Admin state must bind the exact Signed Saved HEAD"
    # The local selection never navigates the Product Run or edits sporting
    # authority. Per-tab storage restores the same period after reload.
    expect(rankings.get_by_role("spinbutton", name="Standings season number")).to_have_value("2")
    expect(rankings.get_by_text("Points have expired.", exact=False)).to_be_visible(timeout=120000)
    # The filter must survive a full browser reload and Branch re-selection,
    # not merely a transient React rerender.
    page.reload()
    page.get_by_role("combobox", name="Admin active Branch").select_option(branch_id)
    expect(rankings.get_by_role("spinbutton", name="Standings season number")).to_have_value("2", timeout=120000)
    expect(rankings.get_by_text("Points have expired.", exact=False)).to_be_visible(timeout=120000)
    expired = [int(table.locator("tbody tr").nth(i).locator("td").nth(3).inner_text())
               for i in range(4)]
    assert expired == [0, 0, 0, 0], expired
    rankings.get_by_role("button", name="View opening week").click()
    expect(rankings.get_by_role("spinbutton", name="Standings season number")).to_have_value("1")
    expect(rankings.get_by_text("Points are still within their validity period.", exact=False)).to_be_visible(timeout=120000)
    # Verify the general manual form too, not only the boundary shortcut.
    rankings.get_by_role("spinbutton", name="Standings season number").fill("2")
    rankings.get_by_role("spinbutton", name="Standings week number").fill("2")
    rankings.get_by_role("button", name="Show selected week").click()
    expect(rankings.get_by_role("spinbutton", name="Standings season number")).to_have_value("2")
    expect(rankings.get_by_text("Points have expired.", exact=False)).to_be_visible(timeout=120000)
    rankings.get_by_role("button", name="View opening week").click()
    expect(rankings.get_by_text("Points are still within their validity period.", exact=False)).to_be_visible(timeout=120000)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
    expect(panel.get_by_text("Připravené body (neoficiální)")).to_be_visible()
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    after = api("GET", "/run-branches?run_id=" + enc(run_id))
    assert next(b for b in after["run_branches"]
                if b["branch_id"] == original_branch_id)["saved_head_revision_id"] == head_before
    # The same native sporting evidence must participate in the normal
    # all-Branch extension flow; it must not be misclassified as unsaved.
    old_score = api("GET", "/run-containers/" + enc(run_id) + "/branches/"
                    + enc(branch_id) + "/saved-revisions/" + enc(scored_revision))
    page.goto(base_url + "/admin/runs/" + enc(run_id))
    page.get_by_role("combobox", name="Admin active Branch").select_option(branch_id)
    extension = page.locator('section[aria-label="Run calendar extension inspection"]')
    new_count = initial["run_calendar"]["season_count"] + 1
    extension.get_by_label("New total season count", exact=True).fill(str(new_count))
    with page.expect_response(lambda r: r.request.method == "GET"
                              and "/calendar/extension-review?" in r.url,
                              timeout=120000) as response:
        extension.get_by_role("button", name="Review all Branches", exact=True).click()
    assert response.value.status == 200, response.value.text()[:1200]
    review = response.value.json()
    assert review["can_save"], review
    assert review["branch_count"] == len(after["run_branches"])
    save_extension = extension.get_by_role("button", name="Confirm & Save entire Run", exact=True)
    expect(save_extension).to_be_disabled()
    extension.get_by_label(
        "I confirm extension across every listed Branch and creation of new Saved Revisions."
    ).check()
    with page.expect_response(lambda r: r.request.method == "POST"
                              and r.url.endswith("/calendar/extension-save"),
                              timeout=120000) as response:
        save_extension.click()
    assert response.value.status == 200, response.value.text()[:1200]
    receipt = response.value.json()
    assert receipt["current_calendar"]["season_count"] == new_count
    assert not receipt["simulation_started"] and not receipt["sporting_execution_unlocked"]
    extended_head = next(b["saved_revision_id"] for b in receipt["branches"]
                         if b["branch_id"] == branch_id)
    old_after = api("GET", "/run-containers/" + enc(run_id) + "/branches/"
                    + enc(branch_id) + "/saved-revisions/" + enc(scored_revision))
    for field in ("revision_id", "content_hash", "payload", "change_summary"):
        assert old_after[field] == old_score[field]
    current = api("GET", root)
    assert current["saved"] and current["knockout_fingerprint"] == prepared["fingerprint"]
    assert current["run_calendar"]["season_count"] == new_count
    assert current["knockout"] == played["knockout"]
    assert api("GET", root + "/calendar-opening-knockout/replay")["exact_replay"]
    page.goto(base_url + "/admin/runs/" + enc(run_id) + "/simulate")
    page.get_by_role("combobox", name="Admin active Branch").select_option(branch_id)
    rankings = page.locator('section[aria-label="Signed calendar knockout as-of standings"]')
    expect(rankings.get_by_role("table", name="Signed tournament standings table")).to_be_visible(
        timeout=120000
    )
    rankings.get_by_role("button", name="View first expired week").click()
    expect(rankings.get_by_text("Points have expired.", exact=False)).to_be_visible(timeout=120000)
    page.reload()
    page.get_by_role("combobox", name="Admin active Branch").select_option(branch_id)
    expect(rankings.get_by_text("Points have expired.", exact=False)).to_be_visible(timeout=120000)
    assert api("GET", root)["saved_head_revision_id"] == extended_head
    page.screenshot(path=str(artifacts / "18-scored-knockout-horizon-extended.png"), full_page=True)
    return {
        "actual_match_engine_matches": 3,
        "same_pre_slot_semifinals": True,
        "winner_fed_final": True,
        "post_semifinal_state_consumed_by_final": True,
        "six_evidenced_player_effects": True,
        "saved_player_checkpoints_cs_en": True,
        "saved_revision": revision,
        "cold_browser_reload": True,
        "exact_three_match_replay": True,
        "cs_en_browser": True,
        "source_branch_unchanged_before_extension": True,
        "reviewed_prepared_points": True,
        "prepared_awards_manual_second_save": scored_revision,
        "points_unpublished": True,
        "signed_as_of_scoreboard": True,
        "exact_calendar_expiry": True,
        "all_branch_extension_after_saved_sport": True,
        "scored_history_byte_identical_after_extension": True,
        "extended_scored_saved_head": extended_head,
        "extended_replay_and_browser_reload": True,
    }
