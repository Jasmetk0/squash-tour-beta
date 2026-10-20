"""Saved Revision snapshot for Run-scoped prospect source metadata.

Run prospects are intentionally shared at Run scope rather than Branch scope.  A
historical Branch restore must therefore never delete or rewrite this table.  Saved
Revisions instead capture an immutable reference snapshot and restore validates that
the shared Run source still matches before any Branch mutation can occur.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from beta_engine.infrastructure.db.models import (
    PlayerLifecycleWeekStateModel,
    RunProspectModel,
)

RUN_PROSPECT_SOURCE_COMPONENT_KEY = "run_prospect_source"
RUN_PROSPECT_SOURCE_SCHEMA = "run_prospect_source_snapshot.v1"
RUN_PROSPECT_EPOCH_SCHEMA = "run_prospect_source_epochs.v2"


def native_birth_requires_source_epochs(session, *, run_id):
    """Run-shared source changes cannot invalidate another Branch's birth proof."""
    for row in session.scalars(
        select(PlayerLifecycleWeekStateModel).where(
            PlayerLifecycleWeekStateModel.run_id == run_id
        )
    ):
        if (
            json.loads(row.payload_json).get("schema_version")
            == "player_lifecycle_calendar_state.v4"
        ):
            from beta_engine.infrastructure.db.player_lifecycle_state import _load

            _load(row, run_id, row.branch_id, row.week_ordinal)
            return True
    return False


@dataclass(frozen=True)
class RunProspectSourceSnapshot:
    schema_version: str
    run_id: str
    records: tuple[dict[str, object], ...]
    fingerprint: str

    def for_week(self, ordinal: int) -> "RunProspectSourceSnapshot":
        if type(ordinal) is not int or ordinal < 0:
            raise ValueError("Invalid source-effective Run ordinal")
        return self


@dataclass(frozen=True)
class RunProspectSourceEpochs:
    """Immutable branch-Saved chain: Run rows remain shared, never branch-copied."""

    schema_version: str
    run_id: str
    epochs: tuple[tuple[int, RunProspectSourceSnapshot], ...]
    fingerprint: str

    @property
    def records(self) -> tuple[dict[str, object], ...]:
        return self.epochs[-1][1].records

    def for_week(self, ordinal: int) -> RunProspectSourceSnapshot:
        if type(ordinal) is not int or ordinal < 0:
            raise ValueError("Invalid source-effective Run ordinal")
        effective = self.epochs[0][1]
        for start, snapshot in self.epochs[1:]:
            if ordinal < start:
                break
            effective = snapshot
        return effective


RunProspectSource = RunProspectSourceSnapshot | RunProspectSourceEpochs


def _snapshot_component(snapshot: RunProspectSourceSnapshot) -> dict:
    return {
        "schema_version": snapshot.schema_version,
        "run_id": snapshot.run_id,
        "records": list(snapshot.records),
        "fingerprint": snapshot.fingerprint,
    }


def _epoch_component(epochs: tuple[tuple[int, RunProspectSourceSnapshot], ...], run_id: str) -> dict:
    content = {
        "schema_version": RUN_PROSPECT_EPOCH_SCHEMA,
        "run_id": run_id,
        "epochs": [
            {"effective_from_ordinal": ordinal, "source": _snapshot_component(snapshot)}
            for ordinal, snapshot in epochs
        ],
    }
    return {**content, "fingerprint": hashlib.sha256(
        _canonical_json(content).encode("utf-8")
    ).hexdigest()}


def _rows_are_immutable_prefix(previous: RunProspectSourceSnapshot, current: RunProspectSourceSnapshot) -> bool:
    earlier = {r["prospect_id"]: r for r in previous.records}
    later = {r["prospect_id"]: r for r in current.records}
    return all(later.get(identity) == row for identity, row in earlier.items())


def _added_records(previous: RunProspectSourceSnapshot, current: RunProspectSourceSnapshot) -> tuple[dict, ...]:
    if not _rows_are_immutable_prefix(previous, current):
        raise ValueError("Previously Saved Run prospects cannot be edited or deleted")
    previous_ids = {row["prospect_id"] for row in previous.records}
    return tuple(row for row in current.records if row["prospect_id"] not in previous_ids)


def _effective_birth_ordinal(row: dict, clock) -> int:
    birth_year, birth_week = row.get("birth_year"), row.get("birth_year_week")
    if type(birth_year) is not int or type(birth_week) is not int:
        raise ValueError("Native prospect has invalid birthday")
    position = clock.calendar_to_season(birth_year + 15, birth_week)
    if position is None:
        raise ValueError("New native prospect birth falls outside Saved Run calendar")
    if (
        row.get("season_start_year") != clock.start_year + position.season_index
        or row.get("season_week") != position.season_week
        or row.get("calendar_year") != position.calendar_year
        or row.get("year_week") != position.year_week
        or row.get("age") != 15
    ):
        raise ValueError("New prospect source disagrees with Saved Run calendar")
    return position.season_index * clock.weeks_per_year + position.season_week - 1


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(*, run_id: str, records: tuple[dict[str, object], ...]) -> str:
    payload = {
        "schema_version": RUN_PROSPECT_SOURCE_SCHEMA,
        "run_id": run_id,
        "records": records,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _record_payload(model: RunProspectModel) -> dict[str, object]:
    return {
        "prospect_id": model.prospect_id,
        "world_id": model.world_id,
        "season_start_year": model.season_start_year,
        "season_label": model.season_label,
        "season_week": model.season_week,
        "calendar_year": model.calendar_year,
        "year_week": model.year_week,
        "birth_year": model.birth_year,
        "birth_year_week": model.birth_year_week,
        "age": model.age,
        "country_code": model.country_code,
        "country_name": model.country_name,
        "status": model.status,
        "source_type": model.source_type,
        "cohort_policy_version": model.cohort_policy_version,
        "profile_version": model.profile_version,
        "first_name": model.first_name,
        "last_name": model.last_name,
        "display_name": model.display_name,
        "short_name": model.short_name,
        "identity_seed": model.identity_seed,
        "profile_seed": model.profile_seed,
        "development_seed": model.development_seed,
        "potential_seed": model.potential_seed,
        "trait_seed": model.trait_seed,
        "profile": json.loads(model.profile_json),
        "development": json.loads(model.development_json),
        "potential": json.loads(model.potential_json),
        "traits": json.loads(model.trait_json),
    }


def capture_run_prospect_source_snapshot(
    session: Session,
    *,
    run_id: str,
) -> RunProspectSourceSnapshot | None:
    models = (
        session.execute(
            select(RunProspectModel)
            .where(RunProspectModel.run_id == run_id)
            .order_by(RunProspectModel.prospect_id.asc())
        )
        .scalars()
        .all()
    )
    if not models:
        return None

    records: list[dict[str, object]] = []
    for model in models:
        try:
            record = _record_payload(model)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Run prospect {model.prospect_id!r} contains malformed persisted JSON"
            ) from exc
        if not isinstance(record["profile"], dict):
            raise ValueError(
                f"Run prospect {model.prospect_id!r} profile must be an object"
            )
        if not isinstance(record["development"], dict):
            raise ValueError(
                f"Run prospect {model.prospect_id!r} development must be an object"
            )
        if not isinstance(record["potential"], dict):
            raise ValueError(
                f"Run prospect {model.prospect_id!r} potential must be an object"
            )
        if not isinstance(record["traits"], dict):
            raise ValueError(
                f"Run prospect {model.prospect_id!r} traits must be an object"
            )
        records.append(record)

    frozen = tuple(records)
    return RunProspectSourceSnapshot(
        schema_version=RUN_PROSPECT_SOURCE_SCHEMA,
        run_id=run_id,
        records=frozen,
        fingerprint=_fingerprint(run_id=run_id, records=frozen),
    )


def capture_saved_run_prospect_source(
    session: Session, payload: dict, *, run_id: str,
    branch_id: str | None = None, allow_append: bool = False,
) -> RunProspectSource | None:
    """An ordinary Save/restore preserves its exact Signed source binding.

    Only the explicit reviewed prospect-source Save may append an epoch. No
    historical Saved bytes or Run-shared prospect rows are rewritten.
    """
    content = payload.setdefault("content", {})
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    old = load_saved_run_prospect_source(payload, run_id=run_id)
    if not allow_append:
        return old
    live = capture_run_prospect_source_snapshot(session, run_id=run_id)
    if live is None:
        raise ValueError("Cannot publish an empty Run prospect source")
    if old is None:
        content[RUN_PROSPECT_SOURCE_COMPONENT_KEY] = _snapshot_component(live)
        return live
    earlier = old.epochs[-1][1] if isinstance(old, RunProspectSourceEpochs) else old
    additions = _added_records(earlier, live)
    if not additions:
        raise ValueError("Run prospect source has no new immutable records")
    if branch_id is None:
        raise ValueError("Source epoch Save requires an explicit Branch")
    from beta_engine.domain.calendar.run_calendar import RunCalendar

    clock = RunCalendar.from_metadata(payload["run"]["run_calendar"])
    current = session.scalar(
        select(func.max(PlayerLifecycleWeekStateModel.week_ordinal)).where(
            PlayerLifecycleWeekStateModel.run_id == run_id,
            PlayerLifecycleWeekStateModel.branch_id == branch_id,
        )
    )
    activation = (current if current is not None else 0) + 1
    # A shared Run may have multiple branches at different weeks. A new source
    # must not create a birthday in ANY already completed Run week.
    furthest = session.scalar(
        select(func.max(PlayerLifecycleWeekStateModel.week_ordinal)).where(
            PlayerLifecycleWeekStateModel.run_id == run_id
        )
    )
    furthest = furthest if furthest is not None else 0
    for row in additions:
        birth = _effective_birth_ordinal(row, clock)
        if birth < activation or birth <= furthest:
            raise ValueError("New Run prospect would retroactively admit a player")
    if isinstance(old, RunProspectSourceEpochs):
        if activation <= old.epochs[-1][0]:
            raise ValueError("New source epoch does not advance historical Run time")
        epochs = (*old.epochs, (activation, live))
    else:
        epochs = ((0, old), (activation, live))
    component = _epoch_component(epochs, run_id)
    content[RUN_PROSPECT_SOURCE_COMPONENT_KEY] = component
    return RunProspectSourceEpochs(
        schema_version=RUN_PROSPECT_EPOCH_SCHEMA, run_id=run_id,
        epochs=epochs, fingerprint=component["fingerprint"],
    )


def _parse_snapshot(raw: dict, *, run_id: str) -> RunProspectSourceSnapshot:
    if set(raw) != {"schema_version", "run_id", "records", "fingerprint"}:
        raise ValueError("Run prospect source component contains unknown fields")
    if raw.get("schema_version") != RUN_PROSPECT_SOURCE_SCHEMA:
        raise ValueError("Run prospect source component schema is unsupported")
    if raw.get("run_id") != run_id:
        raise ValueError("Run prospect source component Run identity mismatch")
    raw_records = raw.get("records")
    if not isinstance(raw_records, list) or any(
        not isinstance(item, dict) for item in raw_records
    ):
        raise ValueError("Run prospect source records must be an object list")
    records = tuple(dict(item) for item in raw_records)
    ids = [item.get("prospect_id") for item in records]
    if any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("Run prospect source contains an invalid prospect identity")
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("Run prospect source identities are not unique and canonical")
    expected = _fingerprint(run_id=run_id, records=records)
    if raw.get("fingerprint") != expected:
        raise ValueError("Run prospect source component fingerprint mismatch")
    return RunProspectSourceSnapshot(
        schema_version=RUN_PROSPECT_SOURCE_SCHEMA, run_id=run_id,
        records=records, fingerprint=expected,
    )


def load_saved_run_prospect_source(
    payload: dict, *, run_id: str,
) -> RunProspectSource | None:
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    raw = content.get(RUN_PROSPECT_SOURCE_COMPONENT_KEY)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Run prospect source component must be an object")
    if raw.get("schema_version") == RUN_PROSPECT_SOURCE_SCHEMA:
        return _parse_snapshot(raw, run_id=run_id)
    if raw.get("schema_version") != RUN_PROSPECT_EPOCH_SCHEMA:
        raise ValueError("Run prospect source component schema is unsupported")
    if set(raw) != {"schema_version", "run_id", "epochs", "fingerprint"} or raw["run_id"] != run_id:
        raise ValueError("Source epochs contain unknown fields or a foreign Run")
    entries = raw["epochs"]
    if not isinstance(entries, list) or len(entries) < 2:
        raise ValueError("Source epochs require an original and a later source")
    from beta_engine.domain.calendar.run_calendar import RunCalendar

    clock = RunCalendar.from_metadata(payload["run"]["run_calendar"])
    epochs = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"effective_from_ordinal", "source"}:
            raise ValueError("Invalid Signed prospect epoch entry")
        ordinal = entry["effective_from_ordinal"]
        if type(ordinal) is not int or ordinal < 0 or (epochs and ordinal <= epochs[-1][0]):
            raise ValueError("Prospect source epochs are not strictly chronological")
        if not epochs and ordinal != 0:
            raise ValueError("Original prospect source epoch must begin at zero")
        if not isinstance(entry["source"], dict):
            raise ValueError("Prospect epoch source must be immutable snapshot data")
        snapshot = _parse_snapshot(entry["source"], run_id=run_id)
        if epochs:
            additions = _added_records(epochs[-1][1], snapshot)
            if not additions or any(
                _effective_birth_ordinal(row, clock) < ordinal for row in additions
            ):
                raise ValueError("Prospect epoch changes historical players or completed weeks")
        epochs.append((ordinal, snapshot))
    expected = _epoch_component(tuple(epochs), run_id)["fingerprint"]
    if raw["fingerprint"] != expected:
        raise ValueError("Run prospect epoch chain fingerprint mismatch")
    return RunProspectSourceEpochs(
        schema_version=RUN_PROSPECT_EPOCH_SCHEMA, run_id=run_id,
        epochs=tuple(epochs), fingerprint=expected,
    )


def validate_live_run_prospect_source_against_saved(
    session: Session, payload: dict, *, run_id: str,
) -> RunProspectSource | None:
    saved = load_saved_run_prospect_source(payload, run_id=run_id)
    live = capture_run_prospect_source_snapshot(session, run_id=run_id)
    if saved is None and live is None:
        return None
    if saved is None:
        raise ValueError("Saved Revision does not capture the live Run prospect source")
    if live is None:
        raise ValueError("Saved Revision prospect source is missing from the live Run")
    signed = saved.epochs[-1][1] if isinstance(saved, RunProspectSourceEpochs) else saved
    if not _rows_are_immutable_prefix(signed, live):
        raise ValueError("Live Run prospect source differs from historically Signed records")
    # New live records belong to the shared Run, not implicitly to this Branch.
    # A Branch selects them only through an explicit, separately Saved epoch.
    return saved
