"""Real four-entrant calendar-native main-only knockout, atomic with exact replay.

Two semifinals read the identical frozen pre-slot population. Their winners
feed the final, which consumes the committed post-semifinal form/load state.
Historical v1 evidence keeps its original frozen-player semantics. This
bounded sporting writer creates no points, publication or week transition.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field, model_validator
from sqlalchemy import text

from beta_engine.application.calendar_standalone_match_service import CalendarStandaloneMatchService
from beta_engine.application.calendar_knockout_health import saved_knockout_health, health_readiness
from beta_engine.domain.players.calendar_knockout_health import CalendarKnockoutHealthSource, calendar_knockout_match_anchor
from beta_engine.core import DeterministicRng
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext, MatchParticipantContext
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.players.calendar_canonical_match import CalendarCanonicalMatchSource, canonical_participant
from beta_engine.domain.players.calendar_match_state import (
    CalendarMatchStatePolicy, CalendarKnockoutSportingState,
    participant_with_state, advance_played_slot,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    CalendarOpeningKnockout, CalendarKnockoutMatch, load_match_rows,
    load_saved_calendar_match, put_match,
)
from beta_engine.infrastructure.db.calendar_knockout_awards_state import (
    CalendarScoredOpeningKnockout,
)


class CalendarCanonicalPreviewCommand(FrozenInput):
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entrant_ids: list[str] = Field(min_length=4, max_length=4)


class CalendarOpeningKnockoutCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    match_id: str = Field(min_length=1, max_length=100)
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entrant_ids: list[str] = Field(min_length=4, max_length=4)
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def distinct_entrants(self):
        if len(set(self.entrant_ids)) != 4 or not all(self.entrant_ids):
            raise ValueError("Opening knockout needs four different player IDs")
        return self


@dataclass(slots=True)
class CalendarOpeningKnockoutService:
    repository: object

    def _context(self, session, *, run_id: str, branch_id: str):
        clock, revision, world = CalendarStandaloneMatchService(self.repository)._context(
            session, run_id=run_id, branch_id=branch_id, allow_calendar_health=True,
        )
        health = saved_knockout_health(
            session, revision=revision, run_id=run_id, branch_id=branch_id,
        )
        return clock, revision, world, health

    @staticmethod
    def _play(*, run_id: str, branch_id: str, clock, saved_head: str,
              world_fingerprint: str, pre_slot_anchor: str, root_id: str,
              round_name: str, slot: int, seed: int, first, second,
              first_context=None, second_context=None, effective_health=None,
              canonical_projections=None) -> CalendarKnockoutMatch:
        context = MatchContext(
            match_id=f"{root_id}-{round_name}",
            player_a=first_context or MatchParticipantContext(player=first),
            player_b=second_context or MatchParticipantContext(player=second),
            best_of=5, games_to=11, win_by=2,
        )
        anchor = calendar_knockout_match_anchor(
            run_id=run_id, branch_id=branch_id, clock=clock, saved_head=saved_head,
            world_fingerprint=world_fingerprint, pre_slot_anchor=pre_slot_anchor,
            round_name=round_name, slot=slot, context=context, seed=seed,
            effective_health=effective_health, canonical_projections=canonical_projections,
        )
        result = MatchEngine(DeterministicRng(seed)).simulate(
            context, log_anchor_hash=anchor, effective_match_health=effective_health,
        )
        return CalendarKnockoutMatch(
            round=round_name, slot=slot, seed=seed,
            input_context=context, result=result, log_anchor_hash=anchor,
            effective_health=effective_health, canonical_projections=canonical_projections,
        )

    def canonical_preview(self, *, run_id, branch_id, command: CalendarCanonicalPreviewCommand):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            _, revision, world, _ = self._context(session, run_id=run_id, branch_id=branch_id)
            if (revision.saved_head_revision_id != command.expected_saved_head
                    or world.fingerprint != command.expected_initial_world_fingerprint):
                raise ValueError("Canonical preview source changed since inspection")
            if load_match_rows(session, run_id=run_id, branch_id=branch_id):
                raise ValueError("Played canonical inputs are already frozen in match history")
            source = CalendarCanonicalMatchSource.from_population(
                world, command.entrant_ids, CalendarStandaloneMatchService._engine_player)
            return {"schema_version": "calendar_canonical_knockout_preview.v1",
                "run_id": run_id, "branch_id": branch_id,
                "saved_head_revision_id": revision.saved_head_revision_id,
                "source": source.model_dump(mode="json"), "fingerprint": source.fingerprint}

    def inspect(self, *, run_id: str, branch_id: str) -> dict:
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            clock, revision, world, health = self._context(
                session, run_id=run_id, branch_id=branch_id
            )
            rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            if len(rows) > 1:
                raise ValueError("Opening knockout cannot coexist with another calendar match")
            if rows and not isinstance(rows[0], (CalendarOpeningKnockout, CalendarScoredOpeningKnockout)):
                raise ValueError("Standalone exhibition already owns this opening-week sporting slice")
            row = rows[0] if rows else None
            match = row.knockout if isinstance(row, CalendarScoredOpeningKnockout) else row
            saved = load_saved_calendar_match(
                revision.saved_revision.payload, run_id=run_id, branch_id=branch_id
            )
            # An unsaved points preparation promotes *only* the live row. The
            # old immutable Saved HEAD still describes the original knockout.
            # All other hash/scope mismatches fail closed.
            if saved is not None:
                if row is None or not (
                    type(saved) is type(row) and saved.fingerprint == row.fingerprint
                    or isinstance(saved, CalendarOpeningKnockout)
                    and isinstance(row, CalendarScoredOpeningKnockout)
                    and saved.fingerprint == row.knockout.fingerprint
                ):
                    raise ValueError("Saved knockout differs from live sporting state")
            is_saved = (saved is not None and row is not None
                        and type(saved) is type(row)
                        and saved.fingerprint == row.fingerprint)
            return {
                "schema_version": "calendar_opening_knockout_inspection.v1",
                "run_id": run_id, "branch_id": branch_id,
                "run_calendar": clock.to_metadata(),
                "saved_head_revision_id": revision.saved_head_revision_id,
                "draft_version": revision.working_draft.draft_version,
                "initial_world_fingerprint": world.fingerprint,
                "player_ids": [p.player_id for p in world.players],
                "knockout": match.model_dump(mode="json") if match else None,
                "knockout_fingerprint": row.fingerprint if row else None,
                "saved": is_saved,
                "health_readiness": health_readiness(health),
                "prepared_points": (
                    {"policy": row.policy.model_dump(mode="json"),
                     "awards": [a.model_dump(mode="json") for a in row.awards],
                     "first_publication_week": row.first_publication_week.model_dump(mode="json"),
                     "publication_status": "prepared_not_official",
                     "scored_fingerprint": row.fingerprint}
                    if isinstance(row, CalendarScoredOpeningKnockout) else None
                ),
            }

    def simulate(self, *, run_id: str, branch_id: str,
                 command: CalendarOpeningKnockoutCommand) -> dict:
        request_fp = canonical_hash({
            "run_id": run_id, "branch_id": branch_id,
            "command": command.model_dump(mode="json"),
        })
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            clock, revision, world, health = self._context(
                session, run_id=run_id, branch_id=branch_id
            )
            rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            if rows:
                existing = rows[0]
                # Point preparation wraps the immutable played command. An
                # exact response-loss retry must still return its ORIGINAL
                # receipt after scoring/Save/extension, never play it again
                # or return the later scoring command's fingerprint.
                if isinstance(existing, CalendarScoredOpeningKnockout):
                    existing = existing.knockout
                if (len(rows) != 1
                    or not isinstance(existing, CalendarOpeningKnockout)
                    or existing.command_id != command.command_id
                    or existing.request_fingerprint != request_fp):
                    raise ValueError("Opening-week sporting evidence already exists")
                return {"knockout": existing.model_dump(mode="json"),
                        "fingerprint": existing.fingerprint}
            if revision.saved_head_revision_id != command.expected_saved_head:
                raise ValueError("Opening knockout Saved HEAD changed since review")
            if world.fingerprint != command.expected_initial_world_fingerprint:
                raise ValueError("Opening knockout Saved population changed since review")
            roster = {p.player_id: p for p in world.players}
            if any(player_id not in roster for player_id in command.entrant_ids):
                raise ValueError("Knockout entrants must belong to Saved population")
            players = {
                player_id: CalendarStandaloneMatchService._engine_player(roster[player_id])
                for player_id in command.entrant_ids
            }
            pre_slot_anchor = canonical_hash({
                "schema_version": "calendar_opening_knockout_slot_snapshot.v1",
                "run_id": run_id, "branch_id": branch_id,
                "calendar": clock.to_metadata(), "week": [0, 1],
                "source_saved_head": revision.saved_head_revision_id,
                "initial_world": world.fingerprint,
                "entrant_ids": command.entrant_ids,
            })
            a, b, c, d = (players[pid] for pid in command.entrant_ids)
            common = dict(
                run_id=run_id, branch_id=branch_id, clock=clock,
                saved_head=revision.saved_head_revision_id,
                world_fingerprint=world.fingerprint,
                pre_slot_anchor=pre_slot_anchor, root_id=command.match_id,
            )
            health_source = (CalendarKnockoutHealthSource.from_state(health, command.entrant_ids)
                             if health is not None else None)
            def health_for(first, second):
                return health_source.for_players(first.player_id, second.player_id) if health_source else None
            canonical_source = CalendarCanonicalMatchSource.from_population(
                world, command.entrant_ids, CalendarStandaloneMatchService._engine_player)
            policy = CalendarMatchStatePolicy()
            initial = policy.initial_states(command.entrant_ids)
            def projections(first, second, states):
                return tuple(canonical_source.project(p.player_id, states) for p in (first, second))
            def context(player, states):
                return canonical_participant(canonical_source.project(player.player_id, states))
            semi_a = self._play(**common, round_name="semifinal_1",
                                slot=1, seed=command.seed, first=a, second=b,
                                first_context=context(a, initial), second_context=context(b, initial),
                                effective_health=health_for(a, b),
                                canonical_projections=projections(a, b, initial))
            semi_b = self._play(**common, round_name="semifinal_2",
                                slot=1, seed=command.seed + 1, first=c, second=d,
                                first_context=context(c, initial), second_context=context(d, initial),
                                effective_health=health_for(c, d),
                                canonical_projections=projections(c, d, initial))
            after_semis, semi_effects = advance_played_slot(initial, (semi_a, semi_b), policy)
            finalist_a = players[semi_a.result.winner_player_id]
            finalist_b = players[semi_b.result.winner_player_id]
            final = self._play(
                **common, round_name="final", slot=2, seed=command.seed + 2,
                first=finalist_a, second=finalist_b,
                first_context=context(finalist_a, after_semis),
                second_context=context(finalist_b, after_semis),
                effective_health=health_for(finalist_a, finalist_b),
                canonical_projections=projections(finalist_a, finalist_b, after_semis),
            )
            terminal, final_effects = advance_played_slot(after_semis, (final,), policy)
            knockout = CalendarOpeningKnockout(
                schema_version="calendar_opening_knockout.v4",
                canonical_source=canonical_source,
                **({"health_source": health_source} if health_source else {}),
                sporting=CalendarKnockoutSportingState(
                    policy=policy, initial=initial, after_semifinals=after_semis,
                    terminal=terminal, effects=semi_effects + final_effects,
                ),
                run_id=run_id, branch_id=branch_id,
                match_id=command.match_id, command_id=command.command_id,
                request_fingerprint=request_fp,
                source_saved_head=revision.saved_head_revision_id,
                source_initial_world_fingerprint=world.fingerprint,
                week=RunWeekPosition(calendar=clock, season_index=0, week=1),
                seed=command.seed, entrant_ids=tuple(command.entrant_ids),
                pre_slot_anchor=pre_slot_anchor,
                matches=(semi_a, semi_b, final),
                operator_label=command.operator_label, audit_reason=command.audit_reason,
            )
            put_match(session, knockout)
            return {"knockout": knockout.model_dump(mode="json"),
                    "fingerprint": knockout.fingerprint}

    def replay(self, *, run_id: str, branch_id: str, match_id: str) -> dict:
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            row = next((r for r in rows
                        if r.match_id == match_id and isinstance(
                            r, (CalendarOpeningKnockout, CalendarScoredOpeningKnockout)
                        )), None)
            if row is None:
                raise KeyError("Calendar knockout not found")
            match = row.knockout if isinstance(row, CalendarScoredOpeningKnockout) else row
            common = {
                "run_id": run_id, "branch_id": branch_id,
                "clock": match.week.calendar,
                "saved_head": match.source_saved_head,
                "world_fingerprint": match.source_initial_world_fingerprint,
                "pre_slot_anchor": match.pre_slot_anchor,
                "root_id": match.match_id,
            }
            for played in match.matches:
                ctx = played.input_context
                replayed = self._play(
                    **common, round_name=played.round, slot=played.slot,
                    seed=played.seed, first=ctx.player_a.player, second=ctx.player_b.player,
                    first_context=ctx.player_a, second_context=ctx.player_b,
                    effective_health=played.effective_health,
                    canonical_projections=played.canonical_projections,
                )
                if replayed.model_dump(mode="json") != played.model_dump(mode="json"):
                    raise ValueError("Knockout replay differs from original MatchEngine logs")
            return {
                "match_id": match_id, "fingerprint": row.fingerprint,
                "winner_player_id": match.matches[2].result.winner_player_id,
                "rally_counts": [len(m.result.rally_log.events) for m in match.matches],
                "exact_replay": True,
            }
