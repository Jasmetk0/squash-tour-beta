"""Single-transaction Run prospect cohort reconciliation.

The reviewed deterministic cohort is an input. Conflict discovery, activated
identity validation, upsert, stale-source removal and committed counts must
all observe the same SQLite writer transaction. Never mutate Saved history or
a different Run, season, country scope or source policy.
"""
from __future__ import annotations

from sqlalchemy import func, select, text

from beta_engine.infrastructure.db.models import RunProspectModel
from beta_engine.infrastructure.db.repositories import (
    RunProspectRecord, SimulationPersistenceRepository, _to_json,
)


class RunProspectCohortConflictError(ValueError):
    def __init__(self, conflicts: list[str]) -> None:
        self.conflicts = conflicts
        super().__init__(f"Conflicting Run prospects: {', '.join(conflicts)}")


_JSON_FIELDS = ("profile_json", "development_json", "potential_json", "trait_json")
_FIELDS = (
    "world_id", "season_start_year", "season_label", "season_week",
    "calendar_year", "year_week", "birth_year", "birth_year_week",
    "age", "country_code", "country_name", "status", "source_type",
    "cohort_policy_version", "profile_version", "first_name", "last_name",
    "display_name", "short_name", "identity_seed", "profile_seed",
    "development_seed", "potential_seed", "trait_seed",
)


def _row_payload(record: RunProspectRecord) -> dict[str, object]:
    # Identical canonical JSON encoders and column fields to repository upsert.
    body = {field: getattr(record, field) for field in _FIELDS}
    body["country_code"] = record.country_code.upper()
    return body | {field: _to_json(getattr(record, field)) for field in _JSON_FIELDS}


def reconcile_run_prospect_cohort(
    repository: SimulationPersistenceRepository, *, run_id: str,
    season_start_year: int, expected: list[RunProspectRecord],
    scope_country_codes: set[str], source_type: str, profile_version: str,
    cohort_policy_version: str, overwrite: bool,
) -> tuple[int, int, int, int]:
    """Return created/existing/conflicting/persisted counts, or roll back all.

    SQLite BEGIN IMMEDIATE serializes writer decisions against both the
    activated lifecycle rows and this Run's prospect catalog.
    """
    if not expected or not scope_country_codes:
        raise ValueError("Prospect reconciliation requires a nonempty reviewed cohort")
    ids = [record.prospect_id for record in expected]
    if len(ids) != len(set(ids)) or any(
        item.run_id != run_id
        or item.season_start_year != season_start_year
        or item.country_code not in scope_country_codes
        or item.source_type != source_type
        or item.profile_version != profile_version
        or item.cohort_policy_version != cohort_policy_version
        for item in expected
    ):
        raise ValueError("Prospect cohort source or identity is inconsistent")

    with repository._session_factory.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        live = session.execute(
            select(RunProspectModel).where(
                RunProspectModel.run_id == run_id,
                RunProspectModel.season_start_year == season_start_year,
            )
        ).scalars().all()
        existing = {
            item.prospect_id: repository._to_run_prospect_record(item)
            for item in live
        }
        wanted = set(ids)
        foreign_year_ids = set(session.execute(
            select(RunProspectModel.prospect_id).where(
                RunProspectModel.run_id == run_id,
                RunProspectModel.prospect_id.in_(wanted),
                RunProspectModel.season_start_year != season_start_year,
            )
        ).scalars().all())
        if foreign_year_ids:
            raise RunProspectCohortConflictError(sorted(foreign_year_ids))

        stale_ids = {
            item.prospect_id for item in live
            if item.country_code in scope_country_codes
            and item.source_type == source_type
            and item.profile_version == profile_version
            and item.cohort_policy_version == cohort_policy_version
            and item.prospect_id not in wanted
        }
        conflicting_ids = {
            item.prospect_id for item in expected
            if item.prospect_id in existing
            and existing[item.prospect_id] != item
        } | stale_ids
        if conflicting_ids and not overwrite:
            raise RunProspectCohortConflictError(sorted(conflicting_ids))
        if conflicting_ids:
            activated = repository._activated_run_prospect_ids_in_session(
                session, run_id=run_id, prospect_ids=conflicting_ids,
            )
            if activated:
                raise RunProspectCohortConflictError(sorted(activated))

        existing_count = len(wanted & existing.keys())
        created_count = len(expected) - existing_count
        for record in expected:
            current = next(
                (row for row in live if row.prospect_id == record.prospect_id), None
            )
            if current is None:
                session.add(RunProspectModel(
                    run_id=run_id, prospect_id=record.prospect_id,
                    **_row_payload(record),
                ))
            elif overwrite and existing[record.prospect_id] != record:
                for field, value in _row_payload(record).items():
                    setattr(current, field, value)

        if overwrite and stale_ids:
            session.query(RunProspectModel).filter(
                RunProspectModel.run_id == run_id,
                RunProspectModel.prospect_id.in_(stale_ids),
            ).delete(synchronize_session=False)

        session.flush()
        persisted = session.scalar(
            select(func.count()).select_from(RunProspectModel).where(
                RunProspectModel.run_id == run_id,
                RunProspectModel.season_start_year == season_start_year,
                RunProspectModel.prospect_id.in_(wanted),
            )
        )
        if persisted != len(expected):
            raise ValueError("Atomic prospect cohort reconciliation is incomplete")
        return created_count, existing_count, len(conflicting_ids), int(persisted)
