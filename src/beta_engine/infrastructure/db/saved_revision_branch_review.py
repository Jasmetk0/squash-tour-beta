"""Read-only review of the existing Saved Revision Branch creation contract.

Native match/birth authorities deliberately remain unsupported. Their source
identities bind real rally logs and birth predecessors; hashing rewritten JSON
would not authorize a new history.
"""

from sqlalchemy import select

from beta_engine.domain.run_branches import first_available_timeline_name
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import RunBranchModel, RunContainerModel

# This is the existing writer's coverage boundary, shared with its review.
FORK_CONTENT_KEYS = frozenset(
    {
        "initial_world",
        "ranking_preparation",
        "run_prospect_source",
        "player_lifecycle",
        "player_health_state",
        "player_sporting_state",
        "simulation_slot_match_state",
        "run_entry_decision_slots",
        "application_validation_slots",
        "tournament_application_submissions",
        "definitive_wild_card_assignments",
        "player_tour_entry_triggers",
        "run_package_state",
        "run_tournament_lab_drafts",
        "season_closure",
    }
)


def unsupported_fork_content(content):
    return sorted(set(content) - FORK_CONTENT_KEYS)


def request_fingerprint(
    *, run_id, source_branch_id, source_revision_id, display_name, review
):
    return canonical_hash(
        {
            "run_id": run_id,
            "source_branch_id": source_branch_id,
            "source_revision_id": source_revision_id,
            "display_name": display_name,
            "review": review,
        }
    )


def review_in_session(
    repository,
    session,
    *,
    run_id,
    source_branch_id,
    source_revision_id,
    display_name=None,
):
    # Import here to avoid the repository/adapter import cycle.
    from beta_engine.infrastructure.db.repositories import (
        BranchRevisionStateConflictError,
        SavedRevisionBranchForkConflictError,
        SavedRevisionBranchForkNotFoundError,
    )

    run = session.get(RunContainerModel, run_id)
    branch = session.get(RunBranchModel, source_branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise SavedRevisionBranchForkNotFoundError("Source Run/Branch was not found")
    try:
        lineage = repository._validated_branch_revision_lineage_in_session(
            session=session,
            branch=branch,
            payload_revision_ids=frozenset({source_revision_id}),
        )
    except BranchRevisionStateConflictError as exc:
        raise SavedRevisionBranchForkConflictError(str(exc)) from exc
    source = next((r for r in lineage if r.revision_id == source_revision_id), None)
    if source is None:
        raise SavedRevisionBranchForkConflictError(
            "The source Saved Revision is not reachable from the selected Branch"
        )
    names = list(
        session.scalars(
            select(RunBranchModel.display_name).where(RunBranchModel.run_id == run_id)
        )
    )
    name = display_name or first_available_timeline_name(names)
    content = source.payload.get("content")
    if not isinstance(content, dict):
        raise SavedRevisionBranchForkConflictError("Invalid Saved Revision content")
    from beta_engine.infrastructure.db.player_health_state import load_saved_health
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        load_saved_lifecycle,
    )
    from beta_engine.infrastructure.db.run_prospect_source_state import (
        load_saved_run_prospect_source,
    )

    # The review must not certify a malformed auxiliary component merely because
    # its key is supported. The writer still performs its complete remap/install.
    try:
        load_saved_lifecycle(source.payload, run_id=run_id, branch_id=source.branch_id)
        load_saved_health(source.payload, run_id=run_id, branch_id=source.branch_id)
        load_saved_run_prospect_source(source.payload, run_id=run_id)
    except (TypeError, ValueError, KeyError) as exc:
        raise SavedRevisionBranchForkConflictError(
            "Saved source components failed validation"
        ) from exc
    blockers = []
    if run.read_only:
        blockers.append({"code": "read_only_run", "message": "Run is read-only"})
    if name in names:
        blockers.append(
            {"code": "branch_name_conflict", "message": "Branch name is already in use"}
        )
    unsupported = unsupported_fork_content(content)
    if unsupported:
        blockers.append(
            {
                "code": "unsupported_fork_components",
                "message": "Branch creation cannot safely remap these Saved components",
                "components": unsupported,
            }
        )
    if any(
        s.get("schema_version") == "player_lifecycle_calendar_state.v4"
        for s in content.get("player_lifecycle", {}).get("states", [])
    ):
        blockers.append(
            {
                "code": "native_birth_fork_authority_required",
                "message": "Native admission history requires authenticated fork source and Entry authority",
            }
        )
    if any(
        s.get("schema_version") == "player_health_calendar_state.v3"
        for s in content.get("player_health_state", {}).get("states", [])
    ):
        blockers.append(
            {
                "code": "native_health_fork_authority_required",
                "message": "Native Health history requires authenticated fork transition authority",
            }
        )
    # Parse only these already-authenticated source bytes, including shared
    # ancestors' actual owner. No current/future simulation inputs are read.
    from beta_engine.infrastructure.db.calendar_standalone_match_state import (
        decode_prevalidated_calendar_sources,
    )

    evidence, checkpoint, _ = decode_prevalidated_calendar_sources(
        source.payload,
        run_id=run_id,
        branch_id=source.branch_id,
    )
    knockout = getattr(evidence, "knockout", evidence)
    match_ids = {m.input_context.match_id for m in getattr(knockout, "matches", ())} | {
        m.match_id for m in getattr(checkpoint, "played_continuations", ())
    }
    if evidence is not None and knockout is evidence and hasattr(evidence, "result"):
        match_ids.add(evidence.match_id)
    cp = content.get("calendar_player_sporting_checkpoint", {}).get("state", {})
    tour = content.get("calendar_tour_authority", {}).get("state", {})
    life = content.get("player_lifecycle", {}).get("states", [])
    result = {
        "schema_version": "saved_revision_branch_review.v1",
        "run_id": run_id,
        "source_branch_id": source_branch_id,
        "source_revision_branch_id": source.branch_id,
        "source_saved_revision_id": source_revision_id,
        "source_content_hash": source.content_hash,
        "source_head_revision_id": branch.saved_head_revision_id,
        "viewer_branch_id": run.official_branch_id,
        "target_display_name": name,
        "components": sorted(content),
        "saved_week": tour.get("week") or cp.get("week"),
        "saved_player_count": len(life[-1].get("players", [])) if life else 0,
        "saved_match_count": len(match_ids),
        "saved_ranking_count": len(tour.get("rankings", [])),
        "prospect_source_schema": content.get("run_prospect_source", {}).get(
            "schema_version"
        ),
        "can_create": not blockers,
        "blockers": blockers,
    }
    # The complete Branch inventory binds the exact proposed Timeline N and name
    # availability. A concurrent create invalidates confirmation, even on siblings.
    result["preview_fingerprint"] = canonical_hash(
        {
            "review": result,
            "reserved_branch_names": sorted(names),
            "run_status": run.status,
            "run_metadata": run.metadata_json,
        }
    )
    return result
