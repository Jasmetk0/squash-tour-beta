"""Actual played/saved calendar sport must survive Run-wide horizon changes.

Positive setup uses production population, MatchEngine, awards and Save commands;
no synthetic sporting outcome or manually re-signed historical revision.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import (
    CalendarStandaloneMatchModel, RunCalendarExtensionReceiptModel,
)
from tests.api.test_calendar_knockout_awards_flow import saved_bracket, proposal
from tests.api.test_calendar_standalone_match_flow import prepare_saved_world, base as exhibition_base
from tests.api.test_calendar_signed_knockout_standings_flow import (
    make_signed_scores, standings,
)
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def extension(server, count):
    return _request("GET", server.base_url
                    + f"/run-containers/run/calendar/extension-review?new_season_count={count}")


def extend(server, review, command_id="extend-after-sport"):
    return _request("POST", server.base_url + "/run-containers/run/calendar/extension-save", {
        "command_id": command_id,
        "new_season_count": review["proposed_calendar"]["season_count"],
        "review_fingerprint": review["review_fingerprint"],
        "explicit_confirmation": True,
    })


def played_command(knockout):
    return {
        **{key: knockout[key] for key in (
            "command_id", "match_id", "seed", "operator_label", "audit_reason", "entrant_ids",
        )},
        "expected_saved_head": knockout["source_saved_head"],
        "expected_initial_world_fingerprint": knockout["source_initial_world_fingerprint"],
    }


@pytest.mark.parametrize("clock", [RunCalendar(52, 1, 2030, 1), RunCalendar(80, 37, 2100, 1)])
def test_saved_scored_knockout_extension_restart_and_historical_restore(tmp_path, clock):
    url = f"sqlite:///{tmp_path / 'sporting-extension.db'}"
    with ApiServer(database_url=url) as server:
        repo, population_head, bracket_head, scored_head, applied = make_signed_scores(server, clock)
        original = repo.get_branch_saved_revision(revision_id=scored_head)
        # Every Branch participates, including an alternative materialized
        # from the earlier population; no privileged Main/Official Branch.
        status, fork = _request("POST", server.base_url + "/run-containers/run/branches", {
            "source_branch_id": "branch", "source_saved_revision_id": population_head,
            "display_name": "Earlier population alternative",
        })
        assert status == 201, fork
        status, review = extension(server, 3)
        assert status == 200, review
        assert review["can_save"], review["blockers"]
        assert review["branch_count"] == 2
        status, receipt = extend(server, review)
        assert status == 200, receipt
        assert receipt["branch_count"] == 2
        extended_head = next(b["saved_revision_id"] for b in receipt["branches"]
                             if b["branch_id"] == "branch")
        assert receipt["simulation_started"] is False
        assert receipt["sporting_execution_unlocked"] is False
        assert extend(server, review) == (200, receipt)
        status, view = _request("GET", base(server))
        assert status == 200 and view["saved"], view
        assert view["run_calendar"]["season_count"] == 3
        assert view["knockout_fingerprint"] == applied["fingerprint"]
        assert view["knockout"]["week"]["calendar"] == clock.to_metadata()
        assert _request("GET", base(server) + "/scoring-source/replay")[1]["exact_replay"]
        played = applied["prepared"]["knockout"]
        assert _request("POST", base(server) + "/simulate", played_command(played)) == (
            201, {"knockout": played, "fingerprint": canonical_hash(played)},
        )
        assert _request("POST", base(server) + "/simulate", {
            **played_command(played), "seed": played["seed"] + 1,
        })[0] == 409
        assert standings(server, scored_head)[0] == 409
        assert standings(server, extended_head)[1]["points_in_period"]
        assert standings(server, extended_head, 1, 1)[1]["points_in_period"]
        assert not standings(server, extended_head, 1, 2)[1]["points_in_period"]
        assert repo.get_branch_saved_revision(revision_id=scored_head) == original
        new = repo.get_branch_saved_revision(revision_id=extended_head)
        assert new.payload["content"] == original.payload["content"]
        status, readiness = _request("GET", server.base_url
                                    + "/admin/runs/run/branches/branch/home-readiness")
        assert status == 200, readiness
        assert readiness["phase"] == "sporting_history"
        assert readiness["saved_transition_count"] == 0
        assert readiness["saved_published_ranking_count"] == 0
        assert not readiness["sporting_calendar_supported_by_legacy_writers"]
        for head in (population_head, bracket_head, scored_head, extended_head):
            assert repo.verify_branch_saved_revision_hash(revision_id=head)

    with ApiServer(database_url=url) as restarted:
        assert extend(restarted, review) == (200, receipt)
        assert _request("GET", base(restarted))[1]["saved"]
        assert _request("GET", base(restarted) + "/scoring-source/replay")[1]["exact_replay"]
        assert not standings(restarted, extended_head, 1, 2)[1]["points_in_period"]
        assert _request("POST", base(restarted) + "/simulate", played_command(played)) == (
            201, {"knockout": played, "fingerprint": canonical_hash(played)},
        )
        restore = (restarted.base_url + "/run-containers/run/branches/branch/saved-revisions/"
                   + bracket_head + "/restore")
        status, preflight = _request("GET", restore + "-preflight")
        assert status == 200 and preflight["can_restore"], preflight
        status, restored = _request("POST", restore, {
            "expected_head_saved_revision_id": extended_head,
            "expected_draft_version": preflight["draft_version"],
            "expected_current_viewer_branch_id": "branch",
            "explicit_confirmation": True,
        })
        assert status == 201, restored
        restored_head = restored["saved_revision"]["revision_id"]
        assert restarted.app.state.runtime.repository.get_branch_saved_revision(
            revision_id=restored_head
        ).payload["run"]["run_calendar"]["season_count"] == 3
        assert standings(restarted, restored_head)[0] == 409
        assert _request("GET", base(restarted) + "/scoring-source/replay")[1]["exact_replay"]
        assert restarted.app.state.runtime.repository.get_branch_saved_revision(
            revision_id=scored_head
        ) == original
        # Forward restore to the earlier scored state still keeps the current
        # extended horizon; it reinstalls exactly the original evidence.
        forward = (restarted.base_url + "/run-containers/run/branches/branch/saved-revisions/"
                   + scored_head + "/restore")
        status, preflight = _request("GET", forward + "-preflight")
        assert status == 200 and preflight["can_restore"], preflight
        status, restored_score = _request("POST", forward, {
            "expected_head_saved_revision_id": restored_head,
            "expected_draft_version": preflight["draft_version"],
            "expected_current_viewer_branch_id": "branch", "explicit_confirmation": True,
        })
        assert status == 201, restored_score
        fresh = restored_score["saved_revision"]["revision_id"]
        assert standings(restarted, fresh)[1]["scored_evidence_fingerprint"] == applied["fingerprint"]
        assert not standings(restarted, fresh, 1, 2)[1]["points_in_period"]
        assert extension(restarted, 4)[1]["can_save"]


def test_unsaved_awards_and_deleted_live_match_block_extension_without_writes(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'blocked-extension.db'}") as server:
        repo, _, head, played = saved_bracket(server, RunCalendar(52, 1, 2030, 2))
        old = repo.get_branch_revision_state(branch_id="branch")
        p = proposal(head, played["fingerprint"], 52)
        status, review = _request("POST", base(server) + "/awards/review", p)
        assert status == 200, review
        command = {
            "command_id": "pending-awards", "proposal": p,
            "expected_preview_fingerprint": review["preview_fingerprint"],
            "explicit_confirmation": True,
        }
        status, applied = _request("POST", base(server) + "/awards/apply", command)
        assert status == 201, applied
        status, blocked = extension(server, 3)
        assert status == 200 and not blocked["can_save"], blocked
        assert "unsaved_live_state_differs_from_saved_head" in blocked["blockers"]
        assert extend(server, blocked)[0] == 409
        assert repo.get_branch_revision_state(branch_id="branch") == old
        assert repo.get_run_container(run_id="run").timeline_end_season == 2031
        with repo._session_factory() as session:
            assert session.scalar(select(RunCalendarExtensionReceiptModel.run_id)) is None
        # Exact play retry cannot discard the unsaved points or run RNG again.
        assert _request("POST", base(server) + "/simulate", played_command(played["knockout"])) == (
            201, played,
        )
        assert _request("GET", base(server))[1]["knockout_fingerprint"] == applied["fingerprint"]
        # A Saved bracket that vanishes from live storage is corruption, not
        # an empty no-op component that extension may silently preserve.
        with repo._session_factory.begin() as session:
            row = session.get(CalendarStandaloneMatchModel, ("run", "branch", "scoring-source"))
            session.delete(row)
        assert not extension(server, 3)[1]["can_save"]
        assert repo.verify_branch_saved_revision_hash(revision_id=head)


def test_saved_exhibition_can_extend_without_replaying_or_resigning(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'exhibition-extension.db'}") as server:
        repo, head = prepare_saved_world(server, RunCalendar(52, 1, 2030, 2))
        _, view = _request("GET", exhibition_base(server))
        status, played = _request("POST", exhibition_base(server) + "/simulate", {
            "command_id": "play", "match_id": "exhibition",
            "expected_saved_head": head,
            "expected_initial_world_fingerprint": view["initial_world_fingerprint"],
            "player_a_id": view["player_ids"][0], "player_b_id": view["player_ids"][1],
            "seed": 418, "operator_label": "Admin", "audit_reason": "Real exhibition",
        })
        assert status == 201, played
        assert not extension(server, 3)[1]["can_save"]
        _, preview = _request("GET", exhibition_base(server) + "/save/preview")
        status, saved = _request("POST", exhibition_base(server) + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_calendar_match_fingerprint": played["fingerprint"],
        })
        assert status == 201, saved
        _, review = extension(server, 3)
        assert review["can_save"], review
        assert extend(server, review)[0] == 200
        assert _request("GET", exhibition_base(server))[1]["match"] == played["match"]
        assert _request("GET", exhibition_base(server) + "/exhibition/replay")[1]["exact_replay"]
        assert repo.get_branch_saved_revision(revision_id=saved["saved_revision"]["revision_id"]).payload == saved["saved_revision"]["payload"]
