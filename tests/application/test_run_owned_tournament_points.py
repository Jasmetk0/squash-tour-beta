from __future__ import annotations

import hashlib
import json

import pytest

from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
    project_tournament_point_award_legacy_dto,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
)
from beta_engine.application.run_owned_match_package import (
    build_run_owned_match_package,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
)
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.prize_money_award_authority import (
    TournamentPrizeMoneyAwardAuthority,
    build_tournament_prize_money_award_authority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
    build_tournament_result_authority,
    project_tournament_result_legacy_dto,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import Base, RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner


pytestmark = pytest.mark.smoke


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'canonical-points.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Timeline 1",
            )
        )
    yield factory
    engine.dispose()


def _input():
    return TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input",
        draw_seed=4321,
        main_seed_count=1,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=("A", "B", "C", "D"),
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=("A",),
        qualification_seed_player_ids=(),
    )


def _event():
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="template",
        event_name="Canonical Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=4,
        qualification_draw_size=0,
        qualifier_spots=0,
    )


def _complete(draw, package):
    projected = package.model_copy(deep=True)
    slots = {slot.slot_index: slot for slot in draw.main.slots}
    winners = {}
    by_id = {match.match_id: match for match in projected.main_draw_matches}

    def resolve(source):
        if source.startswith("winner:"):
            return winners[source.removeprefix("winner:")]
        slot = slots[int(source.removeprefix("slot:"))]
        return slot.player_id

    for node in sorted(
        draw.main.nodes,
        key=lambda item: (item.round_number, item.round_sequence),
    ):
        top = resolve(node.source_top)
        bottom = resolve(node.source_bottom)
        winner = top
        loser = bottom
        match = by_id[node.node_id]
        match.top_player_id = top
        match.bottom_player_id = bottom
        match.winner_player_id = winner
        match.loser_player_id = loser
        match.scoreline = "3-0"
        match.status = "completed"
        match.result_fingerprint = hashlib.sha256(
            f"{node.node_id}|{winner}|{loser}".encode()
        ).hexdigest()
        winners[node.node_id] = winner
    return projected


def _authorities():
    week = RankingWeek(season_index=0, week=1)
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw",
    )
    package = build_run_owned_match_package(
        draw=draw,
        event=_event(),
        week=week,
    )
    package = _complete(draw, package)
    result_authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=week,
        draw=draw,
        package=package,
    )
    result = project_tournament_result_legacy_dto(
        authority=result_authority,
        event=_event(),
        package=package,
        seed=77,
    )
    frozen_points = FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
            "quarterfinal": 250,
            "round_of_16": 120,
            "round_of_32": 60,
            "round_of_64": 30,
            "round_of_128": 10,
            "qualification_winner": 25,
            "qualification_final": 10,
            "qualification_semifinal": 5,
            "qualification_round": 0,
            "main_draw_participant": 0,
            "unknown": 0,
        },
        point_distribution_source="calendar_event.ranking_points_table",
    )
    point_authority = build_tournament_point_award_authority(
        result=result_authority,
        point_authority=frozen_points,
        seed=88,
    )
    awards = project_tournament_point_award_legacy_dto(
        authority=point_authority,
        result_authority=result_authority,
        result=result,
    )
    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="event",
        event_id="event",
        completed_week=week,
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result_authority.fingerprint,
        expected_award_fingerprint=point_authority.fingerprint,
    )
    return result_authority, result, point_authority, awards, binding


def _walkover_authorities():
    week = RankingWeek(season_index=0, week=1)
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw-walkover-points",
    )
    package = build_run_owned_match_package(
        draw=draw,
        event=_event(),
        week=week,
    )
    package = _complete(draw, package)
    terminal_round = max(
        match.round_number for match in package.main_draw_matches
    )
    final = next(
        match
        for match in package.main_draw_matches
        if match.round_number == terminal_round
    )
    final.scoreline = "W/O"
    final.result_fingerprint = hashlib.sha256(
        (
            f"walkover-points|{final.match_id}|"
            f"{final.winner_player_id}|{final.loser_player_id}"
        ).encode()
    ).hexdigest()

    result = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=week,
        draw=draw,
        package=package,
    )
    points = FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
            "main_draw_participant": 0,
        },
        point_distribution_source="calendar_event.ranking_points_table",
    )
    awards = build_tournament_point_award_authority(
        result=result,
        point_authority=points,
        seed=188,
    )
    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="event",
        event_id="event",
        completed_week=week,
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.fingerprint,
        expected_award_fingerprint=awards.fingerprint,
    )
    return result, awards, binding, final


@pytest.mark.pr_critical
def test_withdrawn_q_winner_and_lucky_loser_survive_canonical_points_and_ranking(database):
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="A",
        finalist_player_id="B",
        qualification_winner_ids=("QW",),
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="main",
                reached_stage="champion",
                wins=2,
            ),
            TournamentPlayerResultAuthority(
                player_id="B",
                draw_type="main",
                reached_stage="finalist",
                wins=1,
                losses=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="C",
                draw_type="main",
                reached_stage="semifinal",
                losses=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="QW",
                draw_type="qualification",
                qualifier=True,
                reached_stage="qualification_winner",
                wins=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="LL",
                draw_type="both",
                qualifier=True,
                main_entry_status="lucky_loser",
                reached_stage="semifinal",
                losses=2,
            ),
        ),
        matches=(
            TournamentMatchResultAuthority(
                match_id="q-final",
                draw_type="qualification",
                round_number=1,
                bracket_position=1,
                winner_player_id="QW",
                loser_player_id="LL",
                scoreline="3-0",
                result_fingerprint="1" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="main-semi-1",
                draw_type="main",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="LL",
                scoreline="3-0",
                result_fingerprint="2" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="main-semi-2",
                draw_type="main",
                round_number=1,
                bracket_position=2,
                winner_player_id="B",
                loser_player_id="C",
                scoreline="3-0",
                result_fingerprint="3" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="main-final",
                draw_type="main",
                round_number=2,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="B",
                scoreline="3-0",
                result_fingerprint="4" * 64,
            ),
        ),
    )
    frozen_points = FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
            "qualification_winner": 150,
            "qualification_final": 100,
        },
        point_distribution_source="calendar_event.ranking_points_table",
    )
    point_authority = build_tournament_point_award_authority(
        result=result,
        point_authority=frozen_points,
        seed=812,
    )
    by_player = {
        award.player_id: award for award in point_authority.awards
    }

    # The withdrawn Q winner keeps the earned Qualification component even though
    # they never enter Main. The replacement LL keeps the Q-loser component plus
    # the actual Main finishing-stage component.
    assert by_player["QW"].point_stage is None
    assert by_player["QW"].ranking_points_awarded == 150
    assert by_player["QW"].race_points_awarded == 150

    assert by_player["LL"].qualification_point_stage == "qualification_final"
    assert by_player["LL"].qualification_points_awarded == 100
    assert by_player["LL"].ranking_points_awarded == 500
    assert by_player["LL"].race_points_awarded == 500

    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="event",
        event_id="event",
        completed_week=result.completed_week,
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.fingerprint,
        expected_award_fingerprint=point_authority.fingerprint,
    )
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v4",
        binding=binding,
        canonical_result=result,
        canonical_awards=point_authority,
        adopted_by_command_id="close-q-winner-ll-ranking",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )

    ranking_players = tuple(
        OfficialRankingPlayer(
            player_id=player.player_id,
            tie_break_token=player.player_id,
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player in result.players
    )
    policy = OfficialRankingPolicy(policy_id="policy")
    with database.begin() as session:
        OfficialRankingCandidateStore(session).append(
            calculate_official_ranking(
                run_id="run",
                branch_id="branch",
                week=result.completed_week,
                policy=policy,
                players=ranking_players,
                results=(),
            ),
            bootstrap=True,
        )
        OwnedTournamentRankingSourceStore(session).append(source)

    snapshot = RankingWeekCommandRunner(database, awards=None).execute(
        RankingWeekCommand(
            command_id="publish-q-winner-ll-ranking",
            tournaments=(binding,),
            context=RankingTransitionContext(
                run_id="run",
                branch_id="branch",
                completed_week=result.completed_week,
                target_week=binding.first_publication_week,
                policy=policy,
                players=ranking_players,
                discipline="none",
            ),
        )
    )
    published = {row.player_id: row.points for row in snapshot.rows}
    assert published["QW"] == 150
    assert published["LL"] == 500

    week_three = RankingWeekCommandRunner(database, awards=None).execute(
        RankingWeekCommand(
            command_id="publish-week-three-after-ll",
            tournaments=(),
            context=RankingTransitionContext(
                run_id="run",
                branch_id="branch",
                completed_week=snapshot.week,
                target_week=RankingWeek(season_index=0, week=3),
                policy=policy,
                players=ranking_players,
                discipline="none",
            ),
        )
    )
    assert week_three.week == RankingWeek(season_index=0, week=3)

    with database() as session:
        historical_sources = OwnedTournamentRankingSourceStore(session).history(
            run_id="run",
            branch_id="branch",
        )
    assert len(historical_sources) == 1
    historical = historical_sources[0]
    assert historical is not None
    assert historical.fingerprint == source.fingerprint
    assert historical.canonical_result is not None
    ll_history = next(
        player
        for player in historical.canonical_result.players
        if player.player_id == "LL"
    )
    assert ll_history.main_entry_status == "lucky_loser"
    assert ll_history.qualifier is True


@pytest.mark.pr_critical
def test_canonical_prize_money_authority_awards_actual_finishing_stages():
    result, _, _, _, _ = _authorities()
    event = _event().model_copy(
        update={
            "prize_money_currency": "EUR",
            "prize_money_table": {
                "semifinal": 3000,
                "finalist": 6000,
                "champion": 10000,
            },
        }
    )
    authority = build_tournament_prize_money_award_authority(
        result=result,
        event=event,
    )
    awards = {award.player_id: award for award in authority.awards}

    assert authority.configuration_status == "complete"
    assert authority.total_prize_pool_status == "complete"
    assert authority.total_prize_pool_amount == 22000
    assert authority.known_awarded_amount == 22000
    assert authority.unknown_award_count == 0
    assert awards[result.champion_player_id].amount == 10000
    assert awards[result.finalist_player_id].amount == 6000
    assert sum(
        1
        for award in authority.awards
        if award.reached_stage == "semifinal" and award.amount == 3000
    ) == 2


@pytest.mark.pr_critical
def test_canonical_prize_money_partial_table_keeps_unknown_and_pool_incomplete():
    result, _, _, _, _ = _authorities()
    event = _event().model_copy(
        update={
            "prize_money_currency": "USD",
            "prize_money_table": {
                "semifinal": None,
                "finalist": 6000,
                "champion": 10000,
            },
        }
    )
    authority = build_tournament_prize_money_award_authority(
        result=result,
        event=event,
    )

    semifinal_awards = [
        award for award in authority.awards if award.reached_stage == "semifinal"
    ]
    assert authority.configuration_status == "partial"
    assert authority.total_prize_pool_status == "incomplete"
    assert authority.total_prize_pool_amount is None
    assert authority.known_awarded_amount == 16000
    assert authority.unknown_award_count == 2
    assert all(award.payout_status == "unknown" for award in semifinal_awards)
    assert all(award.amount is None for award in semifinal_awards)


@pytest.mark.pr_critical
def test_canonical_walkover_prize_money_uses_stage_without_played_win():
    result, _, _, final = _walkover_authorities()
    event = _event().model_copy(
        update={
            "prize_money_currency": "GBP",
            "prize_money_table": {
                "semifinal": 3000,
                "finalist": 6000,
                "champion": 10000,
            },
        }
    )
    authority = build_tournament_prize_money_award_authority(
        result=result,
        event=event,
    )
    by_player = {player.player_id: player for player in result.players}
    by_award = {award.player_id: award for award in authority.awards}

    winner = by_player[final.winner_player_id]
    withdrawn = by_player[final.loser_player_id]
    assert winner.walkovers_received == 1
    assert winner.wins == 1
    assert by_award[winner.player_id].amount == 10000
    assert withdrawn.retired_or_walkover_loss is True
    assert withdrawn.losses == 0
    assert by_award[withdrawn.player_id].amount == 6000


@pytest.mark.pr_critical
def test_owned_source_v5_freezes_prize_money_and_ranking_remains_point_bound(database):
    result, _, point_authority, _, binding = _authorities()
    prize_authority = build_tournament_prize_money_award_authority(
        result=result,
        event=_event().model_copy(
            update={
                "prize_money_currency": "EUR",
                "prize_money_table": {
                    "semifinal": 3000,
                    "finalist": 6000,
                    "champion": 10000,
                },
            }
        ),
    )
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v5",
        binding=binding,
        canonical_result=result,
        canonical_awards=point_authority,
        canonical_prize_awards=prize_authority,
        adopted_by_command_id="close-v5",
        provenance_kind=(
            "canonical_run_owned_tournament_authorities_and_prize_money"
        ),
    )
    reopened = OwnedTournamentRankingSource.model_validate_json(
        source.model_dump_json()
    )
    assert reopened == source
    assert reopened.canonical_prize_awards is not None
    assert reopened.canonical_prize_awards.fingerprint == prize_authority.fingerprint

    players = tuple(
        OfficialRankingPlayer(
            player_id=player.player_id,
            tie_break_token=player.player_id,
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player in result.players
    )
    policy = OfficialRankingPolicy(policy_id="policy")
    with database.begin() as session:
        OfficialRankingCandidateStore(session).append(
            calculate_official_ranking(
                run_id="run",
                branch_id="branch",
                week=binding.completed_week,
                policy=policy,
                players=players,
                results=(),
            ),
            bootstrap=True,
        )
        OwnedTournamentRankingSourceStore(session).append(source)

    command = RankingWeekCommand(
        command_id="ranking-from-prize-v5",
        tournaments=(binding,),
        context=RankingTransitionContext(
            run_id="run",
            branch_id="branch",
            completed_week=binding.completed_week,
            target_week=binding.first_publication_week,
            policy=policy,
            players=players,
            discipline="none",
        ),
    )
    snapshot = RankingWeekCommandRunner(database, awards=None).execute(command)
    expected = {
        award.player_id: award.ranking_points_awarded
        for award in point_authority.awards
    }
    assert {row.player_id: row.points for row in snapshot.rows} == expected


@pytest.mark.pr_critical
def test_qualifier_or_lucky_loser_gets_only_final_main_stage_payout():
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="A",
        finalist_player_id="B",
        qualification_winner_ids=("QMAIN",),
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="main",
                reached_stage="champion",
            ),
            TournamentPlayerResultAuthority(
                player_id="B",
                draw_type="main",
                reached_stage="finalist",
            ),
            TournamentPlayerResultAuthority(
                player_id="QMAIN",
                draw_type="both",
                qualifier=True,
                reached_stage="semifinal",
            ),
        ),
        matches=(),
    )
    event = _event().model_copy(
        update={
            "main_draw_size": 4,
            "qualification_draw_size": 2,
            "qualifier_spots": 1,
            "prize_money_currency": "EUR",
            "prize_money_table": {
                "qualification_final": 1000,
                "semifinal": 3000,
                "finalist": 6000,
                "champion": 10000,
            },
        }
    )

    authority = build_tournament_prize_money_award_authority(
        result=result,
        event=event,
    )
    qmain = next(
        award for award in authority.awards if award.player_id == "QMAIN"
    )

    assert qmain.reached_stage == "semifinal"
    assert qmain.amount == 3000
    assert authority.known_awarded_amount == 19000


@pytest.mark.pr_critical
def test_prize_money_required_q_stages_use_each_section_capacity():
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="A",
        finalist_player_id="B",
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="main",
                reached_stage="champion",
            ),
            TournamentPlayerResultAuthority(
                player_id="B",
                draw_type="main",
                reached_stage="finalist",
            ),
            TournamentPlayerResultAuthority(
                player_id="QX",
                draw_type="qualification",
                reached_stage="qualification_semifinal",
            ),
        ),
        matches=(),
    )
    event = _event().model_copy(
        update={
            "main_draw_size": 2,
            "qualification_draw_size": 16,
            "qualifier_spots": 4,
            "prize_money_currency": "EUR",
            "prize_money_table": {
                "qualification_semifinal": 500,
                "qualification_final": 1000,
                "finalist": 6000,
                "champion": 10000,
            },
        }
    )

    authority = build_tournament_prize_money_award_authority(
        result=result,
        event=event,
    )

    assert authority.required_stage_ids == (
        "qualification_semifinal",
        "qualification_final",
        "finalist",
        "champion",
    )
    assert "qualification_round" not in authority.required_stage_ids
    assert authority.configuration_status == "complete"
    q_award = next(
        award for award in authority.awards if award.player_id == "QX"
    )
    assert q_award.amount == 500


@pytest.mark.pr_critical
def test_prize_money_authority_rejects_corrupt_reopen():
    result, _, _, _, _ = _authorities()
    authority = build_tournament_prize_money_award_authority(
        result=result,
        event=_event().model_copy(
            update={
                "prize_money_currency": "EUR",
                "prize_money_table": {
                    "semifinal": 3000,
                    "finalist": 6000,
                    "champion": 10000,
                },
            }
        ),
    )
    payload = authority.model_dump(mode="json")
    payload["known_awarded_amount"] += 1

    with pytest.raises(ValueError, match="known awarded amount mismatch"):
        TournamentPrizeMoneyAwardAuthority.model_validate_json(
            json.dumps(payload, sort_keys=True, separators=(",", ":"))
        )


@pytest.mark.pr_critical
def test_bye_first_real_match_loss_keeps_finishing_stage_but_uses_first_round_points():
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="B",
        finalist_player_id="A",
        qualification_winner_ids=("A",),
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="both",
                qualifier=True,
                reached_stage="finalist",
                final_round_number=2,
                eliminated_by_player_id="B",
                last_match_id="final",
                wins=1,
                losses=1,
                byes_received=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="B",
                draw_type="main",
                reached_stage="champion",
                final_round_number=2,
                last_match_id="final",
                wins=2,
                losses=0,
            ),
            TournamentPlayerResultAuthority(
                player_id="C",
                draw_type="main",
                reached_stage="semifinal",
                final_round_number=1,
                eliminated_by_player_id="B",
                last_match_id="semi",
                wins=0,
                losses=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="D",
                draw_type="qualification",
                reached_stage="qualification_final",
                final_round_number=1,
                eliminated_by_player_id="A",
                last_match_id="q-final",
                wins=0,
                losses=1,
            ),
        ),
        matches=(
            TournamentMatchResultAuthority(
                match_id="q-final",
                draw_type="qualification",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="D",
                scoreline="3-0",
                result_fingerprint="0" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="bye",
                draw_type="main",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                scoreline="BYE",
                result_fingerprint="1" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="semi",
                draw_type="main",
                round_number=1,
                bracket_position=2,
                winner_player_id="B",
                loser_player_id="C",
                scoreline="3-0",
                result_fingerprint="2" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="final",
                draw_type="main",
                round_number=2,
                bracket_position=1,
                winner_player_id="B",
                loser_player_id="A",
                scoreline="3-0",
                result_fingerprint="3" * 64,
            ),
        ),
    )
    frozen_points = FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
            "qualification_winner": 150,
            "qualification_final": 100,
        },
        point_distribution_source="calendar_event.ranking_points_table",
    )

    authority = build_tournament_point_award_authority(
        result=result,
        point_authority=frozen_points,
        seed=991,
    )
    by_player = {award.player_id: award for award in authority.awards}
    finalist = by_player["A"]

    assert authority.schema_version == "tournament_point_award_authority.v3"
    assert finalist.reached_stage == "finalist"
    assert finalist.point_stage == "semifinal"
    assert finalist.qualification_point_stage == "qualification_winner"
    assert finalist.qualification_points_awarded == 150
    assert finalist.ranking_points_awarded == 550
    assert finalist.race_points_awarded == 550

    prize = build_tournament_prize_money_award_authority(
        result=result,
        event=_event().model_copy(
            update={
                "qualification_draw_size": 2,
                "qualifier_spots": 1,
                "prize_money_currency": "EUR",
                "prize_money_table": {
                    "qualification_final": 1000,
                    "semifinal": 3000,
                    "finalist": 6000,
                    "champion": 10000,
                },
            }
        ),
    )
    prize_by_player = {award.player_id: award for award in prize.awards}
    assert prize_by_player["A"].reached_stage == "finalist"
    assert prize_by_player["A"].amount == 6000


@pytest.mark.pr_critical
def test_qualification_winner_walkover_unlocks_main_stage_and_keeps_additive_q_points():
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="B",
        finalist_player_id="A",
        qualification_winner_ids=("A",),
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="both",
                qualifier=True,
                reached_stage="finalist",
                final_round_number=3,
                eliminated_by_player_id="B",
                last_match_id="final",
                wins=1,
                losses=1,
                byes_received=1,
                walkovers_received=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="B",
                draw_type="main",
                reached_stage="champion",
                final_round_number=3,
                last_match_id="final",
                wins=1,
                losses=0,
            ),
            TournamentPlayerResultAuthority(
                player_id="C",
                draw_type="main",
                reached_stage="semifinal",
                final_round_number=2,
                eliminated_by_player_id="A",
                last_match_id="walkover",
                wins=0,
                losses=0,
                retired_or_walkover_loss=True,
            ),
            TournamentPlayerResultAuthority(
                player_id="D",
                draw_type="qualification",
                reached_stage="qualification_final",
                final_round_number=1,
                eliminated_by_player_id="A",
                last_match_id="q-final",
                wins=0,
                losses=1,
            ),
        ),
        matches=(
            TournamentMatchResultAuthority(
                match_id="q-final",
                draw_type="qualification",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="D",
                scoreline="3-0",
                result_fingerprint="0" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="bye",
                draw_type="main",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                scoreline="BYE",
                result_fingerprint="1" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="walkover",
                draw_type="main",
                round_number=2,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="C",
                scoreline="W/O",
                result_fingerprint="2" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="final",
                draw_type="main",
                round_number=3,
                bracket_position=1,
                winner_player_id="B",
                loser_player_id="A",
                scoreline="3-0",
                result_fingerprint="3" * 64,
            ),
        ),
    )

    authority = build_tournament_point_award_authority(
        result=result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution={
                "champion": 1000,
                "finalist": 650,
                "semifinal": 400,
                "quarterfinal": 250,
                "qualification_winner": 150,
                "qualification_final": 100,
            },
            point_distribution_source="calendar_event.ranking_points_table",
        ),
        seed=993,
    )
    by_player = {award.player_id: award for award in authority.awards}
    finalist = by_player["A"]

    assert authority.schema_version == "tournament_point_award_authority.v3"
    assert finalist.reached_stage == "finalist"
    assert finalist.point_stage is None
    assert finalist.qualification_point_stage == "qualification_winner"
    assert finalist.qualification_points_awarded == 150
    assert finalist.ranking_points_awarded == 800
    assert finalist.race_points_awarded == 800
    assert by_player["D"].ranking_points_awarded == 100

    prize = build_tournament_prize_money_award_authority(
        result=result,
        event=_event().model_copy(
            update={
                "main_draw_size": 8,
                "qualification_draw_size": 2,
                "qualifier_spots": 1,
                "prize_money_currency": "EUR",
                "prize_money_table": {
                    "qualification_final": 1000,
                    "quarterfinal": 2000,
                    "semifinal": 3000,
                    "finalist": 6000,
                    "champion": 10000,
                },
            }
        ),
    )
    prize_by_player = {award.player_id: award for award in prize.awards}
    assert prize_by_player["A"].reached_stage == "finalist"
    assert prize_by_player["A"].amount == 6000
    assert prize_by_player["D"].reached_stage == "qualification_final"
    assert prize_by_player["D"].amount == 1000


@pytest.mark.pr_critical
def test_walkover_after_bye_unlocks_actual_finishing_stage_points():
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="C",
        finalist_player_id="A",
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="main",
                reached_stage="finalist",
                final_round_number=3,
                eliminated_by_player_id="C",
                last_match_id="final",
                wins=0,
                losses=1,
                byes_received=1,
                walkovers_received=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="C",
                draw_type="main",
                reached_stage="champion",
                final_round_number=3,
                last_match_id="final",
                wins=1,
                losses=0,
            ),
            TournamentPlayerResultAuthority(
                player_id="D",
                draw_type="main",
                reached_stage="semifinal",
                final_round_number=2,
                eliminated_by_player_id="A",
                last_match_id="walkover",
                wins=0,
                losses=0,
                retired_or_walkover_loss=True,
            ),
        ),
        matches=(
            TournamentMatchResultAuthority(
                match_id="bye",
                draw_type="main",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                scoreline="BYE",
                result_fingerprint="4" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="walkover",
                draw_type="main",
                round_number=2,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="D",
                scoreline="W/O",
                result_fingerprint="5" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="final",
                draw_type="main",
                round_number=3,
                bracket_position=1,
                winner_player_id="C",
                loser_player_id="A",
                scoreline="3-0",
                result_fingerprint="6" * 64,
            ),
        ),
    )
    authority = build_tournament_point_award_authority(
        result=result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution={
                "champion": 1000,
                "finalist": 650,
                "semifinal": 400,
                "quarterfinal": 250,
            },
            point_distribution_source="calendar_event.ranking_points_table",
        ),
        seed=992,
    )
    finalist = next(award for award in authority.awards if award.player_id == "A")

    assert authority.schema_version == "tournament_point_award_authority.v1"
    assert finalist.reached_stage == "finalist"
    assert finalist.point_stage is None
    assert finalist.ranking_points_awarded == 650


def test_canonical_point_authority_maps_frozen_distribution_without_legacy_service():
    result_authority, _, point_authority, _, _ = _authorities()

    by_id = {award.player_id: award for award in point_authority.awards}
    assert by_id[result_authority.champion_player_id].ranking_points_awarded == 1000
    assert by_id[result_authority.finalist_player_id].ranking_points_awarded == 650
    semifinalists = [
        award
        for award in point_authority.awards
        if award.reached_stage == "semifinal"
    ]
    assert len(semifinalists) == 2
    assert all(award.ranking_points_awarded == 400 for award in semifinalists)
    assert point_authority.total_ranking_points == 2450
    assert point_authority.schema_version == "tournament_point_award_authority.v1"
    assert point_authority.total_race_points == 2450
    assert "point_stage" not in point_authority.model_dump_json()


def test_canonical_point_authority_rejects_corrupt_distribution_on_reopen():
    _, _, point_authority, _, _ = _authorities()
    payload = point_authority.model_dump(mode="json")
    distribution = [list(item) for item in payload["point_distribution"]]
    distribution[0][1] += 1
    payload["point_distribution"] = distribution

    with pytest.raises(ValueError, match="distribution snapshot mismatch"):
        TournamentPointAwardAuthority.model_validate_json(json.dumps(payload))


def test_canonical_point_authority_fails_closed_on_fallback_distribution():
    result_authority, _, _, _, _ = _authorities()
    with pytest.raises(ValueError, match="authored point distribution"):
        build_tournament_point_award_authority(
            result=result_authority,
            point_authority=FrozenPointAwardAuthority(
                ranking_status="ranked",
                point_distribution={"champion": 1000},
                point_distribution_source="fallback.default_stage_points",
            ),
            seed=88,
        )


def test_direct_canonical_ranking_materialization_uses_authority_fingerprints():
    result_authority, _, point_authority, _, binding = _authorities()
    versions = prepare_canonical_tournament_ranking_sources(
        binding,
        result_authority,
        point_authority,
    )

    assert {version.result.player_id for version in versions} == {
        player.player_id for player in result_authority.players
    }
    points = {
        version.result.player_id: version.result.main_points
        for version in versions
    }
    assert points[result_authority.champion_player_id] == 1000
    assert points[result_authority.finalist_player_id] == 650
    assert all(
        version.result.first_publication_week == RankingWeek(season_index=0, week=2)
        for version in versions
    )


def test_owned_source_v3_binds_canonical_points_and_compatibility_dto():
    result_authority, result, point_authority, awards, binding = _authorities()
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v3",
        binding=binding,
        result=result,
        awards=awards,
        canonical_result=result_authority,
        canonical_awards=point_authority,
        adopted_by_command_id="close",
        provenance_kind="canonical_run_owned_tournament_result_and_points",
    )
    assert (
        OwnedTournamentRankingSource.model_validate_json(source.model_dump_json())
        == source
    )

    changed = list(awards.awards)
    changed[0] = changed[0].model_copy(
        update={"ranking_points_awarded": changed[0].ranking_points_awarded + 1}
    )
    bad = awards.model_copy(update={"awards": changed})
    with pytest.raises(
        ValueError, match="point-award compatibility projection mismatch"
    ):
        OwnedTournamentRankingSource(
            schema_version="owned_tournament_ranking_source.v3",
            binding=binding,
            result=result,
            awards=bad,
            canonical_result=result_authority,
            canonical_awards=point_authority,
            adopted_by_command_id="close",
            provenance_kind="canonical_run_owned_tournament_result_and_points",
        )


def test_v2_fingerprint_contract_ignores_new_v3_field():
    result_authority, result, _, awards, _ = _authorities()
    legacy_binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="event",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.metadata.build_fingerprint,
        expected_award_fingerprint=awards.metadata.build_fingerprint,
    )
    v2 = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v2",
        binding=legacy_binding,
        result=result,
        awards=awards,
        canonical_result=result_authority,
        adopted_by_command_id="old-close",
        provenance_kind="canonical_run_owned_tournament_result",
    )
    old_payload = v2.model_dump(mode="json")
    old_payload.pop("canonical_awards", None)
    expected = hashlib.sha256(
        json.dumps(old_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    historical_json = json.dumps(old_payload, sort_keys=True, separators=(",", ":"))
    reopened = OwnedTournamentRankingSource.model_validate_json(historical_json)

    assert reopened.schema_version == "owned_tournament_ranking_source.v2"
    assert reopened.canonical_awards is None
    assert reopened.fingerprint == expected



def test_ranking_week_ingests_v3_without_legacy_award_service(database):
    result_authority, result, point_authority, awards, binding = _authorities()
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v3",
        binding=binding,
        result=result,
        awards=awards,
        canonical_result=result_authority,
        canonical_awards=point_authority,
        adopted_by_command_id="close",
        provenance_kind="canonical_run_owned_tournament_result_and_points",
    )
    players = tuple(
        OfficialRankingPlayer(
            player_id=player.player_id,
            tie_break_token=player.player_id,
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player in result_authority.players
    )
    policy = OfficialRankingPolicy(policy_id="policy")
    with database.begin() as session:
        OfficialRankingCandidateStore(session).append(
            calculate_official_ranking(
                run_id="run",
                branch_id="branch",
                week=binding.completed_week,
                policy=policy,
                players=players,
                results=(),
            ),
            bootstrap=True,
        )
        OwnedTournamentRankingSourceStore(session).append(source)

    command = RankingWeekCommand(
        command_id="ranking-from-canonical-points",
        tournaments=(binding,),
        context=RankingTransitionContext(
            run_id="run",
            branch_id="branch",
            completed_week=binding.completed_week,
            target_week=binding.first_publication_week,
            policy=policy,
            players=players,
            discipline="none",
        ),
    )
    snapshot = RankingWeekCommandRunner(database, awards=None).execute(command)
    expected = {
        award.player_id: award.ranking_points_awarded
        for award in point_authority.awards
    }
    assert {row.player_id: row.points for row in snapshot.rows} == expected



def test_owned_source_v4_persists_no_legacy_result_or_award_dtos():
    result_authority, _, point_authority, _, binding = _authorities()
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v4",
        binding=binding,
        canonical_result=result_authority,
        canonical_awards=point_authority,
        adopted_by_command_id="canonical-close",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )

    payload = json.loads(source.model_dump_json())
    assert "result" not in payload
    assert "awards" not in payload
    assert payload["canonical_result"]["event_id"] == "event"
    assert payload["canonical_awards"]["event_id"] == "event"

    reopened = OwnedTournamentRankingSource.model_validate_json(
        source.model_dump_json()
    )
    assert reopened == source
    assert reopened.result is None
    assert reopened.awards is None
    assert reopened.fingerprint == source.fingerprint


def test_owned_source_v4_rejects_legacy_compatibility_copies():
    result_authority, result, point_authority, awards, binding = _authorities()
    with pytest.raises(ValueError, match="cannot persist legacy compatibility DTOs"):
        OwnedTournamentRankingSource(
            schema_version="owned_tournament_ranking_source.v4",
            binding=binding,
            result=result,
            awards=awards,
            canonical_result=result_authority,
            canonical_awards=point_authority,
            adopted_by_command_id="bad-close",
            provenance_kind="canonical_run_owned_tournament_authorities",
        )


def test_owned_source_v3_fingerprint_contract_survives_v4_model():
    result_authority, result, point_authority, awards, binding = _authorities()
    v3 = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v3",
        binding=binding,
        result=result,
        awards=awards,
        canonical_result=result_authority,
        canonical_awards=point_authority,
        adopted_by_command_id="historical-v3",
        provenance_kind="canonical_run_owned_tournament_result_and_points",
    )
    historical_payload = v3.model_dump(mode="json")
    expected = hashlib.sha256(
        json.dumps(
            historical_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    reopened = OwnedTournamentRankingSource.model_validate_json(
        json.dumps(historical_payload, sort_keys=True, separators=(",", ":"))
    )
    assert reopened.fingerprint == expected


@pytest.mark.pr_critical
def test_v4_fingerprint_contract_survives_v5_model():
    result_authority, _, point_authority, _, binding = _authorities()
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v4",
        binding=binding,
        canonical_result=result_authority,
        canonical_awards=point_authority,
        adopted_by_command_id="historical-v4",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )
    historical_payload = source.model_dump(mode="json")
    assert "canonical_prize_awards" not in historical_payload
    expected = hashlib.sha256(
        json.dumps(
            historical_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    reopened = OwnedTournamentRankingSource.model_validate_json(
        json.dumps(
            historical_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    assert reopened.schema_version == "owned_tournament_ranking_source.v4"
    assert reopened.canonical_prize_awards is None
    assert reopened.fingerprint == expected


def test_ranking_week_ingests_v4_without_legacy_dtos_or_award_service(database):
    result_authority, _, point_authority, _, binding = _authorities()
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v4",
        binding=binding,
        canonical_result=result_authority,
        canonical_awards=point_authority,
        adopted_by_command_id="close-v4",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )
    players = tuple(
        OfficialRankingPlayer(
            player_id=player.player_id,
            tie_break_token=player.player_id,
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player in result_authority.players
    )
    policy = OfficialRankingPolicy(policy_id="policy")
    with database.begin() as session:
        OfficialRankingCandidateStore(session).append(
            calculate_official_ranking(
                run_id="run",
                branch_id="branch",
                week=binding.completed_week,
                policy=policy,
                players=players,
                results=(),
            ),
            bootstrap=True,
        )
        stored = OwnedTournamentRankingSourceStore(session).append(source)
        assert stored.result is None
        assert stored.awards is None

    command = RankingWeekCommand(
        command_id="ranking-from-canonical-only-source",
        tournaments=(binding,),
        context=RankingTransitionContext(
            run_id="run",
            branch_id="branch",
            completed_week=binding.completed_week,
            target_week=binding.first_publication_week,
            policy=policy,
            players=players,
            discipline="none",
        ),
    )
    snapshot = RankingWeekCommandRunner(database, awards=None).execute(command)
    expected = {
        award.player_id: award.ranking_points_awarded
        for award in point_authority.awards
    }
    assert {row.player_id: row.points for row in snapshot.rows} == expected


@pytest.mark.pr_critical
def test_canonical_walkover_awards_stage_points_without_played_win_or_loss():
    result, awards, binding, final = _walkover_authorities()
    by_player = {player.player_id: player for player in result.players}
    by_award = {award.player_id: award for award in awards.awards}

    winner = by_player[final.winner_player_id]
    withdrawn = by_player[final.loser_player_id]

    assert winner.reached_stage == "champion"
    assert winner.walkovers_received == 1
    assert winner.wins == 1
    assert winner.losses == 0
    assert withdrawn.reached_stage == "finalist"
    assert withdrawn.retired_or_walkover_loss is True
    assert withdrawn.losses == 0

    assert by_award[winner.player_id].ranking_points_awarded == 1000
    assert by_award[withdrawn.player_id].ranking_points_awarded == 650

    versions = prepare_canonical_tournament_ranking_sources(
        binding,
        result,
        awards,
    )
    ranking_points = {
        version.result.player_id: version.result.main_points
        for version in versions
    }
    assert ranking_points[winner.player_id] == 1000
    assert ranking_points[withdrawn.player_id] == 650


@pytest.mark.pr_critical
def test_canonical_walkover_point_builder_rejects_counter_corruption():
    result, _, _, final = _walkover_authorities()
    corrupted_players = tuple(
        player.model_copy(update={"wins": player.wins + 1})
        if player.player_id == final.winner_player_id
        else player
        for player in result.players
    )
    corrupted = result.model_copy(update={"players": corrupted_players})

    with pytest.raises(
        ValueError,
        match="match counters differ from canonical result",
    ):
        build_tournament_point_award_authority(
            result=corrupted,
            point_authority=FrozenPointAwardAuthority(
                ranking_status="ranked",
                point_distribution={
                    "champion": 1000,
                    "finalist": 650,
                    "semifinal": 400,
                    "main_draw_participant": 0,
                },
                point_distribution_source=(
                    "calendar_event.ranking_points_table"
                ),
            ),
            seed=188,
        )
