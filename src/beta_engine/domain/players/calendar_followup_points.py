"""Frozen, explicitly provisional points for a genuine later-week knockout.

These are operator-authored *prepared* awards, never Official Ranking points.
The separate canonical Tour Edition/Entry configuration and a native Week
Transition must authenticate them before any future Official publication.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarFollowupPointPolicy(FrozenInput):
    schema_version: Literal["calendar_followup_point_policy.v1"] = "calendar_followup_point_policy.v1"
    source_kind: Literal["admin_explicit_reviewed"] = "admin_explicit_reviewed"
    category_label: str = Field(min_length=1, max_length=120)
    champion: int = Field(ge=0, le=1000000)
    finalist: int = Field(ge=0, le=1000000)
    semifinal: int = Field(ge=0, le=1000000)
    validity_weeks: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_distribution(self):
        if not self.champion >= self.finalist >= self.semifinal:
            raise ValueError("Prepared points must decrease by knockout placement")
        if self.champion == self.semifinal:
            raise ValueError("Prepared point table must distinguish champion from semifinalists")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


class CalendarFollowupEightPointPolicy(FrozenInput):
    """Explicit non-Official point policy for all four eight-player finish stages."""
    schema_version: Literal["calendar_followup_point_policy.v2"] = "calendar_followup_point_policy.v2"
    source_kind: Literal["admin_explicit_reviewed"] = "admin_explicit_reviewed"
    category_label: str = Field(min_length=1, max_length=120)
    champion: int = Field(ge=0, le=1000000)
    finalist: int = Field(ge=0, le=1000000)
    semifinal: int = Field(ge=0, le=1000000)
    quarterfinal: int = Field(ge=0, le=1000000)
    validity_weeks: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_distribution(self):
        if not self.champion >= self.finalist >= self.semifinal >= self.quarterfinal:
            raise ValueError("Eight-player prepared points must decrease by placement")
        if self.champion == self.quarterfinal:
            raise ValueError("Prepared points must distinguish champion from quarterfinalists")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


class CalendarFollowupPreparedAward(FrozenInput):
    player_id: str = Field(min_length=1)
    reached_stage: Literal["champion", "finalist", "semifinal", "quarterfinal"]
    main_points: int = Field(ge=0, le=1000000)
    source_tournament_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def derive_followup_awards(event) -> tuple[CalendarFollowupPreparedAward, ...]:
    """Derive authentic placements from the complete winner-fed played bracket.

    Historical v2 derives the same four placements in the same sorted order.
    v4 additionally awards the four quarterfinal losers from seven actual games.
    """
    if len(event.entrant_ids) == 8:
        if len(event.matches) != 7:
            raise ValueError("Eight-player award source must contain seven real matches")
        quarters = event.matches[:4]
        semi_a, semi_b, final = event.matches[4:]
        stages = {match.result.loser_player_id: "quarterfinal" for match in quarters}
        stages.update({
            semi_a.result.loser_player_id: "semifinal",
            semi_b.result.loser_player_id: "semifinal",
            final.result.loser_player_id: "finalist",
            final.result.winner_player_id: "champion",
        })
    else:
        semi_a, semi_b, final = event.matches
        stages = {
            semi_a.result.loser_player_id: "semifinal",
            semi_b.result.loser_player_id: "semifinal",
            final.result.loser_player_id: "finalist",
            final.result.winner_player_id: "champion",
        }
    if set(stages) != set(event.entrant_ids):
        raise ValueError("Prepared point placement disagrees with actual knockout field")
    if event.prepared_policy is None:
        raise ValueError("Prepared point policy is required")
    return tuple(
        CalendarFollowupPreparedAward(
            player_id=pid, reached_stage=stage,
            main_points=getattr(event.prepared_policy, stage),
            source_tournament_fingerprint=event.sporting_fingerprint,
            source_policy_fingerprint=event.prepared_policy.fingerprint,
        )
        for pid, stage in sorted(stages.items())
    )
