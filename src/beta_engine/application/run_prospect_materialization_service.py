"""Materialize deterministic run-scoped 15-year-old prospect cohorts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from beta_engine.application.run_weekly_intake_cohort_preview_service import RunWeeklyIntakeCohortPreviewService
from beta_engine.domain.players.prospect_sporting_profile import (
    DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY,
    materialize_prospect_sporting_profile,
)
from beta_engine.domain.players.talent_models import TalentQualityBand
from beta_engine.domain.players.talent_quality_policy import (
    current_talent_quality_policy_snapshot,
    resolve_persisted_talent_quality,
    talent_quality_result_evidence,
)
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
class MaterializedRunProspectTalentCountrySummary:
    country_code: str
    country_name: str | None
    forecast_count: int
    materialized_count: int
    expected_band_counts: dict[str, float]
    generated_band_counts: dict[str, int]


@dataclass(frozen=True)
class MaterializedRunProspectTalentSummary:
    run_id: str
    season_start_year: int
    forecast_source: str
    forecast_fingerprint: str | None
    cohort_state: str
    forecast_total: int
    total_materialized: int
    quality_policy_id: str
    quality_policy_fingerprint: str
    quality_weights: dict[str, float]
    expected_band_counts: dict[str, float]
    generated_band_counts: dict[str, int]
    countries: list[MaterializedRunProspectTalentCountrySummary]


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
        expected_review_fingerprint: str | None = None,
    ) -> MaterializeRunProspectsResult:
        preview = self.preview_service.preview_season(
            run_id=run_id,
            base_annual_intake_target=base_annual_intake_target,
            season_growth_rate=season_growth_rate,
            country_code=country_code,
            region=region,
        )
        if expected_review_fingerprint is None:
            raise ValueError("expected_review_fingerprint is required; review the current cohort preview before confirming")
        if expected_review_fingerprint != preview.review_fingerprint:
            raise ValueError("Talent Intake preview is stale or belongs to a different Run/season/world/input scope; review again")
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
        if overwrite and conflicts:
            activated_conflicts = sorted(
                self.repository.list_activated_run_prospect_ids(
                    run_id=run_id,
                    prospect_ids=conflicts,
                )
            )
            if activated_conflicts:
                raise RunProspectMaterializationConflictError(activated_conflicts)

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

    def summarize_materialized_talent(
        self,
        *,
        run_id: str,
        season_start_year: int | None = None,
    ) -> MaterializedRunProspectTalentSummary:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        if run_info is None:
            raise KeyError(f"run_id {run_id} was not found")
        target_season = run_info.season if season_start_year is None else season_start_year
        records = self.repository.list_run_prospects(
            run_id=run_id,
            season_start_year=target_season,
            limit=None,
        )
        records = [record for record in records if record.source_type == SOURCE_TYPE]
        generated = {band.value: 0 for band in TalentQualityBand}
        country_rows: dict[tuple[str, str | None], list[tuple[RunProspectRecord, TalentQualityBand]]] = {}
        resolved_policy = None
        for record in records:
            band, snapshot, _ = resolve_persisted_talent_quality(
                potential_seed=record.potential_seed,
                potential_json=record.potential_json,
                cohort_policy_version=record.cohort_policy_version,
                profile_version=record.profile_version,
            )
            if resolved_policy is None:
                resolved_policy = snapshot
            elif resolved_policy.fingerprint != snapshot.fingerprint:
                raise ValueError("Materialized Talent Intake season contains multiple frozen quality policies; mixed-policy summary is not supported yet")
            generated[band.value] += 1
            country_rows.setdefault((record.country_code, record.country_name), []).append((record, band))

        snapshot = resolved_policy or current_talent_quality_policy_snapshot()
        weight_payload = dict(snapshot.normalized_weights)
        forecast = None
        if records:
            raw_forecasts = [record.profile_json.get("cohort_forecast") for record in records]
            stored = [item for item in raw_forecasts if isinstance(item, dict)]
            if stored:
                first = stored[0]
                if any(item != first for item in stored[1:]) or len(stored) != len(records):
                    raise ValueError("Materialized Talent Intake cohort has inconsistent stored forecast evidence")
                forecast = first

        forecast_source = "stored_pre_generation_v1" if forecast is not None else "legacy_conditional_materialized_count"
        forecast_fingerprint = str(forecast.get("forecast_fingerprint")) if forecast is not None else None
        forecast_total = int(forecast.get("total_weekly_target", len(records))) if forecast is not None else len(records)
        cohort_state = "complete" if len(records) == forecast_total else ("empty" if len(records) == 0 else "partial")

        forecast_countries: dict[str, dict[str, object]] = {}
        if forecast is not None:
            raw_countries = forecast.get("countries")
            if not isinstance(raw_countries, list):
                raise ValueError("Stored Talent Intake forecast countries are malformed")
            for row in raw_countries:
                if not isinstance(row, dict) or not isinstance(row.get("country_code"), str):
                    raise ValueError("Stored Talent Intake forecast country is malformed")
                forecast_countries[str(row["country_code"])] = row

        all_country_codes = sorted(
            set(forecast_countries) | {country_code for country_code, _ in country_rows}
        )
        countries: list[MaterializedRunProspectTalentCountrySummary] = []
        for country_code in all_country_codes:
            forecast_row = forecast_countries.get(country_code)
            country_name = (
                forecast_row.get("country_name") if forecast_row is not None
                else next((name for code, name in country_rows if code == country_code), None)
            )
            country_records = next(
                (rows for (code, _), rows in country_rows.items() if code == country_code),
                [],
            )
            country_generated = {band.value: 0 for band in TalentQualityBand}
            for _, band in country_records:
                country_generated[band.value] += 1
            forecast_count = int(forecast_row.get("forecast_count", len(country_records))) if forecast_row is not None else len(country_records)
            expected = (
                {str(k): float(v) for k, v in dict(forecast_row.get("expected_band_counts", {})).items()}
                if forecast_row is not None
                else {
                    band.value: round(forecast_count * weight_payload[band.value], 4)
                    for band in TalentQualityBand
                }
            )
            countries.append(
                MaterializedRunProspectTalentCountrySummary(
                    country_code=country_code,
                    country_name=country_name if isinstance(country_name, str) else None,
                    forecast_count=forecast_count,
                    materialized_count=len(country_records),
                    expected_band_counts=expected,
                    generated_band_counts=country_generated,
                )
            )

        expected_global = {
            band.value: round(forecast_total * weight_payload[band.value], 4)
            for band in TalentQualityBand
        }
        return MaterializedRunProspectTalentSummary(
            run_id=run_id,
            season_start_year=target_season,
            forecast_source=forecast_source,
            forecast_fingerprint=forecast_fingerprint,
            cohort_state=cohort_state,
            forecast_total=forecast_total,
            total_materialized=len(records),
            quality_policy_id=snapshot.policy_id,
            quality_policy_fingerprint=snapshot.fingerprint,
            quality_weights=weight_payload,
            expected_band_counts=expected_global,
            generated_band_counts=generated,
            countries=countries,
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
        quality_policy = current_talent_quality_policy_snapshot()
        cohort_forecast = self._cohort_forecast(preview, quality_policy)
        for week in preview.weeks:
            for allocation in week.allocations:
                for local_sequence in range(1, allocation.allocated_count + 1):
                    prospect_id = deterministic_prospect_id(
                        run_id=preview.run_id, world_id=preview.world_id, season_start_year=preview.season_start_year,
                        season_week=week.season_week, country_code=allocation.country_code, local_sequence=local_sequence,
                        profile_version=PROFILE_VERSION, cohort_policy_version=COHORT_POLICY_VERSION,
                    )
                    seeds = {kind: _stable_seed(prospect_id, preview.run_id, preview.world_id, PROFILE_VERSION, kind) for kind in ("identity", "profile", "development", "potential", "trait")}
                    sporting_profile = materialize_prospect_sporting_profile(
                        player_id=prospect_id,
                        profile_seed=seeds["profile"],
                        development_seed=seeds["development"],
                        potential_seed=seeds["potential"],
                    )
                    sporting_profile_payload = sporting_profile.model_dump(mode="json")
                    sporting_profile_fingerprint = sporting_profile.fingerprint
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
                            "canonical_sporting_profile": sporting_profile_payload,
                            "canonical_sporting_profile_fingerprint": sporting_profile_fingerprint,
                            "materialization_policy": policy,
                            "cohort_forecast": cohort_forecast,
                        },
                        development_json={
                            "schema_version": PROFILE_VERSION,
                            "profile_version": PROFILE_VERSION,
                            "development_timing": sporting_profile.development_timing,
                            "source_development_seed_digest": sporting_profile.source_development_seed_digest,
                            "sporting_profile_fingerprint": sporting_profile_fingerprint,
                        },
                        potential_json={
                            "schema_version": PROFILE_VERSION,
                            "profile_version": PROFILE_VERSION,
                            "talent_quality": talent_quality_result_evidence(seeds["potential"], quality_policy),
                            "potential_ovr": sporting_profile.potential_ovr,
                            "rolled_potential_ovr": sporting_profile.rolled_potential_ovr,
                            "effective_potential_floor_ovr": sporting_profile.effective_potential_floor_ovr,
                            "potential_floor_applied": sporting_profile.potential_floor_applied,
                            "potential_identity": sporting_profile.potential_identity,
                            "potential_provenance": sporting_profile.potential_provenance,
                            "source_potential_seed_digest": sporting_profile.source_potential_seed_digest,
                            "sporting_profile_fingerprint": sporting_profile_fingerprint,
                        },
                        trait_json={
                            "schema_version": PROFILE_VERSION,
                            "profile_version": PROFILE_VERSION,
                            "reserved_for_future_traits": True,
                        },
                    ))
        return records

    def _cohort_forecast(self, preview, quality_policy) -> dict[str, object]:
        weights = dict(quality_policy.normalized_weights)
        countries = [
            {
                "country_code": row.country_code,
                "country_name": row.country_name,
                "forecast_count": row.allocated_count,
                "expected_band_counts": {
                    band.value: round(row.allocated_count * weights[band.value], 4)
                    for band in TalentQualityBand
                },
            }
            for row in preview.country_totals
        ]
        payload = {
            "schema_version": "talent_intake_cohort_forecast.v1",
            "review_fingerprint": preview.review_fingerprint,
            "run_id": preview.run_id,
            "world_id": preview.world_id,
            "season": preview.season,
            "season_start_year": preview.season_start_year,
            "annual_target": preview.annual_target,
            "total_weekly_target": preview.total_weekly_target,
            "quality_policy_id": quality_policy.policy_id,
            "quality_policy_fingerprint": quality_policy.fingerprint,
            "quality_weights": weights,
            "countries": countries,
        }
        payload["forecast_fingerprint"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return payload

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
            "sporting_profile_policy_id": DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY.policy_id,
            "sporting_profile_policy_fingerprint": DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY.fingerprint,
        }
        fingerprint_payload = json.dumps(policy, sort_keys=True, separators=(",", ":"))
        return policy | {"policy_fingerprint": hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()[:32]}

    @staticmethod
    def _normalized_filter_value(value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


def _stable_seed(prospect_id: str, run_id: str, world_id: str, profile_version: str, kind: str) -> str:
    payload = "|".join([prospect_id, run_id, world_id, profile_version, kind])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
