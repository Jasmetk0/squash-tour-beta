"""Persistence acceptance for Finals Tournament Format -> group topology."""

import pytest
from sqlalchemy import delete

from beta_engine.application.canonical_tournament_preparation import (
    CanonicalTournamentPreparationService,
)
from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    calculate_world_tour_finals_race,
    select_world_tour_finals_participants,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.format_authority import (
    TournamentGroupCrossingMatch,
    TournamentGroupCrossingSource,
    TournamentGroupSeedPlacement,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionStore,
)
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
    TournamentEntryFieldVersionModel,
    TournamentFormatAuthorityModel,
    TournamentGroupRulesPolicyModel,
    TournamentGroupMatchScheduleAuthorityModel,
    TournamentTopologyAuthorityModel,
    WorldTourFinalsRaceConfigurationModel,
    WorldTourFinalsRaceSnapshotModel,
    WorldTourFinalsParticipantSelectionConfigurationModel,
    WorldTourFinalsParticipantSelectionSnapshotModel,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_format_authority import (
    TournamentFormatAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_group_rules_policy import (
    TournamentGroupRulesPolicyStore,
)
from beta_engine.infrastructure.db.tournament_group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_topology_authority import (
    TournamentTopologyAuthorityStore,
)


def fp(char: str) -> str:
    return char * 64


@pytest.fixture
def finals_database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'format-topology.db'}")
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
        session.flush()

        race_config = WorldTourFinalsRaceConfiguration(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            finals_event_id="FINALS",
            eligible_categories=("DIAMOND",),
            best_n=2,
            cutoff_week=RankingWeek(season_index=0, week=10),
            cutoff_official_ranking_fingerprint=fp("a"),
            cutoff_transition_fingerprint=fp("b"),
            calendar_content_fingerprint=fp("c"),
            adopted_by_command_id="race-config",
        )
        race = calculate_world_tour_finals_race(
            WorldTourFinalsRaceInput(
                run_id="run",
                branch_id="branch",
                target_season_index=0,
                cutoff_week=race_config.cutoff_week,
                cutoff_official_ranking_fingerprint=(
                    race_config.cutoff_official_ranking_fingerprint
                ),
                eligibility_fingerprint=race_config.eligibility_fingerprint,
                policy_id=race_config.policy_id,
                best_n=race_config.best_n,
                players=tuple(
                    WorldTourFinalsRacePlayer(
                        player_id=f"p{index}",
                        tie_break_token=f"token-{index:02d}",
                    )
                    for index in range(1, 7)
                ),
                eligible_results=(),
            )
        )
        config = WorldTourFinalsParticipantSelectionConfiguration(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            finals_event_id="FINALS",
            participant_capacity=6,
            direct_entry_event_ids=(),
            race_snapshot_fingerprint=race.fingerprint,
            calendar_content_fingerprint=race_config.calendar_content_fingerprint,
            adopted_by_command_id="participants-config",
        )
        selected = select_world_tour_finals_participants(
            configuration=config,
            race_snapshot=race,
            direct_entry_winners=(),
        )
        race_store = WorldTourFinalsRaceAuthorityStore(session)
        race_store.put_configuration(race_config)
        race_store.put_snapshot(race)
        selection_store = WorldTourFinalsParticipantSelectionStore(session)
        selection_store.put_configuration(config)
        selection_store.put_snapshot(selected)
        TournamentEntryFieldStore(
            session
        ).stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="entry",
        )
    yield factory
    engine.dispose()


@pytest.mark.pr_critical
def test_season_group_rules_versions_resolve_without_rewriting_history(finals_database):
    with finals_database.begin() as session:
        store = TournamentGroupRulesPolicyStore(session)
        season0 = store.adopt(
            run_id="run",
            branch_id="branch",
            effective_from_season_index=0,
            command_id="group-rules-s0",
            default_match_best_of=5,
        )
        season3 = store.adopt(
            run_id="run",
            branch_id="branch",
            effective_from_season_index=3,
            command_id="group-rules-s3",
            default_match_best_of=3,
        )

        assert store.resolve(
            run_id="run", branch_id="branch", target_season_index=0
        ) == season0
        assert store.resolve(
            run_id="run", branch_id="branch", target_season_index=2
        ) == season0
        assert store.resolve(
            run_id="run", branch_id="branch", target_season_index=3
        ) == season3
        assert store.resolve(
            run_id="run", branch_id="branch", target_season_index=49
        ) == season3


@pytest.mark.pr_critical
def test_finals_groups_format_and_topology_replay_from_race_seed_order(finals_database):
    with finals_database.begin() as session:
        group_rules = TournamentGroupRulesPolicyStore(session).adopt(
            run_id="run",
            branch_id="branch",
            effective_from_season_index=0,
            command_id="group-rules",
            default_match_best_of=5,
        )
        format_authority = TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="format-groups",
            format_kind="groups",
            group_count=2,
            group_size=3,
            seeded_slots_per_group=1,
            group_seed_placements=(
                TournamentGroupSeedPlacement(
                    seed_number=1, group_index=1, slot_index=1
                ),
                TournamentGroupSeedPlacement(
                    seed_number=2, group_index=2, slot_index=1
                ),
            ),
        )
        topology = TournamentTopologyAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="topology-groups",
            topology_seed=777,
        )
        schedule = TournamentGroupMatchScheduleAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="group-match-schedule",
        )

        assert (
            format_authority.group_configuration.group_rules_policy_fingerprint
            == group_rules.fingerprint
        )
        assert topology.participant_order_player_ids == tuple(
            f"p{index}" for index in range(1, 7)
        )
        assert topology.group_slots[0].player_id == "p1"
        assert topology.group_slots[3].player_id == "p2"
        assert len(topology.group_matches) == 6
        assert schedule.match_day_count == 3
        assert len(schedule.matches) == 6
        assert all(
            match.effective_match_format.format.best_of == 5
            for match in schedule.matches
        )
        assert TournamentGroupMatchScheduleAuthorityStore(session).get(
            run_id="run", branch_id="branch", event_id="FINALS"
        ) == schedule
        assert TournamentFormatAuthorityStore(session).get(
            run_id="run", branch_id="branch", event_id="FINALS"
        ) == format_authority
        assert TournamentTopologyAuthorityStore(session).get(
            run_id="run", branch_id="branch", event_id="FINALS"
        ) == topology

    state = CanonicalTournamentPreparationService(finals_database).inspect(
        run_id="run",
        branch_id="branch",
        event_id="FINALS",
    )
    assert state.phase == "group_match_execution_ready"
    assert state.next_required_action == "none"
    assert state.blockers == ()
    assert state.format_authority_ready is True
    assert state.format_kind == "groups"
    assert state.topology_ready is True
    assert state.topology_group_match_count == 6
    assert state.group_match_schedule_ready is True
    assert state.group_match_count == 6
    assert state.group_match_day_count == 3
    assert state.group_match_schedule_fingerprint == schedule.fingerprint
    assert state.ready_for_match_schedule is True


@pytest.mark.pr_critical
def test_finals_hybrid_keeps_explicit_group_result_crossing(finals_database):
    with finals_database.begin() as session:
        TournamentGroupRulesPolicyStore(session).adopt(
            run_id="run",
            branch_id="branch",
            effective_from_season_index=0,
            command_id="group-rules",
            default_match_best_of=5,
        )
        crossings = (
            TournamentGroupCrossingMatch(
                match_index=1,
                top=TournamentGroupCrossingSource(
                    group_index=1, finishing_position=1
                ),
                bottom=TournamentGroupCrossingSource(
                    group_index=2, finishing_position=1
                ),
            ),
        )
        format_authority = TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="format-hybrid",
            format_kind="groups_knockout",
            group_count=2,
            group_size=3,
            seeded_slots_per_group=1,
            group_seed_placements=(
                TournamentGroupSeedPlacement(
                    seed_number=1, group_index=1, slot_index=1
                ),
                TournamentGroupSeedPlacement(
                    seed_number=2, group_index=2, slot_index=1
                ),
            ),
            advancing_per_group=1,
            knockout_crossings=crossings,
        )
        topology = TournamentTopologyAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="topology-hybrid",
            topology_seed=888,
        )

        assert format_authority.format_kind == "groups_knockout"
        assert topology.hybrid_first_round_crossings == crossings
        assert topology.knockout_draw_fingerprint is None


@pytest.mark.pr_critical
def test_group_format_rejects_unequal_or_partial_participant_partition(finals_database):
    with finals_database.begin() as session:
        TournamentGroupRulesPolicyStore(session).adopt(
            run_id="run",
            branch_id="branch",
            effective_from_season_index=0,
            command_id="group-rules",
            default_match_best_of=5,
        )
        with pytest.raises(ValueError, match="exactly partition"):
            TournamentFormatAuthorityStore(session).configure(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
                command_id="bad-format",
                format_kind="groups",
                group_count=2,
                group_size=4,
            )


@pytest.mark.pr_critical
def test_saved_revision_restores_group_rules_format_and_topology_chain(finals_database):
    with finals_database.begin() as session:
        policy = TournamentGroupRulesPolicyStore(session).adopt(
            run_id="run",
            branch_id="branch",
            effective_from_season_index=0,
            command_id="group-rules",
            default_match_best_of=5,
        )
        format_authority = TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="format-groups",
            format_kind="groups",
            group_count=2,
            group_size=3,
            seeded_slots_per_group=1,
            group_seed_placements=(
                TournamentGroupSeedPlacement(
                    seed_number=1, group_index=1, slot_index=1
                ),
                TournamentGroupSeedPlacement(
                    seed_number=2, group_index=2, slot_index=1
                ),
            ),
        )
        topology = TournamentTopologyAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="topology-groups",
            topology_seed=999,
        )
        schedule = TournamentGroupMatchScheduleAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="group-match-schedule",
        )

        target_payload = {"content": {}}
        capture_saved_simulation_slots(
            session,
            target_payload,
            run_id="run",
            branch_id="branch",
        )
        component = target_payload["content"]["simulation_slot_match_state"]
        assert len(component["group_rules_policies"]) == 1
        assert len(component["format_authorities"]) == 1
        assert len(component["topology_authorities"]) == 1
        assert len(component["group_match_schedules"]) == 1

        for model in (
            TournamentGroupMatchScheduleAuthorityModel,
            TournamentTopologyAuthorityModel,
            TournamentFormatAuthorityModel,
            TournamentGroupRulesPolicyModel,
            TournamentEntryFieldVersionModel,
            WorldTourFinalsParticipantSelectionSnapshotModel,
            WorldTourFinalsParticipantSelectionConfigurationModel,
            WorldTourFinalsRaceSnapshotModel,
            WorldTourFinalsRaceConfigurationModel,
        ):
            session.execute(
                delete(model).where(
                    model.run_id == "run",
                    model.branch_id == "branch",
                )
            )
        session.flush()

        current_payload = {"content": {}}
        capture_saved_simulation_slots(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert "simulation_slot_match_state" not in current_payload["content"]

        restore_saved_simulation_slots(
            session,
            current_payload=current_payload,
            target_payload=target_payload,
            run_id="run",
            branch_id="branch",
        )

        assert TournamentGroupRulesPolicyStore(session).resolve(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        ) == policy
        assert TournamentFormatAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == format_authority
        assert TournamentTopologyAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == topology
        assert TournamentGroupMatchScheduleAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == schedule

