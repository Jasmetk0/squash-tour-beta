"""Confirmed native Tour commands; one SQLite transaction owns every write.

Uses production application-submission/first-entry writers, canonical field/draw
rules, native persisted MatchEngine execution and the existing W-aware ranking
calculator. Save remains a separate, ordinary immutable revision operation.
"""

import json
from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import select, text

from beta_engine.application.calendar_followup_knockout_service import (
    CalendarFollowupEightScoredCommand,
    CalendarFollowupKnockoutService,
    CalendarFollowupScoredCommand,
)
from beta_engine.application.calendar_sporting_week_service import (
    CalendarSportingWeekCommand,
    CalendarSportingWeekService,
)
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_followup_points import (
    CalendarFollowupEightPointPolicy,
    CalendarFollowupPointPolicy,
)
from beta_engine.domain.players.calendar_lifecycle import calendar_lifecycle_history
from beta_engine.domain.players.calendar_sporting_week import age_in_run_years
from beta_engine.domain.rankings.calendar_official import (
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.official import FrozenInput, OfficialRankingPolicy
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
    TournamentApplicationSubmissionBatchAuthority,
)
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarEditionAuthority,
    CalendarTourEdition,
    CalendarTourPolicy,
    CalendarTourReceipt,
    CalendarTourState,
    CalendarTourTransition,
    build_draw,
    calculate_tour_ranking,
    edition_results,
    effective_policy,
    lifecycle_calendars,
    ranking_week,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldResolver
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    replace_checkpoint,
)
from beta_engine.infrastructure.db.calendar_tour import (
    load_tour,
    put_tour,
    verify_tour,
    verify_tour_origins,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    _load as load_lifecycle_row,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    load_saved_lifecycle,
    put_lifecycle,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    TournamentApplicationSubmissionStore,
    record_valid_application_submission_batch,
)


def _lifecycle_history(world, week, state):
    from beta_engine.application.calendar_initial_world import (
        derive_calendar_bootstrap_lifecycle,
    )

    return calendar_lifecycle_history(
        derive_calendar_bootstrap_lifecycle(world),
        week,
        tuple(s for a in state.editions for s in a.submissions) if state else (),
        effective_calendars=lifecycle_calendars(state) if state else None,
    )


class CalendarTourCommand(FrozenInput):
    action: Literal[
        "initialize",
        "create-edition",
        "submit",
        "approve",
        "draw",
        "play",
        "confirm-result",
        "policy",
        "transition",
    ]
    command_id: str = Field(min_length=1, max_length=100)
    expected_saved_head: str = Field(min_length=1)
    expected_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_tour_fingerprint: str | None = None
    edition_id: str | None = None
    seed: int = 1
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    data: dict = Field(default_factory=dict)


class CalendarTourCommit(FrozenInput):
    command: CalendarTourCommand
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    explicit_confirmation: Literal[True]


def _fault_injection_point(name):
    """Late-write failure seam used only by rollback tests."""


@dataclass
class CalendarTourService:
    repository: object

    def _context(self, session, run_id, branch_id):
        from beta_engine.application.calendar_knockout_health import (
            saved_knockout_health,
        )
        from beta_engine.application.calendar_standalone_match_service import (
            CalendarStandaloneMatchService,
        )
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
            load_checkpoint,
            verify_checkpoint,
        )
        from beta_engine.infrastructure.db.calendar_standalone_match_state import (
            load_match_rows,
            load_saved_calendar_sources,
        )

        proofs = {}
        clock, revision, world = CalendarStandaloneMatchService(
            self.repository
        )._context(
            session,
            run_id=run_id,
            branch_id=branch_id,
            allow_calendar_health=True,
            allow_calendar_sporting=True,
            _sporting_component_proofs=proofs,
        )
        health = saved_knockout_health(
            session, revision=revision, run_id=run_id, branch_id=branch_id
        )
        rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
        evidence = rows[0] if len(rows) == 1 else None
        saved_evidence, saved, signed = load_saved_calendar_sources(
            revision.saved_revision.payload,
            run_id=run_id,
            branch_id=branch_id,
            _sporting_component_proofs=proofs,
        )
        checkpoint = load_checkpoint(
            session, run_id=run_id, branch_id=branch_id, _verified_source=saved
        )
        if saved and (
            checkpoint is None
            or getattr(evidence, "knockout", evidence)
            != getattr(saved_evidence, "knockout", saved_evidence)
        ):
            raise ValueError(
                "Live sporting owner or original knockout differs from Saved history"
            )
        # The exact same Saved and live owner needs one full sporting fold, not
        # independent Opening + Continuation + Tour folds of identical inputs.
        # A distinct unsaved owner still receives its own complete verification.
        if checkpoint != saved:
            verify_checkpoint(checkpoint, world, evidence)
        if checkpoint and checkpoint.week.calendar.season_count > clock.season_count:
            raise ValueError("Native sporting owner exceeds the available Run horizon")
        context = (clock, revision, world, health, checkpoint, saved, evidence)
        state = load_tour(session, run_id=run_id, branch_id=branch_id)
        if state != signed or checkpoint != saved:
            verify_tour(state, checkpoint, world)
        verify_tour_origins(session, state)
        signed_life = (
            load_saved_lifecycle(
                revision.saved_revision.payload, run_id=run_id, branch_id=branch_id
            )
            if state is None
            else None
        )
        from beta_engine.infrastructure.db.models import PlayerLifecycleWeekStateModel

        live_life = tuple(
            load_lifecycle_row(row, run_id, branch_id, row.week_ordinal)
            for row in session.scalars(
                select(PlayerLifecycleWeekStateModel)
                .where(
                    PlayerLifecycleWeekStateModel.run_id == run_id,
                    PlayerLifecycleWeekStateModel.branch_id == branch_id,
                )
                .order_by(PlayerLifecycleWeekStateModel.week_ordinal)
            )
        )
        expected_life = (
            _lifecycle_history(world, state.week, state) if state else signed_life
        )
        if live_life != expected_life or (
            state and live_life[-1].fingerprint != state.lifecycle_fingerprint
        ):
            raise ValueError(
                "Native Tour lifecycle differs from its authoritative birth/Entry history"
            )
        if state:
            stored = tuple(
                s
                for s in TournamentApplicationSubmissionStore(session).list(
                    run_id=run_id, branch_id=branch_id
                )
                if s.schema_version.endswith(".v2")
            )
            expected = tuple(s for a in state.editions for s in a.submissions)
            if {s.fingerprint for s in stored} != {s.fingerprint for s in expected}:
                raise ValueError(
                    "Tour submissions differ from production Entry authority"
                )
        return context, state, signed

    def inspect(self, *, run_id, branch_id):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            ctx, state, signed = self._context(session, run_id, branch_id)
            _clock, rev, world, _health, cp, saved, _ = ctx
            lifecycle = (
                _lifecycle_history(world, state.week, state)[-1] if state else None
            )
            identities = (
                {p.player_id: p for p in lifecycle.players} if lifecycle else {}
            )
            sporting = {p.player_id: p for p in cp.players} if cp else {}
            evidence = {}
            contributions = {}
            if state and cp:
                for a in state.editions:
                    event = next(
                        (
                            t
                            for t in cp.tournaments
                            if t.tournament_id == a.edition.edition_id
                        ),
                        None,
                    )
                    if event is None or not a.tournament_fingerprint:
                        continue
                    evidence[a.edition.edition_id] = {
                        "results": [
                            {**r.model_dump(mode="json"), "stage": award.reached_stage}
                            for r, award in zip(
                                edition_results(a, event),
                                event.prepared_awards,
                                strict=True,
                            )
                        ],
                        "matches": [
                            {
                                "match_id": m.match_id,
                                "slot": a.edition.start_slot + 3 + i,
                                "player_a_id": m.result.player_a_id,
                                "player_b_id": m.result.player_b_id,
                                "winner_player_id": m.result.winner_player_id,
                                "rally_count": len(m.result.rally_log.events),
                            }
                            for i, m in enumerate(event.matches)
                        ],
                    }
                    if a.result_confirmed:
                        counted = {
                            r.source_fingerprint
                            for row in state.rankings[-1].rows
                            for r in row.counted_results
                        }
                        for r in edition_results(a, event):
                            age = state.week.ordinal - state.week.calendar.ordinal(
                                r.first_publication_week.season_index,
                                r.first_publication_week.week,
                            )
                            status = (
                                "awaiting_activation"
                                if age < 0
                                else "expired"
                                if age >= r.validity_weeks
                                else "counted"
                                if r.source_fingerprint in counted
                                else "excluded_best_n"
                            )
                            contributions.setdefault(r.player_id, []).append(
                                {**r.model_dump(mode="json"), "status": status}
                            )
            return {
                "schema_version": "calendar_tour_inspection.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "saved_head_revision_id": rev.saved_head_revision_id,
                "draft_version": rev.working_draft.draft_version,
                "run_calendar": _clock.to_metadata(),
                "checkpoint_fingerprint": cp.fingerprint if cp else None,
                "tour_fingerprint": state.fingerprint if state else None,
                "saved": bool(state and signed == state and cp == saved),
                "can_initialize": state is None
                and cp is not None
                and cp == saved
                and cp.week.week >= 2,
                "players": [
                    {
                        "player_id": p.player_id,
                        "name": p.name,
                        "age": identities[p.player_id].age
                        if p.player_id in identities
                        else p.age_years_at_season_start,
                        "status": identities[p.player_id].status
                        if p.player_id in identities
                        else "active",
                        "form": sporting[p.player_id].current_form
                        if p.player_id in sporting
                        else None,
                        "sharpness": sporting[p.player_id].match_sharpness
                        if p.player_id in sporting
                        else None,
                        "fatigue": sporting[p.player_id].long_term_fatigue
                        if p.player_id in sporting
                        else None,
                    }
                    for p in world.players
                ],
                "state": state.model_dump(mode="json") if state else None,
                "edition_evidence": evidence,
                "contributions": contributions,
                "transition_blockers": self._transition_blockers(state, ctx, session)
                if state
                else ["tour_authority_missing"],
            }

    def player(self, *, run_id, branch_id, player_id):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            ctx, state, _signed = self._context(session, run_id, branch_id)
            record = (
                next((p for p in ctx[4].players if p.player_id == player_id), None)
                if ctx[4]
                else None
            )
            if record is None:
                raise KeyError(
                    "Player does not belong to this Run/Branch sporting owner"
                )
            life = _lifecycle_history(ctx[2], state.week, state)[-1] if state else None
            identity = (
                next((p for p in life.players if p.player_id == player_id), None)
                if life
                else None
            )
            return {
                "run_id": run_id,
                "branch_id": branch_id,
                "saved_head_revision_id": ctx[1].saved_head_revision_id,
                "checkpoint_fingerprint": ctx[4].fingerprint,
                "record": record.model_dump(mode="json"),
                "lifecycle": identity.model_dump(mode="json") if identity else None,
            }

    def _prepare(self, session, run_id, branch_id, command, *, loaded=None):
        ctx, state, signed = (
            loaded if loaded is not None else self._context(session, run_id, branch_id)
        )
        _clock, rev, _world, _health, cp, saved, evidence = ctx
        if (
            cp is None
            or cp != saved
            or rev.saved_head_revision_id != command.expected_saved_head
            or cp.fingerprint != command.expected_checkpoint_fingerprint
            or (state.fingerprint if state else None)
            != command.expected_tour_fingerprint
        ):
            raise ValueError(
                "Source HEAD or sporting/Tour input changed; Save and review again"
            )
        if state != signed:
            raise ValueError(
                "Manual Save of the configured Tour authority is required first"
            )
        if command.action != "initialize" and state is None:
            raise ValueError("Initialize the native Tour authority first")
        if command.action == "initialize" and (state is not None or cp.week.week < 2):
            raise ValueError(
                "Native Tour requires one Saved population and Week 2+ sporting checkpoint"
            )
        # All native writes share the identity namespace, including nested matches.
        reserved = {
            e.command_id for e in (*cp.week_events, *cp.continuations, *cp.closures)
        }
        reserved.update(e.command_id for e in cp.played_continuations)
        root = getattr(evidence, "knockout", evidence)
        reserved.add(root.command_id)
        if command.command_id in reserved:
            raise ValueError("Command ID collides with existing sporting history")
        if state and command.action == "transition":
            blockers = self._transition_blockers(state, ctx, session)
            if blockers:
                raise ValueError("Week Transition blocked: " + ", ".join(blockers))
        authority = None
        if command.edition_id:
            authority = (
                next(
                    (
                        a
                        for a in state.editions
                        if a.edition.edition_id == command.edition_id
                    ),
                    None,
                )
                if state
                else None
            )
            if authority is None:
                raise ValueError("Edition does not belong to the selected Run/Branch")
            offsets = {
                "submit": 0,
                "approve": 1,
                "draw": 2,
                "play": 3,
                "confirm-result": authority.edition.main_entrant_count + 2,
            }
            if command.action in offsets and any(
                a.edition.week.ordinal == cp.week.ordinal
                and a.edition.start_slot < authority.edition.start_slot
                and not a.result_confirmed
                for a in state.editions
            ):
                raise ValueError("Complete the nearest earlier mandatory Edition first")
            if (
                command.action in offsets
                and authority.edition.start_slot + offsets[command.action]
                < state.slot_cursor
            ):
                raise ValueError(
                    "Operation precedes the current global Simulation Slot"
                )
        if state and command.action == "play":
            if authority.draw is None or authority.tournament_fingerprint:
                raise ValueError(
                    "Play requires a pre-existing Saved draw and unplayed Edition"
                )
            if ctx[3] is None:
                raise ValueError("Configured Tour play requires Saved Health authority")
            from beta_engine.domain.matches.health import project_player_health

            entrants = (
                {s.player_id for s in authority.draw.main.slots}
                if authority.draw
                else set()
            )
            if any(
                project_player_health(p).numeric_calibration_required
                for p in ctx[3].players
                if p.player_id in entrants
            ):
                raise ValueError(
                    "Official play is blocked by unresolved numeric Health effects for a participant"
                )
            from beta_engine.domain.players.calendar_followup_knockout import (
                ROUNDS,
                ROUNDS_EIGHT,
            )

            suffixes = (
                ROUNDS_EIGHT if authority.edition.main_entrant_count == 8 else ROUNDS
            )
            if {f"{command.command_id}:{s}" for s in suffixes} & {
                r.command_id for r in state.receipts
            }:
                raise ValueError(
                    "Nested match command collides with Tour command history"
                )
        preview = {
            "schema_version": "calendar_tour_command_preview.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "command": command.model_dump(mode="json"),
            "week": cp.week.model_dump(mode="json"),
            "edition": authority.model_dump(mode="json") if authority else None,
        }
        successor = None
        if command.action == "transition":
            candidate, successor = self._transition_candidate(ctx, state, command)
            preview["impact"] = candidate
        else:
            if command.action == "play":
                preview["impact"] = {
                    "action": "play",
                    "manual_save_required": True,
                    "edition_authority_fingerprint": authority.execution_fingerprint,
                    "entrant_ids": [s.player_id for s in authority.draw.main.slots],
                    "point_table": authority.edition.point_table,
                }
            else:
                planned, impact = self._apply(
                    session, ctx, state, authority, command, persist=False
                )
                type(planned).model_validate_json(planned.model_dump_json())
                preview["impact"] = impact
        preview["preview_fingerprint"] = canonical_hash(preview)
        return preview, ctx, state, authority, successor

    def preview(self, *, run_id, branch_id, command):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            return self._prepare(session, run_id, branch_id, command)[0]

    def execute(self, *, run_id, branch_id, request):
        command = request.command
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            # Authenticate the live/signed owners even on exact retries.
            loaded = self._context(session, run_id, branch_id)
            _, current, _ = loaded
            if current:
                for receipt in current.receipts:
                    if receipt.command_id == command.command_id:
                        if receipt.request != request.model_dump(mode="json"):
                            raise ValueError(
                                "Command ID already has a different payload or confirmation"
                            )
                        return receipt.result
            preview, ctx, state, authority, transition_successor = self._prepare(
                session, run_id, branch_id, command, loaded=loaded
            )
            if preview["preview_fingerprint"] != request.expected_preview_fingerprint:
                raise ValueError(
                    "Confirmation is stale; review the current inputs again"
                )
            successor, result = self._apply(
                session,
                ctx,
                state,
                authority,
                command,
                transition_candidate=(preview["impact"], transition_successor),
            )
            successor = successor.model_copy(
                update={
                    "receipts": successor.receipts
                    + (
                        CalendarTourReceipt(
                            command_id=command.command_id,
                            request=request.model_dump(mode="json"),
                            result=result,
                        ),
                    )
                }
            )
            put_tour(session, successor)
            _fault_injection_point("after_tour_write")
            return result

    @staticmethod
    def _transition_blockers(state, ctx, session=None):
        clock, _rev, _world, health, cp, _saved, _evidence = ctx
        blockers = []
        if cp.week.week >= clock.weeks_per_year:
            blockers.append("season_transition_required")
        if health is None:
            blockers.append("saved_health_baseline_missing")
        elif any(
            any(r.lifecycle != "Recovered" for r in p.records)
            or p.permanent_consequences
            for p in health.players
        ):
            blockers.append("health_healing_or_permanent_effect_authority_unsupported")
        for authority in state.editions:
            if (
                authority.edition.week.ordinal <= cp.week.ordinal
                and not authority.result_confirmed
            ):
                blockers.append("edition_not_terminal:" + authority.edition.edition_id)
        if state.checkpoint_fingerprint != cp.fingerprint:
            blockers.append("sporting_owner_drift")
        if session is not None:
            from beta_engine.infrastructure.db.models import (
                RunProspectModel,
                StagedCalendarRankingResultVersionModel,
                StagedCalendarRankingZeroVersionModel,
            )

            if (
                session.scalar(
                    select(RunProspectModel.prospect_id)
                    .where(RunProspectModel.run_id == state.run_id)
                    .limit(1)
                )
                is not None
            ):
                blockers.append(
                    "intake_source_requires_native_calendar_materialization"
                )
            if (
                session.scalar(
                    select(StagedCalendarRankingZeroVersionModel.run_id)
                    .where(
                        StagedCalendarRankingZeroVersionModel.run_id == state.run_id,
                        StagedCalendarRankingZeroVersionModel.branch_id
                        == state.branch_id,
                        StagedCalendarRankingZeroVersionModel.effective_ordinal
                        <= cp.week.ordinal + 1,
                    )
                    .limit(1)
                )
                is not None
            ):
                blockers.append(
                    "disciplinary_source_requires_native_activation_authority"
                )
            if (
                session.scalar(
                    select(StagedCalendarRankingResultVersionModel.run_id)
                    .where(
                        StagedCalendarRankingResultVersionModel.run_id == state.run_id,
                        StagedCalendarRankingResultVersionModel.branch_id
                        == state.branch_id,
                        StagedCalendarRankingResultVersionModel.effective_ordinal
                        <= cp.week.ordinal + 1,
                    )
                    .limit(1)
                )
                is not None
            ):
                blockers.append("ranking_source_requires_edition_binding_or_correction")
        return blockers

    def _transition_candidate(self, ctx, state, command):
        clock, rev, world, health, cp, saved, evidence = ctx
        policy = effective_policy(state, cp.week)
        sporting_cmd = CalendarSportingWeekCommand(
            command_id=command.command_id,
            expected_saved_head=command.expected_saved_head,
            expected_checkpoint_fingerprint=cp.fingerprint,
            seed=command.seed,
            operator_label=command.operator_label,
            audit_reason=command.audit_reason,
        )
        prepared, successor = CalendarSportingWeekService(self.repository)._preview(
            clock,
            rev,
            world,
            cp,
            saved,
            evidence,
            sporting_cmd,
            policy=policy.development,
            official=True,
        )
        target = successor.week
        lifecycle = _lifecycle_history(world, target, state)[-1]
        ages = tuple((p.player_id, p.age) for p in lifecycle.players)
        retired = tuple(p.player_id for p in lifecycle.players if p.status == "retired")
        ranking = calculate_tour_ranking(state, cp, target=target, retired=retired)
        return {
            "completed_week": prepared["advance"]["completed_week"],
            "target_week": target.model_dump(mode="json"),
            "development_policy": policy.development.model_dump(mode="json"),
            "target_ranking_policy": effective_policy(state, target).ranking.model_dump(
                mode="json"
            ),
            "sporting": prepared,
            "ranking": ranking.model_dump(mode="json"),
            "ranking_fingerprint": ranking.fingerprint,
            "ages": ages,
            "retired_player_ids": retired,
            "health_fingerprint": health.fingerprint,
            "lifecycle": lifecycle.model_dump(mode="json"),
            "lifecycle_fingerprint": lifecycle.fingerprint,
        }, successor

    def _apply(
        self,
        session,
        ctx,
        state,
        authority,
        command,
        *,
        transition_candidate=None,
        persist=True,
    ):
        clock, _rev, world, health, cp, _saved, evidence = ctx
        result = {
            "command_id": command.command_id,
            "action": command.action,
            "manual_save_required": True,
        }
        if command.action == "initialize":
            from beta_engine.infrastructure.db.models import RunProspectModel

            if session.scalar(
                select(RunProspectModel.prospect_id)
                .where(RunProspectModel.run_id == cp.run_id)
                .limit(1)
            ):
                raise ValueError(
                    "Native intake source requires calendar materialization before Tour initialization"
                )
            effective_week = RunWeekPosition(
                calendar=clock, season_index=cp.week.season_index, week=cp.week.week
            )
            life = _lifecycle_history(world, effective_week, None)
            if persist:
                for item in life:
                    put_lifecycle(session, item)
            policy = CalendarTourPolicy(
                effective_week=effective_week,
                ranking=OfficialRankingPolicy(
                    policy_id="native-tour.initial.v1",
                    best_n=command.data.get("best_n", 15),
                ),
            )
            ranking = calculate_calendar_official_ranking(
                run_id=cp.run_id,
                branch_id=cp.branch_id,
                run_calendar=clock,
                week=ranking_week(cp.week),
                policy=policy.ranking,
                players=(),
                results=(),
            )
            state = CalendarTourState(
                run_id=cp.run_id,
                branch_id=cp.branch_id,
                week=effective_week,
                checkpoint_fingerprint=cp.fingerprint,
                lifecycle_fingerprint=life[-1].fingerprint,
                policies=(policy,),
                rankings=(ranking,),
            )
        elif command.action == "create-edition":
            edition = CalendarTourEdition.model_validate_json(json.dumps(command.data))
            if (
                edition.week.calendar != clock
                or edition.week.ordinal < cp.week.ordinal
                or edition.announcement_week.ordinal <= cp.week.ordinal
            ):
                raise ValueError(
                    "New Edition must use this Run clock, announce at a future Week Transition and allow a full week before operations"
                )
            if any(a.edition.edition_id == edition.edition_id for a in state.editions):
                raise ValueError("Edition identity already exists")
            if edition.main_entrant_count not in (4, 8) or not edition.ranked:
                raise ValueError(
                    "Current executor supports full Ranked main-only 4/8 fields"
                )
            policy_type = (
                CalendarFollowupEightPointPolicy
                if edition.main_entrant_count == 8
                else CalendarFollowupPointPolicy
            )
            policy_type(
                category_label=edition.edition_id,
                validity_weeks=edition.validity_weeks,
                **edition.point_table,
            )
            if any(
                a.edition.week.ordinal == edition.week.ordinal
                and not (
                    edition.start_slot
                    > a.edition.start_slot + a.edition.main_entrant_count + 2
                    or a.edition.start_slot
                    > edition.start_slot + edition.main_entrant_count + 2
                )
                for a in state.editions
            ):
                raise ValueError(
                    "Edition global slots overlap; shared simultaneous cross-Edition authority is unsupported"
                )
            if edition.edition_id in {
                getattr(evidence, "knockout", evidence).match_id,
                *(t.tournament_id for t in cp.tournaments),
            }:
                raise ValueError(
                    "Existing exhibition cannot be promoted to an Official Edition"
                )
            state = state.model_copy(
                update={
                    "editions": state.editions
                    + (
                        CalendarEditionAuthority(
                            edition=edition,
                            created_command_id=command.command_id,
                            created_saved_head=command.expected_saved_head,
                        ),
                    )
                }
            )
        elif command.action == "policy":
            policy = CalendarTourPolicy.model_validate_json(json.dumps(command.data))
            if (
                policy.effective_week.calendar != clock
                or policy.effective_week.ordinal <= cp.week.ordinal
            ):
                raise ValueError(
                    "Policy changes must be prospectively effective on this Run clock"
                )
            if any(
                p.effective_week.ordinal == policy.effective_week.ordinal
                for p in state.policies
            ):
                raise ValueError("An effective policy already exists at this week")
            state = state.model_copy(
                update={
                    "policies": tuple(
                        sorted(
                            (*state.policies, policy),
                            key=lambda p: p.effective_week.ordinal,
                        )
                    )
                }
            )
        elif command.action == "transition":
            impact, successor = transition_candidate
            replace_checkpoint(session, previous=cp, successor=successor)
            _fault_injection_point("after_development_write")
            from beta_engine.domain.rankings.calendar_official import (
                CalendarOfficialRankingSnapshot,
            )

            ranking = CalendarOfficialRankingSnapshot.model_validate_json(
                json.dumps(impact["ranking"])
            )
            from beta_engine.domain.players.calendar_lifecycle import (
                CalendarTourLifecycleState,
            )

            lifecycle = CalendarTourLifecycleState.model_validate_json(
                json.dumps(impact["lifecycle"])
            )
            put_lifecycle(session, lifecycle)
            event = {
                "kind": "week_transition_completed",
                "week": successor.week.model_dump(mode="json"),
                "ranking_fingerprint": ranking.fingerprint,
                "source_command_id": command.command_id,
                "announced_edition_ids": [
                    a.edition.edition_id
                    for a in state.editions
                    if a.edition.announcement_week.ordinal == successor.week.ordinal
                ],
            }
            transition = CalendarTourTransition(
                command_id=command.command_id,
                completed_week=RunWeekPosition.model_validate_json(
                    json.dumps(impact["completed_week"])
                ),
                target_week=successor.week,
                sporting_advance_fingerprint=impact["sporting"]["advance_fingerprint"],
                ranking_fingerprint=ranking.fingerprint,
                health_fingerprint=health.fingerprint,
                ages=impact["ages"],
                retired_player_ids=impact["retired_player_ids"],
                public_event=event,
            )
            state = state.model_copy(
                update={
                    "week": successor.week,
                    "slot_cursor": 0,
                    "checkpoint_fingerprint": successor.fingerprint,
                    "lifecycle_fingerprint": lifecycle.fingerprint,
                    "rankings": state.rankings + (ranking,),
                    "transitions": state.transitions + (transition,),
                }
            )
            result["impact"] = impact
            _fault_injection_point("after_ranking_and_public_event_staging")
        else:
            if authority is None:
                raise ValueError("This command requires an Edition")
            if authority.edition.week.ordinal != cp.week.ordinal:
                raise ValueError(
                    "Edition operation is outside its scheduled current week"
                )
            if not any(
                authority.edition.edition_id
                in t.public_event.get("announced_edition_ids", [])
                for t in state.transitions
                if t.target_week.ordinal < cp.week.ordinal
            ):
                raise ValueError(
                    "Edition requires its public announcement at least one whole week before operations"
                )
            if command.action == "submit":
                if authority.field:
                    raise ValueError("Applications are closed by field approval")
                ids = command.data.get("player_ids")
                if (
                    not isinstance(ids, list)
                    or not ids
                    or len(set(ids)) != len(ids)
                    or any(type(p) is not str for p in ids)
                ):
                    raise ValueError(
                        "Select distinct player IDs for the application batch"
                    )
                owned = {p.player_id: p for p in world.players}
                if set(ids) - owned.keys() or set(ids) & {
                    s.player_id for s in authority.submissions
                }:
                    raise ValueError(
                        "Application player is foreign or already submitted"
                    )
                slot = authority.edition.start_slot
                submissions = tuple(
                    sorted(
                        (
                            TournamentApplicationSubmissionAuthority(
                                schema_version="tournament_application_submission_authority.v2",
                                application_id=f"{authority.edition.edition_id}:{pid}",
                                run_id=state.run_id,
                                branch_id=state.branch_id,
                                event_id=authority.edition.edition_id,
                                player_id=pid,
                                entry_window="main",
                                submission_week=authority.edition.week,
                                decision_slot_ordinal=slot,
                                nr_tie_break_token=canonical_hash(
                                    {
                                        "run": state.run_id,
                                        "branch": state.branch_id,
                                        "player": pid,
                                    }
                                ),
                                validation_authority_id=command.command_id,
                                validation_authority_fingerprint=authority.edition.fingerprint,
                                provenance=f"Manual validated native Tour application: {command.operator_label}; {command.audit_reason}",
                            )
                            for pid in ids
                        ),
                        key=lambda s: s.application_id,
                    )
                )
                if any(
                    int(age_in_run_years(owned[pid], cp.week))
                    >= world.lifecycle_policy.automatic_retirement_age
                    for pid in ids
                ):
                    raise ValueError(
                        "Retired-age player cannot submit a Tour application"
                    )
                if persist:
                    record_valid_application_submission_batch(
                        session,
                        TournamentApplicationSubmissionBatchAuthority.from_submissions(
                            submissions
                        ),
                    )
                authority = authority.model_copy(
                    update={
                        "submissions": tuple(
                            sorted(
                                authority.submissions + submissions,
                                key=lambda s: s.application_id,
                            )
                        )
                    }
                )
            elif command.action == "approve":
                if (
                    authority.field
                    or len(authority.submissions) < authority.edition.main_entrant_count
                ):
                    raise ValueError(
                        "Approval requires enough valid applications and an unapproved Edition"
                    )
                binding = TournamentRankingSnapshotAuthority(
                    schema_version="tournament_ranking_snapshot_authority.v2",
                    run_id=state.run_id,
                    branch_id=state.branch_id,
                    event_id=authority.edition.edition_id,
                    ranking_week=cp.week,
                    ranking_snapshot=state.rankings[-1],
                    adopted_by_command_id=command.command_id,
                )
                field = TournamentEntryFieldResolver.build_initial(
                    authority=binding,
                    applications=tuple(
                        s.to_entry_field_application() for s in authority.submissions
                    ),
                    capacity=authority.edition.capacity,
                )
                accepted = set(field.direct_main_player_ids)
                if any(
                    a.field
                    and a.edition.edition_id != authority.edition.edition_id
                    and a.edition.week.ordinal == cp.week.ordinal
                    and accepted.intersection(a.field.direct_main_player_ids)
                    for a in state.editions
                ):
                    raise ValueError(
                        "Week Tournament Lock conflict: a player is already approved in another official Edition; native conflict resolution is required"
                    )
                authority = authority.model_copy(
                    update={"field": field, "ranking_authority": binding}
                )
                result["approved_field"] = field.model_dump(mode="json")
            elif command.action == "draw":
                if authority.field is None or authority.draw:
                    raise ValueError(
                        "Draw requires a Saved approved field and no existing draw"
                    )
                draw = build_draw(authority, command.command_id, command.seed)
                authority = authority.model_copy(
                    update={
                        "draw": draw,
                        "draw_seed": command.seed,
                        "draw_command_id": command.command_id,
                    }
                )
                result["draw"] = draw.model_dump(mode="json")
            elif command.action == "play":
                if authority.draw is None or authority.tournament_fingerprint:
                    raise ValueError(
                        "Play requires a pre-existing Saved draw and unplayed Edition"
                    )
                earlier = [
                    a
                    for a in state.editions
                    if a.edition.week.ordinal == cp.week.ordinal
                    and a.edition.start_slot < authority.edition.start_slot
                    and not a.result_confirmed
                ]
                if earlier:
                    raise ValueError(
                        "Complete the nearest earlier mandatory Edition first"
                    )
                size = authority.edition.main_entrant_count
                policy_cls = (
                    CalendarFollowupEightPointPolicy
                    if size == 8
                    else CalendarFollowupPointPolicy
                )
                cmd_cls = (
                    CalendarFollowupEightScoredCommand
                    if size == 8
                    else CalendarFollowupScoredCommand
                )
                point_policy = policy_cls(
                    category_label=authority.edition.edition_id,
                    validity_weeks=authority.edition.validity_weeks,
                    **authority.edition.point_table,
                )
                played = CalendarFollowupKnockoutService(self.repository).simulate(
                    run_id=state.run_id,
                    branch_id=state.branch_id,
                    _tour_session=session,
                    _tour_context=ctx,
                    _edition_authority_fingerprint=authority.execution_fingerprint,
                    command=cmd_cls(
                        command_id=command.command_id,
                        tournament_id=authority.edition.edition_id,
                        expected_saved_head=command.expected_saved_head,
                        expected_checkpoint_fingerprint=cp.fingerprint,
                        entrant_ids=[s.player_id for s in authority.draw.main.slots],
                        seed=command.seed,
                        operator_label=command.operator_label,
                        audit_reason=command.audit_reason,
                        point_policy=point_policy,
                        explicit_point_confirmation=True,
                    ),
                )
                authority = authority.model_copy(
                    update={
                        "played_saved_head": command.expected_saved_head,
                        "tournament_fingerprint": played["fingerprint"],
                    }
                )
                state = state.model_copy(
                    update={"checkpoint_fingerprint": played["checkpoint_fingerprint"]}
                )
                result["played"] = {
                    k: played[k]
                    for k in (
                        "fingerprint",
                        "checkpoint_fingerprint",
                        "winner_player_id",
                        "prepared_awards",
                    )
                }
                result["played"]["match_ids"] = [
                    m["match_id"] for m in played["tournament"]["matches"]
                ]
            elif command.action == "confirm-result":
                if not authority.tournament_fingerprint or authority.result_confirmed:
                    raise ValueError(
                        "Results require a Saved played Edition and independent confirmation"
                    )
                event = next(
                    t
                    for t in cp.tournaments
                    if t.tournament_id == authority.edition.edition_id
                )
                result["results"] = [
                    r.model_dump(mode="json") for r in edition_results(authority, event)
                ]
                authority = authority.model_copy(update={"result_confirmed": True})
            offsets = {
                "submit": 0,
                "approve": 1,
                "draw": 2,
                "play": authority.edition.main_entrant_count + 1,
                "confirm-result": authority.edition.main_entrant_count + 2,
            }
            state = state.model_copy(
                update={
                    "slot_cursor": authority.edition.start_slot
                    + offsets[command.action],
                    "editions": tuple(
                        authority
                        if a.edition.edition_id == authority.edition.edition_id
                        else a
                        for a in state.editions
                    ),
                }
            )
        return state, result
