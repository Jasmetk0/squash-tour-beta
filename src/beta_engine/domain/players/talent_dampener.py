"""Foundation interfaces for future country greatness dampening."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from beta_engine.domain.players.talent_models import TalentQualityBand


class RecentGreatnessDampener(Protocol):
    """Interface for future logic reducing anomaly spawn after manual legends."""

    def quality_multiplier(self, *, country_code: str, year: int, band: TalentQualityBand) -> float:
        """Return multiplicative weight for the provided quality band."""


@dataclass(frozen=True, slots=True)
class NeutralRecentGreatnessDampener:
    """Default no-op dampener used until admin/history wiring is introduced."""

    def quality_multiplier(self, *, country_code: str, year: int, band: TalentQualityBand) -> float:
        _ = (country_code, year, band)
        return 1.0
