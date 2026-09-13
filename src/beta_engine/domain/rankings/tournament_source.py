"""Frozen, independently owned evidence for a supported tournament source."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.season_event_results_service import SeasonEventResultPackage
from beta_engine.application.season_point_awards_service import EventPointAwardPackage
from beta_engine.domain.rankings.official import FrozenInput


class OwnedTournamentRankingSource(FrozenInput):
    schema_version: Literal["owned_tournament_ranking_source.v1"] = "owned_tournament_ranking_source.v1"
    binding: TournamentRankingBinding
    result: SeasonEventResultPackage
    awards: EventPointAwardPackage
    adopted_by_command_id: str = Field(min_length=1, max_length=128)
    provenance_kind: Literal["explicit_legacy_tournament_adoption"] = "explicit_legacy_tournament_adoption"

    @model_validator(mode="after")
    def validate_identity(self):
        if self.binding.event_id != self.result.event_id or self.binding.event_id != self.awards.event_id:
            raise ValueError("Owned tournament source event identity mismatch")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
