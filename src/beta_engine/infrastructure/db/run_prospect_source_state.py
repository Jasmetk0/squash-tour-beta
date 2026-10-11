"""Saved Revision snapshot for Run-scoped prospect source metadata.

Run prospects are intentionally shared at Run scope rather than Branch scope.  A
historical Branch restore must therefore never delete or rewrite this table.  Saved
Revisions instead capture an immutable reference snapshot and restore validates that
the shared Run source still matches before any Branch mutation can occur.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.infrastructure.db.models import RunProspectModel

RUN_PROSPECT_SOURCE_COMPONENT_KEY = "run_prospect_source"
RUN_PROSPECT_SOURCE_SCHEMA = "run_prospect_source_snapshot.v1"


@dataclass(frozen=True)
class RunProspectSourceSnapshot:
    schema_version: str
    run_id: str
    records: tuple[dict[str, object], ...]
    fingerprint: str


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
    models = session.execute(
        select(RunProspectModel)
        .where(RunProspectModel.run_id == run_id)
        .order_by(RunProspectModel.prospect_id.asc())
    ).scalars().all()
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
            raise ValueError(f"Run prospect {model.prospect_id!r} profile must be an object")
        if not isinstance(record["development"], dict):
            raise ValueError(
                f"Run prospect {model.prospect_id!r} development must be an object"
            )
        if not isinstance(record["potential"], dict):
            raise ValueError(
                f"Run prospect {model.prospect_id!r} potential must be an object"
            )
        if not isinstance(record["traits"], dict):
            raise ValueError(f"Run prospect {model.prospect_id!r} traits must be an object")
        records.append(record)

    frozen = tuple(records)
    return RunProspectSourceSnapshot(
        schema_version=RUN_PROSPECT_SOURCE_SCHEMA,
        run_id=run_id,
        records=frozen,
        fingerprint=_fingerprint(run_id=run_id, records=frozen),
    )


def capture_saved_run_prospect_source(
    session: Session,
    payload: dict,
    *,
    run_id: str,
) -> RunProspectSourceSnapshot | None:
    content = payload.setdefault("content", {})
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")

    snapshot = capture_run_prospect_source_snapshot(session, run_id=run_id)
    if snapshot is None:
        content.pop(RUN_PROSPECT_SOURCE_COMPONENT_KEY, None)
        return None

    content[RUN_PROSPECT_SOURCE_COMPONENT_KEY] = {
        "schema_version": snapshot.schema_version,
        "run_id": snapshot.run_id,
        "records": list(snapshot.records),
        "fingerprint": snapshot.fingerprint,
    }
    return snapshot


def load_saved_run_prospect_source(
    payload: dict,
    *,
    run_id: str,
) -> RunProspectSourceSnapshot | None:
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    raw = content.get(RUN_PROSPECT_SOURCE_COMPONENT_KEY)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Run prospect source component must be an object")
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

    fingerprint = raw.get("fingerprint")
    expected = _fingerprint(run_id=run_id, records=records)
    if fingerprint != expected:
        raise ValueError("Run prospect source component fingerprint mismatch")
    return RunProspectSourceSnapshot(
        schema_version=RUN_PROSPECT_SOURCE_SCHEMA,
        run_id=run_id,
        records=records,
        fingerprint=expected,
    )


def validate_live_run_prospect_source_against_saved(
    session: Session,
    payload: dict,
    *,
    run_id: str,
) -> RunProspectSourceSnapshot | None:
    saved = load_saved_run_prospect_source(payload, run_id=run_id)
    live = capture_run_prospect_source_snapshot(session, run_id=run_id)
    if saved is None and live is None:
        return None
    if saved is None and live is not None:
        raise ValueError("Saved Revision does not capture the live Run prospect source")
    if saved is not None and live is None:
        raise ValueError("Saved Revision prospect source is missing from the live Run")
    assert saved is not None and live is not None
    if saved.fingerprint != live.fingerprint:
        raise ValueError(
            "Live Run prospect source differs from the Saved Revision snapshot"
        )
    return saved
