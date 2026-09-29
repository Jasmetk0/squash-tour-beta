"""Domain coverage for groups+knockout entrant materialization."""

import pytest

from beta_engine.domain.tournaments.format_authority import (
    TournamentGroupCrossingMatch,
    TournamentGroupCrossingSource,
)
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupResultReceipt,
    TournamentGroupStanding,
    TournamentGroupStandingRow,
    TournamentGroupStandingsAuthority,
)
from beta_engine.domain.tournaments.hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsBuilder,
)
from beta_engine.domain.tournaments.topology_authority import (
    TournamentGroupTopologyMatch,
    TournamentGroupTopologySlot,
    TournamentTopologyAuthority,
)


def fp(char: str) -> str:
    return char * 64


def topology() -> TournamentTopologyAuthority:
    return TournamentTopologyAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="topology",
        format_authority_fingerprint=fp("a"),
        entry_field_fingerprint=fp("b"),
        format_kind="groups_knockout",
        topology_seed=123,
        participant_order_player_ids=("A", "B", "C", "D"),
        group_slots=(
            TournamentGroupTopologySlot(group_index=1, slot_index=1, player_id="A"),
            TournamentGroupTopologySlot(group_index=1, slot_index=2, player_id="B"),
            TournamentGroupTopologySlot(group_index=2, slot_index=1, player_id="C"),
            TournamentGroupTopologySlot(group_index=2, slot_index=2, player_id="D"),
        ),
        group_matches=(
            TournamentGroupTopologyMatch(
                match_id="g1",
                group_index=1,
                match_index=1,
                top_slot_index=1,
                bottom_slot_index=2,
                top_player_id="A",
                bottom_player_id="B",
            ),
            TournamentGroupTopologyMatch(
                match_id="g2",
                group_index=2,
                match_index=1,
                top_slot_index=1,
                bottom_slot_index=2,
                top_player_id="C",
                bottom_player_id="D",
            ),
        ),
        hybrid_first_round_crossings=(
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


def standing_row(group: int, position: int, player: str) -> TournamentGroupStandingRow:
    return TournamentGroupStandingRow(
        group_index=group,
        position=position,
        player_id=player,
        wins=1 if position == 1 else 0,
        losses=0 if position == 1 else 1,
        group_points=4 if position == 1 else 0,
        played_matches=1,
        games_won=2 if position == 1 else 0,
        games_lost=0 if position == 1 else 2,
        points_won=22 if position == 1 else 10,
        points_lost=10 if position == 1 else 22,
    )


def standings() -> TournamentGroupStandingsAuthority:
    return TournamentGroupStandingsAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="standings",
        group_match_schedule_fingerprint=fp("c"),
        group_rules_policy_fingerprint=fp("d"),
        source_results=(
            TournamentGroupResultReceipt(
                match_id="g1",
                group_index=1,
                result_fingerprint=fp("1"),
                result_kind="played",
                winner_player_id="A",
                loser_player_id="B",
                best_of=3,
                termination_reason="COMPLETED",
            ),
            TournamentGroupResultReceipt(
                match_id="g2",
                group_index=2,
                result_fingerprint=fp("2"),
                result_kind="played",
                winner_player_id="C",
                loser_player_id="D",
                best_of=3,
                termination_reason="COMPLETED",
            ),
        ),
        groups=(
            TournamentGroupStanding(
                group_index=1,
                rows=(
                    standing_row(1, 1, "A"),
                    standing_row(1, 2, "B"),
                ),
            ),
            TournamentGroupStanding(
                group_index=2,
                rows=(
                    standing_row(2, 1, "C"),
                    standing_row(2, 2, "D"),
                ),
            ),
        ),
    )


@pytest.mark.pr_critical
def test_hybrid_entrants_follow_configured_group_crossings_without_reseeding():
    authority = TournamentHybridKnockoutEntrantsBuilder.build(
        topology=topology(),
        standings=standings(),
        command_id="hybrid-entrants",
    )

    assert authority.source_policy_id == "configured_group_crossings_no_reseed.v1"
    assert tuple(
        (
            match.match_index,
            match.top_player_id,
            match.bottom_player_id,
        )
        for match in authority.first_round_matches
    ) == (
        (1, "A", "D"),
        (2, "C", "B"),
    )
    assert authority.first_round_matches[0].top_source.group_index == 1
    assert authority.first_round_matches[0].bottom_source.finishing_position == 2


@pytest.mark.pr_critical
def test_hybrid_entrants_reject_non_hybrid_topology():
    wrong = topology().model_copy(
        update={
            "format_kind": "groups",
            "hybrid_first_round_crossings": (),
        }
    )
    with pytest.raises(ValueError, match="groups\+knockout"):
        TournamentHybridKnockoutEntrantsBuilder.build(
            topology=wrong,
            standings=standings(),
            command_id="hybrid-entrants",
        )


@pytest.mark.pr_critical
def test_hybrid_entrants_reject_standings_from_another_event():
    wrong = standings().model_copy(update={"event_id": "other"})
    with pytest.raises(ValueError, match="scope mismatch"):
        TournamentHybridKnockoutEntrantsBuilder.build(
            topology=topology(),
            standings=wrong,
            command_id="hybrid-entrants",
        )
