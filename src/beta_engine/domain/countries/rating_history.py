"""Versioned, evidence-bearing country ratings; no fabricated historical defaults."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

GAME_ATTRIBUTE_NAMES = (
    "squash_popularity", "squash_access", "development_quality",
    "competition_quality", "elite_support", "squash_tradition",
)
RATING_SCALE_V2 = "country_ratings_1_10.v2"
LEGACY_RATING_SCALE = "country_ratings_1_5.v1"


def validate_rating_v2(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("rating must be a finite number from 1 to 10")
    decimal = Decimal(str(value))
    if not decimal.is_finite() or not Decimal(1) <= decimal <= Decimal(10):
        raise ValueError("rating must be a finite number from 1 to 10")
    if decimal * 10 != (decimal * 10).to_integral_value():
        raise ValueError("rating must have at most one decimal place")
    return float(value)


RatingV2 = Annotated[float, BeforeValidator(validate_rating_v2)]


class RatingEvidence(BaseModel):
    """Ratings are model estimates, even when their underlying counts are observed."""

    model_config = ConfigDict(extra="forbid")
    value: RatingV2
    method: Literal["sourced_estimate", "interpolated", "carried_forward", "backcast"]
    confidence: Literal["low", "medium", "high"]
    source_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    anchor_years: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def meaningful_evidence(self) -> "RatingEvidence":
        if not self.rationale.strip() or any(not item.strip() for item in self.source_ids):
            raise ValueError("evidence and source identifiers must not be blank")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("duplicate source identifier")
        return self


class RatingYear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    historical_entity: str = Field(min_length=1)
    territory_mapping_note: str = Field(min_length=1)
    ratings: dict[str, RatingEvidence]

    @model_validator(mode="after")
    def complete_attributes(self) -> "RatingYear":
        if set(self.ratings) != set(GAME_ATTRIBUTE_NAMES):
            raise ValueError("each authored year must contain exactly the six country ratings")
        if not self.historical_entity.strip() or not self.territory_mapping_note.strip():
            raise ValueError("historical entity and territorial mapping must be explicit")
        return self


class CountryRatingHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["country_rating_history.v1"] = "country_rating_history.v1"
    rating_scale: Literal["country_ratings_1_10.v2"] = RATING_SCALE_V2
    reference_year: int = Field(ge=1955, le=2026)
    data_cutoff: date
    years: dict[int, RatingYear] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_years(self) -> "CountryRatingHistory":
        if self.reference_year not in self.years:
            raise ValueError("reference_year must be authored")
        if any(year < 1955 or year > min(2026, self.data_cutoff.year) for year in self.years):
            raise ValueError("historical years must lie in 1955–2026 and not exceed the data cutoff")
        for year, entry in self.years.items():
            for evidence in entry.ratings.values():
                anchors = evidence.anchor_years
                if any(y < 1955 or y > min(2026, self.data_cutoff.year) for y in anchors):
                    raise ValueError("anchor year outside supported historical coverage")
                if evidence.method == "sourced_estimate" and anchors != [year]:
                    raise ValueError("sourced estimates must identify their own anchor year")
                if evidence.method == "interpolated" and not (len(anchors) == 2 and anchors[0] < year < anchors[1]):
                    raise ValueError("interpolation must identify two enclosing anchors")
                if evidence.method == "carried_forward" and not (len(anchors) == 1 and anchors[0] < year):
                    raise ValueError("carry-forward must identify an earlier anchor")
                if evidence.method == "backcast" and not (len(anchors) == 1 and anchors[0] > year):
                    raise ValueError("backcast must identify a later anchor")
        return self

    def resolve(self, year: int) -> tuple[int, RatingYear]:
        """Exact year, otherwise nearest authored year; earlier wins equal-distance ties.

        This returns the source year explicitly. Beyond 2026 it is a carry-forward,
        never a claim that future sporting conditions are known.
        """
        if isinstance(year, bool) or not isinstance(year, int) or not 1954 <= year <= 2050:
            raise ValueError("requested country-rating year must be an integer in 1954–2050")
        source_year = min(self.years, key=lambda item: (abs(item - year), item))
        return source_year, self.years[source_year]

    @property
    def missing_earth_years(self) -> list[int]:
        return sorted(set(range(1955, 2027)) - set(self.years))
