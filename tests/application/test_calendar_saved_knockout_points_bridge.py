"""Signed match and canonical point authority join, real Run-owned SQLite."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import sessionmaker

from beta_engine.application.calendar_saved_knockout_points_bridge import (
    preview_saved_slot_and_points_knockout_ranking,
    saved_slot_and_points_knockout_sources,
)
from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
)
from beta_engine.application.season_point_awards_service import FrozenPointAwardAuthority
from beta_engine.domain.rankings.calendar_official import CalendarRankingPlayer
from beta_engine.domain.rankings.official import OfficialRankingPolicy, RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)
from beta_engine.infrastructure.db.models import (
    OwnedTournamentRankingSourceModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.saved_revision_rankings import (
    capture_saved_ranking_component,
)
from tests.application.test_calendar_saved_match_knockout_bridge import (
    _resign_saved, _setup_real_completed_saved, _read, w,
)

pytestmark = pytest.mark.pr_critical
RUN, BRANCH, HEAD = "run", "branch", "revision"


def _complete_awards(factory, bracket, tournament, *, points=(100, 60, 30)):
    matches = (*tournament.semifinal_groups, tournament.final_group)
    champion = matches[-1].result.winner_player_id
    finalist = matches[-1].result.loser_player_id
    stages = {
        champion: "champion",
        finalist: "finalist",
        matches[0].result.loser_player_id: "semifinal",
        matches[1].result.loser_player_id: "semifinal",
    }
    count_wins = {p: 0 for p in stages}
    count_losses = {p: 0 for p in stages}
    canonical_matches = []
    for i, group in enumerate(matches):
        r = group.result
        count_wins[r.winner_player_id] += 1
        count_losses[r.loser_player_id] += 1
        canonical_matches.append(TournamentMatchResultAuthority(
            match_id=r.match_id,
            draw_type="main",
            round_number=1 if i < 2 else 2,
            bracket_position=(i + 1) if i < 2 else 1,
            winner_player_id=r.winner_player_id,
            loser_player_id=r.loser_player_id,
            scoreline=(
                f"{r.sets_won[r.winner_player_id]}-"
                f"{r.sets_won[r.loser_player_id]}"
            ),
            result_fingerprint=group.result_fingerprint,
        ))
    canonical_result = TournamentResultAuthority(
        run_id=RUN, branch_id=BRANCH, event_id=bracket.edition_id,
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="a"*64,
        match_package_fingerprint="b"*64,
        champion_player_id=champion, finalist_player_id=finalist,
        players=tuple(TournamentPlayerResultAuthority(
            player_id=p,draw_type="main",reached_stage=stages[p],
            wins=count_wins[p],losses=count_losses[p],
        ) for p in sorted(stages)),
        matches=tuple(canonical_matches),
    )
    table = {"champion": points[0], "finalist": points[1], "semifinal": points[2]}
    canonical_awards = build_tournament_point_award_authority(
        result=canonical_result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution=table,
            point_distribution_source="authored:signed-main-point-table",
        ),
        seed=9321,
    )
    binding = TournamentRankingBinding(
        run_id=RUN, branch_id=BRANCH,
        edition_id=bracket.edition_id,event_id=bracket.edition_id,
        completed_week=RankingWeek(season_index=0,week=1),
        first_publication_week=RankingWeek(season_index=0,week=2),
        validity_weeks=61,ranking_status="ranked",
        expected_result_fingerprint=canonical_result.fingerprint,
        expected_award_fingerprint=canonical_awards.fingerprint,
    )
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v4",
        binding=binding,canonical_result=canonical_result,
        canonical_awards=canonical_awards,
        adopted_by_command_id="saved-close-points",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )
    with factory.begin() as session:
        OwnedTournamentRankingSourceStore(session).append(source)
        _resign_saved(
            session, lambda p: capture_saved_ranking_component(
                session,p,run_id=RUN,branch_id=BRANCH,
            ),
        )
    # The test fixture's authored table is identical to the signed canonical
    # point authority, and provides only bracket geometry to the read service.
    return bracket.model_copy(update={
        "validity_weeks":61,
        "point_distribution":tuple(sorted(table.items())),
        "point_distribution_source":"authored:signed-main-point-table",
    }), source


def _read_combined(factory, bracket, **overrides):
    with factory() as session:
        session.connection().exec_driver_sql("BEGIN")
        args=dict(bracket=bracket,expected_saved_head_revision_id=HEAD)
        args.update(overrides)
        return saved_slot_and_points_knockout_sources(session,**args)


def test_real_saved_match_and_canonical_points_replay_at_same_immutable_head(tmp_path):
    engine,factory,repo,bracket,tournament=_setup_real_completed_saved(tmp_path)
    try:
        bracket,owned=_complete_awards(factory,bracket,tournament)
        before=repo.get_branch_revision_state(branch_id=BRANCH)
        rows, manifest=_read_combined(factory,bracket)
        assert len(rows)==4
        assert manifest.saved_tournament_source_fingerprint==owned.fingerprint
        assert manifest.saved_point_award_fingerprint==owned.canonical_awards.fingerprint
        assert {v.result.source_fingerprint for v in rows}=={manifest.fingerprint}
        assert sorted(v.result.main_points for v in rows)==[30,30,60,100]
        assert {v.result.validity_weeks for v in rows}=={61}
        engine.dispose()
        from sqlalchemy import create_engine
        reopened=create_engine(f"sqlite:///{tmp_path / 'real-slots.db'}")
        try:
            with sessionmaker(bind=reopened)() as session:
                session.connection().exec_driver_sql("BEGIN")
                snapshot, resolved, after=preview_saved_slot_and_points_knockout_ranking(
                    session, bracket=bracket,
                    expected_saved_head_revision_id=HEAD, week=w(0,2),
                    policy=OfficialRankingPolicy(policy_id="signed-top4",best_n=4),
                    players=tuple(CalendarRankingPlayer(
                        player_id=p,tie_break_token=p,tour_entry_week=w(0,1),
                    ) for p in ("a","b","c","d")),
                )
                assert after==manifest
                assert sorted(r.points for r in snapshot.rows)==[30,30,60,100]
                assert {r.source_fingerprint for r in resolved.results}=={manifest.fingerprint}
        finally:
            reopened.dispose()
        assert repo.get_branch_revision_state(branch_id=BRANCH)==before
        assert repo.verify_branch_saved_revision_hash(revision_id=HEAD)
    finally:
        engine.dispose()


@pytest.mark.parametrize("change,reason",[
    ("points","point distribution contradicts"),
    ("source","point distribution contradicts"),
    ("validity","timing or validity differs"),
    ("publication","timing or validity differs"),
])
def test_caller_cannot_rewrite_signed_point_policy_or_timing(tmp_path,change,reason):
    engine,factory,_,bracket,tournament=_setup_real_completed_saved(tmp_path)
    try:
        bracket,_=_complete_awards(factory,bracket,tournament)
        if change=="points":
            updates={"point_distribution":(("champion",101),("finalist",60),("semifinal",30))}
        elif change=="source":
            updates={"point_distribution_source":"authored:unapproved-new-points"}
        elif change=="validity":
            updates={"validity_weeks":62}
        else:
            updates={"first_publication_week":w(0,3)}
        with pytest.raises(ValueError,match=reason):
            _read_combined(factory,bracket.model_copy(update=updates))
    finally:
        engine.dispose()


def test_live_owned_point_receipt_must_equal_saved_canonical_authority(tmp_path):
    engine,factory,_,bracket,tournament=_setup_real_completed_saved(tmp_path)
    try:
        bracket,_=_complete_awards(factory,bracket,tournament)
        with factory.begin() as session:
            row=session.get(OwnedTournamentRankingSourceModel,(RUN,BRANCH,bracket.edition_id))
            row.source_fingerprint="f"*64
        with pytest.raises(ValueError,match="identity or fingerprint"):
            _read_combined(factory,bracket)
    finally:
        engine.dispose()


def test_missing_saved_point_component_fails_even_with_valid_saved_matches(tmp_path):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        with pytest.raises(ValueError,match="lacks a ranking preparation component"):
            _read_combined(factory,bracket)
    finally:
        engine.dispose()


def test_signed_canonical_result_cannot_forge_match_receipt(tmp_path):
    engine,factory,_,bracket,tournament=_setup_real_completed_saved(tmp_path)
    try:
        bracket,_=_complete_awards(factory,bracket,tournament)
        # Replacing one genuine matching Saved Slot source with a different
        # genuine independently signed canonical award authority is not enough.
        # Replacing the actual Saved Slot receipt would have to pass separate
        # immutable Simulation Slot component verification.
        bad=bracket.model_copy(update={
            "matches":(
                bracket.matches[0].model_copy(update={"scoreline":"3-0"}),
                *bracket.matches[1:],
            ),
        })
        with pytest.raises(ValueError,match="contradicts the knockout bracket"):
            _read_combined(factory,bad)
    finally:
        engine.dispose()
