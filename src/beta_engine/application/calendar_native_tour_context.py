"""Authenticate the whole live native Working owner, without creating a Save."""

import json

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    COMPONENT_KEY as SPORTING_KEY,
)
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    saved_checkpoint,
)
from beta_engine.infrastructure.db.calendar_tour import (
    COMPONENT_KEY as TOUR_KEY,
)
from beta_engine.infrastructure.db.calendar_tour import (
    saved_tour,
)
from beta_engine.infrastructure.db.player_health_state import (
    PLAYER_HEALTH_COMPONENT_KEY,
    _parse_health_json,
    capture_saved_health,
    load_saved_health,
)
from beta_engine.infrastructure.db.player_lifecycle_state import capture_saved_lifecycle
from beta_engine.infrastructure.db.run_prospect_source_state import (
    validate_live_run_prospect_source_against_saved,
)


def _verified_health_head(payload):
    """Copy the current value only AFTER this entire payload passed replay.

    This is not a verifier: callers must first authenticate the full Saved owner
    or finish the independent complete live-history proof below. Strict parsing
    creates a fresh isolated head without replaying that same history again.
    """
    return _parse_health_json(
        json.dumps(payload['content'][PLAYER_HEALTH_COMPONENT_KEY]['states'][-1])
    )


def native_working_context(
    session, *, revision, checkpoint, saved, state, signed, evidence, repository=None,
    _verified_payload_out=None,
):
    if state is None:
        raise ValueError("Native sporting owner lacks its coupled Tour authority")
    run_id, branch_id = checkpoint.run_id, checkpoint.branch_id
    payload = {
        **revision.saved_revision.payload,
        "content": dict(revision.saved_revision.payload["content"]),
    }

    def verified_head():
        # Export only owned values AFTER a complete proof succeeds below.
        # This carrier never grants physical/replay authority to another call.
        if _verified_payload_out is not None:
            _verified_payload_out["payload"] = payload
        return _verified_health_head(payload)
    validate_live_run_prospect_source_against_saved(session, payload, run_id=run_id)
    same_checkpoint, same_tour = checkpoint == saved, state == signed
    # The caller independently authenticated the Saved payload and checked the
    # actual live row content against these models. Preserve the exact original
    # component when equal; serializing thousands of unchanged player attributes
    # and all previous rally logs again adds no evidence. Changed components
    # still enter the complete live replay and actual-value proof below.
    if not same_checkpoint:
        body = checkpoint.model_dump(mode="json")
        payload["content"][SPORTING_KEY] = {
            "state": body,
            "fingerprint": canonical_hash(body),
        }
    if not same_tour:
        body = state.model_dump(mode="json")
        payload["content"][TOUR_KEY] = {
            "state": body,
            "fingerprint": canonical_hash(body),
        }
    if checkpoint.schema_version == 'calendar_sporting_checkpoint.v13':
        from beta_engine.infrastructure.db.tournament_application_submissions import capture_saved_application_submissions
        # The complete candidate body must include the same actual production
        # Entry authority captured by manual Save, not its earlier Saved copy.
        capture_saved_application_submissions(session, payload, run_id=run_id, branch_id=branch_id)
    capture_saved_lifecycle(session, payload, run_id=run_id, branch_id=branch_id)
    capture_saved_health(session, payload, run_id=run_id, branch_id=branch_id)
    # The caller authenticated this immutable Saved HEAD in this transaction.
    # Reuse it only if EVERY captured live component is still exactly equal.
    # Different live bytes always get the independent full replay below.
    if (
        same_checkpoint
        and same_tour
        and payload == revision.saved_revision.payload
    ):
        return verified_head()
    # The caller just authenticated the Saved lineage against physical rows.
    # Reuse only a completed proof of these exact captured live bytes in this
    # repository; this is never a source-hash-only authorization shortcut.
    cache = None
    signature = None
    if repository is not None and checkpoint.schema_version == "calendar_sporting_checkpoint.v13":
        signature = (revision.saved_head_revision_id, canonical_hash(payload))
        with repository._revision_validation_lock:
            cache = getattr(repository, "_global_working_proofs", None)
            if cache is None:
                cache = repository._global_working_proofs = {}
            verified_before = signature in cache
        if verified_before:
            # The exact FULL actual payload, including every Health/lifecycle
            # state, already completed independent replay. The fresh Saved
            # physical/source gate above still runs on every request.
            return verified_head()
    verified = saved_checkpoint(
        payload,
        evidence,
        run_id=run_id,
        branch_id=branch_id,
        _verified_saved_prefix=saved,
        _verified_global_prefix=(saved, signed, revision.saved_revision.payload),
        _predecoded_checkpoint=checkpoint if checkpoint.schema_version == 'calendar_sporting_checkpoint.v13' else None,
    )
    if (
        verified != checkpoint
        or saved_tour(
            payload,
            run_id=run_id,
            branch_id=branch_id,
            checkpoint=verified,
            **({"_verified_competition":verified} if verified is not None and verified.schema_version in {"calendar_sporting_checkpoint.v12", "calendar_sporting_checkpoint.v13"} else {}),
        )
        != state
    ):
        raise ValueError(
            "Live native owner differs from its complete component history"
        )
    if cache is not None:
        with repository._revision_validation_lock:
            cache[signature] = True
            while len(cache) > 8:
                cache.pop(next(iter(cache)))
    if checkpoint.schema_version == 'calendar_sporting_checkpoint.v13':
        # saved_checkpoint just independently verified all actual Health and
        # lifecycle histories plus the coupled checkpoint/Tour successor.
        return verified_head()
    return load_saved_health(payload, run_id=run_id, branch_id=branch_id)[-1]
