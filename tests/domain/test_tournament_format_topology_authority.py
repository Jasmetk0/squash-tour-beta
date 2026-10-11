"""Product invariants for season-versioned Tournament Format / Topology authority."""

import pytest

from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionSnapshot,
    WorldTourFinalsSelectedPlayer,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldResolver
from beta_engine.domain.tournaments.format_authority import (
    TournamentFormatAuthority,
    TournamentGroupCrossingMatch,
    TournamentGroupCrossingSource,
    TournamentGroupFormatConfiguration,
    TournamentGroupSeedPlacement,
)
from beta_engine.domain.tournaments.topology_authority import (
    TournamentTopologyAuthorityBuilder,
)


def fp(char: str) -> str:
    return char * 64


def finals_field(count: int = 6):
    selected = WorldTourFinalsParticipantSelectionSnapshot(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=count,
        configuration_fingerprint=fp("a"),
        race_snapshot_fingerprint=fp("b"),
        direct_entry_winner_event_ids=(),
        participants=tuple(
            WorldTourFinalsSelectedPlayer(
                player_id=f"p{index}",
                race_rank=index,
                race_points=1000 - index,
                seed=index,
                qualification_source="race",
            )
            for index in range(1, count + 1)
        ),
    )
    return (
        selected,
        TournamentEntryFieldResolver.build_from_finals_participant_selection(
            selection=selected
        ),
    )


@pytest.mark.pr_critical
def test_group_configuration_requires_explicit_balanced_seed_slots():
    with pytest.raises(ValueError, match="same configured seed count"):
        TournamentGroupFormatConfiguration(
            group_count=2,
            group_size=3,
            seeded_slots_per_group=1,
            group_seed_placements=(
                TournamentGroupSeedPlacement(
                    seed_number=1, group_index=1, slot_index=1
                ),
                TournamentGroupSeedPlacement(
                    seed_number=2, group_index=1, slot_index=2
                ),
            ),
            match_best_of=5,
            rules_source_kind="season_policy",
            group_rules_policy_fingerprint=fp("c"),
            group_rules_effective_from_season_index=0,
        )


@pytest.mark.pr_critical
def test_hybrid_crossing_uses_every_advancing_group_position_exactly_once():
    config = TournamentGroupFormatConfiguration(
        group_count=2,
        group_size=4,
        seeded_slots_per_group=1,
        group_seed_placements=(
            TournamentGroupSeedPlacement(
                seed_number=1, group_index=1, slot_index=1
            ),
            TournamentGroupSeedPlacement(
                seed_number=2, group_index=2, slot_index=1
            ),
        ),
        match_best_of=5,
        rules_source_kind="season_policy",
        group_rules_policy_fingerprint=fp("c"),
        group_rules_effective_from_season_index=0,
        advancing_per_group=2,
        knockout_crossings=(
            TournamentGroupCrossingMatch(
                match_index=1,
                top=TournamentGroupCrossingSource(
                    group_index=1, finishing_position=1
                ),
                bottom=TournamentGroupCrossingSource(
                    group_index=2, finishing_position=2
                ),
            ),
            TournamentGroupCrossingMatch(
                match_index=2,
                top=TournamentGroupCrossingSource(
                    group_index=2, finishing_position=1
                ),
                bottom=TournamentGroupCrossingSource(
                    group_index=1, finishing_position=2
                ),
            ),
        ),
    )
    authority = TournamentFormatAuthority(
        run_id="run",
        branch_id="branch",
        event_id="EVENT",
        target_season_index=0,
        configured_by_command_id="format",
        entry_field_fingerprint=fp("d"),
        format_kind="groups_knockout",
        group_configuration=config,
    )
    assert authority.group_configuration == config

    duplicated = config.model_copy(
        update={
            "knockout_crossings": (
                config.knockout_crossings[0],
                TournamentGroupCrossingMatch(
                    match_index=2,
                    top=TournamentGroupCrossingSource(
                        group_index=1, finishing_position=1
                    ),
                    bottom=TournamentGroupCrossingSource(
                        group_index=2, finishing_position=1
                    ),
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="every advancing group position"):
        TournamentFormatAuthority(
            run_id="run",
            branch_id="branch",
            event_id="EVENT",
            target_season_index=0,
            configured_by_command_id="format",
            entry_field_fingerprint=fp("d"),
            format_kind="groups_knockout",
            group_configuration=duplicated,
        )


@pytest.mark.pr_critical
def test_finals_group_topology_keeps_race_seeds_and_randomizes_only_unseeded():
    selected, field = finals_field(6)
    format_authority = TournamentFormatAuthority(
        run_id="run",
        branch_id="branch",
        event_id="FINALS",
        target_season_index=0,
        configured_by_command_id="format",
        entry_field_fingerprint=field.fingerprint,
        format_kind="groups",
        group_configuration=TournamentGroupFormatConfiguration(
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
            match_best_of=5,
            rules_source_kind="season_policy",
            group_rules_policy_fingerprint=fp("c"),
            group_rules_effective_from_season_index=0,
        ),
    )

    first = TournamentTopologyAuthorityBuilder.build_groups(
        format_authority=format_authority,
        entry_field=field,
        participant_order_player_ids=field.seed_order_player_ids,
        command_id="topology",
        topology_seed=12345,
    )
    replay = TournamentTopologyAuthorityBuilder.build_groups(
        format_authority=format_authority,
        entry_field=field,
        participant_order_player_ids=field.seed_order_player_ids,
        command_id="topology",
        topology_seed=12345,
    )

    assert replay == first
    assert first.group_slots[0].player_id == selected.participants[0].player_id
    assert first.group_slots[0].seed_number == 1
    assert first.group_slots[3].player_id == selected.participants[1].player_id
    assert first.group_slots[3].seed_number == 2
    assert {
        slot.player_id for slot in first.group_slots if slot.seed_number is None
    } == {"p3", "p4", "p5", "p6"}
    assert len(first.group_matches) == 6
    assert all(
        match.top_player_id != match.bottom_player_id
        for match in first.group_matches
    )


@pytest.mark.pr_critical
def test_hybrid_topology_carries_group_result_crossing_not_race_player_ids():
    _, field = finals_field(8)
    crossings = (
        TournamentGroupCrossingMatch(
            match_index=1,
            top=TournamentGroupCrossingSource(group_index=1, finishing_position=1),
            bottom=TournamentGroupCrossingSource(group_index=2, finishing_position=2),
        ),
        TournamentGroupCrossingMatch(
            match_index=2,
            top=TournamentGroupCrossingSource(group_index=2, finishing_position=1),
            bottom=TournamentGroupCrossingSource(group_index=1, finishing_position=2),
        ),
    )
    format_authority = TournamentFormatAuthority(
        run_id="run",
        branch_id="branch",
        event_id="FINALS",
        target_season_index=0,
        configured_by_command_id="format",
        entry_field_fingerprint=field.fingerprint,
        format_kind="groups_knockout",
        group_configuration=TournamentGroupFormatConfiguration(
            group_count=2,
            group_size=4,
            seeded_slots_per_group=1,
            group_seed_placements=(
                TournamentGroupSeedPlacement(
                    seed_number=1, group_index=1, slot_index=1
                ),
                TournamentGroupSeedPlacement(
                    seed_number=2, group_index=2, slot_index=1
                ),
            ),
            match_best_of=5,
            rules_source_kind="season_policy",
            group_rules_policy_fingerprint=fp("c"),
            group_rules_effective_from_season_index=0,
            advancing_per_group=2,
            knockout_crossings=crossings,
        ),
    )

    topology = TournamentTopologyAuthorityBuilder.build_groups(
        format_authority=format_authority,
        entry_field=field,
        participant_order_player_ids=field.seed_order_player_ids,
        command_id="topology",
        topology_seed=99,
    )

    assert topology.hybrid_first_round_crossings == crossings
    serialized = topology.model_dump_json()
    assert '"finishing_position":1' in serialized
    assert '"finishing_position":2' in serialized
    # Crossing owns standings positions, never Race player identities.
    crossing_json = [
        crossing.model_dump(mode="json")
        for crossing in topology.hybrid_first_round_crossings
    ]
    assert all("player_id" not in str(item) for item in crossing_json)
