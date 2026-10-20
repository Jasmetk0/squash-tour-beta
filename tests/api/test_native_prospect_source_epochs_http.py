"""Full real HTTP/SQLite prospective source epoch -> Tour/MatchEngine -> next cohort.

Dedicated acceptance only: never add this long scenario to Fast CI.
"""
from copy import deepcopy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.run_prospect_source_state import (
    RUN_PROSPECT_SOURCE_COMPONENT_KEY, RUN_PROSPECT_EPOCH_SCHEMA,
    load_saved_run_prospect_source,
)
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_population_sporting_checkpoint import restore
from tests.api.test_calendar_tour_flow import (
    command, execute, inspect, save_tour, setup, tour_url,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def _source_url(server):
    return server.base_url + "/admin/runs/run/branches/branch/authoritative-simulation/prospect-source/save"


def _review_new_year(server, *, season):
    url = server.base_url + "/admin/players/runs/run/branches/branch/intake/native-calendar"
    request = {
        "world_package_id": "official_fax_world",
        "season_index": season,
        "base_annual_intake_target": 14,
        "country_code": "GER",
    }
    code, review = _request("POST", url + "/preview", request)
    assert code == 200, review
    assert review["materialization_supported"] and review["prepared_profile_count"] > 0
    return url, request, review


def _transition_and_save(server, *, action="transition", name):
    result, retry = execute(server, command(inspect(server), action, name=name))
    saved = save_tour(server)
    return result, retry, saved


def test_real_run_future_epoch_preserves_matched_tour_and_admits_next_year_after_restart(tmp_path):
    """Short 7-week production calendar keeps real year rollover affordable.

    Earth W52/FAX W61 strict birthday/replay is separately tested against both
    real clocks; this end-to-end is deliberately not duplicated in Fast CI.
    """
    path = tmp_path / "epochs-tour.db"
    db = f"sqlite:///{path}"
    clock = RunCalendar(7, 1, 2030, 3)
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, 4)
        saved_first = sign_prospects(server, repo, clock)
        assert saved_first["content_hash"]
        born, _, born_saved = _transition_and_save(server, name="epoch-first-birthday")
        assert "born-native-15" in born["impact"]["admitted_player_ids"]
        prior_birth = repo.get_branch_saved_revision(revision_id=born_saved["revision_id"])
        original_source = load_saved_run_prospect_source(prior_birth.payload, run_id="run")
        assert original_source.schema_version == "run_prospect_source_snapshot.v1"
        assert original_source.for_week(2).fingerprint == original_source.fingerprint

        # Genuine signed current-population Tour, four entrants, original
        # deterministic MatchEngine, immutable result and Official points.
        view = inspect(server)
        week = {**view["state"]["week"], "calendar": view["run_calendar"]}
        execute(server, command(
            view, "create-edition", name="epoch:create",
            data={
                "edition_id": "epoch-cup", "name": "Historically signed Cup",
                "week": {**week, "week": 5},
                "announcement_week": {**week, "week": 4},
                "start_slot": 1, "main_entrant_count": 4, "ranked": True,
                "validity_weeks": 7,
                "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
            },
        ))
        save_tour(server)
        for w in (4, 5):
            _transition_and_save(server, name=f"epoch-before-play-{w}")
        view = inspect(server)
        entrants = ["born-native-15"] + [
            p["player_id"] for p in view["players"] if p["player_id"] != "born-native-15"
        ][:3]
        assert len(entrants) == 4
        execute(server, command(
            view, "submit", edition_id="epoch-cup", name="epoch:submit",
            data={"player_ids": entrants},
        ))
        for action in ("approve", "draw"):
            execute(server, command(
                inspect(server), action, edition_id="epoch-cup", name=f"epoch:{action}",
            ))
        save_tour(server)
        actual, exact_retry = execute(server, command(
            inspect(server), "play", edition_id="epoch-cup", name="epoch:play",
        ))
        assert actual["impact"]
        play_saved = save_tour(server)
        past_match_payload = repo.get_branch_saved_revision(
            revision_id=play_saved["revision_id"]
        ).payload
        original_match_fingerprint = past_match_payload["content"][
            "calendar_player_sporting_checkpoint"
        ]["fingerprint"]
        changed = deepcopy(exact_retry)
        changed["command"]["seed"] += 1
        assert _request("POST", tour_url(server) + "/execute", changed)[0] == 409
        execute(server, command(
            inspect(server), "confirm-result", edition_id="epoch-cup",
            name="epoch:confirm",
        ))
        save_tour(server)
        awarded, _, awarded_save = _transition_and_save(
            server, name="epoch-official-result",
        )
        assert sorted(r["points"] for r in awarded["impact"]["ranking"]["rows"]) == [
            30, 30, 60, 100,
        ]
        signed_match = repo.get_branch_saved_revision(
            revision_id=awarded_save["revision_id"]
        )
        signed_match_hash = signed_match.content_hash

        # New YEAR, genuine existing native Saved-World generation review.
        url, request, review = _review_new_year(server, season=1)
        before_preview = _dump(path)
        assert _request("POST", url + "/preview", request) == (200, review)
        assert _dump(path) == before_preview
        altered = {
            "request": request, "expected_saved_head": review["saved_head_revision_id"],
            "expected_review_fingerprint": "0" * 64, "explicit_confirmation": True,
            "audit_label": "Admin", "audit_reason": "Explicit later season source cohort",
        }
        assert _request("POST", url + "/materialize", altered)[0] == 409
        assert _dump(path) == before_preview
        confirmed = {
            **altered, "expected_review_fingerprint": review["review_fingerprint"],
        }
        code, materialized = _request("POST", url + "/materialize", confirmed)
        assert code == 201, materialized
        assert materialized["requires_manual_source_save"]
        assert materialized["created_count"] == review["prepared_profile_count"]
        assert repo.get_branch_saved_revision(revision_id=born_saved["revision_id"]).content_hash == prior_birth.content_hash

        source_url = _source_url(server)
        code, before_save = _request("GET", source_url + "/preview")
        assert code == 200 and before_save["can_save"] and not before_save["blockers"]
        expected = {
            "expected_draft_version": before_save["draft_version"],
            "expected_run_prospect_source_fingerprint": before_save[
                "run_prospect_source_fingerprint"
            ],
            "expected_saved_head_revision_id": before_save["saved_head_revision_id"],
        }
        stale = {**expected, "expected_saved_head_revision_id": "forged"}
        before_stale = _dump(path)
        assert _request("POST", source_url, stale)[0] == 409
        assert _request("POST", source_url.replace("/branches/branch/", "/branches/foreign/"), expected)[0] == 409
        assert _dump(path) == before_stale
        code, epoch_save = _request("POST", source_url, expected)
        assert code == 201, epoch_save
        epoch_revision = repo.get_branch_saved_revision(
            revision_id=epoch_save["saved_revision"]["revision_id"]
        )
        raw_epoch = epoch_revision.payload["content"][RUN_PROSPECT_SOURCE_COMPONENT_KEY]
        assert raw_epoch["schema_version"] == RUN_PROSPECT_EPOCH_SCHEMA
        historic = load_saved_run_prospect_source(epoch_revision.payload, run_id="run")
        assert historic.for_week(2).fingerprint == original_source.fingerprint
        assert historic.for_week(6).fingerprint != original_source.fingerprint
        assert len(historic.records) > len(original_source.records)
        assert repo.get_branch_saved_revision(revision_id=awarded_save["revision_id"]).content_hash == signed_match_hash
        assert repo.get_branch_saved_revision(revision_id=play_saved["revision_id"]).payload[
            "content"
        ]["calendar_player_sporting_checkpoint"]["fingerprint"] == original_match_fingerprint

        # Last week, true Season Transition, then exact birth clock from the
        # generated future cohort; no preview or materialization activated them.
        assert not set(p["prospect_id"] for p in review["first_prepared_prospects"]) & {
            p["player_id"] for p in inspect(server)["players"]
        }
        _transition_and_save(server, name="epoch-last-first-year")
        _transition_and_save(server, action="season-transition", name="epoch-next-year")
        first_due = next(i for i, n in enumerate(review["week_counts"], 1) if n > 0)
        last = None
        for week in range(2, first_due + 1):
            last, _, _ = _transition_and_save(server, name=f"epoch-second-year-{week}")
        if first_due == 1:
            with repo._session_factory() as session:
                from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
                life = get_lifecycle(session, run_id="run", branch_id="branch",
                    week=inspect(server)["state"]["week"])
            assert life is not None
        else:
            assert last is not None and last["impact"]["admitted_player_ids"]
        assert len(inspect(server)["players"]) > 5
        post = save_tour(server) if not inspect(server)["saved"] else None
        assert post is None or post["revision_id"]

    with ApiServer(database_url=db) as restarted:
        repo = restarted.app.state.runtime.repository
        code, view = _request("GET", tour_url(restarted))
        assert code == 200, view
        assert len(view["players"]) > 5
        historic = repo.get_branch_saved_revision(revision_id=awarded_save["revision_id"])
        assert historic.content_hash == signed_match_hash
        assert repo.verify_branch_saved_revision_hash(revision_id=play_saved["revision_id"])
        assert repo.verify_branch_saved_revision_hash(revision_id=awarded_save["revision_id"])
        restored = restore(restarted, awarded_save["revision_id"])
        source = load_saved_run_prospect_source(restored["payload"], run_id="run")
        assert source.schema_version == "run_prospect_source_snapshot.v1"
        assert source.fingerprint == original_source.fingerprint
        assert repo.get_branch_saved_revision(
            revision_id=epoch_save["saved_revision"]["revision_id"]
        ).payload["content"][RUN_PROSPECT_SOURCE_COMPONENT_KEY] == raw_epoch
