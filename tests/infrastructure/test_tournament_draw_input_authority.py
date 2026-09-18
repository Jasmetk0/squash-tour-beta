"""Run/Branch-owned Tournament Draw Input authority regression coverage."""

from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldCapacity,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    TournamentDrawInputAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityConflict,
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldConflict,
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


pytestmark = pytest.mark.smoke


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'draw-input.db'}")
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


def ranking_snapshot(
    *,
    week: int = 3,
    points: dict[str, int] | None = None,
):
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    target = RankingWeek(season_index=0, week=week)
    values = points or {
        "A": 100,
        "B": 90,
        "C": 80,
        "D": 70,
        "E": 60,
        "F": 50,
        "G": 40,
    }
    players = tuple(
        OfficialRankingPlayer(
            player_id=player_id,
            tie_break_token=f"rank-{player_id}",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player_id in sorted(values)
    )
    results = tuple(
        OfficialRankingResult(
            edition_id=f"prior-{player_id}-{week}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}-{week}",
            completed_week=completed,
            first_publication_week=published,
            main_points=value,
        )
        for player_id, value in sorted(values.items())
    )
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=target,
        policy=OfficialRankingPolicy(policy_id=f"policy-{week}"),
        players=players,
        results=results,
    )


def install_ranking_authority(session):
    snapshot = ranking_snapshot()
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=snapshot.week.ordinal,
            snapshot_fingerprint=snapshot.fingerprint,
            payload_json=snapshot.model_dump_json(),
        )
    )
    session.flush()
    return TournamentRankingSnapshotAuthorityStore(session).adopt(
        run_id="run",
        branch_id="branch",
        event_id="event",
        ranking_week=snapshot.week,
        command_id="adopt-ranking",
    )


def app(player_id: str, window: str):
    return TournamentEntryApplication(
        application_id=f"app-{player_id}",
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id=player_id,
        entry_window=window,
        decision_slot_ordinal=10,
        nr_tie_break_token=f"entry-{player_id}",
    )


def applications():
    return (
        app("A", "main"),
        app("C", "main"),
        app("D", "main"),
        app("B", "qualification"),
        app("E", "qualification"),
        app("F", "qualification"),
        app("G", "qualification"),
    )


def capacity(*, wild_cards: int = 0):
    return TournamentEntryFieldCapacity(
        main_draw_size=4,
        qualification_draw_size=2,
        qualifier_spots=1,
        wild_card_slots=wild_cards,
    )


def stage_initial_field(session, *, wild_cards: int = 0):
    install_ranking_authority(session)
    return TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=applications(),
        capacity=capacity(wild_cards=wild_cards),
        command_id="initial-field",
    )


def commit_draw_input(session, *, command_id: str = "commit-draw", seed: int = 123):
    return TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id=command_id,
        draw_seed=seed,
        main_seed_count=2,
        qualification_seed_count=1,
    )


def test_commit_freezes_terminal_field_seed_order_and_exact_retry(database):
    with database.begin() as session:
        field = stage_initial_field(session)
        committed = commit_draw_input(session)

        assert committed.entry_field_fingerprint == field.fingerprint
        assert committed.field_sequence == 1
        assert committed.capacity == field.capacity
        assert committed.direct_main_player_ids == ("A", "C", "D")
        assert committed.qualification_player_ids == ("B", "E")
        assert committed.main_seed_player_ids == ("A", "C")
        assert committed.qualification_seed_player_ids == ("B",)
        assert committed.qualifier_placeholder_ids == ("Q1",)
        assert committed.withdrawn_player_ids == ()
        assert (
            TournamentDrawInputAuthorityStore(session).get(
                run_id="run",
                branch_id="branch",
                event_id="event",
            )
            == committed
        )
        assert commit_draw_input(session) == committed

        with pytest.raises(
            TournamentDrawInputAuthorityConflict, match="different request"
        ):
            commit_draw_input(session, seed=999)


def test_repaired_terminal_field_is_committed_and_newer_ranking_does_not_move_it(
    database,
):
    with database.begin() as session:
        stage_initial_field(session)
        repaired = TournamentEntryFieldStore(session).stage_pre_draw_repair(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            withdrawn_player_ids=("D",),
            command_id="withdraw-d",
        )
        committed = commit_draw_input(session)
        assert committed.field_sequence == 2
        assert committed.entry_field_fingerprint == repaired.fingerprint
        assert committed.direct_main_player_ids == ("A", "B", "C")
        assert committed.qualification_player_ids == ("E", "F")
        assert committed.withdrawn_player_ids == ("D",)
        assert committed.main_seed_player_ids == ("A", "B")
        assert committed.qualification_seed_player_ids == ("E",)

        # The draw lock blocks new pre-draw changes but must preserve exact
        # idempotent retries of a repair that was already committed beforehand.
        assert TournamentEntryFieldStore(session).stage_pre_draw_repair(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=list(reversed(applications())),
            withdrawn_player_ids=("D",),
            command_id="withdraw-d",
        ) == repaired

        newer = ranking_snapshot(
            week=4,
            points={
                "A": 10,
                "B": 20,
                "C": 30,
                "D": 40,
                "E": 50,
                "F": 60,
                "G": 70,
            },
        )
        session.add(
            PublishedOfficialRankingModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=newer.week.ordinal,
                snapshot_fingerprint=newer.fingerprint,
                payload_json=newer.model_dump_json(),
            )
        )
        session.flush()

        reloaded = TournamentDrawInputAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        assert reloaded == committed
        assert reloaded.main_seed_player_ids == ("A", "B")


def test_draw_commit_locks_further_pre_draw_field_repair(database):
    with database.begin() as session:
        stage_initial_field(session)
        commit_draw_input(session)

        with pytest.raises(
            TournamentEntryFieldConflict, match="locked after Tournament Draw Input"
        ):
            TournamentEntryFieldStore(session).stage_pre_draw_repair(
                run_id="run",
                branch_id="branch",
                event_id="event",
                applications=applications(),
                withdrawn_player_ids=("D",),
                command_id="too-late-withdrawal",
            )

        assert len(
            TournamentEntryFieldStore(session).history(
                run_id="run",
                branch_id="branch",
                event_id="event",
            )
        ) == 1


def test_unresolved_wild_card_capacity_fails_closed_before_commit(database):
    with database.begin() as session:
        stage_initial_field(session, wild_cards=1)

        with pytest.raises(ValueError, match="Wild Card authority"):
            commit_draw_input(session)

        assert session.get(
            TournamentDrawInputAuthorityModel,
            ("run", "branch", "event"),
        ) is None


def test_corrupt_payload_and_read_only_scope_fail_closed(database):
    with database.begin() as session:
        stage_initial_field(session)
        commit_draw_input(session)

    with database.begin() as session:
        row = session.get(
            TournamentDrawInputAuthorityModel,
            ("run", "branch", "event"),
        )
        assert row is not None
        row.payload_json = row.payload_json.replace(
            '"draw_seed":123',
            '"draw_seed":124',
            1,
        )

    with database() as session:
        with pytest.raises(ValueError, match="corrupt"):
            TournamentDrawInputAuthorityStore(session).get(
                run_id="run",
                branch_id="branch",
                event_id="event",
            )

    engine = create_sqlite_engine(
        DatabaseSettings(url="sqlite:///:memory:")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="readonly-run",
                timeline_start_season=2000,
                timeline_end_season=2049,
                read_only=1,
            )
        )
        session.add(
            RunBranchModel(
                run_id="readonly-run",
                branch_id="readonly-branch",
                display_name="Timeline 1",
            )
        )
    with factory.begin() as session:
        with pytest.raises(ValueError, match="not writable"):
            TournamentDrawInputAuthorityStore(session).commit(
                run_id="readonly-run",
                branch_id="readonly-branch",
                event_id="event",
                command_id="commit",
                draw_seed=1,
                main_seed_count=0,
                qualification_seed_count=0,
            )
    engine.dispose()
