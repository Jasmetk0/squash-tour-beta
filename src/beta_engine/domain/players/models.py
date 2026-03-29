"""Player generation domain models for MVP module 1."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HiddenCareerTraits(BaseModel):
    potential_ceiling: int = Field(ge=50, le=99)
    growth_curve: str
    professionalism: float = Field(ge=0.0, le=1.0)
    ambition: float = Field(ge=0.0, le=1.0)
    travel_tolerance: float = Field(ge=0.0, le=1.0)
    schedule_aggression: float = Field(ge=0.0, le=1.0)
    injury_proneness: float = Field(ge=0.0, le=1.0)
    resilience: float = Field(ge=0.0, le=1.0)


class Player(BaseModel):
    player_id: str
    name: str
    age: int = Field(ge=16, le=41)
    nationality: str
    technique: int = Field(ge=1, le=99)
    movement: int = Field(ge=1, le=99)
    physical: int = Field(ge=1, le=99)
    mental: int = Field(ge=1, le=99)
    consistency: int = Field(ge=1, le=99)
    clutch: int = Field(ge=1, le=99)
    recovery: int = Field(ge=1, le=99)
    play_style: str
    archetype: str
    hidden_career_traits: HiddenCareerTraits
