"""Master v87 Turn Pro: a separate lifecycle event that grants Tour Player status.

Under a lifecycle policy with ``tour_entry_rule="turn_pro.v87"`` a prospect becomes
a Tour Player only through a :class:`PlayerTurnProDecision`. Its week is chosen by
the player's AI (the decision model itself is an open Master item and lives
elsewhere); this module only owns the immutable contract and its pure validation:

* the decision is made during the Week Transition *into* ``effective_week`` and is
  effective from the start of that week, so a first application or definitive wild
  card may happen in the same week but never before it;
* applications and wild cards no longer create Tour entry under this rule;
* history recorded under the earlier policy is never reinterpreted (that policy
  keeps ``tour_entry_rule=None`` and its exact serialized bytes).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash

TurnProDecisionSource = Literal["player_ai"]


def turn_pro_tie_break_token(*, run_id: str, branch_id: str, player_id: str) -> str:
    """Stable NR tie-break token, domain-separated from application tokens."""
    return canonical_hash(
        {"kind": "turn_pro.v87", "run": run_id, "branch": branch_id, "player": player_id}
    )


def opening_turn_pro_tie_break_token(*, run_id: str, player_id: str) -> str:
    """Token of a player who was already pro at Run start.

    Keyed by Run, not Branch: pre-Run history is shared by every fork.
    """
    return canonical_hash({"kind": "initial_turn_pro.v1", "run": run_id, "player": player_id})


class PlayerTurnProDecision(FrozenInput):
    """Immutable evidence that one prospect turned professional at a week start."""

    schema_version: Literal["player_turn_pro_decision.v1"] = "player_turn_pro_decision.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    effective_week: RunWeekPosition
    decision_source: TurnProDecisionSource
    # Fingerprint of the exact pre-transition inputs the decision was made from.
    source_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: str = Field(min_length=1)

    @property
    def tie_break_token(self) -> str:
        return turn_pro_tie_break_token(
            run_id=self.run_id, branch_id=self.branch_id, player_id=self.player_id
        )

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def turn_pro_decisions_by_player(
    decisions: Iterable[PlayerTurnProDecision], *, run_id: str, branch_id: str
) -> dict[str, PlayerTurnProDecision]:
    """Index decisions; a player turns pro at most once in a Branch history."""
    indexed: dict[str, PlayerTurnProDecision] = {}
    for decision in decisions:
        if (decision.run_id, decision.branch_id) != (run_id, branch_id):
            raise ValueError("Foreign Turn Pro decision")
        if decision.player_id in indexed:
            raise ValueError("A player can turn pro only once")
        indexed[decision.player_id] = decision
    return indexed


def is_professional_at(lifecycle, player_id: str, week: RunWeekPosition) -> bool:
    """Whether the lifecycle shows this player as a Tour Player in ``week``."""
    player = next((p for p in lifecycle.players if p.player_id == player_id), None)
    entry = getattr(player, "tour_entry_week", None)
    return entry is not None and entry.ordinal <= week.ordinal


def require_professional_for_entry(lifecycle, player_id: str, week: RunWeekPosition) -> None:
    """Master v87 gate for a first application or a definitive wild card.

    Under the historical rule an application itself creates Tour entry, so there is
    nothing to check here. Under ``turn_pro.v87`` the player must already have
    turned pro at or before ``week``.
    """
    if not lifecycle.policy.requires_turn_pro:
        return
    if not is_professional_at(lifecycle, player_id, week):
        raise ValueError(
            "Player has not turned pro; a first MSA Tour application or wild card "
            "is allowed only from the Turn Pro week"
        )
