"""Two overlapping actual global-slot tournaments on EITHER side of a signed season boundary.

This is a live production HTTP/SQLite, two Signed Seasons integration test
with twelve genuine MatchEngine rally logs. Distinct from a single cross-season
Edition and two same-season overlapping weeks. No direct DB/JSON writes and
no shortcut for genuine entry validation or full FAX release acceptance.
"""
from collections import Counter

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark=pytest.mark.smoke

FIRST_WEEK=("s1-final-alpha","s1-final-beta")
SECOND_WEEK=("s2-opening-gamma","s2-opening-delta")
EDITION_FACTORS={FIRST_WEEK[0]:1,FIRST_WEEK[1]:2,SECOND_WEEK[0]:3,SECOND_WEEK[1]:4}


def _schedule():
    return tuple(
        (eid, 0 if i < 2 else 1, 4 if i < 2 else 1,
         0, 3 if i < 2 else 4, i + 1)
        for i,eid in enumerate((*FIRST_WEEK,*SECOND_WEEK))
    )


@pytest.mark.pr_critical
def test_cross_season_overlaps_have_unambiguous_source_dates_and_distinct_editions():
    rows=_schedule()
    assert len(rows)==4
    assert len({row[0] for row in rows})==4
    assert [(s,w) for _,s,w,_,_,_ in rows]==[(0,4),(0,4),(1,1),(1,1)]
    assert [(s,w) for _,_,_,s,w,_ in rows]==[(0,3),(0,3),(0,4),(0,4)]
    assert set(EDITION_FACTORS)=={row[0] for row in rows}


def _plan(server,edition_ids):
    """Four distinct reviewed/Saved authoritatively configured Edition plans."""
    source={entry[0]:entry for entry in _schedule()}
    for eid in edition_ids:
        _,season,week,announced_season,announced_week,factor=source[eid]
        view=inspect(server)
        start=view["state"]["week"]
        assert (start["season_index"],start["week"]) in {(0,2),(0,3)}
        data={
            "schema_version":"calendar_tournament_edition.v2",
            "simulation_seed":900+factor,
            "edition_id":eid,
            "name":eid,
            "week":{**start,"season_index":season,"week":week},
            "announcement_week":{**start,"season_index":announced_season,"week":announced_week},
            "start_slot":1,"main_entrant_count":4,"ranked":True,
            "validity_weeks":4,
            "point_table":{"champion":100*factor,"finalist":60*factor,
                           "semifinal":30*factor},
        }
        result,_=execute(server,command(view,"create-edition",name=eid+":plan",data=data))
        assert result["manual_save_required"]
        saved=save_tour(server)
        assert inspect(server)["saved_head_revision_id"]==saved["revision_id"]


def _advance(server,action,name,season,week):
    result,request=execute(server,command(inspect(server),action,name=name))
    assert result["manual_save_required"]
    draft=inspect(server)
    assert not draft["saved"]
    assert (draft["state"]["week"]["season_index"],draft["state"]["week"]["week"])==(season,week)
    saved=save_tour(server)
    assert inspect(server)["saved_head_revision_id"]==saved["revision_id"]
    return result,request,saved


def _signed_season(server,season):
    code,data=_request("GET",tour_url(server)+f"/seasons/{season}")
    assert code==200,data
    assert data["saved_head_revision_id"]==inspect(server)["saved_head_revision_id"]
    return data["selected"]


def _records(server):
    code,data=_request("GET",tour_url(server)+"/records")
    assert code==200,data
    assert data["saved_head_revision_id"]==inspect(server)["saved_head_revision_id"]
    return data


def _prepare_fields(server, edition_ids):
    """One group of four real players per overlapping slot, no collision."""
    players = [p["player_id"] for p in inspect(server)["players"]]
    assert len(players) == len(set(players)) == 8
    for index, edition_id in enumerate(edition_ids):
        ids = players[index * 4:(index + 1) * 4]
        assert len(ids) == 4
        result, _ = execute(
            server, command(inspect(server), "submit",
                name=edition_id + ":submit", edition_id=edition_id,
                data={"player_ids": ids}),
        )
        assert result["manual_save_required"]
        for action in ("approve", "draw"):
            execute(server, command(
                inspect(server), action,
                name=edition_id + ":" + action, edition_id=edition_id,
            ))
        assert not inspect(server)["saved"]
        save_tour(server)
    ready = inspect(server)
    assert ready["next_slot"] is not None
    assert len(ready["next_slot"]["matches"]) > 0
    assert not ready["next_slot"]["conflicts"]
    return players


def _play_week(server, edition_ids, week, *, max_slots=8):
    """Real global-slot children, never direct play() or inserted outcomes."""
    observed = []
    original_requests = []
    for i in range(max_slots):
        before = inspect(server)
        assert before["state"]["week"]["week"] == week
        if before["next_slot"] is None:
            break
        slot = before["next_slot"]
        assert slot["number"] > 0
        assert slot["matches"]
        assert slot["remaining"] > 0
        assert not slot["conflicts"]
        result, request = execute(
            server, command(
                before, "next-slot", name=f"global-season-{inspect(server)['state']['week']['season_index']}-week-{week}-slot-{i}",
            ),
        )
        assert result["manual_save_required"]
        assert not inspect(server)["saved"]
        saved = save_tour(server)
        observed.append({
            "slot_number": slot["number"],
            "match_count": len(slot["matches"]),
            "saved_revision_id": saved["revision_id"],
        })
        original_requests.append((request, result))
    else:
        raise AssertionError("Global slot progression exceeded the bounded week")
    assert inspect(server)["next_slot"] is None
    assert len(observed) >= 2, observed
    assert sum(s["match_count"] for s in observed) == 6

    for edition_id in edition_ids:
        evidence = inspect(server)["edition_evidence"][edition_id]
        matches = evidence["matches"]
        assert len(matches) == 3
        assert all(m["rally_count"] > 0 for m in matches)
        # Actual outcomes cannot be inferred from the draw or the Fixture.
        assert not next(e for e in inspect(server)["state"]["editions"]
                        if e["edition"]["edition_id"] == edition_id)["result_confirmed"]

        result, request = execute(
            server, command(inspect(server), "confirm-result",
                name=edition_id + ":confirm", edition_id=edition_id),
        )
        assert result["manual_save_required"]
        saved = save_tour(server)
        assert saved["revision_id"] == inspect(server)["saved_head_revision_id"]
        original_requests.append((request, result))

    evidence = inspect(server)["edition_evidence"]
    confirmed = {
        eid: {
            "matches": evidence[eid]["matches"],
            "results": evidence[eid]["results"],
        } for eid in edition_ids
    }
    for edition_id, item in confirmed.items():
        assert len(item["matches"]) == 3
        assert len(item["results"]) == 4
        factor = EDITION_FACTORS[edition_id]
        assert sorted(x["main_points"] for x in item["results"]) == [
            factor * 30, factor * 30, factor * 60, factor * 100,
        ]
        assert next(e for e in inspect(server)["state"]["editions"]
                    if e["edition"]["edition_id"] == edition_id)["result_confirmed"]
    return confirmed, original_requests, observed


def _check_ranking(server,season,week,editions,total):
    view=inspect(server)
    ranking=view["state"]["rankings"][-1]
    assert ranking["week"]=={"season_index":season,"week":week}
    rows=ranking["rows"]
    assert len(rows)==8
    assert sum(row["points"] for row in rows)==total
    observed=Counter(
        entry["edition_id"] for row in rows for entry in row["counted_results"]
    )
    assert observed==Counter({eid:4 for eid in editions})
    for row in rows:
        actual=row["counted_results"]
        assert len(actual)==len(editions)//2
        assert sum(e["edition_id"] in FIRST_WEEK for e in actual)==1
        assert sum(e["edition_id"] in SECOND_WEEK for e in actual)==(len(editions)==4)
        assert row["points"]==sum(e["main_points"]+e["qualification_points"] for e in actual)
        for result in actual:
            assert result["first_publication_week"]==(
                {"season_index":1,"week":1}
                if result["edition_id"] in FIRST_WEEK
                else {"season_index":1,"week":2}
            )
    return ranking


def test_simultaneous_s1_terminal_and_s2_opening_real_matches_two_signed_seasons(tmp_path):
    database=f"sqlite:///{tmp_path / 'cross-season-overlap.sqlite'}"
    url="/viewer/runs/run/calendar-tour"
    with ApiServer(database_url=database) as server:
        repo,initial=setup(server,RunCalendar(4,2,2030,3),count=8)
        initial_record=repo.get_branch_saved_revision(revision_id=initial["revision_id"])
        assert inspect(server)["state"]["week"]["week"]==2

        _plan(server,FIRST_WEEK)
        _advance(server,"transition","s1-open-announcement-w3",0,3)
        _plan(server,SECOND_WEEK)

        # S2 cannot collect submissions before its Saved announcement in S1 W4.
        before=inspect(server)
        premature=command(before,"submit",name="premature-s2-entry",
            edition_id=SECOND_WEEK[0],
            data={"player_ids":[p["player_id"] for p in before["players"][:4]]})
        assert _request("POST",tour_url(server)+"/preview",premature)[0]==409
        _advance(server,"transition","s1-open-final-w4",0,4)
        view=inspect(server)
        assert set(view["state"]["transitions"][-1]["public_event"]["announced_edition_ids"])==set(SECOND_WEEK)
        assert _request("GET",tour_url(server)+"/seasons/0")[0]==409

        original_viewer=_request("GET",server.base_url+url)
        assert original_viewer[0]==200
        players=_prepare_fields(server,FIRST_WEEK)
        first,first_requests,first_slots=_play_week(server,FIRST_WEEK,week=4)
        assert sum(len(e["matches"]) for e in first.values())==6
        assert inspect(server)["state"]["rankings"][-1]["week"]=={"season_index":0,"week":4}
        assert _request("GET",server.base_url+url)[1]["official_ranking"]==original_viewer[1]["official_ranking"]
        assert _request("GET",tour_url(server)+"/seasons/0")[0]==409

        transition,season_request,s1_receipt=_advance(
            server,"season-transition","s1-closure-with-two-simultaneous-editions",1,1
        )
        assert transition["impact"]["target_week"]["season_index"]==1
        current=inspect(server)
        assert current["saved_completed_seasons"]==[0]
        _check_ranking(server,1,1,FIRST_WEEK,660)
        signed_s1=_signed_season(server,0)
        assert signed_s1["completed_edition_count"]==2
        assert {e["edition_id"] for e in signed_s1["editions"]}==set(FIRST_WEEK)
        assert sum(c["awarded_points"] for c in signed_s1["countries"])==660
        assert sum(c["titles"] for c in signed_s1["countries"])==2
        assert _records(server)["completed_edition_count"]==2
        assert _request("GET",tour_url(server)+"/seasons/1")[0]==409
        assert repo.get_branch_saved_revision(revision_id=initial_record.revision_id)==initial_record
        first_head=current["saved_head_revision_id"]
        viewer_first=_request("GET",server.base_url+url)[1]
        print("Signed S1: two overlapping real Editions / 6 actual matches / 660 awards",
              first_slots,flush=True)

    # A cold SQLAlchemy/HTTP reopen separates the terminal from the new season.
    with ApiServer(database_url=database) as server:
        reopened=inspect(server)
        assert reopened["saved"] and reopened["saved_head_revision_id"]==first_head
        assert _request("GET",server.base_url+url)==(200,viewer_first)
        assert _signed_season(server,0)==signed_s1
        assert _check_ranking(server,1,1,FIRST_WEEK,660)
        assert all(reopened["edition_evidence"][eid]["matches"]==item["matches"]
                   for eid,item in first.items())
        assert not any(reopened["edition_evidence"].get(eid,{}).get("matches")
                       for eid in SECOND_WEEK)

        assert _prepare_fields(server,SECOND_WEEK)==players
        second,second_requests,second_slots=_play_week(server,SECOND_WEEK,week=1)
        assert sum(len(e["matches"]) for e in second.values())==6
        assert _check_ranking(server,1,1,FIRST_WEEK,660)
        # Playing in S2 must not rewrite signed S1's actual sport history.
        signed_after=_signed_season(server,0)
        for key in ("editions","countries","last_week_published_ranking"):
            assert signed_after[key]==signed_s1[key]
        assert _request("GET",tour_url(server)+"/seasons/1")[0]==409
        current_viewer=_request("GET",server.base_url+url)[1]
        assert current_viewer["official_ranking"]==viewer_first["official_ranking"]

        w2,w2_request,_=_advance(server,"transition","s2-publish-overlapping-w1",1,2)
        published=_check_ranking(server,1,2,(*FIRST_WEEK,*SECOND_WEEK),2200)
        assert w2["impact"]["ranking"]["rows"]==published["rows"]
        assert _signed_season(server,0)["editions"]==signed_s1["editions"]
        _advance(server,"transition","s2-empty-w3",1,3)
        _advance(server,"transition","s2-empty-w4",1,4)
        _advance(server,"season-transition","s2-close-two-editions",2,1)

        final=inspect(server)
        assert final["saved_completed_seasons"]==[0,1]
        season0=_signed_season(server,0)
        season1=_signed_season(server,1)
        assert season0["editions"]==signed_s1["editions"]
        assert season0["countries"]==signed_s1["countries"]
        assert season1["completed_edition_count"]==2
        assert {e["edition_id"] for e in season1["editions"]}==set(SECOND_WEEK)
        assert sum(c["awarded_points"] for c in season1["countries"])==1540
        assert sum(c["titles"] for c in season1["countries"])==2
        assert _request("GET",tour_url(server)+"/seasons/2")[0]==409

        record=_records(server)
        assert record["completed_seasons"]==[0,1]
        assert record["completed_edition_count"]==4
        country_totals={}
        for signed in (season0,season1):
            for country in signed["countries"]:
                code=country["country_code"]
                country_totals[code]=country_totals.get(code,0)+country["awarded_points"]
        assert sum(country_totals.values())==2200
        best=next(x for x in record["records"]
                  if x["record_id"]=="native_tour.country.awarded_points.v1")
        assert best["value"]==max(country_totals.values())
        assert {x["entity_id"] for x in best["holders"]}=={
            code for code,total in country_totals.items() if total==best["value"]
        }
        last_head=final["saved_head_revision_id"]
        last_public=_request("GET",server.base_url+url)[1]
        all_matches={**first,**second}
        replay=[*first_requests,*second_requests,(season_request,transition),(w2_request,w2)]
        print("Signed S2: four independent Editions / 12 actual matches / 2200 awards",
              second_slots,flush=True)

    with ApiServer(database_url=database) as server:
        current=inspect(server)
        assert current["saved"] and current["saved_head_revision_id"]==last_head
        assert current["saved_completed_seasons"]==[0,1]
        for eid,original in all_matches.items():
            evidence=current["edition_evidence"][eid]
            assert evidence["matches"]==original["matches"]
            assert evidence["results"]==original["results"]
        assert _signed_season(server,0)==season0
        assert _signed_season(server,1)==season1
        assert _records(server)==record
        assert _request("GET",server.base_url+url)==(200,last_public)
        for request,receipt in replay:
            assert _request("POST",tour_url(server)+"/execute",request)==(201,receipt)
        stable=inspect(server)
        assert stable["saved"] and stable["saved_head_revision_id"]==last_head
        assert stable["saved_completed_seasons"]==[0,1]
        assert _records(server)==record
