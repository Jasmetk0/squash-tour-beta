"""Immutable standings authority for completed tournament group stages.

This module implements only the group-table rules decided in Master Vision v68:
wins, group-table points, two-player head-to-head, all-group game ratio,
all-group point ratio, and an explicit unresolved state when those criteria still
cannot produce a unique order. It deliberately refuses to invent RET group
scoring, fake W/O score data, random fallbacks, player-id fallbacks or Race
reseeding.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import cmp_to_key
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.matches.models import MatchResult, MatchTerminationReason
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthority,
    TournamentGroupScheduledMatch,
)
from beta_engine.domain.tournaments.walkover_authority import TournamentWalkoverResult


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentGroupStandingsUnsupportedResult(ValueError):
    """Completed group evidence exists but Master does not define its table effect."""


class TournamentGroupStandingsTieCase(FrozenInput):
    """Exact unresolved tie evidence that requires an explicit Admin decision."""

    schema_version: Literal["tournament_group_standings_tie_case.v1"] = (
        "tournament_group_standings_tie_case.v1"
    )
    group_index: int = Field(ge=1, le=64)
    player_ids: tuple[str, ...] = Field(min_length=2)
    reason: str = Field(min_length=1, max_length=128)
    source_match_results: tuple[tuple[str, str], ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_case(self) -> "TournamentGroupStandingsTieCase":
        if self.player_ids != tuple(sorted(self.player_ids)):
            raise ValueError("Unresolved tie player IDs must use canonical sorted order")
        if len(self.player_ids) != len(set(self.player_ids)):
            raise ValueError("Unresolved tie cannot contain duplicate players")
        if len(self.source_match_results) != len(
            {match_id for match_id, _ in self.source_match_results}
        ):
            raise ValueError("Unresolved tie evidence contains duplicate match identity")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentGroupTieResolutionDecision(FrozenInput):
    """One audited Admin ordering for one exact unresolved tie case."""

    schema_version: Literal["tournament_group_tie_resolution_decision.v1"] = (
        "tournament_group_tie_resolution_decision.v1"
    )
    case: TournamentGroupStandingsTieCase
    ordered_player_ids: tuple[str, ...] = Field(min_length=2)
    admin_reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_order(self) -> "TournamentGroupTieResolutionDecision":
        if len(self.ordered_player_ids) != len(set(self.ordered_player_ids)):
            raise ValueError("Admin tie resolution cannot contain duplicate players")
        if set(self.ordered_player_ids) != set(self.case.player_ids):
            raise ValueError(
                "Admin tie resolution must order exactly the unresolved players"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentGroupStandingsUnresolvedTie(ValueError):
    """The decided automatic criteria cannot produce one unique group order."""

    def __init__(self, case: TournamentGroupStandingsTieCase):
        self.case = case
        self.group_index = case.group_index
        self.player_ids = case.player_ids
        self.reason = case.reason
        super().__init__(
            "group standings require explicit Admin resolution: "
            f"group={case.group_index}, players={','.join(case.player_ids)}, "
            f"reason={case.reason}, case={case.fingerprint}"
        )


class TournamentGroupPlayedGame(FrozenInput):
    """One actually played squash game used only as ratio evidence."""

    winner_player_id: str = Field(min_length=1)
    loser_player_id: str = Field(min_length=1)
    winner_points: int = Field(ge=0)
    loser_points: int = Field(ge=0)


class TournamentGroupResultReceipt(FrozenInput):
    """Compact immutable table input derived from one canonical match receipt."""

    match_id: str = Field(min_length=1)
    group_index: int = Field(ge=1, le=64)
    result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_kind: Literal["played", "walkover"]
    winner_player_id: str = Field(min_length=1)
    loser_player_id: str = Field(min_length=1)
    best_of: Literal[3, 5]
    games: tuple[TournamentGroupPlayedGame, ...] = ()
    termination_reason: Literal["COMPLETED", "W/O"]

    @model_validator(mode="after")
    def validate_receipt(self) -> "TournamentGroupResultReceipt":
        if self.winner_player_id == self.loser_player_id:
            raise ValueError("Group standings receipt cannot use one player twice")
        if self.result_kind == "walkover":
            if self.termination_reason != "W/O" or self.games:
                raise ValueError("Group W/O receipt cannot fabricate played games")
        elif self.termination_reason != "COMPLETED":
            raise ValueError("Played group receipt must be a completed match")
        return self


class TournamentGroupStandingRow(FrozenInput):
    group_index: int = Field(ge=1, le=64)
    position: int = Field(ge=1, le=128)
    player_id: str = Field(min_length=1)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    group_points: int = Field(ge=0)
    played_matches: int = Field(ge=0)
    walkovers_received: int = Field(ge=0)
    walkovers_conceded: int = Field(ge=0)
    games_won: int = Field(ge=0)
    games_lost: int = Field(ge=0)
    points_won: int = Field(ge=0)
    points_lost: int = Field(ge=0)


class TournamentGroupStanding(FrozenInput):
    group_index: int = Field(ge=1, le=64)
    rows: tuple[TournamentGroupStandingRow, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_rows(self) -> "TournamentGroupStanding":
        if any(row.group_index != self.group_index for row in self.rows):
            raise ValueError("Group standing row references a different group")
        if tuple(row.position for row in self.rows) != tuple(
            range(1, len(self.rows) + 1)
        ):
            raise ValueError("Group standing positions must be contiguous from one")
        players = tuple(row.player_id for row in self.rows)
        if len(players) != len(set(players)):
            raise ValueError("Group standing contains a duplicate player")
        return self


class TournamentGroupStandingsAuthority(FrozenInput):
    """Immutable final table order for one fully completed group stage."""

    schema_version: Literal[
        "tournament_group_standings_authority.v1",
        "tournament_group_standings_authority.v2",
    ] = "tournament_group_standings_authority.v2"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    generated_by_command_id: str = Field(min_length=1, max_length=128)
    group_match_schedule_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_rules_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scoring_policy_id: Literal["master_group_table_points.v1"] = (
        "master_group_table_points.v1"
    )
    tie_break_policy_id: Literal[
        "wins_points_h2h_ratios_admin_unresolved.v1"
    ] = "wins_points_h2h_ratios_admin_unresolved.v1"
    walkover_policy_id: Literal[
        "group_wo_win_max_points_no_fabricated_ratios.v1"
    ] = "group_wo_win_max_points_no_fabricated_ratios.v1"
    source_results: tuple[TournamentGroupResultReceipt, ...] = Field(min_length=1)
    admin_tie_resolutions: tuple[TournamentGroupTieResolutionDecision, ...] = ()
    groups: tuple[TournamentGroupStanding, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_authority(self) -> "TournamentGroupStandingsAuthority":
        if tuple(group.group_index for group in self.groups) != tuple(
            range(1, len(self.groups) + 1)
        ):
            raise ValueError("Group standings must cover contiguous groups from one")
        result_ids = tuple(receipt.match_id for receipt in self.source_results)
        if len(result_ids) != len(set(result_ids)):
            raise ValueError("Group standings contains duplicate source match identity")
        resolution_cases = tuple(
            decision.case.fingerprint for decision in self.admin_tie_resolutions
        )
        if len(resolution_cases) != len(set(resolution_cases)):
            raise ValueError("Group standings contains duplicate Admin tie resolution")
        return self

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json")
        if self.schema_version == "tournament_group_standings_authority.v1":
            payload.pop("admin_tie_resolutions", None)
        return _fingerprint(payload)


@dataclass
class _MutableStanding:
    player_id: str
    wins: int = 0
    losses: int = 0
    group_points: int = 0
    played_matches: int = 0
    walkovers_received: int = 0
    walkovers_conceded: int = 0
    games_won: int = 0
    games_lost: int = 0
    points_won: int = 0
    points_lost: int = 0


class TournamentGroupStandingsBuilder:
    """Derive final group order without any hidden fallback."""

    @staticmethod
    def receipt_from_result(
        *,
        scheduled_match: TournamentGroupScheduledMatch,
        result: MatchResult | TournamentWalkoverResult,
        result_fingerprint: str,
    ) -> TournamentGroupResultReceipt:
        expected_players = {
            scheduled_match.top_player_id,
            scheduled_match.bottom_player_id,
        }
        if {result.winner_player_id, result.loser_player_id} != expected_players:
            raise ValueError("Group result participants differ from frozen schedule")

        best_of = scheduled_match.effective_match_format.format.best_of
        if isinstance(result, TournamentWalkoverResult):
            return TournamentGroupResultReceipt(
                match_id=result.match_id,
                group_index=scheduled_match.group_index,
                result_fingerprint=result_fingerprint,
                result_kind="walkover",
                winner_player_id=result.winner_player_id,
                loser_player_id=result.loser_player_id,
                best_of=best_of,
                termination_reason="W/O",
            )

        if result.best_of != best_of:
            raise ValueError("Group result best-of differs from frozen schedule")
        if result.termination_reason != MatchTerminationReason.COMPLETED:
            raise TournamentGroupStandingsUnsupportedResult(
                "group RET table points/tie-break effects remain unresolved in Master"
            )
        return TournamentGroupResultReceipt(
            match_id=result.match_id,
            group_index=scheduled_match.group_index,
            result_fingerprint=result_fingerprint,
            result_kind="played",
            winner_player_id=result.winner_player_id,
            loser_player_id=result.loser_player_id,
            best_of=best_of,
            termination_reason="COMPLETED",
            games=tuple(
                TournamentGroupPlayedGame(
                    winner_player_id=game.winner_player_id,
                    loser_player_id=game.loser_player_id,
                    winner_points=game.winner_games,
                    loser_points=game.loser_games,
                )
                for game in result.sets
            ),
        )

    @staticmethod
    def build(
        *,
        schedule: TournamentGroupMatchScheduleAuthority,
        receipts: tuple[TournamentGroupResultReceipt, ...],
        command_id: str,
        admin_tie_resolutions: tuple[TournamentGroupTieResolutionDecision, ...] = (),
        schema_version: Literal[
            "tournament_group_standings_authority.v1",
            "tournament_group_standings_authority.v2",
        ] = "tournament_group_standings_authority.v2",
    ) -> TournamentGroupStandingsAuthority:
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Group Standings requires a valid command ID")
        by_match = {receipt.match_id: receipt for receipt in receipts}
        if len(by_match) != len(receipts):
            raise ValueError("Group Standings contains duplicate result receipts")
        scheduled_ids = tuple(match.match_id for match in schedule.matches)
        if set(by_match) != set(scheduled_ids):
            raise ValueError(
                "Group Standings requires exactly one result for every scheduled match"
            )

        scheduled_by_id = {match.match_id: match for match in schedule.matches}
        ordered_receipts: list[TournamentGroupResultReceipt] = []
        for match in schedule.matches:
            receipt = by_match[match.match_id]
            if receipt.group_index != match.group_index:
                raise ValueError("Group result receipt references wrong group")
            if receipt.best_of != match.effective_match_format.format.best_of:
                raise ValueError("Group result receipt references wrong match format")
            if {receipt.winner_player_id, receipt.loser_player_id} != {
                match.top_player_id,
                match.bottom_player_id,
            }:
                raise ValueError("Group result receipt participants differ from schedule")
            ordered_receipts.append(receipt)

        resolution_by_case = {
            decision.case.fingerprint: decision
            for decision in admin_tie_resolutions
        }
        if len(resolution_by_case) != len(admin_tie_resolutions):
            raise ValueError("Duplicate Admin tie resolution case")
        used_resolution_cases: set[str] = set()

        groups: list[TournamentGroupStanding] = []
        for group_index in range(1, schedule.group_count + 1):
            group_matches = tuple(
                match for match in schedule.matches if match.group_index == group_index
            )
            player_ids = tuple(
                sorted(
                    {
                        player_id
                        for match in group_matches
                        for player_id in (
                            match.top_player_id,
                            match.bottom_player_id,
                        )
                    }
                )
            )
            if len(player_ids) != schedule.group_size:
                raise ValueError("Group schedule does not contain configured player count")
            stats = {
                player_id: _MutableStanding(player_id=player_id)
                for player_id in player_ids
            }
            group_receipts = tuple(
                by_match[match.match_id] for match in group_matches
            )
            for receipt in group_receipts:
                TournamentGroupStandingsBuilder._apply_receipt(stats, receipt)

            ordered_players = TournamentGroupStandingsBuilder._order_group(
                group_index=group_index,
                stats=stats,
                receipts=group_receipts,
                admin_tie_resolutions=resolution_by_case,
                used_resolution_cases=used_resolution_cases,
            )
            rows = tuple(
                TournamentGroupStandingRow(
                    group_index=group_index,
                    position=position,
                    player_id=player_id,
                    wins=stats[player_id].wins,
                    losses=stats[player_id].losses,
                    group_points=stats[player_id].group_points,
                    played_matches=stats[player_id].played_matches,
                    walkovers_received=stats[player_id].walkovers_received,
                    walkovers_conceded=stats[player_id].walkovers_conceded,
                    games_won=stats[player_id].games_won,
                    games_lost=stats[player_id].games_lost,
                    points_won=stats[player_id].points_won,
                    points_lost=stats[player_id].points_lost,
                )
                for position, player_id in enumerate(ordered_players, start=1)
            )
            groups.append(TournamentGroupStanding(group_index=group_index, rows=rows))

        # Validate every receipt belongs to the exact scheduled match after all
        # semantic checks. This also keeps a stale result fingerprint inside the
        # immutable authority instead of silently relying on database row order.
        for receipt in ordered_receipts:
            if receipt.match_id not in scheduled_by_id:
                raise ValueError("Unknown group result receipt")

        if set(resolution_by_case) != used_resolution_cases:
            raise ValueError(
                "Admin tie resolution does not match any current unresolved tie case"
            )

        return TournamentGroupStandingsAuthority(
            schema_version=schema_version,
            run_id=schedule.run_id,
            branch_id=schedule.branch_id,
            event_id=schedule.event_id,
            generated_by_command_id=command_id,
            group_match_schedule_fingerprint=schedule.fingerprint,
            group_rules_policy_fingerprint=schedule.group_rules_policy_fingerprint,
            source_results=tuple(ordered_receipts),
            admin_tie_resolutions=tuple(
                resolution_by_case[case_fingerprint]
                for case_fingerprint in sorted(used_resolution_cases)
            ),
            groups=tuple(groups),
        )

    @staticmethod
    def _apply_receipt(
        stats: dict[str, _MutableStanding],
        receipt: TournamentGroupResultReceipt,
    ) -> None:
        winner = stats[receipt.winner_player_id]
        loser = stats[receipt.loser_player_id]
        winner.wins += 1
        loser.losses += 1

        if receipt.result_kind == "walkover":
            winner.walkovers_received += 1
            loser.walkovers_conceded += 1
            winner.group_points += 4 if receipt.best_of == 3 else 6
            return

        winner.played_matches += 1
        loser.played_matches += 1
        games_won = {winner.player_id: 0, loser.player_id: 0}
        for game in receipt.games:
            if {game.winner_player_id, game.loser_player_id} != {
                winner.player_id,
                loser.player_id,
            }:
                raise ValueError("Played group game contains unknown participant")
            games_won[game.winner_player_id] += 1
            stats[game.winner_player_id].games_won += 1
            stats[game.loser_player_id].games_lost += 1
            stats[game.winner_player_id].points_won += game.winner_points
            stats[game.winner_player_id].points_lost += game.loser_points
            stats[game.loser_player_id].points_won += game.loser_points
            stats[game.loser_player_id].points_lost += game.winner_points

        needed = receipt.best_of // 2 + 1
        if games_won[winner.player_id] != needed:
            raise ValueError("Completed group match winner lacks decisive game count")
        loser_games = games_won[loser.player_id]
        if receipt.best_of == 3:
            points = {(2, 0): (4, 0), (2, 1): (3, 1)}
        else:
            points = {(3, 0): (6, 0), (3, 1): (5, 1), (3, 2): (4, 2)}
        try:
            winner_points, loser_points = points[(needed, loser_games)]
        except KeyError as exc:
            raise ValueError("Completed group score is invalid for its best-of") from exc
        winner.group_points += winner_points
        loser.group_points += loser_points

    @staticmethod
    def _order_group(
        *,
        group_index: int,
        stats: dict[str, _MutableStanding],
        receipts: tuple[TournamentGroupResultReceipt, ...],
        admin_tie_resolutions: dict[str, TournamentGroupTieResolutionDecision],
        used_resolution_cases: set[str],
    ) -> tuple[str, ...]:
        primary: dict[tuple[int, int], list[str]] = {}
        for player_id, row in stats.items():
            primary.setdefault((row.wins, row.group_points), []).append(player_id)

        ordered: list[str] = []
        for key in sorted(primary, key=lambda value: (-value[0], -value[1])):
            tied = tuple(sorted(primary[key]))
            ordered.extend(
                TournamentGroupStandingsBuilder._resolve_tie(
                    group_index=group_index,
                    player_ids=tied,
                    stats=stats,
                    receipts=receipts,
                    metric="games",
                    admin_tie_resolutions=admin_tie_resolutions,
                    used_resolution_cases=used_resolution_cases,
                )
            )
        return tuple(ordered)

    @staticmethod
    def _resolve_tie(
        *,
        group_index: int,
        player_ids: tuple[str, ...],
        stats: dict[str, _MutableStanding],
        receipts: tuple[TournamentGroupResultReceipt, ...],
        metric: Literal["games", "points"],
        admin_tie_resolutions: dict[str, TournamentGroupTieResolutionDecision],
        used_resolution_cases: set[str],
    ) -> tuple[str, ...]:
        if len(player_ids) == 1:
            return player_ids
        if len(player_ids) == 2:
            return TournamentGroupStandingsBuilder._head_to_head(
                group_index=group_index,
                player_ids=player_ids,
                receipts=receipts,
                admin_tie_resolutions=admin_tie_resolutions,
                used_resolution_cases=used_resolution_cases,
            )

        ratio_pairs = {
            player_id: (
                (stats[player_id].games_won, stats[player_id].games_lost)
                if metric == "games"
                else (stats[player_id].points_won, stats[player_id].points_lost)
            )
            for player_id in player_ids
        }
        if any(won == 0 and lost == 0 for won, lost in ratio_pairs.values()):
            return TournamentGroupStandingsBuilder._admin_resolution_or_raise(
                group_index=group_index,
                player_ids=player_ids,
                receipts=receipts,
                reason=f"{metric}_ratio_has_insufficient_played_data",
                admin_tie_resolutions=admin_tie_resolutions,
                used_resolution_cases=used_resolution_cases,
            )

        def compare(left: str, right: str) -> int:
            comparison = TournamentGroupStandingsBuilder._compare_ratio(
                ratio_pairs[left], ratio_pairs[right]
            )
            if comparison:
                return -comparison
            return 0

        sorted_players = tuple(sorted(player_ids, key=cmp_to_key(compare)))
        partitions: list[list[str]] = []
        for player_id in sorted_players:
            if not partitions:
                partitions.append([player_id])
                continue
            previous = partitions[-1][0]
            if (
                TournamentGroupStandingsBuilder._compare_ratio(
                    ratio_pairs[previous], ratio_pairs[player_id]
                )
                == 0
            ):
                partitions[-1].append(player_id)
            else:
                partitions.append([player_id])

        resolved: list[str] = []
        for partition in partitions:
            subgroup = tuple(partition)
            if len(subgroup) == 1:
                resolved.extend(subgroup)
            elif len(subgroup) == 2:
                resolved.extend(
                    TournamentGroupStandingsBuilder._head_to_head(
                        group_index=group_index,
                        player_ids=subgroup,
                        receipts=receipts,
                        admin_tie_resolutions=admin_tie_resolutions,
                        used_resolution_cases=used_resolution_cases,
                    )
                )
            elif metric == "games":
                resolved.extend(
                    TournamentGroupStandingsBuilder._resolve_tie(
                        group_index=group_index,
                        player_ids=subgroup,
                        stats=stats,
                        receipts=receipts,
                        metric="points",
                        admin_tie_resolutions=admin_tie_resolutions,
                        used_resolution_cases=used_resolution_cases,
                    )
                )
            else:
                resolved.extend(
                    TournamentGroupStandingsBuilder._admin_resolution_or_raise(
                        group_index=group_index,
                        player_ids=subgroup,
                        receipts=receipts,
                        reason="automatic_tie_breaks_exhausted",
                        admin_tie_resolutions=admin_tie_resolutions,
                        used_resolution_cases=used_resolution_cases,
                    )
                )
        return tuple(resolved)

    @staticmethod
    def _head_to_head(
        *,
        group_index: int,
        player_ids: tuple[str, str],
        receipts: tuple[TournamentGroupResultReceipt, ...],
        admin_tie_resolutions: dict[str, TournamentGroupTieResolutionDecision],
        used_resolution_cases: set[str],
    ) -> tuple[str, str]:
        target = set(player_ids)
        matches = tuple(
            receipt
            for receipt in receipts
            if {receipt.winner_player_id, receipt.loser_player_id} == target
        )
        if len(matches) != 1:
            raise ValueError("Group head-to-head evidence is missing or duplicated")
        result = matches[0]
        if result.result_kind != "played":
            resolved = TournamentGroupStandingsBuilder._admin_resolution_or_raise(
                group_index=group_index,
                player_ids=player_ids,
                receipts=receipts,
                reason="head_to_head_is_walkover_not_played_match",
                admin_tie_resolutions=admin_tie_resolutions,
                used_resolution_cases=used_resolution_cases,
            )
            return (resolved[0], resolved[1])
        return (result.winner_player_id, result.loser_player_id)

    @staticmethod
    def _tie_case(
        *,
        group_index: int,
        player_ids: tuple[str, ...],
        receipts: tuple[TournamentGroupResultReceipt, ...],
        reason: str,
    ) -> TournamentGroupStandingsTieCase:
        return TournamentGroupStandingsTieCase(
            group_index=group_index,
            player_ids=tuple(sorted(player_ids)),
            reason=reason,
            source_match_results=tuple(
                sorted(
                    (receipt.match_id, receipt.result_fingerprint)
                    for receipt in receipts
                )
            ),
        )

    @staticmethod
    def _admin_resolution_or_raise(
        *,
        group_index: int,
        player_ids: tuple[str, ...],
        receipts: tuple[TournamentGroupResultReceipt, ...],
        reason: str,
        admin_tie_resolutions: dict[str, TournamentGroupTieResolutionDecision],
        used_resolution_cases: set[str],
    ) -> tuple[str, ...]:
        case = TournamentGroupStandingsBuilder._tie_case(
            group_index=group_index,
            player_ids=player_ids,
            receipts=receipts,
            reason=reason,
        )
        decision = admin_tie_resolutions.get(case.fingerprint)
        if decision is None:
            raise TournamentGroupStandingsUnresolvedTie(case)
        if decision.case != case:
            raise ValueError("Admin tie resolution evidence does not match current case")
        used_resolution_cases.add(case.fingerprint)
        return decision.ordered_player_ids

    @staticmethod
    def _compare_ratio(left: tuple[int, int], right: tuple[int, int]) -> int:
        left_won, left_lost = left
        right_won, right_lost = right
        if left_lost == 0:
            if right_lost == 0:
                return (left_won > right_won) - (left_won < right_won)
            return 1
        if right_lost == 0:
            return -1
        left_product = left_won * right_lost
        right_product = right_won * left_lost
        return (left_product > right_product) - (left_product < right_product)
