"""Read-only publication views over authenticated actual Saved fork sources."""

from types import SimpleNamespace

from beta_engine.application.native_fork_runtime_reducer import source_inputs
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.native_fork_runtime_state import load_runtime


def publication_inputs(repository, session, revision):
    # The complete Saved dependency proof precedes this projection; no draft or
    # mutable Run-wide prospect catalog participates in historical publication.
    runtime = load_runtime(revision.payload)
    original = repository._validated_saved_revision_in_session(
        session=session,
        model=session.get(
            BranchSavedRevisionModel, runtime.baseline.source_binding.source.revision_id
        ),
    )
    sources = source_inputs(original, repository, session)
    state = SimpleNamespace(
        **{k: getattr(runtime.tour, k) for k in type(runtime.tour).model_fields}
    )
    history = (*getattr(sources, "history_tours", ()), sources.tour)
    state.fingerprint = runtime.tour.fingerprint
    state.inherited_final_closure = getattr(sources, "final_closure", None)
    state.receipts = (
        tuple(r for t in history for r in t.receipts) + runtime.tour.receipts
    )
    state.rankings = (
        tuple(r for t in history for r in t.rankings) + runtime.tour.rankings
    )
    world = SimpleNamespace(
        run_id=runtime.run_id,
        branch_id=runtime.branch_id,
        players=sources.world.players,
    )
    return state, world
