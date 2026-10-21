"""Resolve native historical authority without remapping or installing state.

The selected Saved Revision and its ancestry must already have passed the
repository's full identity/hash/component/lineage checks in this transaction.
Actual original execution sources are then checked against that historical
prefix, not against the selected Branch's newer live head or prospect catalog.
This is the source side of a fork; target continuation remains a separate writer.
"""

from beta_engine.domain.native_fork_source import (
    NativeForkComponentSource,
    NativeForkSavedSource,
    NativeForkSourceBinding,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    decode_prevalidated_calendar_sources,
)
from beta_engine.infrastructure.db.calendar_tour import verify_tour_origins
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel


def resolve_native_fork_source_binding(repository, session, *, binding, branch):
    """Reauthenticate a persisted reference; possession of a hash is insufficient.

    The caller owns the surrounding transaction. This returns the original Saved
    record, not a remapped working state and not permission to execute on its owner.
    """
    if branch.run_id != binding.run_id:
        raise ValueError("Native fork source belongs to another Run")
    lineage = repository._validated_branch_revision_lineage_in_session(
        session=session,
        branch=branch,
        payload_revision_ids=frozenset({binding.source.revision_id}),
    )
    source = next(
        (r for r in lineage if r.revision_id == binding.source.revision_id),
        None,
    )
    if source is None:
        raise ValueError("Native fork source is not reachable from this Branch")
    expected = bind_prevalidated_native_fork_source(
        repository,
        session,
        source=source,
        lineage=lineage,
    )
    if expected != binding:
        raise ValueError(
            "Native fork source binding differs from actual Saved authority"
        )
    return source


def bind_prevalidated_native_fork_source(repository, session, *, source, lineage):
    """Bind original native inputs to real Saved sources, or fail closed.

    ``lineage`` is produced by ``_validated_branch_revision_lineage_in_session``.
    Only ancestors BEFORE ``source`` are eligible; a later valid source from the
    same Branch is still forbidden. Referenced rows are reloaded and authenticated
    so this function never authorizes caller-supplied model hashes or metadata.
    """
    evidence, checkpoint, tour = decode_prevalidated_calendar_sources(
        source.payload,
        run_id=source.run_id,
        branch_id=source.branch_id,
    )
    if evidence is None:
        if checkpoint is not None or tour is not None:
            raise ValueError("Native fork has orphan sporting/Tour authority")
        return None
    prefix = {r.revision_id: r for r in lineage if r.sequence < source.sequence}
    if source.revision_id not in {r.revision_id for r in lineage}:
        raise ValueError("Native fork source is absent from its authenticated lineage")
    world = load_saved_initial_world(
        source.payload,
        run_id=source.run_id,
        branch_id=source.branch_id,
    )
    if world is None:
        raise ValueError("Native fork has no original Saved population")
    resolved = {}

    def origin(revision_id, *, materialize_payload=False):
        if revision_id not in prefix:
            raise ValueError(
                "Native execution source is outside the selected Saved past"
            )
        if revision_id in resolved and not materialize_payload:
            return resolved[revision_id]
        row = session.get(BranchSavedRevisionModel, revision_id)
        if row is None or (row.run_id, row.branch_id) != (
            source.run_id,
            source.branch_id,
        ):
            raise ValueError(
                "Native execution source is missing or has a foreign owner"
            )
        original = repository._validated_saved_revision_in_session(
            session=session,
            model=row,
            materialize_payload=materialize_payload,
        )
        # The lineage could contain metadata-only records. Compare their signed
        # envelope identity as well as the freshly authenticated actual row.
        member = prefix[revision_id]
        if (original.content_hash, original.branch_id, original.sequence) != (
            member.content_hash,
            member.branch_id,
            member.sequence,
        ):
            raise ValueError("Native execution source changed after lineage validation")
        # Do not retain a full roster/rally log copy for every historical command.
        # The repository still validates every exact stored signature; only the
        # one actual pre-play source below needs its payload materialized here.
        from dataclasses import replace

        resolved[revision_id] = replace(original, payload={}, change_summary={})
        return original

    knockout = getattr(evidence, "knockout", evidence)
    opening = origin(knockout.source_saved_head, materialize_payload=True)
    original_world = load_saved_initial_world(
        opening.payload,
        run_id=source.run_id,
        branch_id=source.branch_id,
    )
    if (
        original_world is None
        or original_world.fingerprint != knockout.source_initial_world_fingerprint
    ):
        raise ValueError(
            "Native opening match does not own its actual pre-play Saved population"
        )
    if original_world.fingerprint != world.fingerprint:
        raise ValueError(
            "Native fork population differs from original played authority"
        )
    if opening.payload["content"].get("calendar_standalone_match") is not None:
        raise ValueError("Native opening source already contains played history")
    if getattr(knockout, "schema_version", None) in {
        "calendar_opening_knockout.v3",
        "calendar_opening_knockout.v4",
        "calendar_opening_knockout.v5",
    }:
        from beta_engine.domain.players.calendar_knockout_health import (
            CalendarKnockoutHealthSource,
        )
        from beta_engine.infrastructure.db.player_health_state import load_saved_health

        health = load_saved_health(
            opening.payload,
            run_id=source.run_id,
            branch_id=source.branch_id,
        )
        if health and (len(health) != 1 or health[0].week.ordinal != 0):
            raise ValueError("Native opening source has no unique opening Health state")
        expected = (
            CalendarKnockoutHealthSource.from_state(health[0], knockout.entrant_ids)
            if health
            else None
        )
        if knockout.health_source != expected:
            raise ValueError(
                "Native opening Health differs from its actual pre-play Saved source"
            )
    if tour is not None:
        verify_tour_origins(session, tour, _reachable_revision_ids=frozenset(prefix))
        for receipt in tour.receipts:
            command = receipt.request.get("command")
            if not isinstance(command, dict) or not command.get("expected_saved_head"):
                raise ValueError("Native command lacks its original Saved source")
            origin(command["expected_saved_head"])
        for edition in tour.editions:
            origin(edition.created_saved_head)
            if edition.played_saved_head:
                origin(edition.played_saved_head)
    if checkpoint is not None:
        tournament_matches = {
            m.match_id for event in checkpoint.tournaments for m in event.matches
        }
        for event in checkpoint.tournaments:
            origin(event.source_saved_head)
        for match in checkpoint.played_continuations:
            if match.match_id not in tournament_matches:
                origin(match.source_saved_head)
    return NativeForkSourceBinding(
        run_id=source.run_id,
        source=NativeForkSavedSource(
            revision_id=source.revision_id,
            branch_id=source.branch_id,
            content_hash=source.content_hash,
        ),
        components=tuple(
            NativeForkComponentSource(key=key, content_hash=canonical_hash(value))
            for key, value in sorted(source.payload["content"].items())
        ),
        historical_sources=tuple(
            NativeForkSavedSource(
                revision_id=r.revision_id,
                branch_id=r.branch_id,
                content_hash=r.content_hash,
            )
            for _, r in sorted(resolved.items())
        ),
    )
