"""Canonical World Tour Finals Race configuration and immutable snapshot authority."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingPlayer,
    RankingWeek,
)


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class FinalsRaceConfiguration(FrozenInput):
    """One season's frozen Race rules and cutoff evidence.

    Category values are configuration selectors only. The resulting Race snapshot freezes
    the exact source event/source fingerprints that actually matched this configuration.
    """

    schema_version: Literal["finals_race_configuration.v1"] = (
        "finals_race_configuration.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    season_index: int = Field(ge=0, le=49)
    best_n_results: int = Field(ge=1)
    eligible_categories: tuple[str, ...]
    cutoff_ranking_week: RankingWeek
    cutoff_ranking_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cutoff_transition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    adopted_by_command_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.cutoff_ranking_week.season_index != self.season_index:
            raise ValueError("Finals Race cutoff must belong to the configured season")
        normalized = tuple(value.strip() for value in self.eligible_categories)
        if (
            not normalized
            or any(not value for value in normalized)
            or normalized != tuple(sorted(set(normalized)))
        ):
            raise ValueError(
                "Finals Race eligible categories must be unique, sorted and non-empty"
            )
        if normalized != self.eligible_categories:
            raise ValueError("Finals Race eligible categories must be normalized")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class FinalsRaceTournamentAward(FrozenInput):
    player_id: str = Field(min_length=1)
    race_points_awarded: int = Field(ge=0)


class FinalsRaceTournamentSource(FrozenInput):
    """Frozen canonical tournament evidence eligible for one Race calculation."""

    schema_version: Literal["finals_race_tournament_source.v1"] = (
        "finals_race_tournament_source.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    completed_week: RankingWeek
    first_publication_week: RankingWeek
    owned_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    point_award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    awards: tuple[FinalsRaceTournamentAward, ...]

    @model_validator(mode="after")
    def validate_source(self):
        player_ids = tuple(award.player_id for award in self.awards)
        if player_ids != tuple(sorted(set(player_ids))):
            raise ValueError(
                "Finals Race tournament awards must use unique sorted player identities"
            )
        if self.first_publication_week.ordinal <= self.completed_week.ordinal:
            raise ValueError(
                "Finals Race tournament source must publish after tournament completion"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class FinalsRaceContribution(FrozenInput):
    event_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    completed_week: RankingWeek
    first_publication_week: RankingWeek
    race_points_awarded: int = Field(ge=0)
    owned_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    point_award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class FinalsRaceRow(FrozenInput):
    rank: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    race_points: int = Field(ge=0)
    counted_results: int = Field(ge=0)
    result_point_profile: tuple[int, ...]
    tie_break_token: str = Field(min_length=1)
    counted_contributions: tuple[FinalsRaceContribution, ...]

    @model_validator(mode="after")
    def validate_row(self):
        if self.counted_results != len(self.counted_contributions):
            raise ValueError("Finals Race counted-result total does not match evidence")
        if self.race_points != sum(
            item.race_points_awarded for item in self.counted_contributions
        ):
            raise ValueError("Finals Race points do not match counted evidence")
        if self.result_point_profile != tuple(
            item.race_points_awarded for item in self.counted_contributions
        ):
            raise ValueError("Finals Race point profile differs from counted evidence")
        if any(
            left < right
            for left, right in zip(
                self.result_point_profile, self.result_point_profile[1:]
            )
        ):
            raise ValueError("Finals Race result profile must be descending")
        return self


class FinalsRaceSnapshot(FrozenInput):
    """Immutable Race standings at the configured published-ranking cutoff."""

    schema_version: Literal["finals_race_snapshot.v1"] = "finals_race_snapshot.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    season_index: int = Field(ge=0, le=49)
    cutoff_ranking_week: RankingWeek
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cutoff_ranking_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cutoff_transition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_ids: tuple[str, ...]
    source_fingerprints: tuple[str, ...]
    rows: tuple[FinalsRaceRow, ...]

    @model_validator(mode="after")
    def validate_snapshot(self):
        if self.cutoff_ranking_week.season_index != self.season_index:
            raise ValueError("Finals Race snapshot cutoff season mismatch")
        if self.source_event_ids != tuple(sorted(set(self.source_event_ids))):
            raise ValueError("Finals Race source event identities must be unique/sorted")
        if self.source_fingerprints != tuple(sorted(set(self.source_fingerprints))):
            raise ValueError("Finals Race source fingerprints must be unique/sorted")
        if tuple(row.rank for row in self.rows) != tuple(
            range(1, len(self.rows) + 1)
        ):
            raise ValueError("Finals Race ranks must be contiguous")
        player_ids = tuple(row.player_id for row in self.rows)
        if len(set(player_ids)) != len(player_ids):
            raise ValueError("Finals Race snapshot contains duplicate players")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def build_finals_race_snapshot(
    *,
    configuration: FinalsRaceConfiguration,
    players: tuple[OfficialRankingPlayer, ...],
    tournament_sources: tuple[FinalsRaceTournamentSource, ...],
    calendar_content_fingerprint: str,
    cutoff_transition_fingerprint: str,
) -> FinalsRaceSnapshot:
    """Build Master-v67 Race standings from already frozen canonical evidence.

    Ranking order is exactly:
    1) sum of the configured best N results;
    2) highest result, then second-highest, etc.;
    3) the already-frozen canonical player tie-break token.

    No Official Ranking position or previous-season ordering participates.
    """

    if calendar_content_fingerprint != configuration.calendar_content_fingerprint:
        raise ValueError("Finals Race Calendar evidence changed after configuration")
    if cutoff_transition_fingerprint != configuration.cutoff_transition_fingerprint:
        raise ValueError("Finals Race cutoff transition evidence mismatch")

    player_by_id = {player.player_id: player for player in players}
    if len(player_by_id) != len(players):
        raise ValueError("Finals Race roster contains duplicate players")
    tokens = [player.tie_break_token for player in players]
    if len(tokens) != len(set(tokens)):
        raise ValueError("Finals Race roster tie-break tokens must be unique")

    source_by_event: dict[str, FinalsRaceTournamentSource] = {}
    contributions_by_player: dict[str, list[FinalsRaceContribution]] = defaultdict(
        list
    )

    for source in sorted(tournament_sources, key=lambda item: item.event_id):
        if (source.run_id, source.branch_id) != (
            configuration.run_id,
            configuration.branch_id,
        ):
            raise ValueError("Finals Race tournament source scope mismatch")
        if source.completed_week.season_index != configuration.season_index:
            continue
        if source.first_publication_week.ordinal > configuration.cutoff_ranking_week.ordinal:
            continue
        if source.category not in configuration.eligible_categories:
            continue
        if source.event_id in source_by_event:
            raise ValueError("Finals Race contains duplicate eligible tournament source")
        source_by_event[source.event_id] = source

        for award in source.awards:
            if award.player_id not in player_by_id:
                raise ValueError(
                    "Finals Race tournament source references player outside cutoff roster"
                )
            contributions_by_player[award.player_id].append(
                FinalsRaceContribution(
                    event_id=source.event_id,
                    category=source.category,
                    completed_week=source.completed_week,
                    first_publication_week=source.first_publication_week,
                    race_points_awarded=award.race_points_awarded,
                    owned_source_fingerprint=source.owned_source_fingerprint,
                    point_award_fingerprint=source.point_award_fingerprint,
                )
            )

    rows: list[FinalsRaceRow] = []
    for player in sorted(players, key=lambda item: item.player_id):
        contributions = sorted(
            contributions_by_player.get(player.player_id, []),
            key=lambda item: (
                -item.race_points_awarded,
                item.event_id,
                item.completed_week.ordinal,
            ),
        )
        counted = tuple(contributions[: configuration.best_n_results])
        profile = tuple(item.race_points_awarded for item in counted)
        rows.append(
            FinalsRaceRow(
                rank=1,
                player_id=player.player_id,
                race_points=sum(profile),
                counted_results=len(counted),
                result_point_profile=profile,
                tie_break_token=player.tie_break_token,
                counted_contributions=counted,
            )
        )

    def race_order(row: FinalsRaceRow):
        padded_profile = row.result_point_profile + (0,) * (
            configuration.best_n_results - len(row.result_point_profile)
        )
        return (
            -row.race_points,
            tuple(-points for points in padded_profile),
            row.tie_break_token,
        )

    ordered = sorted(rows, key=race_order)
    ranked = tuple(
        row.model_copy(update={"rank": index + 1})
        for index, row in enumerate(ordered)
    )
    source_event_ids = tuple(sorted(source_by_event))
    source_fingerprints = tuple(
        sorted(source.fingerprint for source in source_by_event.values())
    )
    return FinalsRaceSnapshot(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        season_index=configuration.season_index,
        cutoff_ranking_week=configuration.cutoff_ranking_week,
        configuration_fingerprint=configuration.fingerprint,
        cutoff_ranking_snapshot_fingerprint=(
            configuration.cutoff_ranking_snapshot_fingerprint
        ),
        cutoff_transition_fingerprint=configuration.cutoff_transition_fingerprint,
        calendar_content_fingerprint=configuration.calendar_content_fingerprint,
        source_event_ids=source_event_ids,
        source_fingerprints=source_fingerprints,
        rows=ranked,
    )
