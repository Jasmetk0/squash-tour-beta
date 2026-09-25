"""Reviewed InitialWorld adoption from a Run-owned generated World pool."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.initial_world import (
    InitialWorldState,
    resolve_initial_world_lifecycle_policy,
)
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
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db import SimulationPersistenceRepository


class RunWorldInitialWorldAdoptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    command_id: str = Field(min_length=1, max_length=128)
    world_package_id: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
    )
    season: Literal["2000/2001"] = "2000/2001"
    generation_seed: int
    target_pool_size: int = Field(ge=1, le=2000)
    country_code: str | None = Field(default=None, min_length=3, max_length=3)
    region: str | None = Field(default=None, min_length=1)
    bootstrap_seed: int
    audit_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    official_run: bool = False
    best_n: int | None = Field(default=None, ge=1)
    automatic_retirement_age: int | None = Field(default=None, ge=16, le=120)

    @model_validator(mode="after")
    def validate_policy(self) -> "RunWorldInitialWorldAdoptionRequest":
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


class RunWorldInitialWorldPreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_world_initial_world_preview.v1"] = (
        "run_world_initial_world_preview.v1"
    )
    run_id: str
    branch_id: str
    request: RunWorldInitialWorldAdoptionRequest
    run_package_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    initial_pool_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_country_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_generation_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    state: InitialWorldState
    preview_only: Literal[True] = True

    @property
    def preview_fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


@dataclass(slots=True)
class RunWorldInitialWorldAdoptionService:
    repository: SimulationPersistenceRepository
    pool_preview_service: RunWorldInitialPoolPreviewService

    def preview(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: RunWorldInitialWorldAdoptionRequest,
    ) -> RunWorldInitialWorldPreview:
        branch = self.repository.get_run_branch(branch_id=branch_id)
        if branch is None or branch.run_id != run_id:
            raise ValueError("Initial-world Run/Branch scope not found")

        pool_preview = self.pool_preview_service.preview(
            run_id=run_id,
            branch_id=branch_id,
            request=RunWorldInitialPoolPreviewRequest(
                world_package_id=request.world_package_id,
                season=request.season,
                seed=request.generation_seed,
                target_pool_size=request.target_pool_size,
                country_code=request.country_code,
                region=request.region,
            ),
        )
        players = tuple(
            sorted(
                (
                    self._convert_player(
                        player,
                        season=request.season,
                        bootstrap_seed=request.bootstrap_seed,
                        pool_preview_fingerprint=pool_preview.preview_fingerprint,
                    )
                    for player in pool_preview.result.players
                ),
                key=lambda item: item.player_id,
            )
        )
        bootstrap_id = self._bootstrap_id(
            run_id=run_id,
            branch_id=branch_id,
            request=request,
            pool_preview_fingerprint=pool_preview.preview_fingerprint,
        )
        players = tuple(
            player.model_copy(update={"bootstrap_id": bootstrap_id})
            for player in players
        )
        bootstrap_fingerprint = canonical_hash(
            {
                "schema_version": "run_world_initial_world_bootstrap.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "request_fingerprint": request.fingerprint_for_scope(
                    run_id=run_id, branch_id=branch_id
                ),
                "pool_preview_fingerprint": pool_preview.preview_fingerprint,
                "player_bootstrap_fingerprints": [
                    player.bootstrap_fingerprint for player in players
                ],
            }
        )
        best_n = 15 if request.official_run else request.best_n
        if best_n is None:
            raise ValueError("Custom Run requires an explicit first-season Best N")

        state = InitialWorldState(
            run_id=run_id,
            branch_id=branch_id,
            players=players,
            policies=(
                OfficialRankingPolicy(
                    policy_id="msa-official-2000-01",
                    best_n=best_n,
                ),
            ),
            source_kind="run_world_generated_pool.v1",
            source_season=request.season,
            source_fingerprint=pool_preview.preview_fingerprint,
            world_package_id=request.world_package_id,
            world_country_content_fingerprint=(
                pool_preview.world_country_content_fingerprint
            ),
            world_generation_content_fingerprint=(
                pool_preview.world_generation_content_fingerprint
            ),
            bootstrap_seed=request.bootstrap_seed,
            bootstrap_fingerprint=bootstrap_fingerprint,
            adopted_by_command_id=request.command_id,
            audit_label=request.audit_label,
            audit_reason=request.audit_reason,
            adoption_request_fingerprint=request.fingerprint_for_scope(
                run_id=run_id, branch_id=branch_id
            ),
        )
        return RunWorldInitialWorldPreview(
            run_id=run_id,
            branch_id=branch_id,
            request=request,
            run_package_state_fingerprint=(
                pool_preview.run_package_state_fingerprint
            ),
            initial_pool_preview_fingerprint=pool_preview.preview_fingerprint,
            world_country_content_fingerprint=(
                pool_preview.world_country_content_fingerprint
            ),
            world_generation_content_fingerprint=(
                pool_preview.world_generation_content_fingerprint
            ),
            state=state,
        )

    def confirm(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: RunWorldInitialWorldAdoptionRequest,
        expected_state_fingerprint: str,
    ) -> InitialWorldState:
        current = self.repository.get_initial_world(
            run_id=run_id, branch_id=branch_id
        )
        request_fingerprint = request.fingerprint_for_scope(
            run_id=run_id, branch_id=branch_id
        )
        if current is not None:
            if (
                current.source_kind != "run_world_generated_pool.v1"
                or current.adopted_by_command_id != request.command_id
                or current.adoption_request_fingerprint != request_fingerprint
                or current.fingerprint != expected_state_fingerprint
            ):
                raise ValueError(
                    "Initial-world adoption retry differs from the stored request"
                )
            self.repository.ensure_initial_world_lifecycle(
                current,
                policy=resolve_initial_world_lifecycle_policy(
                    official_run=request.official_run,
                    automatic_retirement_age=request.automatic_retirement_age,
                ),
            )
            return current

        preview = self.preview(
            run_id=run_id, branch_id=branch_id, request=request
        )
        if preview.state.fingerprint != expected_state_fingerprint:
            raise ValueError(
                "Run-owned generated Initial World changed since preview"
            )
        return self.repository.adopt_initial_world(
            preview.state,
            lifecycle_policy=resolve_initial_world_lifecycle_policy(
                official_run=request.official_run,
                automatic_retirement_age=request.automatic_retirement_age,
            ),
            expected_run_package_state_fingerprint=(
                preview.run_package_state_fingerprint
            ),
        )

    @staticmethod
    def _bootstrap_id(
        *,
        run_id: str,
        branch_id: str,
        request: RunWorldInitialWorldAdoptionRequest,
        pool_preview_fingerprint: str,
    ) -> str:
        suffix = canonical_hash(
            {
                "schema_version": "run_world_initial_world_bootstrap_id.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "request": request.model_dump(mode="json"),
                "pool_preview_fingerprint": pool_preview_fingerprint,
            }
        )[:20]
        return f"BOOT-RUNWORLD-{suffix}"

    @staticmethod
    def _convert_player(
        player,
        *,
        season: str,
        bootstrap_seed: int,
        pool_preview_fingerprint: str,
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
        player_bootstrap_fingerprint = canonical_hash(
            {
                "schema_version": "run_world_player_bootstrap.v1",
                "season": season,
                "bootstrap_seed": bootstrap_seed,
                "pool_preview_fingerprint": pool_preview_fingerprint,
                "player_id": player.player_id,
                "player_generation_fingerprint": player.generation_fingerprint,
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
            manual_override=False,
            locked_from_initial_pool=False,
            bootstrap_fingerprint=player_bootstrap_fingerprint,
            bootstrap_seed=bootstrap_seed,
            bootstrap_id="pending",
        )
