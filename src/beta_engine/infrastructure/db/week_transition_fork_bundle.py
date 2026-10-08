"""Bind verified event-free transition receipts to a remapped ranking lineage.

Pure planning step for a future atomic post-transition fork. No database writes
and no relaxation of the production fail-closed branch/restore guards.
"""

from __future__ import annotations

from collections.abc import Mapping

from beta_engine.application.authoritative_week_transition import (
    AuthoritativeWeekTransitionCommand,
    AuthoritativeWeekTransitionResult,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.infrastructure.db.week_transition_fork_audit import (
    WeekTransitionForkAuditUnsupportedError,
    remap_event_free_week_transition_audit,
)


def _reject(reason: str):
    raise WeekTransitionForkAuditUnsupportedError(reason)


def _unique_fingerprint_map(
    original, remapped, *,
    identity,
    field: str,
) -> dict[str, str]:
    if len(original) != len(remapped):
        _reject(f"Ranking fork {field} count changed")
    mapping: dict[str, str] = {}
    for left, right in zip(original, remapped, strict=True):
        if identity(left) != identity(right):
            _reject(f"Ranking fork {field} chronology or evidence changed")
        if left.fingerprint in mapping:
            _reject(f"Ranking fork {field} source fingerprint is duplicated")
        mapping[left.fingerprint] = right.fingerprint
    if len(set(mapping.values())) != len(mapping):
        _reject(f"Ranking fork {field} target fingerprint is duplicated")
    return mapping


def bind_event_free_transition_audit_to_ranking_fork(
    *,
    source: RankingRevisionState,
    target: RankingRevisionState,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    lifecycle_fingerprint_map: Mapping[str, str],
    sporting_fingerprint_map: Mapping[str, str],
    health_fingerprint_map: Mapping[str, str],
    valid_source_revision_ids: frozenset[str] | None = None,
) -> RankingRevisionState:
    """Return a validated target ranking bundle with rebuilt Week Transition audit.

    Caller must first remap the ranking lineage with
    `remap_source_free_ranking_state_for_branch` using an in-memory audit-free
    *copy*. The original source (including its receipts/events) is immutable.
    Caller-supplied player mappings must come from separately verified
    target-local player state; this pure layer cannot prove their provenance.
    It must NOT be installed until the surrounding atomic player/slot/revision
    fork transaction and replay/rollback verification are implemented.
    When the caller supplies its independently validated source revision lineage,
    both the authority's creation revision and the later confirmed command's
    base revision must be reachable; a Save may legitimately occur between them.
    """
    if (
        not run_id or not source_branch_id or not target_branch_id
        or source_branch_id == target_branch_id
        or (source.run_id, source.branch_id) != (run_id, source_branch_id)
        or (target.run_id, target.branch_id) != (run_id, target_branch_id)
        or source.authoritative_transition_state is None
        or target.authoritative_transition_state is None
    ):
        _reject("Ranking fork evidence Run/Branch scope mismatch")
    source_state = source.authoritative_transition_state
    target_state = target.authoritative_transition_state
    if not isinstance(source_state, dict) or not isinstance(target_state, dict):
        _reject("Ranking fork transition audit state must be captured")
    if target_state["receipts"] or target_state["events"]:
        _reject("Target ranking fork audit must be empty before rebinding")
    if not source_state["receipts"] or len(source_state["receipts"]) != len(source_state["events"]):
        _reject("Source Week Transition audit is incomplete")
    if source.season_closing_rankings or target.season_closing_rankings:
        _reject("Season Closing fork evidence is not supported")

    snapshot_map = _unique_fingerprint_map(
        tuple(entry.snapshot for entry in source.entries),
        tuple(entry.snapshot for entry in target.entries),
        identity=lambda row: (
            row.week, row.policy,
            tuple((item.player_id, item.rank, item.points) for item in row.rows),
        ),
        field="snapshot",
    )
    authority_map = _unique_fingerprint_map(
        source.transition_authorities,
        target.transition_authorities,
        identity=lambda row: (
            row.completed_week, row.target_week, row.players, row.policy,
            row.audit, row.provenance, row.adopted_by_command_id,
        ),
        field="transition authority",
    )
    target_authorities = {
        item.target_week.ordinal: item for item in target.transition_authorities
    }
    source_authorities = {
        item.target_week.ordinal: item for item in source.transition_authorities
    }
    source_snapshots = {item.snapshot.week.ordinal: item.snapshot for item in source.entries}
    if (
        len(source_authorities) != len(source.transition_authorities)
        or len(target_authorities) != len(target.transition_authorities)
    ):
        _reject("Ranking transition authority week is duplicated")

    base_revision_map: dict[str, str] = {}
    for row in source_state["receipts"]:
        try:
            original = AuthoritativeWeekTransitionCommand.model_validate_json(
                row["request_payload_json"]
            )
            result = AuthoritativeWeekTransitionResult.model_validate_json(
                row["result_json"]
            )
            authority = source_authorities[original.target_week.ordinal]
            target_authority = target_authorities[original.target_week.ordinal]
            source_snapshot = source_snapshots[original.target_week.ordinal]
        except (KeyError, TypeError, ValueError) as exc:
            raise WeekTransitionForkAuditUnsupportedError(
                f"Week Transition fork audit has no canonical ranking authority: {exc}"
            ) from exc
        if (
            original.completed_week != authority.completed_week
            or original.target_week != authority.target_week
            or original.authority_fingerprint != authority.fingerprint
            or (
                original.base_revision_id != authority.base_revision_id
                if valid_source_revision_ids is None
                else (
                    original.base_revision_id not in valid_source_revision_ids
                    or authority.base_revision_id not in valid_source_revision_ids
                )
            )
            or original.audit != authority.audit
            or result.target_week != original.target_week
            or result.official_ranking_fingerprint != source_snapshot.fingerprint
        ):
            _reject("Saved Week Transition receipt differs from frozen ranking authority")
        previous = base_revision_map.setdefault(
            original.base_revision_id, target_authority.base_revision_id
        )
        if previous != target_authority.base_revision_id:
            _reject("One historical Saved Revision maps to conflicting fork identities")
    if not source_state["receipts"]:
        _reject("No Week Transition receipts to rebind")

    remapped = remap_event_free_week_transition_audit(
        {"receipts": source_state["receipts"], "events": source_state["events"]},
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
        base_revision_ids=base_revision_map,
        ranking_authorities=authority_map,
        ranking_snapshots=snapshot_map,
        lifecycle_states=lifecycle_fingerprint_map,
        sporting_states=sporting_fingerprint_map,
        health_states=health_fingerprint_map,
    )
    merged_state = {
        **target_state,
        "receipts": remapped["receipts"],
        "events": remapped["events"],
    }
    try:
        rebound = RankingRevisionState.model_validate_json(
            target.model_copy(
                update={"authoritative_transition_state": merged_state}
            ).model_dump_json()
        )
    except ValueError as exc:
        raise WeekTransitionForkAuditUnsupportedError(
            f"Rebound ranking revision failed validation: {exc}"
        ) from exc
    return rebound
