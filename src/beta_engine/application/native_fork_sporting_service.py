"""Internal native-fork match draft; public activation/Tour/Save are still blocked.

The special pending Branch owns this versioned draft format. Ordinary read-only
Branches cannot opt into it. Original Saved roots and runtime tables are untouched.
"""

from dataclasses import dataclass

from sqlalchemy import func, text

from beta_engine.application.calendar_continuation_service import (
    CalendarContinuationCommand,
)
from beta_engine.domain.native_fork_sporting import (
    NativeForkSportingCheckpoint,
    play_native_fork_match,
    verify_native_fork_sporting,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    DIRTY_WORKING_DRAFT_STATUS,
    SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION,
    canonical_json,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.native_fork_saved_root import (
    PENDING_STATUS,
    load_native_fork_saved_root,
)
from beta_engine.infrastructure.db.run_prospect_source_state import (
    load_saved_run_prospect_source,
)

COMPONENT_KEY = "native_fork_sporting"
DRAFT_SCHEMA = "native_fork_sporting_working_draft.v1"


def _review_fingerprint(checkpoint, *, draft_id, draft_version):
    return canonical_hash(
        {
            "schema_version": "native_fork_match_review.v1",
            "draft_id": draft_id,
            "draft_version": draft_version,
            "candidate_fingerprint": checkpoint.fingerprint,
        }
    )


def _receipt(checkpoint):
    step = checkpoint.steps[-1]
    return {
        "schema_version": "native_fork_match_draft_receipt.v1",
        "run_id": checkpoint.run_id,
        "branch_id": checkpoint.branch_id,
        "command_id": step.match.command_id,
        "match_fingerprint": step.match.fingerprint,
        "checkpoint_fingerprint": checkpoint.fingerprint,
        "draft_version": step.draft_version_before + 1,
        "saved": False,
    }


@dataclass(slots=True)
class NativeForkSportingService:
    repository: object

    def _context(self, session, *, run_id, branch_id):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Native fork sporting Run/Branch is missing or foreign")
        if (
            run.read_only
            or run.status != "working"
            or run.storage_kind != "custom_local"
            or branch.status != PENDING_STATUS
            or not branch.read_only
        ):
            raise ValueError(
                "Native fork sporting draft requires its pending internal target"
            )
        state = self.repository._validated_branch_revision_state_in_session(
            session=session, branch=branch
        )
        baseline = load_native_fork_saved_root(state.saved_revision)
        if baseline is None:
            raise ValueError("Native fork sporting draft lacks an authenticated root")
        # Saved root validation above independently rebuilt all baseline facts
        # from this exact original revision inside the same SQLite snapshot.
        source = self.repository._validated_saved_revision_in_session(
            session=session,
            model=session.get(
                BranchSavedRevisionModel, baseline.source_binding.source.revision_id
            ),
        )
        world = load_saved_initial_world(
            source.payload, run_id=run_id, branch_id=source.branch_id
        )
        prospects = load_saved_run_prospect_source(source.payload, run_id=run_id)
        if prospects is not None:
            prospects = prospects.for_week(baseline.week.ordinal)
        draft = state.working_draft
        checkpoint = NativeForkSportingCheckpoint(
            root_saved_revision_id=state.saved_revision.revision_id,
            baseline=baseline,
        )
        if draft.status == CLEAN_WORKING_DRAFT_STATUS:
            if (
                draft.draft_schema_version
                != SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION
            ):
                raise ValueError(
                    "Native fork clean Working Draft has an unsupported schema"
                )
        else:
            if draft.draft_schema_version != DRAFT_SCHEMA or len(draft.changes) != 1:
                raise ValueError(
                    "Native fork sporting draft cannot absorb unrelated changes"
                )
            component = draft.changes[0]
            if (
                not isinstance(component, dict)
                or set(component) != {"kind", "fingerprint", "state"}
                or component["kind"] != COMPONENT_KEY
            ):
                raise ValueError("Native fork sporting draft component is malformed")
            checkpoint = NativeForkSportingCheckpoint.model_validate_json(
                canonical_json(component["state"])
            )
            if (
                checkpoint.baseline != baseline
                or checkpoint.root_saved_revision_id != state.saved_revision.revision_id
                or component["fingerprint"] != checkpoint.fingerprint
                or not checkpoint.steps
                or draft.draft_version != checkpoint.steps[-1].draft_version_before + 1
            ):
                raise ValueError(
                    "Native fork sporting draft differs from its actual root or version"
                )
            verify_native_fork_sporting(
                checkpoint,
                world=world,
                prospects=prospects,
                command_factory=CalendarContinuationCommand,
            )
        return state, checkpoint, world, prospects

    def inspect(self, *, run_id, branch_id):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            state, checkpoint, _, _ = self._context(
                session, run_id=run_id, branch_id=branch_id
            )
            return {
                "checkpoint": checkpoint,
                "draft_version": state.working_draft.draft_version,
                "saved_head_revision_id": state.saved_head_revision_id,
                "saved": not checkpoint.steps,
            }

    def preview_save(
        self,
        *,
        run_id,
        branch_id,
        expected_saved_head,
        expected_draft_version,
        expected_checkpoint_fingerprint,
    ):
        """Read-only authenticated review for a future native fork Manual Save.

        This is not a Save endpoint or permission to activate the pending Branch.
        Actual source rows and the entire match draft are replay-verified by
        _context before the review fingerprint is computed.
        """
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            state, checkpoint, _, _ = self._context(
                session, run_id=run_id, branch_id=branch_id
            )
            draft = state.working_draft
            if draft.status != DIRTY_WORKING_DRAFT_STATUS or not checkpoint.steps:
                raise ValueError("Native fork Save review requires a dirty played draft")
            if expected_saved_head != state.saved_head_revision_id:
                raise ValueError("Native fork Save review has a stale Saved HEAD")
            if expected_draft_version != draft.draft_version:
                raise ValueError("Native fork Save review has a stale Working Draft")
            if expected_checkpoint_fingerprint != checkpoint.fingerprint:
                raise ValueError("Native fork Save review has a stale sporting checkpoint")
            review = {
                "schema_version": "native_fork_sporting_save_review.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "root_saved_revision_id": checkpoint.root_saved_revision_id,
                "saved_head_revision_id": state.saved_head_revision_id,
                "draft_id": draft.draft_id,
                "draft_version": draft.draft_version,
                "checkpoint_fingerprint": checkpoint.fingerprint,
                "match_count": len(checkpoint.steps),
                "last_match_fingerprint": checkpoint.steps[-1].match.fingerprint,
            }
            return {
                "review": review,
                "review_fingerprint": canonical_hash(review),
                "saved": False,
            }

    def preview(self, *, run_id, branch_id, command, expected_draft_version):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            state, checkpoint, world, prospects = self._context(
                session, run_id=run_id, branch_id=branch_id
            )
            if expected_draft_version != state.working_draft.draft_version:
                raise ValueError("Native fork match Working Draft review is stale")
            candidate = play_native_fork_match(
                checkpoint,
                command,
                draft_version=expected_draft_version,
                world=world,
                prospects=prospects,
            )
            return {
                "checkpoint": candidate,
                "preview_fingerprint": _review_fingerprint(
                    candidate,
                    draft_id=state.working_draft.draft_id,
                    draft_version=expected_draft_version,
                ),
            }

    def execute(
        self,
        *,
        run_id,
        branch_id,
        command,
        expected_draft_version,
        expected_preview_fingerprint,
        explicit_confirmation,
    ):
        if explicit_confirmation is not True:
            raise ValueError("Explicit native fork match confirmation is required")
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            state, checkpoint, world, prospects = self._context(
                session, run_id=run_id, branch_id=branch_id
            )
            for index, step in enumerate(checkpoint.steps):
                if step.match.command_id == command.command_id:
                    prefix = checkpoint.model_copy(
                        update={"steps": checkpoint.steps[: index + 1]}
                    )
                    request = canonical_hash(
                        {
                            "run_id": run_id,
                            "branch_id": branch_id,
                            "command": command.model_dump(mode="json"),
                        }
                    )
                    if (
                        step.match.request_fingerprint != request
                        or step.draft_version_before != expected_draft_version
                        or _review_fingerprint(
                            prefix,
                            draft_id=state.working_draft.draft_id,
                            draft_version=expected_draft_version,
                        )
                        != expected_preview_fingerprint
                    ):
                        raise ValueError(
                            "Native fork match retry conflicts with the recorded command"
                        )
                    return _receipt(prefix)
            if expected_draft_version != state.working_draft.draft_version:
                raise ValueError("Native fork match Working Draft review is stale")
            candidate = play_native_fork_match(
                checkpoint,
                command,
                draft_version=expected_draft_version,
                world=world,
                prospects=prospects,
            )
            if (
                _review_fingerprint(
                    candidate,
                    draft_id=state.working_draft.draft_id,
                    draft_version=expected_draft_version,
                )
                != expected_preview_fingerprint
            ):
                raise ValueError(
                    "Native fork match preview is stale or belongs to another command"
                )
            draft = session.get(BranchWorkingDraftModel, state.working_draft.draft_id)
            draft.status = DIRTY_WORKING_DRAFT_STATUS
            draft.draft_schema_version = DRAFT_SCHEMA
            draft.draft_version += 1
            draft.updated_at = func.current_timestamp()
            draft.change_count = 1
            draft.changes_json = canonical_json(
                [
                    {
                        "kind": COMPONENT_KEY,
                        "fingerprint": candidate.fingerprint,
                        "state": candidate.model_dump(mode="json"),
                    }
                ]
            )
            session.flush()
            return _receipt(candidate)

    def discard(
        self, *, run_id, branch_id, expected_draft_version, explicit_confirmation
    ):
        if explicit_confirmation is not True:
            raise ValueError(
                "Explicit native fork draft discard confirmation is required"
            )
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            state, _, _, _ = self._context(session, run_id=run_id, branch_id=branch_id)
            if expected_draft_version != state.working_draft.draft_version:
                raise ValueError("Native fork draft discard review is stale")
            if state.working_draft.status == CLEAN_WORKING_DRAFT_STATUS:
                return
            draft = session.get(BranchWorkingDraftModel, state.working_draft.draft_id)
            draft.status = CLEAN_WORKING_DRAFT_STATUS
            draft.draft_schema_version = (
                SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION
            )
            draft.draft_version += 1
            draft.updated_at = func.current_timestamp()
            draft.change_count = 0
            draft.changes_json = "[]"
            session.flush()
