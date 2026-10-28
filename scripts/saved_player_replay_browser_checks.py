"""Real browser verification of immutable saved player match replay after tournament Save."""
from __future__ import annotations

from urllib.parse import quote
from playwright.sync_api import expect


def verify_saved_player_replay(page, run_url, artifacts, port, prefix="", expected_branch_id=None):
    base, run_id = run_url.split("/admin/runs/", 1)
    api = f"http://127.0.0.1:{port}"

    def get(path, status=200):
        response = page.request.get(api + path, timeout=30000)
        assert response.status == status, (path, response.status, response.text()[:1300])
        return response.json() if status == 200 else None

    branches = get("/run-branches?run_id=" + quote(run_id, safe=""))["run_branches"]
    if expected_branch_id is None:
        assert len(branches) == 1, branches
        branch = branches[0]
    else:
        candidates = [row for row in branches if row["branch_id"] == expected_branch_id]
        assert len(candidates) == 1, branches
        branch = candidates[0]
    assert branch["run_id"] == run_id
    branch_id = branch["branch_id"]
    event_id = "EVT-2000-W01-browser_cup"
    official = get("/viewer/runs/" + quote(run_id, safe="") +
                   "/tournaments/" + quote(event_id, safe="") + "/result")
    assert official["viewer_branch_id"] == branch_id
    finals = [match for match in official["matches"]
              if match["winner_player_id"] == official["champion_player_id"]
              and match["loser_player_id"] == official["finalist_player_id"]]
    assert len(finals) == 1, official["matches"]
    final = finals[0]
    player_id, match_id = final["winner_player_id"], final["match_id"]
    scope = ("/admin/runs/" + quote(run_id, safe="") + "/branches/" +
             quote(branch_id, safe="") + "/player-profiles/" + quote(player_id, safe=""))
    career = get(scope + "/matches")
    assert career["status"] == "ready" and career["career_played_wins"] >= 2, career
    assert any(row["event_id"] == event_id and row["match_id"] == match_id
               for row in career["matches"]), career
    path = scope + "/matches/" + quote(event_id, safe="") + "/" + quote(match_id, safe="")
    first = get(path + "?offset=0&limit=25")
    assert first["saved_revision_id"] == career["saved_revision_id"] == branch["saved_head_revision_id"]
    assert first["winner_player_id"] == player_id and first["match"]["scoreline"] == final["scoreline"]
    assert first["replay_status"] == "available", ("Saved real match replay missing", first)
    total = first["total_rallies"]
    assert total > 25 and first["has_more"] and len(first["rallies"]) == 25, first
    assert [r["rally_index"] for r in first["rallies"]] == list(range(1, 26))
    next_page = get(path + "?offset=25&limit=25")
    assert next_page["rallies"][0]["rally_index"] == 26
    assert next_page["saved_revision_id"] == first["saved_revision_id"]
    last = get(path + f"?offset={total-1}&limit=25")
    assert len(last["rallies"]) == 1 and not last["has_more"]
    assert last["rallies"][0]["rally_index"] == total and last["rallies"][0]["match_complete"]
    get(path.replace("/branches/" + quote(branch_id, safe="") + "/",
                     "/branches/not-this-branch/"), status=404)
    get(scope + "/matches/unpublished/" + quote(match_id, safe=""), status=404)

    # The same real persisted Saved Revision must contain this player in the
    # canonical inventory; no legacy Run-level roster can satisfy this check.
    roster_scope = ("/admin/runs/" + quote(run_id, safe="") + "/branches/" +
                    quote(branch_id, safe="") + "/saved-players")
    roster = get(roster_scope + "?search=" + quote(player_id, safe=""))
    assert roster["saved_revision_id"] == career["saved_revision_id"], roster
    assert roster["source"] == "selected_branch_saved_revision" and roster["time_context"] == "present"
    assert any(row["player_id"] == player_id for row in roster["players"]), roster

    player_route = "/admin/runs/" + quote(run_id, safe="") + "/people/" + quote(player_id, safe="")
    match_route = player_route + "/matches/" + quote(event_id, safe="") + "/" + quote(match_id, safe="")
    page.goto(base + "/admin/runs/" + quote(run_id, safe="") + "/players")
    if expected_branch_id:
        page.get_by_role("combobox", name="Admin active Branch").select_option(expected_branch_id)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    page.get_by_role("textbox", name="Player search").fill(player_id)
    expect(page.locator('a[href="' + player_route + '"]')).to_have_count(1)
    page.goto(base + player_route)
    if expected_branch_id:
        page.get_by_role("combobox", name="Admin active Branch").select_option(expected_branch_id)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    page.get_by_role("tab", name="Career & results").click()
    expect(page.get_by_role("heading", name="Match career")).to_be_visible()
    # The replay link carries the career return context. Keep the exact match
    # identity check, including the new query, rather than using a broad prefix.
    linked_match_route = (match_route + "?tab=career&replayBranch=" + quote(branch_id, safe="") +
                          "&replayHead=" + quote(first["saved_revision_id"], safe=""))
    link = page.locator('a[href="' + linked_match_route + '"]')
    expect(link).to_have_count(1)
    link.click()
    expect(page.get_by_role("heading", name="Match detail")).to_be_visible()
    expect(page.get_by_role("heading", name="Rally replay")).to_be_visible()
    expect(page.get_by_text(f"Rally 1/{total}", exact=False)).to_be_visible()
    for index in range(1, 26):
        page.get_by_role("button", name="Next rally →").click()
        expect(page.get_by_text(f"Rally {index+1}/{total}", exact=False)).to_be_visible()
    page.screenshot(path=str(artifacts / f"{prefix}07-player-replay-page2.png"), full_page=True)
    # Rally 26 survives a real Chromium refresh, at its exact Saved HEAD.
    page.reload()
    expect(page.get_by_role("heading", name="Match detail")).to_be_visible()
    expect(page.get_by_text(f"Rally 26/{total}", exact=False)).to_be_visible()
    page.get_by_role("button", name="Last rally").click()
    expect(page.get_by_text(f"Rally {total}/{total}", exact=False)).to_be_visible()
    page.get_by_text("Browse archived rallies", exact=False).click()
    expect(page.get_by_role("button", name=f"Rally {total} ·", exact=False)).to_have_attribute("aria-current", "step")
    page.get_by_role("spinbutton", name="Archived rally number").fill("2")
    page.get_by_role("button", name="Jump to rally").click()
    expect(page.get_by_text(f"Rally 2/{total}", exact=False)).to_be_visible()
    page.get_by_role("button", name="First rally").click()
    expect(page.get_by_text(f"Rally 1/{total}", exact=False)).to_be_visible()
    # Test an actual out-of-range HTTP read, then first -> last. Empty data from
    # beyond the end must not be considered an adjacent archived page (#1651).
    page.goto(base + linked_match_route + f"&rally={total+50}")
    expect(page.get_by_text("Requested rally does not exist in this archive.", exact=False)).to_be_visible()
    page.get_by_role("button", name="First valid rally").click()
    expect(page.get_by_text(f"Rally 1/{total}", exact=False)).to_be_visible()
    page.get_by_role("button", name="Last rally").click()
    expect(page.get_by_text(f"Rally {total}/{total}", exact=False)).to_be_visible()
    page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
    expect(page.get_by_text(f"Výměna {total}/{total}", exact=False)).to_be_visible()
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    expect(page.get_by_text(f"Rally {total}/{total}", exact=False)).to_be_visible()
    page.get_by_role("link", name="← Back to player profile").click()
    expect(page).to_have_url(base + player_route + "?tab=career")
    expect(page.get_by_role("tab", name="Career & results")).to_have_attribute("aria-selected", "true")
    expect(page.get_by_role("heading", name="Match career")).to_be_visible()
    # Local career search/filter and source-bound return context, with real
    # production HTTP/SQLite; no mutation or simulation is dispatched.
    page.get_by_role("textbox", name="Search loaded page").fill(match_id)
    page.get_by_role("combobox", name="Filter wins and losses").select_option("win")
    page.get_by_role("combobox", name="Filter played and walkovers").select_option("played")
    filtered_link = page.locator('a[href^="' + linked_match_route + '&careerOutcome=win&careerCompletion=played&careerQ="]')
    expect(filtered_link).to_have_count(1)
    filtered_link.click()
    expect(page.get_by_role("heading", name="Match detail")).to_be_visible()
    page.get_by_role("link", name="← Back to player profile").click()
    expect(page.get_by_role("textbox", name="Search loaded page")).to_have_value(match_id)
    expect(page.get_by_role("combobox", name="Filter wins and losses")).to_have_value("win")
    expect(page.get_by_role("combobox", name="Filter played and walkovers")).to_have_value("played")
    return dict(run_id=run_id, branch_id=branch_id,
                saved_revision_id=first["saved_revision_id"], event_id=event_id,
                player_id=player_id, match_id=match_id, scoreline=final["scoreline"],
                total_rallies=total, first_rally=first["rallies"][0],
                page_boundary_rally=next_page["rallies"][0], last_rally=last["rallies"][0])

def verify_materialized_branch_fork_replay(page, run_url, artifacts, port, source, fork_id=None, prefix=""):
    """Fork completed real tournament, compare scoped saved replay, and inspect UI."""
    from urllib.parse import quote
    from playwright.sync_api import expect
    base, run_id = run_url.split("/admin/runs/", 1)
    api = f"http://127.0.0.1:{port}"

    def get(path, expected=200):
        reply = page.request.get(api + path, timeout=30000)
        assert reply.status == expected, (path, reply.status, reply.text()[:1600])
        return reply.json() if expected == 200 else None

    source_branch = source["branch_id"]
    before = get("/run-branches/" + quote(source_branch, safe=""))
    assert before["run_id"] == run_id
    assert before["saved_head_revision_id"] == source["saved_revision_id"]
    if fork_id is None:
        # Product-Run Saved Revision fork, not the legacy SimulationRun
        # checkpoint fork (this canonical Run has no legacy checkpoint).
        payload = dict(
            source_branch_id=source_branch,
            source_saved_revision_id=source["saved_revision_id"],
            display_name="Independent saved replay timeline",
        )
        reply = page.request.post(
            api + "/run-containers/" + quote(run_id, safe="") + "/branches",
            data=payload, timeout=120000,
        )
        assert reply.status == 201, ("Saved Revision fork rejected canonical source",
                                     reply.status, reply.text()[:1800])
        created = reply.json()
        assert created["run_id"] == run_id
        assert created["forked_from_branch_id"] == source_branch
        assert created["forked_from_saved_revision_id"] == source["saved_revision_id"]
        fork_id = created["branch_id"]
        assert fork_id and fork_id != source_branch
    fork = get("/run-branches/" + quote(fork_id, safe=""))
    assert fork["branch_id"] == fork_id and fork["run_id"] == run_id
    assert fork["saved_head_revision_id"], fork

    def route(branch_id):
        return ("/admin/runs/" + quote(run_id, safe="") + "/branches/" +
                quote(branch_id, safe="") + "/player-profiles/" +
                quote(source["player_id"], safe="") + "/matches/" +
                quote(source["event_id"], safe="") + "/" + quote(source["match_id"], safe=""))

    original = get(route(source_branch) + "?offset=0&limit=25")
    target = get(route(fork_id) + "?offset=0&limit=25")
    assert original["branch_id"] == source_branch
    assert target["branch_id"] == fork_id
    assert target["saved_revision_id"] == fork["saved_head_revision_id"]
    assert target["winner_player_id"] == original["winner_player_id"]
    assert target["match"]["scoreline"] == original["match"]["scoreline"] == source["scoreline"]
    assert target["replay_status"] == original["replay_status"] == "available"
    assert target["total_rallies"] == original["total_rallies"] == source["total_rallies"]
    assert target["rallies"] == original["rallies"]
    boundary = get(route(fork_id) + "?offset=25&limit=25")
    assert boundary["rallies"] == get(route(source_branch) + "?offset=25&limit=25")["rallies"]
    assert boundary["rallies"][0]["rally_index"] == 26
    assert get("/run-branches/" + quote(source_branch, safe=""))["saved_head_revision_id"] == source["saved_revision_id"]
    get(route(fork_id).replace("/branches/" + quote(fork_id, safe="") + "/",
                               "/branches/not-a-real-branch/"), expected=404)

    profile = ("/admin/runs/" + quote(run_id, safe="") +
               "/people/" + quote(source["player_id"], safe=""))
    page.goto(base + profile)
    page.get_by_role("combobox", name="Admin active Branch").select_option(fork_id)
    page.get_by_role("tab", name="Career & results").click()
    expect(page.get_by_role("heading", name="Match career")).to_be_visible()
    match_route = profile + "/matches/" + quote(source["event_id"], safe="") + "/" + quote(source["match_id"], safe="")
    page.locator('a[href="' + match_route + '?tab=career&replayBranch=' +
                 quote(fork_id, safe="") + '&replayHead=' +
                 quote(fork["saved_head_revision_id"], safe="") + '"]').click()
    expect(page.get_by_role("heading", name="Match detail")).to_be_visible()
    expect(page.get_by_text(f'Rally 1/{target["total_rallies"]}', exact=False)).to_be_visible()
    page.screenshot(path=str(artifacts / f"{prefix}08-forked-saved-replay.png"), full_page=True)
    # An original Branch/HEAD bookmark must fail closed after switching to the
    # fork even though the fork contains an identical stored match.
    old_link = (match_route + "?tab=career&replayBranch=" +
                quote(source_branch, safe="") + "&replayHead=" +
                quote(source["saved_revision_id"], safe="") + "&rally=26")
    page.goto(base + old_link)
    expect(page.get_by_text("This link belongs to a different Branch or Saved HEAD.", exact=False)).to_be_visible()
    page.get_by_role("button", name="Open current Saved HEAD").click()
    expect(page.get_by_text(f'Rally 1/{target["total_rallies"]}', exact=False)).to_be_visible()
    return dict(
        source_branch_id=source_branch, target_branch_id=fork_id,
        source_revision_id=original["saved_revision_id"],
        target_revision_id=target["saved_revision_id"],
        scoreline=target["match"]["scoreline"], total_rallies=target["total_rallies"],
        first_rally=target["rallies"][0], boundary_rally=boundary["rallies"][0],
    )
