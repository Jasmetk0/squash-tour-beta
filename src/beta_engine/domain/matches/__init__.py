"""Matches bounded-context exports."""

from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import (
    MatchContext,
    MatchParticipantContext,
    MatchResult,
    MatchTerminationReason,
    RetirementRule,
    RetirementTrigger,
    SetResult,
)

__all__ = [
    "MatchContext",
    "MatchEngine",
    "MatchParticipantContext",
    "MatchResult",
    "MatchTerminationReason",
    "RetirementRule",
    "RetirementTrigger",
    "SetResult",
]
