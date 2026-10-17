"""Real MatchEngine rally logs -> W52/61/80 immutable source, SQLite and candidate."""

from __future__ import annotations

import hashlib
import json

import pytest

from beta_engine.application.calendar_engine_knockout_staging import (
    stage_calendar_engine_knockout_results,
)
from beta_engine.application.calendar_official_ranking_preview import (
    preview_calendar_official_ranking_from_sqlite_staging,
)
from beta_engine.core import DeterministicRng
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.matches import MatchEngine
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer, CalendarRankingWeek,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_knockout_engine_witness import (
    CalendarEngineMatchWitness,
    CalendarEngineKnockoutEvidence,
    prepare_calendar_engine_knockout_versions,
)
from beta_engine.domain.tournaments.calendar_knockout_ranking_evidence import (
    CalendarKnockoutMatch,
    CalendarKnockoutRankingEvidence,
)
from beta_engine.infrastructure.db.staged_calendar_ranking_sources import (
    CalendarRankingStagingConflict,
    StagedCalendarRankingSourceStore,
)
from tests.application.test_run_calendar_read_authority import (
    _setup, _signed_test_calendar,
)
from tests.domain.test_match_engine import _context, _player


pytestmark = pytest.mark.pr_critical
RUN, BRANCH, HEAD = "run-1", "branch-1", "revision-1"


def w(season_index: int, week: int) -> CalendarRankingWeek:
    return CalendarRankingWeek(season_index=season_index, week=week)


def _hash(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def _engine_evidence(clock: RunCalendar) -> CalendarEngineKnockoutEvidence:
    """Play all three matches with the actual seeded rally-by-rally MatchEngine."""
    entrants = ("A", "B", "C", "D")
    games = []
    for match_id, players, seed in (
        ("semi-1", entrants[:2], 1101),
        ("semi-2", entrants[2:], 1102),
    ):
        games.append(MatchEngine(rng=DeterministicRng(seed)).simulate(
            _context(match_id, *(
                _player(player_id=pid, base=84 - entrants.index(pid))
                for pid in players
            ))
        ))
    finalist_ids = tuple(game.winner_player_id for game in games)
    games.append(MatchEngine(rng=DeterministicRng(1103)).simulate(
        _context(
            "final",
            *(_player(player_id=pid, base=84 - entrants.index(pid))
              for pid in finalist_ids),
        )
    ))
    witnesses = []
    matches = []
    for i, result in enumerate(games):
        input_fp = _hash({"frozen_engine_input": result.match_id})
        receipt_fp = _hash({
            "input": input_fp,
            "result": result.model_dump(mode="json"),
        })
        witnesses.append(CalendarEngineMatchWitness(
            match_input_fingerprint=input_fp,
            authoritative_result_fingerprint=receipt_fp,
            result=result,
        ))
        matches.append(CalendarKnockoutMatch(
            match_id=result.match_id,
            round_number=1 if i < 2 else 2,
            bracket_position=i + 1 if i < 2 else 1,
            winner_player_id=result.winner_player_id,
            loser_player_id=result.loser_player_id,
            scoreline=(
                f"{result.sets_won[result.winner_player_id]}-"
                f"{result.sets_won[result.loser_player_id]}"
            ),
        ))
    nxt = clock.advance_weeks(0, clock.weeks_per_year, 1)
    bracket = CalendarKnockoutRankingEvidence(
        run_id=RUN, branch_id=BRANCH, edition_id="engine-open",
        run_calendar=clock.to_metadata(),
        completed_week=w(0, clock.weeks_per_year),
        first_publication_week=w(nxt.season_index, nxt.season_week),
        entrants_by_bracket_position=entrants,
        matches=tuple(matches),
        point_distribution=(
            ("champion", 100), ("finalist", 60), ("semifinal", 30),
        ),
        point_distribution_source="authored:engine-test-points",
    )
    return CalendarEngineKnockoutEvidence(
        bracket=bracket, witnesses=tuple(witnesses),
    )


@pytest.mark.parametrize("W,offset", [(52, 1), (61, 37), (80, 37)])
def test_real_match_engine_logs_staged_and_replayed_across_season_and_restart(
    tmp_path, W, offset,
):
    clock=RunCalendar(W,offset,2030,3)
    engine,factory,repository=_setup(tmp_path)
    try:
        _signed_test_calendar(factory,clock)
        evidence=_engine_evidence(clock)
        saved_before=repository.get_branch_revision_state(branch_id=BRANCH)
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            versions=stage_calendar_engine_knockout_results(
                session,evidence=evidence,
                expected_evidence_fingerprint=evidence.fingerprint,
                expected_saved_head_revision_id=HEAD,
            )
            assert len(versions)==4
            assert {v.result.source_fingerprint for v in versions}=={
                evidence.fingerprint,
            }
            assert stage_calendar_engine_knockout_results(
                session,evidence=evidence,
                expected_evidence_fingerprint=evidence.fingerprint,
                expected_saved_head_revision_id=HEAD,
            )==versions
        engine.dispose()
        from beta_engine.infrastructure.db import (
            DatabaseSettings,create_session_factory,create_sqlite_engine,
        )
        reopened=create_sqlite_engine(DatabaseSettings(
            url=f"sqlite:///{tmp_path / 'calendar-authority.db'}",
        ))
        try:
            with create_session_factory(reopened)() as session:
                session.connection().exec_driver_sql("BEGIN")
                store=StagedCalendarRankingSourceStore(session)
                assert store.history(
                    run_id=RUN,branch_id=BRANCH,
                    expected_saved_head_revision_id=HEAD,
                )==(versions,())
                assert store.resolve(
                    run_id=RUN,branch_id=BRANCH,
                    expected_saved_head_revision_id=HEAD,
                    week=w(0,W),
                ).results==()
                snapshot,manifest=preview_calendar_official_ranking_from_sqlite_staging(
                    session,run_id=RUN,branch_id=BRANCH,
                    expected_saved_head_revision_id=HEAD,
                    week=w(1,1),
                    policy=OfficialRankingPolicy(policy_id="best4",best_n=4),
                    players=tuple(
                        CalendarRankingPlayer(
                            player_id=player,tie_break_token=player,
                            tour_entry_week=w(0,1),
                        ) for player in evidence.bracket.entrants_by_bracket_position
                    ),
                )
                assert snapshot.rows[0].points==100
                assert sorted(row.points for row in snapshot.rows)==[30,30,60,100]
                assert {r.source_fingerprint for r in manifest.results}=={
                    evidence.fingerprint,
                }
        finally:
            reopened.dispose()
        assert repository.get_branch_revision_state(branch_id=BRANCH)==saved_before
        assert repository.verify_branch_saved_revision_hash(revision_id=HEAD)
    finally:
        engine.dispose()


def test_witness_rejects_changed_match_result_and_receipt_and_wrong_bracket():
    clock=RunCalendar(52,1,2030,3)
    valid=_engine_evidence(clock)
    assert len(prepare_calendar_engine_knockout_versions(
        valid,run_calendar=clock,expected_evidence_fingerprint=valid.fingerprint,
    ))==4
    with pytest.raises(ValueError,match="fingerprint mismatch"):
        prepare_calendar_engine_knockout_versions(
            valid,run_calendar=clock,expected_evidence_fingerprint="f"*64,
        )
    with pytest.raises(ValueError,match="Run calendar mismatch"):
        prepare_calendar_engine_knockout_versions(
            valid,run_calendar=RunCalendar(80,37,2030,3),
            expected_evidence_fingerprint=valid.fingerprint,
        )
    first=valid.witnesses[0]
    wrong=first.model_copy(update={
        "authoritative_result_fingerprint":"a"*64,
    })
    with pytest.raises(ValueError,match="receipt fingerprint mismatch"):
        CalendarEngineKnockoutEvidence.model_validate_json(
            valid.model_copy(update={
                "witnesses":(wrong,*valid.witnesses[1:]),
            }).model_dump_json()
        )
    bad_result=first.result.model_copy(update={
        "winner_player_id":first.result.loser_player_id,
        "loser_player_id":first.result.winner_player_id,
    })
    with pytest.raises(ValueError,match="winner disagrees"):
        CalendarEngineMatchWitness.model_validate_json(
            first.model_copy(update={"result":bad_result}).model_dump_json()
        )
    invalid_bracket=valid.bracket.model_copy(update={
        "matches":(
            valid.bracket.matches[0].model_copy(update={"scoreline":"3-0"}),
            *valid.bracket.matches[1:],
        ),
    })
    with pytest.raises(ValueError,match="contradicts the knockout bracket"):
        CalendarEngineKnockoutEvidence.model_validate_json(
            valid.model_copy(update={"bracket":invalid_bracket}).model_dump_json()
        )


def test_missing_engine_log_retirement_and_extra_result_are_rejected():
    clock=RunCalendar(52,1,2030,3)
    valid=_engine_evidence(clock)
    original=valid.witnesses[0]
    with pytest.raises(ValueError,match="rally-logged"):
        CalendarEngineMatchWitness.model_validate_json(
            original.model_copy(update={
                "result": original.result.model_copy(update={
                    "rally_log":None,
                    "timeline_log":None,
                    "stamina_log":None,
                }),
            }).model_dump_json()
        )
    with pytest.raises(ValueError,match="rally-logged"):
        CalendarEngineMatchWitness.model_validate_json(
            original.model_copy(update={
                "result": original.result.model_copy(update={
                    "termination_reason":"RETIREMENT",
                }),
            }).model_dump_json()
        )
    with pytest.raises(ValueError,match="cover every bracket"):
        CalendarEngineKnockoutEvidence.model_validate_json(
            valid.model_copy(update={
                "witnesses":(*valid.witnesses,valid.witnesses[0]),
            }).model_dump_json()
        )


def test_mixed_source_or_partial_edition_never_silently_merges(tmp_path):
    clock=RunCalendar(80,37,2030,3)
    engine,factory,_=_setup(tmp_path)
    try:
        _signed_test_calendar(factory,clock)
        proof=_engine_evidence(clock)
        versions=prepare_calendar_engine_knockout_versions(
            proof,run_calendar=clock,expected_evidence_fingerprint=proof.fingerprint,
        )
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            StagedCalendarRankingSourceStore(session).append_result(
                versions[0],expected_saved_head_revision_id=HEAD,
            )
        with pytest.raises(CalendarRankingStagingConflict,match="partial"):
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                stage_calendar_engine_knockout_results(
                    session,evidence=proof,
                    expected_evidence_fingerprint=proof.fingerprint,
                    expected_saved_head_revision_id=HEAD,
                )
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            saved,_=StagedCalendarRankingSourceStore(session).history(
                run_id=RUN,branch_id=BRANCH,
                expected_saved_head_revision_id=HEAD,
            )
            assert saved==(versions[0],)
    finally:
        engine.dispose()


def test_legacy_v1_knockout_staging_remains_byte_identical_after_shared_helper(tmp_path):
    """This PR refactors the original staging command; guard that path as well."""
    from beta_engine.application.calendar_knockout_staging import (
        stage_calendar_knockout_ranking_results,
    )
    from tests.application.test_calendar_knockout_staging import ev
    clock = RunCalendar(52, 1, 2030, 3)
    engine, factory, _ = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, clock)
        original = ev(clock)
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            store = StagedCalendarRankingSourceStore(session)
            saved = stage_calendar_knockout_ranking_results(
                session, evidence=original,
                expected_evidence_fingerprint=original.fingerprint,
                expected_saved_head_revision_id=HEAD,
            )
            assert len(saved) == 4
            assert stage_calendar_knockout_ranking_results(
                session, evidence=original,
                expected_evidence_fingerprint=original.fingerprint,
                expected_saved_head_revision_id=HEAD,
            ) == saved
            actual, zeros = store.history(
                run_id=RUN, branch_id=BRANCH,
                expected_saved_head_revision_id=HEAD,
            )
            assert actual == saved and zeros == ()
            assert {v.result.source_fingerprint for v in actual} == {
                original.fingerprint,
            }
    finally:
        engine.dispose()
