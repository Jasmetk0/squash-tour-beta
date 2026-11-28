"""Dallas 2025 on a native W52 Run: real HTTP, SQLite, MatchEngine and Saves.

Entry, Wild Cards and the Draw use the ordinary native Tour commands against the
copied Saved ATP profile. Qualification (16, four sections) is played in Run
week 5 and Main (32) in week 6 through the shared global slot ledger. Players
are fictional generated squash players; this is one tournament, not the
two-season ATP acceptance.
"""

import json
import time

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.calendar_tour import CalendarEditionAuthority
from beta_engine.domain.tournaments.native_scheduled_knockout import (
    scheduled_edition_plan,
)
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_atp_next_gen_edition import _save_atp_source
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

DALLAS = "atp_2025_dallas"
CLOCK = RunCalendar(52, 1, 2025, 2)
TIMINGS = {}


def _clock(view):
    return view["run_calendar"]


def dallas_schedule(view, *, q_week=5, main_week=6):
    clock = _clock(view)

    def position(week, slot):
        return {"week": {"calendar": clock, "season_index": 0, "week": week}, "slot": slot}

    return {
        "calendar": clock,
        "qualification": [position(q_week, 1), position(q_week, 2)],
        "main": [position(main_week, s) for s in range(1, 6)],
    }


def catalog_entry(server, occurrence_id=DALLAS):
    code, catalog = _request("GET", tour_url(server) + "/atp-source-editions")
    assert code == 200, catalog
    return next(e for e in catalog["entries"] if e["profile"]["occurrence_id"] == occurrence_id)


def scheduled_request(view, entry, schedule, *, name="import-dallas"):
    return {
        "command_id": name,
        "expected_saved_head": view["saved_head_revision_id"],
        "expected_checkpoint_fingerprint": view["checkpoint_fingerprint"],
        "expected_tour_fingerprint": view["tour_fingerprint"],
        "expected_profile_fingerprint": entry["profile_fingerprint"],
        "schedule": schedule,
        "operator_label": "Admin",
        "audit_reason": "Review the Saved ATP knockout profile",
    }


def preview_scheduled(server, occurrence_id, body):
    return _request(
        "POST", tour_url(server) + f"/atp-source-editions/{occurrence_id}/scheduled-edition-preview", body
    )


def confirm(server, review):
    request = {
        "command": review["command"],
        "expected_preview_fingerprint": review["preview_fingerprint"],
        "explicit_confirmation": True,
    }
    code, result = _request("POST", tour_url(server) + "/execute", request)
    assert code == 201, result
    return result


def transition(server, name):
    started = time.perf_counter()
    result, _ = execute(server, command(inspect(server), "transition", name=name))
    save_tour(server)
    TIMINGS.setdefault("transition+save", []).append(round(time.perf_counter() - started, 2))
    return result


def edition(view, occurrence_id=DALLAS):
    return next(a for a in view["state"]["editions"] if a["edition"]["edition_id"] == occurrence_id)


def authority(view, occurrence_id=DALLAS):
    return CalendarEditionAuthority.model_validate_json(json.dumps(edition(view, occurrence_id)))


def sporting_outcomes(matches):
    """Seed-determined sporting content; Saved revision ids are excluded."""
    return {
        mid: (m.seed, m.result.player_a_id, m.result.player_b_id, m.result.winner_player_id,
              [(g.winner_player_id, g.winner_games, g.loser_games) for g in m.result.sets],
              len(m.result.rally_log.events))
        for mid, m in sorted(matches.items())
    }


def accepted_matches(repo):
    with repo._session_factory() as session:
        cp = load_checkpoint(session, run_id="run", branch_id="branch")
    return {m.match_id: m for m in cp.played_continuations}


def timed_slot(server, name):
    view = inspect(server)
    cmd = command(view, "next-slot", name=name)
    started = time.perf_counter()
    code, preview = _request("POST", tour_url(server) + "/preview", cmd)
    assert code == 200, preview
    middle = time.perf_counter()
    request = {"command": cmd, "expected_preview_fingerprint": preview["preview_fingerprint"],
               "explicit_confirmation": True}
    code, result = _request("POST", tour_url(server) + "/execute", request)
    assert code == 201, result
    done = time.perf_counter()
    saved = save_tour(server)
    TIMINGS.setdefault("slot", []).append({
        "name": name, "preview_s": round(middle - started, 2), "execute_s": round(done - middle, 2),
        "save_s": round(time.perf_counter() - done, 2), "matches": len(result["match_ids"]),
    })
    return result, request, saved


def prepare_dallas_entry(server, *, occurrence_id=DALLAS, name_prefix="dallas", players=slice(0, 44),
                         direct=25, wild_cards=3):
    """Q week: native applications and field approval; returns WC nominees."""
    view = inspect(server)
    applicants = sorted(p["player_id"] for p in view["players"])[players]
    execute(server, command(view, "submit", name=f"{name_prefix}-submit", edition_id=occurrence_id,
                            data={"player_ids": applicants}))
    execute(server, command(inspect(server), "approve", name=f"{name_prefix}-approve", edition_id=occurrence_id))
    field = edition(inspect(server), occurrence_id)["field"]
    assert len(field["direct_main_player_ids"]) == direct
    assert len(field["qualification_player_ids"]) == 16
    below = field["below_qualification_cut_player_ids"]
    assert len(below) == wild_cards
    return below


@pytest.fixture(scope="module")
def dallas_run(tmp_path_factory):
    path = tmp_path_factory.mktemp("dallas") / "dallas-w52.db"
    database = f"sqlite:///{path}"
    record = {"database": database, "path": path}
    with ApiServer(database_url=database) as server:
        repo, _ = setup(server, CLOCK, count=48)
        assert inspect(server)["state"]["week"]["week"] == 2
        _save_atp_source(server)
        view = inspect(server)
        entry = catalog_entry(server)
        assert entry["profile"]["qualification_date_status"] == "verified"
        assert entry["profile"]["wild_cards"] == 3 and entry["profile"]["seeds_count"] == 8
        schedule = dallas_schedule(view)

        # Q outside its sourced week, wrong Main week and a stale head stay read-only rejections.
        for damaged in (dallas_schedule(view, q_week=4), dallas_schedule(view, main_week=7)):
            code, error = preview_scheduled(server, DALLAS, scheduled_request(view, entry, damaged))
            assert code == 409, error
        stale = {**scheduled_request(view, entry, schedule), "expected_saved_head": "stale"}
        assert preview_scheduled(server, DALLAS, stale)[0] == 409
        assert inspect(server) == view

        code, review = preview_scheduled(server, DALLAS, scheduled_request(view, entry, schedule))
        assert code == 200, review
        assert inspect(server) == view  # Preview is read-only.
        data = review["command"]["data"]
        assert data["schema_version"] == "calendar_tournament_edition.v5"
        assert data["week"]["week"] == 5 and data["announcement_week"]["week"] == 4
        assert data["point_table"]["champion"] == 500 and data["point_table"]["qualification_winner"] == 25

        # The client cannot substitute points, Draw sources or another profile.
        forged = []
        changed = json.loads(json.dumps(review["command"]))
        changed["data"]["point_table"]["champion"] = 900
        forged.append(changed)
        changed = json.loads(json.dumps(review["command"]))
        changed["data"]["scheduled_binding"]["profile"]["main_points"]["champion"] = 900
        forged.append(changed)
        changed = json.loads(json.dumps(review["command"]))
        changed["data"]["scheduled_binding"]["source_saved_content_hash"] = "f" * 64
        forged.append(changed)
        rotterdam = catalog_entry(server, "atp_2025_rotterdam")
        code, other = preview_scheduled(server, "atp_2025_rotterdam", scheduled_request(view, rotterdam, schedule))
        assert code == 200, other
        changed = json.loads(json.dumps(review["command"]))
        changed["data"]["scheduled_binding"] = other["command"]["data"]["scheduled_binding"]
        forged.append(changed)
        for cmd in forged:
            code, error = _request("POST", tour_url(server) + "/preview", cmd)
            assert code == 409, error
        # Foreign Branch cannot read or create from this Branch's Saved source.
        foreign = tour_url(server).replace("/branches/branch/", "/branches/foreign/")
        code, _ = _request("POST", foreign + f"/atp-source-editions/{DALLAS}/scheduled-edition-preview",
                           scheduled_request(view, entry, schedule))
        assert code in {404, 409}
        assert inspect(server) == view

        confirm(server, review)
        save_tour(server)
        public = _request("GET", server.base_url + "/viewer/runs/run/calendar-tour")[1]
        assert DALLAS not in {e["edition_id"] for e in public["editions"]}
        record["transitions"] = {}
        for week in (2, 3, 4):
            record["transitions"][week] = transition(server, f"dallas-week-{week}")["impact"]["completed_week"]
        assert inspect(server)["state"]["week"]["week"] == 5
        public = _request("GET", server.base_url + "/viewer/runs/run/calendar-tour")[1]
        assert DALLAS in {e["edition_id"] for e in public["editions"]}

        wild_cards = prepare_dallas_entry(server)
        before_draw = inspect(server)
        # No slot can run before the reviewed Saved Draw.
        assert _request("POST", tour_url(server) + "/preview", command(before_draw, "next-slot"))[0] == 409
        for bad in ([], wild_cards[:2], [*wild_cards[:2], edition(before_draw)["field"]["direct_main_player_ids"][0]]):
            code, error = _request("POST", tour_url(server) + "/preview",
                                   command(before_draw, "draw", edition_id=DALLAS, data={"wild_card_player_ids": bad}))
            assert code == 409, error
        malformed = command(
            before_draw, "draw", edition_id=DALLAS,
            data={"wild_card_player_ids": [*wild_cards[:2], {}]},
        )
        code, error = _request("POST", tour_url(server) + "/preview", malformed)
        assert code == 409, error
        assert "distinct Wild Card players" in error["detail"]["message"]
        assert inspect(server) == before_draw
        drawn, _ = execute(server, command(before_draw, "draw", name="dallas-draw", edition_id=DALLAS,
                                           data={"wild_card_player_ids": wild_cards}))
        assert drawn["wild_card_player_ids"] == wild_cards
        # The live Draw is not enough: Save it before any match.
        assert _request("POST", tour_url(server) + "/preview", command(inspect(server), "next-slot"))[0] == 409
        save_tour(server)
        view = inspect(server)
        plan = scheduled_edition_plan(authority(view))
        record["plan"] = plan
        assert len(plan.topology.plans) == 43
        assert set(plan.draw_input.wild_card_player_ids) == set(wild_cards)
        assert len(plan.draw_input.main_seed_player_ids) == 8

        # Premature Main and transition are rejected without mutation.
        main_first = next(n.node_id for n in plan.draw.main.nodes if n.round_number == 1)
        code, error = _request("POST", tour_url(server) + "/preview",
                               command(view, "next-match", data={"match_id": main_first}))
        assert code == 409, error
        code, error = _request("POST", tour_url(server) + "/preview", command(view, "transition"))
        assert code == 409, error
        assert "scheduled_round_incomplete:" + DALLAS in view["transition_blockers"]
        assert inspect(server) == view

        # Week 5: Qualification, two slots, real MatchEngine; replay is idempotent.
        first, request, _ = timed_slot(server, "dallas-q-1")
        assert len(first["match_ids"]) == 8
        before_repeat = accepted_matches(repo)
        assert _request("POST", tour_url(server) + "/execute", request) == (201, first)
        assert accepted_matches(repo) == before_repeat
        second, _, saved = timed_slot(server, "dallas-q-2")
        assert len(second["match_ids"]) == 4
        q_matches = {mid: m for mid, m in accepted_matches(repo).items() if mid in {
            p.match_id for p in plan.topology.plans}}
        assert len(q_matches) == 12
        assert all(m.week.week == 5 and m.result.rally_log.events for m in q_matches.values())
        view = inspect(server)
        assert view["next_slot"] is None
        assert not edition(view)["tournament_fingerprint"]
        record["q_matches"] = {mid: m.fingerprint for mid, m in q_matches.items()}
        record["q_outcomes"] = sporting_outcomes(q_matches)
        record["after_q"] = view
        record["after_q_saved"] = saved
    return record


def test_dallas_q_week_main_week_save_restart_and_official_points(dallas_run):
    database = dallas_run["database"]
    plan = dallas_run["plan"]
    with ApiServer(database_url=database) as server:
        repo = server.app.state.runtime.repository
        view = inspect(server)
        # Cold reopen of the same Run restores exactly the explicitly Saved Q week.
        for field in ("saved_head_revision_id", "checkpoint_fingerprint", "tour_fingerprint", "state"):
            assert view[field] == dallas_run["after_q"][field]
        assert {mid: m.fingerprint for mid, m in accepted_matches(repo).items()
                if mid in dallas_run["q_matches"]} == dallas_run["q_matches"]
        event = transition(server, "dallas-q-to-main")
        week_event = inspect(server)["state"]["transitions"][-1]["public_event"]
        dallas_run["w05_w06_event"] = week_event
        assert week_event["kind"] == "week_transition_completed"
        assert week_event["week"]["week"] == 6
        view = inspect(server)
        assert view["state"]["week"]["week"] == 6

        # Exactly the four confirmed Q winners occupy their Main places.
        matches = accepted_matches(repo)
        q_finals = {b.section_id: max(b.nodes, key=lambda n: n.round_number).node_id
                    for b in plan.draw.qualification_brackets}
        winners = {f"winner:{mid}": matches[mid].result.winner_player_id for mid in q_finals.values()}
        slot = view["next_slot"]
        assert slot["number"] == 1 and len(slot["matches"]) == 16
        main_pairs = {m["match_id"]: (m["player_a_id"], m["player_b_id"]) for m in slot["matches"]}
        placed = {}
        for item in plan.topology.plans:
            if item.match_id in main_pairs:
                for source, pid in zip(item.participant_sources, main_pairs[item.match_id], strict=True):
                    if source in winners:
                        placed[source] = pid
        assert placed == winners

        for number in range(1, 6):
            timed_slot(server, f"dallas-main-{number}")
        view = inspect(server)
        assert edition(view)["tournament_fingerprint"]
        evidence = view["edition_evidence"][DALLAS]
        main = [m for m in evidence["matches"] if m["match_id"] not in dallas_run["q_matches"]]
        assert len(evidence["matches"]) == 43 and len(main) == 31
        assert len(evidence["results"]) == 44
        before_publication = view["state"]["rankings"][-1]
        confirmed, confirm_request = execute(server, command(view, "confirm-result", edition_id=DALLAS))
        assert _request("POST", tour_url(server) + "/execute", confirm_request) == (201, confirmed)
        assert inspect(server)["state"]["rankings"][-1] == before_publication
        save_tour(server)
        transition(server, "dallas-publication")
        final = inspect(server)
        assert final["state"]["week"]["week"] == 7
        resolved = {r["player_id"]: (r["main_points"], r["qualification_points"]) for r in evidence["results"]}
        ranking = {row["player_id"]: row for row in final["state"]["rankings"][-1]["rows"]}
        for pid, (main_points, q_points) in resolved.items():
            counted = [r for r in ranking[pid]["counted_results"] if r["edition_id"] == DALLAS]
            assert len(counted) == 1
            assert (counted[0]["main_points"], counted[0]["qualification_points"]) == (main_points, q_points)
            assert ranking[pid]["points"] == main_points + q_points
        assert sorted(q for _, q in resolved.values() if q == 25) == [25] * 4
        assert sum(1 for m, q in resolved.values() if q == 13) == 4
        champion = max(resolved, key=lambda pid: resolved[pid][0])
        assert resolved[champion] == (500, 0) or resolved[champion][0] == 500
        # Publication happens once: another Week Transition keeps one Dallas result.
        transition(server, "dallas-after-publication")
        later = inspect(server)["state"]["rankings"][-1]["rows"]
        assert all(sum(r["edition_id"] == DALLAS for r in row["counted_results"]) <= 1 for row in later)
        published = inspect(server)
        from beta_engine.application.calendar_continuation_service import CalendarContinuationService
        replay = CalendarContinuationService(repo).replay(
            run_id="run", branch_id="branch", match_id=plan.topology.terminal_group_id)
        assert replay["exact_replay"]

        # Physical corruption of the copied profile's Saved source fails closed.
        source_id = authority(published).scheduled_binding.source_saved_revision_id
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, source_id)
            original = row.payload_json
            changed = json.loads(original)
            changed["run"]["display_name"] = "damaged Saved ATP source"
            row.payload_json = json.dumps(changed)
        assert _request("GET", tour_url(server))[0] == 409
        with repo._session_factory.begin() as session:
            session.get(BranchSavedRevisionModel, source_id).payload_json = original
        assert inspect(server)["tour_fingerprint"] == published["tour_fingerprint"]

    with ApiServer(database_url=database) as restarted:
        reopened = inspect(restarted)
        assert reopened["state"] == published["state"]
        assert reopened["edition_evidence"][DALLAS] == published["edition_evidence"][DALLAS]
        status, public = _request("GET", restarted.base_url + "/viewer/runs/run/calendar-tour")
        assert status == 200, public
        assert next(e for e in public["editions"] if e["edition_id"] == DALLAS)["completed"] is True
    dallas_run["final"] = published
    print("DALLAS_TIMINGS", json.dumps(TIMINGS))
    print("DALLAS_W05_W06_EVENT", json.dumps(dallas_run["w05_w06_event"]))


def test_same_seed_reproduces_dallas_qualification_in_an_independent_run(dallas_run, tmp_path):
    """A second Run from identical inputs/seeds yields the same 12 Q results."""
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'dallas-repeat.db'}") as server:
        repo, _ = setup(server, CLOCK, count=48)
        _save_atp_source(server)
        view = inspect(server)
        entry = catalog_entry(server)
        code, review = preview_scheduled(server, DALLAS, scheduled_request(view, entry, dallas_schedule(view)))
        assert code == 200, review
        confirm(server, review)
        save_tour(server)
        for week in (2, 3, 4):
            transition(server, f"repeat-week-{week}")
        wild_cards = prepare_dallas_entry(server)
        execute(server, command(inspect(server), "draw", name="dallas-draw", edition_id=DALLAS,
                                data={"wild_card_player_ids": wild_cards}))
        save_tour(server)
        plan = scheduled_edition_plan(authority(inspect(server)))
        assert plan.draw.model_dump(exclude={"run_id", "branch_id"}) == dallas_run["plan"].draw.model_dump(
            exclude={"run_id", "branch_id"})
        timed_slot(server, "repeat-q-1")
        timed_slot(server, "repeat-q-2")
        ids = {p.match_id for p in plan.topology.plans}
        repeat = sporting_outcomes({mid: m for mid, m in accepted_matches(repo).items() if mid in ids})
        assert repeat == dallas_run["q_outcomes"]

        # Branch isolation: a native fork of this Saved head is rejected
        # explicitly instead of remapping the cross-week source silently.
        from beta_engine.infrastructure.db.native_fork_baseline import prepare_native_fork_baseline_in_session
        head = inspect(server)["saved_head_revision_id"]
        with repo._session_factory() as session:
            with pytest.raises(ValueError, match="Scheduled cross-week"):
                prepare_native_fork_baseline_in_session(
                    repo, session, run_id="run", source_branch_id="branch",
                    source_revision_id=head, target_branch_id="fork")
