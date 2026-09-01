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
from beta_engine.domain.matches.rallies import (
    MatchRallyLog,
    PostRallyStateSnapshot,
    RallyAnalyticalAttribution,
    RallyEvent,
    RallyScoreMutation,
    RallyScoreSnapshot,
    RallyTerminalTrigger,
)

__all__ = [
    "OFFICIAL_MATCH_FORMAT",
    "EffectiveMatchFormatSnapshot",
    "MatchContext",
    "MatchEngine",
    "MatchFormat",
    "MatchInputSnapshot",
    "MatchParticipantContext",
    "MatchRallyLog",
    "MatchResult",
    "MatchTerminationReason",
    "PostRallyStateSnapshot",
    "RallyAnalyticalAttribution",
    "RallyEvent",
    "RallyScoreMutation",
    "RallyScoreSnapshot",
    "RallyTerminalTrigger",
    "RetirementRule",
    "RetirementTrigger",
    "SetResult",
    "official_match_format_snapshot",
    "resolve_effective_match_format",
]
