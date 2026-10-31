"""SQLite snapshot/export and atomic cold installation of a closed Saved archive."""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import String, Text, select, text
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Mapped, mapped_column

from beta_engine.domain.run_branch_archive import (
    AuditSpec,
    BranchSpec,
    CheckpointSpec,
    RevisionSpec,
    RunSpec,
    decode,
    digest,
    encode,
    fail,
    pack,
)
from beta_engine.domain.run_revisions import RUN_WORKING_DRAFT_SCHEMA_VERSION
from beta_engine.infrastructure.db.models import (
    Base,
    BranchRevisionAuditEventModel,
    BranchSavedRevisionCheckpointModel,
    BranchSavedRevisionModel,
    BranchStateModel,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
    RunPackageIdentityAllocatorModel,
)
from beta_engine.infrastructure.db.run_branch_archive_components import (
    capture_content,
    install_components,
    install_prospects,
    prospect_records,
    validate_components,
)


class RunBranchArchiveReceiptModel(Base):
    """Confirmed import audit and exact retry, committed with every installed row."""

    __tablename__ = "run_branch_archive_receipts"
    command_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    archive_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_label: Mapped[str] = mapped_column(String(160), nullable=False)
    audit_reason: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


def _row_values(row, spec):
    return {name: getattr(row, name) for name in spec.model_fields}


def _scope_branch(session, run_id, branch_id):
    branch = session.get(RunBranchModel, branch_id)
    if branch is None or branch.run_id != run_id:
        fail(
            "missing_owner",
            f"Required original Branch {branch_id!r} is missing or foreign",
        )
    if (
        branch.status != "active"
        or branch.read_only
        or any(
            (
                branch.legacy_simulation_run_id,
                branch.head_checkpoint_id,
                branch.forked_from_checkpoint_id,
            )
        )
    ):
        fail(
            "unsupported_branch",
            "Archive v1 requires active writable Saved Branches without legacy simulation/checkpoint ownership",
        )
    # Task Center history is product data, not a worker lease. Until a separate
    # semantic Task-history adapter exists, reject it instead of dropping it or
    # restoring controls that could restart a process.
    from beta_engine.infrastructure.db.full_simulation_command_scope import (
        sporting_simulation_commands,
    )
    from beta_engine.infrastructure.db.models import (
        AuthoritativeSimulationCommandModel,
        FullSimulationTaskModel,
    )

    if (
        session.scalar(
            select(FullSimulationTaskModel.task_id)
            .where(
                FullSimulationTaskModel.run_id == run_id,
                FullSimulationTaskModel.branch_id == branch_id,
            )
            .limit(1)
        )
        is not None
    ):
        fail(
            "unsupported_task_history",
            "Archive v1 needs a Task-history adapter for this Branch; no Task history or process will be silently omitted/restarted",
        )
    commands = session.scalars(
        select(AuthoritativeSimulationCommandModel).where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        )
    ).all()
    if len(sporting_simulation_commands(session, commands)) != len(commands):
        fail(
            "unsupported_task_history",
            "Archive v1 cannot yet transfer independent native Task history/controls",
        )
    return branch


def _check_clean(repository, session, branch, payload):
    draft = session.scalar(
        select(BranchWorkingDraftModel).where(
            BranchWorkingDraftModel.branch_id == branch.branch_id
        )
    )
    if (
        draft is None
        or draft.run_id != branch.run_id
        or draft.base_revision_id != branch.saved_head_revision_id
        or draft.status != "clean"
        or draft.change_count != 0
        or decode(draft.changes_json) != []
    ):
        fail(
            "unsaved_changes",
            f"Save or cancel export: Branch {branch.branch_id!r} has unsaved/incoherent Working Draft",
        )
    from beta_engine.infrastructure.db.saved_revision_restore_coverage import (
        active_transient_restore_blockers,
        missing_component_coverage,
    )

    if active_transient_restore_blockers(
        session, run_id=branch.run_id, branch_id=branch.branch_id
    ):
        fail(
            "unsaved_changes",
            "Save or cancel export: unsaved authoring/task state exists in exported scope",
        )
    if "native_fork_runtime" in payload["content"]:
        # The native clean draft resolves the existing fully verified aggregate;
        # no mutable live component tables may be silently omitted.
        live = missing_component_coverage(
            session, run_id=branch.run_id, branch_id=branch.branch_id, saved_content={}
        )
        if live:
            fail(
                "uncaptured_live_state",
                "Native fork has foreign live components outside its Saved aggregate",
            )
        return
    if encode(
        capture_content(
            session, payload, run_id=branch.run_id, branch_id=branch.branch_id
        )
    ) != encode(payload["content"]):
        fail(
            "unsaved_changes",
            f"Save or cancel export: live components differ from Saved HEAD of {branch.branch_id!r}",
        )
    missing = missing_component_coverage(
        session,
        run_id=branch.run_id,
        branch_id=branch.branch_id,
        saved_content=payload["content"],
    )
    if missing:
        fail(
            "uncaptured_live_state",
            "Saved HEAD does not capture: " + ", ".join(x.label for x in missing),
        )


def collect_archive(repository, session, *, run_id, branch_id, expected_head=None):
    """All reads belong to ONE explicit SQLite snapshot owned by the caller."""
    run = session.get(RunContainerModel, run_id)
    if run is None:
        fail("run_not_found", "Export Run was not found")
    if (
        run.storage_kind != "custom_local"
        or run.read_only
        or any(
            x is not None
            for x in (
                run.world_id,
                run.world_package_fingerprint,
                run.config_version,
                run.config_fingerprint,
                run.global_seed,
            )
        )
    ):
        fail(
            "unsupported_run",
            "Archive v1 supports custom Saved Runs; legacy/global-backed or protected Run metadata needs another adapter",
        )
    selected = _scope_branch(session, run_id, branch_id)
    if expected_head is not None and selected.saved_head_revision_id != expected_head:
        fail(
            "stale_export_preview",
            "Saved HEAD changed since export preview; review the new Saved state",
        )
    branches, anchors, rows, payloads, checked = {}, {}, {}, {}, set()
    pending = []

    def anchor(bid, revision_id=None):
        owner = _scope_branch(session, run_id, bid)
        rid = revision_id or owner.saved_head_revision_id
        row = session.get(BranchSavedRevisionModel, rid)
        if row is None or row.run_id != run_id:
            fail(
                "missing_revision",
                "Required source/head Saved Revision is absent or foreign",
            )
        previous = anchors.get(bid)
        if (
            previous is None
            or row.sequence > session.get(BranchSavedRevisionModel, previous).sequence
        ):
            branches[bid], anchors[bid] = owner, rid
            pending.append((bid, rid))

    anchor(branch_id)
    anchor(run.official_branch_id)
    # The Viewer choice may have been Saved by a third editing Branch. Preserve
    # that actual immutable witness as a dependency instead of inventing a new
    # selection or assuming the Viewer Branch Saved its own selection.
    expected_run = {
        "run_id": run.run_id,
        "display_name": run.display_name,
        "status": run.status,
        "timeline_start_season": run.timeline_start_season,
        "timeline_end_season": run.timeline_end_season,
        "viewer_branch_id": run.official_branch_id,
    }
    metadata = decode(run.metadata_json)
    candidates = session.scalars(
        select(RunBranchModel).where(RunBranchModel.run_id == run_id)
    ).all()
    candidates.sort(
        key=lambda b: (
            b.branch_id != branch_id,
            b.branch_id != run.official_branch_id,
            b.branch_id,
        )
    )
    activation_revision_id = None
    for candidate in candidates:
        witness = session.get(
            BranchSavedRevisionModel, candidate.saved_head_revision_id
        )
        if witness is None:
            continue
        projection = decode(witness.payload_json).get("run", {})
        if all(
            projection.get(k) == v for k, v in expected_run.items()
        ) and projection.get("run_calendar") == metadata.get("run_calendar"):
            activation_revision_id = witness.revision_id
            anchor(candidate.branch_id, witness.revision_id)
            break
    if activation_revision_id is None:
        fail(
            "unsaved_run_metadata",
            "No current Saved Branch witnesses the actual Run calendar/name/Viewer choice",
        )

    def drain_pending():
        while pending:
            bid, rid = pending.pop()
            key = bid, rid
            if key in checked:
                continue
            checked.add(key)
            owner = branches[bid]
            # Verify reachability against ACTUAL source metadata and full original
            # lineage. Only the selected historical prefix goes into the archive.
            lineage = repository._validated_branch_revision_lineage_in_session(
                session=session, branch=owner
            )
            members = {r.revision_id: r for r in lineage}
            if rid not in members:
                fail(
                    "unreachable_revision",
                    "Required Saved revision is not reachable through its selected Branch context",
                )
            current = rid
            while current is not None:
                revision = members.get(current)
                if revision is None:
                    fail(
                        "unreachable_revision",
                        "A parent is outside authenticated original history",
                    )
                row = session.get(BranchSavedRevisionModel, current)
                if current not in rows:
                    rows[current] = RevisionSpec.model_validate(
                        _row_values(row, RevisionSpec)
                    )
                    payloads[current] = decode(row.payload_json)
                    validate_components(
                        payloads[current], run_id=run_id, branch_id=row.branch_id
                    )
                    anchor(row.branch_id, current)
                    # Historical Viewer identities must remain valid read contexts.
                    viewer = payloads[current]["run"]["viewer_branch_id"]
                    if viewer not in anchors:
                        anchor(viewer)
                    baseline = (
                        payloads[current]["content"]
                        .get("native_fork_baseline", {})
                        .get("state")
                    )
                    if baseline:
                        anchor(
                            baseline["selected_source_branch_id"],
                            baseline["source_binding"]["source"]["revision_id"],
                        )
                current = revision.parent_revision_id
            if owner.forked_from_branch_id:
                anchor(owner.forked_from_branch_id, owner.forked_from_saved_revision_id)

    while True:
        drain_pending()
        # A pre-restore Viewer may differ from every retained Saved envelope
        # when that selection was Saved through another editing Branch.
        checkpoint_viewers = session.scalars(
            select(BranchSavedRevisionCheckpointModel.viewer_branch_id).where(
                BranchSavedRevisionCheckpointModel.run_id == run_id,
                BranchSavedRevisionCheckpointModel.restore_saved_revision_id.in_(rows),
            )
        ).all()
        for viewer in checkpoint_viewers:
            if viewer not in anchors:
                anchor(viewer)
        if not pending:
            break
    specs = []
    for bid in sorted(branches):
        branch, rid = branches[bid], anchors[bid]
        if rid == branch.saved_head_revision_id:
            _check_clean(repository, session, branch, payloads[rid])
        specs.append(
            BranchSpec(
                branch_id=bid,
                display_name=branch.display_name,
                status=branch.status,
                branch_seed=branch.branch_seed,
                forked_from_branch_id=branch.forked_from_branch_id,
                forked_from_saved_revision_id=branch.forked_from_saved_revision_id,
                saved_head_revision_id=rid,
                metadata_json=branch.metadata_json,
                role="selected" if bid == branch_id else "dependency",
            ).model_dump()
        )
    revision_ids = set(rows)
    audits = [
        AuditSpec.model_validate(_row_values(a, AuditSpec)).model_dump()
        for a in session.scalars(
            select(BranchRevisionAuditEventModel)
            .where(
                BranchRevisionAuditEventModel.run_id == run_id,
                BranchRevisionAuditEventModel.saved_revision_id.in_(revision_ids),
            )
            .order_by(BranchRevisionAuditEventModel.audit_event_id)
        )
    ]
    checkpoints = [
        CheckpointSpec.model_validate(_row_values(c, CheckpointSpec)).model_dump()
        for c in session.scalars(
            select(BranchSavedRevisionCheckpointModel)
            .where(
                BranchSavedRevisionCheckpointModel.run_id == run_id,
                BranchSavedRevisionCheckpointModel.restore_saved_revision_id.in_(
                    revision_ids
                ),
            )
            .order_by(BranchSavedRevisionCheckpointModel.checkpoint_id)
        )
    ]
    allocator = session.get(RunPackageIdentityAllocatorModel, run_id)
    omitted = sorted(
        set(
            session.scalars(
                select(RunBranchModel.branch_id).where(RunBranchModel.run_id == run_id)
            )
        )
        - branches.keys()
    )
    spec = RunSpec(
        run_id=run_id,
        display_name=run.display_name,
        status=run.status,
        timeline_start_season=run.timeline_start_season,
        timeline_end_season=run.timeline_end_season,
        viewer_branch_id=run.official_branch_id,
        activation_revision_id=activation_revision_id,
        metadata_json=run.metadata_json,
    )
    raw = pack(
        run=spec.model_dump(),
        branches=specs,
        revisions=[
            r.model_dump()
            for r in sorted(rows.values(), key=lambda r: (r.sequence, r.revision_id))
        ],
        audits=audits,
        checkpoints=checkpoints,
        allocator=allocator.next_run_local_id if allocator else 1,
        selected_branch_id=branch_id,
        selected_head_revision_id=selected.saved_head_revision_id,
        omitted_branch_ids=omitted,
    )
    return raw


def _draft_id(branch_id):
    return "archive-clean-draft:" + digest(branch_id.encode())


def conflicts(session, archive):
    """Check every original/deterministic identity, including orphaned ownership."""
    from beta_engine.infrastructure.db.models import SimulationRunModel

    result = []
    run_id = archive.run.run_id
    # A Run can have orphaned component/receipt rows. Reserve the complete Run
    # namespace, not just its top-level row, without importing any table data.
    for table in Base.metadata.sorted_tables:
        if (
            "run_id" in table.c
            and session.execute(
                select(table.c.run_id).where(table.c.run_id == run_id).limit(1)
            ).first()
        ):
            result.append(
                {"code": "run_identity_exists", "identity": run_id, "area": table.name}
            )
    if session.get(SimulationRunModel, run_id) is not None:
        result.append({"code": "legacy_run_identity_exists", "identity": run_id})
    if (
        session.scalar(
            select(RunContainerModel.run_id).where(
                RunContainerModel.display_name == archive.run.display_name
            )
        )
        is not None
    ):
        result.append({"code": "run_name_exists", "identity": archive.run.display_name})
    for model, ids in (
        (RunBranchModel, [b.branch_id for b in archive.branches]),
        (BranchStateModel, [b.branch_id for b in archive.branches]),
        (BranchWorkingDraftModel, [_draft_id(b.branch_id) for b in archive.branches]),
        (BranchSavedRevisionModel, [r.revision_id for r in archive.revisions]),
        (BranchRevisionAuditEventModel, [a.audit_event_id for a in archive.audits]),
        (
            BranchSavedRevisionCheckpointModel,
            [c.checkpoint_id for c in archive.checkpoints],
        ),
    ):
        for identity in ids:
            if session.get(model, identity) is not None:
                result.append(
                    {
                        "code": "original_identity_exists",
                        "identity": identity,
                        "area": model.__tablename__,
                    }
                )
    # Also catch an orphaned draft using a different draft_id for this Branch.
    for bid in [b.branch_id for b in archive.branches]:
        if session.scalar(
            select(BranchWorkingDraftModel.draft_id).where(
                BranchWorkingDraftModel.branch_id == bid
            )
        ):
            result.append({"code": "branch_draft_exists", "identity": bid})
    return result


def _validate_run_envelope(archive):
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.run_branches import normalize_branch_display_name
    from beta_engine.domain.run_containers import normalize_run_display_name

    run = archive.run
    if normalize_run_display_name(run.display_name) != run.display_name:
        fail(
            "invalid_run_name", "Run name must retain a valid normalized original name"
        )
    metadata = decode(run.metadata_json)
    if not isinstance(metadata, dict) or set(metadata) - {"run_calendar"}:
        fail(
            "unsupported_run_metadata",
            "Archive v1 only activates the Saved Run calendar metadata",
        )
    clock = (
        RunCalendar.from_metadata(metadata["run_calendar"])
        if "run_calendar" in metadata
        else RunCalendar.legacy_fax()
    )
    if (run.timeline_start_season, run.timeline_end_season) != (
        clock.start_year,
        clock.start_year + clock.season_count - 1,
    ):
        fail("invalid_run_calendar", "Run timeline and original calendar disagree")
    for branch in archive.branches:
        if normalize_branch_display_name(
            branch.display_name
        ) != branch.display_name or not isinstance(decode(branch.metadata_json), dict):
            fail("invalid_branch_metadata", "Branch name or metadata is invalid")
    revisions = {r.revision_id: r for r in archive.revisions}
    for branch in archive.branches:
        head = revisions[branch.saved_head_revision_id]
        if head.branch_id == branch.branch_id:
            signed = decode(head.payload_json)["branch"]
            for name in (
                "branch_id",
                "display_name",
                "status",
                "forked_from_branch_id",
                "forked_from_saved_revision_id",
            ):
                if signed.get(name) != getattr(branch, name):
                    fail(
                        "invalid_branch_context",
                        "Branch activation differs from its original owned Saved HEAD",
                    )
    # Preserve every historical calendar, but require a Saved witness for the
    # current Run clock/name/status and Viewer choice. No new defaults/migration.
    activation = next(
        r for r in archive.revisions if r.revision_id == run.activation_revision_id
    )
    witness = decode(activation.payload_json)["run"]
    expected = {
        "run_id": run.run_id,
        "display_name": run.display_name,
        "status": run.status,
        "timeline_start_season": run.timeline_start_season,
        "timeline_end_season": run.timeline_end_season,
        "viewer_branch_id": run.viewer_branch_id,
    }
    if (
        not all(witness.get(k) == v for k, v in expected.items())
        or witness.get("run_calendar", clock.to_metadata()) != clock.to_metadata()
    ):
        fail(
            "unsaved_run_metadata",
            "Run activation has no matching original Saved witness",
        )
    for r in archive.revisions:
        saved = decode(r.payload_json)["run"]
        historical = (
            RunCalendar.from_metadata(saved["run_calendar"])
            if "run_calendar" in saved
            else RunCalendar.legacy_fax()
        )
        if (
            historical.weeks_per_year,
            historical.season_start_year_week,
            historical.start_year,
        ) != (
            clock.weeks_per_year,
            clock.season_start_year_week,
            clock.start_year,
        ) or historical.season_count > clock.season_count:
            fail(
                "incompatible_calendar",
                "Historical Saved calendar is incompatible with its Run",
            )


def install_archive(repository, session, archive):
    """Caller owns transaction; every failure, including receipts, rolls back."""
    _validate_run_envelope(archive)
    run, run_id = archive.run, archive.run.run_id
    session.add(
        RunContainerModel(
            run_id=run_id,
            display_name=run.display_name,
            storage_kind="custom_local",
            read_only=0,
            timeline_start_season=run.timeline_start_season,
            timeline_end_season=run.timeline_end_season,
            official_branch_id=run.viewer_branch_id,
            status=run.status,
            metadata_json=run.metadata_json,
        )
    )
    for b in archive.branches:
        values = b.model_dump(exclude={"role"})
        session.add(RunBranchModel(run_id=run_id, read_only=0, **values))
        session.add(
            BranchStateModel(run_id=run_id, branch_id=b.branch_id, status=b.status)
        )
        session.add(
            BranchWorkingDraftModel(
                draft_id=_draft_id(b.branch_id),
                run_id=run_id,
                branch_id=b.branch_id,
                base_revision_id=b.saved_head_revision_id,
                status="clean",
                change_count=0,
                draft_version=0,
                changes_json="[]",
                draft_schema_version=RUN_WORKING_DRAFT_SCHEMA_VERSION,
            )
        )
    for r in archive.revisions:
        session.add(BranchSavedRevisionModel(**r.model_dump()))
    for a in archive.audits:
        session.add(BranchRevisionAuditEventModel(**a.model_dump()))
    for c in archive.checkpoints:
        session.add(BranchSavedRevisionCheckpointModel(**c.model_dump()))
    session.add(
        RunPackageIdentityAllocatorModel(
            run_id=run_id, next_run_local_id=archive.allocator
        )
    )
    install_prospects(
        session, run_id=run_id, records=prospect_records(archive.revisions)
    )
    session.flush()
    # Validate ALL actual immutable rows/owners/physical proofs BEFORE activating
    # any live component. Import never invents a new simulation authority.
    for b in archive.branches:
        repository._validated_branch_revision_lineage_in_session(
            session=session, branch=session.get(RunBranchModel, b.branch_id)
        )
    by_id = {r.revision_id: r for r in archive.revisions}
    max_local_id = 0
    for revision in archive.revisions:
        payload = decode(revision.payload_json)
        validate_components(payload, run_id=run_id, branch_id=revision.branch_id)
        package = payload["content"].get("run_package_state", {}).get("state", {})
        max_local_id = max(
            max_local_id, *(e["run_local_id"] for e in package.get("entities", ())), 0
        )
    if archive.allocator <= max_local_id:
        fail(
            "invalid_allocator",
            "Package allocator would recycle a historical Run-local identity",
        )
    for b in archive.branches:
        revision = by_id[b.saved_head_revision_id]
        payload = decode(revision.payload_json)
        if revision.branch_id != b.branch_id:
            if payload["content"]:
                fail(
                    "unsupported_shared_activation",
                    "A shared nonempty HEAD requires the existing materialized-fork adapter before export",
                )
            continue
        install_components(session, payload, run_id=run_id, branch_id=b.branch_id)
        if "native_fork_runtime" not in payload["content"] and encode(
            capture_content(session, payload, run_id=run_id, branch_id=b.branch_id)
        ) != encode(payload["content"]):
            fail(
                "incomplete_activation",
                "Cold activation differs from the original Saved component set",
            )
    session.flush()
    # Reuse the established recovery-activity validator against this SAME
    # uncommitted transaction, including checkpoint/audit pairing and ownership.
    from beta_engine.application.run_saved_revision_recovery_activity_service import (
        RunSavedRevisionRecoveryActivityService,
    )

    history = _TransactionHistory(repository, session)
    for b in archive.branches:
        RunSavedRevisionRecoveryActivityService(history).get_activity(
            run_id=run_id, branch_id=b.branch_id
        )
    # Final actual physical source/lineage gate, after every component write.
    for b in archive.branches:
        repository._validated_branch_revision_lineage_in_session(
            session=session, branch=session.get(RunBranchModel, b.branch_id)
        )


def validate_in_isolated_database(archive):
    """No target writes, source file, global Package registry or process cache."""
    from beta_engine.infrastructure.db.engine import (
        DatabaseSettings,
        create_session_factory,
        create_sqlite_engine,
    )
    from beta_engine.infrastructure.db.repositories import (
        SimulationPersistenceRepository,
    )

    with TemporaryDirectory(prefix="run-branch-archive-") as directory:
        # Required temporary space is operation-specific, never a history quota.
        if shutil.disk_usage(directory).free < archive.size * 3:
            fail(
                "insufficient_temporary_space",
                "Insufficient temporary space to validate this archive atomically",
            )
        engine = create_sqlite_engine(
            DatabaseSettings(url=f"sqlite:///{Path(directory) / 'validation.db'}")
        )
        try:
            Base.metadata.create_all(engine)
            repository = SimulationPersistenceRepository(
                engine=engine, session_factory=create_session_factory(engine)
            )
            with repository._session_factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                install_archive(repository, session, archive)
        except (OverflowError, StatementError) as exc:
            reason = str(exc.orig) if isinstance(exc, StatementError) else str(exc)
            fail(
                "invalid_archive_persistence",
                "Archive cannot satisfy the supported SQLite schema: " + reason,
            )
        finally:
            engine.dispose()


class _TransactionHistory:
    """Read-only adapter for existing history validation in a caller transaction."""

    def __init__(self, repository, session):
        self.repository, self.session = repository, session

    def get_branch_saved_revision_history(self, *, run_id, branch_id):
        from beta_engine.infrastructure.db.repositories import (
            BranchSavedRevisionHistoryRecord,
        )

        branch = self.session.get(RunBranchModel, branch_id)
        lineage = self.repository._validated_branch_revision_lineage_in_session(
            session=self.session, branch=branch
        )
        return BranchSavedRevisionHistoryRecord(
            run_id, branch_id, branch.saved_head_revision_id, tuple(reversed(lineage))
        )

    def list_branch_saved_revision_checkpoints(self, *, branch_id):
        return [
            self.repository._to_branch_saved_revision_checkpoint(row)
            for row in self.session.scalars(
                select(BranchSavedRevisionCheckpointModel).where(
                    BranchSavedRevisionCheckpointModel.branch_id == branch_id
                )
            )
        ]

    def list_branch_revision_audit_events(self, *, branch_id):
        # The existing recovery validator predates sporting Saves and recognizes
        # only Viewer-selection and guarded-restore audit semantics. Other audit
        # kinds are retained byte-for-byte and structurally owner-checked by the
        # closed archive; do not misclassify sporting Saves as Viewer commands.
        rows = self.session.scalars(
            select(BranchRevisionAuditEventModel).where(
                BranchRevisionAuditEventModel.branch_id == branch_id
            )
        ).all()
        supported = []
        for row in rows:
            revision = self.session.get(BranchSavedRevisionModel, row.saved_revision_id)
            if row.event_kind == "branch_restored" or (
                row.event_kind == "saved_revision_created"
                and revision.kind == "viewer_branch_selection"
            ):
                supported.append(self.repository._to_branch_revision_audit_event(row))
        return supported
