"""Domain coverage for the complete post-group hybrid knockout tree."""

import pytest

from beta_engine.domain.tournaments.format_authority import TournamentGroupCrossingSource
from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthority,
    TournamentHybridKnockoutBracketBuilder,
)
from beta_engine.domain.tournaments.hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsAuthority,
    TournamentHybridKnockoutMatchEntrants,
)


def fp(char: str) -> str:
    return char * 64


def entrants_eight() -> TournamentHybridKnockoutEntrantsAuthority:
    pairs = (
        ("A1", "B2"),
        ("C1", "D2"),
        ("B1", "A2"),
        ("D1", "C2"),
    )
    matches = []
    for index, (top, bottom) in enumerate(pairs, start=1):
        matches.append(
            TournamentHybridKnockoutMatchEntrants(
                match_id=f"event:hybrid:knockout:first:M{index}",
                match_index=index,
                top_source=TournamentGroupCrossingSource(
                    group_index=((index - 1) % 4) + 1,
                    finishing_position=1,
                ),
                top_player_id=top,
                bottom_source=TournamentGroupCrossingSource(
                    group_index=((index) % 4) + 1,
                    finishing_position=2,
                ),
                bottom_player_id=bottom,
            )
        )
    return TournamentHybridKnockoutEntrantsAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="entrants",
        topology_authority_fingerprint=fp("a"),
        group_standings_authority_fingerprint=fp("b"),
        first_round_matches=tuple(matches),
    )


@pytest.mark.pr_critical
def test_hybrid_bracket_preserves_configured_first_round_and_adjacent_winner_tree():
    entrants = entrants_eight()
    authority = TournamentHybridKnockoutBracketBuilder.build(
        entrants=entrants,
        command_id="bracket",
    )

    assert authority.entrant_count == 8
    assert authority.round_count == 3
    assert len(authority.matches) == 7
    assert authority.bracket_policy_id == (
        "configured_crossings_standard_winner_tree_no_reseed.v1"
    )

    round_one = tuple(match for match in authority.matches if match.round_number == 1)
    assert tuple(match.match_id for match in round_one) == tuple(
        match.match_id for match in entrants.first_round_matches
    )
    assert tuple(match.participant_sources for match in round_one) == (
        ("player:A1", "player:B2"),
        ("player:C1", "player:D2"),
        ("player:B1", "player:A2"),
        ("player:D1", "player:C2"),
    )

    round_two = tuple(match for match in authority.matches if match.round_number == 2)
    assert tuple(match.participant_sources for match in round_two) == (
        (
            "winner:event:hybrid:knockout:first:M1",
            "winner:event:hybrid:knockout:first:M2",
        ),
        (
            "winner:event:hybrid:knockout:first:M3",
            "winner:event:hybrid:knockout:first:M4",
        ),
    )

    final = next(match for match in authority.matches if match.round_number == 3)
    assert final.participant_sources == (
        "winner:event:hybrid:knockout:R2:M1",
        "winner:event:hybrid:knockout:R2:M2",
    )
    assert authority.terminal_match_id == final.match_id


@pytest.mark.pr_critical
def test_hybrid_bracket_replay_is_deterministic_and_does_not_consult_ranking_identity():
    entrants = entrants_eight()
    first = TournamentHybridKnockoutBracketBuilder.build(
        entrants=entrants,
        command_id="same-command",
    )
    second = TournamentHybridKnockoutBracketBuilder.build(
        entrants=entrants,
        command_id="same-command",
    )

    assert first == second
    assert first.fingerprint == second.fingerprint
    dumped = first.model_dump_json()
    assert "ranking" not in dumped.lower()
    assert "race" not in dumped.lower()


@pytest.mark.pr_critical
def test_hybrid_bracket_authority_rejects_reseeded_later_round_sources():
    authority = TournamentHybridKnockoutBracketBuilder.build(
        entrants=entrants_eight(),
        command_id="bracket",
    )
    altered = list(authority.matches)
    semifinal = altered[4]
    altered[4] = semifinal.model_copy(
        update={
            "participant_sources": (
                "winner:event:hybrid:knockout:first:M1",
                "winner:event:hybrid:knockout:first:M3",
            )
        }
    )

    with pytest.raises(ValueError, match="adjacent winner feeders"):
        TournamentHybridKnockoutBracketAuthority(
            **{
                **authority.model_dump(mode="python"),
                "matches": tuple(altered),
            }
        )
