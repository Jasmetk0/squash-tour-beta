"""Read-only v2 Run generation, isolated from legacy adoption and replay."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldExactCountryQuota,
)
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.players.calendar_initial_pool import (
    CalendarInitialPlayerPoolGenerator,
    CalendarInitialPoolResult,
    InitialPoolCalendarBasis,
)
from beta_engine.domain.run_packages import canonical_hash

if TYPE_CHECKING:
    from beta_engine.infrastructure.db import SimulationPersistenceRepository


class RunCalendarInitialPoolPreviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["run_calendar_initial_pool_request.v2"] = "run_calendar_initial_pool_request.v2"
    world_package_id: str = Field(min_length=1, max_length=128)
    seed: int = Field(ge=0, le=2**63 - 1)
    target_pool_size: int = Field(default=128, ge=1, le=10000)
    min_age: int = Field(default=15, ge=15, le=45)
    max_age: int = Field(default=45, ge=15, le=45)
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    geographic_region: str | None = Field(default=None, min_length=1, max_length=128)
    travel_region: str | None = Field(default=None, min_length=1, max_length=128)
    country_quotas: list[RunWorldExactCountryQuota] = Field(default_factory=list, max_length=1000)
    naming_policy: Literal["country_serial.v1"] = "country_serial.v1"

    @model_validator(mode="after")
    def validate_conditions(self):
        if self.min_age > self.max_age:
            raise ValueError("min_age must not exceed max_age")
        codes = [quota.country_code for quota in self.country_quotas]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate country quotas")
        return self


class RunCalendarInitialPoolPreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_calendar_initial_pool_preview.v2"] = "run_calendar_initial_pool_preview.v2"
    run_id: str
    branch_id: str
    calendar_saved_revision_id: str | None
    run_calendar: dict
    run_package_state_fingerprint: str
    world_country_content_fingerprint: str
    world_generation_content_fingerprint: str
    request: RunCalendarInitialPoolPreviewRequest
    result: CalendarInitialPoolResult
    python_runtime: str
    preview_only: Literal[True] = True
    adoption_supported: Literal[False] = False
    package_source: Literal["run_owned_working_state"] = "run_owned_working_state"
    limitations: tuple[str, ...] = (
        "calendar_v2_adoption_lifecycle_and_sporting_execution_not_implemented",
        "keep_edit_and_saved_proposals_require_a_versioned_v2_followup",
        "cross_python_runtime_regeneration_equivalence_not_guaranteed",
    )
    country_rating_sources: list[dict]

    @property
    def preview_fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


@dataclass(slots=True)
class RunCalendarInitialPoolPreviewService:
    repository: SimulationPersistenceRepository
    world_adapter: WorldPackageRunAdapter

    def preview(self, *, run_id: str, branch_id: str,
                request: RunCalendarInitialPoolPreviewRequest) -> RunCalendarInitialPoolPreview:
        # Imports stay local to avoid repository -> generation -> db cycles.
        from beta_engine.application.run_calendar_read_authority import (
            resolve_saved_run_calendar,
        )
        from beta_engine.infrastructure.db.models import RunBranchModel
        from beta_engine.infrastructure.db.run_package_state import (
            get_run_package_state,
        )

        with self.repository._session_factory() as session:
            # sqlite3's legacy transaction mode does not BEGIN for SELECT. An
            # explicit read transaction binds clock, Saved proof and package
            # content to a single snapshot without locking a writer or writing.
            session.connection().exec_driver_sql("BEGIN")
            calendar = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
            branch = session.get(RunBranchModel, branch_id)
            saved_revision_id = branch.saved_head_revision_id
            state = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
            if state is None:
                raise ValueError("Run Package state is empty")
            # Projection and sampling need no open database transaction. These
            # are detached validated snapshot objects, never live source files.
        countries = self.world_adapter.project_countries(state, package_id=request.world_package_id)
        generation = self.world_adapter.project_generation(state, package_id=request.world_package_id)
        selected = list(countries.countries)
        for requested, attribute, label in (
            (request.country_code, "code", "country"),
            (request.geographic_region, "region", "Geographic Region"),
            (request.travel_region, "effective_travel_region", "Travel Region"),
        ):
            if requested is not None:
                selected = [country for country in selected if getattr(country, attribute) == requested]
                if not selected:
                    raise ValueError(f"No saved World countries satisfy the {label} condition '{requested}'")
        generator = CalendarInitialPlayerPoolGenerator(
            identity_config=generation.identity_config,
            time_basis=InitialPoolCalendarBasis.from_run_calendar(calendar),
            minimum_age=request.min_age, maximum_age=request.max_age,
        )
        result = generator.generate(
            countries=selected, seed=request.seed, target_pool_size=request.target_pool_size,
            country_quotas={quota.country_code: quota.count for quota in request.country_quotas},
            naming_policy=request.naming_policy, dry_run=True,
        )
        # Expose the exact years behind the attribute inputs. Outside observed
        # coverage a nearest endpoint is an estimate, never an invented record.
        rating_sources = []
        years = sorted({calendar.start_year, *generator._birth_year_weights(calendar.start_year)})
        for country in selected:
            history = country.rating_history
            entries = []
            for year in years:
                if history is None:
                    entries.append({"requested_year": year, "kind": "static_snapshot", "source_years": []})
                elif country.rating_resolution_version is not None and 1954 <= year <= 2050:
                    resolved = history.resolve_effective(year)
                    first = next(iter(resolved.values()))
                    entries.append({"requested_year": year, "kind": first.kind,
                                    "source_years": list(first.source_years)})
                else:
                    source = min(history.years, key=lambda y: (abs(y - year), y))
                    entries.append({"requested_year": year,
                                    "kind": "exact" if source == year else "nearest_fallback",
                                    "source_years": [source]})
            rating_sources.append({"country_code": country.code, "years": entries})
        # Explicit legacy marker stays read-only; never write legacy metadata.
        calendar_payload = {
            "schema_version": calendar.schema_version,
            "weeks_per_year": calendar.weeks_per_year,
            "season_start_year_week": calendar.season_start_year_week,
            "start_year": calendar.start_year, "season_count": calendar.season_count,
        }
        return RunCalendarInitialPoolPreview(
            run_id=run_id, branch_id=branch_id,
            calendar_saved_revision_id=saved_revision_id, run_calendar=calendar_payload,
            run_package_state_fingerprint=state.fingerprint,
            world_country_content_fingerprint=countries.content_fingerprint,
            world_generation_content_fingerprint=generation.content_fingerprint,
            request=request, result=result, python_runtime=platform.python_version(),
            country_rating_sources=rating_sources,
        )
