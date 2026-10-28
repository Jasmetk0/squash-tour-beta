"""Explicit independent native fork commands and immutable aggregate Saves.

The original event owners are never rewritten. Each operation authenticates the
actual original Saved inputs and replays the new target suffix in its transaction.
"""

import json
from copy import deepcopy
from dataclasses import dataclass

from sqlalchemy import select, text

from beta_engine.application.native_fork_runtime_reducer import (
    prepare_command,
    source_inputs,
    tour_fingerprint,
    transition_blockers,
)
from beta_engine.domain.rankings.calendar_terminal_result import (
    CalendarTerminalRankingResult,
    result_activation_ordinal,
)
from beta_engine.domain.run_revisions import (
    canonical_json,
    saved_revision_content_hash,
    saved_viewer_branch_id,
)
from beta_engine.domain.tournaments.calendar_tour import edition_results
from beta_engine.infrastructure.db.models import (
    BranchRevisionAuditEventModel,
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.native_fork_runtime_state import (
    DRAFT_SCHEMA,
    KEY,
    SAVED_SCHEMA,
    commit_prepared,
    component,
    load_runtime,
    native_read_proof_scope,
    verify_runtime,
)


def is_native_fork(repository, run_id, branch_id):
    with repository._session_factory() as session:
        branch = session.get(RunBranchModel, branch_id)
        row = (
            session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
            if branch
            else None
        )
        return bool(
            branch
            and branch.run_id == run_id
            and row
            and row.payload_schema_version == SAVED_SCHEMA
        )


@dataclass
class NativeForkRuntimeService:
    repository: object

    def _context(self, session, run_id, branch_id):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Native fork Run/Branch was not found")
        if run.read_only or branch.read_only or branch.status != "active":
            raise ValueError("Native fork requires a writable active Branch")
        revision = self.repository._validated_saved_revision_in_session(
            session=session,
            model=session.get(BranchSavedRevisionModel, branch.saved_head_revision_id),
        )
        signed = load_runtime(revision.payload)
        original = self.repository._validated_saved_revision_in_session(
            session=session,
            model=session.get(
                BranchSavedRevisionModel,
                signed.baseline.source_binding.source.revision_id,
            ),
        )
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == branch_id
            )
        )
        if (
            draft is None
            or draft.run_id != run_id
            or draft.base_revision_id != revision.revision_id
        ):
            raise ValueError(
                "Native fork Working Draft has a missing or foreign Saved base"
            )
        current = signed
        if draft.status == "dirty":
            changes = json.loads(draft.changes_json)
            if draft.draft_schema_version == DRAFT_SCHEMA:
                if (
                    not isinstance(changes, list)
                    or len(changes) != 1
                    or set(changes[0]) != {"kind", "component"}
                    or changes[0]["kind"] != KEY
                    or draft.change_count != 1
                ):
                    raise ValueError("Malformed native fork Working Draft")
                current = load_runtime({"content": {KEY: changes[0]["component"]}})
                if (
                    current.baseline != signed.baseline
                    or current.root_saved_revision_id != signed.root_saved_revision_id
                ):
                    raise ValueError(
                        "Native fork Working Draft changes the original source"
                    )
                # Both immutable sources have just passed actual-row dependency
                # validation. Cache only the exact complete Working aggregate.
                signature = (revision.revision_id, revision.content_hash, original.content_hash, current.fingerprint)
                with self.repository._revision_validation_lock:
                    proofs = getattr(self.repository, "_global_fork_working_proofs", None)
                    if proofs is None:
                        proofs = self.repository._global_fork_working_proofs = {}
                    verified = bool(current.global_slots and signature in proofs)
                if not verified:
                    verify_runtime(
                        self.repository,
                        session,
                        runtime=current,
                        revision=revision,
                        original=original,
                        working=True,
                    )
                    if current.global_slots:
                        with self.repository._revision_validation_lock:
                            proofs[signature] = True
                            while len(proofs) > 8:
                                proofs.pop(next(iter(proofs)))
            elif draft.draft_schema_version != "run_working_draft_v1":
                raise ValueError("Native fork has an unsupported Working Draft")
        elif (
            draft.status != "clean" or draft.change_count or draft.changes_json != "[]"
        ):
            raise ValueError("Native fork has an incoherent clean Working Draft")
        sources = source_inputs(original, self.repository, session)
        from beta_engine.domain.calendar.run_calendar import RunCalendar

        sources.execution_calendar = RunCalendar.from_metadata(
            revision.payload["run"]["run_calendar"]
        )
        return run, branch, revision, draft, signed, current, original, sources

    def inspect(self, *, run_id, branch_id):
        with self.repository._session_factory() as session, native_read_proof_scope():
            session.execute(text("BEGIN"))
            _run, _branch, revision, draft, signed, current, _original, sources = (
                self._context(session, run_id, branch_id)
            )
            return self._inspection(revision, draft, signed, current, sources)

    def _inspection(self, revision, draft, signed, current, sources):
        from beta_engine.application.calendar_tour_season_summary import (
            completed_season_indices,
            saved_final_closure,
        )
        from beta_engine.domain.native_fork_runtime import ForkCompetitionView
        from beta_engine.domain.players.calendar_native_competition import (
            native_match_slot,
        )

        names = {p.player_id: p.name for p in sources.world.players}
        if sources.prospects:
            names.update(
                {
                    r["prospect_id"]: r.get("display_name") or r["prospect_id"]
                    for r in sources.prospects.records
                }
            )
        life = {p.player_id: p for p in current.lifecycle.players}
        evidence, contributions = {}, {}
        tournaments = {
            t.tournament_id: t
            for t in ForkCompetitionView(current, sources.checkpoint).tournaments
        }
        counted = {
            r.source_fingerprint
            for row in current.tour.rankings[-1].rows
            for r in row.counted_results
        }
        for authority in current.tour.editions:
            event = tournaments.get(authority.edition.edition_id)
            if event is None or not authority.tournament_fingerprint:
                continue
            results = edition_results(authority, event)
            evidence[authority.edition.edition_id] = {
                "results": [
                    {**r.model_dump(mode="json"), "stage": a.reached_stage}
                    for r, a in zip(results, event.prepared_awards, strict=True)
                ],
                "matches": [
                    {
                        "match_id": m.match_id,
                        "slot": next((s.number for s in ForkCompetitionView(current, sources.checkpoint).history_global_slots if hasattr(s, "accepted") and any(x.match_id == m.match_id for x in s.accepted)), None) if authority.edition.schema_version == "calendar_tournament_edition.v3" else native_match_slot(authority, i),
                        "player_a_id": m.result.player_a_id,
                        "player_b_id": m.result.player_b_id,
                        "winner_player_id": m.result.winner_player_id,
                        "rally_count": len(m.result.rally_log.events),
                    }
                    for i, m in enumerate(event.matches)
                ],
            }
            for result in results:
                age = current.week.ordinal - result_activation_ordinal(result, current.week.calendar)
                status = (
                    "awaiting_confirmation"
                    if not authority.result_confirmed
                    else "closing_only"
                    if isinstance(result, CalendarTerminalRankingResult) and age < 0
                    else "awaiting_activation"
                    if age < 0
                    else "expired"
                    if age >= result.validity_weeks
                    else "counted"
                    if result.source_fingerprint in counted
                    else "excluded_best_n"
                )
                contributions.setdefault(result.player_id, []).append(
                    {**result.model_dump(mode="json"), "status": status}
                )
        from beta_engine.application.calendar_global_slot_service import slot_inspection
        from beta_engine.application.calendar_native_groups import inspect_groups
        return {
            "groups": inspect_groups(current.tour, ForkCompetitionView(current, sources.checkpoint)),
            "schema_version": "calendar_tour_inspection.v1",
            "run_id": current.run_id,
            "branch_id": current.branch_id,
            "saved_head_revision_id": revision.revision_id,
            "draft_version": draft.draft_version,
            "run_calendar": sources.execution_calendar.to_metadata(),
            "saved_completed_seasons": completed_season_indices(signed.tour, saved_final_closure(revision.payload, current.branch_id, getattr(sources, "final_closure", None))),
            "checkpoint_fingerprint": current.checkpoint_fingerprint,
            "tour_fingerprint": tour_fingerprint(current, draft.draft_version),
            "saved": current == signed and draft.status == "clean",
            "sporting_saved": current.checkpoint_fingerprint
            == signed.checkpoint_fingerprint,
            "post_birth_competition_supported": True,
            "can_initialize": False,
            "players": [
                {
                    "player_id": p.player_id,
                    "name": names.get(p.player_id, p.player_id),
                    "age": life[p.player_id].age,
                    "status": life[p.player_id].status,
                    "form": p.current_form,
                    "sharpness": p.match_sharpness,
                    "fatigue": p.long_term_fatigue,
                }
                for p in current.players
            ],
            "state": current.tour.model_dump(mode="json"),
            "edition_evidence": evidence,
            "next_slot": slot_inspection(current.tour, ForkCompetitionView(current, sources.checkpoint)),
            "contributions": contributions,
            "transition_blockers": transition_blockers(
                current, calendar=sources.execution_calendar
            ),
            "season_transition_blockers": transition_blockers(
                current, season=True, calendar=sources.execution_calendar
            ),
        }

    def player(self, *, run_id, branch_id, player_id):
        with self.repository._session_factory() as session, native_read_proof_scope():
            session.execute(text("BEGIN"))
            _, _, revision, _, _, current, _, _ = self._context(
                session, run_id, branch_id
            )
            record = next(
                (p for p in current.players if p.player_id == player_id), None
            )
            if record is None:
                raise ValueError(
                    "Player does not belong to the current native fork population"
                )
            identity = next(
                p for p in current.lifecycle.players if p.player_id == player_id
            )
            return {
                "run_id": run_id,
                "branch_id": branch_id,
                "saved_head_revision_id": revision.revision_id,
                "checkpoint_fingerprint": current.checkpoint_fingerprint,
                "record": record.model_dump(mode="json"),
                "lifecycle": identity.model_dump(mode="json"),
            }

    def preview(self, *, run_id, branch_id, command):
        with self.repository._session_factory() as session, native_read_proof_scope():
            session.execute(text("BEGIN"))
            _, _, revision, draft, signed, current, _, sources = self._context(
                session, run_id, branch_id
            )
            from beta_engine.application.native_full_simulation_closure import (
                saved_native_closure,
            )
            if saved_native_closure(revision.payload, branch_id=branch_id, calendar=sources.execution_calendar):
                raise ValueError("This native Branch is completed; extend the Run before new Tour work")
            if draft.status == "dirty" and draft.draft_schema_version != DRAFT_SCHEMA:
                raise ValueError(
                    "Save the other Working Draft change before a Tour command"
                )
            return prepare_command(
                current,
                command,
                sources,
                saved_head=revision.revision_id,
                draft_version=draft.draft_version,
                is_saved=current == signed,
            )[0]

    def execute(self, *, run_id, branch_id, request):
        with (
            self.repository._session_factory.begin() as session,
            native_read_proof_scope(),
        ):
            session.execute(text("BEGIN IMMEDIATE"))
            _, _, revision, draft, signed, current, _, sources = self._context(
                session, run_id, branch_id
            )
            for event in current.journal:
                if event.request["command"]["command_id"] == request.command.command_id:
                    if event.request != request.model_dump(mode="json"):
                        raise ValueError(
                            "Command ID already has another request or confirmation"
                        )
                    return event.result
            from beta_engine.application.native_full_simulation_closure import (
                saved_native_closure,
            )
            if saved_native_closure(revision.payload, branch_id=branch_id, calendar=sources.execution_calendar):
                raise ValueError("This native Branch is completed; extend the Run before new Tour work")
            if draft.status == "dirty" and draft.draft_schema_version != DRAFT_SCHEMA:
                raise ValueError(
                    "Save the other Working Draft change before a Tour command"
                )
            preview, candidate, result = prepare_command(
                current,
                request.command,
                sources,
                saved_head=revision.revision_id,
                draft_version=draft.draft_version,
                is_saved=current == signed,
            )
            if preview["preview_fingerprint"] != request.expected_preview_fingerprint:
                raise ValueError(
                    "Native fork confirmation is stale; inspect and review again"
                )
            successor = commit_prepared(
                current, candidate, request, result, draft.draft_version
            )
            draft.draft_schema_version, draft.status, draft.change_count = (
                DRAFT_SCHEMA,
                "dirty",
                1,
            )
            draft.changes_json = canonical_json(
                [{"kind": KEY, "component": component(successor)}]
            )
            draft.draft_version += 1
            session.flush()
            from beta_engine.application.calendar_tour_service import (
                _fault_injection_point,
            )

            _fault_injection_point("after_tour_write")
            return result

    def _append(
        self,
        session,
        ctx,
        runtime,
        *,
        revision_id,
        audit_event_id,
        kind="native_fork_save",
        payload=None,
        summary=None,
        viewer_id=None,
    ):
        run, branch, previous, draft = ctx[:4]
        payload = deepcopy(payload or previous.payload)
        # Restore changes this timeline's state, never the Run-wide time basis or
        # an already committed strict horizon extension. Old target bytes stay exact.
        payload["run"]["run_calendar"] = deepcopy(
            previous.payload["run"]["run_calendar"]
        )
        payload["run"]["timeline_end_season"] = previous.payload["run"][
            "timeline_end_season"
        ]
        payload["content"][KEY] = component(runtime)
        if viewer_id is not None:
            payload["run"]["viewer_branch_id"] = viewer_id
        details = {
            "revision_id": revision_id,
            "run_id": run.run_id,
            "branch_id": branch.branch_id,
            "sequence": previous.sequence + 1,
            "parent_revision_id": previous.revision_id,
            "kind": kind,
            "payload_schema_version": SAVED_SCHEMA,
        }
        summary = summary or {"kind": kind, "runtime_fingerprint": runtime.fingerprint}
        row = BranchSavedRevisionModel(
            **details,
            content_hash_algorithm="sha256",
            content_hash=saved_revision_content_hash(
                **details, payload=payload, change_summary=summary
            ),
            payload_json=canonical_json(payload),
            change_summary_json=canonical_json(summary),
        )
        session.add(row)
        branch.saved_head_revision_id = revision_id
        draft.base_revision_id, draft.status, draft.change_count, draft.changes_json = (
            revision_id,
            "clean",
            0,
            "[]",
        )
        draft.draft_schema_version = "saved_revision_fork_working_draft_v1"
        draft.draft_version += 1
        audit = BranchRevisionAuditEventModel(
            audit_event_id=audit_event_id,
            run_id=run.run_id,
            branch_id=branch.branch_id,
            saved_revision_id=revision_id,
            event_kind=kind,
            payload_json=canonical_json(summary),
        )
        session.add(audit)
        session.flush()
        # Never carry an operation's pre-write proof over an altered row.
        record = self.repository._validated_saved_revision_in_session(
            session=session, model=row
        )
        return record, audit

    def save(
        self,
        *,
        run_id,
        branch_id,
        expected_draft_version,
        expected_calendar_tour_fingerprint=None,
        revision_id,
        audit_event_id,
        **kwargs,
    ):
        from beta_engine.infrastructure.db.repositories import (
            BranchRevisionAuditEventRecord,
            ViewerBranchSaveResult,
        )

        with (
            self.repository._session_factory.begin() as session,
            native_read_proof_scope(),
        ):
            session.execute(text("BEGIN IMMEDIATE"))
            ctx = self._context(session, run_id, branch_id)
            run, _branch, previous, draft, _signed, current = ctx[:6]
            if (
                kwargs.get("expected_saved_head_revision_id") is not None
                and previous.revision_id != kwargs["expected_saved_head_revision_id"]
            ):
                raise ValueError("Native fork Save expected Saved HEAD is stale")
            if draft.draft_version != expected_draft_version:
                raise ValueError("Native fork Save draft version is stale")
            if draft.status != "dirty":
                raise ValueError("Native fork has no Working Draft changes to Save")
            if (
                expected_calendar_tour_fingerprint is not None
                and expected_calendar_tour_fingerprint
                != tour_fingerprint(current, draft.draft_version)
            ):
                raise ValueError("Native fork Save fingerprint is stale")
            before = run.official_branch_id
            viewer_id = before
            if draft.draft_schema_version == "run_working_draft_v1":
                from beta_engine.domain.run_revisions import (
                    viewer_branch_id_from_changes,
                )

                viewer_id = viewer_branch_id_from_changes(
                    json.loads(draft.changes_json)
                )
                owner = session.get(RunBranchModel, viewer_id)
                if (
                    owner is None
                    or owner.run_id != run_id
                    or owner.status != "active"
                    or owner.read_only
                ):
                    raise ValueError("Selected Viewer Branch is unavailable")
                run.official_branch_id = viewer_id
            record, audit = self._append(
                session,
                ctx,
                current,
                revision_id=revision_id,
                audit_event_id=audit_event_id,
                viewer_id=viewer_id,
                summary={
                    "kind": "native_fork_save",
                    "runtime_fingerprint": current.fingerprint,
                    "input_draft_version": expected_draft_version,
                    "input_tour_fingerprint": expected_calendar_tour_fingerprint,
                },
            )
            working = self.repository._viewer_branch_working_draft_in_session(
                session=session, run_id=run_id, branch_id=branch_id
            )
            return ViewerBranchSaveResult(
                run_id,
                branch_id,
                before,
                viewer_id,
                record,
                working,
                BranchRevisionAuditEventRecord(
                    audit.audit_event_id,
                    run_id,
                    branch_id,
                    record.revision_id,
                    audit.event_kind,
                    json.loads(audit.payload_json),
                    audit.created_at,
                ),
            )

    def _restore_review(self, session, run_id, branch_id, target_id, ctx):
        from beta_engine.infrastructure.db.repositories import (
            BranchSavedRevisionRestorePreflight,
            SavedRevisionRestorePreflightBlocker,
        )

        run, branch, previous, draft = ctx[:4]
        lineage = self.repository._validated_branch_revision_lineage_in_session(
            session=session, branch=branch, payload_revision_ids=frozenset({target_id})
        )
        target = next((r for r in lineage if r.revision_id == target_id), None)
        blockers = []
        from beta_engine.infrastructure.db.full_simulation_command_scope import (
            pending_native_task_parents,
        )
        if pending_native_task_parents(session, run_id=run_id, branch_id=branch_id):
            blockers.append(SavedRevisionRestorePreflightBlocker(
                "pending_native_full_simulation", "Stop the pending native Full Simulation before restoring this Branch"
            ))
        if (
            target is None
            or target.branch_id != branch_id
            or target.payload_schema_version != SAVED_SCHEMA
        ):
            blockers.append(
                SavedRevisionRestorePreflightBlocker(
                    "native_target_not_owned",
                    "Choose a Saved Revision owned by this native fork",
                )
            )
        if draft.status != "clean":
            blockers.append(
                SavedRevisionRestorePreflightBlocker(
                    "dirty_working_draft",
                    "Save or discard the Working Draft before restore",
                )
            )
        viewer = (
            saved_viewer_branch_id(target.payload)
            if target and target.payload
            else None
        )
        owner = session.get(RunBranchModel, viewer) if viewer else None
        if (
            owner is None
            or owner.run_id != run_id
            or owner.status != "active"
            or owner.read_only
        ):
            blockers.append(
                SavedRevisionRestorePreflightBlocker(
                    "target_viewer_branch_unavailable",
                    "Target Saved Viewer Branch is unavailable",
                )
            )
        if (
            target
            and target.branch_id == branch_id
            and load_runtime(target.payload).root_saved_revision_id
            != ctx[4].root_saved_revision_id
        ):
            blockers.append(
                SavedRevisionRestorePreflightBlocker(
                    "native_root_differs", "Target has another native fork root"
                )
            )
        return BranchSavedRevisionRestorePreflight(
            run_id,
            branch_id,
            target_id,
            previous.revision_id,
            draft.draft_version,
            run.official_branch_id,
            viewer,
            not blockers,
            tuple(blockers),
        ), target

    def preview_restore(self, *, run_id, branch_id, target_saved_revision_id):
        with self.repository._session_factory() as session, native_read_proof_scope():
            session.execute(text("BEGIN"))
            ctx = self._context(session, run_id, branch_id)
            return self._restore_review(
                session, run_id, branch_id, target_saved_revision_id, ctx
            )[0]

    def restore(
        self,
        *,
        run_id,
        branch_id,
        target_saved_revision_id,
        expected_head_saved_revision_id,
        expected_draft_version,
        expected_current_viewer_branch_id,
        checkpoint_id,
        restore_saved_revision_id,
        audit_event_id,
    ):
        from beta_engine.domain.run_revisions import (
            saved_revision_checkpoint_content_hash,
        )
        from beta_engine.infrastructure.db.models import (
            BranchSavedRevisionCheckpointModel,
        )
        from beta_engine.infrastructure.db.repositories import (
            BranchRevisionAuditEventRecord,
            BranchSavedRevisionRestoreResult,
            SavedRevisionRestoreConflictError,
        )

        with (
            self.repository._session_factory.begin() as session,
            native_read_proof_scope(),
        ):
            session.execute(text("BEGIN IMMEDIATE"))
            ctx = self._context(session, run_id, branch_id)
            run, _, previous, draft = ctx[:4]
            if (previous.revision_id, draft.draft_version, run.official_branch_id) != (
                expected_head_saved_revision_id,
                expected_draft_version,
                expected_current_viewer_branch_id,
            ):
                raise SavedRevisionRestoreConflictError(
                    "Native fork restore review is stale"
                )
            review, target = self._restore_review(
                session, run_id, branch_id, target_saved_revision_id, ctx
            )
            if not review.can_restore:
                raise SavedRevisionRestoreConflictError(
                    "; ".join(b.message for b in review.blockers)
                )
            old_viewer = run.official_branch_id
            fields = {
                "checkpoint_id": checkpoint_id,
                "run_id": run_id,
                "branch_id": branch_id,
                "saved_revision_id": previous.revision_id,
                "target_saved_revision_id": target_saved_revision_id,
                "restore_saved_revision_id": restore_saved_revision_id,
                "kind": "pre_restore_saved_revision",
                "draft_id": draft.draft_id,
                "draft_version": draft.draft_version,
                "viewer_branch_id": old_viewer,
            }
            checkpoint = BranchSavedRevisionCheckpointModel(
                **fields,
                content_hash_algorithm="sha256",
                content_hash=saved_revision_checkpoint_content_hash(**fields),
            )
            session.add(checkpoint)
            run.official_branch_id = review.target_viewer_branch_id
            record, audit = self._append(
                session,
                ctx,
                load_runtime(target.payload),
                revision_id=restore_saved_revision_id,
                audit_event_id=audit_event_id,
                kind="branch_restore",
                payload=target.payload,
                summary={
                    "kind": "branch_restore",
                    "previous_head_revision_id": previous.revision_id,
                    "target_saved_revision_id": target_saved_revision_id,
                    "previous_viewer_branch_id": old_viewer,
                    "restored_viewer_branch_id": review.target_viewer_branch_id,
                },
            )
            working = self.repository._viewer_branch_working_draft_in_session(
                session=session, run_id=run_id, branch_id=branch_id
            )
            return BranchSavedRevisionRestoreResult(
                run_id,
                branch_id,
                previous.revision_id,
                target_saved_revision_id,
                old_viewer,
                review.target_viewer_branch_id,
                self.repository._to_branch_saved_revision_checkpoint(checkpoint),
                record,
                working,
                BranchRevisionAuditEventRecord(
                    audit.audit_event_id,
                    run_id,
                    branch_id,
                    record.revision_id,
                    audit.event_kind,
                    json.loads(audit.payload_json),
                    audit.created_at,
                ),
            )

    def replay(self, *, run_id, branch_id, match_id):
        from beta_engine.core import DeterministicRng
        from beta_engine.domain.matches.match_engine import MatchEngine
        from beta_engine.domain.native_fork_runtime import ForkCompetitionView
        from beta_engine.domain.run_packages import canonical_hash

        with self.repository._session_factory() as session, native_read_proof_scope():
            session.execute(text("BEGIN"))
            _, _, _, _, signed, current, _, sources = self._context(
                session, run_id, branch_id
            )
            if current != signed:
                raise ValueError("Save native fork before historical replay")
            matches = (
                tuple(sources.opening.matches)
                + ForkCompetitionView(signed, sources.checkpoint).played_continuations
            )
            entry = next(
                (m for m in matches if m.input_context.match_id == match_id), None
            )
            if entry is None:
                raise KeyError("Native fork historical match was not found")
            result = MatchEngine(DeterministicRng(entry.seed)).simulate(
                entry.input_context,
                log_anchor_hash=entry.log_anchor_hash,
                effective_match_health=entry.effective_health,
            )
            if result.model_dump(mode="json") != entry.result.model_dump(mode="json"):
                raise ValueError(
                    "Native fork historical replay differs from actual MatchEngine"
                )
            return {
                "match_id": match_id,
                "fingerprint": getattr(
                    entry, "fingerprint", canonical_hash(entry.model_dump(mode="json"))
                ),
                "winner_player_id": result.winner_player_id,
                "rally_count": len(result.rally_log.events),
                "exact_replay": True,
                "historical_owner_scope": "native_fork_original_or_target",
                "source_branch_id": getattr(
                    entry, "branch_id", sources.opening.branch_id
                ),
            }

    def readiness(self, *, run_id, branch_id):
        from beta_engine.domain.calendar.run_week_position import RunWeekPosition
        from beta_engine.domain.players.calendar_prospect_birth import (
            build_calendar_prospect_birth_event,
        )
        from beta_engine.domain.run_packages import canonical_hash

        with self.repository._session_factory() as session, native_read_proof_scope():
            session.execute(text("BEGIN"))
            _, _, revision, draft, _signed, current, _, sources = self._context(
                session, run_id, branch_id
            )
            clock = sources.execution_calendar
            season = current.week.week == clock.weeks_per_year
            blockers = transition_blockers(current, season=season, calendar=clock)
            if draft.status != "clean":
                blockers.append("manual_save_required")
            target, due = None, []
            if current.week.ordinal + 1 < clock.weeks_per_year * clock.season_count:
                p = clock.position_at_ordinal(current.week.ordinal + 1)
                target = RunWeekPosition(
                    calendar=clock, season_index=p.season_index, week=p.season_week
                )
                if sources.prospects:
                    source = sources.prospects.for_week(target.ordinal)
                    event = build_calendar_prospect_birth_event(
                        predecessor=current.lifecycle,
                        target=target,
                        source=source,
                        world_package_id=sources.world.world_package_id,
                    )
                    names = {
                        r["prospect_id"]: r.get("display_name") or r["prospect_id"]
                        for r in source.records
                    }
                    due = [
                        {
                            "player_id": b.player_id,
                            "display_name": names[b.player_id],
                            "country_code": b.country_code,
                        }
                        for b in event.births
                    ]
            body = {
                "schema_version": "native_tour_transition_readiness.v2",
                "run_id": run_id,
                "branch_id": branch_id,
                "saved_head_revision_id": revision.revision_id,
                "checkpoint_fingerprint": current.checkpoint_fingerprint,
                "tour_fingerprint": tour_fingerprint(current, draft.draft_version),
                "source_fingerprint": sources.prospects.for_week(
                    target.ordinal
                ).fingerprint
                if sources.prospects and target
                else None,
                "health_fingerprint": current.health.fingerprint,
                "run_calendar": clock.to_metadata(),
                "completed_week": current.week.model_dump(mode="json"),
                "target_week": target.model_dump(mode="json") if target else None,
                "action": "season-transition" if season else "transition",
                "can_preview_transition": not blockers,
                "blockers": sorted(set(blockers)),
                "source_problems": [],
                "due": due,
                "due_count": len(due),
                "admitted_population_count": len(current.players)
                - len(sources.world.players),
                "current_scope": "native_competition",
                "target_scope": "native_competition",
                "post_birth_competition_supported": True,
                "source_epoch_changes_supported": False,
                "command_preview_required": True,
                "explicit_confirmation_required": True,
                "manual_save_required": True,
                "simulation_started": False,
            }
            body["readiness_fingerprint"] = canonical_hash(body)
            return body

    def report(self, *, run_id, branch_id, kind, **options):

        from beta_engine.application.calendar_tour_season_summary import (
            compare_completed_seasons,
            saved_final_closure,
        )
        from beta_engine.application.calendar_tour_signed_records import (
            signed_tour_records,
        )

        with self.repository._session_factory() as session, native_read_proof_scope():
            session.execute(text("BEGIN"))
            _, _, revision, _, _signed, _, _, _sources = self._context(
                session, run_id, branch_id
            )
            from beta_engine.application.native_fork_publication import (
                publication_inputs,
            )

            state, world = publication_inputs(self.repository, session, revision)
            if kind == "records":
                return {
                    **signed_tour_records(state, world, closure=saved_final_closure(revision.payload, branch_id, getattr(state, "inherited_final_closure", None)), **options),
                    "schema_version": "calendar_tour_signed_records_response.v1",
                    "saved_head_revision_id": revision.revision_id,
                }
            return {
                "schema_version": "calendar_tour_season_comparison.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "saved_head_revision_id": revision.revision_id,
                **compare_completed_seasons(state, world, closure=saved_final_closure(revision.payload, branch_id, getattr(state, "inherited_final_closure", None)), **options),
            }
