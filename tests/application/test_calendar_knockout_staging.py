"""Calendar-native main-only knockout results through real SQLite ranking preview."""

from __future__ import annotations

import pytest

from beta_engine.application.calendar_knockout_staging import (
    stage_calendar_knockout_ranking_results,
)
from beta_engine.application.calendar_official_ranking_preview import (
    preview_calendar_official_ranking_from_sqlite_staging,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer, CalendarRankingWeek,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_knockout_ranking_evidence import (
    CalendarKnockoutMatch,
    CalendarKnockoutRankingEvidence,
    prepare_calendar_knockout_ranking_versions,
)
from beta_engine.infrastructure.db.staged_calendar_ranking_sources import (
    CalendarRankingStagingConflict, StagedCalendarRankingSourceStore,
)
from tests.application.test_run_calendar_read_authority import (
    _setup, _signed_test_calendar,
)


pytestmark = pytest.mark.pr_critical
RUN, BRANCH, HEAD = "run-1", "branch-1", "revision-1"


def w(s, week):
    return CalendarRankingWeek(season_index=s, week=week)


def ev(clock: RunCalendar, *, draw=4, name="open", finish=None):
    entrants = tuple("ABCDEFGH"[:draw])
    assert draw in {4, 8}
    matches = []
    # Fixed fictional *explicit completed* draw facts; never simulated by adapter.
    winners = list(entrants)
    round_no = 0
    while len(winners) > 1:
        round_no += 1
        new = []
        for pos in range(0, len(winners), 2):
            left, right = winners[pos:pos+2]
            matches.append(CalendarKnockoutMatch(
                match_id=f"match-{round_no}-{pos // 2 + 1}",
                round_number=round_no,
                bracket_position=pos // 2 + 1,
                winner_player_id=left,
                loser_player_id=right,
                scoreline="3-1",
            ))
            new.append(left)
        winners = new
    dist = [
        ("champion", 100),
        ("finalist", 60),
        ("semifinal", 30),
    ]
    if draw == 8:
        dist.append(("quarterfinal", 15))
    completed = finish or w(0, clock.weeks_per_year)
    publication = clock.advance_weeks(
        completed.season_index, completed.week, 1,
    )
    return CalendarKnockoutRankingEvidence(
        run_id=RUN, branch_id=BRANCH, edition_id=name,
        run_calendar=clock.to_metadata(),
        completed_week=completed,
        first_publication_week=w(
            publication.season_index, publication.season_week,
        ),
        entrants_by_bracket_position=entrants,
        matches=tuple(matches),
        point_distribution=tuple(sorted(dist)),
        point_distribution_source="authored:test-event-points",
    )


@pytest.mark.parametrize("W,offset,draw", [
    (52, 1, 4), (61, 37, 8), (80, 37, 4),
])
def test_real_saved_sqlite_full_draw_w_to_next_season_ranking_and_restart(
    tmp_path, W, offset, draw,
):
    clock = RunCalendar(W, offset, 2030, 3)
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, clock)
        proof = ev(clock, draw=draw)
        before = repo.get_branch_revision_state(branch_id=BRANCH)
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            versions = stage_calendar_knockout_ranking_results(
                session, evidence=proof,
                expected_evidence_fingerprint=proof.fingerprint,
                expected_saved_head_revision_id=HEAD,
            )
            assert len(versions) == draw
            assert stage_calendar_knockout_ranking_results(
                session, evidence=proof,
                expected_evidence_fingerprint=proof.fingerprint,
                expected_saved_head_revision_id=HEAD,
            ) == versions
        engine.dispose()
        from beta_engine.infrastructure.db import (
            DatabaseSettings, create_session_factory, create_sqlite_engine,
        )
        opened = create_sqlite_engine(DatabaseSettings(
            url=f"sqlite:///{tmp_path / 'calendar-authority.db'}",
        ))
        try:
            new_factory = create_session_factory(opened)
            with new_factory() as session:
                session.connection().exec_driver_sql("BEGIN")
                store = StagedCalendarRankingSourceStore(session)
                results, zeros = store.history(
                    run_id=RUN, branch_id=BRANCH,
                    expected_saved_head_revision_id=HEAD,
                )
                assert results == versions and zeros == ()
                earlier = store.resolve(
                    run_id=RUN, branch_id=BRANCH,
                    expected_saved_head_revision_id=HEAD, week=w(0, W),
                )
                assert earlier.results == ()
                candidate, manifest = preview_calendar_official_ranking_from_sqlite_staging(
                    session, run_id=RUN, branch_id=BRANCH,
                    expected_saved_head_revision_id=HEAD,
                    week=w(1, 1),
                    policy=OfficialRankingPolicy(policy_id="Best 4", best_n=4),
                    players=tuple(
                        CalendarRankingPlayer(
                            player_id=player, tie_break_token=player,
                            tour_entry_week=w(0, 1),
                        )
                        for player in proof.entrants_by_bracket_position
                    ),
                )
                table = {r.player_id:r.points for r in candidate.rows}
                assert table["A"] == 100
                assert table["C"] == (30 if draw == 8 else 60)
                if draw == 8:
                    assert table["B"] == 15
                    assert table["D"] == 15
                    assert table["E"] == 60
                    assert table["G"] == 30
                else:
                    assert table["B"] == 30
                    assert table["D"] == 30
                assert len(manifest.results) == draw
                assert {r.source_fingerprint for r in manifest.results} == {
                    proof.fingerprint,
                }
        finally:
            opened.dispose()
        assert repo.get_branch_revision_state(branch_id=BRANCH) == before
        assert repo.verify_branch_saved_revision_hash(revision_id=HEAD)
    finally:
        engine.dispose()


@pytest.mark.parametrize("change,error", [
    ("skip_match", "exact complete match tree"),
    ("extra_match", "exact complete match tree"),
    ("bad_winner", "invalid progression"),
    ("wrong_position", "invalid progression"),
    ("wrong_round", "invalid progression"),
    ("reused_match_id", "Duplicate knockout match"),
    ("walkover", "dedicated result authority"),
    ("unknown_point_stage", "exactly cover"),
    ("missing_stage", "exactly cover"),
    ("negative_points", "exactly cover"),
    ("reused_player", "unique, complete"),
])
def test_rejects_incomplete_fabricated_or_badly_scored_draw(change,error):
    clock = RunCalendar(52, 1, 2030, 3)
    proof = ev(clock)
    updates={}
    match=list(proof.matches)
    if change == "skip_match": updates["matches"] = tuple(match[:-1])
    if change == "extra_match": updates["matches"] = (*match,match[-1])
    if change == "bad_winner":
        match[0] = match[0].model_copy(update={"winner_player_id":"X"})
        updates["matches"] = tuple(match)
    if change == "wrong_position":
        match[0] = match[0].model_copy(update={"bracket_position":2})
        updates["matches"] = tuple(match)
    if change == "wrong_round":
        match[0] = match[0].model_copy(update={"round_number":2})
        updates["matches"] = tuple(match)
    if change == "reused_match_id":
        match[1] = match[1].model_copy(update={"match_id":match[0].match_id})
        updates["matches"] = tuple(match)
    if change == "walkover":
        match[1] = match[1].model_copy(update={"scoreline":"W/O"})
        updates["matches"] = tuple(match)
    if change == "unknown_point_stage":
        updates["point_distribution"] = (*proof.point_distribution,("mystery",4))
    if change == "missing_stage":
        updates["point_distribution"] = proof.point_distribution[:-1]
    if change == "negative_points":
        updates["point_distribution"] = (("champion",-1), *proof.point_distribution[1:])
    if change == "reused_player":
        updates["entrants_by_bracket_position"] = ("A","B","C","A")
    raw = proof.model_copy(update=updates)
    with pytest.raises(ValueError, match=error):
        prepare_calendar_knockout_ranking_versions(
            raw, run_calendar=clock,
            expected_evidence_fingerprint=proof.fingerprint,
        )


def test_fingerprint_clock_and_strict_publication_boundaries():
    clock = RunCalendar(80, 37, 2030, 3)
    proof = ev(clock)
    for expected, calendar, error in (
        ("a" * 64, clock, "fingerprint mismatch"),
        (proof.fingerprint, RunCalendar(52, 1, 2030, 3), "Run calendar mismatch"),
        ("not-hex", clock, "External knockout evidence fingerprint"),
    ):
        with pytest.raises(ValueError, match=error):
            prepare_calendar_knockout_ranking_versions(
                proof, run_calendar=calendar,
                expected_evidence_fingerprint=expected,
            )
    with pytest.raises(ValueError, match="publication must be after"):
        CalendarKnockoutRankingEvidence.model_validate_json(
            proof.model_copy(
                update={"first_publication_week": w(0, 80)}
            ).model_dump_json()
        )


def test_whole_edition_rejects_partial_storage_and_concurrent_changed_batch(tmp_path):
    clock = RunCalendar(52, 1, 2030, 3)
    engine, factory, _ = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, clock)
        proof = ev(clock)
        versions = prepare_calendar_knockout_ranking_versions(
            proof,run_calendar=clock,expected_evidence_fingerprint=proof.fingerprint,
        )
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            StagedCalendarRankingSourceStore(session).append_result(
                versions[0], expected_saved_head_revision_id=HEAD,
            )
        with pytest.raises(CalendarRankingStagingConflict, match="partial"):
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                stage_calendar_knockout_ranking_results(
                    session,evidence=proof,expected_evidence_fingerprint=proof.fingerprint,
                    expected_saved_head_revision_id=HEAD,
                )
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            rows,_=StagedCalendarRankingSourceStore(session).history(
                run_id=RUN,branch_id=BRANCH,expected_saved_head_revision_id=HEAD,
            )
            assert rows == (versions[0],)
    finally:
        engine.dispose()


def test_whole_edition_injected_mid_batch_failure_rolls_back_all(tmp_path,monkeypatch):
    clock=RunCalendar(52,1,2030,3)
    engine,factory,_=_setup(tmp_path)
    try:
        _signed_test_calendar(factory,clock)
        proof=ev(clock)
        original=StagedCalendarRankingSourceStore.append_result
        hits=[]
        def interrupted(self,version,*,expected_saved_head_revision_id):
            hits.append(version.result.player_id)
            if len(hits)==3:
                raise RuntimeError("injected complete-edition failure")
            return original(self,version,expected_saved_head_revision_id=expected_saved_head_revision_id)
        monkeypatch.setattr(StagedCalendarRankingSourceStore,"append_result",interrupted)
        with pytest.raises(RuntimeError,match="injected"):
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                stage_calendar_knockout_ranking_results(
                    session,evidence=proof,expected_evidence_fingerprint=proof.fingerprint,
                    expected_saved_head_revision_id=HEAD,
                )
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            assert StagedCalendarRankingSourceStore(session).history(
                run_id=RUN,branch_id=BRANCH,expected_saved_head_revision_id=HEAD,
            ) == ((),())
        monkeypatch.setattr(StagedCalendarRankingSourceStore,"append_result",original)
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            assert len(stage_calendar_knockout_ranking_results(
                session,evidence=proof,expected_evidence_fingerprint=proof.fingerprint,
                expected_saved_head_revision_id=HEAD,
            ))==4
    finally:
        engine.dispose()


def test_staging_rejects_changed_clock_and_stale_saved_head(tmp_path):
    clock=RunCalendar(80,37,2030,3)
    engine,factory,_=_setup(tmp_path)
    try:
        _signed_test_calendar(factory,clock)
        proof=ev(clock)
        with pytest.raises(ValueError,match="stale Saved HEAD"):
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                stage_calendar_knockout_ranking_results(
                    session,evidence=proof,
                    expected_evidence_fingerprint=proof.fingerprint,
                    expected_saved_head_revision_id="old",
                )
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            foreign=ev(RunCalendar(52,1,2030,3))
            with pytest.raises(ValueError,match="Run calendar mismatch"):
                stage_calendar_knockout_ranking_results(
                    session,evidence=foreign,
                    expected_evidence_fingerprint=foreign.fingerprint,
                    expected_saved_head_revision_id=HEAD,
                )
    finally:
        engine.dispose()
