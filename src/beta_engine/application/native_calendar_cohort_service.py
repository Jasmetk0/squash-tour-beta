"""Deterministic, Run-clock-native 15-year-old cohort generator over Saved World truth.

No database mutations: this builds *actual* canonical 57-attribute RunProspect
records for future explicit confirmation. The original 61-week generator and
its seed/version remain unchanged. A preview is never sporting activation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from beta_engine.application.run_prospect_materialization_service import (
    PROFILE_VERSION, _stable_seed,
)
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.countries import Country
from beta_engine.domain.players.intake_volume_policy import IntakeVolumePolicy
from beta_engine.domain.players.prospect_sporting_profile import (
    DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY,
    materialize_prospect_sporting_profile,
)
from beta_engine.domain.players.talent_quality_policy import (
    current_talent_quality_policy_snapshot,
    talent_quality_result_evidence,
)
from beta_engine.domain.players.weekly_intake import WeeklyIntakePlanner
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.repositories import (
    RunProspectRecord, deterministic_prospect_id,
)

NATIVE_COHORT_POLICY = "native_calendar_15yo_cohort_v1"
NATIVE_COHORT_SOURCE = "native_calendar_15yo_cohort"
MAX_NATIVE_ANNUAL_TARGET = 2000


class NativeCalendarCohortRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal["native_calendar_cohort_request.v1"] = (
        "native_calendar_cohort_request.v1"
    )
    world_package_id: str = Field(min_length=1, max_length=128)
    season_index: int = Field(ge=0)
    base_annual_intake_target: int = Field(default=200, ge=1, le=MAX_NATIVE_ANNUAL_TARGET)
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


@dataclass(frozen=True)
class NativeCalendarCohort:
    records: tuple[RunProspectRecord, ...]
    season_index: int
    season_start_year: int
    annual_target: int
    week_counts: tuple[int, ...]
    country_counts: dict[str, int]
    content_fingerprint: str


def build_native_calendar_cohort(
    *, clock: RunCalendar, run_id: str, world_id: str,
    season_index: int, countries: list[Country],
    base_annual_intake_target: int = 200,
    country_content_fingerprint: str,
) -> NativeCalendarCohort:
    """Produce exact full-calendar W-week record profiles, without side effects.

    15th birthdays are derived from each Run's actual year/week position.
    Season index and W/O are committed seed inputs, never legacy 2000/61
    ordinals. Remainders conserve the exact weighted annual cohort.
    """
    if not isinstance(run_id, str) or not run_id or not world_id:
        raise ValueError("Cohort requires Run and World identities")
    clock.season_to_calendar(season_index, 1)
    if not countries or len({c.code for c in countries}) != len(countries):
        raise ValueError("Native cohort requires distinct authored World countries")
    if type(base_annual_intake_target) is not int or not 1 <= base_annual_intake_target <= MAX_NATIVE_ANNUAL_TARGET:
        raise ValueError("Native cohort base annual intake target is outside supported bounds")
    ordered = sorted(countries, key=lambda c: c.code)
    annual_position = clock.start_year + season_index
    policy = IntakeVolumePolicy()
    key = f"{NATIVE_COHORT_POLICY}|{run_id}|{world_id}|W{clock.weeks_per_year}|O{clock.season_start_year_week}|start{clock.start_year}|{season_index}"
    variation = policy._mapped_float(key + "|season-variation", 0.9, 1.1)
    annual_target = round(base_annual_intake_target * (1.015 ** season_index) * variation)
    if annual_target > MAX_NATIVE_ANNUAL_TARGET:
        raise ValueError("Derived native annual intake exceeds the reviewed limit")
    weights = [
        policy._mapped_float(f"{key}|week|{w}", 0.55, 1.55)
        for w in range(1, clock.weeks_per_year + 1)
    ]
    week_counts = tuple(policy._allocate_weighted(annual_target=annual_target, weights=weights))
    planner = WeeklyIntakePlanner()
    quality_policy = current_talent_quality_policy_snapshot()
    records: list[RunProspectRecord] = []
    country_counts = {c.code: 0 for c in ordered}
    names = {c.code: c.name for c in ordered}
    source_policy = {
        "schema_version": NATIVE_COHORT_POLICY,
        "run_calendar": clock.to_metadata(),
        "season_index": season_index,
        "base_annual_intake_target": base_annual_intake_target,
        "annual_target": annual_target,
        "world_country_content_fingerprint": country_content_fingerprint,
        "sporting_profile_policy_fingerprint": DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY.fingerprint,
        "quality_policy_fingerprint": quality_policy.fingerprint,
    }
    source_policy["fingerprint"] = canonical_hash(source_policy)
    for week, volume in enumerate(week_counts, start=1):
        position = clock.season_to_calendar(season_index, week)
        birth_year = position.calendar_year - 15
        allocations = planner._allocate_countries(
            countries=ordered, population_year=birth_year, target_intake_count=volume,
        )
        if sum(a.allocated_count for a in allocations) != volume:
            raise ValueError("Country allocation does not conserve native weekly cohort")
        for allocation in allocations:
            country_counts[allocation.country_code] += allocation.allocated_count
            for sequence in range(1, allocation.allocated_count + 1):
                prospect_id = deterministic_prospect_id(
                    run_id=run_id, world_id=world_id,
                    season_start_year=annual_position, season_week=week,
                    country_code=allocation.country_code, local_sequence=sequence,
                    profile_version=PROFILE_VERSION, cohort_policy_version=NATIVE_COHORT_POLICY,
                )
                seeds = {
                    kind: _stable_seed(prospect_id, run_id, world_id, PROFILE_VERSION, kind)
                    for kind in ("identity", "profile", "development", "potential", "trait")
                }
                sporting = materialize_prospect_sporting_profile(
                    player_id=prospect_id, profile_seed=seeds["profile"],
                    development_seed=seeds["development"], potential_seed=seeds["potential"],
                )
                fingerprint = sporting.fingerprint
                display = f"{allocation.country_code} Prospect {week:02d}-{sequence:04d}"
                records.append(RunProspectRecord(
                    prospect_id=prospect_id, run_id=run_id, world_id=world_id,
                    season_start_year=annual_position, season_label=clock.label(season_index),
                    season_week=week, calendar_year=position.calendar_year,
                    year_week=position.year_week, birth_year=birth_year,
                    birth_year_week=position.year_week, age=15,
                    country_code=allocation.country_code,
                    country_name=names[allocation.country_code], status="prospect",
                    source_type=NATIVE_COHORT_SOURCE,
                    cohort_policy_version=NATIVE_COHORT_POLICY, profile_version=PROFILE_VERSION,
                    first_name=None, last_name=None, display_name=display, short_name=display,
                    identity_seed=seeds["identity"], profile_seed=seeds["profile"],
                    development_seed=seeds["development"], potential_seed=seeds["potential"],
                    trait_seed=seeds["trait"],
                    profile_json={
                        "schema_version": PROFILE_VERSION,
                        "profile_version": PROFILE_VERSION,
                        "generated_by": NATIVE_COHORT_SOURCE,
                        "canonical_sporting_profile": sporting.model_dump(mode="json"),
                        "canonical_sporting_profile_fingerprint": fingerprint,
                        "materialization_policy": source_policy,
                    },
                    development_json={
                        "schema_version": PROFILE_VERSION,
                        "profile_version": PROFILE_VERSION,
                        "development_timing": sporting.development_timing,
                        "source_development_seed_digest": sporting.source_development_seed_digest,
                        "sporting_profile_fingerprint": fingerprint,
                    },
                    potential_json={
                        "schema_version": PROFILE_VERSION,
                        "profile_version": PROFILE_VERSION,
                        "talent_quality": talent_quality_result_evidence(seeds["potential"], quality_policy),
                        "potential_ovr": sporting.potential_ovr,
                        "rolled_potential_ovr": sporting.rolled_potential_ovr,
                        "effective_potential_floor_ovr": sporting.effective_potential_floor_ovr,
                        "potential_floor_applied": sporting.potential_floor_applied,
                        "potential_identity": sporting.potential_identity,
                        "potential_provenance": sporting.potential_provenance,
                        "source_potential_seed_digest": sporting.source_potential_seed_digest,
                        "sporting_profile_fingerprint": fingerprint,
                    },
                    trait_json={
                        "schema_version": PROFILE_VERSION,
                        "profile_version": PROFILE_VERSION,
                        "reserved_for_future_traits": True,
                    },
                ))
    if len(records) != annual_target or len({r.prospect_id for r in records}) != len(records):
        raise ValueError("Native calendar cohort has duplicate or incomplete identities")
    ordered_records = tuple(sorted(records, key=lambda r: r.prospect_id))
    return NativeCalendarCohort(
        records=ordered_records, season_index=season_index,
        season_start_year=annual_position, annual_target=annual_target,
        week_counts=week_counts, country_counts=country_counts,
        content_fingerprint=canonical_hash([asdict(row) for row in ordered_records]),
    )


@dataclass(slots=True)
class NativeCalendarCohortService:
    repository: object
    world_adapter: WorldPackageRunAdapter

    def preview(self, *, run_id: str, branch_id: str, request: NativeCalendarCohortRequest) -> dict:
        from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
        from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel, RunContainerModel
        from beta_engine.infrastructure.db.run_package_state import (
            get_run_package_state, load_saved_run_package_state,
        )
        import json

        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            clock = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
            clock.season_to_calendar(request.season_index, 1)
            branch = session.get(RunBranchModel, branch_id)
            run = session.get(RunContainerModel, run_id)
            if branch is None or branch.saved_head_revision_id is None:
                raise ValueError("Native cohort requires an immutable Saved Branch head")
            if run is None or run.read_only or branch.read_only or branch.status != "active":
                raise ValueError("Native cohort requires a writable Run and active Branch")
            if run.world_id is not None and run.world_id != request.world_package_id:
                raise ValueError("World Package differs from Run world identity")
            revision = session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
            if revision is None:
                raise ValueError("Saved Branch head is missing")
            saved = load_saved_run_package_state(
                json.loads(revision.payload_json),
                run_id=run_id, branch_id=branch_id,
            )
            live = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
            if saved is None or live is None or saved != live:
                raise ValueError("Native cohort requires the exact Saved World Package state")
            head = branch.saved_head_revision_id
        projection = self.world_adapter.project_countries(saved, package_id=request.world_package_id)
        countries = list(projection.countries)
        if request.country_code is not None:
            countries = [c for c in countries if c.code == request.country_code]
            if not countries:
                raise ValueError("Selected country is not in the Saved World Package")
        cohort = build_native_calendar_cohort(
            clock=clock, run_id=run_id, world_id=request.world_package_id,
            season_index=request.season_index, countries=countries,
            base_annual_intake_target=request.base_annual_intake_target,
            country_content_fingerprint=projection.content_fingerprint,
        )
        response = {
            "schema_version": "native_calendar_cohort_preview.v1",
            "run_id": run_id, "branch_id": branch_id,
            "saved_head_revision_id": head,
            "saved_run_package_fingerprint": saved.fingerprint,
            "world_country_content_fingerprint": projection.content_fingerprint,
            "run_calendar": clock.to_metadata(),
            "request": request.model_dump(mode="json"),
            "season_label": clock.label(request.season_index),
            "season_start_year": cohort.season_start_year,
            "annual_target": cohort.annual_target,
            "week_counts": list(cohort.week_counts),
            "country_counts": cohort.country_counts,
            "prepared_profile_count": len(cohort.records),
            "record_content_fingerprint": cohort.content_fingerprint,
            "first_prepared_prospects": [
                {
                    "prospect_id": row.prospect_id,
                    "country_code": row.country_code,
                    "season_week": row.season_week,
                    "birth_year": row.birth_year,
                    "birth_year_week": row.birth_year_week,
                    "profile_fingerprint": row.profile_json["canonical_sporting_profile_fingerprint"],
                }
                for row in cohort.records[:5]
            ],
            "preview_only": True,
            "materialization_supported": False,
            "native_tour_activation_supported": False,
        }
        return {**response, "review_fingerprint": canonical_hash(response)}
