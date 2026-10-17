"""W-aware complete-knockout ranking evidence, never a sporting result writer.

This is an independently fingerprinted, *caller-authenticated* complete
single-elimination result and authored point distribution. It proves internal
bracket progression and deterministic points, not whether a match was actually
played. Only a future Run-native match authority can provide that provenance.
No qualification, BYE, walkover, retirement or group/hybrid mode is inferred.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingResult, CalendarRankingWeek,
)
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion,
)
from beta_engine.domain.rankings.official import FrozenInput


_LOSER_STAGES = {
    2: "finalist",
    4: "semifinal",
    8: "quarterfinal",
    16: "round_of_16",
    32: "round_of_32",
    64: "round_of_64",
    128: "round_of_128",
}


class CalendarKnockoutMatch(FrozenInput):
    match_id: str = Field(min_length=1)
    round_number: int = Field(ge=1)
    bracket_position: int = Field(ge=1)
    winner_player_id: str = Field(min_length=1)
    loser_player_id: str = Field(min_length=1)
    scoreline: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_unresolved_or_abnormal(self):
        if self.winner_player_id == self.loser_player_id:
            raise ValueError("Knockout match requires two distinct players")
        if self.scoreline.strip().upper() in {"BYE", "W/O", "WO", "RET", "WALKOVER"}:
            raise ValueError("BYE/W/O/RET requires a dedicated result authority")
        return self


class CalendarKnockoutRankingEvidence(FrozenInput):
    schema_version: Literal["calendar_knockout_ranking_evidence.v1"] = (
        "calendar_knockout_ranking_evidence.v1"
    )
    run_id: str = Field(min_length=1, max_length=128)
    branch_id: str = Field(min_length=1, max_length=128)
    edition_id: str = Field(min_length=1)
    run_calendar: dict[str, int | str]
    completed_week: CalendarRankingWeek
    first_publication_week: CalendarRankingWeek
    entrants_by_bracket_position: tuple[str, ...] = Field(min_length=2, max_length=128)
    matches: tuple[CalendarKnockoutMatch, ...] = ()
    # Exactly the used finishing stages, in name-sorted canonical order.
    point_distribution: tuple[tuple[str, int], ...]
    point_distribution_source: str = Field(min_length=1)
    validity_weeks: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def verify_full_draw_and_points(self):
        calendar = RunCalendar.from_metadata(self.run_calendar)
        if calendar.schema_version != "run_calendar.v1":
            raise ValueError("Explicit Run calendar required for tournament evidence")
        complete = calendar.ordinal(
            self.completed_week.season_index, self.completed_week.week,
        )
        published = calendar.ordinal(
            self.first_publication_week.season_index,
            self.first_publication_week.week,
        )
        if complete >= published:
            raise ValueError("Ranking publication must be after tournament completion")
        if self.point_distribution_source.startswith("fallback"):
            raise ValueError("Knockout ranking needs an authored point distribution")
        entrants = self.entrants_by_bracket_position
        size = len(entrants)
        if size & (size - 1) or len(set(entrants)) != size or not all(entrants):
            raise ValueError("Knockout field must be unique, complete and power-of-two")
        if len(self.matches) != size - 1:
            raise ValueError("Knockout requires an exact complete match tree")
        if len({m.match_id for m in self.matches}) != len(self.matches):
            raise ValueError("Duplicate knockout match identity")

        previous_winners = list(entrants)
        losers_by_stage: dict[str, str] = {}
        index = 0
        while len(previous_winners) > 1:
            stage_size = len(previous_winners)
            next_winners: list[str] = []
            for position in range(1, stage_size // 2 + 1):
                match = self.matches[index]
                expected = {
                    previous_winners[2 * (position - 1)],
                    previous_winners[2 * (position - 1) + 1],
                }
                if (
                    match.round_number != (size.bit_length() - stage_size.bit_length() + 1)
                    or match.bracket_position != position
                    or {match.winner_player_id, match.loser_player_id} != expected
                ):
                    raise ValueError("Knockout match is missing, out of order or has invalid progression")
                next_winners.append(match.winner_player_id)
                losers_by_stage[match.loser_player_id] = _LOSER_STAGES[stage_size]
                index += 1
            previous_winners = next_winners
        champion = previous_winners[0]
        if len(losers_by_stage) != size - 1 or champion in losers_by_stage:
            raise ValueError("Knockout winner or elimination lineage is invalid")

        point_map = dict(self.point_distribution)
        required = {"champion", *losers_by_stage.values()}
        if (
            len(point_map) != len(self.point_distribution)
            or set(point_map) != required
            or tuple(self.point_distribution) != tuple(sorted(self.point_distribution))
            or any(not isinstance(p, int) or isinstance(p, bool) or p < 0 for p in point_map.values())
        ):
            raise ValueError("Knockout point distribution must exactly cover canonical finishing stages")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()


def prepare_calendar_knockout_ranking_versions(
    evidence: CalendarKnockoutRankingEvidence,
    *,
    run_calendar: RunCalendar,
    expected_evidence_fingerprint: str,
) -> tuple[CalendarRankingResultVersion, ...]:
    """Revalidate complete externally authenticated input before projecting.

    expected_evidence_fingerprint is independent trusted input from the caller;
    merely supplying an arbitrary self-computed hash is NOT match authority.
    Only initial results are produced, never fabricated corrections/zeros.
    """
    if (
        len(expected_evidence_fingerprint) != 64
        or any(c not in "0123456789abcdef" for c in expected_evidence_fingerprint)
    ):
        raise ValueError("External knockout evidence fingerprint is required")
    evidence = CalendarKnockoutRankingEvidence.model_validate_json(
        evidence.model_dump_json()
    )
    if evidence.run_calendar != run_calendar.to_metadata():
        raise ValueError("Tournament evidence Run calendar mismatch")
    if evidence.fingerprint != expected_evidence_fingerprint:
        raise ValueError("Tournament evidence fingerprint mismatch")

    remaining = list(evidence.entrants_by_bracket_position)
    lost_stages: dict[str, str] = {}
    size = len(remaining)
    index = 0
    while len(remaining) > 1:
        next_winners = []
        for _ in range(len(remaining) // 2):
            match = evidence.matches[index]
            lost_stages[match.loser_player_id] = _LOSER_STAGES[len(remaining)]
            next_winners.append(match.winner_player_id)
            index += 1
        remaining = next_winners
    lost_stages[remaining[0]] = "champion"
    points = dict(evidence.point_distribution)
    return tuple(
        CalendarRankingResultVersion(
            run_id=evidence.run_id, branch_id=evidence.branch_id,
            effective_week=evidence.first_publication_week,
            previous_fingerprint=None,
            result=CalendarRankingResult(
                edition_id=evidence.edition_id, player_id=player_id,
                source_fingerprint=evidence.fingerprint,
                completed_week=evidence.completed_week,
                first_publication_week=evidence.first_publication_week,
                qualification_points=0,
                main_points=points[stage],
                validity_weeks=evidence.validity_weeks,
            ),
        )
        for player_id, stage in sorted(lost_stages.items())
    )
