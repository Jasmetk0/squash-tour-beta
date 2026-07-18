"""Materialize deterministic run-scoped 15-year-old prospect cohorts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

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
        expected = self._build_records(
            preview,
            country_code=country_code,
            region=region,
        )
        if not expected:
            return MaterializeRunProspectsResult(
                run_id=preview.run_id, world_id=preview.world_id, season=preview.season, season_start_year=preview.season_start_year,
                annual_target=preview.annual_target, requested_prospect_count=0, created_count=0, existing_count=0, skipped_count=0,
                conflict_count=0, total_persisted_for_scope=0, weeks_materialized=[], country_totals=[], already_materialized=True,
                message="No prospects requested for this materialization scope.",
            )

        scope_country_codes = self._scope_country_codes(preview)
        existing_for_season = self.repository.list_run_prospects(
            run_id=run_id,
            season_start_year=preview.season_start_year,
            limit=None,
        )
        existing_by_id = {record.prospect_id: record for record in existing_for_season}
        expected_by_id = {record.prospect_id: record for record in expected}
        expected_ids = set(expected_by_id)
        existing_in_scope = [
            record
            for record in existing_for_season
            if record.source_type == SOURCE_TYPE
            and record.profile_version == PROFILE_VERSION
            and record.cohort_policy_version == COHORT_POLICY_VERSION
            and record.country_code in scope_country_codes
        ]
        payload_conflicts = [
            record.prospect_id
            for record in expected
            if record.prospect_id in existing_by_id and existing_by_id[record.prospect_id] != record
        ]
        stale_records = [record for record in existing_in_scope if record.prospect_id not in expected_ids]
        conflicts = sorted(set(payload_conflicts + [record.prospect_id for record in stale_records]))
        if conflicts and not overwrite:
            raise RunProspectMaterializationConflictError(conflicts)

        to_upsert = [record for record in expected if overwrite or record.prospect_id not in existing_by_id]
        self.repository.upsert_run_prospects(to_upsert)
        if overwrite:
            self.repository.delete_run_prospects_by_ids(
                run_id=run_id,
                prospect_ids=[record.prospect_id for record in stale_records],
            )
        existing_count = len(expected) - len([r for r in expected if r.prospect_id not in existing_by_id])
        created_count = len([r for r in expected if r.prospect_id not in existing_by_id])
        if overwrite:
            created_count = len([r for r in expected if r.prospect_id not in existing_by_id])
        persisted_expected_ids = expected_ids
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

    def _build_records(
        self,
        preview,
        *,
        country_code: str | None,
        region: str | None,
    ) -> list[RunProspectRecord]:
        records: list[RunProspectRecord] = []
        policy = self._materialization_policy(
            preview,
            country_code=country_code,
            region=region,
        )
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
                        profile_json={
                            "schema_version": PROFILE_VERSION,
                            "profile_version": PROFILE_VERSION,
                            "generated_by": SOURCE_TYPE,
                            "reserved_for_future_attributes": True,
                            "materialization_policy": policy,
                        },
                        development_json={"schema_version": PROFILE_VERSION, "profile_version": PROFILE_VERSION, "reserved_for_future_development": True},
                        potential_json={"schema_version": PROFILE_VERSION, "profile_version": PROFILE_VERSION, "reserved_for_future_potential": True},
                        trait_json={"schema_version": PROFILE_VERSION, "profile_version": PROFILE_VERSION, "reserved_for_future_traits": True},
                    ))
        return records

    @staticmethod
    def _scope_country_codes(preview) -> set[str]:
        return {
            allocation.country_code.upper()
            for week in preview.weeks
            for allocation in week.allocations
        }

    def _materialization_policy(
        self,
        preview,
        *,
        country_code: str | None,
        region: str | None,
    ) -> dict[str, object]:
        country_codes = sorted(self._scope_country_codes(preview))
        # The preview service normalizes filters before applying them.  Store the
        # corresponding canonical values so policy identity remains replayable.
        policy = {
            "base_annual_intake_target": preview.base_annual_intake_target,
            "season_growth_rate": preview.season_growth_rate,
            "country_code": self._normalized_filter_value(country_code),
            "region": self._normalized_filter_value(region),
            "filtered_country_codes": country_codes,
            "profile_version": PROFILE_VERSION,
            "cohort_policy_version": COHORT_POLICY_VERSION,
        }
        fingerprint_payload = json.dumps(policy, sort_keys=True, separators=(",", ":"))
        return policy | {"policy_fingerprint": hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()[:32]}

    @staticmethod
    def _normalized_filter_value(value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


def _stable_seed(prospect_id: str, run_id: str, world_id: str, profile_version: str, kind: str) -> str:
    payload = "|".join([prospect_id, run_id, world_id, profile_version, kind])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
