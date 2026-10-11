"""Read-only evidence for adjacent equal-point rows of a verified candidate."""

from typing import Literal
from beta_engine.domain.rankings.official import FrozenInput, OfficialRankingSnapshot, ranking_order_key
from beta_engine.domain.rankings.input_manifest import RankingInputManifest


class RankingTieExplanation(FrozenInput):
    higher_player_id: str
    lower_player_id: str
    higher_rank: int
    lower_rank: int
    points: int
    reason: Literal["result_profile", "completion_age", "previous_position", "stored_token"]
    result_slot: int | None = None
    higher_value: int | str | None
    lower_value: int | str | None


def explain_ranking_ties(
    snapshot: OfficialRankingSnapshot, manifest: RankingInputManifest,
    previous: OfficialRankingSnapshot | None,
) -> tuple[RankingTieExplanation, ...]:
    # No explanation from active data, incomplete manifests or altered output.
    manifest.verify(snapshot, previous)
    players = {p.player_id: p for p in manifest.players}
    ranks = {r.player_id: r.rank for r in previous.rows} if previous else {}
    explanations = []
    for higher, lower in zip(snapshot.rows, snapshot.rows[1:]):
        if higher.points != lower.points:
            continue
        keys = [ranking_order_key(players[r.player_id], r.counted_results, ranks, snapshot.policy.best_n) for r in (higher, lower)]
        layer = next(i for i in range(1, 5) if keys[0][i] != keys[1][i])
        slot = None
        if layer in (1, 2):
            index = next(i for i, pair in enumerate(zip(keys[0][layer], keys[1][layer])) if pair[0] != pair[1])
            slot = index + 1
            values = [-key[layer][index] for key in keys]
            # -1 is the sort sentinel for an absent completion, not a real week.
            if layer == 2:
                values = [None if v == -1 else v for v in values]
        elif layer == 3:
            values = [ranks.get(r.player_id) for r in (higher, lower)]
        else:
            values = [players[r.player_id].tie_break_token for r in (higher, lower)]
        explanations.append(RankingTieExplanation(
            higher_player_id=higher.player_id, lower_player_id=lower.player_id,
            higher_rank=higher.rank, lower_rank=lower.rank, points=higher.points,
            reason=("result_profile", "completion_age", "previous_position", "stored_token")[layer - 1],
            result_slot=slot, higher_value=values[0], lower_value=values[1],
        ))
    return tuple(explanations)
