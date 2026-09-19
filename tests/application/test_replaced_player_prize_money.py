from __future__ import annotations

import json

import pytest

from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
)
from beta_engine.application.player_prize_money_history import (
    PlayerPrizeMoneyHistoryService,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.tournament_source import (
    OwnedTournamentRankingSource,
)
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.prize_money_award_authority import (
    TournamentPrizeMoneyAwardAuthority,
    build_tournament_prize_money_award_authority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)


pytestmark = pytest.mark.pr_critical


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'replaced-prize.db'}")
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


def _result() -> TournamentResultAuthority:
    return TournamentResultAuthority(
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


def _event() -> CalendarEvent:
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="template",
        event_name="Replacement Prize Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=4,
        qualification_draw_size=2,
        qualifier_spots=1,
        prize_money_currency="EUR",
        prize_money_table={
            "qualification_final": 1000,
            "semifinal": 3000,
            "finalist": 6000,
            "champion": 10000,
        },
    )


def _point_awards(result: TournamentResultAuthority):
    return build_tournament_point_award_authority(
        result=result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution={
                "champion": 1000,
                "finalist": 650,
                "semifinal": 400,
                "qualification_winner": 150,
                "qualification_final": 100,
            },
            point_distribution_source="calendar_event.ranking_points_table",
        ),
        seed=813,
    )


def test_replaced_q_winner_is_explicit_zero_not_unknown():
    result = _result()
    authority = build_tournament_prize_money_award_authority(
        result=result,
        event=_event(),
    )
    by_player = {award.player_id: award for award in authority.awards}

    assert authority.schema_version == "tournament_prize_money_award_authority.v2"

    withdrawn = by_player["QW"]
    assert withdrawn.reached_stage == "qualification_winner"
    assert withdrawn.payout_status == "zero"
    assert withdrawn.amount == 0
    assert withdrawn.currency == "EUR"
    assert withdrawn.zero_reason == "replaced_before_first_real_match"

    lucky_loser = by_player["LL"]
    assert lucky_loser.payout_status == "known"
    assert lucky_loser.amount == 3000
    assert lucky_loser.zero_reason is None

    assert authority.configuration_status == "complete"
    assert authority.unknown_award_count == 0
    assert authority.known_awarded_amount == 22000
    assert authority.total_prize_pool_status == "complete"
    assert authority.total_prize_pool_amount == 22000


def test_zero_payout_provenance_rejects_corrupt_reopen():
    authority = build_tournament_prize_money_award_authority(
        result=_result(),
        event=_event(),
    )
    payload = authority.model_dump(mode="json")
    withdrawn = next(
        award for award in payload["awards"] if award["player_id"] == "QW"
    )
    withdrawn["zero_reason"] = None

    with pytest.raises(
        ValueError,
        match="differs from frozen stage table",
    ):
        TournamentPrizeMoneyAwardAuthority.model_validate_json(
            json.dumps(payload, sort_keys=True, separators=(",", ":"))
        )


def test_historical_v1_prize_authority_without_zero_provenance_remains_readable():
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="c" * 64,
        match_package_fingerprint="d" * 64,
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
        ),
        matches=(),
    )
    event = _event().model_copy(
        update={
            "main_draw_size": 2,
            "qualification_draw_size": 0,
            "qualifier_spots": 0,
            "prize_money_table": {
                "finalist": 6000,
                "champion": 10000,
            },
        }
    )
    current = build_tournament_prize_money_award_authority(
        result=result,
        event=event,
    )
    payload = current.model_dump(mode="json")
    payload["schema_version"] = "tournament_prize_money_award_authority.v1"

    historical = TournamentPrizeMoneyAwardAuthority.model_validate_json(
        json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )
    assert historical.schema_version == "tournament_prize_money_award_authority.v1"
    assert all(award.zero_reason is None for award in historical.awards)
    assert all(award.payout_status == "known" for award in historical.awards)


def test_explicit_zero_survives_owned_source_into_player_prize_history(database):
    result = _result()
    points = _point_awards(result)
    prize = build_tournament_prize_money_award_authority(
        result=result,
        event=_event(),
    )
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
        expected_award_fingerprint=points.fingerprint,
    )
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v5",
        binding=binding,
        canonical_result=result,
        canonical_awards=points,
        canonical_prize_awards=prize,
        adopted_by_command_id="close-replaced-q-winner",
        provenance_kind=(
            "canonical_run_owned_tournament_authorities_and_prize_money"
        ),
    )

    with database.begin() as session:
        OwnedTournamentRankingSourceStore(session).append(source)

    history = PlayerPrizeMoneyHistoryService(database).inspect(
        run_id="run",
        branch_id="branch",
        player_id="QW",
    )
    assert len(history.entries) == 1
    entry = history.entries[0]
    assert entry.payout_status == "zero"
    assert entry.amount == 0
    assert entry.currency == "EUR"
    assert entry.zero_reason == "replaced_before_first_real_match"
    assert history.coverage_status == "complete"
    assert history.known_payout_count == 0
    assert history.zero_payout_count == 1
    assert history.unknown_payout_count == 0
    assert history.not_configured_count == 0
    assert history.historical_unavailable_count == 0
    assert history.career_known_totals_by_currency == ()

    assert len(history.season_summaries) == 1
    summary = history.season_summaries[0]
    assert summary.event_count == 1
    assert summary.known_payout_count == 0
    assert summary.zero_payout_count == 1
    assert summary.known_totals_by_currency == ()
