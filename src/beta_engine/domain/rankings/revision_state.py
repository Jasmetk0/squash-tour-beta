"""Self-contained ranking preparation state for future Saved Revision content."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator, model_serializer
from beta_engine.domain.rankings.command_audit import verify_request_payload
from beta_engine.domain.rankings.zero_history import RankingZeroVersion, validate_zero_successor, resolve_zero_versions

from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingSnapshot,
    RankingWeek,
    load_official_ranking_snapshot,
)
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.result_history import RankingResultVersion, validate_result_successor
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)


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
    schema_version: Literal[
        "ranking_revision_state.v1",
        "ranking_revision_state.v2",
        "ranking_revision_state.v3",
        "ranking_revision_state.v4",
        "ranking_revision_state.v5",
    ] = "ranking_revision_state.v4"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    entries: tuple[RankingRevisionEntry, ...]
    sources: tuple[RankingResultVersion, ...]
    zero_sources: tuple[RankingZeroVersion, ...] = ()
    tournament_sources: tuple[OwnedTournamentRankingSource, ...] = ()
    transition_authorities: tuple[RankingTransitionAuthority, ...] = ()
    tournament_ranking_snapshot_authorities: tuple[
        TournamentRankingSnapshotAuthority, ...
    ] = ()
    authoritative_transition_state: dict | None = None

    @model_serializer(mode="wrap")
    def serialize_state(self, handler):
        data = handler(self)
        if not self.zero_sources:
            data.pop("zero_sources", None)
        if not self.tournament_sources:
            data.pop("tournament_sources", None)
        if not self.transition_authorities:
            data.pop("transition_authorities", None)
        if not self.tournament_ranking_snapshot_authorities:
            data.pop("tournament_ranking_snapshot_authorities", None)
        if self.authoritative_transition_state is None:
            data.pop("authoritative_transition_state", None)
        return data

    @model_validator(mode="after")
    def validate_complete_state(self):
        if self.schema_version == "ranking_revision_state.v1" and self.tournament_sources:
            raise ValueError("Ranking revision state v1 cannot contain tournament sources")
        if self.schema_version in ("ranking_revision_state.v1", "ranking_revision_state.v2") and self.transition_authorities:
            raise ValueError("Legacy ranking revision state cannot contain transition authority")
        if self.schema_version not in {"ranking_revision_state.v4", "ranking_revision_state.v5"} and self.authoritative_transition_state is not None:
            raise ValueError("Legacy ranking revision state cannot contain Week Transition state")
        if (
            self.schema_version != "ranking_revision_state.v5"
            and self.tournament_ranking_snapshot_authorities
        ):
            raise ValueError(
                "Legacy ranking revision state cannot contain Tournament Ranking Snapshot authority"
            )
        if self.authoritative_transition_state is not None:
            state = self.authoritative_transition_state
            if set(state) != {"world", "publications", "receipts", "events"}:
                raise ValueError("Invalid authoritative Week Transition revision state")
            world = state["world"]
            if world is not None and (world["run_id"], world["branch_id"]) != (self.run_id, self.branch_id):
                raise ValueError("Authoritative world state scope mismatch")
            ordinals = [row["week_ordinal"] for row in state["publications"]]
            if ordinals != sorted(set(ordinals)):
                raise ValueError("Official Ranking publication order is invalid")
            if ordinals and ordinals != list(range(ordinals[0], ordinals[-1] + 1)):
                raise ValueError("Official Ranking publication lineage has a gap")
            for row in state["publications"]:
                if (row["run_id"], row["branch_id"]) != (self.run_id, self.branch_id):
                    raise ValueError("Official Ranking publication scope mismatch")
                load_official_ranking_snapshot(
                    row["payload_json"],
                    expected_fingerprint=row["snapshot_fingerprint"],
                    run_id=self.run_id,
                    branch_id=self.branch_id,
                    week=RankingWeek(
                        season_index=row["week_ordinal"] // 61,
                        week=row["week_ordinal"] % 61 + 1,
                    ),
                )
            receipt_ids = [row["command_id"] for row in state["receipts"]]
            event_ids = [row["command_id"] for row in state["events"]]
            if receipt_ids != sorted(set(receipt_ids)) or event_ids != receipt_ids:
                raise ValueError("Week Transition receipts and World Events do not pair")
            for row in (*state["receipts"], *state["events"]):
                if (row["run_id"], row["branch_id"]) != (self.run_id, self.branch_id):
                    raise ValueError("Week Transition audit scope mismatch")
            if world is not None and (not ordinals or world["current_ordinal"] != ordinals[-1]
                    or world["ranking_fingerprint"] != state["publications"][-1]["snapshot_fingerprint"]):
                raise ValueError("Authoritative world head differs from published ranking")
        tournament_snapshot_keys = [
            authority.event_id
            for authority in self.tournament_ranking_snapshot_authorities
        ]
        if tournament_snapshot_keys != sorted(set(tournament_snapshot_keys)):
            raise ValueError(
                "Tournament Ranking Snapshot authority order or uniqueness is invalid"
            )
        publication_by_week = {}
        if self.authoritative_transition_state is not None:
            publication_by_week = {
                row["week_ordinal"]: row
                for row in self.authoritative_transition_state["publications"]
            }
        for authority in self.tournament_ranking_snapshot_authorities:
            if (authority.run_id, authority.branch_id) != (
                self.run_id,
                self.branch_id,
            ):
                raise ValueError(
                    "Tournament Ranking Snapshot authority scope mismatch"
                )
            publication = publication_by_week.get(authority.ranking_week.ordinal)
            if publication is None:
                raise ValueError(
                    "Tournament Ranking Snapshot authority publication is missing"
                )
            if (
                publication["snapshot_fingerprint"]
                != authority.ranking_snapshot_fingerprint
            ):
                raise ValueError(
                    "Tournament Ranking Snapshot authority publication fingerprint differs"
                )

        ordinals = [a.target_week.ordinal for a in self.transition_authorities]
        if ordinals != sorted(set(ordinals)):
            raise ValueError("Ranking transition authority order or uniqueness is invalid")
        if any((a.run_id, a.branch_id) != (self.run_id, self.branch_id) for a in self.transition_authorities):
            raise ValueError("Ranking transition authority scope mismatch")
        owned_keys = [(s.binding.edition_id, s.binding.event_id) for s in self.tournament_sources]
        if owned_keys != sorted(set(owned_keys)):
            raise ValueError("Owned tournament source order or uniqueness is invalid")
        for source in self.tournament_sources:
            if (source.binding.run_id, source.binding.branch_id) != (self.run_id, self.branch_id):
                raise ValueError("Owned tournament source scope mismatch")
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


def ranking_revision_states_equivalent(
    left: RankingRevisionState, right: RankingRevisionState
) -> bool:
    """Compare authoritative content without rewriting historical wire identity.

    V1-v4 predate Tournament Ranking Snapshot authority.  When neither side carries
    that authority they retain the established v4 normalization used by Saved
    Revision compatibility.  Once either side carries event ranking authority the
    comparison upgrades both sides to v5; a v4 state cannot silently erase that
    authority because the non-empty field remains part of the normalized payload.
    """
    normalized_version = (
        "ranking_revision_state.v5"
        if (
            left.tournament_ranking_snapshot_authorities
            or right.tournament_ranking_snapshot_authorities
        )
        else "ranking_revision_state.v4"
    )
    return left.model_copy(
        update={"schema_version": normalized_version}
    ).model_dump(mode="json") == right.model_copy(
        update={"schema_version": normalized_version}
    ).model_dump(mode="json")
