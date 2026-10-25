"""Run-calendar-owned MatchEngine results and immutable Saved Revision projection.

No conversion to historical 61-week RankingWeek or legacy SimulationSlot keys.
A completed standalone exhibition is real sporting evidence, not a tournament,
published points, or an implicit Week Transition.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, model_serializer, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
from beta_engine.domain.matches.models import MatchContext, MatchResult
from beta_engine.domain.players.calendar_canonical_match import (
    CalendarCanonicalMatchSource,
    canonical_participant,
)
from beta_engine.domain.players.calendar_knockout_health import (
    CalendarKnockoutHealthSource,
    calendar_knockout_match_anchor,
)
from beta_engine.domain.players.calendar_match_state import (
    CalendarKnockoutSportingState,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import CanonicalPlayerMatchProjection
from beta_engine.infrastructure.db.models import CalendarStandaloneMatchModel

COMPONENT_KEY = "calendar_standalone_match"


class CalendarStandaloneMatch(FrozenInput):
    schema_version: Literal["calendar_standalone_match.v1"] = "calendar_standalone_match.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1, max_length=128)
    command_id: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_saved_head: str = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    week: RunWeekPosition
    seed: int
    input_context: MatchContext
    result: MatchResult
    operator_label: str = Field(min_length=1)
    audit_reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_match(self):
        if (self.week.season_index, self.week.week) != (0, 1):
            raise ValueError("Standalone match v1 supports opening Week 1 only")
        if self.input_context.match_id != self.match_id or self.result.match_id != self.match_id:
            raise ValueError("Calendar match identity mismatch")
        if (
            self.result.player_a_id != self.input_context.player_a.player.player_id
            or self.result.player_b_id != self.input_context.player_b.player.player_id
            or {self.result.winner_player_id, self.result.loser_player_id}
            != {self.result.player_a_id, self.result.player_b_id}
        ):
            raise ValueError("Calendar match participants or winner differ from input")
        if self.result.rally_log is None or not self.result.rally_log.events:
            raise ValueError("Calendar match requires authoritative played rally history")
        if self.result.timeline_log is None or self.result.stamina_log is None:
            raise ValueError("Calendar match requires complete MatchEngine logs")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))



class CalendarKnockoutMatch(FrozenInput):
    """A played MatchEngine match with an exact frozen input and log anchor."""
    round: Literal["semifinal_1", "semifinal_2", "final"]
    slot: int = Field(ge=1, le=2)
    seed: int
    input_context: MatchContext
    result: MatchResult
    log_anchor_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    effective_health: EffectiveMatchHealthSnapshot | None = None
    canonical_projections: tuple[CanonicalPlayerMatchProjection, CanonicalPlayerMatchProjection] | None = None

    @model_serializer(mode="wrap")
    def historical_shape(self, handler):
        body = handler(self)
        if self.effective_health is None:
            body.pop("effective_health", None)
        if self.canonical_projections is None:
            body.pop("canonical_projections", None)
        return body

    @model_validator(mode="after")
    def verify_played_result(self):
        left = self.input_context.player_a.player.player_id
        right = self.input_context.player_b.player.player_id
        if left == right or (
            self.input_context.match_id != self.result.match_id
            or self.result.player_a_id != left or self.result.player_b_id != right
            or {self.result.winner_player_id, self.result.loser_player_id} != {left, right}
        ):
            raise ValueError("Knockout match identity, finalists or winner invalid")
        if not self.result.rally_log or not self.result.rally_log.events:
            raise ValueError("Knockout match has no authoritative rally history")
        if self.result.timeline_log is None or self.result.stamina_log is None:
            raise ValueError("Knockout match requires timeline and stamina evidence")
        return self


class CalendarOpeningKnockout(FrozenInput):
    """One complete four-player main-only knockout, not ranking publication."""
    schema_version: Literal["calendar_opening_knockout.v1", "calendar_opening_knockout.v2", "calendar_opening_knockout.v3", "calendar_opening_knockout.v4", "calendar_opening_knockout.v5"] = "calendar_opening_knockout.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1, max_length=128)  # Edition-scoped root ID.
    command_id: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_saved_head: str = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    week: RunWeekPosition
    seed: int
    entrant_ids: tuple[str, str, str, str]
    pre_slot_anchor: str = Field(pattern=r"^[0-9a-f]{64}$")
    matches: tuple[CalendarKnockoutMatch, CalendarKnockoutMatch, CalendarKnockoutMatch]
    operator_label: str = Field(min_length=1)
    audit_reason: str = Field(min_length=1)

    sporting: CalendarKnockoutSportingState | None = None
    health_source: CalendarKnockoutHealthSource | None = None
    canonical_source: CalendarCanonicalMatchSource | None = None

    @model_serializer(mode="wrap")
    def historical_shape(self, handler):
        body = handler(self)
        if self.schema_version not in ("calendar_opening_knockout.v4", "calendar_opening_knockout.v5"):
            body.pop("canonical_source", None)
        if self.schema_version != "calendar_opening_knockout.v3" and self.health_source is None:
            body.pop("health_source", None)
        if self.schema_version == "calendar_opening_knockout.v1":
            body.pop("sporting", None)
        return body

    @model_validator(mode="after")
    def validate_bracket(self):
        if (self.week.season_index, self.week.week) != (0, 1):
            raise ValueError("Opening knockout is supported in Season 1 Week 1 only")
        if len(set(self.entrant_ids)) != 4:
            raise ValueError("Opening knockout requires four distinct saved players")
        semi_a, semi_b, final = self.matches
        if [(m.round, m.slot) for m in self.matches] != [
            ("semifinal_1", 1), ("semifinal_2", 1), ("final", 2)
        ]:
            raise ValueError("Knockout rounds must have two simultaneous semis and winner-fed final")
        def pair(match):
            ctx = match.input_context
            return (ctx.player_a.player.player_id, ctx.player_b.player.player_id)
        if pair(semi_a) != self.entrant_ids[:2] or pair(semi_b) != self.entrant_ids[2:]:
            raise ValueError("Knockout semifinal pairings differ from frozen draw")
        if pair(final) != (semi_a.result.winner_player_id, semi_b.result.winner_player_id):
            raise ValueError("Knockout final must be fed by actual semifinal winners")
        for semi in (semi_a, semi_b):
            original = (
                semi.input_context.player_a
                if semi.result.winner_player_id == semi.input_context.player_a.player.player_id
                else semi.input_context.player_b
            )
            finalist = (
                final.input_context.player_a if semi is semi_a else final.input_context.player_b
            )
            if self.schema_version == "calendar_opening_knockout.v1":
                if original.model_dump(mode="json") != finalist.model_dump(mode="json"):
                    raise ValueError("Winner-fed final changes frozen player inputs")
            elif original.player != finalist.player:
                raise ValueError("Winner-fed final changes frozen player attributes")
        if self.schema_version in ("calendar_opening_knockout.v2", "calendar_opening_knockout.v3", "calendar_opening_knockout.v4", "calendar_opening_knockout.v5"):
            if self.sporting is None:
                raise ValueError("v2 knockout requires owned sporting checkpoints")
            if set(p.player_id for p in self.sporting.initial) != set(self.entrant_ids):
                raise ValueError("Sporting checkpoints differ from knockout entrants")
            self.sporting.verify_matches(self.matches)
        elif "sporting" in self.model_fields_set:
            raise ValueError("Historical v1 knockout cannot carry v2 sporting state")
        if self.schema_version in ("calendar_opening_knockout.v4", "calendar_opening_knockout.v5"):
            source = self.canonical_source
            if (source is None or source.source_initial_world_fingerprint != self.source_initial_world_fingerprint
                    or set(p.player_id for p in source.records) != set(self.entrant_ids)):
                raise ValueError("Canonical source does not match knockout population/entrants")
            for match in self.matches:
                states = self.sporting.initial if match.slot == 1 else self.sporting.after_semifinals
                ctx = match.input_context
                projections = tuple(source.project(pid, states) for pid in (
                    ctx.player_a.player.player_id, ctx.player_b.player.player_id))
                if (match.canonical_projections != projections
                        or (ctx.player_a, ctx.player_b) != tuple(canonical_participant(p) for p in projections)):
                    raise ValueError("Match does not consume its 57-attribute canonical projection")
        elif "canonical_source" in self.model_fields_set or any(m.canonical_projections is not None for m in self.matches):
            raise ValueError("Historical knockout cannot acquire canonical v4 inputs")
        if self.schema_version == "calendar_opening_knockout.v3" or (
                self.schema_version in ("calendar_opening_knockout.v4", "calendar_opening_knockout.v5") and self.health_source is not None):
            source = self.health_source
            if source is None or set(p.player_id for p in source.profiles) != set(self.entrant_ids):
                raise ValueError("Health-backed knockout requires exact entrant Health source")
            original, current = source.source_week.calendar, self.week.calendar
            if ((original.weeks_per_year, original.season_start_year_week, original.start_year)
                    != (current.weeks_per_year, current.season_start_year_week, current.start_year)
                    or original.season_count > current.season_count):
                raise ValueError("Knockout Health source clock differs from played calendar")
            for match in self.matches:
                ctx = match.input_context
                expected = source.for_players(ctx.player_a.player.player_id, ctx.player_b.player.player_id)
                if match.effective_health != expected:
                    raise ValueError("Played Health input differs from frozen Saved source")
                anchor = calendar_knockout_match_anchor(
                    run_id=self.run_id, branch_id=self.branch_id, clock=self.week.calendar,
                    saved_head=self.source_saved_head, world_fingerprint=self.source_initial_world_fingerprint,
                    pre_slot_anchor=self.pre_slot_anchor, round_name=match.round, slot=match.slot,
                    context=ctx, seed=match.seed, effective_health=expected,
                    canonical_projections=match.canonical_projections,
                )
                if match.log_anchor_hash != anchor or match.result.rally_log.input_snapshot_hash != anchor:
                    raise ValueError("Health snapshot is detached from actual played log anchor")
        elif (self.schema_version not in ("calendar_opening_knockout.v4", "calendar_opening_knockout.v5") and "health_source" in self.model_fields_set
              or any(m.effective_health is not None for m in self.matches)):
            raise ValueError("Historical knockout cannot acquire newer Health inputs")
        if self.schema_version in ("calendar_opening_knockout.v4", "calendar_opening_knockout.v5"):
            for match in self.matches:
                anchor = calendar_knockout_match_anchor(
                    run_id=self.run_id, branch_id=self.branch_id, clock=self.week.calendar,
                    saved_head=self.source_saved_head, world_fingerprint=self.source_initial_world_fingerprint,
                    pre_slot_anchor=self.pre_slot_anchor, round_name=match.round, slot=match.slot,
                    context=match.input_context, seed=match.seed, effective_health=match.effective_health,
                    canonical_projections=match.canonical_projections,
                )
                if match.log_anchor_hash != anchor or match.result.rally_log.input_snapshot_hash != anchor:
                    raise ValueError("Canonical attributes are detached from played log input")
        if len({m.input_context.match_id for m in self.matches}) != 3:
            raise ValueError("Knockout match IDs must be distinct")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


CalendarMatchEvidence = CalendarStandaloneMatch | CalendarOpeningKnockout


def _parse_calendar_match(serialized: str) -> CalendarMatchEvidence:
    raw = json.loads(serialized)
    if not isinstance(raw, dict):
        raise ValueError("Malformed calendar match evidence")
    if raw.get("schema_version") == "calendar_standalone_match.v1":
        return CalendarStandaloneMatch.model_validate_json(serialized)
    if raw.get("schema_version") in ("calendar_opening_knockout.v1", "calendar_opening_knockout.v2", "calendar_opening_knockout.v3", "calendar_opening_knockout.v4", "calendar_opening_knockout.v5"):
        return CalendarOpeningKnockout.model_validate_json(serialized)
    if raw.get("schema_version") == "calendar_scored_opening_knockout.v1":
        # Delayed import avoids a circular dependency on the historical,
        # byte-stable v1 tournament model.
        from beta_engine.infrastructure.db.calendar_knockout_awards_state import (
            CalendarScoredOpeningKnockout,
        )
        return CalendarScoredOpeningKnockout.model_validate_json(serialized)
    raise ValueError("Unknown calendar match evidence schema; refuse reinterpretation")


def load_match_rows(session: Session, *, run_id: str, branch_id: str,
                    _verified_source=None) -> tuple[CalendarMatchEvidence, ...]:
    rows = session.scalars(
        select(CalendarStandaloneMatchModel)
        .where(CalendarStandaloneMatchModel.run_id == run_id,
               CalendarStandaloneMatchModel.branch_id == branch_id)
        .order_by(CalendarStandaloneMatchModel.match_id)
    ).all()
    states = []
    for row in rows:
        if _verified_source is not None:
            source = _verified_source
            expected = source.fingerprint
            if (
                (source.run_id, source.branch_id, source.match_id, source.command_id,
                 source.request_fingerprint, expected)
                == (run_id, branch_id, row.match_id, row.command_id,
                    row.request_fingerprint, row.fingerprint)
                and canonical_hash(json.loads(row.payload_json)) == expected
            ):
                # The caller authenticated this exact Saved root in its current
                # transaction. Hash actual live values and all physical scope
                # columns; never trust only the stored fingerprint column.
                states.append(source)
                continue
        state = _parse_calendar_match(row.payload_json)
        if (
            (state.run_id, state.branch_id, state.match_id, state.command_id,
             state.request_fingerprint, state.fingerprint)
            != (run_id, branch_id, row.match_id, row.command_id,
                row.request_fingerprint, row.fingerprint)
        ):
            raise ValueError("Calendar match SQLite identity/hash mismatch")
        states.append(state)
    return tuple(states)


def put_match(session: Session, state: CalendarMatchEvidence) -> None:
    if session.get(CalendarStandaloneMatchModel, (state.run_id, state.branch_id, state.match_id)):
        raise ValueError("Calendar match already exists")
    session.add(CalendarStandaloneMatchModel(
        run_id=state.run_id, branch_id=state.branch_id, match_id=state.match_id,
        command_id=state.command_id, request_fingerprint=state.request_fingerprint,
        fingerprint=state.fingerprint, payload_json=state.model_dump_json(),
    ))
    session.flush()


def replace_saved_knockout_with_prepared_awards(
    session: Session, *, original: CalendarOpeningKnockout, scored,
) -> None:
    """Atomic version promotion of one live row; never edits signed history."""
    existing = load_match_rows(
        session, run_id=original.run_id, branch_id=original.branch_id
    )
    if len(existing) != 1 or not isinstance(existing[0], CalendarOpeningKnockout):
        raise ValueError("Prepared awards require one unmodified, unscored knockout row")
    if existing[0].fingerprint != original.fingerprint:
        raise ValueError("Knockout changed since reviewed award source")
    if scored.knockout.fingerprint != original.fingerprint:
        raise ValueError("Prepared awards refer to another knockout")
    row = session.get(CalendarStandaloneMatchModel, (
        original.run_id, original.branch_id, original.match_id
    ))
    if row is None:
        raise ValueError("Prepared award source row disappeared")
    row.command_id = scored.command_id
    row.request_fingerprint = scored.request_fingerprint
    row.fingerprint = scored.fingerprint
    row.payload_json = scored.model_dump_json()
    session.flush()


def capture_saved_calendar_match(session: Session, payload: dict, *, run_id: str, branch_id: str,
                                 _defer_full_verification: bool = False,
                                 _authenticated_tour_prefix=None, _repository=None) -> None:
    states = load_match_rows(session, run_id=run_id, branch_id=branch_id)
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        capture_checkpoint,
    )
    capture_checkpoint(session, payload, states[0] if len(states) == 1 else None,
                       run_id=run_id, branch_id=branch_id,
                       _defer_full_verification=_defer_full_verification, _repository=_repository)
    from beta_engine.infrastructure.db.calendar_tour import capture_tour
    capture_tour(session, payload, run_id=run_id, branch_id=branch_id,
                 _defer_full_verification=_defer_full_verification,
                 _authenticated_prefix=_authenticated_tour_prefix, _repository=_repository)
    if states:
        # Exactly one operation-scoped completed standalone match in this slice.
        if len(states) != 1:
            raise ValueError("Calendar standalone match v1 supports exactly one match")
        state = states[0]
        payload["content"][COMPONENT_KEY] = {
            "fingerprint": state.fingerprint,
            "state": state.model_dump(mode="json"),
        }


def _parse_saved_calendar_match_evidence(payload: dict, *, run_id: str, branch_id: str) -> CalendarMatchEvidence | None:
    """Validate original signed MatchEngine evidence, not the sporting checkpoint.

    Restore calls the full Saved sporting verifier itself immediately below, in
    the same transaction; avoid performing that entire 7-match replay twice.
    """
    component = payload.get("content", {}).get(COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "state"}:
        raise ValueError("Invalid Saved calendar standalone match component")
    # MatchEngine rally/timeline objects contain enum-valued fields. Use the
    # JSON validation boundary just as for the live SQLite row: strict frozen
    # input models must decode serialized enum values, not treat dict strings
    # as in-process Enum instances.
    state = _parse_calendar_match(json.dumps(component["state"]))
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id, branch_id, component["fingerprint"]
    ):
        raise ValueError("Saved calendar standalone match identity/hash mismatch")
    if payload.get("run", {}).get("run_calendar") != state.week.calendar.to_metadata():
        # A Run-wide horizon extension keeps earlier match W, basis and source
        # untouched. The old signed match clock remains independently verifiable.
        from beta_engine.domain.calendar.run_calendar import RunCalendar
        metadata = payload.get("run", {}).get("run_calendar")
        if not isinstance(metadata, dict):
            raise ValueError("Saved calendar match has no Run calendar")
        current = RunCalendar.from_metadata(metadata)
        original = state.week.calendar
        if (
            (current.weeks_per_year, current.season_start_year_week, current.start_year)
            != (original.weeks_per_year, original.season_start_year_week, original.start_year)
            or current.season_count <= original.season_count
        ):
            raise ValueError("Saved calendar match clock cannot be reinterpreted")
    return state


def decode_prevalidated_calendar_sources(payload: dict, *, run_id: str, branch_id: str):
    """Decode an ALREADY authenticated Saved HEAD without a redundant replay.

    INTERNAL ONLY: its caller MUST first pass these exact immutable payload bytes
    through repository._validated_branch_revision_state_in_session. That gate
    checks the signed hash, identity, ancestry and all sporting/Tour components;
    its content-digest keyed validation cache invalidates on any byte mutation.
    Use only for an authenticated Admin read or an atomically validated restore
    which has just checked BOTH immutable source payloads. Never use with raw
    history, public Viewer, a new/unverified Save candidate, or unknown JSON.
    A Save coordinator may decode its authenticated PREVIOUS Saved HEAD as a
    prefix; it must still fully validate the new candidate and every new event.
    Re-parse and re-check each source's scope/fingerprint; the only work elided
    here is a second full MatchEngine/ranking fold of the very same Signed bytes.
    """
    evidence = _parse_saved_calendar_match_evidence(
        payload, run_id=run_id, branch_id=branch_id
    )
    from beta_engine.domain.tournaments.calendar_tour import parse_tour_json
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        parse_checkpoint_json,
    )

    content = payload.get("content", {})
    cp_raw = content.get("calendar_player_sporting_checkpoint")
    checkpoint = None
    checkpoint_fingerprint = None
    if cp_raw is not None:
        if not isinstance(cp_raw, dict) or set(cp_raw) != {"fingerprint", "state"}:
            raise ValueError("Invalid prevalidated Saved sporting component")
        checkpoint = parse_checkpoint_json(json.dumps(cp_raw["state"]))
        checkpoint_fingerprint = checkpoint.fingerprint
        if (checkpoint.run_id, checkpoint.branch_id, checkpoint_fingerprint) != (
            run_id, branch_id, cp_raw["fingerprint"]
        ):
            raise ValueError("Prevalidated Saved sporting scope/hash changed")

    tour_raw = content.get("calendar_tour_authority")
    tour = None
    if tour_raw is not None:
        if not isinstance(tour_raw, dict) or set(tour_raw) != {"fingerprint", "state"}:
            raise ValueError("Invalid prevalidated Saved Tour component")
        tour = parse_tour_json(json.dumps(tour_raw["state"]))
        if (tour.run_id, tour.branch_id, tour.fingerprint) != (
            run_id, branch_id, tour_raw["fingerprint"]
        ):
            raise ValueError("Prevalidated Saved Tour scope/hash changed")
        if checkpoint is None or (
            tour.checkpoint_fingerprint != checkpoint_fingerprint
            or tour.week.ordinal != checkpoint.week.ordinal
        ):
            raise ValueError("Prevalidated Saved Tour sporting owner changed")
    return evidence, checkpoint, tour


def load_saved_calendar_match(payload: dict, *, run_id: str, branch_id: str, _sporting_component_proofs=None, _verified_global_prefix=None) -> CalendarMatchEvidence | None:
    """Validate both the played MatchEngine evidence and the full Saved owner."""
    return load_saved_calendar_sources(payload,run_id=run_id,branch_id=branch_id,
        _sporting_component_proofs=_sporting_component_proofs,
        _verified_global_prefix=_verified_global_prefix)[0]


def load_saved_calendar_sources(payload: dict, *, run_id: str, branch_id: str,
                                _sporting_component_proofs=None,
                                _verified_saved_prefix=None, _verified_global_prefix=None):
    """Return the coupled sources, sharing only exact transaction-local proofs."""
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        saved_checkpoint,
    )
    # Exact content-addressed proof reuse is private to a single validated
    # lineage walk. Never retain it across requests/transactions. Tour authority
    # remains independently validated for each revision even on a sporting hit.
    key = None
    verified = None
    if _sporting_component_proofs is not None:
        content = payload.get('content', {})
        raw_checkpoint = content.get('calendar_player_sporting_checkpoint') or {}
        raw_checkpoint_state = raw_checkpoint.get('state') if isinstance(raw_checkpoint,dict) else None
        native_dependencies = (
            {k:content.get(k) for k in ('calendar_tour_authority','player_lifecycle','player_health_state','run_prospect_source')}
            if isinstance(raw_checkpoint_state,dict) and raw_checkpoint_state.get('schema_version') in {'calendar_sporting_checkpoint.v11', 'calendar_sporting_checkpoint.v12', 'calendar_sporting_checkpoint.v13'}
            else {}
        )
        key = canonical_hash({'run_id':run_id,'branch_id':branch_id,'run':payload.get('run'),
            'components':{k:content.get(k) for k in ('initial_world','calendar_standalone_match','calendar_player_sporting_checkpoint')},
            'native_dependencies':native_dependencies})
        verified = _sporting_component_proofs.get(key)
    if verified is None:
        root_key = None
        root_proofs = None
        if _sporting_component_proofs is not None:
            root_proofs = _sporting_component_proofs.setdefault('_opening_roots', {})
            root_key = canonical_hash({'run_id':run_id,'branch_id':branch_id,
                'run':payload.get('run'),
                'match':payload.get('content',{}).get('calendar_standalone_match')})
        if root_proofs is not None and root_key in root_proofs:
            state = root_proofs[root_key]
        else:
            state = _parse_saved_calendar_match_evidence(payload,run_id=run_id,branch_id=branch_id)
            if root_proofs is not None:
                root_proofs[root_key] = state
        checkpoint = saved_checkpoint(payload, state, run_id=run_id, branch_id=branch_id,
            _prefix_proofs=_sporting_component_proofs.setdefault('_prefixes',{}) if _sporting_component_proofs is not None else None,
            _verified_saved_prefix=_verified_saved_prefix, _verified_global_prefix=_verified_global_prefix)
        if key is not None:
            _sporting_component_proofs[key] = (state,checkpoint)
    else:
        state,checkpoint = verified
    from beta_engine.infrastructure.db.calendar_tour import saved_tour
    # The validation scope is ONE caller-owned Signed lineage walk. Many
    # successive revisions retain exactly the same native Tour and lifecycle
    # despite changing unrelated working or simulation components. Parsing
    # 1,000-player lifecycle and replaying every historical ranking for each
    # identical source adds seconds per revision after a physical restart.
    #
    # The proof cache keys the complete canonical inputs used by saved_tour:
    # run clock, world, played root, sporting, Tour and lifecycle. No cache
    # survives the request, and _validated_saved_revision_in_session still
    # independently checks every revision's signature, owner, bytes and ancestry.
    tour_proofs = (
        _sporting_component_proofs.setdefault("_verified_tour_sources", {})
        if _sporting_component_proofs is not None else None
    )
    tour_key = None
    if tour_proofs is not None:
        content = payload.get("content", {})
        tour_key = canonical_hash({
            "run_id": run_id,
            "branch_id": branch_id,
            "run": payload.get("run"),
            "world": content.get("initial_world"),
            "played_root": content.get("calendar_standalone_match"),
            "sporting": content.get("calendar_player_sporting_checkpoint"),
            "tour": content.get("calendar_tour_authority"),
            "lifecycle": content.get("player_lifecycle"),
            "health": content.get("player_health_state"),
            "prospects": content.get("run_prospect_source"),
        })
    if tour_proofs is not None and tour_key in tour_proofs:
        tour = tour_proofs[tour_key]
    else:
        tour = saved_tour(
            payload, run_id=run_id, branch_id=branch_id, checkpoint=checkpoint,
            **({"_verified_competition":checkpoint} if checkpoint is not None and checkpoint.schema_version in {"calendar_sporting_checkpoint.v12", "calendar_sporting_checkpoint.v13"} else {}),
        )
        if tour_proofs is not None:
            tour_proofs[tour_key] = tour
    return state,checkpoint,tour


def restore_saved_calendar_match(
    session: Session, *, current_payload: dict, target_payload: dict,
    run_id: str, branch_id: str, _validated_saved_sources=None,
) -> None:
    # Ordinary callers keep strict full Saved source verification.
    # The repository restore coordinator may pass decoded inputs ONLY after
    # authenticating both exact Saved Revision payloads in the same transaction.
    # This avoids repeated source folds while preserving live-owner checks and
    # the independent post-restore capture/revalidation.
    if _validated_saved_sources is None:
        current = _parse_saved_calendar_match_evidence(
            current_payload, run_id=run_id, branch_id=branch_id,
        )
        target = _parse_saved_calendar_match_evidence(
            target_payload, run_id=run_id, branch_id=branch_id,
        )
    else:
        current, _current_checkpoint, _current_tour = _validated_saved_sources[0]
        target, _target_checkpoint, _target_tour = _validated_saved_sources[1]
    live = load_match_rows(session, run_id=run_id, branch_id=branch_id)
    if tuple(s.fingerprint for s in live) != (
        (current.fingerprint,) if current else ()
    ):
        raise ValueError("Live calendar match differs from current Saved head")
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        restore_checkpoint,
    )
    from beta_engine.infrastructure.db.calendar_tour import restore_tour
    restore_tour(session, current_payload=current_payload, target_payload=target_payload,
                 run_id=run_id, branch_id=branch_id,
                 _validated_states=(
                     (_validated_saved_sources[0][2], _validated_saved_sources[1][2])
                     if _validated_saved_sources is not None else None
                 ))
    restore_checkpoint(session, current_payload=current_payload, target_payload=target_payload,
                       current=current, target=target, run_id=run_id, branch_id=branch_id,
                       _validated_states=(
                           (_validated_saved_sources[0][1], _validated_saved_sources[1][1])
                           if _validated_saved_sources is not None else None
                       ))
    for state in live:
        session.delete(session.get(CalendarStandaloneMatchModel, (run_id, branch_id, state.match_id)))
    session.flush()
    if target is not None:
        put_match(session, target)
