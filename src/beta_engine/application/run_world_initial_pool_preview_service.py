"""Read-only initial-player pool preview from Run-owned World Package state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.players.initial_pool import InitialPlayerPoolGenerator, InitialPoolResult
from beta_engine.domain.run_packages import canonical_hash


class RunWorldInitialPoolPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    world_package_id: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
    )
    season: str = Field(default="2000/2001", min_length=4, max_length=32)
    seed: int
    target_pool_size: int = Field(default=128, ge=1, le=2000)
    country_code: str | None = Field(default=None, min_length=3, max_length=3)
    region: str | None = Field(default=None, min_length=1)  # Legacy union for replay
    geographic_region: str | None = Field(default=None, min_length=1)
    travel_region: str | None = Field(default=None, min_length=1)
    min_age: int | None = Field(default=None, ge=15, le=45)
    max_age: int | None = Field(default=None, ge=15, le=45)

    @model_validator(mode="after")
    def validate_age_range(self) -> "RunWorldInitialPoolPreviewRequest":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("Age condition requires minimum age no higher than maximum age")
        return self

    def fingerprint_payload(self) -> dict:
        """Preserve the pre-extension request digest for absent optional extensions.

        Old saved requests contained the legacy `region` field, but not the
        newer typed geography or Keep extensions. Do not hash injected defaults.
        """
        payload = self.model_dump(mode="json")
        for field in (
            "geographic_region", "travel_region", "keep_from_seed",
            "keep_from_preview_fingerprint", "keep_player_ids",
        ):
            if payload.get(field) is None or payload.get(field) == []:
                payload.pop(field, None)
        return payload


class RunWorldInitialPoolPreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_world_initial_pool_preview.v1"] = (
        "run_world_initial_pool_preview.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    world_package_id: str = Field(min_length=1)
    run_package_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_country_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_generation_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: RunWorldInitialPoolPreviewRequest
    result: InitialPoolResult
    preview_only: Literal[True] = True

    @property
    def preview_fingerprint(self) -> str:
        payload = self.model_dump(mode="json")
        payload["request"] = self.request.fingerprint_payload()
        return canonical_hash(payload)


@dataclass(slots=True)
class RunWorldInitialPoolPreviewService:
    package_service: RunPackageService
    world_adapter: WorldPackageRunAdapter

    def preview(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: RunWorldInitialPoolPreviewRequest,
    ) -> RunWorldInitialPoolPreview:
        state = self.package_service.get(run_id=run_id, branch_id=branch_id)
        if state is None:
            raise ValueError("Run Package state is empty")

        countries = self.world_adapter.project_countries(
            state, package_id=request.world_package_id
        )
        generation = self.world_adapter.project_generation(
            state, package_id=request.world_package_id
        )

        # These are hard generation conditions, not distribution hints.
        # Diagnose contradictions against the Run-owned snapshot itself;
        # never fall back to another country, region, or global World.
        selected_countries = list(countries.countries)
        if request.country_code:
            code = request.country_code.upper()
            if not any(country.code == code for country in selected_countries):
                raise ValueError(
                    f"Country condition '{code}' is unavailable in saved World "
                    f"'{request.world_package_id}'"
                )
            selected_countries = [
                country for country in selected_countries if country.code == code
            ]
        if request.region:
            if not any(
                request.region in (country.region, country.effective_travel_region)
                for country in selected_countries
            ):
                if request.country_code:
                    raise ValueError(
                        f"Conflicting generation conditions: country "
                        f"'{request.country_code.upper()}' does not belong to "
                        f"region '{request.region}' in the saved World"
                    )
                raise ValueError(
                    f"Region condition '{request.region}' has no eligible "
                    "countries in the saved World"
                )

        # New exact layer predicates never cross-match names. Keep old `region`
        # union semantics unchanged for previously saved inputs and replay.
        for requested, attribute, kind in (
            (request.geographic_region, "region", "Geographic Region"),
            (request.travel_region, "effective_travel_region", "Travel Region"),
        ):
            if requested:
                selected_countries = [
                    country for country in selected_countries
                    if getattr(country, attribute) == requested
                ]
                if not selected_countries:
                    raise ValueError(
                        f"Conflicting generation conditions: {kind} '{requested}' "
                        "has no eligible countries under the other saved-World conditions"
                    )

        result = InitialPlayerPoolGenerator(
            identity_config=generation.identity_config
        ).generate(
            countries=(selected_countries if request.geographic_region or request.travel_region
                       else list(countries.countries)),
            season=request.season,
            seed=request.seed,
            target_pool_size=request.target_pool_size,
            country_code=request.country_code,
            region=request.region,
            min_age=request.min_age,
            max_age=request.max_age,
            existing_locked_players=[],
            dry_run=True,
        )

        return RunWorldInitialPoolPreview(
            run_id=run_id,
            branch_id=branch_id,
            world_package_id=request.world_package_id,
            run_package_state_fingerprint=state.fingerprint,
            world_country_content_fingerprint=countries.content_fingerprint,
            world_generation_content_fingerprint=generation.content_fingerprint,
            request=request,
            result=result,
        )
