"""Official Ranking reuse keeps the exact preview, ranking and proof.

Component tests on a genuinely produced Saved v2 Run (``prepared_slots_v2``:
real HTTP/SQLite global slots, actual MatchEngine, two confirmed ranked
Editions, two Saved Week Transitions). The production Week Transition
candidate is compared with the same calculation with every new memo disabled
(the original full path), and a changed authority must still be rejected.
"""

import json

import pytest

from tests.api.test_calendar_global_slots import copy_database

pytestmark = pytest.mark.smoke


@pytest.fixture
def loaded(tmp_path, prepared_slots_v2):
    from sqlalchemy import text

    from beta_engine.api.deps import build_runtime
    from beta_engine.application.calendar_tour_service import (
        CalendarTourCommand,
        CalendarTourService,
    )
    from tests.api.test_calendar_tour_flow import command

    path = tmp_path / "ranking-reuse.db"
    copy_database(prepared_slots_v2, path)
    repository = build_runtime(database_url=f"sqlite:///{path}").repository
    service = CalendarTourService(repository)
    view = json.loads(json.dumps(service.inspect(run_id="run", branch_id="branch")))
    assert sum(a["result_confirmed"] for a in view["state"]["editions"]) == 2
    cmd = CalendarTourCommand.model_validate(command(view, "transition", name="ranking-reuse"))
    with repository._session_factory() as session:
        session.execute(text("BEGIN"))
        fingerprints = {}
        context = service._context(session, "run", "branch", _fingerprints=fingerprints)
        yield service, session, cmd, context, fingerprints


def _candidate(service, session, cmd, context, fingerprints):
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.domain.tournaments.calendar_global_slots import (
        _prime_private_fingerprint,
        global_replay_projection_scope,
    )

    with global_replay_projection_scope():
        for value, fingerprint in fingerprints.values():
            _prime_private_fingerprint(value, fingerprint)
        preview, *_, successor = service._prepare_from_context(
            session, "run", "branch", cmd, *context
        )
    body = json.loads(json.dumps(preview))
    return canonical_hash(body), body, successor.fingerprint


def _disable_new_memos(monkeypatch):
    from beta_engine.domain.players import calendar_native_ranking_bridge as bridge
    from beta_engine.domain.rankings import calendar_official
    from beta_engine.domain.tournaments import calendar_tour, ranking_snapshot_authority

    for module in (calendar_tour, ranking_snapshot_authority, calendar_official):
        monkeypatch.setattr(module, "identity_value", lambda value, name, compute: compute())
    monkeypatch.setattr(calendar_tour, "identity_values", lambda name, objects, compute, key=(): compute())
    assert bridge.validate_previous_ranking_owner  # the index itself is exact


def test_transition_candidate_is_identical_with_the_full_path(loaded, monkeypatch):
    reused = _candidate(*loaded)
    _disable_new_memos(monkeypatch)
    full = _candidate(*loaded)
    assert reused == full
    impact = reused[1]["impact"]
    ranking = impact["ranking"]
    assert ranking["rows"] and impact["ranking_adoption_fingerprint"]
    # Every confirmed Edition's sources enter the ranking input.
    counted = {r["edition_id"] for row in ranking["rows"] for r in row["counted_results"]}
    assert counted == {"parallel-a", "parallel-b"}


def test_a_replay_rebuilds_each_earlier_edition_once_and_rejects_changes(loaded, monkeypatch):
    from beta_engine.domain.tournaments import calendar_tour
    from beta_engine.domain.tournaments.calendar_global_slots import global_replay_projection_scope
    from beta_engine.domain.tournaments.calendar_native_tour_week import native_confirmed_results

    service, session, cmd, context, fingerprints = loaded
    ctx, state, _signed = context
    clock, checkpoint = ctx[0], ctx[4]
    target = clock.position_at_ordinal(checkpoint.week.ordinal + 1)
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition

    target = RunWeekPosition(calendar=clock, season_index=target.season_index, week=target.season_week)
    rebuilt = []
    original = calendar_tour.edition_results

    def counted(authority, event):
        rebuilt.append(authority.edition.edition_id)
        return original(authority, event)

    monkeypatch.setattr(calendar_tour, "edition_results", counted)
    full = native_confirmed_results(state, checkpoint, target, clock)
    assert len(rebuilt) == 2 and len(full) == 8  # two 4-player draws
    rebuilt.clear()
    with global_replay_projection_scope():
        for _week in range(5):  # each replayed later Week Transition
            assert native_confirmed_results(state, checkpoint, target, clock) == full
        assert sorted(rebuilt) == ["parallel-a", "parallel-b"]

        # A changed authority (a different played-tournament binding) is a new
        # object: it is rebuilt and rejected, never served from the memo.
        confirmed = [a for a in state.editions if a.result_confirmed]
        forged = confirmed[0].model_copy(update={"tournament_fingerprint": "0" * 64})
        changed = state.model_copy(update={"editions": tuple(
            forged if a is confirmed[0] else a for a in state.editions
        )})
        for _attempt in range(2):
            with pytest.raises(ValueError, match="detached from played MatchEngine"):
                native_confirmed_results(changed, checkpoint, target, clock)
    # Outside a private scope every call is the original full path.
    rebuilt.clear()
    assert native_confirmed_results(state, checkpoint, target, clock) == full
    assert len(rebuilt) == 2
