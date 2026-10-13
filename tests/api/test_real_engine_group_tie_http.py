"""Production FastAPI endpoints for a genuine MatchEngine-generated group tie.

This tests actual HTTP, authoritative SQLite rows and audit command semantics.
Only schedule/result *input adapters* are fixtures fed by real MatchEngine
matches. It does not claim a normal Run Match-Day execution or Run Save here.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsBuilder, TournamentGroupStandingsUnresolvedTie,
)
from beta_engine.infrastructure.db import (
    tournament_group_standings_authority as standings_module,
    tournament_group_tie_resolution_authority as ties_module,
)
from beta_engine.infrastructure.db.models import (
    TournamentGroupStandingsAuthorityModel,
    TournamentGroupTieResolutionAuthorityModel,
)
from beta_engine.application.run_saved_tour_group_schedule import RunSavedTourGroupSchedule
from beta_engine.application.run_saved_tour_group_standings import (
    resolve_saved_tour_group_standings, resolve_saved_tour_pending_group_ties,
)
from tests.infrastructure.test_real_match_engine_group_tie import _engine_cyclic_receipts
from tests.infrastructure.real_four_player_cyclic_tie_evidence import (
    _generate_four_player_cyclic_receipts,
)
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

pytestmark = pytest.mark.pr_critical


def _saved_tie_row(row):
    return {
        "run_id": row.run_id,
        "branch_id": row.branch_id,
        "event_id": row.event_id,
        "command_id": row.command_id,
        "authority_fingerprint": row.authority_fingerprint,
        "case_fingerprint": row.case_fingerprint,
        "group_match_schedule_fingerprint": row.group_match_schedule_fingerprint,
        "payload_json": row.payload_json,
    }


def _saved_table_row(row):
    return {
        "run_id": row.run_id,
        "branch_id": row.branch_id,
        "event_id": row.event_id,
        "command_id": row.command_id,
        "authority_fingerprint": row.authority_fingerprint,
        "group_match_schedule_fingerprint": row.group_match_schedule_fingerprint,
        "group_rules_policy_fingerprint": row.group_rules_policy_fingerprint,
        "payload_json": row.payload_json,
    }


@pytest.mark.parametrize("group_size", (3, 4))
def test_real_engine_cyclic_tie_http_audit_and_finalization_survive_restart(
    tmp_path, monkeypatch, group_size,
):
    # A bounded, deterministic search produces real BO3 MatchEngine scores,
    # point totals and rally logs, not synthetic win/scoreline receipts.
    initial_schedule, receipts, real_case = (
        _engine_cyclic_receipts()
        if group_size == 3
        else _generate_four_player_cyclic_receipts()
    )
    assert initial_schedule.group_size == group_size
    assert len(receipts) == (3 if group_size == 3 else 6)
    assert real_case.player_ids == ("A", "B", "C")

    # The runtime-created Run/Branch IDs are different on every test execution.
    # Read-only fixture adapters bind the genuine match receipts/schedule to
    # that exact Run. HTTP commands, scope checks, CAS/idempotency, authority
    # rows, commit transactions and historical projections stay production.
    scope = {}
    class ScheduleFixture:
        def __init__(self, session):
            self.session = session

        def get(self, *, run_id, branch_id, event_id):
            if (run_id, branch_id, event_id) != (
                scope.get("run_id"), scope.get("branch_id"), "event"
            ):
                return None
            return initial_schedule.model_copy(update={
                "run_id": run_id, "branch_id": branch_id,
            })

    monkeypatch.setattr(
        ties_module, "TournamentGroupMatchScheduleAuthorityStore", ScheduleFixture
    )
    monkeypatch.setattr(
        standings_module, "TournamentGroupMatchScheduleAuthorityStore",
        ScheduleFixture,
    )
    monkeypatch.setattr(
        standings_module.TournamentGroupStandingsAuthorityStore,
        "_result_receipts", lambda self, **kwargs: receipts,
    )
    database_url = f"sqlite:///{tmp_path / 'real-group-tie-http.db'}"
    event_id = "event"
    interim_component = None

    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, initial_revision = _create_run(
            server, display_name="Real Engine HTTP tie",
        )
        scope.update(run_id=run_id, branch_id=branch_id)
        prefix = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            f"/tournaments/{event_id}/group-standings"
        )
        tied = prefix + "/tie-resolution"

        status, absent = _request("GET", prefix)
        assert status == 404
        status, pending = _request("GET", tied)
        assert status == 200
        assert pending["unresolved_case"] == real_case.model_dump(mode="json")
        assert pending["unresolved_case_fingerprint"] == real_case.fingerprint
        assert pending["resolutions"] == []

        status, premature = _request(
            "POST", prefix + "/generate", {"command_id": "too-early"}
        )
        assert status == 409
        assert premature["detail"]["code"] == "tournament_group_standings_conflict"

        reason = "Reviewed real simulated sets, point ratios and rally evidence."
        decision = {
            "command_id": "operator-http-tie-case",
            "case_fingerprint": real_case.fingerprint,
            "ordered_player_ids": ["C", "A", "B"],
            "admin_reason": reason,
        }
        for changed in (
            {**decision, "case_fingerprint": "0" * 64},
            {**decision, "ordered_player_ids": ["A", "B", "wrong"]},
        ):
            code, invalid = _request("POST", tied, changed)
            assert code == 409
            assert invalid["detail"]["code"] == "tournament_group_tie_resolution_conflict"

        code, wrong_event = _request(
            "GET", tied.replace(f"/{event_id}/", "/unrelated/")
        )
        assert code == 409
        code, other_run = _request(
            "GET", tied.replace(f"/runs/{run_id}/", "/runs/not-this-run/")
        )
        assert code == 409

        status, committed = _request("POST", tied, decision)
        assert status == 201, committed
        assert committed["decision"]["ordered_player_ids"] == ["C", "A", "B"]
        assert committed["decision"]["case"] == real_case.model_dump(mode="json")
        assert committed["decision"]["admin_reason"] == reason
        assert len(committed["authority_fingerprint"]) == 64

        status, retry = _request("POST", tied, decision)
        assert status == 201 and retry == committed
        status, conflict = _request(
            "POST", tied, {**decision, "ordered_player_ids": ["A", "B", "C"]}
        )
        assert status == 409
        assert conflict["detail"]["code"] == "tournament_group_tie_resolution_conflict"
        status, pending = _request("GET", tied)
        assert status == 200
        assert pending["unresolved_case"] is None
        assert pending["unresolved_case_fingerprint"] is None
        assert len(pending["resolutions"]) == 1
        assert pending["resolutions"][0] == committed

        engine = create_engine(database_url)
        with Session(engine) as session:
            row = session.get(
                TournamentGroupTieResolutionAuthorityModel,
                (run_id, branch_id, event_id, real_case.fingerprint),
            )
            assert row is not None
            assert row.authority_fingerprint == committed["authority_fingerprint"]
            interim_component = {"group_tie_resolutions": [_saved_tie_row(row)]}
        engine.dispose()

        frozen_schedule = initial_schedule.model_copy(
            update={"run_id": run_id, "branch_id": branch_id}
        )
        archived_schedule = RunSavedTourGroupSchedule(
            run_id=run_id, revision_branch_id=branch_id,
            event_id=event_id, authority_fingerprint=frozen_schedule.fingerprint,
            group_count=1, group_size=group_size, match_day_count=3, matches=(),
        )
        assert resolve_saved_tour_group_standings(
            interim_component, run_id=run_id, branch_id=branch_id,
            event_id=event_id, group_schedule=archived_schedule,
        ) is None
        interim_audit = resolve_saved_tour_pending_group_ties(
            interim_component, run_id=run_id, branch_id=branch_id,
            event_id=event_id, group_schedule=archived_schedule,
        )
        assert len(interim_audit) == 1
        assert interim_audit[0].admin_reason == reason
        assert interim_audit[0].ordered_player_ids == ("C", "A", "B")

    # Re-open the actual FastAPI HTTP service against the same SQLite DB
    # before final table generation, retaining the same fixture inputs.
    with ApiServer(database_url=database_url) as server:
        prefix = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            f"/tournaments/{event_id}/group-standings"
        )
        tied = prefix + "/tie-resolution"
        status, persisted = _request("GET", tied)
        assert status == 200 and persisted["resolutions"] == [committed]
        assert persisted["unresolved_case"] is None

        status, final = _request(
            "POST", prefix + "/generate", {"command_id": "after-audited-http"}
        )
        assert status == 201, final
        assert [r["player_id"] for r in final["groups"][0]["rows"]] == (
            ["C", "A", "B"] + (["D"] if group_size == 4 else [])
        )
        assert final["admin_tie_resolutions"][0]["case"] == real_case.model_dump(mode="json")
        assert final["admin_tie_resolutions"][0]["admin_reason"] == reason
        status, same = _request(
            "POST", prefix + "/generate", {"command_id": "after-audited-http"}
        )
        assert status == 201 and same == final
        status, rejected = _request(
            "POST", prefix + "/generate", {"command_id": "different-final"}
        )
        assert status == 409
        status, rejected = _request(
            "POST", tied,
            {**decision, "command_id": "late-decision"},
        )
        assert status == 409

    # Third process instance: the immutable final DB row and separate older
    # intermediate projection still replay from exact persisted identities.
    with ApiServer(database_url=database_url) as server:
        prefix = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            f"/tournaments/{event_id}/group-standings"
        )
        status, read_final = _request("GET", prefix)
        assert status == 200
        assert read_final == final

    engine = create_engine(database_url)
    with Session(engine) as session:
        row = session.get(
            TournamentGroupStandingsAuthorityModel,
            (run_id, branch_id, event_id),
        )
        assert row is not None
        final_component = {
            **interim_component,
            "group_standings": [_saved_table_row(row)],
        }
        projected = resolve_saved_tour_group_standings(
            final_component, run_id=run_id, branch_id=branch_id,
            event_id=event_id, group_schedule=archived_schedule,
        )
        assert projected is not None
        assert projected.authority_fingerprint == final["authority_fingerprint"]
        assert len(projected.tie_decisions) == 1
        assert [r.player_id for r in projected.groups[0].rows] == (
            ["C", "A", "B"] + (["D"] if group_size == 4 else [])
        )
        assert resolve_saved_tour_pending_group_ties(
            final_component, run_id=run_id, branch_id=branch_id,
            event_id=event_id, group_schedule=archived_schedule,
        ) == ()
        assert resolve_saved_tour_group_standings(
            interim_component, run_id=run_id, branch_id=branch_id,
            event_id=event_id, group_schedule=archived_schedule,
        ) is None
    engine.dispose()
