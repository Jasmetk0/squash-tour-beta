"""Pure authority contract for the first formal MSA Tour-entry trigger."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


TourEntryTriggerKind = Literal[
    "valid_tournament_application",
    "definitive_wild_card_assignment",
]


class PlayerTourEntryTrigger(FrozenInput):
    """Immutable evidence that one pre-Tour player reached the Master Tour-entry trigger.

    This is deliberately only a domain authority contract. It does not decide whether
    an application is valid, whether a Wild Card is definitive, or whether the player
    later survives a field cut. Those facts must be proven by the referenced upstream
    authority before this trigger is constructed.

    The effective career boundary is the exact FAX week plus global Simulation Slot in
    which the trigger occurred. Official Ranking publication is intentionally separate:
    a newly entered player is not retroactively inserted into an already-published
    snapshot.
    """

    schema_version: Literal["player_tour_entry_trigger.v1"] = (
        "player_tour_entry_trigger.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    trigger_kind: TourEntryTriggerKind
    trigger_week: RankingWeek
    decision_slot_ordinal: int = Field(ge=1)
    source_evidence_id: str = Field(min_length=1, max_length=256)
    source_evidence_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: str = Field(min_length=1)

    @property
    def tour_entry_week(self) -> RankingWeek:
        """The lifecycle Tour-entry week implied by this exact trigger."""

        return self.trigger_week

    @property
    def decision_position(self) -> tuple[int, int]:
        """Stable chronological key without relying on processing order."""

        return (self.trigger_week.ordinal, self.decision_slot_ordinal)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
