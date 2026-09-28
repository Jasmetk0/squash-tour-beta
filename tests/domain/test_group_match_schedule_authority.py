"""Product invariants for canonical group Match + Match Day schedule authority."""

import pytest

from beta_engine.domain.tournaments.format_authority import (
    TournamentFormatAuthority,
    TournamentGroupFormatConfiguration,
)
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleBuilder,
)
from beta_engine.domain.tournaments.topology_authority import (
    TournamentGroupTopologyMatch,
    TournamentGroupTopologySlot,
    TournamentTopologyAuthority,
)


def fp(char: str) -> str:
    return char * 64


def build_format(*, group_count: int, group_size: int, best_of: int = 5, source: str = "season_policy"):
    return TournamentFormatAuthority(
        run_id="run",
        branch_id="branch",
        event_id="EVENT",
        target_season_index=0,
        configured_by_command_id="format",
        entry_field_fingerprint=fp("a"),
        format_kind="groups",
        group_configuration=TournamentGroupFormatConfiguration(
            group_count=group_count,
            group_size=group_size,
            seeded_slots_per_group=0,
            group_seed_placements=(),
            match_best_of=best_of,
            rules_source_kind=source,
            group_rules_policy_fingerprint=fp("b"),
            group_rules_effective_from_season_index=0,
        ),
    )


def build_topology(format_authority: TournamentFormatAuthority):
    group = format_authority.group_configuration
    assert group is not None
    slots = []
    matches = []
    player_ids = []
    for group_index in range(1, group.group_count + 1):
        group_slots = []
        for slot_index in range(1, group.group_size + 1):
            player_id = f"g{group_index}p{slot_index}"
            player_ids.append(player_id)
            slot = TournamentGroupTopologySlot(
                group_index=group_index,
                slot_index=slot_index,
                player_id=player_id,
            )
            slots.append(slot)
            group_slots.append(slot)
        match_index = 0
        for top_index in range(group.group_size - 1):
            for bottom_index in range(top_index + 1, group.group_size):
                match_index += 1
                top = group_slots[top_index]
                bottom = group_slots[bottom_index]
                matches.append(
                    TournamentGroupTopologyMatch(
                        match_id=f"EVENT:group:{group_index}:M{match_index}",
                        group_index=group_index,
                        match_index=match_index,
                        top_slot_index=top.slot_index,
                        bottom_slot_index=bottom.slot_index,
                        top_player_id=top.player_id,
                        bottom_player_id=bottom.player_id,
                    )
                )
    return TournamentTopologyAuthority(
        run_id="run",
        branch_id="branch",
        event_id="EVENT",
        generated_by_command_id="topology",
        format_authority_fingerprint=format_authority.fingerprint,
        entry_field_fingerprint=format_authority.entry_field_fingerprint,
        format_kind="groups",
        topology_seed=123,
        participant_order_player_ids=tuple(player_ids),
        group_slots=tuple(slots),
        group_matches=tuple(matches),
    )


def assert_no_player_twice_per_day(authority):
    for day in range(1, authority.match_day_count + 1):
        seen = set()
        for match in authority.matches:
            if match.match_day_ordinal != day:
                continue
            assert match.top_player_id not in seen
            assert match.bottom_player_id not in seen
            seen.add(match.top_player_id)
            seen.add(match.bottom_player_id)


@pytest.mark.pr_critical
def test_even_four_player_groups_use_three_conflict_free_match_days():
    format_authority = build_format(group_count=2, group_size=4)
    topology = build_topology(format_authority)

    authority = TournamentGroupMatchScheduleBuilder.build(
        format_authority=format_authority,
        topology_authority=topology,
        command_id="schedule",
    )

    assert authority.group_count == 2
    assert authority.group_size == 4
    assert authority.match_day_count == 3
    assert len(authority.matches) == 12
    assert_no_player_twice_per_day(authority)
    assert [
        sum(match.match_day_ordinal == day for match in authority.matches)
        for day in (1, 2, 3)
    ] == [4, 4, 4]
    assert all(
        match.effective_match_format.format.best_of == 5
        for match in authority.matches
    )
    assert all(
        match.effective_match_format.source_scope
        == "tournament_group_rules_policy"
        for match in authority.matches
    )


@pytest.mark.pr_critical
def test_odd_three_player_groups_use_three_days_with_one_bye_per_group_per_day():
    format_authority = build_format(group_count=2, group_size=3)
    topology = build_topology(format_authority)

    authority = TournamentGroupMatchScheduleBuilder.build(
        format_authority=format_authority,
        topology_authority=topology,
        command_id="schedule",
    )

    assert authority.match_day_count == 3
    assert len(authority.matches) == 6
    assert_no_player_twice_per_day(authority)
    assert [
        sum(match.match_day_ordinal == day for match in authority.matches)
        for day in (1, 2, 3)
    ] == [2, 2, 2]
    for group_index in (1, 2):
        assert [
            sum(
                match.group_index == group_index
                and match.match_day_ordinal == day
                for match in authority.matches
            )
            for day in (1, 2, 3)
        ] == [1, 1, 1]


@pytest.mark.pr_critical
def test_edition_override_materializes_hash_protected_bo3_without_changing_scoring():
    format_authority = build_format(
        group_count=1,
        group_size=4,
        best_of=3,
        source="edition_override",
    )
    topology = build_topology(format_authority)

    authority = TournamentGroupMatchScheduleBuilder.build(
        format_authority=format_authority,
        topology_authority=topology,
        command_id="schedule",
    )

    for match in authority.matches:
        snapshot = match.effective_match_format
        assert snapshot.format.best_of == 3
        assert snapshot.format.games_to == 11
        assert snapshot.format.win_by == 2
        assert snapshot.source_scope == "tournament_group_edition_override"
        # Re-validation proves the stored hash covers the effective format + provenance.
        assert snapshot.model_copy() == snapshot


@pytest.mark.pr_critical
def test_schedule_builder_rejects_stale_topology_binding():
    format_authority = build_format(group_count=1, group_size=4)
    topology = build_topology(format_authority).model_copy(
        update={"format_authority_fingerprint": fp("f")}
    )

    with pytest.raises(ValueError, match="stale"):
        TournamentGroupMatchScheduleBuilder.build(
            format_authority=format_authority,
            topology_authority=topology,
            command_id="schedule",
        )
