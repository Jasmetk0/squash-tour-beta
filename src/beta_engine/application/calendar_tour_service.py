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
from beta_engine.application.calendar_tour_season_summary import (
    compare_completed_seasons,
    completed_season_indices,
)
from beta_engine.application.calendar_tour_signed_records import signed_tour_records
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
    decode_prevalidated_lifecycle,
    get_lifecycle,
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
        "season-transition",
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
            decode_prevalidated_calendar_sources,
            load_match_rows,
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
        # CalendarStandaloneMatchService._context has just authenticated this
        # exact Saved HEAD via the repository's signed lineage validator. The
        # latter either strictly folds all sporting/Tour sources or reuses an
        # identical-byte verified signature. Do not fold the same 14 real matches
        # and all ranking publications a second time on every Admin operation.
        saved_evidence, saved, signed = decode_prevalidated_calendar_sources(
            revision.saved_revision.payload,
            run_id=run_id,
            branch_id=branch_id,
        )
        rows = load_match_rows(
            session,
            run_id=run_id,
            branch_id=branch_id,
            _verified_source=saved_evidence,
        )
        evidence = rows[0] if len(rows) == 1 else None
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

        native = checkpoint is not None and checkpoint.schema_version in {
            "calendar_sporting_checkpoint.v11",
            "calendar_sporting_checkpoint.v12",
        }
        state = load_tour(session, run_id=run_id, branch_id=branch_id)
        if native:
            from beta_engine.application.calendar_native_tour_context import (
                native_working_context,
            )

            health = native_working_context(
                session,
                revision=revision,
                checkpoint=checkpoint,
                saved=saved,
                state=state,
                signed=signed,
                evidence=evidence,
            )
        else:
            health = saved_knockout_health(
                session, revision=revision, run_id=run_id, branch_id=branch_id
            )
        if checkpoint != saved and not native:
            # This exact Saved predecessor was authenticated above, just as in
            # the Save coordinator. Rebuild the complete NEW live suffix and
            # compare the full successor; divergence falls back to full replay.
            verify_checkpoint(
                checkpoint,
                world,
                evidence,
                _verified_saved_prefix=saved,
            )
        if checkpoint and checkpoint.week.calendar.season_count > clock.season_count:
            raise ValueError("Native sporting owner exceeds the available Run horizon")
        context = (clock, revision, world, health, checkpoint, saved, evidence)
        if not native and (state != signed or checkpoint != saved):
            verify_tour(state, checkpoint, world)
        verify_tour_origins(session, state)
        # The exact Saved HEAD has been fully authenticated in _context's
        # repository lineage walk. Comparing immutable Saved lifecycle bytes
        # to independently parsed live rows is sufficient for unchanged Tour
        # state; a changed Working Draft still gets the full birth/Entry fold.
        signed_life = decode_prevalidated_lifecycle(
            revision.saved_revision.payload, run_id=run_id, branch_id=branch_id
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
            signed_life
            if state is None or (state == signed and checkpoint == saved)
            else live_life
            if native
            else _lifecycle_history(world, state.week, state)
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

    def records(
        self,
        *,
        run_id,
        branch_id,
        as_of_season_index=None,
        from_season_index=0,
        country_code=None,
        leaderboard_limit=20,
    ):
        """Read only the authenticated Saved Tour, not newer Working changes."""
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            ctx, _working, signed = self._context(session, run_id, branch_id)
            _clock, rev, world, _health, _checkpoint, _saved, _evidence = ctx
            if signed is None or world is None:
                raise ValueError("Native Records require a Saved configured Tour")
            report = signed_tour_records(
                signed,
                world,
                as_of_season_index=as_of_season_index,
                from_season_index=from_season_index,
                country_code=country_code,
                leaderboard_limit=leaderboard_limit,
            )
            return {
                **report,
                "schema_version": "calendar_tour_signed_records_response.v1",
                "saved_head_revision_id": rev.saved_head_revision_id,
            }

    def season_summary(self, *, run_id, branch_id, season_index, compare_to=None):
        """Read only an already authenticated Saved Tour, never the Working candidate."""
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            ctx, _working, signed = self._context(session, run_id, branch_id)
            _clock, rev, world, _health, _checkpoint, _saved, _evidence = ctx
            if signed is None or world is None:
                raise ValueError("Season summary requires a Saved configured Tour")
            summary = compare_completed_seasons(
                signed,
                world,
                season_index,
                compare_to,
            )
            return {
                "schema_version": "calendar_tour_season_comparison.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "saved_head_revision_id": rev.saved_head_revision_id,
                **summary,
            }

    def inspect(self, *, run_id, branch_id):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            ctx, state, signed = self._context(session, run_id, branch_id)
            _clock, rev, world, _health, cp, saved, _ = ctx
            checkpoint_fingerprint = cp.fingerprint if cp else None
            # _context verified the full live lifecycle against its Saved
            # owner (or rebuilt an unsaved one). Read the authenticated current
            # row instead of replaying every historical birth/Entry week again.
            lifecycle = (
                get_lifecycle(
                    session, run_id=run_id, branch_id=branch_id, week=state.week
                )
                if state
                else None
            )
            identities = (
                {p.player_id: p for p in lifecycle.players} if lifecycle else {}
            )
            sporting = {p.player_id: p for p in cp.players} if cp else {}
            names = {p.player_id: p.name for p in world.players}
            if identities.keys() - names.keys():
                from beta_engine.infrastructure.db.run_prospect_source_state import (
                    load_saved_run_prospect_source,
                )

                source = load_saved_run_prospect_source(
                    rev.saved_revision.payload, run_id=run_id
                )
                names.update(
                    {
                        r["prospect_id"]: r.get("display_name") or r["prospect_id"]
                        for r in source.records
                        if r["prospect_id"] in identities
                    }
                )
            population = tuple(identities) if identities else tuple(names)
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
                    from beta_engine.domain.players.calendar_native_competition import (
                        native_match_slot,
                    )

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
                                "slot": native_match_slot(a, i)
                                if event.schema_version
                                == "calendar_followup_knockout.v6"
                                else a.edition.start_slot + 3 + i,
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
                "saved_completed_seasons": (
                    completed_season_indices(signed) if signed else ()
                ),
                "checkpoint_fingerprint": checkpoint_fingerprint,
                "tour_fingerprint": state.fingerprint if state else None,
                "saved": bool(state and signed == state and cp == saved),
                "sporting_saved": bool(cp and cp == saved),
                "post_birth_competition_supported": bool(
                    cp
                    and cp.schema_version
                    in {
                        "calendar_sporting_checkpoint.v11",
                        "calendar_sporting_checkpoint.v12",
                    }
                ),
                "can_initialize": state is None
                and cp is not None
                and cp == saved
                and cp.week.week >= 2,
                "players": [
                    {
                        "player_id": pid,
                        "name": names[pid],
                        "age": identities[pid].age
                        if pid in identities
                        else next(
                            p.age_years_at_season_start
                            for p in world.players
                            if p.player_id == pid
                        ),
                        "status": identities[pid].status
                        if pid in identities
                        else "active",
                        "form": sporting[pid].current_form if pid in sporting else None,
                        "sharpness": sporting[pid].match_sharpness
                        if pid in sporting
                        else None,
                        "fatigue": sporting[pid].long_term_fatigue
                        if pid in sporting
                        else None,
                    }
                    for pid in population
                ],
                "state": state.model_dump(mode="json") if state else None,
                "edition_evidence": evidence,
                "contributions": contributions,
                "transition_blockers": self._transition_blockers(
                    state, ctx, session, _checkpoint_fingerprint=checkpoint_fingerprint
                )
                if state
                else ["tour_authority_missing"],
                "season_transition_blockers": self._transition_blockers(
                    state,
                    ctx,
                    session,
                    _checkpoint_fingerprint=checkpoint_fingerprint,
                    season=True,
                )
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
            life = (
                get_lifecycle(
                    session, run_id=run_id, branch_id=branch_id, week=state.week
                )
                if state
                else None
            )
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
        # Non-sporting configuration can be reviewed and staged together in
        # one Working Draft. Playing a real match, confirming its result and
        # advancing the public week must still start from an immutable Save.
        if state != signed and command.action in (
            "play",
            "confirm-result",
            "transition",
            "season-transition",
        ):
            raise ValueError(
                "Manual Save of the configured Tour authority is required first"
            )
        if command.action != "initialize" and state is None:
            raise ValueError("Initialize the native Tour authority first")
        if command.action == "initialize" and (state is not None or cp.week.week < 2):
            raise ValueError(
                "Native Tour requires one Saved population and Week 2+ sporting checkpoint"
            )

        if cp.schema_version in {
            "calendar_sporting_checkpoint.v11",
            "calendar_sporting_checkpoint.v12",
        } and (
            command.action in {"initialize", "policy"}
            or (
                command.action in {"transition", "season-transition"}
                and (command.data or command.edition_id)
            )
        ):
            raise ValueError(
                "Native competition keeps policy edits and extra transition inputs unsupported"
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
        if state and command.action in {"transition", "season-transition"}:
            season = command.action == "season-transition"
            blockers = self._transition_blockers(
                state,
                ctx,
                session,
                season=season,
            )
            if blockers:
                raise ValueError(
                    ("Season Transition" if season else "Week Transition")
                    + " blocked: "
                    + ", ".join(blockers)
                )
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
        if command.action in {"transition", "season-transition"}:
            candidate, successor = self._transition_candidate(
                session, ctx, state, command
            )
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
            if successor.schema_version in {
                "calendar_tour_authority.v3",
                "calendar_tour_authority.v4",
            }:
                # Reject any coupled-write discrepancy before this transaction
                # commits, not on the next inspection or eventual manual Save.
                self._context(session, run_id, branch_id)
                _fault_injection_point("after_native_replay")
            return result

    def _play_native(
        self, session, ctx, state, authority, command, *, persist, native_inputs=None
    ):
        from beta_engine.application.calendar_followup_knockout_service import (
            CalendarFollowupKnockoutService,
        )
        from beta_engine.domain.players.calendar_native_competition import (
            play_native_tournament,
        )
        from beta_engine.infrastructure.db.run_prospect_source_state import (
            load_saved_run_prospect_source,
        )

        clock, revision, world, health, cp, _, _ = ctx
        event, successor = (
            native_inputs[2]
            if native_inputs is not None and len(native_inputs) > 2
            else play_native_tournament(
                checkpoint=cp,
                world=world,
                lifecycle=native_inputs[0]
                if native_inputs is not None
                else get_lifecycle(
                    session,
                    run_id=state.run_id,
                    branch_id=state.branch_id,
                    week=cp.week,
                ),
                health=health,
                source=native_inputs[1]
                if native_inputs is not None
                else load_saved_run_prospect_source(
                    revision.saved_revision.payload, run_id=state.run_id
                ),
                clock=clock,
                authority=authority,
                command=command,
                knockout=getattr(ctx[6], "knockout", ctx[6]),
            )
        )
        if persist:
            replace_checkpoint(session, previous=cp, successor=successor)
            _fault_injection_point("after_native_matches_write")
        receipt = CalendarFollowupKnockoutService._receipt(event, successor)
        receipt["participant_identities"] = {
            p.player_id: {"name": p.name, "country_code": p.nationality}
            for m in event.matches
            for p in m.canonical_projections
        }
        return receipt

    @staticmethod
    def _transition_blockers(
        state, ctx, session=None, *, _checkpoint_fingerprint=None, season=False
    ):
        clock, _rev, _world, health, cp, _saved, _evidence = ctx
        blockers = []
        if season:
            if cp.week.week != clock.weeks_per_year:
                blockers.append("season_transition_requires_last_week")
            if cp.week.season_index + 1 >= clock.season_count:
                blockers.append("season_transition_horizon_exhausted")
        elif cp.week.week >= clock.weeks_per_year:
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
        checkpoint_fingerprint = (
            cp.fingerprint
            if _checkpoint_fingerprint is None
            else _checkpoint_fingerprint
        )
        if state.checkpoint_fingerprint != checkpoint_fingerprint:
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
                from beta_engine.domain.players.calendar_prospect_birth import (
                    build_calendar_prospect_birth_event,
                )
                from beta_engine.infrastructure.db.run_prospect_source_state import (
                    validate_live_run_prospect_source_against_saved,
                )

                try:
                    source = validate_live_run_prospect_source_against_saved(
                        session, _rev.saved_revision.payload, run_id=state.run_id
                    )
                    if cp.week.ordinal + 1 < clock.season_count * clock.weeks_per_year:
                        position = clock.position_at_ordinal(cp.week.ordinal + 1)
                        target = RunWeekPosition(
                            calendar=clock,
                            season_index=position.season_index,
                            week=position.season_week,
                        )
                        life = get_lifecycle(
                            session,
                            run_id=state.run_id,
                            branch_id=state.branch_id,
                            week=cp.week,
                        )
                        build_calendar_prospect_birth_event(
                            predecessor=life,
                            target=target,
                            source=source,
                            world_package_id=_world.world_package_id,
                        )
                except ValueError:
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

    def _transition_candidate(self, session, ctx, state, command):
        clock, rev, world, health, cp, saved, evidence = ctx
        from beta_engine.domain.tournaments.calendar_native_tour_week import (
            prepare_native_tour_week,
        )
        from beta_engine.infrastructure.db.player_health_state import load_saved_health
        from beta_engine.infrastructure.db.player_lifecycle_state import (
            load_saved_lifecycle,
        )
        from beta_engine.infrastructure.db.run_prospect_source_state import (
            validate_live_run_prospect_source_against_saved,
        )

        source = validate_live_run_prospect_source_against_saved(
            session, rev.saved_revision.payload, run_id=state.run_id
        )
        if source is not None:
            native = prepare_native_tour_week(
                state=state,
                checkpoint=cp,
                world=world,
                source=source,
                lifecycle=load_saved_lifecycle(
                    rev.saved_revision.payload,
                    run_id=state.run_id,
                    branch_id=state.branch_id,
                ),
                health=load_saved_health(
                    rev.saved_revision.payload,
                    run_id=state.run_id,
                    branch_id=state.branch_id,
                ),
                clock=clock,
                knockout=getattr(evidence, "knockout", evidence),
                command=command.model_dump(mode="json"),
            )
            if native is not None:
                if command.data or command.edition_id is not None:
                    raise ValueError(
                        "Native birth transition cannot contain Edition or extra command data"
                    )
                return native
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
            season=command.action == "season-transition",
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
        _native_inputs=None,
    ):
        clock, _rev, world, _health, cp, _saved, evidence = ctx
        result = {
            "command_id": command.command_id,
            "action": command.action,
            "manual_save_required": True,
        }
        if (
            state is not None
            and state.schema_version == "calendar_tour_authority.v3"
            and command.action not in {"transition", "season-transition"}
        ):
            from beta_engine.domain.tournaments.calendar_native_tour import (
                competition_tour,
            )

            state = competition_tour(state, command.expected_saved_head)
            from beta_engine.domain.players.calendar_native_competition import (
                competition_checkpoint,
            )

            previous_cp = cp
            cp = competition_checkpoint(cp)
            if persist:
                replace_checkpoint(session, previous=previous_cp, successor=cp)
            state = state.model_copy(update={"checkpoint_fingerprint": cp.fingerprint})
            ctx = (*ctx[:4], cp, *ctx[5:])
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
        elif command.action in {"transition", "season-transition"}:
            impact, successor = transition_candidate
            if persist:
                replace_checkpoint(session, previous=cp, successor=successor)
            _fault_injection_point("after_development_write")
            from beta_engine.domain.rankings.calendar_official import (
                CalendarOfficialRankingSnapshot,
            )

            ranking = CalendarOfficialRankingSnapshot.model_validate_json(
                json.dumps(impact["ranking"])
            )
            from beta_engine.infrastructure.db.player_lifecycle_state import (
                _parse_lifecycle_json,
            )

            lifecycle = _parse_lifecycle_json(json.dumps(impact["lifecycle"]))
            if impact.get("native_transition"):
                from beta_engine.infrastructure.db.player_health_state import (
                    _parse_health_json,
                    put_health,
                )

                if persist:
                    for raw in impact["health_states"]:
                        put_health(session, _parse_health_json(json.dumps(raw)))
                _fault_injection_point("after_health_write")
            if persist:
                put_lifecycle(session, lifecycle)
            _fault_injection_point("after_lifecycle_write")
            event = {
                "kind": (
                    "season_transition_completed"
                    if command.action == "season-transition"
                    else "week_transition_completed"
                ),
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
                health_fingerprint=impact["health_fingerprint"],
                ages=impact["ages"],
                retired_player_ids=impact["retired_player_ids"],
                public_event=event,
            )
            updates = {
                "schema_version": (
                    "calendar_tour_authority.v4"
                    if state.schema_version == "calendar_tour_authority.v4"
                    else "calendar_tour_authority.v3"
                    if impact.get("native_transition")
                    else "calendar_tour_authority.v2"
                    if command.action == "season-transition"
                    else state.schema_version
                ),
                "week": successor.week,
                "slot_cursor": 0,
                "checkpoint_fingerprint": successor.fingerprint,
                "lifecycle_fingerprint": lifecycle.fingerprint,
                "rankings": state.rankings + (ranking,),
                "transitions": state.transitions + (transition,),
            }
            if (
                impact.get("native_transition")
                and state.schema_version != "calendar_tour_authority.v4"
            ):
                from beta_engine.domain.tournaments.calendar_native_tour import (
                    CalendarNativeTourState,
                )

                values = {key: getattr(state, key) for key in type(state).model_fields}
                values.update(updates)
                values.update(
                    schema_version="calendar_tour_authority.v3",
                    native_root_tour=getattr(state, "native_root_tour", state),
                    native_root_saved_head=getattr(
                        state, "native_root_saved_head", command.expected_saved_head
                    ),
                    native_root_health_state_count=getattr(
                        state,
                        "native_root_health_state_count",
                        impact["source_health_state_count"],
                    ),
                )
                # Receipt is attached immediately below in execute, before the
                # strict persisted v3 validator sees this staged aggregate.
                state = CalendarNativeTourState.model_construct(**values)
            else:
                state = state.model_copy(update=updates)
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
                native_competition = (
                    state.schema_version == "calendar_tour_authority.v4"
                )
                owned = {
                    p.player_id: p
                    for p in (
                        (
                            _native_inputs[0]
                            if _native_inputs is not None
                            else get_lifecycle(
                                session,
                                run_id=state.run_id,
                                branch_id=state.branch_id,
                                week=cp.week,
                            )
                        ).players
                        if native_competition
                        else world.players
                    )
                }
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
                    (
                        owned[pid].status == "retired"
                        if native_competition
                        else int(age_in_run_years(owned[pid], cp.week))
                        >= world.lifecycle_policy.automatic_retirement_age
                    )
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
                        "Draw requires an approved field and no existing draw"
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
                played = (
                    self._play_native(
                        session,
                        ctx,
                        state,
                        authority,
                        command,
                        persist=persist,
                        native_inputs=_native_inputs,
                    )
                    if state.schema_version == "calendar_tour_authority.v4"
                    else CalendarFollowupKnockoutService(self.repository).simulate(
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
                            entrant_ids=[
                                s.player_id for s in authority.draw.main.slots
                            ],
                            seed=command.seed,
                            operator_label=command.operator_label,
                            audit_reason=command.audit_reason,
                            point_policy=point_policy,
                            explicit_point_confirmation=True,
                        ),
                    )
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
                if "participant_identities" in played:
                    result["played"]["participant_identities"] = played[
                        "participant_identities"
                    ]
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
