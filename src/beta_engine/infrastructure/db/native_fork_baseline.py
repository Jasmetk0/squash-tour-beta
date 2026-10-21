"""Read-only preparation and reauthentication of target-owned native baselines.

This adapter neither reserves an identifier nor installs runtime rows. The final
Branch writer must install the baseline and all continuation authorities in one
transaction before enabling native creation. Existing create guards stay intact.
"""

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.native_fork_baseline import project_native_fork_baseline
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    decode_prevalidated_calendar_sources,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.models import RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.native_fork_source import (
    bind_prevalidated_native_fork_source,
    resolve_native_fork_source_binding,
)
from beta_engine.infrastructure.db.player_health_state import load_saved_health
from beta_engine.infrastructure.db.player_lifecycle_state import load_saved_lifecycle


def _project(source, binding, *, source_branch_id, target_branch_id):
    world = load_saved_initial_world(
        source.payload,
        run_id=source.run_id,
        branch_id=source.branch_id,
    )
    life = load_saved_lifecycle(
        source.payload,
        run_id=source.run_id,
        branch_id=source.branch_id,
    )
    health = load_saved_health(
        source.payload,
        run_id=source.run_id,
        branch_id=source.branch_id,
    )
    _, checkpoint, tour = decode_prevalidated_calendar_sources(
        source.payload,
        run_id=source.run_id,
        branch_id=source.branch_id,
    )
    if world is None or not life or not health or checkpoint is None or tour is None:
        raise ValueError(
            "Native fork baseline requires the complete initialized Saved Tour"
        )
    calendar = RunCalendar.from_metadata(source.payload["run"]["run_calendar"])
    position = calendar.position_at_ordinal(tour.week.ordinal)
    week = RunWeekPosition(
        calendar=calendar,
        season_index=position.season_index,
        week=position.season_week,
    )
    return project_native_fork_baseline(
        binding=binding,
        selected_source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
        week=week,
        world_fingerprint=world.fingerprint,
        lifecycle=life[-1],
        health=health[-1],
        checkpoint=checkpoint,
        tour=tour,
    )


def prepare_native_fork_baseline_in_session(
    repository,
    session,
    *,
    run_id,
    source_branch_id,
    source_revision_id,
    target_branch_id,
):
    run = session.get(RunContainerModel, run_id)
    branch = session.get(RunBranchModel, source_branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise ValueError("Native fork baseline source Run/Branch is missing or foreign")
    if run.read_only:
        raise ValueError(
            "Native fork baseline cannot prepare a new Branch in a read-only Run"
        )
    if session.get(RunBranchModel, target_branch_id) is not None:
        raise ValueError("Native fork target Branch identifier is already in use")
    lineage = repository._validated_branch_revision_lineage_in_session(
        session=session,
        branch=branch,
        payload_revision_ids=frozenset({source_revision_id}),
    )
    source = next((r for r in lineage if r.revision_id == source_revision_id), None)
    if source is None:
        raise ValueError(
            "Native fork baseline source is not reachable from selected Branch"
        )
    binding = bind_prevalidated_native_fork_source(
        repository,
        session,
        source=source,
        lineage=lineage,
    )
    if binding is None:
        raise ValueError("Native fork baseline has no authenticated played source")
    return _project(
        source,
        binding,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
    )


def verify_native_fork_baseline_in_session(
    repository,
    session,
    *,
    baseline,
    run_id,
    source_branch_id,
    source_revision_id,
    target_branch_id,
):
    # All expected identities come from the caller's command/transaction, not
    # from the supplied reference. A valid baseline for another target is not
    # permission to execute the current command there.
    if (
        baseline.run_id,
        baseline.selected_source_branch_id,
        baseline.source_binding.source.revision_id,
        baseline.branch_id,
    ) != (run_id, source_branch_id, source_revision_id, target_branch_id):
        raise ValueError("Native fork baseline differs from the expected command scope")
    branch = session.get(RunBranchModel, source_branch_id)
    if branch is None or branch.run_id != run_id:
        raise ValueError(
            "Native fork baseline selected source Branch is missing or foreign"
        )
    target = session.get(RunBranchModel, target_branch_id)
    if target is not None and (
        target.run_id,
        target.forked_from_branch_id,
        target.forked_from_saved_revision_id,
    ) != (run_id, source_branch_id, source_revision_id):
        raise ValueError("Native fork baseline target has a different declared origin")
    source = resolve_native_fork_source_binding(
        repository,
        session,
        binding=baseline.source_binding,
        branch=branch,
    )
    expected = _project(
        source,
        baseline.source_binding,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
    )
    if expected != baseline:
        raise ValueError(
            "Native fork baseline current facts differ from actual Saved authority"
        )
    return baseline
