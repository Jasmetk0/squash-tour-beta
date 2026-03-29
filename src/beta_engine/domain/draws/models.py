"""Deterministic tournament draw structures for qualification and main draws."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from beta_engine.domain.entries.models import AcceptanceStatus


class DrawType(str, Enum):
    QUALIFICATION = "QUALIFICATION"
    MAIN = "MAIN"


class DrawEntrantType(str, Enum):
    PLAYER = "PLAYER"
    QUALIFIER_PLACEHOLDER = "QUALIFIER_PLACEHOLDER"
    WILD_CARD_PLACEHOLDER = "WILD_CARD_PLACEHOLDER"
    WITHDRAWAL_PLACEHOLDER = "WITHDRAWAL_PLACEHOLDER"
    LATE_REPLACEMENT_PLACEHOLDER = "LATE_REPLACEMENT_PLACEHOLDER"
    BYE = "BYE"
    TBD = "TBD"


class DrawSlot(BaseModel):
    """One position in a draw bracket."""

    slot_index: int = Field(gt=0)
    seed_number: int | None = Field(default=None, ge=1)
    entrant_type: DrawEntrantType
    entry_id: str | None = None
    player_id: str | None = None
    acceptance_status: AcceptanceStatus | None = None
    is_seed_protected: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class DrawNode(BaseModel):
    """A bracket node/match structure with deterministic sources."""

    node_id: str
    round_number: int = Field(ge=1)
    round_sequence: int = Field(ge=1)
    source_top: str
    source_bottom: str


class LuckyLoserHook(BaseModel):
    """Future-facing lucky loser replacement attachment points."""

    enabled: bool
    replacement_window: str
    max_spots: int = Field(ge=0)
    candidate_slot_indexes: list[int] = Field(default_factory=list)


class GeneratedDraw(BaseModel):
    """Generated draw output consumable by future tournament/match engines."""

    event_id: str
    draw_type: DrawType
    bracket_size: int = Field(gt=0)
    target_draw_size: int = Field(gt=0)
    seeds_count: int = Field(ge=0)
    seed_positions: dict[int, int] = Field(default_factory=dict)
    slots: list[DrawSlot]
    nodes: list[DrawNode]
    qualifier_slot_indexes: list[int] = Field(default_factory=list)
    wild_card_slot_indexes: list[int] = Field(default_factory=list)
    bye_slot_indexes: list[int] = Field(default_factory=list)
    lucky_loser_hook: LuckyLoserHook | None = None
