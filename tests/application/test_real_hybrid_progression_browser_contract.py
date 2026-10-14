"""Critical post-group hybrid bracket contract, paired with real Chromium acceptance.

The browser test plays actual Run-owned group matches. This fast guard asserts
the invariant that a frozen bracket cannot replace the approved Group positions
with ranking/Race seeds or an unauthorized future-round feeder.
"""
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

pytestmark = pytest.mark.pr_critical


def test_real_hybrid_progression_admin_bracket_keeps_frozen_two_group_winners():
    """Two known *positions* are the only permitted direct bracket players."""
    entrants = TournamentHybridKnockoutEntrantsAuthority(
        run_id="real-run", branch_id="branch", event_id="cup",
        generated_by_command_id="audited-entrants",
        topology_authority_fingerprint="a"*64,
        group_standings_authority_fingerprint="b"*64,
        first_round_matches=(
            TournamentHybridKnockoutMatchEntrants(
                match_id="cup:hybrid:knockout:first:M1",
                match_index=1,
                top_source=TournamentGroupCrossingSource(
                    group_index=1,finishing_position=1,
                ),
                top_player_id="group-1-winner",
                bottom_source=TournamentGroupCrossingSource(
                    group_index=2,finishing_position=1,
                ),
                bottom_player_id="group-2-winner",
            ),
        ),
    )
    bracket = TournamentHybridKnockoutBracketBuilder.build(
        entrants=entrants, command_id="reviewed-bracket",
    )
    assert bracket.entrant_count == 2
    assert bracket.round_count == 1
    assert bracket.terminal_match_id == bracket.matches[0].match_id
    assert bracket.matches[0].participant_sources == (
        "player:group-1-winner", "player:group-2-winner",
    )
    assert bracket.entrants_authority_fingerprint == entrants.fingerprint
    assert TournamentHybridKnockoutBracketAuthority.model_validate_json(
        bracket.model_dump_json()
    ) == bracket


def test_real_hybrid_progression_browser_is_real_match_day_and_explicit_admin_only():
    """Guard against silently substituting seeded score fixtures for real Run play."""
    from pathlib import Path
    base = Path(__file__).resolve().parents[2]
    browser = (base/"scripts/real_hybrid_progression_browser_checks.py").read_text()
    shell = (base/"scripts/admin_saved_group_browser_smoke.py").read_text()
    assert 'browser_click(page, "Simulate reviewed authoritative Match Day")' in browser
    assert 'Confirm generation from all completed canonical group matches' in browser
    assert '"Generate frozen knockout entrants"' in browser
    assert '"Generate frozen knockout bracket"' in browser
    assert "real_hybrid_progression_browser_checks import play_and_freeze_hybrid" in shell
    assert '--hybrid-progression' in shell
    assert 'standings_authority_fingerprint' in browser
    assert 'knockout_preview["match_day_ordinal"] == 2' in browser
    assert 'browser_click(page, "Simulate reviewed authoritative Match Day")' in browser
    assert 'match-replays?limit=50' in browser
    assert 'final["winner_player_id"], final["loser_player_id"]' in browser
    assert 'result_published":True' in browser
    assert '"Freeze hybrid ranking points policy"' in browser
    assert '"Close real hybrid tournament ranking source"' in browser
    assert 'closure["total_ranking_points"] == 180' in browser
    assert 'archived["published_result"] is not None' in browser
    assert '"/hybrid-ranking-close"' in shell
    assert 'frozen_final_context' in shell
    assert 'real_knockout_matches' in shell
