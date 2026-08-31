"""Matches bounded-context exports."""

from beta_engine.domain.matches.formats import (
    OFFICIAL_MATCH_FORMAT,
    EffectiveMatchFormatSnapshot,
    MatchFormat,
    official_match_format_snapshot,
    resolve_effective_match_format,
)
from beta_engine.domain.matches.inputs import MatchInputSnapshot
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
    "OFFICIAL_MATCH_FORMAT",
    "EffectiveMatchFormatSnapshot",
    "MatchContext",
    "MatchEngine",
    "MatchFormat",
    "MatchInputSnapshot",
    "MatchParticipantContext",
    "MatchResult",
    "MatchTerminationReason",
    "RetirementRule",
    "RetirementTrigger",
    "SetResult",
    "official_match_format_snapshot",
    "resolve_effective_match_format",
]
