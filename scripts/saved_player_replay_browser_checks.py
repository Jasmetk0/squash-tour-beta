"""Real browser verification of immutable saved player match replay after tournament Save."""
from __future__ import annotations

from urllib.parse import quote
from playwright.sync_api import expect


def verify_saved_player_replay(page, run_url, artifacts, port, prefix=""):
    base, run_id = run_url.split("/admin/runs/", 1)
    api = f"http://127.0.0.1:{port}"

    def get(path, status=200):
        response = page.request.get(api + path, timeout=30000)
        assert response.status == status, (path, response.status, response.text()[:1300])
        return response.json() if status == 200 else None

    branches = get("/run-branches?run_id=" + quote(run_id, safe=""))["run_branches"]
    assert len(branches) == 1, branches
    branch = branches[0]
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

    player_route = "/admin/runs/" + quote(run_id, safe="") + "/people/" + quote(player_id, safe="")
    match_route = player_route + "/matches/" + quote(event_id, safe="") + "/" + quote(match_id, safe="")
    page.goto(base + player_route)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    expect(page.get_by_role("heading", name="Match career")).to_be_visible()
    link = page.locator('a[href="' + match_route + '"]')
    expect(link).to_have_count(1)
    link.click()
    expect(page.get_by_role("heading", name="Match detail")).to_be_visible()
    expect(page.get_by_role("heading", name="Rally replay")).to_be_visible()
    expect(page.get_by_text(f"Rally 1/{total}", exact=False)).to_be_visible()
    for index in range(1, 26):
        page.get_by_role("button", name="Next rally →").click()
        expect(page.get_by_text(f"Rally {index+1}/{total}", exact=False)).to_be_visible()
    page.screenshot(path=str(artifacts / f"{prefix}07-player-replay-page2.png"), full_page=True)
    page.reload()
    expect(page.get_by_role("heading", name="Match detail")).to_be_visible()
    expect(page.get_by_text(f"Rally 1/{total}", exact=False)).to_be_visible()
    page.get_by_role("link", name="← Back to player profile").click()
    expect(page.get_by_role("heading", name="Match career")).to_be_visible()
    return dict(run_id=run_id, branch_id=branch_id,
                saved_revision_id=first["saved_revision_id"], event_id=event_id,
                player_id=player_id, match_id=match_id, scoreline=final["scoreline"],
                total_rallies=total, first_rally=first["rallies"][0],
                page_boundary_rally=next_page["rallies"][0], last_rally=last["rallies"][0])
