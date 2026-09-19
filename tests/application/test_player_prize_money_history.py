from __future__ import annotations

import hashlib

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
    build_tournament_prize_money_award_authority,
)
from beta_engine.domain.tournaments.result_authority import (
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
        DatabaseSettings(
            url=f"sqlite:///{tmp_path / 'player-prize-history.db'}"
        )
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


def _result(*, event_id: str, week: RankingWeek) -> TournamentResultAuthority:
    return TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id=event_id,
        completed_week=week,
        draw_authority_fingerprint=hashlib.sha256(
            f"draw|{event_id}".encode()
        ).hexdigest(),
        match_package_fingerprint=hashlib.sha256(
            f"package|{event_id}".encode()
        ).hexdigest(),
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


def _event(
    *,
    event_id: str,
    week: RankingWeek,
    currency: str | None = None,
    table: dict[str, int | None] | None = None,
) -> CalendarEvent:
    return CalendarEvent(
        event_id=event_id,
        season=f"S{week.season_index}",
        season_week=week.week,
        template_id="template",
        event_name=event_id,
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=2,
        qualification_draw_size=0,
        qualifier_spots=0,
        prize_money_currency=currency,
        prize_money_table=table or {},
    )


def _source(
    *,
    event_id: str,
    week: RankingWeek,
    schema_version: str = "owned_tournament_ranking_source.v5",
    currency: str | None = None,
    table: dict[str, int | None] | None = None,
) -> OwnedTournamentRankingSource:
    result = _result(event_id=event_id, week=week)
    point_awards = build_tournament_point_award_authority(
        result=result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution={
                "champion": 1000,
                "finalist": 650,
            },
            point_distribution_source="calendar_event.ranking_points_table",
        ),
        seed=1,
    )
    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id=event_id,
        event_id=event_id,
        completed_week=week,
        first_publication_week=RankingWeek(
            season_index=week.season_index,
            week=week.week + 1,
        ),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.fingerprint,
        expected_award_fingerprint=point_awards.fingerprint,
    )

    if schema_version == "owned_tournament_ranking_source.v4":
        return OwnedTournamentRankingSource(
            schema_version="owned_tournament_ranking_source.v4",
            binding=binding,
            canonical_result=result,
            canonical_awards=point_awards,
            adopted_by_command_id=f"close-{event_id}",
            provenance_kind="canonical_run_owned_tournament_authorities",
        )

    prize_awards = build_tournament_prize_money_award_authority(
        result=result,
        event=_event(
            event_id=event_id,
            week=week,
            currency=currency,
            table=table,
        ),
    )
    return OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v5",
        binding=binding,
        canonical_result=result,
        canonical_awards=point_awards,
        canonical_prize_awards=prize_awards,
        adopted_by_command_id=f"close-{event_id}",
        provenance_kind=(
            "canonical_run_owned_tournament_authorities_and_prize_money"
        ),
    )


def test_player_prize_money_history_preserves_currencies_and_unknowns(database):
    with database.begin() as session:
        store = OwnedTournamentRankingSourceStore(session)
        store.append(
            _source(
                event_id="A1",
                week=RankingWeek(season_index=0, week=1),
                schema_version="owned_tournament_ranking_source.v4",
            )
        )
        store.append(
            _source(
                event_id="B2",
                week=RankingWeek(season_index=0, week=2),
                currency="EUR",
                table={"finalist": 6000, "champion": 10000},
            )
        )
        store.append(
            _source(
                event_id="C3",
                week=RankingWeek(season_index=1, week=1),
                currency="USD",
                table={"finalist": 7000, "champion": 12000},
            )
        )
        store.append(
            _source(
                event_id="D4",
                week=RankingWeek(season_index=1, week=2),
                currency="GBP",
                table={"finalist": 5000, "champion": None},
            )
        )
        store.append(
            _source(
                event_id="E5",
                week=RankingWeek(season_index=1, week=3),
            )
        )

    history = PlayerPrizeMoneyHistoryService(database).inspect(
        run_id="run",
        branch_id="branch",
        player_id="A",
    )

    assert [entry.event_id for entry in history.entries] == [
        "A1",
        "B2",
        "C3",
        "D4",
        "E5",
    ]
    assert [entry.payout_status for entry in history.entries] == [
        "historical_unavailable",
        "known",
        "known",
        "unknown",
        "not_configured",
    ]
    assert history.coverage_status == "partial"
    assert history.reporting_currency_status == "requires_historical_fx_authority"
    assert history.known_payout_count == 2
    assert history.unknown_payout_count == 1
    assert history.not_configured_count == 1
    assert history.historical_unavailable_count == 1

    assert [
        total.model_dump()
        for total in history.career_known_totals_by_currency
    ] == [
        {"currency": "EUR", "amount": 10000, "payout_count": 1},
        {"currency": "USD", "amount": 12000, "payout_count": 1},
    ]

    assert len(history.season_summaries) == 2
    season_zero, season_one = history.season_summaries
    assert season_zero.season_index == 0
    assert season_zero.event_count == 2
    assert season_zero.historical_unavailable_count == 1
    assert season_zero.known_totals_by_currency[0].currency == "EUR"
    assert season_zero.known_totals_by_currency[0].amount == 10000

    assert season_one.season_index == 1
    assert season_one.event_count == 3
    assert season_one.known_payout_count == 1
    assert season_one.unknown_payout_count == 1
    assert season_one.not_configured_count == 1
    assert season_one.known_totals_by_currency[0].currency == "USD"
    assert season_one.known_totals_by_currency[0].amount == 12000


def test_player_prize_money_history_is_empty_not_zero_for_player_without_events(
    database,
):
    history = PlayerPrizeMoneyHistoryService(database).inspect(
        run_id="run",
        branch_id="branch",
        player_id="NO-EVENTS",
    )

    assert history.entries == ()
    assert history.season_summaries == ()
    assert history.career_known_totals_by_currency == ()
    assert history.known_payout_count == 0
    assert history.unknown_payout_count == 0
    assert history.not_configured_count == 0
    assert history.historical_unavailable_count == 0
    assert history.coverage_status == "complete"


def test_player_prize_money_history_rejects_wrong_run_branch_scope(database):
    with pytest.raises(KeyError, match="Run/Branch scope"):
        PlayerPrizeMoneyHistoryService(database).inspect(
            run_id="other",
            branch_id="branch",
            player_id="A",
        )
