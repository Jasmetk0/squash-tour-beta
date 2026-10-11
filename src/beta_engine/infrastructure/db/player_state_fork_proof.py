"""Verify target-owned player history before committing a materialized Branch fork.

The Saved Revision component loaders validate chain fingerprints independently.
This cross-component proof additionally ensures identity rebinding has not changed
any player facts, historical timing, effective policy or sporting context semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from beta_engine.domain.players.health import PlayerHealthWeekState
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerSportingWeekState,
)


class PlayerStateForkProofError(ValueError):
    """Source and target player histories are not an equivalent Branch fork."""


@dataclass(frozen=True)
class VerifiedForkPlayerStateMaps:
    lifecycle: dict[str, str]
    sporting: dict[str, str]
    health: dict[str, str]
    contexts: dict[str, str]


def _verify_states(
    source: Sequence[Any],
    target: Sequence[Any],
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    kind: str,
    mutable_fields: frozenset[str],
) -> dict[str, str]:
    if len(source) != len(target):
        raise PlayerStateForkProofError(f"{kind}: source/target history length differs")
    mapping: dict[str, str] = {}
    target_values: set[str] = set()
    previous_source = None
    previous_target = None
    previous_ordinal = None
    for original, forked in zip(source, target, strict=True):
        if (
            (original.run_id, original.branch_id) != (run_id, source_branch_id)
            or (forked.run_id, forked.branch_id) != (run_id, target_branch_id)
            or original.week != forked.week
        ):
            raise PlayerStateForkProofError(f"{kind}: ownership/week mismatch")
        ordinal = original.week.ordinal
        if previous_ordinal is not None and ordinal != previous_ordinal + 1:
            raise PlayerStateForkProofError(f"{kind}: historical week gap")
        if (
            original.predecessor_fingerprint
            != (previous_source.fingerprint if previous_source else None)
            or forked.predecessor_fingerprint
            != (previous_target.fingerprint if previous_target else None)
        ):
            raise PlayerStateForkProofError(f"{kind}: predecessor chain mismatch")
        original_data = original.model_dump(mode="json")
        forked_data = forked.model_dump(mode="json")
        for field in mutable_fields | {"branch_id", "predecessor_fingerprint"}:
            original_data.pop(field, None)
            forked_data.pop(field, None)
        if original_data != forked_data:
            raise PlayerStateForkProofError(
                f"{kind}: historical player data or effective policy changed"
            )
        if original.fingerprint in mapping or forked.fingerprint in target_values:
            raise PlayerStateForkProofError(f"{kind}: non-unique historical fingerprint")
        mapping[original.fingerprint] = forked.fingerprint
        target_values.add(forked.fingerprint)
        previous_source, previous_target = original, forked
        previous_ordinal = ordinal
    return mapping


def _verify_contexts(
    source: Sequence[CompletedWeekSportingContext],
    target: Sequence[CompletedWeekSportingContext],
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> dict[str, str]:
    if len(source) != len(target):
        raise PlayerStateForkProofError("Sporting context count mismatch")
    mapping: dict[str, str] = {}
    target_fingerprints: set[str] = set()
    previous_week = None
    for original, forked in zip(source, target, strict=True):
        if (
            (original.run_id, original.branch_id) != (run_id, source_branch_id)
            or (forked.run_id, forked.branch_id) != (run_id, target_branch_id)
            or original.completed_week != forked.completed_week
            or original.schema_version != forked.schema_version
            or original.competitive_match_counts != forked.competitive_match_counts
            or original.provenance != forked.provenance
        ):
            raise PlayerStateForkProofError("Sporting context identity/facts mismatch")
        ordinal = original.completed_week.ordinal
        if previous_week is not None and ordinal != previous_week + 1:
            raise PlayerStateForkProofError("Sporting context chronological gap")
        if (
            original.fingerprint in mapping
            or forked.fingerprint in target_fingerprints
        ):
            raise PlayerStateForkProofError("Sporting context fingerprint collision")
        mapping[original.fingerprint] = forked.fingerprint
        target_fingerprints.add(forked.fingerprint)
        previous_week = ordinal
    return mapping


def verify_fork_player_state_maps(
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    source_lifecycle: Sequence[PlayerLifecycleWeekState] = (),
    target_lifecycle: Sequence[PlayerLifecycleWeekState] = (),
    source_sporting: Sequence[PlayerSportingWeekState] = (),
    target_sporting: Sequence[PlayerSportingWeekState] = (),
    source_health: Sequence[PlayerHealthWeekState] = (),
    target_health: Sequence[PlayerHealthWeekState] = (),
    source_contexts: Sequence[CompletedWeekSportingContext] = (),
    target_contexts: Sequence[CompletedWeekSportingContext] = (),
) -> VerifiedForkPlayerStateMaps:
    """Prove immutable player histories are equivalent, then return fingerprint maps.

    This does not authorize post-transition forks by itself. That requires
    independently verified target ranking, Saved Revision and receipts/events,
    installed in the same transaction before the revision is committed.
    """
    if not run_id or not source_branch_id or not target_branch_id or (
        source_branch_id == target_branch_id
    ):
        raise PlayerStateForkProofError("Source and target Branch must be distinct")
    lifecycle = _verify_states(
        source_lifecycle, target_lifecycle,
        run_id=run_id, source_branch_id=source_branch_id,
        target_branch_id=target_branch_id, kind="Lifecycle",
        mutable_fields=frozenset(),
    )
    health = _verify_states(
        source_health, target_health,
        run_id=run_id, source_branch_id=source_branch_id,
        target_branch_id=target_branch_id, kind="Health",
        mutable_fields=frozenset(),
    )
    contexts = _verify_contexts(
        source_contexts, target_contexts,
        run_id=run_id, source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
    )
    sporting = _verify_states(
        source_sporting, target_sporting,
        run_id=run_id, source_branch_id=source_branch_id,
        target_branch_id=target_branch_id, kind="Sporting",
        mutable_fields=frozenset({"completed_context_fingerprint"}),
    )
    for original, forked in zip(source_sporting, target_sporting, strict=True):
        source_context_fp = original.completed_context_fingerprint
        target_context_fp = forked.completed_context_fingerprint
        if original.week.ordinal == 0:
            if source_context_fp != target_context_fp:
                raise PlayerStateForkProofError(
                    "Sporting bootstrap context changed"
                )
        elif contexts.get(source_context_fp) != target_context_fp:
            raise PlayerStateForkProofError(
                "Sporting snapshot has no mapped completed-week context"
            )
    return VerifiedForkPlayerStateMaps(
        lifecycle=lifecycle,
        sporting=sporting,
        health=health,
        contexts=contexts,
    )
