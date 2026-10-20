"""Authenticate the whole live native Working owner, without creating a Save."""

import json

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


def native_working_context(
    session, *, revision, checkpoint, saved, state, signed, evidence
):
    if state is None:
        raise ValueError("Native sporting owner lacks its coupled Tour authority")
    run_id, branch_id = checkpoint.run_id, checkpoint.branch_id
    payload = {
        **revision.saved_revision.payload,
        "content": dict(revision.saved_revision.payload["content"]),
    }
    validate_live_run_prospect_source_against_saved(session, payload, run_id=run_id)
    payload["content"][SPORTING_KEY] = {
        "state": checkpoint.model_dump(mode="json"),
        "fingerprint": checkpoint.fingerprint,
    }
    payload["content"][TOUR_KEY] = {
        "state": state.model_dump(mode="json"),
        "fingerprint": state.fingerprint,
    }
    capture_saved_lifecycle(session, payload, run_id=run_id, branch_id=branch_id)
    capture_saved_health(session, payload, run_id=run_id, branch_id=branch_id)
    # The caller authenticated this immutable Saved HEAD in this transaction.
    # Reuse it only if EVERY captured live component is still exactly equal.
    # Different live bytes always get the independent full replay below.
    if (
        checkpoint == saved
        and state == signed
        and payload == revision.saved_revision.payload
    ):
        return _parse_health_json(
            json.dumps(payload["content"][PLAYER_HEALTH_COMPONENT_KEY]["states"][-1])
        )
    verified = saved_checkpoint(
        payload,
        evidence,
        run_id=run_id,
        branch_id=branch_id,
        _verified_saved_prefix=saved,
    )
    if (
        verified != checkpoint
        or saved_tour(
            payload,
            run_id=run_id,
            branch_id=branch_id,
            checkpoint=verified,
            **({"_verified_competition":verified} if verified is not None and verified.schema_version == "calendar_sporting_checkpoint.v12" else {}),
        )
        != state
    ):
        raise ValueError(
            "Live native owner differs from its complete component history"
        )
    return load_saved_health(payload, run_id=run_id, branch_id=branch_id)[-1]
