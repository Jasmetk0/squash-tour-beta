"""Real SQLite unpublished calendar ranking source storage and safe replay."""

from __future__ import annotations

import pytest

from beta_engine.application.calendar_official_ranking_preview import (
    preview_calendar_official_ranking_from_sqlite_staging,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarDisciplinaryZero, CalendarRankingPlayer, CalendarRankingResult,
    CalendarRankingWeek,
)
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion, CalendarRankingZeroVersion,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db import (
    DatabaseSettings, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel, RunBranchModel, RunContainerModel,
    StagedCalendarRankingResultVersionModel,
    StagedCalendarRankingZeroVersionModel,
)
from beta_engine.infrastructure.db.staged_calendar_ranking_sources import (
    CalendarRankingStagingConflict, StagedCalendarRankingSourceStore,
)

from tests.application.test_run_calendar_read_authority import _setup, _signed_test_calendar

pytestmark = pytest.mark.pr_critical
RUN, BRANCH, HEAD = "run-1", "branch-1", "revision-1"


def w(s: int, n: int) -> CalendarRankingWeek:
    return CalendarRankingWeek(season_index=s, week=n)


def rv(W: int, *, pts=75, after=None, at=None, edition="event") -> CalendarRankingResultVersion:
    return CalendarRankingResultVersion(
        run_id=RUN, branch_id=BRANCH,
        effective_week=at or w(0, W),
        previous_fingerprint=after.fingerprint if after else None,
        result=CalendarRankingResult(
            edition_id=edition, player_id="p", source_fingerprint="trusted-event",
            completed_week=w(0, W-1), first_publication_week=w(0, W),
            main_points=pts,
        ),
    )


def zv(*, W: int, duration=2, after=None, at=None):
    return CalendarRankingZeroVersion(
        effective_week=at or w(1, 1),
        previous_fingerprint=after.fingerprint if after else None,
        zero=CalendarDisciplinaryZero(
            zero_id="sanction", run_id=RUN, branch_id=BRANCH,
            player_id="p", source_fingerprint="trusted-sanction",
            effective_week=w(1, 1), duration_weeks=duration,
        ),
    )


def scope(*, week=None):
    args = dict(
        run_id=RUN, branch_id=BRANCH,
        expected_saved_head_revision_id=HEAD,
    )
    if week is not None:
        args["week"] = week
    return args


@pytest.mark.parametrize("W,O", [(52, 1), (61, 37), (80, 37)])
def test_sqlite_restart_corrected_result_zeros_real_saved_bridge_and_idempotency(tmp_path, W, O):
    engine, factory, repo = _setup(tmp_path)
    db_url = f"sqlite:///{tmp_path / 'calendar-authority.db'}"
    try:
        _signed_test_calendar(factory, RunCalendar(W, O, 2030, 3))
        original_saved = repo.get_branch_revision_state(branch_id=BRANCH)
        first = rv(W)
        correction = rv(W, pts=175, at=w(1, 1), after=first)
        zero = zv(W=W)
        revised_zero = zv(W=W, duration=1, at=w(1, 2), after=zero)
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            store = StagedCalendarRankingSourceStore(session)
            assert store.append_result(first, expected_saved_head_revision_id=HEAD) == first
            assert store.append_result(first, expected_saved_head_revision_id=HEAD) == first
            assert store.append_result(correction, expected_saved_head_revision_id=HEAD) == correction
            assert store.append_zero(zero, expected_saved_head_revision_id=HEAD) == zero
            assert store.append_zero(revised_zero, expected_saved_head_revision_id=HEAD) == revised_zero
        # A new engine and Session must read the same independent staging rows.
        engine.dispose()
        restarted_engine = create_sqlite_engine(DatabaseSettings(url=db_url))
        restarted_factory = create_session_factory(restarted_engine)
        try:
            with restarted_factory() as session:
                session.connection().exec_driver_sql("BEGIN")
                store = StagedCalendarRankingSourceStore(session)
                results, zeros = store.history(**scope())
                assert results == (first, correction)
                assert zeros == (zero, revised_zero)
                earlier = store.resolve(**scope(week=w(0, W)))
                assert earlier.results[0].points == 75
                assert earlier.disciplinary_zeros == ()
                ranking, manifest = preview_calendar_official_ranking_from_sqlite_staging(
                    session, **scope(week=w(1, 1)),
                    policy=OfficialRankingPolicy(policy_id="Best 2", best_n=2),
                    players=(CalendarRankingPlayer(
                        player_id="p", tie_break_token="p",
                        tour_entry_week=w(0, 1),
                    ),),
                )
                assert ranking.rows[0].points == 175
                assert ranking.rows[0].disciplinary_zeros[0].zero_id == "sanction"
                assert manifest.results[0].main_points == 175
                later = store.resolve(**scope(week=w(1, 2)))
                assert later.disciplinary_zeros[0].duration_weeks == 1
                # Preview replay remains read-only.
                assert store.history(**scope()) == (results, zeros)
        finally:
            restarted_engine.dispose()
        assert repo.get_branch_revision_state(branch_id=BRANCH) == original_saved
        assert repo.verify_branch_saved_revision_hash(revision_id=HEAD)
    finally:
        engine.dispose()


def test_atomic_rollback_rejects_bad_correction_and_conflicting_retry(tmp_path):
    engine, factory, _ = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar.earth_default(start_year=2030, season_count=3))
        first = rv(52)
        with pytest.raises(ValueError, match="lineage"):
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                store = StagedCalendarRankingSourceStore(session)
                store.append_result(first, expected_saved_head_revision_id=HEAD)
                bogus = rv(52, pts=150, after=first, at=w(1, 1)).model_copy(
                    update={"previous_fingerprint": "a" * 64}
                )
                store.append_result(bogus, expected_saved_head_revision_id=HEAD)
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            assert StagedCalendarRankingSourceStore(session).history(**scope()) == ((), ())
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            StagedCalendarRankingSourceStore(session).append_result(
                first, expected_saved_head_revision_id=HEAD,
            )
        with pytest.raises(CalendarRankingStagingConflict, match="Conflicting"):
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                StagedCalendarRankingSourceStore(session).append_result(
                    rv(52, pts=90), expected_saved_head_revision_id=HEAD,
                )
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            results, _ = StagedCalendarRankingSourceStore(session).history(**scope())
            assert results == (first,)
    finally:
        engine.dispose()


def test_corrupted_sqlite_row_hash_and_missing_chain_refuse_to_replay(tmp_path):
    engine, factory, _ = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(52, 1, 2030, 3))
        original = rv(52)
        correction = rv(52, pts=150, after=original, at=w(1, 1))
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            store = StagedCalendarRankingSourceStore(session)
            store.append_result(original, expected_saved_head_revision_id=HEAD)
            store.append_result(correction, expected_saved_head_revision_id=HEAD)
        with factory.begin() as session:
            row = session.get(StagedCalendarRankingResultVersionModel, (
                RUN, BRANCH, "event", "p", 51,
            ))
            row.fingerprint = "f" * 64
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            with pytest.raises(ValueError, match="identity/hash"):
                StagedCalendarRankingSourceStore(session).resolve(**scope(week=w(1, 2)))
        with factory.begin() as session:
            session.get(StagedCalendarRankingResultVersionModel, (
                RUN, BRANCH, "event", "p", 51,
            )).fingerprint = original.fingerprint
            session.delete(session.get(StagedCalendarRankingResultVersionModel, (
                RUN, BRANCH, "event", "p", 51,
            )))
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            with pytest.raises(ValueError, match="publication origin"):
                StagedCalendarRankingSourceStore(session).history(**scope())
    finally:
        engine.dispose()


def test_stale_head_read_only_fork_and_published_world_are_fenced(tmp_path):
    engine, factory, _ = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(80, 37, 2030, 3))
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            with pytest.raises(ValueError, match="stale Saved HEAD"):
                StagedCalendarRankingSourceStore(session).history(
                    run_id=RUN, branch_id=BRANCH,
                    expected_saved_head_revision_id="old-head",
                )
        with factory.begin() as session:
            session.get(RunContainerModel, RUN).read_only = 1
        with pytest.raises(ValueError, match="read-only"):
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                StagedCalendarRankingSourceStore(session).append_result(
                    rv(80), expected_saved_head_revision_id=HEAD,
                )
        with factory.begin() as session:
            session.get(RunContainerModel, RUN).read_only = 0
            session.get(RunBranchModel, BRANCH).forked_from_branch_id = "parent"
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            with pytest.raises(ValueError, match="Forked"):
                StagedCalendarRankingSourceStore(session).history(**scope())
        with factory.begin() as session:
            session.get(RunBranchModel, BRANCH).forked_from_branch_id = None
            session.add(AuthoritativeWorldStateModel(
                run_id=RUN, branch_id=BRANCH, current_ordinal=0,
                ranking_fingerprint="c" * 64,
            ))
        with pytest.raises(ValueError, match="Published sporting state"):
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                StagedCalendarRankingSourceStore(session).append_result(
                    rv(80), expected_saved_head_revision_id=HEAD,
                )
    finally:
        engine.dispose()


def test_previous_staging_replays_after_strict_horizon_extension(tmp_path):
    engine, factory, _ = _setup(tmp_path)
    try:
        clock = RunCalendar(52, 1, 2030, 2)
        _signed_test_calendar(factory, clock)
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            StagedCalendarRankingSourceStore(session).append_result(
                rv(52), expected_saved_head_revision_id=HEAD,
            )
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            before = StagedCalendarRankingSourceStore(session).resolve(
                **scope(week=w(1, 1)),
            )
        # Fixture-only replacement of a signed Run/Saved clock; production uses
        # its audited multi-Branch extension command and creates new revisions.
        _signed_test_calendar(factory, clock.extend_to(4))
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            after = StagedCalendarRankingSourceStore(session).resolve(
                **scope(week=w(1, 1)),
            )
            assert after == before
            assert after.source_fingerprint == before.source_fingerprint
    finally:
        engine.dispose()


def test_calendar_staging_requires_a_physical_sqlite_transaction(tmp_path):
    engine, factory, _ = _setup(tmp_path)
    try:
        with factory() as session:
            with pytest.raises(ValueError, match="caller transaction"):
                StagedCalendarRankingSourceStore(session).history(**scope())
    finally:
        engine.dispose()
