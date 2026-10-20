"""Confirmed native birth weeks over an immutable historical Tour root.

This bounded v3 supports natural Week/Season transitions only after first birth.
Edition/Entry/match edits require their own born-player authorities, never an
implicit upgrade of the old InitialWorld-only competition adapters.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.tournaments.calendar_tour import CalendarTourState


class CalendarNativeTourState(CalendarTourState):
    schema_version: Literal["calendar_tour_authority.v3"] = "calendar_tour_authority.v3"
    native_root_tour: CalendarTourState
    native_root_saved_head: str = Field(min_length=1)
    native_root_health_state_count: int = Field(ge=1)

    @model_validator(mode="after")
    def native_prefix_and_receipts(self):
        root = self.native_root_tour
        if (
            (root.run_id, root.branch_id) != (self.run_id, self.branch_id)
            or root.week.ordinal >= self.week.ordinal
            or self.policies != root.policies
            or self.editions != root.editions
            or self.slot_cursor != 0
            or self.native_root_health_state_count > root.week.ordinal + 1
            or self.rankings[: len(root.rankings)] != root.rankings
            or self.transitions[: len(root.transitions)] != root.transitions
            or self.receipts[: len(root.receipts)] != root.receipts
            or len(self.receipts) - len(root.receipts)
            != len(self.transitions) - len(root.transitions)
        ):
            raise ValueError(
                "Native Tour cannot rewrite its historical root or invent Edition operations"
            )
        extra = self.receipts[len(root.receipts) :]
        first_command = extra[0].request.get("command") if extra else None
        if (
            not extra
            or not isinstance(first_command, dict)
            or first_command.get("expected_saved_head") != self.native_root_saved_head
        ):
            raise ValueError("Native Tour lacks its confirmed first-birth Saved origin")
        if any(
            r.result.get("action") not in {"transition", "season-transition"}
            for r in extra
        ):
            raise ValueError(
                "Native Tour v3 supports natural Week/Season transitions only"
            )
        return self
