"""Immutable-shape qualifier link shared by match plans and legacy packages."""

from typing import Literal

from pydantic import BaseModel, Field


class FrozenQualifierPromotion(BaseModel):
    qualifier_index: int = Field(ge=1)
    source_match_id: str
    target_match_id: str
    target_side: Literal["top", "bottom"]
    target_slot_id: str
