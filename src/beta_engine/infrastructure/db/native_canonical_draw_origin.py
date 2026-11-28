"""Physical Saved source authentication, separate from mathematical slot replay."""

import json

from beta_engine.application.saved_fax_knockout_feeders import read_saved_fax_draw
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_revisions import (
    CONTENT_HASH_ALGORITHM,
    saved_revision_content_hash,
)
from beta_engine.domain.tournaments.canonical_knockout_feeders import (
    freeze_knockout_feeder_plan,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel


def verify_canonical_draw_origins(session, state, reachable):
    decoded = {}
    for authority in state.editions:
        binding = authority.canonical_binding
        if binding is None:
            continue
        row = session.get(BranchSavedRevisionModel, binding.saved_revision_id)
        if (
            binding.saved_revision_id not in reachable
            or row is None
            or (row.run_id, row.branch_id, row.content_hash_algorithm, row.content_hash)
            != (
                state.run_id,
                state.branch_id,
                CONTENT_HASH_ALGORITHM,
                binding.saved_content_hash,
            )
        ):
            raise ValueError(
                "Canonical Draw Saved origin is missing, foreign or unreachable"
            )
        if row.revision_id not in decoded:
            payload = json.loads(row.payload_json)
            actual = saved_revision_content_hash(
                revision_id=row.revision_id,
                run_id=row.run_id,
                branch_id=row.branch_id,
                sequence=row.sequence,
                parent_revision_id=row.parent_revision_id,
                kind=row.kind,
                payload_schema_version=row.payload_schema_version,
                payload=payload,
                change_summary=json.loads(row.change_summary_json),
            )
            if actual != row.content_hash:
                raise ValueError(
                    "Canonical Draw Saved origin content hash differs from actual bytes"
                )
            decoded[row.revision_id] = payload
        payload = decoded[row.revision_id]
        source = read_saved_fax_draw(
            payload,
            run_id=state.run_id,
            branch_id=state.branch_id,
            season=str(binding.source_event.season),
            event_id=authority.edition.edition_id,
        )
        plan = freeze_knockout_feeder_plan(
            source=source,
            source_saved_revision_id=row.revision_id,
            source_saved_content_hash=row.content_hash,
            calendar=RunCalendar.from_metadata(payload["run"]["run_calendar"]),
        )
        if plan != binding.plan(authority.draw):
            raise ValueError(
                "Canonical Draw differs from its physical authenticated Saved source"
            )


def verify_scheduled_profile_origins(session, state, reachable):
    """Authenticate each v5 Edition's copied profile against its physical Saved bytes."""
    from beta_engine.application.atp_knockout_schedule_preview import (
        ATPKnockoutSchedulePreviewRequest,
        validate_saved_atp_knockout_schedule,
    )
    from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state

    decoded = {}
    for authority in state.editions:
        binding = getattr(authority, "scheduled_binding", None)
        if binding is None:
            continue
        row = session.get(BranchSavedRevisionModel, binding.source_saved_revision_id)
        if (
            binding.source_saved_revision_id not in reachable
            or row is None
            or (row.run_id, row.branch_id, row.content_hash_algorithm, row.content_hash)
            != (state.run_id, state.branch_id, CONTENT_HASH_ALGORITHM, binding.source_saved_content_hash)
        ):
            raise ValueError("Scheduled profile Saved origin is missing, foreign or unreachable")
        if row.revision_id not in decoded:
            payload = json.loads(row.payload_json)
            actual = saved_revision_content_hash(
                revision_id=row.revision_id,
                run_id=row.run_id,
                branch_id=row.branch_id,
                sequence=row.sequence,
                parent_revision_id=row.parent_revision_id,
                kind=row.kind,
                payload_schema_version=row.payload_schema_version,
                payload=payload,
                change_summary=json.loads(row.change_summary_json),
            )
            if actual != row.content_hash:
                raise ValueError("Scheduled profile Saved origin content hash differs from actual bytes")
            decoded[row.revision_id] = payload
        payload = decoded[row.revision_id]
        packages = load_saved_run_package_state(payload, run_id=state.run_id, branch_id=state.branch_id)
        if packages is None:
            raise ValueError("Scheduled profile Saved origin lacks its ATP Package")
        profile, fingerprint, _source, _geometry = validate_saved_atp_knockout_schedule(
            calendar=RunCalendar.from_metadata(payload["run"]["run_calendar"]),
            state=packages,
            occurrence_id=authority.edition.edition_id,
            request=ATPKnockoutSchedulePreviewRequest(
                expected_saved_head=row.revision_id,
                expected_profile_fingerprint=binding.source_profile_fingerprint,
                schedule=binding.schedule,
            ),
        )
        if profile != binding.profile or fingerprint != binding.source_profile_fingerprint:
            raise ValueError("Scheduled Edition differs from its physical authenticated Saved profile")
