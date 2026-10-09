"""Bind verified Week Transition receipts to their target-owned ranking lineage.

Canonical standard tournaments, including simultaneous same-week events, are supported
only when each frozen canonical source has independently remapped evidence.
No database writes occur in this module.
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


def _verify_published_transition_coverage(
    source: RankingRevisionState,
) -> None:
    """Reject missing history even when receipt and World Event vanish together.

    Published ranking weeks are authoritative and cannot be silently inferred
    from a surviving subset of Week Transition receipts. Staged, *unpublished*
    future ranking candidates/authorities are not part of this requirement.
    """
    state = source.authoritative_transition_state
    if not isinstance(state, dict):
        _reject("Post-transition fork requires captured publication history")
    publications = state.get("publications")
    world = state.get("world")
    receipts = state.get("receipts")
    if not isinstance(publications, list) or not isinstance(receipts, list) or not isinstance(world, dict):
        _reject("Post-transition fork requires authoritative published history")

    # A Run begins with Week 1 (ordinal zero) and every confirmed empty
    # transition publishes exactly the following ordinal. Never treat an
    # intermediate gap as a branchable Saved Revision.
    expected_ordinals = list(range(len(publications)))
    actual_ordinals = [row.get("week_ordinal") for row in publications if isinstance(row, dict)]
    if not publications or actual_ordinals != expected_ordinals:
        _reject("Published ranking history is missing, duplicated or out of order")
    snapshots = {entry.snapshot.week.ordinal: entry.snapshot for entry in source.entries}
    if (
        len(snapshots) != len(source.entries)
        or any(
            ordinal not in snapshots
            or row.get("run_id") != source.run_id
            or row.get("branch_id") != source.branch_id
            or row.get("snapshot_fingerprint") != snapshots[ordinal].fingerprint
            for ordinal, row in enumerate(publications)
        )
        or world.get("run_id") != source.run_id
        or world.get("branch_id") != source.branch_id
        or world.get("current_ordinal") != expected_ordinals[-1]
        or world.get("ranking_fingerprint") != snapshots[expected_ordinals[-1]].fingerprint
    ):
        _reject("Published ranking/world head differs from frozen source snapshots")

    confirmed_weeks: list[int] = []
    for row in receipts:
        try:
            command = AuthoritativeWeekTransitionCommand.model_validate_json(
                row["request_payload_json"]
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WeekTransitionForkAuditUnsupportedError(
                "Published Week Transition receipt is invalid"
            ) from exc
        confirmed_weeks.append(command.target_week.ordinal)
    if sorted(confirmed_weeks) != expected_ordinals[1:]:
        _reject("Published ranking weeks lack exactly paired Week Transition receipts")


def _verified_tournament_bindings(
    source: RankingRevisionState,
    target: RankingRevisionState,
    *,
    source_branch_id: str,
    target_branch_id: str,
) -> dict:
    """Prove exact source/target tournament identity before audit reconstruction.

    Ranking remapping validates source command history, frozen result versions,
    canonical result/point awards and target ranking recalculation. Do not allow
    the audit adapter to invent a target binding missing from that proof.
    """
    if len(source.tournament_sources) != len(target.tournament_sources):
        _reject("Tournament ranking source count changed in fork")
    bindings = {}
    week_events: set[tuple[int, str]] = set()
    for original, remapped in zip(
        source.tournament_sources, target.tournament_sources, strict=True
    ):
        old, new = original.binding, remapped.binding
        if (
            old.branch_id != source_branch_id
            or new.branch_id != target_branch_id
            or old.run_id != source.run_id
            or new.run_id != target.run_id
            or old.closing_only
            or new.closing_only
            or original.schema_version not in {
                "owned_tournament_ranking_source.v4",
                "owned_tournament_ranking_source.v5",
            }
            or original.canonical_result is None
            or original.canonical_awards is None
            or remapped.canonical_result is None
            or remapped.canonical_awards is None
            or not original.canonical_result.matches
            or any(
                match.result_fingerprint is None
                for match in original.canonical_result.matches
                if match.scoreline != "BYE"
            )
            or (
                old.edition_id, old.event_id, old.completed_week,
                old.first_publication_week, old.validity_weeks,
                old.ranking_status,
            ) != (
                new.edition_id, new.event_id, new.completed_week,
                new.first_publication_week, new.validity_weeks,
                new.ranking_status,
            )
            or (
                original.canonical_result.champion_player_id,
                original.canonical_result.finalist_player_id,
                original.canonical_result.players,
            ) != (
                remapped.canonical_result.champion_player_id,
                remapped.canonical_result.finalist_player_id,
                remapped.canonical_result.players,
            )
            or old.edition_id in bindings
            or (old.completed_week.ordinal, old.event_id) in week_events
        ):
            _reject("Completed tournament canonical source does not match fork evidence")
        bindings[old.edition_id] = new
        week_events.add((old.completed_week.ordinal, old.event_id))
    return bindings


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
    It must only be installed by the surrounding atomic player/slot/revision
    fork transaction after verified target-local player/slot evidence exists.
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
    _verify_published_transition_coverage(source)

    tournament_bindings = _verified_tournament_bindings(
        source, target,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
    )
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
        tournament_bindings=tournament_bindings,
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
