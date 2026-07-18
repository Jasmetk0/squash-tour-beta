"""Materialize deterministic run-scoped 15-year-old prospect cohorts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from beta_engine.application.run_weekly_intake_cohort_preview_service import RunWeeklyIntakeCohortPreviewService
from beta_engine.infrastructure.db import RunProspectRecord, SimulationPersistenceRepository, deterministic_prospect_id

COHORT_POLICY_VERSION = "weekly_15yo_cohort_v1"
PROFILE_VERSION = "prospect_profile_v1"
SOURCE_TYPE = "weekly_15yo_cohort"
PROSPECT_STATUS = "prospect"


@dataclass(frozen=True)
class MaterializedRunProspectCountryTotal:
    country_code: str
    country_name: str | None
    materialized_count: int


@dataclass(frozen=True)
class MaterializedRunProspectWeekTotal:
    season_week: int
    materialized_count: int


@dataclass(frozen=True)
class MaterializeRunProspectsResult:
    run_id: str
    world_id: str
    season: str
    season_start_year: int
    annual_target: int
    requested_prospect_count: int
    created_count: int
    existing_count: int
    skipped_count: int
    conflict_count: int
    total_persisted_for_scope: int
    weeks_materialized: list[MaterializedRunProspectWeekTotal]
    country_totals: list[MaterializedRunProspectCountryTotal]
    already_materialized: bool
    message: str


class RunProspectMaterializationConflictError(RuntimeError):
    def __init__(self, conflicts: list[str]) -> None:
        self.conflicts = conflicts
        super().__init__(f"{len(conflicts)} conflicting run prospect record(s) already exist")


@dataclass(slots=True)
class RunProspectMaterializationService:
    repository: SimulationPersistenceRepository
    preview_service: RunWeeklyIntakeCohortPreviewService

    def materialize_15yo_cohort(
        self,
        *,
        run_id: str,
        base_annual_intake_target: int = 200,
        season_growth_rate: float = 0.015,
        country_code: str | None = None,
        region: str | None = None,
        overwrite: bool = False,
    ) -> MaterializeRunProspectsResult:
        preview = self.preview_service.preview_season(
            run_id=run_id,
            base_annual_intake_target=base_annual_intake_target,
            season_growth_rate=season_growth_rate,
            country_code=country_code,
            region=region,
        )
        expected = self._build_records(preview)
        if not expected:
            return MaterializeRunProspectsResult(
                run_id=preview.run_id, world_id=preview.world_id, season=preview.season, season_start_year=preview.season_start_year,
                annual_target=preview.annual_target, requested_prospect_count=0, created_count=0, existing_count=0, skipped_count=0,
                conflict_count=0, total_persisted_for_scope=0, weeks_materialized=[], country_totals=[], already_materialized=True,
                message="No prospects requested for this materialization scope.",
            )

        existing_by_id = {record.prospect_id: record for record in self.repository.list_run_prospects(run_id=run_id, season_start_year=preview.season_start_year, limit=None)}
        conflicts = [record.prospect_id for record in expected if record.prospect_id in existing_by_id and existing_by_id[record.prospect_id] != record]
        if conflicts and not overwrite:
            raise RunProspectMaterializationConflictError(conflicts)

        to_upsert = [record for record in expected if overwrite or record.prospect_id not in existing_by_id]
        self.repository.upsert_run_prospects(to_upsert)
        existing_count = len(expected) - len([r for r in expected if r.prospect_id not in existing_by_id])
        created_count = len([r for r in expected if r.prospect_id not in existing_by_id])
        if overwrite:
            created_count = len([r for r in expected if r.prospect_id not in existing_by_id])
        persisted_expected_ids = {record.prospect_id for record in expected}
        persisted = [record for record in self.repository.list_run_prospects(run_id=run_id, season_start_year=preview.season_start_year, limit=None) if record.prospect_id in persisted_expected_ids]
        country_totals: dict[tuple[str, str | None], int] = {}
        week_totals: dict[int, int] = {}
        for record in expected:
            country_totals[(record.country_code, record.country_name)] = country_totals.get((record.country_code, record.country_name), 0) + 1
            week_totals[record.season_week] = week_totals.get(record.season_week, 0) + 1
        already = len(expected) == existing_count and not conflicts
        return MaterializeRunProspectsResult(
            run_id=preview.run_id, world_id=preview.world_id, season=preview.season, season_start_year=preview.season_start_year,
            annual_target=preview.annual_target, requested_prospect_count=len(expected), created_count=created_count,
            existing_count=existing_count, skipped_count=existing_count, conflict_count=len(conflicts), total_persisted_for_scope=len(persisted),
            weeks_materialized=[MaterializedRunProspectWeekTotal(season_week=week, materialized_count=count) for week, count in sorted(week_totals.items())],
            country_totals=[MaterializedRunProspectCountryTotal(country_code=code, country_name=name, materialized_count=count) for (code, name), count in sorted(country_totals.items())],
            already_materialized=already,
            message=("Prospect cohort was already materialized." if already else "Prospect cohort materialized."),
        )

    def _build_records(self, preview) -> list[RunProspectRecord]:
        records: list[RunProspectRecord] = []
        for week in preview.weeks:
            for allocation in week.allocations:
                for local_sequence in range(1, allocation.allocated_count + 1):
                    prospect_id = deterministic_prospect_id(
                        run_id=preview.run_id, world_id=preview.world_id, season_start_year=preview.season_start_year,
                        season_week=week.season_week, country_code=allocation.country_code, local_sequence=local_sequence,
                        profile_version=PROFILE_VERSION, cohort_policy_version=COHORT_POLICY_VERSION,
                    )
                    seeds = {kind: _stable_seed(prospect_id, preview.run_id, preview.world_id, PROFILE_VERSION, kind) for kind in ("identity", "profile", "development", "potential", "trait")}
                    display_name = f"{allocation.country_code} Prospect {local_sequence:04d}"
                    records.append(RunProspectRecord(
                        prospect_id=prospect_id, run_id=preview.run_id, world_id=preview.world_id, season_start_year=preview.season_start_year,
                        season_label=preview.season, season_week=week.season_week, calendar_year=week.calendar_year, year_week=week.year_week,
                        birth_year=week.birth_year, birth_year_week=week.birth_year_week, age=15, country_code=allocation.country_code,
                        country_name=allocation.country_name, status=PROSPECT_STATUS, source_type=SOURCE_TYPE, cohort_policy_version=COHORT_POLICY_VERSION,
                        profile_version=PROFILE_VERSION, first_name=None, last_name=None, display_name=display_name, short_name=display_name,
                        identity_seed=seeds["identity"], profile_seed=seeds["profile"], development_seed=seeds["development"],
                        potential_seed=seeds["potential"], trait_seed=seeds["trait"],
                        profile_json={"schema_version": PROFILE_VERSION, "profile_version": PROFILE_VERSION, "generated_by": SOURCE_TYPE, "reserved_for_future_attributes": True},
                        development_json={"schema_version": PROFILE_VERSION, "profile_version": PROFILE_VERSION, "reserved_for_future_development": True},
                        potential_json={"schema_version": PROFILE_VERSION, "profile_version": PROFILE_VERSION, "reserved_for_future_potential": True},
                        trait_json={"schema_version": PROFILE_VERSION, "profile_version": PROFILE_VERSION, "reserved_for_future_traits": True},
                    ))
        return records


def _stable_seed(prospect_id: str, run_id: str, world_id: str, profile_version: str, kind: str) -> str:
    payload = "|".join([prospect_id, run_id, world_id, profile_version, kind])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
