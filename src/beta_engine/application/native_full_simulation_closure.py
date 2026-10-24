"""Reviewed native terminal closure: preview, approval, then explicit manual Save.

No next week, development, lifecycle or Official publication is fabricated.
The closing-only ranking uses the outgoing policy at the boundary ordinal.
"""

from copy import deepcopy
from types import SimpleNamespace

from sqlalchemy import text

from beta_engine.application.native_fork_runtime_reducer import source_inputs
from beta_engine.application.native_full_simulation import (
    NativeFullSimulationDriver,
    NativeWeek,
    _write,
    native_context,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_season_closing import (
    calculate_calendar_season_closing,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.run_revisions import canonical_json, saved_revision_content_hash
from beta_engine.domain.tournaments.calendar_tour import (
    edition_results,
    effective_policy,
    ranking_players,
)
from beta_engine.infrastructure.db.models import (
    BranchRevisionAuditEventModel,
    BranchSavedRevisionModel,
    FullSimulationExecutionLeaseModel,
)

KEY = "native_branch_closures"
KIND = "native_final_run_closure"


def _fault_injection_point(name):
    """Late transaction failure seam, exercised by real SQLite acceptance."""


def closure_facts(repository, session, revision, *, final=True):
    sources = source_inputs(revision, repository, session)
    state, checkpoint = sources.tour, sources.checkpoint
    clock = RunCalendar.from_metadata(revision.payload["run"]["run_calendar"])
    week = NativeWeek(season_index=state.week.season_index, week=state.week.week)
    if week.week != clock.weeks_per_year or (final and week.ordinal(clock) != clock.weeks_per_year * clock.season_count - 1):
        raise ValueError("Native final closure requires the actual Run horizon")
    if any(not a.result_confirmed and a.edition.week.ordinal <= state.week.ordinal for a in state.editions):
        raise ValueError("Native final closure requires all Editions to be terminal")
    events = {t.tournament_id: t for t in checkpoint.tournaments}
    results = tuple(r for a in state.editions if a.result_confirmed for r in edition_results(a, events[a.edition.edition_id]))
    submissions = tuple(s for a in state.editions for s in a.submissions)
    if state.schema_version == "native_fork_tour.v1":
        # Source submissions retain their original identity. This local player
        # projection uses the authenticated independent Branch's current owner.
        submissions = tuple(SimpleNamespace(**{**s.model_dump(), "run_id": state.run_id, "branch_id": state.branch_id,
            "submission_week": s.submission_week, "decision_position": s.decision_position}) for s in submissions)
    retired = tuple(p.player_id for p in sources.lifecycle.players if p.status == "retired")
    ranking = calculate_calendar_season_closing(calendar=clock, completed_week=week,
        policy=effective_policy(state, state.week).ranking,
        players=ranking_players(state, submissions, retired=retired),
        results=results, previous=state.rankings[-1],
        # Only the completely authenticated source_inputs graph may introduce
        # inherited source owners; callers cannot supply this through an API.
        inherited_terminal_sources=tuple((r.source_fingerprint, r.run_id, r.branch_id)
            for r in results if getattr(r, "schema_version", None) == "calendar_terminal_edition_result.v1"))
    season_editions = tuple(a for a in state.editions if a.edition.week.season_index == week.season_index)
    summary = {
        "schema_version": "native_final_season_summary.v1", "season_index": week.season_index,
        "edition_ids": [a.edition.edition_id for a in season_editions],
        "played_match_count": sum(len(events[a.edition.edition_id].matches) for a in season_editions),
        "awarded_points": sum(r.points for r in results if r.completed_week.season_index == week.season_index),
        "closing_ranking_fingerprint": ranking["fingerprint"],
    }
    return {
        "schema_version": "native_final_run_closure.v1" if final else "native_season_closure.v1", "run_id": revision.run_id,
        "branch_id": revision.branch_id, "execution_calendar": clock.to_metadata(),
        "completed_week": week.model_dump(mode="json"),
        "source_revision_id": revision.revision_id, "source_content_hash": revision.content_hash,
        "source_state_fingerprint": canonical_hash(revision.payload["content"]),
        "checkpoint_fingerprint": checkpoint.fingerprint,
        "closing_ranking": ranking, "season_summary": summary,
        "season_summary_fingerprint": canonical_hash(summary),
    }


def saved_native_closure(payload, *, branch_id, calendar):
    closures = payload.get("run", {}).get(KEY, {})
    if not isinstance(closures, dict):
        raise TypeError("Native closure history is malformed")
    marker = closures.get(branch_id)
    if marker is None:
        return None
    if (not isinstance(marker, dict)
        or marker.get("fingerprint") != canonical_hash({k: v for k, v in marker.items() if k != "fingerprint"})
        or marker.get("branch_id") != branch_id or marker.get("run_id") != payload["run"]["run_id"]):
        raise ValueError("Saved native closure identity/fingerprint is corrupt")
    original = RunCalendar.from_metadata(marker["execution_calendar"])
    if (original.weeks_per_year, original.season_start_year_week, original.start_year) != (calendar.weeks_per_year, calendar.season_start_year_week, calendar.start_year) or original.season_count > calendar.season_count:
        raise ValueError("Saved native closure calendar is incompatible")
    if marker["completed_week"] != {"season_index": original.season_count - 1, "week": original.weeks_per_year}:
        raise ValueError("Saved native closure has a false terminal week")
    return marker if original == calendar else None


def verify_saved_native_closure(repository, session, revision):
    """Recompute terminal facts from actual immutable ancestors, even after rehash."""
    markers = revision.payload.get("run", {}).get(KEY, {})
    if not isinstance(markers, dict):
        raise TypeError("Malformed Saved native closure history")
    marker = markers.get(revision.branch_id)
    if marker is None:
        return
    clock = RunCalendar.from_metadata(revision.payload["run"]["run_calendar"])
    saved_native_closure(revision.payload, branch_id=revision.branch_id, calendar=clock)
    source_id = marker["source_revision_id"]
    ancestor_id = revision.parent_revision_id
    seen = set()
    while ancestor_id != source_id:
        if ancestor_id is None or ancestor_id in seen:
            raise ValueError("Native closure source is not reachable ancestry")
        seen.add(ancestor_id)
        ancestor = session.get(BranchSavedRevisionModel, ancestor_id)
        if ancestor is None or ancestor.run_id != revision.run_id:
            raise ValueError("Native closure ancestry is missing")
        from beta_engine.application.final_season_transition import _revision_payload
        _revision_payload(ancestor)
        ancestor_id = ancestor.parent_revision_id
    source_row = session.get(BranchSavedRevisionModel, source_id)
    if source_row is None or source_row.run_id != revision.run_id or source_row.branch_id != revision.branch_id:
        raise ValueError("Native closure source identity is corrupt")
    source = repository._validated_saved_revision_in_session(session=session, model=source_row)
    facts = closure_facts(repository, session, source)
    if any(marker.get(k) != v for k, v in facts.items()):
        raise ValueError("Native closure differs from actual Saved sporting/ranking facts")


class NativeFullSimulationClosureService:
    def __init__(self, repository):
        self.repository = repository
        self.driver = NativeFullSimulationDriver(repository)

    def _review(self, session, command):
        row, payload = self.driver._parent(session, command)
        if row.status != "pending" or command.target_week is not None:
            raise ValueError("Final closure requires a pending original Run-end task")
        ctx = native_context(self.repository, session, command.run_id, command.branch_id)
        if not ctx["saved"] or ctx["calendar"].to_metadata() != command.execution_calendar:
            raise ValueError("Final closure requires an unchanged original horizon and a clean manual Save")
        blockers = [b for b in ctx["blockers"] if b != "season_transition_horizon_exhausted"]
        if blockers:
            raise ValueError("Native final closure blocked: " + ", ".join(blockers))
        facts = closure_facts(self.repository, session, ctx["revision"])
        body = {**facts, "parent_command_id": command.command_id,
            "expected_position_fingerprint": ctx["position_fingerprint"]}
        return row, payload, ctx, {**body, "review_fingerprint": canonical_hash(body)}

    def review(self, command):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            return self._review(session, command)[3]

    @staticmethod
    def _idle(session, command):
        import time
        lease = session.get(FullSimulationExecutionLeaseModel, "all_runs")
        if lease and lease.run_id == command.run_id and lease.branch_id == command.branch_id and lease.expires_at_unix > int(time.time()):
            raise ValueError("Wait for the native worker to release its lease")

    def approve(self, command, request):
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._idle(session, command)
            row, payload = self.driver._parent(session, command)
            prior = payload.get("closure_approval")
            if prior and prior["request"]["request_id"] == request["request_id"]:
                if prior["request"] != request:
                    raise ValueError("Closure approval request ID was reused")
                return prior
            _, _, _, review = self._review(session, command)
            if request["review_fingerprint"] != review["review_fingerprint"]:
                raise ValueError("Native final closure review is stale")
            approval = {"request": request, "review": review}
            payload["closure_approval"] = approval
            _write(row, payload)
            return approval

    def save(self, command, request):
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._idle(session, command)
            row, payload = self.driver._parent(session, command)
            prior = payload.get("closure_save")
            if prior:
                if prior["request"] != request:
                    raise ValueError("Final closure was already Saved with another request")
                source = session.get(BranchSavedRevisionModel, prior["revision_id"])
                self.repository._validated_saved_revision_in_session(session=session, model=source)
                return prior
            _, _, ctx, review = self._review(session, command)
            approval = payload.get("closure_approval")
            if not approval or approval["review"] != review or request["review_fingerprint"] != review["review_fingerprint"]:
                raise ValueError("Explicit current closure approval is required before manual final Save")
            facts = closure_facts(self.repository, session, ctx["revision"])
            marker = {**facts, "approval": approval["request"], "save": request,
                "parent_command_id": command.command_id}
            marker["fingerprint"] = canonical_hash(marker)
            previous = ctx["revision"]
            saved_payload = deepcopy(previous.payload)
            saved_payload["run"].setdefault(KEY, {})[command.branch_id] = marker
            saved_payload["run"]["status"] = "completed"
            revision_id = "native-close-" + canonical_hash({"command": command.model_dump(mode="json"), "save": request})[:48]
            details = {"revision_id": revision_id, "run_id": command.run_id, "branch_id": command.branch_id,
                "sequence": previous.sequence + 1, "parent_revision_id": previous.revision_id,
                "kind": KIND, "payload_schema_version": previous.payload_schema_version}
            changes = {"kind": KIND, "marker_fingerprint": marker["fingerprint"],
                "operator_label": request["operator_label"], "audit_reason": request["audit_reason"]}
            saved_row = BranchSavedRevisionModel(**details, content_hash_algorithm="sha256",
                content_hash=saved_revision_content_hash(**details, payload=saved_payload, change_summary=changes),
                payload_json=canonical_json(saved_payload), change_summary_json=canonical_json(changes))
            session.add(saved_row)
            session.add(BranchRevisionAuditEventModel(audit_event_id=revision_id + ":audit",
                run_id=command.run_id, branch_id=command.branch_id, saved_revision_id=revision_id,
                event_kind=KIND, payload_json=canonical_json(changes)))
            ctx["branch"].saved_head_revision_id = revision_id
            ctx["run"].status = "completed"
            draft = ctx["draft"]
            draft.base_revision_id, draft.status, draft.change_count, draft.changes_json = revision_id, "clean", 0, "[]"
            draft.draft_version += 1
            result = {"schema_version": "native_final_run_closure_save.v1", "revision_id": revision_id,
                "marker_fingerprint": marker["fingerprint"], "request": request}
            payload["closure_save"] = result
            _write(row, payload)
            session.flush()
            self.repository._validated_saved_revision_in_session(session=session, model=saved_row)
            _fault_injection_point("after_native_final_closure_save")
            return result
