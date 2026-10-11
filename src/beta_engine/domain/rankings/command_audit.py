"""Declared Admin provenance and hash-bound canonical preparation requests."""

import hashlib
import json

from pydantic import Field, field_validator
from beta_engine.domain.rankings.official import FrozenInput


class RankingCommandAudit(FrozenInput):
    # A declared label, not an authenticated account or permission grant.
    actor_label: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("actor_label", "reason")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Audit fields must not be blank")
        return value


def verify_request_payload(payload: str | None, *, request_fingerprint: str,
                           command_id: str, snapshot=None):
    if payload is None:
        return None
    if hashlib.sha256(payload.encode()).hexdigest() != request_fingerprint:
        raise ValueError("Ranking request payload fingerprint mismatch")
    data = json.loads(payload)
    if not isinstance(data, dict) or data.get("command_id") != command_id:
        raise ValueError("Ranking request payload identity mismatch")
    context = data.get("context", data)
    if not isinstance(context, dict):
        raise ValueError("Ranking request context is invalid")
    if snapshot is not None and (
        context.get("run_id"), context.get("branch_id"), context.get("target_week")
    ) != (snapshot.run_id, snapshot.branch_id, snapshot.week.model_dump(mode="json")):
        raise ValueError("Ranking request payload scope or week mismatch")
    if data.get("audit") is not None:
        return RankingCommandAudit.model_validate(data["audit"])
    return None
