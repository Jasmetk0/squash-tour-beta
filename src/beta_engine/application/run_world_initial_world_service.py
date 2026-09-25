"""Reviewed InitialWorld adoption from a Run-owned World generated pool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest,
    RunWorldInitialPoolPreviewService,
)
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    completed_weeks_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.initial_pool import InitialPoolGeneratedPlayer
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.run_packages import canonical_hash


class RunWorldInitialWorldAdoptionRequest(BaseModel):
    """Exact reviewed command used to adopt a Run-owned generated player pool."""

    model_config = ConfigDict(extra="forbid", strict=True)

    command_id: str = Field(min_length=1, max_length=128)
    generation: RunWorldInitialPoolPreviewRequest
    audit_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    official_run: bool = False
    best_n: int | None = Field(default=None, ge=1)
    automatic_retirement_age: int | None = Field(default=None, ge=16, le=120)

    @model_validator(mode="after")
    def validate_initial_world_scope(self) -> "RunWorldInitialWorldAdoptionRequest":
        if self.generation.season != "2000/2001":
            raise ValueError("InitialWorld V1 must adopt season 2000/2001")
        if self.official_run and self.best_n not in (None, 15):
            raise ValueError("Official Run first-season policy is Best 15")
        if not self.official_run and self.best_n is None:
            raise ValueError("Custom Run requires an explicit first-season Best N")
        if self.official_run and self.automatic_retirement_age not in (None, 46):
            raise ValueError("Official Run automatic retirement age is 46")
        return self

    def fingerprint_for_scope(self, *, run_id: str, branch_id: str) -> str:
        return canonical_hash(
            {
                "run_id": run_id,
                "branch_id": branch_id,
                **self.model_dump(mode="json"),
            }
        )


@dataclass(slots=True)
class RunWorldInitialWorldService:
    """Resolve immutable InitialWorld state only from Run-owned Package material."""

    preview_service: RunWorldInitialPoolPreviewService

    def preview(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: RunWorldInitialWorldAdoptionRequest,
    ) -> InitialWorldState:
        pool = self.preview_service.preview(
            run_id=run_id,
            branch_id=branch_id,
            request=request.generation,
        )
        players = tuple(
            sorted(
                (
                    self._convert_player(
                        player,
                        season=request.generation.season,
                        bootstrap_seed=request.generation.seed,
                        source_fingerprint=pool.preview_fingerprint,
                    )
                    for player in pool.result.players
                ),
                key=lambda player: player.player_id,
            )
        )
        best_n = 15 if request.official_run else request.best_n
        if best_n is None:
            raise ValueError("Custom Run requires an explicit first-season Best N")
        bootstrap_fingerprint = canonical_hash(
            {
                "pool_preview_fingerprint": pool.preview_fingerprint,
                "bootstrap_seed": request.generation.seed,
                "players": [player.model_dump(mode="json") for player in players],
            }
        )
        return InitialWorldState(
            run_id=run_id,
            branch_id=branch_id,
            players=players,
            policies=(
                OfficialRankingPolicy(policy_id="msa-official-2000-01", best_n=best_n),
            ),
            source_kind="run_world_generated_pool.v1",
            source_season=request.generation.season,
            source_fingerprint=pool.preview_fingerprint,
            world_package_id=request.generation.world_package_id,
            world_country_content_fingerprint=pool.world_country_content_fingerprint,
            world_generation_content_fingerprint=pool.world_generation_content_fingerprint,
            run_world_pool_preview_fingerprint=pool.preview_fingerprint,
            bootstrap_seed=request.generation.seed,
            bootstrap_fingerprint=bootstrap_fingerprint,
            adopted_by_command_id=request.command_id,
            audit_label=request.audit_label,
            audit_reason=request.audit_reason,
            adoption_request_fingerprint=request.fingerprint_for_scope(
                run_id=run_id, branch_id=branch_id
            ),
        )

    @staticmethod
    def _convert_player(
        player: InitialPoolGeneratedPlayer,
        *,
        season: Literal["2000/2001"],
        bootstrap_seed: int,
        source_fingerprint: str,
    ) -> SeasonActivePlayer:
        season_start_year = int(season.split("/", 1)[0])
        initial_position = season_week_to_calendar_position(season_start_year, 1)
        age_years = age_at_calendar_position(
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            calendar_year=initial_position.calendar_year,
            year_week=initial_position.year_week,
        )
        age_weeks = completed_weeks_at_calendar_position(
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            calendar_year=initial_position.calendar_year,
            year_week=initial_position.year_week,
        )
        bootstrap_id = "RUN-WORLD-" + canonical_hash(
            {
                "season": season,
                "seed": bootstrap_seed,
                "source": source_fingerprint,
            }
        )[:16]
        player_bootstrap_fingerprint = canonical_hash(
            {
                "bootstrap_id": bootstrap_id,
                "player_id": player.player_id,
                "generation_fingerprint": player.generation_fingerprint,
            }
        )
        return SeasonActivePlayer(
            player_id=player.player_id,
            name=player.name,
            country_code=player.country_code,
            nationality=player.nationality or player.country_code,
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            age_years_at_season_start=age_years,
            age_weeks_at_season_start=age_weeks,
            current_ability=player.current_ability,
            potential_ability=player.potential_ability,
            potential_tier=player.potential_tier,
            career_stage=player.career_stage,
            play_style=player.play_style,
            archetype=player.archetype,
            attributes=player.attributes,
            hidden_career_traits=player.hidden_career_traits,
            health_status="fresh",
            active_status="active",
            ranking_points=0,
            race_points=0,
            protected_ranking_points=0,
            season=season,
            source_pool_player_id=player.player_id,
            source_generation_fingerprint=player.generation_fingerprint,
            source_generation="initial_pool",
            manual_override=player.manual_override,
            locked_from_initial_pool=player.locked,
            bootstrap_fingerprint=player_bootstrap_fingerprint,
            bootstrap_seed=bootstrap_seed,
            bootstrap_id=bootstrap_id,
        )
