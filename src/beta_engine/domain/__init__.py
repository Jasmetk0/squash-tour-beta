"""Domain package exports by bounded context."""

from beta_engine.domain.countries import CountriesConfig, Country, CountryTalentModel
from beta_engine.domain.players import HiddenCareerTraits, Player, PlayerGenerator
from beta_engine.domain.draws import (
    DrawEngine,
    DrawEntrantType,
    DrawNode,
    DrawSlot,
    DrawType,
    GeneratedDraw,
    LuckyLoserHook,
)
from beta_engine.domain.matches import (
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchResult,
    MatchTerminationReason,
    RetirementRule,
    RetirementTrigger,
    SetResult,
)

from beta_engine.domain.entries import (
    AcceptanceList,
    AcceptanceStatus,
    EntryDecision,
    EntryEngine,
    EntryTarget,
    EntryTuningConfig,
    TournamentEntry,
)
from beta_engine.domain.tournaments import (
    CalendarEvent,
    LuckyLoserRules,
    SeasonCalendar,
    TournamentPointDistribution,
    TournamentTemplate,
    TournamentTemplatesConfig,
    validate_calendar_template_references,
)

__all__ = [
    "CountriesConfig",
    "Country",
    "CountryTalentModel",
    "HiddenCareerTraits",
    "Player",
    "PlayerGenerator",
    "DrawEngine",
    "DrawEntrantType",
    "DrawNode",
    "DrawSlot",
    "DrawType",
    "GeneratedDraw",
    "LuckyLoserHook",
    "MatchContext",
    "MatchEngine",
    "MatchParticipantContext",
    "MatchResult",
    "MatchTerminationReason",
    "RetirementRule",
    "RetirementTrigger",
    "SetResult",
    "AcceptanceList",
    "AcceptanceStatus",
    "EntryDecision",
    "EntryEngine",
    "EntryTarget",
    "EntryTuningConfig",
    "TournamentEntry",
    "CalendarEvent",
    "LuckyLoserRules",
    "SeasonCalendar",
    "TournamentPointDistribution",
    "TournamentTemplate",
    "TournamentTemplatesConfig",
    "validate_calendar_template_references",
]
