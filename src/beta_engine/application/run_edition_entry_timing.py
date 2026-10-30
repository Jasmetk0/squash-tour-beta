"""Reviewed Run Calendar edits plus the existing immutable ranking binding.

Timing lives in the Run-owned Calendar event, not a second registry. Confirm
stages the normal Package edit and optional published-ranking adoption in one
SQLite transaction; the ordinary Working Draft Save remains explicit.
"""

from copy import deepcopy
from dataclasses import dataclass
import json

from sqlalchemy import text, select

from beta_engine.application.calendar_package_run_adapter import (
    CALENDAR_EVENT_ENTITY_KIND, CalendarPackageRunAdapter,
)
from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar, require_supported_legacy_sporting_calendar,
)
from beta_engine.application.run_package_service import (
    RunPackageService, RunPackageConflictError, RunPackageNotFoundError,
    _load_receipt_result, _require_writable, _require_component_authority,
)
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import RankingWeek, load_official_ranking_snapshot
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.edition_entry_timing import (
    EditionEntryTiming, resolve_entry_timing, entry_window_at,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel, PublishedOfficialRankingModel,
    RunPackageApplicationReceiptModel,
)
from beta_engine.infrastructure.db.run_package_state import get_run_package_state
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


TIMING_KEY = "entry_timing"


@dataclass(slots=True)
class RunEditionEntryTimingService:
    packages: RunPackageService

    def _context(self, session, run_id, branch_id, package_id, event_id):
        run, branch, draft = self.packages._context(session, run_id, branch_id)
        clock = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
        state = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
        if state is None:
            raise RunPackageNotFoundError("Entry timing requires a Run-owned Calendar Package")
        projection = CalendarPackageRunAdapter.project_calendar(state, package_id=package_id)
        matches = [e for e in state.entities if e.entity_kind == CALENDAR_EVENT_ENTITY_KIND
                   and e.source_entity_id == event_id]
        if len(matches) != 1 or matches[0].source_package_id != package_id:
            raise ValueError("Entry timing requires one unambiguous Run-owned Edition identity")
        event = next((e for e in projection.calendar.events if e.event_id == event_id), None)
        if event is None:
            raise RunPackageNotFoundError("Run Calendar Edition was not found")
        try:
            year, next_year = map(int, projection.season.split("/"))
        except (ValueError, TypeError) as exc:
            raise ValueError("Entry timing requires an explicit year/year season") from exc
        if next_year != year + 1:
            raise ValueError("Entry timing season is not consecutive")
        play = RunWeekPosition(calendar=clock, season_index=year - clock.start_year,
                               week=event.start_season_week)
        return run, branch, draft, state, matches[0], event, play

    def _preview(self, session, *, run_id, branch_id, package_id, event_id, timing):
        run, branch, draft, state, entity, event, play = self._context(
            session, run_id, branch_id, package_id, event_id)
        resolved = resolve_entry_timing(timing, play)
        configuration = timing.model_dump(mode="json")
        old = event.event_level_overrides.get(TIMING_KEY)
        if TIMING_KEY in event.event_level_overrides:
            # A malformed saved input is not silently normalized away by editing.
            old_timing = EditionEntryTiming.model_validate_json(json.dumps(old))
            resolve_entry_timing(old_timing, play)
            old = old_timing.model_dump(mode="json")
        blockers = []
        writable = True
        try:
            _require_writable(run, branch)
            _require_component_authority(session, branch)
        except RunPackageConflictError as exc:
            writable = False
            blockers.append({"code": "scope_not_writable", "detail": str(exc)})
        supported = True
        try:
            require_supported_legacy_sporting_calendar(
                session, run_id=run_id, branch_id=branch_id, operation="Edition Entry ranking binding")
        except ValueError as exc:
            supported = False
            blockers.append({"code": "unsupported_execution", "detail": str(exc)})

        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id)) if supported else None
        current = None
        if world is not None:
            current = RunWeekPosition(calendar=play.calendar,
                                      season_index=world.current_ordinal // play.calendar.weeks_per_year,
                                      week=world.current_ordinal % play.calendar.weeks_per_year + 1)
            head = session.scalar(select(PublishedOfficialRankingModel).where(
                PublishedOfficialRankingModel.run_id == run_id,
                PublishedOfficialRankingModel.branch_id == branch_id,
            ).order_by(PublishedOfficialRankingModel.week_ordinal.desc()).limit(1))
            if head is None or head.week_ordinal != world.current_ordinal or head.snapshot_fingerprint != world.ranking_fingerprint:
                raise ValueError("Authoritative world head differs from published ranking")
            load_official_ranking_snapshot(head.payload_json, expected_fingerprint=head.snapshot_fingerprint,
                run_id=run_id, branch_id=branch_id,
                week=RankingWeek(season_index=current.season_index, week=current.week))
        # Bind a missing snapshot later without changing an already opened plan.
        timing_locked = current is not None and current.ordinal >= min(
            resolved["main_open"].ordinal,
            EditionEntryTiming.model_validate_json(json.dumps(old)).main_open.ordinal if old else resolved["main_open"].ordinal,
        ) and old != configuration
        if timing_locked:
            blockers.append({"code": "entry_timing_locked", "detail": "An opened Entry process cannot be retimed by this preparation command"})

        publication = resolved["ranking_publication_week"]
        ranking = None
        existing = None
        if supported:
            store = TournamentRankingSnapshotAuthorityStore(session)
            existing = store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
            if publication is not None:
                week = RankingWeek(season_index=publication.season_index, week=publication.week)
                row = session.get(PublishedOfficialRankingModel, (run_id, branch_id, week.ordinal))
                if row is not None:
                    ranking = load_official_ranking_snapshot(row.payload_json,
                        expected_fingerprint=row.snapshot_fingerprint, run_id=run_id,
                        branch_id=branch_id, week=week)
        if publication is None:
            blockers.append({"code": "pre_start_ranking_required", "detail": "Main Closing has no preceding Run week; select an existing publication explicitly"})
        elif ranking is None and supported:
            blockers.append({"code": "ranking_publication_missing", "detail": "The exact required Official publication does not exist; no latest-ranking fallback is allowed"})
        ranking_conflict = existing is not None and (
            ranking is None or existing.ranking_snapshot_fingerprint != ranking.fingerprint)
        if ranking_conflict:
            blockers.append({"code": "ranking_binding_conflict", "detail": "This Edition already froze a different Tournament Ranking Snapshot"})
        if ranking is not None and (current is None or publication.ordinal > current.ordinal):
            blockers.append({"code": "ranking_not_yet_current", "detail": "Ranking binding requires a known authoritative position at or after publication"})
            ranking = None
        can_bind = supported and ranking is not None and not ranking_conflict
        # Missing future publications do not forbid saving a valid preparation plan.
        can_confirm = writable and not timing_locked and not ranking_conflict
        body = {
            "schema_version": "run_edition_entry_timing_preview.v1",
            "run_id": run_id, "branch_id": branch_id,
            "package_id": package_id, "event_id": event_id,
            "saved_head_revision_id": branch.saved_head_revision_id,
            "draft_version": draft.draft_version,
            "state_fingerprint": state.fingerprint,
            "edition_fingerprint": entity.content_fingerprint,
            "timing": configuration,
            "before": old,
            "resolved": {k: v.model_dump(mode="json") if isinstance(v, RunWeekPosition) else v for k, v in resolved.items()},
            "current_week": current.model_dump(mode="json") if current else None,
            "current_window": entry_window_at(resolved, current) if current else None,
            "ranking_snapshot_fingerprint": ranking.fingerprint if ranking else None,
            "ranking_authority_fingerprint": existing.fingerprint if existing else None,
            "ranking_will_be_bound": can_bind and existing is None,
            "ranking_binding_status": "bound" if can_bind and existing else "ready_for_explicit_confirmation" if can_bind else "missing_prerequisite",
            "configuration_state": "working_draft",
            "timing_and_ranking_ready": can_bind and existing is not None and old == configuration and not timing_locked and writable,
            "preflight_status": "unsupported_execution" if not supported else "blocked" if not can_confirm else "missing_content" if blockers else "ready",
            "automatic_eligibility_status": "not_implemented",
            "can_confirm_configuration": can_confirm,
            "blockers": blockers,
        }
        return body | {"preview_fingerprint": canonical_hash(body)}

    def preview(self, *, run_id, branch_id, package_id, event_id, timing):
        with self.packages.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            return self._preview(session, run_id=run_id, branch_id=branch_id,
                                 package_id=package_id, event_id=event_id, timing=timing)

    def inspect(self, *, run_id, branch_id, package_id, event_id):
        with self.packages.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            *_, event, play = self._context(session, run_id, branch_id, package_id, event_id)
            raw = event.event_level_overrides.get(TIMING_KEY)
            if TIMING_KEY not in event.event_level_overrides:
                return {"run_id": run_id, "branch_id": branch_id, "package_id": package_id,
                        "event_id": event_id, "timing": None, "preflight_status": "missing_content",
                        "blockers": [{"code": "entry_timing_missing", "detail": "Configure explicit Main opening week; no lead time is inferred from play week"}],
                        "automatic_eligibility_status": "not_implemented"}
            return self._preview(session, run_id=run_id, branch_id=branch_id, package_id=package_id,
                                 event_id=event_id, timing=EditionEntryTiming.model_validate_json(json.dumps(raw)))

    def confirm(self, *, run_id, branch_id, package_id, event_id, timing, command_id,
                expected_preview_fingerprint, operator_label, audit_reason):
        for label, value, limit in (("command_id", command_id, 128),
                                    ("operator_label", operator_label, 160),
                                    ("audit_reason", audit_reason, 1000)):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"Entry timing requires a nonempty bounded {label}")
        request = {"kind": "run_edition_entry_timing.v1", "run_id": run_id, "branch_id": branch_id,
                   "package_id": package_id, "event_id": event_id, "timing": timing.model_dump(mode="json"),
                   "expected_preview_fingerprint": expected_preview_fingerprint,
                   "operator_label": operator_label, "audit_reason": audit_reason}
        request_fp = canonical_hash(request)
        with self.packages.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            receipt = session.get(RunPackageApplicationReceiptModel, (run_id, branch_id, command_id))
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise RunPackageConflictError("Entry timing command ID was reused with another request")
                _load_receipt_result(receipt, run_id=run_id, branch_id=branch_id)
                result = json.loads(receipt.payload_json)
                digest = result.pop("receipt_fingerprint", None)
                if digest != canonical_hash(result) or result.get("request") != request:
                    raise RunPackageConflictError("Entry timing receipt is corrupt")
                result["receipt_fingerprint"] = digest
                return result | {"already_applied": True}
            preview = self._preview(session, run_id=run_id, branch_id=branch_id, package_id=package_id,
                                    event_id=event_id, timing=timing)
            if preview["preview_fingerprint"] != expected_preview_fingerprint:
                raise RunPackageConflictError("Entry timing preview changed since review")
            if not preview["can_confirm_configuration"]:
                raise RunPackageConflictError("Entry timing configuration is blocked")
            _, _, _, _, entity, _, _ = self._context(session, run_id, branch_id, package_id, event_id)
            payload = deepcopy(entity.payload)
            payload.setdefault("event_level_overrides", {})[TIMING_KEY] = timing.model_dump(mode="json")
            # The explicit review is part of the local Calendar edit even when
            # unchanged window inputs now bind a newly available publication.
            # It is provenance, not a second ranking authority. Ordinary Package
            # Save must see that effective edit and capture both components.
            payload["event_level_overrides"]["entry_timing_review"] = {
                "command_id": command_id, "operator_label": operator_label,
                "audit_reason": audit_reason,
            }
            state = self.packages._edit_entity_in_session(session, run_id=run_id, branch_id=branch_id,
                run_local_id=entity.run_local_id, payload=payload,
                expected_draft_version=preview["draft_version"], expected_state_fingerprint=preview["state_fingerprint"])
            authority = None
            if preview["ranking_will_be_bound"]:
                position = preview["resolved"]["ranking_publication_week"]
                authority = TournamentRankingSnapshotAuthorityStore(session).adopt(
                    run_id=run_id, branch_id=branch_id, event_id=event_id,
                    ranking_week=RankingWeek(season_index=position["season_index"], week=position["week"]),
                    command_id=command_id)
            result = {
                "command_id": command_id, "request_fingerprint": request_fp,
                "request": request, "preview": preview,
                "draft_version": preview["draft_version"] + 1,
                "state_fingerprint": state.fingerprint,
                "state": state.model_dump(mode="json"),
                "ranking_authority_fingerprint": authority.fingerprint if authority else preview["ranking_authority_fingerprint"],
                "already_applied": False,
            }
            result["receipt_fingerprint"] = canonical_hash(result)
            session.add(RunPackageApplicationReceiptModel(run_id=run_id, branch_id=branch_id,
                command_id=command_id, request_fingerprint=request_fp, result_fingerprint=state.fingerprint,
                payload_json=json.dumps(result, sort_keys=True, separators=(",", ":"))))
            return result
