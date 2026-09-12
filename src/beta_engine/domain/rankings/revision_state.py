"""Self-contained ranking preparation state for future Saved Revision content."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator, model_serializer
from beta_engine.domain.rankings.command_audit import verify_request_payload
from beta_engine.domain.rankings.zero_history import RankingZeroVersion, validate_zero_successor, resolve_zero_versions

from beta_engine.domain.rankings.official import FrozenInput, OfficialRankingSnapshot
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.result_history import RankingResultVersion, validate_result_successor


class RankingRevisionReceipt(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_payload_json: str | None = None

    @model_serializer(mode="wrap")
    def serialize_receipt(self, handler):
        data = handler(self)
        if self.request_payload_json is None:
            data.pop("request_payload_json", None)
        return data


class RankingRevisionEntry(FrozenInput):
    snapshot: OfficialRankingSnapshot
    inputs: RankingInputManifest
    receipts: tuple[RankingRevisionReceipt, ...] = Field(min_length=1)


class RankingRevisionState(FrozenInput):
    schema_version: Literal["ranking_revision_state.v1"] = "ranking_revision_state.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    entries: tuple[RankingRevisionEntry, ...]
    sources: tuple[RankingResultVersion, ...]
    zero_sources: tuple[RankingZeroVersion, ...] = ()

    @model_serializer(mode="wrap")
    def serialize_state(self, handler):
        data = handler(self)
        if not self.zero_sources:
            data.pop("zero_sources", None)
        return data

    @model_validator(mode="after")
    def validate_complete_state(self):
        source_keys = [(v.result.edition_id, v.result.player_id, v.effective_week.ordinal) for v in self.sources]
        if source_keys != sorted(set(source_keys)):
            raise ValueError("Ranking revision source order or uniqueness is invalid")
        latest = {}
        for version in self.sources:
            if (version.run_id, version.branch_id) != (self.run_id, self.branch_id):
                raise ValueError("Ranking revision source scope mismatch")
            key = (version.result.edition_id, version.result.player_id)
            if key in latest:
                validate_result_successor(latest[key], version)
            elif version.previous_fingerprint is not None:
                raise ValueError("Ranking revision source predecessor is missing")
            latest[key] = version
        zero_keys = [(v.zero.zero_id, v.effective_week.ordinal) for v in self.zero_sources]
        if zero_keys != sorted(set(zero_keys)):
            raise ValueError("Ranking zero source order or uniqueness is invalid")
        latest_zeros = {}
        for version in self.zero_sources:
            if (version.zero.run_id, version.zero.branch_id) != (self.run_id, self.branch_id):
                raise ValueError("Ranking zero source scope mismatch")
            previous_zero = latest_zeros.get(version.zero.zero_id)
            if previous_zero is not None:
                validate_zero_successor(previous_zero, version)
            elif version.previous_fingerprint is not None:
                raise ValueError("Ranking zero source predecessor is missing")
            latest_zeros[version.zero.zero_id] = version
        previous = None
        command_ids = set()
        for entry in self.entries:
            snapshot = entry.snapshot
            if (snapshot.run_id, snapshot.branch_id) != (self.run_id, self.branch_id):
                raise ValueError("Ranking revision candidate scope mismatch")
            if previous is None and snapshot.week.ordinal != 0:
                raise ValueError("Ranking revision requires complete history from Week 1")
            entry.inputs.verify(snapshot, previous)
            if entry.inputs.zeros_from_history and entry.inputs.disciplinary_zeros != resolve_zero_versions(self.zero_sources, snapshot.week):
                raise ValueError("Ranking zero history differs from frozen inputs")
            resolved = {}
            for version in self.sources:
                if version.effective_week.ordinal <= snapshot.week.ordinal:
                    resolved[(version.result.edition_id, version.result.player_id)] = version.result
            if resolved != {(r.edition_id, r.player_id): r for r in entry.inputs.results}:
                raise ValueError("Ranking revision sources differ from frozen inputs")
            for receipt in entry.receipts:
                if entry.inputs.command_request_fingerprint is not None and (
                    receipt.request_payload_json is None or receipt.request_fingerprint != entry.inputs.command_request_fingerprint
                ):
                    raise ValueError("Ranking revision requires original command payload")
                verify_request_payload(receipt.request_payload_json, request_fingerprint=receipt.request_fingerprint,
                                       command_id=receipt.command_id, snapshot=snapshot)
            ids = [r.command_id for r in entry.receipts]
            if ids != sorted(set(ids)) or command_ids.intersection(ids):
                raise ValueError("Ranking revision command identities are not unique and ordered")
            command_ids.update(ids)
            previous = snapshot
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()


def load_ranking_revision_state(payload: str, *, expected_fingerprint: str, run_id: str, branch_id: str) -> RankingRevisionState:
    state = RankingRevisionState.model_validate_json(payload)
    if (state.run_id, state.branch_id) != (run_id, branch_id) or state.fingerprint != expected_fingerprint:
        raise ValueError("Ranking revision identity or fingerprint mismatch")
    return state
