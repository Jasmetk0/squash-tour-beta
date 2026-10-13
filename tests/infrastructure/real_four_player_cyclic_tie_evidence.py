"""Bounded, authentic MatchEngine evidence for a four-player group cycle.

This is an INTEGRATION TEST INPUT generator, not the actual Run Match-Day
seed scheduler or an editable scoreboard. All six results are produced by
MatchEngine.simulate, with real game-by-game and rally-by-rally data. It
deliberately searches multiple independent candidate RNG seeds; it must not
be misrepresented as normal identity-derived Run auto-seeding.
"""
from __future__ import annotations

import hashlib
import json

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import MatchContext, MatchEngine, MatchParticipantContext
from beta_engine.domain.matches.models import MatchTerminationReason
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsBuilder, TournamentGroupStandingsUnresolvedTie,
)
from tests.domain.test_match_rally_log import _player
from tests.domain.test_tournament_group_standings_authority import schedule_four


# One possible sporting cycle: A beats B; B beats C; C beats A;
# all three beat D. The 2-0 game margins and point ratios must
# *also* agree -- a cyclic winner graph alone is not an unresolved tie.
_DESIRED_WINNERS = {
    "A-D": "A", "B-C": "B", "A-C": "C",
    "B-D": "B", "A-B": "A", "C-D": "C",
}
_SEED_BUDGET = 400


def _generate_four_player_cyclic_receipts():
    schedule = schedule_four()
    athletes = {
        identity: MatchParticipantContext(player=_player(identity, 82))
        for identity in ("A", "B", "C", "D")
    }
    # Each candidate has a real independent match seed. For an exact
    # 3-player ratio tie it suffices to select completed natural BO3
    # games with the *same* 2-0 (22:k) aggregate for all 6 pairings.
    # The six schedules and participants remain original and immutable.
    eligible = {match.match_id: {} for match in schedule.matches}
    chosen = None
    common_score = None
    for seed in range(1, _SEED_BUDGET + 1):
        for match in schedule.matches:
            expected = _DESIRED_WINNERS[match.match_id]
            # No test-injected outcomes: a candidate that is not a natural
            # clean 2-0 victory simply gets ignored.
            result = MatchEngine(rng=DeterministicRng(seed)).simulate(
                MatchContext(
                    match_id=match.match_id,
                    player_a=athletes[match.top_player_id],
                    player_b=athletes[match.bottom_player_id],
                    best_of=3,
                    games_to=11,
                    win_by=2,
                ),
            )
            if (
                result.termination_reason != MatchTerminationReason.COMPLETED
                or result.winner_player_id != expected
                or len(result.sets) != 2
                or any(
                    game.winner_games != 11 for game in result.sets
                )
            ):
                continue
            loser_points = sum(game.loser_games for game in result.sets)
            eligible[match.match_id].setdefault(loser_points, (seed, result))
        available = set.intersection(
            *(set(options) for options in eligible.values())
        )
        if available:
            common_score = min(available)
            chosen = {
                match_id: eligible[match_id][common_score]
                for match_id in eligible
            }
            break
    assert chosen is not None, (
        "Bounded real MatchEngine search could not produce six natural "
        "2-0 results with matching loser point totals; do not fabricate scores"
    )
    receipts = []
    for match in schedule.matches:
        seed, result = chosen[match.match_id]
        assert seed <= _SEED_BUDGET
        assert result.rally_log is not None
        assert result.rally_log.events and result.rally_log.scoring_rallies == (
            sum(game.winner_games + game.loser_games for game in result.sets)
        )
        assert result.match_id == match.match_id
        assert {result.winner_player_id, result.loser_player_id} == {
            match.top_player_id, match.bottom_player_id,
        }
        result_fingerprint = hashlib.sha256(json.dumps(
            result.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        receipt = TournamentGroupStandingsBuilder.receipt_from_result(
            scheduled_match=match,
            result=result,
            result_fingerprint=result_fingerprint,
        )
        assert receipt.result_kind == "played" and len(receipt.games) == 2
        assert sum(g.loser_points for g in receipt.games) == common_score
        receipts.append(receipt)

    # The canonical standings implementation, not an artificial test
    # scoreboard, must genuinely find the three-way unresolved case.
    try:
        TournamentGroupStandingsBuilder.build(
            schedule=schedule,
            receipts=tuple(receipts),
            command_id="four-real-engine-tie-preview",
        )
    except TournamentGroupStandingsUnresolvedTie as error:
        assert error.case.group_index == 1
        assert error.case.player_ids == ("A", "B", "C")
        assert error.case.reason == "automatic_tie_breaks_exhausted"
        assert len(error.case.source_match_results) == 6
        return schedule, tuple(receipts), error.case
    raise AssertionError("Six natural squash match results did not produce an exact tie")
