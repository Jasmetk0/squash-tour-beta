"""Archived Season Closing Ranking for the Week 61 season boundary.

This ranking is deliberately separate from Official Ranking publication.  It uses the
outgoing season policy, includes results that become ranking-eligible after Week 61,
and exists only as immutable season-summary evidence.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import (
    DisciplinaryZero,
    FrozenInput,
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    OfficialRankingRow,
    OfficialRankingSnapshot,
    RankingWeek,
    ranking_order_key,
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _active_at_boundary(zero: DisciplinaryZero, boundary_ordinal: int) -> bool:
    return 0 <= boundary_ordinal - zero.effective_week.ordinal < zero.duration_weeks


class SeasonClosingRankingSnapshot(FrozenInput):
    schema_version: Literal["season_closing_ranking.v1"] = "season_closing_ranking.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    completed_week: RankingWeek
    policy: OfficialRankingPolicy
    predecessor_official_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    rows: tuple[OfficialRankingRow, ...]

    @model_validator(mode="after")
    def validate_snapshot(self) -> "SeasonClosingRankingSnapshot":
        if self.completed_week.week != 61:
            raise ValueError("Season Closing Ranking requires completed Week 61")
        if tuple(row.rank for row in self.rows) != tuple(
            range(1, len(self.rows) + 1)
        ):
            raise ValueError("Season Closing Ranking positions must be contiguous")
        ids = [row.player_id for row in self.rows]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate Season Closing Ranking player")
        if any(a.points < b.points for a, b in zip(self.rows, self.rows[1:])):
            raise ValueError("Season Closing Ranking points must be descending")

        boundary_ordinal = self.completed_week.ordinal + 1
        zero_ids: list[str] = []
        for row in self.rows:
            zero_ids.extend(zero.zero_id for zero in row.disciplinary_zeros)
            if len(row.counted_results) > max(
                0, self.policy.best_n - len(row.disciplinary_zeros)
            ):
                raise ValueError("Season Closing Ranking counted results exceed Best N")
            for zero in row.disciplinary_zeros:
                if (
                    zero.run_id,
                    zero.branch_id,
                ) != (self.run_id, self.branch_id) or not _active_at_boundary(
                    zero, boundary_ordinal
                ):
                    raise ValueError(
                        "Season Closing Ranking disciplinary zero is not active at boundary"
                    )
            for result in row.counted_results:
                age = boundary_ordinal - result.first_publication_week.ordinal
                if (
                    result.completed_week.ordinal > self.completed_week.ordinal
                    or not result.ranked
                    or not 0 <= age < result.validity_weeks
                ):
                    raise ValueError(
                        "Season Closing Ranking contains an ineligible result"
                    )
        if len(set(zero_ids)) != len(zero_ids):
            raise ValueError("Duplicate disciplinary zero across closing ranking rows")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


def calculate_season_closing_ranking(
    *,
    run_id: str,
    branch_id: str,
    completed_week: RankingWeek,
    policy: OfficialRankingPolicy,
    players: tuple[OfficialRankingPlayer, ...],
    results: tuple[OfficialRankingResult, ...],
    predecessor: OfficialRankingSnapshot,
    disciplinary_zeros: tuple[DisciplinaryZero, ...] = (),
) -> SeasonClosingRankingSnapshot:
    """Calculate the archived ranking immediately after completed Week 61.

    The predecessor is the canonical Official Ranking for Week 61.  Its policy is
    the outgoing season policy.  Week 61 results are evaluated at the following
    ranking boundary without creating or publishing a next-season Official Ranking.
    """

    predecessor = OfficialRankingSnapshot.model_validate_json(
        predecessor.model_dump_json()
    )
    if completed_week.week != 61:
        raise ValueError("Season Closing Ranking requires completed Week 61")
    if (
        predecessor.run_id,
        predecessor.branch_id,
        predecessor.week,
    ) != (run_id, branch_id, completed_week):
        raise ValueError(
            "Season Closing Ranking predecessor must be Official Ranking Week 61"
        )
    if predecessor.policy != policy:
        raise ValueError("Season Closing Ranking must use the outgoing Week 61 policy")

    player_ids = [player.player_id for player in players]
    known_players = set(player_ids)
    if len(known_players) != len(player_ids):
        raise ValueError("Duplicate player identity")
    tokens = [player.tie_break_token for player in players]
    if len(set(tokens)) != len(tokens):
        raise ValueError("Ranking tie-break tokens must be unique")

    result_keys = [(result.edition_id, result.player_id) for result in results]
    if len(set(result_keys)) != len(result_keys):
        raise ValueError("One resolved result per Edition/player is required")
    if any(result.player_id not in known_players for result in results):
        raise ValueError("Season Closing Ranking result references an unknown player")
    if any(result.completed_week.ordinal > completed_week.ordinal for result in results):
        raise ValueError("Season Closing Ranking cannot consume future results")

    zeros = tuple(
        DisciplinaryZero.model_validate_json(zero.model_dump_json())
        for zero in disciplinary_zeros
    )
    if len({zero.zero_id for zero in zeros}) != len(zeros):
        raise ValueError("Duplicate disciplinary zero identity")
    if any(
        (zero.run_id, zero.branch_id) != (run_id, branch_id)
        or zero.player_id not in known_players
        for zero in zeros
    ):
        raise ValueError("Disciplinary zero has unknown player or mismatched scope")

    boundary_ordinal = completed_week.ordinal + 1
    active_zeros = {
        player_id: tuple(
            sorted(
                (
                    zero
                    for zero in zeros
                    if zero.player_id == player_id
                    and _active_at_boundary(zero, boundary_ordinal)
                ),
                key=lambda zero: zero.zero_id,
            )
        )
        for player_id in known_players
    }
    previous_ranks = {row.player_id: row.rank for row in predecessor.rows}
    by_player: dict[str, list[OfficialRankingResult]] = {
        player.player_id: [] for player in players
    }
    for result in results:
        age = boundary_ordinal - result.first_publication_week.ordinal
        if result.ranked and 0 <= age < result.validity_weeks:
            by_player[result.player_id].append(result)

    candidates = []
    for player in players:
        if player.retired or player.tour_entry_week.ordinal >= boundary_ordinal:
            continue
        counted = tuple(
            sorted(
                by_player[player.player_id],
                key=lambda result: (
                    -result.points,
                    -result.completed_week.ordinal,
                    result.edition_id,
                ),
            )[: max(0, policy.best_n - len(active_zeros[player.player_id]))]
        )
        points = sum(result.points for result in counted)
        key = ranking_order_key(
            player, counted, previous_ranks, policy.best_n
        )
        candidates.append((key, player.player_id, points, counted))
    candidates.sort(key=lambda item: item[0])

    input_body = {
        "predecessor_official_fingerprint": predecessor.fingerprint,
        "players": [
            player.model_dump(mode="json")
            for player in sorted(players, key=lambda player: player.player_id)
        ],
        "results": [
            result.model_dump(mode="json")
            for result in sorted(
                results, key=lambda result: (result.edition_id, result.player_id)
            )
        ],
        "disciplinary_zeros": [
            zero.model_dump(mode="json")
            for zero in sorted(zeros, key=lambda zero: zero.zero_id)
        ],
    }
    return SeasonClosingRankingSnapshot(
        run_id=run_id,
        branch_id=branch_id,
        completed_week=completed_week,
        policy=policy,
        predecessor_official_fingerprint=predecessor.fingerprint,
        input_fingerprint=_fingerprint(input_body),
        rows=tuple(
            OfficialRankingRow(
                rank=index,
                player_id=player_id,
                points=points,
                counted_results=counted,
                disciplinary_zeros=active_zeros[player_id],
            )
            for index, (_, player_id, points, counted) in enumerate(
                candidates, start=1
            )
        ),
    )
