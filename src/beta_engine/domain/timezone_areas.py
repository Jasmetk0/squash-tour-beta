"""Deterministic, package-scoped Timezone Area circular topology."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator

class TimezoneArea(BaseModel):
    """Canonical area; ``position`` is explicit and contiguous within a package."""
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, pattern=r"^[A-Z0-9][A-Z0-9_-]*$")
    name: str = Field(min_length=1)
    position: int = Field(ge=0)

    @field_validator("code", "name")
    @classmethod
    def no_surrounding_space(cls, value: str) -> str:
        if value != value.strip(): raise ValueError("must not have surrounding whitespace")
        return value

class RingDirection(str, Enum):
    NONE = "none"
    FORWARD = "forward"
    BACKWARD = "backward"
    TIE = "tie"

class TimezoneDisplacement(BaseModel):
    transitions: int
    direction: RingDirection


def validate_timezone_areas(areas: list[TimezoneArea]) -> list[TimezoneArea]:
    """Return position order, rejecting empty, ambiguous, or malformed registries."""
    if not areas:
        raise ValueError("Timezone Area registry must contain at least one area")
    if len({a.code for a in areas}) != len(areas): raise ValueError("Timezone Area codes must be unique")
    ordered = sorted(areas, key=lambda a: a.position)
    if [a.position for a in ordered] != list(range(len(areas))):
        raise ValueError("Timezone Area positions must be unique and contiguous from zero")
    return ordered


def circular_displacement(areas: list[TimezoneArea], source: str, destination: str) -> TimezoneDisplacement:
    """Describe shortest ring displacement; exact opposite points return neutral ``tie``."""
    ordered = validate_timezone_areas(areas)
    if not ordered: raise ValueError("Timezone Area registry is empty")
    positions = {area.code: area.position for area in ordered}
    if source not in positions: raise ValueError(f"unknown source Timezone Area '{source}'")
    if destination not in positions: raise ValueError(f"unknown destination Timezone Area '{destination}'")
    forward = (positions[destination] - positions[source]) % len(ordered)
    backward = (positions[source] - positions[destination]) % len(ordered)
    if forward == 0:
        return TimezoneDisplacement(transitions=0, direction=RingDirection.NONE)
    if forward == backward:
        return TimezoneDisplacement(transitions=forward, direction=RingDirection.TIE)
    return TimezoneDisplacement(transitions=min(forward, backward), direction=RingDirection.FORWARD if forward < backward else RingDirection.BACKWARD)
