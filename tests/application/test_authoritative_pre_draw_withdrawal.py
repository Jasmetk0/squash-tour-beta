"""Canonical pre-draw withdrawal command integration."""

from __future__ import annotations

import pytest

from beta_engine.application.canonical_tournament_preparation import (
    CanonicalTournamentPreparationService,
)
from beta_engine.application.authoritative_pre_draw_withdrawal import (
    CanonicalPreDrawWithdrawalCommand,
    CanonicalPreDrawWithdrawalService,
)
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
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
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
def factory(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'canonical-withdrawal.db'}")
    )
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory.begin() as session:
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
    yield session_factory
    engine.dispose()


def _ranking_snapshot():
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    target = RankingWeek(season_index=0, week=3)
    points = {
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
        for player_id in sorted(points)
    )
    results = tuple(
        OfficialRankingResult(
            edition_id=f"prior-{player_id}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}",
            completed_week=completed,
            first_publication_week=published,
            main_points=value,
        )
        for player_id, value in sorted(points.items())
    )
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=target,
        policy=OfficialRankingPolicy(policy_id="policy"),
        players=players,
        results=results,
    )


def _application(player_id: str, window: str) -> TournamentEntryApplication:
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


def _applications() -> tuple[TournamentEntryApplication, ...]:
    return (
        _application("A", "main"),
        _application("C", "main"),
        _application("D", "main"),
        _application("B", "qualification"),
        _application("E", "qualification"),
        _application("F", "qualification"),
        _application("G", "qualification"),
    )


def _stage_initial(factory):
    snapshot = _ranking_snapshot()
    with factory.begin() as session:
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
        TournamentRankingSnapshotAuthorityStore(session).adopt(
            run_id="run",
            branch_id="branch",
            event_id="event",
            ranking_week=snapshot.week,
            command_id="adopt-ranking",
        )
        return TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=_applications(),
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=2,
                qualifier_spots=1,
            ),
            command_id="initial-field",
        )


@pytest.mark.pr_critical
def test_preparation_state_tracks_pre_draw_repair_to_draw_ready(factory):
    initial = _stage_initial(factory)
    preparation = CanonicalTournamentPreparationService(factory)

    before = preparation.inspect(
        run_id="run", branch_id="branch", event_id="event"
    )
    assert before.phase == "draw_input_ready"
    assert before.next_required_action == "review_pre_draw_or_commit_draw_input"
    assert before.entry_field_fingerprint == initial.fingerprint
    assert before.pre_draw_repair_open is True
    assert before.can_apply_pre_draw_withdrawal is True
    assert before.can_commit_draw_input is True
    assert before.ready_for_match_schedule is False
    assert before.authority_source == "run_owned_db_authorities.v1"

    blocked_rollup = preparation.inspect_many(
        run_id="run",
        branch_id="branch",
        event_ids=("event",),
    )
    assert blocked_rollup.ready_for_week_schedule is False
    assert blocked_rollup.blockers == ("event:draw_input_ready",)
    blocked_fingerprint = blocked_rollup.preparation_fingerprint

    repaired = CanonicalPreDrawWithdrawalService(factory).execute(
        CanonicalPreDrawWithdrawalCommand(
            command_id="prep-withdraw-d",
            run_id="run",
            branch_id="branch",
            event_id="event",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("D",),
        )
    )
    after_repair = preparation.inspect(
        run_id="run", branch_id="branch", event_id="event"
    )
    assert after_repair.field_sequence == 2
    assert after_repair.entry_field_fingerprint == repaired.field_fingerprint
    assert after_repair.withdrawn_player_count == 1
    assert after_repair.phase == "draw_input_ready"

    with factory.begin() as session:
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="prep-draw-input",
            draw_seed=5001,
        )
    input_ready = preparation.inspect(
        run_id="run", branch_id="branch", event_id="event"
    )
    assert input_ready.phase == "draw_generation_ready"
    assert input_ready.next_required_action == "generate_draw"
    assert input_ready.draw_input_fingerprint == draw_input.fingerprint
    assert input_ready.pre_draw_repair_open is False
    assert input_ready.can_apply_pre_draw_withdrawal is False
    assert input_ready.can_generate_draw is True

    with factory.begin() as session:
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="prep-draw",
        )
    ready = preparation.inspect(
        run_id="run", branch_id="branch", event_id="event"
    )
    assert ready.phase == "draw_ready"
    assert ready.next_required_action == "none"
    assert ready.initial_draw_fingerprint == draw.fingerprint
    assert ready.effective_draw_fingerprint == draw.fingerprint
    assert ready.ready_for_match_schedule is True
    assert ready.blockers == ()

    ready_rollup = preparation.inspect_many(
        run_id="run",
        branch_id="branch",
        event_ids=("event",),
    )
    assert ready_rollup.ready_for_week_schedule is True
    assert ready_rollup.blockers == ()
    assert ready_rollup.preparation_fingerprint != blocked_fingerprint
    assert ready_rollup.tournaments == (ready,)


def test_main_withdrawal_promotes_q_and_backfills_from_frozen_inputs(factory):
    initial = _stage_initial(factory)
    service = CanonicalPreDrawWithdrawalService(factory)
    command = CanonicalPreDrawWithdrawalCommand(
        command_id="withdraw-d",
        run_id="run",
        branch_id="branch",
        event_id="event",
        expected_field_fingerprint=initial.fingerprint,
        withdrawn_player_ids=("D",),
    )

    result = service.execute(command)

    assert result.field_sequence == 2
    assert result.newly_withdrawn_player_ids == ("D",)
    assert result.promoted_to_main_player_ids == ("B",)
    assert result.qualification_backfill_player_ids == ("F",)
    assert result.direct_main_player_ids == ("A", "B", "C")
    assert result.qualification_player_ids == ("E", "F")
    assert result.below_qualification_cut_player_ids == ("G",)
    assert result.withdrawn_player_ids == ("D",)
    assert result.predecessor_field_fingerprint != result.field_fingerprint

    # Exact retry is a pure replay of the already-persisted command/result.
    assert service.execute(command) == result


def test_followup_qualification_withdrawal_backfills_without_changing_main(factory):
    initial = _stage_initial(factory)
    service = CanonicalPreDrawWithdrawalService(factory)
    first = service.execute(
        CanonicalPreDrawWithdrawalCommand(
            command_id="withdraw-d",
            run_id="run",
            branch_id="branch",
            event_id="event",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("D",),
        )
    )

    second = service.execute(
        CanonicalPreDrawWithdrawalCommand(
            command_id="withdraw-e",
            run_id="run",
            branch_id="branch",
            event_id="event",
            expected_field_fingerprint=first.field_fingerprint,
            withdrawn_player_ids=("E",),
        )
    )

    assert second.field_sequence == 3
    assert second.predecessor_field_fingerprint == first.field_fingerprint
    assert second.newly_withdrawn_player_ids == ("E",)
    assert second.promoted_to_main_player_ids == ()
    assert second.qualification_backfill_player_ids == ("G",)
    assert second.direct_main_player_ids == ("A", "B", "C")
    assert second.qualification_player_ids == ("F", "G")
    assert second.withdrawn_player_ids == ("D", "E")

    # The first historical command remains an exact replay even after a later
    # repair version advanced the event field.
    replayed_first = service.execute(
        CanonicalPreDrawWithdrawalCommand(
            command_id="withdraw-d",
            run_id="run",
            branch_id="branch",
            event_id="event",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("D",),
        )
    )
    assert replayed_first == first


def test_command_id_reuse_with_different_withdrawal_fails_closed(factory):
    initial = _stage_initial(factory)
    service = CanonicalPreDrawWithdrawalService(factory)
    service.execute(
        CanonicalPreDrawWithdrawalCommand(
            command_id="withdraw-player",
            run_id="run",
            branch_id="branch",
            event_id="event",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("D",),
        )
    )

    with pytest.raises(TournamentEntryFieldConflict, match="different request"):
        service.execute(
            CanonicalPreDrawWithdrawalCommand(
                command_id="withdraw-player",
                run_id="run",
                branch_id="branch",
                event_id="event",
                expected_field_fingerprint=initial.fingerprint,
                withdrawn_player_ids=("E",),
            )
        )


def test_missing_initial_field_fails_closed(factory):
    service = CanonicalPreDrawWithdrawalService(factory)

    with pytest.raises(
        TournamentEntryFieldConflict,
        match="requires an initial Tournament Entry Field",
    ):
        service.execute(
            CanonicalPreDrawWithdrawalCommand(
                command_id="withdraw-d",
                run_id="run",
                branch_id="branch",
                event_id="event",
                expected_field_fingerprint="0" * 64,
                withdrawn_player_ids=("D",),
            )
        )

def test_multi_withdrawal_is_atomic_and_input_order_independent(factory):
    initial = _stage_initial(factory)
    service = CanonicalPreDrawWithdrawalService(factory)

    result = service.execute(
        CanonicalPreDrawWithdrawalCommand(
            command_id="withdraw-d-e",
            run_id="run",
            branch_id="branch",
            event_id="event",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("E", "D"),
        )
    )

    assert result.newly_withdrawn_player_ids == ("D", "E")
    assert result.promoted_to_main_player_ids == ("B",)
    assert result.qualification_backfill_player_ids == ("F", "G")
    assert result.direct_main_player_ids == ("A", "B", "C")
    assert result.qualification_player_ids == ("F", "G")
    assert result.withdrawn_player_ids == ("D", "E")


def test_draw_commit_locks_new_repairs_but_keeps_exact_retry(factory):
    initial = _stage_initial(factory)
    service = CanonicalPreDrawWithdrawalService(factory)
    command = CanonicalPreDrawWithdrawalCommand(
        command_id="withdraw-d",
        run_id="run",
        branch_id="branch",
        event_id="event",
        expected_field_fingerprint=initial.fingerprint,
        withdrawn_player_ids=("D",),
    )
    result = service.execute(command)

    with factory.begin() as session:
        TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="commit-draw",
            draw_seed=123,
        )

    # Historical exact retry remains valid after the draw commitment.
    assert service.execute(command) == result

    with pytest.raises(
        TournamentEntryFieldConflict,
        match="locked after Tournament Draw Input authority is committed",
    ):
        service.execute(
            CanonicalPreDrawWithdrawalCommand(
                command_id="withdraw-e",
                run_id="run",
                branch_id="branch",
                event_id="event",
                expected_field_fingerprint=result.field_fingerprint,
                withdrawn_player_ids=("E",),
            )
        )


def test_stale_expected_field_fingerprint_fails_closed(factory):
    initial = _stage_initial(factory)
    service = CanonicalPreDrawWithdrawalService(factory)
    first = service.execute(
        CanonicalPreDrawWithdrawalCommand(
            command_id="withdraw-d",
            run_id="run",
            branch_id="branch",
            event_id="event",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("D",),
        )
    )
    assert first.field_fingerprint != initial.fingerprint

    with pytest.raises(
        TournamentEntryFieldConflict,
        match="changed since the withdrawal command was prepared",
    ):
        service.execute(
            CanonicalPreDrawWithdrawalCommand(
                command_id="withdraw-e-stale",
                run_id="run",
                branch_id="branch",
                event_id="event",
                expected_field_fingerprint=initial.fingerprint,
                withdrawn_player_ids=("E",),
            )
        )