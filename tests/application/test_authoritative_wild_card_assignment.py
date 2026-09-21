import pytest

from beta_engine.application.authoritative_wild_card_assignment import (
    AuthoritativeWildCardAssignmentService,
    AuthoritativeWildCardCommitCommand,
    AuthoritativeWildCardReviewRequest,
    EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID,
)
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
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
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    DefinitiveWildCardAssignmentStore,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    Base,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    RunEntryDecisionSlotAuthorityModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityConflict,
    wild_card_decision_slot_ordinals,
)


WEEK = RankingWeek(season_index=0, week=3)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'wc-admin.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def _lifecycle_player(player_id: str, *, pre_tour: bool = False):
    position = season_week_to_calendar_position(2000, WEEK.week)
    birth_year = 1980
    birth_week = 1
    return PlayerLifecycleIdentity(
        player_id=player_id,
        birth_year=birth_year,
        birth_year_week=birth_week,
        tie_break_token=f"token-{player_id}",
        tie_break_provenance="canonical WC Admin test",
        tour_entry_week=(
            None if pre_tour else RankingWeek(season_index=0, week=1)
        ),
        age=age_at_calendar_position(
            birth_year=birth_year,
            birth_year_week=birth_week,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        ),
        status="active",
        origin="test",
    )


def _ranking():
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    values = {
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
            edition_id=f"prior-{player_id}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}",
            completed_week=completed,
            first_publication_week=published,
            main_points=points,
        )
        for player_id, points in sorted(values.items())
    )
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        policy=OfficialRankingPolicy(policy_id="ranking-policy"),
        players=players,
        results=results,
    )


def _app(player_id: str, window: str):
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


def _install_world(session):
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Run",
            storage_kind="custom_local",
            read_only=0,
            timeline_start_season=2000,
            timeline_end_season=2049,
            official_branch_id="branch",
            status="working",
        )
    )
    session.add(
        RunBranchModel(
            run_id="run",
            branch_id="branch",
            display_name="Timeline 1",
            status="active",
            read_only=0,
            saved_head_revision_id="revision-1",
        )
    )
    ranking = _ranking()
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=WEEK.ordinal,
            snapshot_fingerprint=ranking.fingerprint,
            payload_json=ranking.model_dump_json(),
        )
    )
    session.add(
        AuthoritativeWorldStateModel(
            run_id="run",
            branch_id="branch",
            current_ordinal=WEEK.ordinal,
            ranking_fingerprint=ranking.fingerprint,
        )
    )
    put_lifecycle(
        session,
        PlayerLifecycleWeekState(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            players=tuple(
                sorted(
                    (
                        *(_lifecycle_player(player_id) for player_id in "ABCDEFG"),
                        _lifecycle_player("PROSPECT", pre_tour=True),
                    ),
                    key=lambda player: player.player_id,
                )
            ),
            source_initial_world_fingerprint="world",
        ),
    )
    TournamentRankingSnapshotAuthorityStore(session).adopt(
        run_id="run",
        branch_id="branch",
        event_id="event",
        ranking_week=WEEK,
        command_id="adopt-ranking",
    )
    field = TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=(
            _app("A", "main"),
            _app("C", "main"),
            _app("D", "main"),
            _app("B", "qualification"),
            _app("E", "qualification"),
            _app("F", "qualification"),
            _app("G", "qualification"),
        ),
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
            wild_card_slots=1,
        ),
        command_id="initial-field",
    )
    session.flush()
    return field


def _request():
    return AuthoritativeWildCardReviewRequest(
        command_id="admin-wc-review-1",
        original_wild_card_player_ids=("A",),
        reserve_wild_card_player_ids=("PROSPECT",),
        unavailable_player_ids=(),
        operator_label="Commissioner",
        reason="Explicit pre-alpha review; automatic WC eligibility is not defined.",
    )


@pytest.mark.pr_critical
def test_preview_and_commit_release_direct_holder_to_rwc_and_create_tour_entry(database):
    with database.begin() as session:
        field = _install_world(session)
        assert field.direct_main_player_ids == ("A", "C")
        assert field.qualification_player_ids == ("B", "D")

    service = AuthoritativeWildCardAssignmentService(database)
    preview = service.preview(
        run_id="run",
        branch_id="branch",
        event_id="event",
        request=_request(),
    )

    assert preview.persisted is False
    assert preview.week == WEEK
    assert preview.decision_slot_ordinal == 1
    assert preview.authority.schema_version == "tournament_wild_card_authority.v3"
    assert (
        preview.authority.selection_policy_id
        == EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID
    )
    assert preview.authority.operator_label == "Commissioner"
    assert preview.authority.slots[0].released_because_direct_acceptance is True
    assert preview.authority.slots[0].source == "reserve_wc"
    assert preview.authority.slots[0].active_player_id == "PROSPECT"
    assert preview.authority.slots[0].reserve_ordinal == 1
    assert tuple(item.player_id for item in preview.definitive_assignments) == (
        "PROSPECT",
    )
    assert preview.first_tour_entry_source_player_ids == ("PROSPECT",)

    command = AuthoritativeWildCardCommitCommand(
        **_request().model_dump(),
        expected_week=preview.week,
        expected_revision_id=preview.expected_revision_id,
        expected_decision_slot_ordinal=preview.decision_slot_ordinal,
        expected_proposal_fingerprint=preview.proposal_fingerprint,
    )
    committed = service.commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command=command,
    )
    assert committed.adoption == "committed"
    assert committed.authority == preview.authority
    assert len(committed.assignment_results) == 1
    assert committed.assignment_results[0].assignment.player_id == "PROSPECT"
    assert (
        committed.assignment_results[0].assignment_is_first_tour_entry_source
        is True
    )

    retry = service.commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command=command,
    )
    assert retry.model_copy(update={"adoption": "committed"}) == committed

    with database() as session:
        assignments = DefinitiveWildCardAssignmentStore(session).list(
            run_id="run",
            branch_id="branch",
        )
        assert len(assignments) == 1
        trigger = PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="PROSPECT",
        )
        assert trigger is not None
        assert trigger.trigger_kind == "definitive_wild_card_assignment"
        assert trigger.trigger_week == WEEK
        assert trigger.decision_slot_ordinal == 1
        assert wild_card_decision_slot_ordinals(
            session,
            run_id="run",
            branch_id="branch",
            week_ordinal=WEEK.ordinal,
        ) == {1}


@pytest.mark.pr_critical
def test_preview_cannot_overtake_unresolved_entry_slot(database):
    with database.begin() as session:
        _install_world(session)
        session.add(
            RunEntryDecisionSlotAuthorityModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=WEEK.ordinal,
                decision_slot_ordinal=1,
                fingerprint="a" * 64,
                payload_json="{}",
            )
        )

    with pytest.raises(
        TournamentWildCardAuthorityConflict,
        match="unresolved Entry decision slot",
    ):
        AuthoritativeWildCardAssignmentService(database).preview(
            run_id="run",
            branch_id="branch",
            event_id="event",
            request=_request(),
        )
